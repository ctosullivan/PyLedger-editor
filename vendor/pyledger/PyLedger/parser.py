"""Journal file parser for PyLedger.

Converts raw .journal text into Journal/Transaction/Posting objects.
See docs/hledger-compatibility.md for the transaction block structure and
the list of supported format features.
"""

from __future__ import annotations

import datetime
import re
from decimal import Decimal, InvalidOperation

from PyLedger.models import Amount, BalanceAssertion, Journal, Posting, PriceDirective, SourceSpan, Transaction


# ---------------------------------------------------------------------------
# Module-level constants
# ---------------------------------------------------------------------------

# Matches the two-or-more-space + comment-character separator used in directives.
#
# Purpose: split directive lines on the boundary between directive body and
#          inline comment, per hledger's rule that a single space may appear
#          inside a body value (e.g. an account name like "expenses:fun money")
#          but two or more spaces before a comment character always begin a comment.
#
# Pattern: \s{2,}[;#]
#   \s{2,}  — two or more whitespace characters (spaces or tabs)
#   [;#]    — semicolon or hash: both are recognised comment introducers in PyLedger
#
# Edge cases:
#   - A single space before ';' or '#' is NOT a separator (belongs to the body)
#   - Only the FIRST match is used (re.split with maxsplit=1)
#   - Lines with no such pattern return the original body unchanged
_TWO_SPACE_SEP = re.compile(r"\s{2,}[;#]")


class ParseError(ValueError):
    """Raised on malformed hledger journal input.

    Attributes:
        line_number: 1-based line number where the error was detected,
                     or None if not applicable.
    """

    def __init__(self, message: str, line_number: int | None = None) -> None:
        self.line_number = line_number
        location = f" (line {line_number})" if line_number is not None else ""
        super().__init__(f"{message}{location}")


# ---------------------------------------------------------------------------
# Regex patterns
# ---------------------------------------------------------------------------

# Matches a transaction header line in hledger journal format.
#
# Purpose: extract date, optional status flag, optional transaction code,
#          description text, and optional inline comment from a single
#          non-indented line that begins a transaction block.
#
# Group breakdown:
#   (1) simple date             — captured as a raw string and passed to
#                                 _parse_simple_date; see _SIMPLE_DATE for detail.
#                                 Handles YYYY-MM-DD, YYYY/MM/DD, YYYY.MM.DD,
#                                 and year-omitted forms (M/DD, MM-DD, etc.);
#                                 leading zeros optional on month and day.
#   (2) [*!]?                  — status flag: '*' = cleared, '!' = pending;
#                                absent means uncleared
#   (3) (?:\(([^)]*)\))?       — transaction code in parentheses, e.g. (INV-42);
#                                outer parens consumed, only inner text captured;
#                                [^)]* prevents greedily crossing a closing paren
#   (4) .*?                    — description: lazy so the trailing comment anchor
#                                can match; stripped of surrounding whitespace
#                                after the match
#   (5) (?:\s*;\s*(.*))?       — inline comment following ';'; the ';' itself and
#                                surrounding spaces are consumed but not captured
#
# Edge cases:
#   - Description may be empty (e.g. "2024-01-01 *" with no text after the flag)
#   - Code may be absent even when a flag is present, and vice versa
#   - A bare ';' anywhere after the date is treated as the comment delimiter;
#     this matches hledger's own behaviour (first ';' ends the description)
#   - Mixed separators (e.g. "2024-01/15") are captured here without complaint;
#     _parse_simple_date accepts them since each separator pair is matched
#     independently
_TXN_HEADER = re.compile(
    r"^((?:\d{4}[-/.])?(?:\d{1,2})[-/.](?:\d{1,2}))"
    r"\s*([*!])?"
    r"\s*(?:\(([^)]*)\))?"
    r"\s*(.*?)"
    r"(?:\s*;\s*(.*))?$"
)

# Parses a simple date string captured by _TXN_HEADER into its year, month,
# and day components.
#
# Purpose: decompose a raw date token (any of the accepted formats) into
#          integer components so that datetime.date() can validate and
#          construct the final date object.
#
# Group breakdown:
#   (1) (\d{4})    — four-digit year; the entire (?:...) wrapper is optional,
#                    so this group is None when the year is omitted
#   [-/.]          — separator: hyphen, forward-slash, or dot; not captured
#   (2) (\d{1,2})  — month, 1–2 digits, leading zero optional
#   [-/.]          — separator (same character classes; mixing is tolerated)
#   (3) (\d{1,2})  — day of month, 1–2 digits, leading zero optional
#
# Edge cases:
#   - Year absent ("1/31", "01-31"): group 1 is None; caller supplies default_year
#   - Invalid calendar values ("2024-13-01"): regex matches but datetime.date()
#     raises ValueError, which _parse_simple_date converts to ParseError
#   - Dot separator ("2010.1.31"): matched by [-/.]; note this is unambiguous in
#     header context because amounts (which also use '.') are on indented lines
_SIMPLE_DATE = re.compile(
    r"^(?:(\d{4})[-/.])?(\d{1,2})[-/.](\d{1,2})$"
)

