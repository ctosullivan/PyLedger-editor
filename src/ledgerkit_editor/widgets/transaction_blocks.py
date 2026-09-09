"""Transaction block selection, duplication, and cleared-toggle for JournalEditor.

Split out of transaction_table.py (Phase 2 of the next-release plan — see
planning/next-release-phase-plan.md) once that module passed the Module Size
Rule threshold. Covers Ctrl+T (select/extend block), Ctrl+G (duplicate to
end), and Ctrl+R (single/bulk cleared toggle).
"""

from __future__ import annotations

from datetime import date as _date

from ledgerkit_editor.highlighting.highlighter import LineKind
from ledgerkit_editor.widgets.date_shift import _TXN_HEADER_RE
from ledgerkit_editor.widgets.ledger_textarea import LedgerTextArea
from textual.widgets import TextArea

__all__ = ["TransactionBlocksMixin", "_cycle_flag_in_header", "_find_transaction_block"]


def _cycle_flag_in_header(line: str) -> str:
    """Return line with the cleared/pending flag cycled: none → ! → * → none.

    Returns the original line unchanged if it does not match the header format.
    """
    m = _TXN_HEADER_RE.match(line)
    if not m:
        return line
    date_str, current_flag, rest = m.group(1), m.group(2), m.group(3)
    if current_flag is None:
        new_flag: str | None = "!"
    elif current_flag == "!":
        new_flag = "*"
    else:
        new_flag = None

    parts = [date_str]
    if new_flag:
        parts.append(new_flag)
    if rest:
        parts.append(rest)
    return " ".join(parts)


# Purpose: locate the start and end rows of the hledger transaction block
#   containing the given row. A block begins at the first non-indented,
#   non-blank line at or above `row` (the header) and ends at the last
#   consecutive indented line below the header (the postings).
# Returns: (start_row, end_row) — both are valid indices into `lines`.
# Edge cases: blank lines between postings are treated as block terminators;
#   a row with no header above it returns (0, end_row); an empty list
#   returns (0, 0); `row` is clamped to [0, len(lines)-1].
def _find_transaction_block(lines: list[str], row: int) -> tuple[int, int]:
    """Return (start_row, end_row) of the transaction block containing row."""
    if not lines:
        return (0, 0)
    row = max(0, min(row, len(lines) - 1))
    start = row
    while start > 0 and (not lines[start] or lines[start][0].isspace()):
        start -= 1
    end = start
    total = len(lines)
    while end + 1 < total:
        next_line = lines[end + 1]
        if not next_line or not next_line[0].isspace():
            break
        end += 1
    return (start, end)


