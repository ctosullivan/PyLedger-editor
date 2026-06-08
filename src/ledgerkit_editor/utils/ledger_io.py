"""Journal file I/O via ledgerkit.

Thin wrappers around ledgerkit's public API so the rest of the editor can
call load/save without directly coupling to ledgerkit import paths.

Key ledgerkit types used here:
  - ledgerkit.load(path)              → Journal  (alias for loader.load_journal)
  - ledgerkit.EditorDocument(path)   → in-memory editable document
  - ledgerkit.journal_to_text(j)     → str
  - ledgerkit.transaction_to_text(t) → str

Always consult the ledgerkit PyPI package source (ledgerkit/models.py, etc.)
before extending this module. Never assume the ledgerkit API — read the source first.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ledgerkit.models import Journal, Transaction

__all__ = [
    "align_posting_amounts",
    "load_journal",
    "save_journal",
    "split_journal_segments",
    "split_preamble",
]

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

# Matches the start of a transaction header: an ISO date (YYYY-MM-DD) at the
# very beginning of a line.
# Purpose: locate where the first transaction begins so all content that
#          precedes it (P directives, account/commodity/payee declarations,
#          standalone comments, blank lines) can be extracted as a preamble
#          block and preserved across sort-and-reserialise cycles.
#
# Group breakdown: none — no capture groups; .search() start position is used.
#
# Edge cases:
#   - "P 2024-01-01 ..." starts with "P ", not a digit → never matches; correctly
#     treated as preamble.
#   - A transaction header with a cleared flag ("2024-01-01 * ...") starts with the
#     date, so it matches correctly.
#   - A date-like string embedded in a description or posting line cannot appear at
#     column 0 in valid hledger format, so false positives are not a concern.
_TXN_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}", re.MULTILINE)


def split_preamble(text: str) -> tuple[str, str]:
    """Split journal text into (preamble, transactions).

    The preamble contains all content before the first transaction header:
    P directives, account/commodity/payee declarations, standalone comments,
    and blank lines. The second element starts at the first line whose first
    ten characters match YYYY-MM-DD.

    Known limitation: directives interleaved *between* transactions are not
    preserved; only the pre-first-transaction block is. This covers the dominant
    real-world pattern (declarations at the top of the file).

    Args:
        text: Raw journal text (from the editor textarea).

    Returns:
        A tuple ``(preamble, body)`` where ``preamble`` may be empty and
        ``body`` starts at the first transaction header line. If no
        transaction is found, returns ``(text, "")``.
    """
    m = _TXN_DATE_RE.search(text)
    if m is None:
        return text, ""
    return text[: m.start()], text[m.start():]


def split_journal_segments(
    text: str,
    transactions: list[Transaction],
) -> tuple[list[str], list[str]]:
    """Split journal text into non-transaction blocks and transaction blocks.

    Uses Transaction.source_span (1-based, inclusive line numbers) to locate
    each transaction precisely, so non-transaction content — P directives,
    account/commodity/payee declarations, standalone comments, blank lines —
    is extracted into separate blocks that survive sort-and-reserialise cycles.

    Returns two parallel structures that together span the whole text:

    - non_txn_blocks: N+1 strings where N = len(transactions).
      non_txn_blocks[0] is the preamble (before the first transaction).
      non_txn_blocks[i] for i > 0 is the content between txn_blocks[i-1]
      and txn_blocks[i] in the original file.
      non_txn_blocks[-1] is trailing content after the last transaction.

    - txn_blocks: N strings, each the verbatim source lines of one transaction,
      in original file order (sorted by source_span.start_line, not by date).

    When the caller sorts transactions by date and reassembles by interleaving
    serialised transaction texts with the original non_txn_blocks in positional
    order, interleaved directives remain between their adjacent transactions.

    Falls back to split_preamble semantics (non-empty preamble block only,
    empty inter/trailing blocks) if any Transaction.source_span is None.

    Args:
        text: Raw journal text from the editor textarea.
        transactions: Parsed Transaction objects, in any order.

    Returns:
        ``(non_txn_blocks, txn_blocks)`` with
        ``len(non_txn_blocks) == len(txn_blocks) + 1``.
    """
    if not transactions:
        return [text], []

    lines = text.splitlines(keepends=True)

    # Build (start_0based, end_0based_exclusive) from each SourceSpan.
    # SourceSpan.start_line and .end_line are 1-based inclusive, so:
    #   0-based start = start_line - 1
    #   0-based exclusive end = end_line  (same numeric value as 1-based inclusive end)
    spans: list[tuple[int, int]] = []
    for txn in transactions:
        span = getattr(txn, "source_span", None)
        if span is None:
            # Fallback: source_span unavailable; preserve preamble only.
            preamble, _ = split_preamble(text)
            n = len(transactions)
            return [preamble] + [""] * n, [""] * n
        spans.append((span.start_line - 1, span.end_line))

    # Sort by file position to iterate in original source order.
    spans.sort(key=lambda s: s[0])

    non_txn_blocks: list[str] = []
    txn_blocks: list[str] = []
    prev_end = 0

    for start, end in spans:
        non_txn_blocks.append("".join(lines[prev_end:start]))
        txn_blocks.append("".join(lines[start:end]))
        prev_end = end

    non_txn_blocks.append("".join(lines[prev_end:]))  # trailing content

    return non_txn_blocks, txn_blocks


def align_posting_amounts(text: str, column: int = 52) -> str:
    """Right-align amount fields in serialised journal text to a fixed column.

    Emacs ledger-mode right-aligns posting amounts so the last character of
    each amount lands at a fixed column (default 52), giving visual consistency
    across the whole file regardless of amount length, rather than the
    per-transaction alignment produced by ledgerkit's journal_to_text().

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

    Delegates to ledgerkit.load() which handles include directives, glob
    expansion, and circular-include detection.

    Args:
        path: Absolute path to the .journal or .ledger file.

    Returns:
        Parsed Journal containing all transactions, prices, and declared
        accounts/commodities/payees.

    Raises:
        FileNotFoundError: if the path does not exist.
        ledgerkit.parser.ParseError: if the file content is malformed.
    """
    import ledgerkit  # noqa: PLC0415 — deferred to avoid startup cost
    return ledgerkit.load(path)


def save_journal(path: Path, journal: "Journal") -> None:
    """Serialise a Journal to the given path.

    Uses ledgerkit.journal_to_text() for serialisation. Note: directives
    (account, commodity, payee, P) are not round-tripped by journal_to_text
    in ledgerkit v0.1.0 — only transactions are serialised.

    Args:
        path:    Absolute path to write the journal file.
        journal: Journal object to serialise.
    """
    import ledgerkit  # noqa: PLC0415 — deferred to avoid startup cost
    text = ledgerkit.journal_to_text(journal)
    path.write_text(text, encoding="utf-8")