# Matches an hledger amount string in either prefix-symbol or suffix-symbol form.
#
# Purpose: parse the quantity and commodity out of an amount token that has
#          already been separated from the account name.  Supports both
#          '£30.00' (symbol before number) and '30.00 EUR' (symbol after number),
#          optional thousands-separator commas, and a leading minus sign.
#
# Group breakdown:
#   (1) (-?)                      — optional leading minus sign; always applied
#                                   to the quantity regardless of symbol position
#   (2) ([^\d,.\s-]*)             — prefix commodity: any run of characters that
#                                   are not digits, commas, dots, whitespace, or
#                                   minus; matches '£', '$', '€', etc.; empty
#                                   string when the commodity is a suffix
#   (3) ([\d,]+(?:\.\d*)?)         — numeric quantity: one or more digits/commas
#                                   followed by an optional decimal part; commas
#                                   are stripped before Decimal conversion
#   (4) ([A-Za-z][A-Za-z0-9]*)?   — suffix commodity: a letter-started alphanumeric
#                                   token (e.g. EUR, USD, AAPL); absent when the
#                                   commodity is a prefix symbol
#
# Edge cases:
#   - Exactly one of group 2 or group 4 must be non-empty; if both are empty
#     the caller raises ParseError (no commodity)
#   - A space between prefix symbol and quantity is allowed: '£ 30.00' matches
#     because \s* between groups 2 and 3 absorbs it
#   - Integer quantities ('£100') are valid; the decimal part is optional
#   - Negative suffix amounts ('-30.00 EUR'): the minus in group 1 precedes the
#     empty group 2, then the quantity in group 3, then EUR in group 4
#   - Trailing decimal with no fractional digits ('$1,000.') is accepted;
#     Python's Decimal('1000.') is valid and equals Decimal('1000')
_AMOUNT = re.compile(
    r"^(-?)"
    r"([^\d,.\s-]*)"
    r"\s*([\d,]+(?:\.\d*)?)"
    r"\s*([A-Za-z][A-Za-z0-9]*)?"
    r"$"
)

# Matches an hledger amount string when `decimal-mark ,` is active (European
# notation where comma is the decimal mark and period is the thousands separator).
#
# Purpose: parse amounts of the form "1.234,56" or "€1.234,56" where the
#          convention is the reverse of the default _AMOUNT regex.  Selected
#          by _parse_amount when decimal_mark == ",".
#
# Group breakdown: (mirrors _AMOUNT; only the numeric group differs)
#   (1) (-?)                      — optional leading minus sign
#   (2) ([^\d,.\s-]*)             — prefix commodity symbol (£, $, €, etc.)
#   (3) ([\d.]*(?:,\d*)?)          — numeric quantity in comma-decimal form:
#                                   zero or more digits/periods (digit-group marks)
#                                   followed by an optional comma+decimal digits;
#                                   periods are stripped and the comma is replaced
#                                   with a period before Decimal conversion
#   (4) ([A-Za-z][A-Za-z0-9]*)?   — suffix commodity symbol (EUR, USD, etc.)
#
# Edge cases:
#   - "1.234,56"  → period=thousands, comma=decimal → Decimal("1234.56")
#   - "100,50"    → no thousands separator          → Decimal("100.50")
#   - "1.234"     → period=thousands, no decimal    → Decimal("1234")
#   - "100"       → no separators at all            → Decimal("100")
#   - "€1.234,56" → prefix "€" + comma-decimal numeric
#   - "1.234,56 EUR" → suffix "EUR" style
#   - Trailing comma with no fractional digits ('1.234,') is accepted;
#     Python's Decimal('1234.') is valid and equals Decimal('1234')
_AMOUNT_COMMA = re.compile(
    r"^(-?)"
    r"([^\d,.\s-]*)"
    r"\s*([\d.]*(?:,\d*)?)"
    r"\s*([A-Za-z][A-Za-z0-9]*)?"
    r"$"
)

# Matches a P (market price) directive line.
#
# Purpose: detect a P directive and capture its three space-delimited components
#          so the handler can extract date, commodity symbol, and price amount.
#
# Group breakdown:
#   (1) (\S+)  — raw date string; no whitespace; passed to _parse_simple_date
#   (2) (\S+)  — COMMODITY1SYMBOL: the commodity being priced, e.g. "€", "$", "AAPL";
#                no whitespace — multi-word commodity names are not valid in this position
#   (3) (.+)   — raw COMMODITY2AMOUNT string, e.g. "$1.35", "1.40 USD";
#                may include a trailing inline comment ("  ; note") — caller strips
#                with _strip_directive_comment before passing to _parse_amount
#
# Edge cases:
#   - "P 2024-01-01 AAPL $179.00  ; note" → group 3 is "$179.00  ; note";
#     _strip_directive_comment removes the trailing "  ;" portion
#   - "P 2024-01-01 AAPL" (no price amount) does not match; caller raises ParseError
#   - Lines starting with "P" but not "P " never reach this handler because they
#     are either transaction headers (start with a date digit) or posting lines
#     (indented)
#   - "P" alone (no whitespace) does not match because \s+ requires at least one space
_P_DIRECTIVE = re.compile(r"^P\s+(\S+)\s+(\S+)\s+(.+)$")

# Matches an alias directive line.
#
# Purpose: detect an alias directive and capture the entire body after
#          "alias " so the handler can determine whether it is a basic
#          alias or a regex alias and parse it accordingly.
#
# Group breakdown:
#   (1) (.+)  — the raw alias body, e.g. "checking = assets:bank" or
#               "/^(.+):bank/ = \1" or "/old/=new  ; note" or "/old/=new  # note";
#               inline comments (  ; or  #) are stripped by _strip_directive_comment
#               before further parsing
#
# Edge cases:
#   - "alias" with no body does not match because \s+ requires at least
#     one space and (.+) requires at least one character after it
#   - "aliases" (plural) does not match because \s+ requires whitespace
#     immediately after the exact word "alias"
#   - Leading whitespace on line: the outer guard (not line[0:1].isspace())
#     prevents indented lines from ever reaching this check
_ALIAS_DIRECTIVE = re.compile(r"^alias\s+(.+)$")

# Matches an end aliases directive line (exact keyword, no trailing content).
#
# Purpose: detect the "end aliases" directive that clears all currently
#          active alias rules from the parse state.  The handler passes the
#          line through _strip_directive_comment first, so trailing "; comment"
#          and "# comment" sequences (with two-or-more-space prefix) are stripped
#          before this regex is applied.
#
# Group breakdown:
#   No capture groups — presence of the directive is sufficient.
#
# Edge cases:
#   - "end  aliases" (two spaces between words) matches because \s+ allows
#     multiple spaces — consistent with hledger's lenient whitespace handling
#   - "end aliases  ; comment" or "end aliases  # comment": the handler strips
#     the trailing comment via _strip_directive_comment before matching, so
#     both forms are recognised correctly
#   - "end aliasesX" does not match because $ anchors immediately after "aliases"
_END_ALIASES = re.compile(r"^end\s+aliases$")


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------