class TransactionBlocksMixin:
    """JournalEditor mixin providing Ctrl+T / Ctrl+G / Ctrl+R block actions.

    Expects "#journal_textarea" (a LedgerTextArea) to be present, exactly as
    DateShiftMixin does. Owns no instance state of its own.
    """

    def action_toggle_cleared(self) -> None:
        """Cycle or bulk-toggle the cleared flag on transaction header(s).

        Single-transaction cycle: none → '!' → '*' → none.
        Multi-transaction bulk-toggle: all cleared → all uncleared; otherwise → all '*'.
        """
        textarea = self.query_one("#journal_textarea", TextArea)
        sel = textarea.selection
        start_row = min(sel.start[0], sel.end[0])
        end_row = max(sel.start[0], sel.end[0])
        if end_row > start_row:
            self._bulk_toggle_cleared(textarea, start_row, end_row)
        else:
            row, _ = textarea.cursor_location
            lines = textarea.text.splitlines()
            if row >= len(lines):
                return
            line = lines[row]
            if not line or line[0].isspace():
                return
            new_line = _cycle_flag_in_header(line)
            if new_line != line:
                textarea.replace(new_line, (row, 0), (row, len(line)))

    def _bulk_toggle_cleared(
        self, textarea: TextArea, start_row: int, end_row: int
    ) -> None:
        """Toggle cleared flag on all transaction headers within [start_row, end_row].

        If every header in the range is already cleared, remove all flags.
        Otherwise set all headers to '*' (cleared).
        Changes are applied in reverse row order so earlier row indices stay valid.
        """
        lines = textarea.text.splitlines()
        header_rows = [
            i for i in range(start_row, end_row + 1)
            if i < len(lines)
            and lines[i]
            and not lines[i][0].isspace()
            and _TXN_HEADER_RE.match(lines[i])
        ]
        if not header_rows:
            return
        all_cleared = all(
            _TXN_HEADER_RE.match(lines[r]).group(2) == "*"  # type: ignore[union-attr]
            for r in header_rows
        )
        new_flag: str | None = None if all_cleared else "*"
        from ledgerkit_editor.utils.atomic_edit import atomic_edit  # noqa: PLC0415
        with atomic_edit(textarea):
            for r in reversed(header_rows):
                m = _TXN_HEADER_RE.match(lines[r])
                if not m:
                    continue
                parts = [m.group(1)]
                if new_flag:
                    parts.append(new_flag)
                if m.group(3):
                    parts.append(m.group(3))
                new_line = " ".join(parts)
                textarea.replace(new_line, (r, 0), (r, len(lines[r])))

    def action_select_transaction_block(self) -> None:
        """Select the transaction block at the cursor; extend on each repeated press.

        First press: selects the block containing the cursor.
        Each subsequent press: if the current selection ends exactly at a
        transaction block boundary, extends to include the next block.
        """
        from textual.document._document import Selection  # noqa: PLC0415

        textarea = self.query_one("#journal_textarea", LedgerTextArea)
        lines = textarea.text.splitlines()
        if not lines:
            return

        sel = textarea.selection
        sel_start_row = min(sel.start[0], sel.end[0])
        sel_end_row = max(sel.start[0], sel.end[0])
        sel_end_col = (
            sel.start[1] if sel.start[0] > sel.end[0] else sel.end[1]
        )

        if sel_start_row < sel_end_row and sel_end_row < len(lines):
            expected_end_col = len(lines[sel_end_row])
            if sel_end_col == expected_end_col:
                _, confirmed_block_end = _find_transaction_block(lines, sel_end_row)
                if confirmed_block_end == sel_end_row:
                    line_infos = textarea._highlighter._line_infos
                    for i in range(sel_end_row + 1, len(line_infos)):
                        if i < len(lines) and line_infos[i].kind == LineKind.XACT_HEADER:
                            _, next_block_end = _find_transaction_block(lines, i)
                            next_end_col = len(lines[next_block_end]) if next_block_end < len(lines) else 0
                            textarea.selection = Selection(
                                (sel_start_row, 0), (next_block_end, next_end_col)
                            )
                            return

        row, _ = textarea.cursor_location
        start_row, end_row = _find_transaction_block(lines, row)
        end_col = len(lines[end_row]) if end_row < len(lines) else 0
        textarea.selection = Selection((start_row, 0), (end_row, end_col))

    def action_autofill(self) -> None:
        """Duplicate current or all selected transactions to end of file (Ctrl+G).

        Single cursor: duplicates the one transaction block at the cursor.
        Multi-line selection (e.g. from repeated Ctrl+T): duplicates every
        transaction block whose header falls within the selection range.
        Each duplicate gets today's date on its header line.
        """
        textarea = self.query_one("#journal_textarea", LedgerTextArea)
        sel = textarea.selection
        lines = textarea.text.splitlines()
        if not lines:
            return
        today = _date.today().isoformat()

        sel_start = min(sel.start[0], sel.end[0])
        sel_end = max(sel.start[0], sel.end[0])

        if sel_start < sel_end:
            line_infos = textarea._highlighter._line_infos
            seen: set[int] = set()
            blocks: list[tuple[int, int]] = []
            for r in range(sel_start, min(sel_end + 1, len(line_infos))):
                if line_infos[r].kind == LineKind.XACT_HEADER and r not in seen:
                    start_r, end_r = _find_transaction_block(lines, r)
                    for br in range(start_r, end_r + 1):
                        seen.add(br)
                    blocks.append((start_r, end_r))
            if not blocks:
                row, _ = textarea.cursor_location
                blocks = [_find_transaction_block(lines, row)]
        else:
            row, _ = textarea.cursor_location
            blocks = [_find_transaction_block(lines, row)]

        new_block_texts: list[str] = []
        for start_r, end_r in blocks:
            block_lines = list(lines[start_r : end_r + 1])
            m = _TXN_HEADER_RE.match(block_lines[0])
            if m:
                block_lines[0] = today + block_lines[0][len(m.group(1)):]
            new_block_texts.append("\n".join(block_lines))

        appended = "\n\n".join(new_block_texts)
        current_text = textarea.text.rstrip("\n")
        new_text = current_text + "\n\n" + appended + "\n"

        # Use replace() instead of load_text() so the operation is recorded in the
        # undo stack.  load_text() calls history.clear(), destroying prior undo
        # history.  A single full-document replace() creates one undoable entry.
        raw = textarea.text
        parts = raw.split("\n")
        doc_end = (len(parts) - 1, len(parts[-1]))
        textarea.replace(new_text, (0, 0), doc_end)

        first_new_start = len(current_text.splitlines()) + 1  # +1 for blank separator
        textarea.move_cursor((first_new_start, 0))
