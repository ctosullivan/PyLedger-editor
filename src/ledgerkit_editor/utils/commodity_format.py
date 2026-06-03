"""Commodity format propagation for ledgerkit-editor.

Wraps ledgerkit's CommodityStyle API to apply consistent commodity formatting
throughout a journal file on save. The workflow is:

  1. ``extract_commodity_styles(journal)`` — pull the inferred CommodityStyle
     dict straight from ``Journal.commodity_styles`` (ledgerkit v0.1.0+).
  2. ``apply_commodity_styles(text, styles)`` — post-process serialised journal
     text, replacing each amount token with a version formatted according to
     its commodity's CommodityStyle.

Only step 2 touches text; step 1 reads the already-parsed Journal model so
there is no additional parsing cost.
"""

from __future__ import annotations

import re
from decimal import Decimal
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ledgerkit.commodity_style import CommodityStyle
    from ledgerkit.models import Journal

__all__ = [
    "apply_commodity_styles",
    "extract_commodity_styles",
]

# ---------------------------------------------------------------------------
# Regexes used by apply_commodity_styles
# ---------------------------------------------------------------------------

# Matches a posting line with an explicit amount (4-space indent, account,
# 2+-space separator, amount token) so we can find the amount substring.
#
# Purpose: identify posting lines in serialised journal text so only those
#          lines are processed; header lines, comment lines, and directive
#          lines are left unchanged.
#
# Group breakdown:
#   (1) indent:   exactly 4 leading spaces — hledger posting indent.
#   (2) account:  account name, which may contain single internal spaces
#                 (e.g. "Assets:Bank:AIB Cormac").
#                 [^\s;] — first char must not be space or ';' (skips comment
#                 lines such as "    ; note").
#                 \S*(?:[ ]\S+)* — rest of name, allowing single-space words.
#   (3) sep:      2 or more spaces — mandatory separator before the amount.
#   (4) amount:   rest of the line up to an optional inline comment prefix
#                 ("  ;"). This is captured greedily so the full amount string
#                 is available for commodity pattern matching.
#
# Edge cases:
#   "    ; note"          — [^\s;] blocks ';'; not matched.
#   "    expenses:food"   — no " {2,}" + non-space; not matched.
#   "    exp:food  50 EUR  ; note" — matched; amount = "50 EUR  ; note";
#                           comment is stripped before replacement (see code).
_POSTING_RE = re.compile(r"^(    )([^\s;]\S*(?:[ ]\S+)*)( {2,})(.+)$")

# Matches a suffix-style amount token: optional leading '-', digits/commas/dots,
# optional decimal portion, then one space and an alphabetic commodity code.
#
# Purpose: recognise amounts like "500.00 EUR", "1,234 GBP", "-30.00 EUR" so
#          the numeric portion and commodity can be extracted for reformatting.
#
# Group breakdown:
#   (1) sign:     optional '-' at the start.
#   (2) numeric:  digits, commas, and dots (the number before the commodity).
#   (3) space:    exactly one space separating number from commodity code.
#   (4) commodity: letter-started alphanumeric token (e.g. "EUR", "USD", "AAPL").
#
# Edge cases:
#   "500.00 EUR"    — matches; sign='', numeric='500.00', commodity='EUR'.
#   "-30.00 EUR"    — matches; sign='-', numeric='30.00', commodity='EUR'.
#   "1,234.56 GBP"  — matches; numeric='1,234.56'.
#   "£30.00"        — does NOT match (no trailing alphabetic token).
#   "500.00EUR"     — does NOT match (no space before commodity).
_SUFFIX_RE = re.compile(r"^(-?)([\d,.][\d,.]*)([ ])([A-Za-z][A-Za-z0-9]*)$")