def _parse_simple_date(
    date_str: str, lineno: int, default_year: int
) -> datetime.date:
    """Parse a simple date string into a datetime.date.

    Accepts YYYY-MM-DD, YYYY/MM/DD, YYYY.MM.DD, and year-omitted forms such as
    M/DD or MM-DD. Leading zeros on month and day are optional. When the year is
    absent, default_year is used (typically the current calendar year).

    Raises:
        ParseError: if the string does not match the simple date pattern or the
                    resulting calendar date is invalid (e.g. month 13).
    """
    m = _SIMPLE_DATE.match(date_str)
    if not m:
        raise ParseError(f"invalid date {date_str!r}", lineno)
    year_str, month_str, day_str = m.groups()
    year = int(year_str) if year_str else default_year
    try:
        return datetime.date(year, int(month_str), int(day_str))
    except ValueError as exc:
        raise ParseError(f"invalid date {date_str!r}: {exc}", lineno)


def _parse_txn_header(line: str, lineno: int, default_year: int) -> Transaction:
    """Parse a transaction header line into a Transaction with no postings."""
    m = _TXN_HEADER.match(line)
    if not m:
        raise ParseError(f"invalid transaction header: {line!r}", lineno)

    date_str, flag, code, description, comment = m.groups()
    date = _parse_simple_date(date_str, lineno, default_year)

    comment_text = (comment or "").strip()
    return Transaction(
        date=date,
        description=(description or "").strip(),
        postings=[],
        cleared=(flag == "*"),
        pending=(flag == "!"),
        code=(code or "").strip(),
        comment=comment_text,
        source_line=lineno,
        inline_comment=comment_text or None,
    )


def _parse_amount(raw: str, lineno: int, decimal_mark: str = ".") -> Amount:
    """Parse a raw amount string into an Amount.

    Supports prefix commodity (£30.00), suffix commodity (30.00 EUR),
    negative amounts (-£5.00, -30.00 EUR), and digit-group separators.

    When decimal_mark is "." (default), commas are treated as thousands
    separators and periods as decimal marks (e.g. 1,234.56).
    When decimal_mark is ",", periods are thousands separators and commas
    are decimal marks (e.g. 1.234,56).
    """
    if decimal_mark == ",":
        m = _AMOUNT_COMMA.match(raw.strip())
    else:
        m = _AMOUNT.match(raw.strip())

    if not m:
        raise ParseError(f"invalid amount: {raw!r}", lineno)

    minus, prefix_sym, quantity_str, suffix_sym = m.groups()

    commodity = (prefix_sym or suffix_sym or "").strip()
    if not commodity:
        raise ParseError(f"amount has no commodity symbol: {raw!r}", lineno)

    if decimal_mark == ",":
        # Period is the digit-group mark; comma is the decimal mark.
        quantity_clean = quantity_str.replace(".", "").replace(",", ".")
    else:
        # Comma is the digit-group mark; period is the decimal mark (default).
        quantity_clean = quantity_str.replace(",", "")

    try:
        quantity = Decimal(minus + quantity_clean)
    except InvalidOperation:
        raise ParseError(f"invalid numeric quantity in amount: {raw!r}", lineno)

    return Amount(quantity=quantity, commodity=commodity)


def _strip_directive_comment(raw: str) -> str:
    """Strip an inline comment from a directive body using the 2-space rule.

    Returns the body text before the first '  ;' sequence, stripped of
    surrounding whitespace. If no such sequence exists, returns the stripped
    input unchanged.
    """
    parts = _TWO_SPACE_SEP.split(raw, maxsplit=1)
    return parts[0].strip()


# Matches the numeric-and-optional-suffix part of a commodity sample amount.
#
# Purpose: extract the commodity symbol from a commodity directive whose body
#          is an amount token (e.g. "$1,000.00", "1,000.00 EUR", "1000. AAAA").
#          Also handles a bare symbol (e.g. "$", "INR") where no digits follow.
#
# Group breakdown:
#   (1) [^\d,.\s"-]*  — prefix symbol: any run of chars that are NOT digits,
#                       commas, dots, whitespace, quotes, or minus; captures
#                       '$', '£', '€', etc. when they lead the token; empty
#                       string when the commodity is a suffix token
#   (2) [\d,. ]*      — numeric portion: digits, commas, dots, and spaces
#                       (thousands-separated amounts can contain internal spaces)
#   (3) \s*([^\d,.\s]*)  — suffix symbol: any non-numeric run after the numeric
#                          portion, stripped of leading whitespace; captures
#                          'EUR', 'USD', 'AAPL' etc.; empty when prefix symbol
#
# Edge cases:
#   - "1000. AAAA"  → prefix='' numeric='1000. ' suffix='AAAA'
#   - "$1,000.00"   → prefix='$' numeric='1,000.00' suffix=''
#   - "$"           → prefix='$' numeric='' suffix=''
#   - "INR"         → prefix='' numeric='' suffix='INR'  (falls through to bare-symbol path)
#   - '1 000 000.0000' → internal spaces handled by numeric group
_COMMODITY_AMOUNT = re.compile(
    r'^([^\d,.\s"-]*)'
    r'([\d,. ]*)'
    r'\s*([^\d,.\s]*)'
    r'$'
)


def _extract_commodity_symbol(raw: str, lineno: int) -> str:
    """Extract the commodity symbol from a commodity directive body.

    Handles all hledger commodity directive forms:
      - Quoted:       "AAPL 2023"  →  AAPL 2023
      - Prefix+amt:   $1,000.00    →  $
      - Suffix+amt:   1,000.00 EUR →  EUR
      - Bare symbol:  INR          →  INR
      - Bare sigil:   $            →  $
      - Empty quoted: ""           →  (empty string, the no-symbol commodity)

    Raises:
        ParseError: if the body is empty after stripping.
    """
    body = raw.strip()
    if not body:
        raise ParseError("commodity directive has no symbol", lineno)

    # Quoted symbol: "AAPL 2023" or ""
    if body.startswith('"'):
        end = body.find('"', 1)
        if end == -1:
            raise ParseError(f"commodity directive has unterminated quoted symbol: {body!r}", lineno)
        return body[1:end]

    m = _COMMODITY_AMOUNT.match(body)
    if not m:
        raise ParseError(f"commodity directive: cannot parse symbol from {body!r}", lineno)

    prefix, numeric, suffix = m.group(1), m.group(2), m.group(3)

    if prefix:
        return prefix
    if suffix:
        return suffix.strip()
    # Numeric-only body (e.g. "1000.") — no symbol, no-symbol commodity
    return ""


