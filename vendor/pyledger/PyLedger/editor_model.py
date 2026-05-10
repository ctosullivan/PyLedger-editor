"""In-memory editable document model for PyLedger.

Provides EditorDocument: load a journal file, mutate transactions in memory,
validate individual transactions, and write changes back to disk faithfully.
Intended for use by TUI/editor frontends. Not imported by any core module.
"""

from __future__ import annotations

from pathlib import Path

from PyLedger.checks import CheckError, check_transaction_autobalanced
from PyLedger.models import Journal, SourceSpan, Transaction
from PyLedger.parser import parse_string
from PyLedger.writer import transaction_to_text


class EditorDocument:
    """An in-memory editable representation of a journal file.

    Attributes:
        path:    Resolved absolute path to the journal file.
        journal: Parsed Journal with all transactions (source_span populated).
        lines:   Current file content as a list of strings, one per line,
                 without newline characters.
        dirty:   True when lines differ from the last saved/loaded content.

    V1 limitation: include directives in the file are not processed; the file
    is parsed as-is with parse_string(). Use loader.load_journal() when
    full include support is required.
    """

    path: str
    journal: Journal
    lines: list[str]
    dirty: bool

    def __init__(self, path: str) -> None:
        """Load the journal at path; populate journal and lines."""
        abs_path = str(Path(path).resolve())
        self.path = abs_path
        text = Path(abs_path).read_text(encoding="utf-8")
        self.lines = text.splitlines()
        self.journal = parse_string(text, source_file=abs_path)
        self.dirty = False

    # ------------------------------------------------------------------
    # Span refresh helpers
    # ------------------------------------------------------------------

    def _shift_spans_after(self, after_line: int, delta: int) -> None:
        """Shift source_span of every transaction that starts after after_line."""
        for txn in self.journal.transactions:
            if txn.source_span and txn.source_span.start_line > after_line:
                txn.source_span = SourceSpan(
                    file=txn.source_span.file,
                    start_line=txn.source_span.start_line + delta,
                    end_line=txn.source_span.end_line + delta,
                )

    # ------------------------------------------------------------------
    # Mutation methods
    # ------------------------------------------------------------------

    def add_transaction(self, txn: Transaction) -> None:
        """Insert txn into self.lines in chronological order.

        Inserts after the last transaction whose date <= txn.date. Updates
        self.journal.transactions. Sets dirty=True. txn.source_span is
        assigned after insertion.
        """
        new_lines = transaction_to_text(txn).splitlines()
        n = len(new_lines)

        # Find the last transaction with date <= txn.date (by start_line order)
        sorted_txns = sorted(
            [t for t in self.journal.transactions if t.source_span],
            key=lambda t: (t.date, t.source_span.start_line),  # type: ignore[union-attr]
        )
        insert_after: Transaction | None = None
        for t in sorted_txns:
            if t.date <= txn.date:
                insert_after = t

        if insert_after is None or insert_after.source_span is None:
            # Insert at the very beginning (prepend)
            insert_idx = 0  # 0-based index into self.lines
            self.lines[0:0] = new_lines + [""]
            txn.source_span = SourceSpan(
                file=self.path,
                start_line=1,
                end_line=n,
            )
            self._shift_spans_after(n, n + 1)
        else:
            # Insert after the end of insert_after (insert_idx is 0-based)
            insert_idx = insert_after.source_span.end_line  # end_line is 1-based → index after block
            self.lines[insert_idx:insert_idx] = [""] + new_lines
            txn.source_span = SourceSpan(
                file=self.path,
                start_line=insert_idx + 2,   # +1 for the blank line, +1 for 1-based
                end_line=insert_idx + 1 + n,
            )
            self._shift_spans_after(insert_after.source_span.end_line, n + 1)

        self.journal.transactions.append(txn)
        self.journal.transactions.sort(
            key=lambda t: (t.date, t.source_span.start_line if t.source_span else 0)
        )
        self.dirty = True

    def update_transaction(self, original: Transaction, updated: Transaction) -> None:
        """Replace the lines occupied by original with the serialised form of updated.

        Refreshes all source_span values for transactions whose line numbers
        shifted. Sets dirty=True.
        """
        span = original.source_span
        if span is None:
            raise ValueError("update_transaction: original has no source_span")

        new_lines = transaction_to_text(updated).splitlines()
        old_count = span.end_line - span.start_line + 1
        delta = len(new_lines) - old_count

        # Replace lines in-place (start_line is 1-based → index = start_line - 1)
        self.lines[span.start_line - 1 : span.end_line] = new_lines

        updated.source_span = SourceSpan(
            file=span.file,
            start_line=span.start_line,
            end_line=span.start_line + len(new_lines) - 1,
        )

        # Replace in journal.transactions
        idx = self.journal.transactions.index(original)
        self.journal.transactions[idx] = updated

        # Shift all transactions that come after the modified block
        if delta != 0:
            self._shift_spans_after(span.end_line, delta)

        self.dirty = True

    def delete_transaction(self, txn: Transaction) -> None:
        """Remove the lines occupied by txn and any immediately following blank line.

        Refreshes source_span values. Sets dirty=True.
        """
        span = txn.source_span
        if span is None:
            raise ValueError("delete_transaction: txn has no source_span")

        # end is the 0-based exclusive end index for slicing
        start_idx = span.start_line - 1   # inclusive, 0-based
        end_idx = span.end_line           # exclusive, 0-based (span.end_line is 1-based inclusive)

        # Also consume a trailing blank separator line if present
        if end_idx < len(self.lines) and self.lines[end_idx] == "":
            end_idx += 1

        removed = end_idx - start_idx
        del self.lines[start_idx:end_idx]

        self.journal.transactions.remove(txn)
        self._shift_spans_after(span.start_line, -removed)

        self.dirty = True

    def save(self) -> None:
        """Write self.lines to self.path; set dirty=False."""
        content = "\n".join(self.lines)
        if content and not content.endswith("\n"):
            content += "\n"
        Path(self.path).write_text(content, encoding="utf-8")
        self.dirty = False

    def reload(self) -> None:
        """Re-read self.path from disk and re-parse.

        Replaces self.journal and self.lines. Resets dirty=False.
        """
        text = Path(self.path).read_text(encoding="utf-8")
        self.lines = text.splitlines()
        self.journal = parse_string(text, source_file=self.path)
        self.dirty = False

    def validate_transaction(self, txn: Transaction) -> list[CheckError]:
        """Run the autobalanced check on txn alone.

        Returns a (possibly empty) list of CheckError. Does not raise.
        """
        return check_transaction_autobalanced(txn)