# Matches a prefix-style amount token: non-digit commodity symbol at the start,
# optional '-' (hledger prefix-negative convention: £-30.00), then the number.
#
# Purpose: recognise amounts like "£30.00", "$-1,234.56", "€0" so the
#          commodity symbol and numeric portion can be extracted.
#
# Group breakdown:
#   (1) commodity:  one or more characters that are not digits, commas, dots,
#                   whitespace, or '-' — captures currency symbols like £,$,€,¥.
#   (2) sign:       optional '-' immediately after the commodity symbol, per
#                   hledger's prefix-negative convention (e.g. £-30.00).
#   (3) numeric:    one or more digits, commas, and dots forming the quantity.
#
# Edge cases:
#   "£30.00"    — matches; commodity='£', sign='', numeric='30.00'.
#   "£-30.00"   — matches; commodity='£', sign='-', numeric='30.00'.
#   "$1,234.56" — matches; commodity='$', numeric='1,234.56'.
#   "500.00 EUR" — does NOT match (starts with a digit).
#   "-£30.00"   — does NOT match (leading '-' not consumed; use _NEGATIVE_PREFIX_RE).
_PREFIX_RE = re.compile(r"^([^\d,.\s-]+)(-?)([\d,.][\d,.]*)$")

# Matches a negative prefix-style amount where the minus sign leads the token,
# before the commodity symbol (e.g. "-£30.00", "-$1,234.56").
#
# Purpose: hledger negative-prefix amounts can appear either as "£-30.00" (symbol
#          first) or as "-£30.00" (minus first). This regex handles the minus-first
#          variant that _PREFIX_RE cannot match.
#
# Group breakdown:
#   (1) commodity:  non-digit/non-separator symbol after the leading '-'.
#   (2) numeric:    digits, commas, dots forming the absolute quantity.
#
# Edge cases:
#   "-£30.00"   — matches; commodity='£', numeric='30.00'.
#   "-$1,234"   — matches; commodity='$', numeric='1,234'.
#   "-30.00 EUR" — does NOT match (no prefix symbol after '-').
_NEGATIVE_PREFIX_RE = re.compile(r"^-([^\d,.\s-]+)([\d,.][\d,.]*)$")


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def extract_commodity_styles(journal: "Journal") -> "dict[str, CommodityStyle]":
    """Return commodity styles inferred from a parsed Journal.

    Delegates to ``Journal.commodity_styles`` for the base styles (first-seen
    amount per commodity, with ``commodity`` directives taking priority), then
    upgrades any commodity whose first-seen amount had no group separator if a
    later amount does have one.

    This "prefer richest format" pass ensures that files where small amounts
    (e.g. ``10.00 EUR``) precede large ones (e.g. ``1,500.00 EUR``) correctly
    infer the comma group separator from the larger amount.

    Args:
        journal: A parsed Journal object (from ledgerkit.load or parse_string).

    Returns:
        Dict mapping commodity symbol → CommodityStyle.  Empty when the
        journal has no amounts with raw strings.
    """
    from ledgerkit.commodity_style import CommodityStyle  # noqa: PLC0415

    styles: dict = dict(journal.commodity_styles)

    # Upgrade any commodity whose base style has no group separator if a
    # later posting has one — handles mixed-format files.
    for txn in journal.transactions:
        for p in txn.postings:
            if not (p.amount and p.amount.raw and p.amount.commodity):
                continue
            commodity = p.amount.commodity
            current = styles.get(commodity)
            if current is None or current.group_separator:
                continue  # not tracked yet, or already has a group separator
            try:
                candidate = CommodityStyle.infer(commodity, p.amount.raw)
                if candidate.group_separator:
                    styles[commodity] = candidate
            except Exception:  # noqa: BLE001
                pass

    return styles