# Matches a balance assertion marker embedded in a posting amount token.
# Purpose: detect the first occurrence of ==*, ==, =*, or = that is preceded
#          and followed by whitespace, so we can split a posting amount token
#          into "posting amount" and "assertion amount".
# Group breakdown:
#   (1) ==* | == | =* | = — the assertion marker; alternatives ordered
#       longest-first so ==* is tried before == and =* before =
# Edge cases:
#   - ==* must precede == in the alternation to avoid consuming only ==
#   - =* must precede = in the alternation to avoid consuming only =
#   - surrounding \s+ prevents matching = inside commodity symbols or
#     numbers (e.g. scientific notation, if ever supported)
#   - a bare = at the start of amount_raw ("= $500") indicates a balance
#     assignment (amount elided); this regex will not match it because
#     there is no leading \s+ before the =
_ASSERTION_MARKER_RE = re.compile(r"\s+(==\*|==|=\*|=)\s+")


def _parse_posting(line: str, lineno: int, decimal_mark: str = ".") -> Posting:
    """Parse a single posting line (already stripped of leading whitespace).

    Splits on two-or-more whitespace to separate account from amount.
    If no amount token is present the posting is elided (amount=None).
    decimal_mark controls how the amount's numeric portion is interpreted
    ("." = period-decimal default; "," = comma-decimal / EU style).
    """
    # Purpose: split the posting line into (account, amount) on the first run
    #          of two or more whitespace characters.  hledger requires at least
    #          two spaces to separate account from amount so that account names
    #          containing single spaces (e.g. "expenses:fun money") are preserved.
    # Pattern: \s{2,}
    #   \s{2,} — two or more whitespace characters (spaces or tabs)
    #   maxsplit=1 ensures only the first such gap is used as the delimiter;
    #             any further double-spaces inside the amount are left intact
    # Edge cases:
    #   - A posting with no amount ("  assets:bank") produces a single-element
    #     list; the caller treats this as an elided amount (None)
    #   - An account name with a single internal space ("expenses:fun money  £5")
    #     is correctly split because the delimiter requires two spaces
    parts = re.split(r"\s{2,}", line, maxsplit=1)
    account = parts[0].strip()

    if not account:
        raise ParseError("posting has no account name", lineno)

    # Strip inline comment from the amount portion and capture it
    amount_raw = ""
    posting_inline_comment: str | None = None
    if len(parts) > 1:
        amount_part = parts[1]
        # Remove trailing ; comment and capture the text
        comment_idx = amount_part.find(";")
        if comment_idx != -1:
            posting_inline_comment = amount_part[comment_idx + 1:].strip() or None
            amount_part = amount_part[:comment_idx]
        amount_raw = amount_part.strip()

    if not amount_raw:
        return Posting(account=account, amount=None, source_line=lineno, inline_comment=posting_inline_comment)

    # Detect a balance assertion marker (=, ==, =*, ==*) in the amount token.
    # If found, split into posting amount and assertion amount.
    assertion: BalanceAssertion | None = None
    am = _ASSERTION_MARKER_RE.search(amount_raw)
    if am:
        marker = am.group(1)
        posting_amount_raw = amount_raw[: am.start()].strip()
        assertion_amount_raw = amount_raw[am.end() :].strip()
        assertion = BalanceAssertion(
            amount=_parse_amount(assertion_amount_raw, lineno, decimal_mark),
            inclusive="*" in marker,
            sole_commodity=marker.startswith("=="),
        )
        amount_raw = posting_amount_raw

    if not amount_raw:
        # Posting amount elided (balance assignment syntax) — amount stays None
        return Posting(
            account=account,
            amount=None,
            balance_assertion=assertion,
            source_line=lineno,
            inline_comment=posting_inline_comment,
        )

    return Posting(
        account=account,
        amount=_parse_amount(amount_raw, lineno, decimal_mark),
        balance_assertion=assertion,
        source_line=lineno,
        inline_comment=posting_inline_comment,
    )


def _parse_alias_body(body: str, lineno: int) -> tuple[str, str, bool]:
    """Parse alias directive body; return (old_or_pattern, replacement, is_regex)."""
    if body.startswith("/"):
        # Regex alias: /PATTERN/ = REPLACEMENT
        # Scan forward to find the closing unescaped '/'.
        i = 1
        while i < len(body):
            if body[i] == "/" and body[i - 1] != "\\":
                break
            i += 1
        if i >= len(body):
            raise ParseError(f"unclosed regex in alias directive: {body!r}", lineno)
        pattern_str = body[1:i].replace("\\/", "/")
        rest = body[i + 1 :].lstrip()
        if not rest.startswith("="):
            raise ParseError(f"missing '=' in alias directive: {body!r}", lineno)
        replacement = rest[1:].lstrip()
        try:
            re.compile(pattern_str, re.IGNORECASE)  # validate regex early
        except re.error as exc:
            raise ParseError(f"invalid regex in alias directive: {exc}", lineno)
        return (pattern_str, replacement, True)
    else:
        # Basic alias: OLD = NEW  (spaces around '=' are optional)
        if "=" not in body:
            raise ParseError(f"missing '=' in alias directive: {body!r}", lineno)
        idx = body.index("=")
        old = body[:idx].rstrip()
        new = body[idx + 1 :].lstrip()
        if not old:
            raise ParseError(f"empty account name in alias directive: {body!r}", lineno)
        return (old, new, False)


