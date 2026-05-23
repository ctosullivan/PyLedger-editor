"""Journal file I/O via PyLedger.

Thin wrappers around PyLedger's public API so the rest of the editor can
call load/save without directly coupling to PyLedger import paths.

Key PyLedger types used here:
  - PyLedger.load(path)              → Journal  (alias for loader.load_journal)
  - PyLedger.EditorDocument(path)   → in-memory editable document
  - PyLedger.journal_to_text(j)     → str
  - PyLedger.transaction_to_text(t) → str

Always consult vendor/pyledger/dev-docs/api-spec.md before extending this
module. Never assume the PyLedger API — read the spec first.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from PyLedger.models import Journal

__all__ = ["align_posting_amounts", "load_journal", "save_journal"]

# Matches an hledger posting line that carries an explicit amount.
# Purpose: identify posting lines to re-space after journal_to_text() formats them,
#          so that the last character of each amount lands at a fixed column across
#          the whole file (right-aligned, emacs ledger-mode style).
#
# Group 1 (indent):   exactly 4 leading spaces — the hledger posting indent.
# Group 2 (account):  account name, which may contain single spaces (hledger allows
#                     account names like "Assets:Bank:AIB Cormac").
#                     [^\s;] guard requires the account not to start with a space or
#                     ';' (the latter skips comment-only lines like "    ; note").
#                     \S*             — rest of the first word (zero or more non-space).
#                     (?:[ ]\S+)*     — zero or more (exactly-one-space + non-space-word)
#                     groups, handling multi-word account names.  The *greedy* outer
#                     quantifier consumes as many single-space-separated words as
#                     possible; it stops as soon as the separator group ( {2,}) would
#                     fail, which happens at the first two-or-more-space run.
# Group 3 (sep):      2 or more spaces — the mandatory separator between account and
#                     amount in hledger format.  Single spaces inside an account name
#                     are consumed by Group 2; a double-space run always marks the
#                     start of this separator.  journal_to_text() may rjust() amounts
#                     with a leading space; ( {2,}) consumes it greedily so Group 4
#                     always starts at the first non-space character of the amount.
# Group 4 (amount):   everything after the separator — amount + any inline comment.
#
# Formula applied after matching:
#   needed = max(2, (column - len(amount)) - len(indent) - len(account))
#
# Edge cases (inline comments are peeled from the line before this regex runs):
#   "    ; posting note"              — skipped; [^\s;] blocks ';'.
#   "    expenses:food"               — skipped; no " {2,}" separator + non-space.
#   "    Assets:Bank:AIB Cormac  £5"  — matched; multi-word account captured in full.
#   "    assets:bank $-100.00"        — NOT matched (only 1 space before amount —
#                                       invalid hledger, but safe to skip).
#   "    expenses:food  ; note"       — comment peeled to comment_tail before match;
#                                       body "    expenses:food" has no separator →
#                                       regex skips; line output unchanged.
#   "    exp:food  50 EUR  ; note"    — comment peeled; body "    exp:food  50 EUR"
#                                       matches; amount = "50 EUR"; comment reattached.
_POSTING_AMOUNT_RE = re.compile(r"^(    )([^\s;]\S*(?:[ ]\S+)*)( {2,})(\S.*)$")


def align_posting_amounts(text: str, column: int = 52) -> str:
    """Right-align amount fields in serialised journal text to a fixed column.

    Emacs ledger-mode right-aligns posting amounts so the last character of
    each amount lands at a fixed column (default 52), giving visual consistency
    across the whole file regardless of amount length, rather than the
    per-transaction alignment produced by PyLedger's journal_to_text().

    Lines that are not posting lines with amounts (transaction headers, comment
    lines, blank lines, balance-completing postings) are passed through
    unchanged.

    Args:
        text:   Full journal text as produced by journal_to_text().
        column: Target column (1-indexed) at which the last character of each
                amount field must land.

    Returns:
        Journal text with posting amounts re-aligned so their last character
        is at ``column``.
    """
    result: list[str] = []
    for line in text.splitlines():
        # Peel off any inline comment ("  ; ...") before regex matching so the
        # greedy account-name group cannot consume suffix-currency amount words
        # (e.g. "50.00 EUR") when a comment follows.  Only applied to potential
        # posting lines: 4-space indent + account starting with non-space/non-";".
        comment_tail = ""
        line_body = line
        if len(line) > 4 and line[:4] == "    " and line[4] not in (";", " "):
            idx = line.find("  ;", 4)
            if idx > 4:
                line_body = line[:idx]
                comment_tail = line[idx:]

        m = _POSTING_AMOUNT_RE.match(line_body)
        if m:
            indent, account, _sep, amount = m.group(1), m.group(2), m.group(3), m.group(4)
            needed = max(2, (column - len(amount)) - len(indent) - len(account))
            line = indent + account + " " * needed + amount + comment_tail
        result.append(line)
    return "\n".join(result) + ("\n" if text.endswith("\n") else "")


def load_journal(path: Path) -> "Journal":
    """Load a journal file and return a parsed Journal object.

    Delegates to PyLedger.load() which handles include directives, glob
    expansion, and circular-include detection.

    Args:
        path: Absolute path to the .journal or .ledger file.

    Returns:
        Parsed Journal containing all transactions, prices, and declared
        accounts/commodities/payees.

    Raises:
        FileNotFoundError: if the path does not exist.
        PyLedger.parser.ParseError: if the file content is malformed.
    """
    import PyLedger  # noqa: PLC0415 — deferred to avoid startup cost
    return PyLedger.load(path)


def save_journal(path: Path, journal: "Journal") -> None:
    """Serialise a Journal to the given path.

    Uses PyLedger.journal_to_text() for serialisation. Note: directives
    (account, commodity, payee, P) are not round-tripped by journal_to_text
    in PyLedger v0.5.0 — only transactions are serialised.

    Args:
        path:    Absolute path to write the journal file.
        journal: Journal object to serialise.
    """
    import PyLedger  # noqa: PLC0415 — deferred to avoid startup cost
    text = PyLedger.journal_to_text(journal)
    path.write_text(text, encoding="utf-8")