def apply_commodity_styles(
    text: str,
    styles: "dict[str, CommodityStyle]",
) -> str:
    """Post-process serialised journal text to apply detected commodity formats.

    For each posting line, extracts the amount token, looks up its commodity in
    ``styles``, and replaces the token with a version formatted by
    ``CommodityStyle.format()``.  Lines whose commodity is not in ``styles``,
    and all non-posting lines (headers, comments, directives, blank lines), are
    passed through unchanged.

    This is a pure text-transformation step intended to run after
    ``align_posting_amounts()`` so that the two post-processors compose cleanly:
    format first (commodity precision/grouping), align second (column spacing).

    Args:
        text:   Serialised journal text from ledgerkit.journal_to_text() or
                similar.
        styles: Dict from ``extract_commodity_styles``.  When empty, returns
                ``text`` unchanged immediately.

    Returns:
        Journal text with amount tokens reformatted per their commodity style.
    """
    if not styles:
        return text

    result: list[str] = []
    for line in text.splitlines():
        result.append(_reformat_posting_line(line, styles))
    return "\n".join(result) + ("\n" if text.endswith("\n") else "")


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _reformat_posting_line(
    line: str,
    styles: "dict[str, CommodityStyle]",
) -> str:
    """Reformat the amount token in a single posting line if its commodity is known."""
    m = _POSTING_RE.match(line)
    if not m:
        return line

    indent, account, sep, rest = m.group(1), m.group(2), m.group(3), m.group(4)

    # Peel off any inline comment ("  ; ...") so the amount token is clean.
    comment_tail = ""
    comment_idx = rest.find("  ;")
    if comment_idx > 0:
        comment_tail = rest[comment_idx:]
        rest = rest[:comment_idx]

    amount_str = rest.strip()
    reformatted = _reformat_amount(amount_str, styles)
    if reformatted is None:
        return line

    return indent + account + sep + reformatted + comment_tail


def _reformat_amount(
    amount_str: str,
    styles: "dict[str, CommodityStyle]",
) -> str | None:
    """Attempt to reformat amount_str using the matching style.

    Returns the reformatted string, or None when no matching style is found.
    """
    # Try suffix style first (e.g. "500.00 EUR").
    m = _SUFFIX_RE.match(amount_str)
    if m:
        sign, numeric, _space, commodity = m.group(1), m.group(2), m.group(3), m.group(4)
        style = styles.get(commodity)
        if style is None:
            return None
        qty = _parse_numeric(sign + numeric)
        if qty is None:
            return None
        return style.format(qty)

    # Try prefix style (e.g. "£30.00" or "£-30.00").
    m = _PREFIX_RE.match(amount_str)
    if m:
        commodity, sign, numeric = m.group(1), m.group(2), m.group(3)
        style = styles.get(commodity)
        if style is None:
            return None
        qty = _parse_numeric(("-" if sign else "") + numeric)
        if qty is None:
            return None
        formatted = style.format(qty)
        # CommodityStyle.format() for negative prefix produces "SYMBOL-NUMBER"
        # (e.g. "£-300.00") but the ledgerkit parser only accepts "-SYMBOL+NUMBER"
        # (e.g. "-£300.00").  Convert to the parseable form.
        if sign and style.prefix and formatted.startswith(commodity + "-"):
            formatted = "-" + commodity + formatted[len(commodity) + 1:]
        return formatted

    # Try negative-prefix style (e.g. "-£30.00").
    m = _NEGATIVE_PREFIX_RE.match(amount_str)
    if m:
        commodity, numeric = m.group(1), m.group(2)
        style = styles.get(commodity)
        if style is None:
            return None
        qty = _parse_numeric("-" + numeric)
        if qty is None:
            return None
        formatted = style.format(qty)
        # CommodityStyle.format() for negative prefix produces "SYMBOL-NUMBER"
        # (e.g. "£-300.00") but the ledgerkit parser only accepts "-SYMBOL+NUMBER"
        # (e.g. "-£300.00").  Convert to the parseable form.
        if style.prefix and formatted.startswith(commodity + "-"):
            formatted = "-" + commodity + formatted[len(commodity) + 1:]
        return formatted

    return None


def _parse_numeric(s: str) -> Decimal | None:
    """Parse a numeric string (possibly with comma thousands separator) to Decimal.

    Strips comma thousands separators before passing to Decimal().  Returns
    None when the string cannot be converted.
    """
    try:
        return Decimal(s.replace(",", ""))
    except Exception:
        return None