def _apply_aliases(account: str, aliases: list[tuple[str, str, bool]]) -> str:
    """Apply active alias rules to an account name, most-recently-defined first (LIFO).

    Basic aliases match as an exact name or colon-delimited prefix.
    Regex aliases use re.sub with IGNORECASE and support backreferences.
    """
    for old, new, is_regex in reversed(aliases):
        if is_regex:
            # Purpose: substitute matching substring in account name.
            # re.IGNORECASE per hledger spec ("REGEX is case-insensitive as usual").
            # Backreferences in `new` (e.g. \1) are supported by re.sub natively.
            account = re.sub(old, new, account, flags=re.IGNORECASE)
        else:
            # Basic alias: replace OLD as exact match or as colon-delimited prefix.
            # "checking" rewrites "checking" → new and "checking:a" → new + ":a"
            # but NOT "other:checking" (prefix boundary enforced by + ":").
            if account == old:
                account = new
            elif account.startswith(old + ":"):
                account = new + account[len(old):]
    return account


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def resolve_elision(txn: Transaction) -> list[Posting]:
    """Return the full posting list for txn with any elided amount resolved.

    If txn has zero elided postings, returns list(txn.postings) unchanged.
    If txn has one elided posting and exactly one commodity in the explicit
    postings, replaces the elided posting with one inferred Posting whose
    amount is the negation of that commodity's net.
    If txn has one elided posting and N > 1 commodities, replaces the elided
    posting with N inferred Postings (one per commodity, sorted by symbol).

    Edge cases:
      - 2+ elided postings: returns list(txn.postings) unchanged (parse-time error).
      - All explicit postings have amount=None (empty commodity_sums): returns
        list(txn.postings) unchanged.
      - Inferred postings carry inferred=True and the elided posting's source_line.

    Args:
        txn: A Transaction, parsed or constructed programmatically.

    Returns:
        List of Posting objects representing the resolved transaction.
    """
    elided_indices = [i for i, p in enumerate(txn.postings) if p.amount is None]
    if len(elided_indices) != 1:
        return list(txn.postings)

    elided_idx = elided_indices[0]
    elided_posting = txn.postings[elided_idx]

    # Build per-commodity sums from all explicit postings.
    commodity_sums: dict[str, Decimal] = {}
    for p in txn.postings:
        if p.amount is None:
            continue
        c = p.amount.commodity
        commodity_sums[c] = commodity_sums.get(c, Decimal(0)) + p.amount.quantity

    if not commodity_sums:
        return list(txn.postings)

    # Generate one synthetic posting per commodity (sorted for determinism).
    synthetic = [
        Posting(
            account=elided_posting.account,
            amount=Amount(-net, commodity),
            source_line=elided_posting.source_line,
            inferred=True,
        )
        for commodity, net in sorted(commodity_sums.items())
    ]

    result = list(txn.postings)
    result[elided_idx : elided_idx + 1] = synthetic
    return result


def _flush_txn(
    txn: Transaction,
    end: int,
    all_lines: list[str],
    source_file: str,
) -> None:
    """Attach SourceSpan and raw_text to a transaction that is about to be finalised."""
    start = txn.source_line or 1
    txn.source_span = SourceSpan(file=source_file, start_line=start, end_line=end)
    txn.raw_text = "\n".join(all_lines[start - 1 : end]) + "\n"


def _parse_string_impl(
    text: str,
    default_year: int,
    errors_out: list[ParseError] | None,
    source_file: str = "(string)",
) -> Journal:
    """Shared body for parse_string and parse_string_lenient.

    When errors_out is None, raises ParseError on the first malformed line.
    When errors_out is a list, appends errors and continues parsing; malformed
    transactions are discarded and parsing resumes at the next boundary.
    """
    all_lines = text.splitlines()
    transactions: list[Transaction] = []
    prices: list[PriceDirective] = []
    declared_accounts: list[str] = []
    declared_commodities: list[str] = []
    declared_payees: list[str] = []
    declared_tags: list[str] = []
    aliases: list[tuple[str, str, bool]] = []  # (old_or_pattern, replacement, is_regex)
    decimal_mark: str = "."  # updated by decimal-mark directive
    current_txn: Transaction | None = None
    current_txn_last_lineno: int | None = None  # tracks end_line for source_span
    last_posting_in_txn: Posting | None = None  # for standalone comment attribution
    in_block_comment = False
    in_subdirective = False  # True while consuming indented subdirective lines
    skip_until_blank = False  # lenient mode: True while skipping a malformed transaction

    for lineno, raw in enumerate(all_lines, start=1):
        line = raw.rstrip()

        # --- Block comment mode ---
        #
        # Purpose: skip every line between a `comment` directive and its
        #          matching `end comment` directive (or EOF).
        #
        # `comment` and `end comment` are non-indented directives. The
        # `comment` keyword may be followed by an inline comment but must be
        # the first word on the line. `end comment` is matched after stripping
        # any surrounding whitespace to be lenient about trailing spaces.
        #
        # Edge cases:
        #   - A `comment` block that reaches EOF without `end comment` is
        #     silently accepted; the parser simply consumes the rest of the file
        #   - A `comment` directive encountered mid-transaction flushes the open
        #     transaction first, then enters block-comment mode
        #   - `end comment` outside a block comment falls through to the
        #     "silently skip" branch (no error raised)
        #   - Nested `comment` directives inside a block comment are ignored
        if in_block_comment:
            if line.strip() == "end comment":
                in_block_comment = False
            continue

        # --- Lenient mode: skip remainder of a malformed transaction ---
        #
        # When errors_out is not None and a ParseError occurs mid-transaction,
        # skip_until_blank is set True and current_txn is cleared. Subsequent
        # lines are discarded until a blank line or a new transaction header is
        # encountered, at which point normal parsing resumes.
        if skip_until_blank:
            if not line.strip():
                skip_until_blank = False
                in_subdirective = False
                continue
            if not re.match(r"^(?:\d{4}[-/.])?(?:\d{1,2})[-/.](?:\d{1,2})(?=[\s*!(]|$)", line):
                continue
            skip_until_blank = False
            # Fall through: treat this line as a new transaction header.

        # --- Blank line: end the current block ---
        if not line.strip():
            if current_txn is not None:
                end = current_txn_last_lineno or (current_txn.source_line or 1)
                _flush_txn(current_txn, end, all_lines, source_file)
                transactions.append(current_txn)
                current_txn = None
                current_txn_last_lineno = None
                last_posting_in_txn = None
            in_subdirective = False
            continue

        # --- Comment-only line (whole-line or indented follow-on `;` / `#`) ---
        #
        # Two distinct sub-cases share this branch:
        #
        # 1. Column-0 (non-indented) `#` or `;` — a standalone top-level comment.
        #    These are ALWAYS silently skipped regardless of whether a transaction
        #    block is open.  They never contribute to a transaction's comment fields
        #    and never extend its source_span.
        #
        # 2. Indented (leading whitespace) `#` or `;` inside an open transaction —
        #    a follow-on comment line.  `;`-led lines are attached to the preceding
        #    posting's inline_comment (or to the transaction's inline_comment if no
        #    posting has been seen yet in this block). `#`-led lines update the span
        #    but do not attach their text.
        #
        # The `is_indented` flag disambiguates the two sub-cases; `lstrip()` is
        # applied only for the startswith test, not for the indentation check.
        #
        # Edge cases:
        #   - A column-0 `;` with no blank line between two transactions is a
        #     top-level comment; it must NOT be captured as a follow-on comment
        #     on the previous transaction's last posting.
        #   - An empty `;` (nothing after the semicolon) sets inline_comment to
        #     None, not to the empty string.
        is_indented = line[0:1].isspace()
        stripped = line.lstrip()
        if stripped.startswith(";") or stripped.startswith("#"):
            if current_txn is not None and is_indented:
                current_txn_last_lineno = lineno
                if stripped.startswith(";"):
                    comment_text = stripped[1:].strip()
                    if last_posting_in_txn is None:
                        if current_txn.inline_comment:
                            current_txn.inline_comment += "\n" + comment_text
                        else:
                            current_txn.inline_comment = comment_text or None
                    else:
                        if last_posting_in_txn.inline_comment:
                            last_posting_in_txn.inline_comment += "\n" + comment_text
                        else:
                            last_posting_in_txn.inline_comment = comment_text or None
            continue

        # --- Transaction header (non-indented line starting with a simple date) ---
        #
        # Purpose: quickly determine whether a non-indented line opens a new
        #          transaction block before handing off to _parse_txn_header.
        #          This check runs before posting detection so that a date-like
        #          token at column 0 is always treated as a new header, never as
        #          an un-indented posting inside an open block.
        # Pattern: ^(?:\d{4}[-/.])?(?:\d{1,2})[-/.](?:\d{1,2})(?=[\s*!(]|$)
        #   ^                         — anchored to start of the rstripped line
        #   (?:\d{4}[-/.])?           — optional four-digit year + separator
        #   (?:\d{1,2})[-/.]          — month (1–2 digits) + separator
        #   (?:\d{1,2})               — day (1–2 digits)
        #   (?=[\s*!(]|$)             — lookahead: must be followed by whitespace,
        #                               a status flag, the start of a code, or
        #                               end-of-line; prevents matching bare numeric
        #                               expressions that aren't transaction dates
        # Edge cases:
        #   - "2024-13-45 Bad" passes this check but fails in _parse_simple_date
        #     when datetime.date() rejects the invalid calendar values
        #   - "1.5" without a trailing space/flag does NOT match (lookahead fails),
        #     preventing accidental collision with decimal amounts on directive lines
        if re.match(r"^(?:\d{4}[-/.])?(?:\d{1,2})[-/.](?:\d{1,2})(?=[\s*!(]|$)", line):
            if current_txn is not None:
                # No blank line between transactions — flush previous block
                end = current_txn_last_lineno or (current_txn.source_line or 1)
                _flush_txn(current_txn, end, all_lines, source_file)
                transactions.append(current_txn)
            in_subdirective = False
            current_txn_last_lineno = None
            last_posting_in_txn = None
            try:
                current_txn = _parse_txn_header(line, lineno, default_year)
                current_txn_last_lineno = lineno
            except ParseError as _err:
                if errors_out is None:
                    raise
                errors_out.append(_err)
                current_txn = None
                skip_until_blank = True
            continue

        # --- Block comment start (`comment` directive) ---
        #
        # A non-indented line whose first whitespace-delimited token is exactly
        # "comment" opens a block comment. Anything after "comment" on the same
        # line is ignored (treated as inline commentary on the directive itself).
        # Any open transaction is flushed before entering block-comment mode so
        # that a `comment` block sitting between transactions is parsed cleanly.
        if not line[0:1].isspace() and line.split()[0] == "comment":
            if current_txn is not None:
                transactions.append(current_txn)
                current_txn = None
            in_subdirective = False
            in_block_comment = True
            continue

        # --- Subdirective lines (indented lines following account/commodity/payee) ---
        #
        # Purpose: consume Ledger-style indented subdirectives (e.g. "format …"
        #          below a commodity directive) without treating them as postings
        #          or raising ParseError.  in_subdirective is set to True whenever
        #          we finish processing an account/commodity/payee directive line;
        #          it is cleared on the next non-indented, non-blank line.
        #
        # Edge cases:
        #   - Blank lines above already clear in_subdirective via the blank-line
        #     branch (which sets current_txn=None and falls through; the next
        #     non-blank line will hit this check with in_subdirective still True
        #     only if there was no blank line — so blank lines naturally end the
        #     subdirective block)
        #   - An indented subdirective line that contains a valid posting syntax
        #     is still skipped here (subdirective wins); the containing file is
        #     expected to be well-formed per hledger conventions
        if in_subdirective:
            if line[0:1].isspace():
                continue  # consume indented subdirective silently
            in_subdirective = False
            # fall through to process this non-indented line normally

        # --- account directive ---
        #
        # Purpose: record a declared account name for strict-mode checking.
        #          The account name follows the keyword and may contain spaces
        #          and ';' characters; an inline comment is delimited by the
        #          first occurrence of two-or-more spaces followed by ';'.
        #          Indented lines that follow (Ledger-style subdirectives) are
        #          consumed silently via the in_subdirective flag.
        #
        # Edge cases:
        #   - "account a:b;c" (single space before ';') → name is "a:b;c"
        #   - "account a:b  ; note" → name is "a:b"
        #   - "accounts" does not match because \s+ requires whitespace after
        #     the exact word "account"
        if not line[0:1].isspace() and re.match(r"^account\s+", line):
            body = line[len("account"):].lstrip()
            account_name = _strip_directive_comment(body)
            if account_name:
                declared_accounts.append(_apply_aliases(account_name, aliases))
            in_subdirective = True
            continue

        # --- commodity directive ---
        #
        # Purpose: record a declared commodity symbol for strict-mode checking.
        #          Supports all hledger commodity directive forms: sample amount
        #          with prefix symbol ($1,000.00), sample amount with suffix
        #          symbol (1,000.00 EUR), bare symbol ($, INR), quoted symbol
        #          ("AAPL 2023"), empty-quoted no-symbol (""), and numeric-only
        #          (1000.) for format declarations.
        #
        # Edge cases:
        #   - "commodity" with no body raises ParseError (empty symbol)
        #   - Indented "format" subdirectives are consumed via in_subdirective
        #   - The same symbol may be declared more than once; deduplication is
        #     done at check time, not parse time
        if not line[0:1].isspace() and re.match(r"^commodity(\s|$)", line):
            rest = line[len("commodity"):].strip()
            body = _strip_directive_comment(rest)
            symbol = _extract_commodity_symbol(body, lineno)
            declared_commodities.append(symbol)
            in_subdirective = True
            continue

        # --- payee directive ---
        #
        # Purpose: record a declared payee name for strict-mode / payee checking.
        #          The payee name follows the keyword; inline comments are stripped
        #          with the 2-space rule. Quoted empty-string payee ("") is stored
        #          as the empty string. Tags in comments are ignored per the spec.
        #
        # Edge cases:
        #   - 'payee ""' → stored as "" (the no-payee sentinel)
        #   - "payee Whole Foods  ; comment" → "Whole Foods"
        #   - Indented Ledger-style subdirectives are consumed silently
        if not line[0:1].isspace() and re.match(r"^payee\s+", line):
            body = line[len("payee"):].lstrip()
            payee_name = _strip_directive_comment(body)
            # Unquote a quoted payee name (e.g. payee "" or payee "Smith & Co")
            if payee_name.startswith('"') and payee_name.endswith('"'):
                payee_name = payee_name[1:-1]
            declared_payees.append(payee_name)
            in_subdirective = True
            continue

        # --- tag directive ---
        #
        # Purpose: record a declared tag name for strict-mode / tag checking.
        #          TAGNAME follows the keyword with no spaces. Inline comments
        #          are stripped using the 2-space separator rule. Indented
        #          subdirectives are consumed silently via in_subdirective.
        #
        # Edge cases:
        #   - "tag item-id  ; note" → tag name is "item-id"
        #   - "tags" does not match because \s+ requires whitespace after
        #     the exact word "tag"
        if not line[0:1].isspace() and re.match(r"^tag\s+", line):
            body = line[len("tag"):].lstrip()
            tag_name = _strip_directive_comment(body)
            if tag_name:
                declared_tags.append(tag_name)
            in_subdirective = True
            continue

        # --- decimal-mark directive ---
        #
        # Purpose: declare which character is the decimal mark for amount
        #          parsing in this file. Affects all postings from this point
        #          forward (typically placed at the top of file).
        #          Only "." (default) and "," are valid values.
        #
        # Edge cases:
        #   - "decimal-mark ." → default; no change to behaviour
        #   - "decimal-mark ,"  → commas are decimal marks; periods are
        #     digit-group marks (e.g. 1.234,56 = 1234.56)
        #   - Any other value raises ParseError
        #   - No subdirectives are defined for decimal-mark; in_subdirective
        #     is NOT set (nothing to consume)
        if not line[0:1].isspace() and re.match(r"^decimal-mark(\s|$)", line):
            rest = line[len("decimal-mark"):].strip()
            dm = _strip_directive_comment(rest)
            if dm not in (".", ","):
                _err = ParseError(
                    f"decimal-mark must be '.' or ',',"
                    f" got {dm!r}",
                    lineno,
                )
                if errors_out is None:
                    raise _err
                errors_out.append(_err)
                continue
            decimal_mark = dm
            continue

        # --- P directive ---
        #
        # Purpose: record a market price declaration (commodity conversion rate
        #          on a date). Stored in `prices` for later use by valuation
        #          reports. No subdirectives are defined for P; in_subdirective
        #          is NOT set.
        #
        # Edge cases:
        #   - "P DATE COMMODITY PRICE  ; comment" → comment stripped before parse
        #   - A P directive encountered while a transaction is open does NOT close
        #     the transaction (consistent with other directive handlers); P inside
        #     a transaction block is malformed but handled leniently
        #   - A "P " line that fails the full regex (missing commodity or amount)
        #     raises ParseError immediately
        if not line[0:1].isspace() and line.startswith("P "):
            m_p = _P_DIRECTIVE.match(line)
            if not m_p:
                _err = ParseError(f"invalid P directive: {line!r}", lineno)
                if errors_out is None:
                    raise _err
                errors_out.append(_err)
                continue
            date_str, commodity1, amount_raw = m_p.groups()
            amount_clean = _strip_directive_comment(amount_raw)
            try:
                p_date = _parse_simple_date(date_str, lineno, default_year)
                p_price = _parse_amount(amount_clean, lineno, decimal_mark)
            except ParseError as _err:
                if errors_out is None:
                    raise
                errors_out.append(_err)
                continue
            prices.append(PriceDirective(date=p_date, commodity=commodity1, price=p_price))
            continue

        # --- alias directive ---
        #
        # Purpose: register an account-name alias rule. Rules accumulate in `aliases`
        #          and are applied to every posting account name parsed after this point.
        #          Basic aliases match as an exact name or colon-delimited prefix;
        #          regex aliases match any substring (case-insensitive, backrefs supported).
        #          Aliases are also applied to account names in `account` directives.
        #          No subdirectives; in_subdirective is NOT set.
        #
        # Edge cases:
        #   - "alias /invalid[/ = x" → ParseError (invalid regex detected early)
        #   - "alias  = new" (empty OLD) → ParseError
        #   - "alias old = new  ; comment" or "alias old = new  # comment"
        #     → comment stripped by _strip_directive_comment before body parse
        #   - Rules accumulate; use "end aliases" to clear all
        if not line[0:1].isspace() and _ALIAS_DIRECTIVE.match(line):
            m_alias = _ALIAS_DIRECTIVE.match(line)
            body = _strip_directive_comment(m_alias.group(1))
            try:
                old, new, is_regex = _parse_alias_body(body, lineno)
            except ParseError as _err:
                if errors_out is None:
                    raise
                errors_out.append(_err)
                continue
            aliases.append((old, new, is_regex))
            continue

        # --- end aliases directive ---
        #
        # Purpose: clear all active alias rules so postings after this line are
        #          not rewritten. A no-op if no aliases are currently active.
        #          _strip_directive_comment is applied first so that trailing
        #          "; comment" or "# comment" (with two-space separation) are
        #          stripped before the keyword is matched.
        #
        # Edge cases:
        #   - "end aliases  ; done" or "end aliases  # done" → comment stripped,
        #     directive recognised correctly
        #   - "end aliases" with no active aliases: silently clears empty list
        #   - Inside a block comment: skipped by the in_block_comment guard above
        if not line[0:1].isspace() and _END_ALIASES.match(_strip_directive_comment(line)):
            aliases.clear()
            continue

        # --- Posting line ---
        #
        # Posting lines are conventionally written with 2+ leading spaces or a
        # tab, but indentation is not strictly required inside an open block.
        # Any line inside an open transaction block that has not been matched by
        # the blank-line, comment, transaction-header, or directive branches
        # above is treated as a posting.
        #
        # Indented lines (2+ spaces or tab) outside a transaction block still
        # raise ParseError — indentation unambiguously signals "this is a
        # posting", so encountering one with no open block is always an error.
        # Non-indented lines outside a block are silently skipped (directives,
        # stray text, etc.).
        if current_txn is None and (line.startswith("  ") or line.startswith("\t")):
            _err = ParseError("posting found outside a transaction block", lineno)
            if errors_out is None:
                raise _err
            errors_out.append(_err)
            skip_until_blank = True
            continue
        if current_txn is not None:
            try:
                posting = _parse_posting(stripped, lineno, decimal_mark)
            except ParseError as _err:
                if errors_out is None:
                    raise
                errors_out.append(_err)
                current_txn = None
                current_txn_last_lineno = None
                last_posting_in_txn = None
                skip_until_blank = True
                continue
            if aliases:
                posting = Posting(
                    account=_apply_aliases(posting.account, aliases),
                    amount=posting.amount,
                    balance_assertion=posting.balance_assertion,
                    source_line=posting.source_line,
                    inline_comment=posting.inline_comment,
                )
            # Enforce at-most-one elided amount per block
            if posting.amount is None:
                elided = [p for p in current_txn.postings if p.amount is None]
                if elided:
                    _err = ParseError(
                        "a transaction block may have at most one elided amount", lineno
                    )
                    if errors_out is None:
                        raise _err
                    errors_out.append(_err)
                    current_txn = None
                    current_txn_last_lineno = None
                    last_posting_in_txn = None
                    skip_until_blank = True
                    continue
            current_txn.postings.append(posting)
            current_txn_last_lineno = lineno
            last_posting_in_txn = posting
            continue

        # --- Any other line outside a transaction block: silently skip ---

    # Flush final block if file ends without a trailing blank line
    if current_txn is not None:
        end = current_txn_last_lineno or (current_txn.source_line or 1)
        _flush_txn(current_txn, end, all_lines, source_file)
        transactions.append(current_txn)

    return Journal(
        transactions=transactions,
        prices=prices,
        declared_accounts=declared_accounts,
        declared_commodities=declared_commodities,
        declared_payees=declared_payees,
        declared_tags=declared_tags,
    )


def parse_string(
    text: str,
    default_year: int | None = None,
    source_file: str = "(string)",
) -> Journal:
    """Parse a journal from a string and return a Journal object.

    Accepted date formats: YYYY-MM-DD, YYYY/MM/DD, YYYY.MM.DD, and year-omitted
    forms such as M/DD or MM-DD. Leading zeros on month and day are optional.
    When the year is omitted, default_year is used (defaults to the current
    calendar year when None).

    source_file is stored in every Transaction.source_span.file. Defaults to
    "(string)" for direct callers; loader.py passes the resolved absolute path.

    Raises:
        ParseError: if the input is not valid hledger journal syntax.
    """
    if default_year is None:
        default_year = datetime.date.today().year
    return _parse_string_impl(text, default_year, errors_out=None, source_file=source_file)


def parse_string_lenient(
    text: str,
    default_year: int | None = None,
    source_file: str = "(string)",
) -> tuple[Journal, list[ParseError]]:
    """Parse a journal leniently, collecting errors instead of raising.

    Returns a (Journal, list[ParseError]) tuple. The Journal contains all
    transactions that were successfully parsed; malformed transactions are
    discarded. The error list is empty when the input is valid.

    This function never raises. It is intended for editor integrations that
    call it on every text-changed event to provide real-time diagnostics while
    the file is being edited.

    Args:
        text: Raw journal text.
        default_year: Year to use for year-omitted dates. Defaults to the
                      current calendar year when None.

    Returns:
        A (journal, errors) tuple where journal contains all valid transactions
        and errors is a (possibly empty) list of ParseError.
    """
    if default_year is None:
        default_year = datetime.date.today().year
    errors: list[ParseError] = []
    journal = _parse_string_impl(text, default_year, errors_out=errors, source_file=source_file)
    return journal, errors


