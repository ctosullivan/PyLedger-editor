"""Main editing surface: a full-text editor for hledger journal files.

Shows raw journal text in a LedgerTextArea. Ctrl+L cycles the editor view
between All, Cleared, and Unreconciled transactions without leaving the editor.
Search bar (Ctrl+F) is implemented in SearchBar (search_bar.py). View filter bar
is implemented in ViewFilterBar (view_filter_bar.py).
"""

from __future__ import annotations

import calendar
import re
import time as _time
from datetime import date as _date
from datetime import timedelta
from pathlib import Path

from textual.app import ComposeResult
from textual.binding import Binding
from textual.message import Message
from textual.widget import Widget
from textual.widgets import TextArea

from ledgerkit_editor.highlighting.highlighter import LineKind
from ledgerkit_editor.widgets.ledger_textarea import LedgerTextArea
from ledgerkit_editor.widgets.view_filter_bar import ViewFilterBar

__all__ = ["JournalEditor"]

# Purpose: parse an hledger transaction header line to extract and cycle the
#   status flag while preserving the date, code, description, and comments.
# Group breakdown:
#   group 1 — date segment (YYYY-MM-DD or YYYY/MM/DD)
#   group 2 — status flag (* or !) — absent (None) when the transaction is uncleared
#   group 3 — remainder: optional code (INV-42), description, inline comment
# Edge cases: date-only lines match with empty group 3; posting lines (leading
#   whitespace) must never be passed here — the caller is responsible for that guard.
_TXN_HEADER_RE = re.compile(
    r"^(\d{4}[-/]\d{2}[-/]\d{2})\s*(\*|!)?\s*(.*)"
)

# Purpose: split an hledger posting line at the account/amount boundary.
#   hledger requires at least two spaces (or a tab) between the account name
#   and the amount so that account names with single spaces are unambiguous.
# Edge cases: elided postings (no amount) produce a single-element split,
#   returning the full stripped line as the account name. Caller must strip
#   the leading indent before splitting.
_POSTING_SPLIT_RE = re.compile(r"\s{2,}|\t")


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


def _extract_account_from_line(line: str) -> str | None:
    """Return the account name from an hledger posting line, or None.

    Returns None for blank lines and non-posting lines (no leading whitespace).
    """
    if not line or not line[0].isspace():
        return None
    stripped = line.lstrip()
    if not stripped:
        return None
    parts = _POSTING_SPLIT_RE.split(stripped, maxsplit=1)
    account = parts[0].strip()
    return account if account else None


def _account_at_cursor(textarea: TextArea) -> str | None:
    """Return the account name at the TextArea's current cursor row, or None."""
    row, _ = textarea.cursor_location
    lines = textarea.text.splitlines()
    if row >= len(lines):
        return None
    return _extract_account_from_line(lines[row])


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


def _date_subfield_at_col(col: int) -> str | None:
    """Return 'year', 'month', or 'day' for a cursor column within a 10-char date.

    A date like 2024-01-15 occupies columns 0–9. Separators (col 4, col 7) are
    assigned to the field on their right: col 4 → month, col 7 → day.
    Returns None when col is outside the date (col >= 10).
    """
    if col < 4:
        return "year"
    if col < 7:
        return "month"
    if col < 10:
        return "day"
    return None


# Purpose: parse a 10-character hledger date string of the form YYYY<sep>MM<sep>DD,
#   where <sep> is any of '-', '/', or '.', into year/month/day integers.
# Group breakdown:
#   group 1 — four-digit year (chars 0–3)
#   char  4 — separator (captured directly via date_str[4])
#   group 2 — two-digit month (chars 5–6)
#   group 3 — two-digit day (chars 8–9)
# Edge cases: the caller guarantees date_str matches _TXN_HEADER_RE group 1, so
#   the format is always exactly 10 chars; no need to handle missing leading zeros.
_DATE_PARSE_RE = re.compile(r"^(\d{4}).(\d{2}).(\d{2})$")


def _shift_date_str(date_str: str, subfield: str, delta: int) -> str:
    """Return date_str with the given sub-field shifted by delta, separator preserved.

    Month-end overflow is clamped: Jan 31 + 1 month → Feb 28/29. Year shift
    clamps Feb 29 on a leap year to Feb 28 on a non-leap year.
    """
    m = _DATE_PARSE_RE.match(date_str)
    if not m:
        return date_str
    sep = date_str[4]
    y, mo, d = int(m.group(1)), int(m.group(2)), int(m.group(3))

    if subfield == "day":
        new = _date(y, mo, d) + timedelta(days=delta)
        return f"{new.year:04d}{sep}{new.month:02d}{sep}{new.day:02d}"

    if subfield == "month":
        total = (y * 12 + mo - 1) + delta
        new_y, new_m0 = divmod(total, 12)
        new_mo = new_m0 + 1
        max_d = calendar.monthrange(new_y, new_mo)[1]
        return f"{new_y:04d}{sep}{new_mo:02d}{sep}{min(d, max_d):02d}"

    # subfield == "year"
    new_y = y + delta
    max_d = calendar.monthrange(new_y, mo)[1]
    return f"{new_y:04d}{sep}{mo:02d}{sep}{min(d, max_d):02d}"


class JournalEditor(Widget):
    """Full-text editor for hledger journal files.

    Loads the raw journal file into a LedgerTextArea. Ctrl+S validates, sorts
    by date, and writes back to disk. Ctrl+F opens the incremental search bar.
    Ctrl+L cycles the view filter (All / Cleared / Unreconciled).

    Args:
        journal_path: Absolute path to the journal file being edited.
    """

    BINDINGS = [
        Binding("ctrl+s", "save", "Save", key_display="Ctrl+S"),
        Binding("ctrl+r", "toggle_cleared", "Toggle cleared", key_display="Ctrl+R"),
        Binding("ctrl+g", "autofill", "Duplicate to end", key_display="Ctrl+G"),
        Binding("ctrl+d", "insert_today", "Insert date",
                key_display="Ctrl+D", priority=True),
        Binding("escape", "blur_editor", "Unfocus", show=False),
        Binding("ctrl+t", "select_transaction_block", "Select transaction",
                show=False, priority=True),
        Binding("shift+pageup", "prev_transaction", "Prev transaction",
                show=False, priority=True),
        Binding("shift+pagedown", "next_transaction", "Next transaction",
                show=False, priority=True),
        Binding("ctrl+home", "cursor_to_start", "Start of file",
                show=False, priority=True),
        Binding("ctrl+end", "cursor_to_end", "End of file",
                show=False, priority=True),
        Binding("ctrl+a", "select_all", "Select all",
                show=False, priority=True),
        # Search — Ctrl+F: open bar if closed, else next match (priority=True overrides
        # TextArea's ctrl+f → delete_word_right). Ctrl+Shift+F: prev match.
        # Ctrl+R: prev match when search bar visible, else toggle-cleared (see action_toggle_cleared).
        Binding("ctrl+f", "open_search", "Search",
                key_display="Ctrl+F", priority=True),
        # View filter — cycle All / Cleared / Unreconciled
        Binding("ctrl+l", "cycle_view_filter", "Filter cleared",
                key_display="Ctrl+L", show=True),
        # Undo/redo — priority=True so JournalEditor intercepts before LedgerTextArea
        # routes these to the native TextArea undo stack.  action_undo / action_redo
        # consult CommandHistory first, then fall through to textarea.action_undo/redo.
        Binding("ctrl+z", "undo", "Undo", show=False, priority=True),
        Binding("ctrl+y", "redo", "Redo", show=False, priority=True),
        # Date shifting — intercept Shift+Up/Down before TextArea's selection handler.
        # Falls through to selection when cursor is not on a date field.
        Binding("shift+up", "date_shift_up", "Date up", show=False, priority=True),
        Binding("shift+down", "date_shift_down", "Date down", show=False, priority=True),
    ]

    DEFAULT_CSS = """
    JournalEditor {
        layout: vertical;
    }
    JournalEditor > LedgerTextArea {
        height: 1fr;
    }
    """

    # ------------------------------------------------------------------
    # Message classes
    # ------------------------------------------------------------------

    class SaveCompleted(Message):
        """Posted after a successful Ctrl+S save."""

    class FileModifiedChanged(Message):
        """Posted when the modified state of the editor changes.

        Carries modified=True when the text differs from the last saved state,
        modified=False immediately after a Ctrl+S save.
        """

        def __init__(self, modified: bool) -> None:
            super().__init__()
            self.modified = modified

    # ------------------------------------------------------------------
    # Initialisation
    # ------------------------------------------------------------------

    def __init__(self, journal_path: Path, start_line: int | None = None) -> None:
        """Initialise with the resolved absolute journal file path.

        Args:
            journal_path: Absolute path to the .journal or .ledger file to edit.
            start_line: 1-indexed line to place the cursor on after the file loads.
        """
        from ledgerkit_editor.commands import CommandHistory  # noqa: PLC0415
        super().__init__()
        self.journal_path = journal_path
        self._start_line = start_line
        self._seek_window_end: float = 0.0  # monotonic deadline for resize-triggered re-seek
        self._current_account: str | None = None
        self._last_saved_text: str = ""
        self._command_history: CommandHistory = CommandHistory()
        # View filter state
        self._view_filter_mode: int = 0          # 0=All, 1=Cleared, 2=Unreconciled
        self._filter_journal: object | None = None
        self._filter_visible_indices: list[int] = []
        # Non-transaction blocks (directives, comments, blank-line separators)
        # captured when entering a filter so they survive the mode-0 restore.
        self._filter_non_txn_blocks: list[str] = []
        # (commodity styles are now computed per-save from the current text)

    def compose(self) -> ComposeResult:
        """Render ViewFilterBar, LedgerTextArea, and hidden SearchBar."""
        from ledgerkit_editor.widgets.search_bar import SearchBar  # noqa: PLC0415

        yield ViewFilterBar()
        yield LedgerTextArea(id="journal_textarea", show_line_numbers=True)
        yield SearchBar(id="search-bar")

    def on_mount(self) -> None:
        """Load the raw journal text into the TextArea and focus it."""
        text = Path(self.journal_path).read_text(encoding="utf-8")
        textarea = self.query_one("#journal_textarea", TextArea)
        textarea.load_text(text)
        self._last_saved_text = text
        textarea.focus()
        # Defer the cursor seek: move_cursor here would set the document
        # position correctly but scroll_cursor_visible is a no-op before the
        # first layout pass (widget size is 0). call_after_refresh ensures the
        # layout has run before we try to scroll the viewport.
        if self._start_line is not None:
            # Open a 3-second window so on_resize can re-seek if a Windows
            # console resize event (from hledger-ui handoff) fires after the
            # initial call_after_refresh and resets the scroll position.
            self._seek_window_end = _time.monotonic() + 3.0
            self.call_after_refresh(self._seek_to_start_line)

    def _seek_to_start_line(self) -> None:
        """Move cursor and scroll viewport to the requested start line."""
        textarea = self.query_one("#journal_textarea", TextArea)
        lines = textarea.text.splitlines()
        row = min(max(0, self._start_line - 1), max(0, len(lines) - 1))  # type: ignore[operator]
        textarea.move_cursor((row, 0))

    def on_resize(self, event: object) -> None:
        """Re-seek on resize within the startup window.

        When pyledger-editor is spawned by hledger-ui, Windows emits a console
        resize event as control of the terminal is handed over. That resize can
        reset the TextArea scroll position after the initial call_after_refresh
        seek. Re-scheduling the seek here (only while inside the startup window)
        restores the correct position after the resize re-render completes.
        """
        if self._start_line is not None and _time.monotonic() < self._seek_window_end:
            self.call_after_refresh(self._seek_to_start_line)

    # ------------------------------------------------------------------
    # Cursor tracking
    # ------------------------------------------------------------------

    def on_text_area_selection_changed(self, event: TextArea.SelectionChanged) -> None:
        """Track the account name at the cursor as it moves."""
        self._current_account = _account_at_cursor(event.text_area)

    def on_text_area_changed(self, event: TextArea.Changed) -> None:
        """Post FileModifiedChanged whenever the text content changes."""
        self._update_modified_indicator()

    def _update_modified_indicator(self) -> None:
        """Post FileModifiedChanged with the current modified state."""
        textarea = self.query_one("#journal_textarea", TextArea)
        modified = textarea.text != self._last_saved_text
        self.post_message(self.FileModifiedChanged(modified=modified))

    # ------------------------------------------------------------------
    # Key actions — file operations
    # ------------------------------------------------------------------

    # ------------------------------------------------------------------
    # Undo / redo — two-layer stack
    # ------------------------------------------------------------------

    def action_undo(self) -> None:
        """Undo the most recent operation.

        Consults CommandHistory first (Layer 2 — operations that affect both
        text and in-memory model state).  Falls through to the child
        LedgerTextArea's native undo (Layer 1 — EditHistory) when
        CommandHistory has no entries.
        """
        if self._command_history.can_undo:
            cmd = self._command_history.undo()
            if cmd:
                self.notify(f"Undid: {cmd.description}", timeout=2)
        else:
            textarea = self.query_one("#journal_textarea", TextArea)
            textarea.action_undo()

    def action_redo(self) -> None:
        """Redo the most recently undone operation."""
        if self._command_history.can_redo:
            cmd = self._command_history.redo()
            if cmd:
                self.notify(f"Redid: {cmd.description}", timeout=2)
        else:
            textarea = self.query_one("#journal_textarea", TextArea)
            textarea.action_redo()

    def action_blur_editor(self) -> None:
        """Escape: dismiss search bar if open, else unfocus."""
        from ledgerkit_editor.widgets.search_bar import SearchBar  # noqa: PLC0415

        search_bar = self.query_one("#search-bar", SearchBar)
        if search_bar.display:
            search_bar.dismiss()
            return
        self.app.set_focus(None)

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

    def action_save(self) -> None:
        """Validate, sort by date, and write the journal to disk.

        When a view filter is active the full (unfiltered) journal is saved:
        edits are merged back from the visible slice before writing.
        Notifications are shown for parse and check errors but do not block the
        write. The cursor row is restored after content is replaced.
        """
        import ledgerkit  # noqa: PLC0415

        # Merge filtered edits into full journal before saving.
        if self._view_filter_mode != 0:
            ta = self.query_one("#journal_textarea", LedgerTextArea)
            self._merge_filtered_edits(ta)
            self._view_filter_mode = 0
            self._apply_view_filter(ta)

        textarea = self.query_one("#journal_textarea", TextArea)
        text = textarea.text
        journal, parse_errors = ledgerkit.parse_string_lenient(text)

        for err in parse_errors:
            self.app.notify(str(err), severity="warning")

        from ledgerkit_editor.utils.ledger_io import align_posting_amounts, split_journal_segments  # noqa: PLC0415
        from ledgerkit_editor.utils.commodity_format import apply_commodity_styles, extract_commodity_styles  # noqa: PLC0415
        # Extract non-transaction blocks (directives, comments, blank-line separators)
        # before sorting so they can be woven back in at their original positions.
        non_txn_blocks, _ = split_journal_segments(text, journal.transactions)

        # Infer commodity styles from the current text so that: (a) edits that
        # add or change group separators are picked up immediately, and (b) the
        # "prefer richest format" pass in extract_commodity_styles upgrades any
        # commodity whose first-seen amount has no group separator.
        commodity_styles = extract_commodity_styles(journal)

        journal.transactions.sort(key=lambda t: t.date)

        # Serialise each sorted transaction, then interleave with the preserved
        # non-transaction blocks: preamble + txn[0] + sep[1] + txn[1] + ... + trailer.
        sorted_txn_texts = [ledgerkit.transaction_to_text(t) for t in journal.transactions]
        parts = [non_txn_blocks[0]]
        for i, txn_text in enumerate(sorted_txn_texts):
            parts.append(txn_text)
            parts.append(non_txn_blocks[i + 1])
        # Apply commodity formatting first, then re-align columns so that
        # reformatted amounts (potentially wider or narrower) are spaced correctly.
        sorted_text = apply_commodity_styles("".join(parts), commodity_styles)
        sorted_text = align_posting_amounts(sorted_text)

        saved_loc = textarea.cursor_location
        textarea.load_text(sorted_text)

        lines = sorted_text.splitlines()
        max_row = max(0, len(lines) - 1)
        textarea.move_cursor((min(saved_loc[0], max_row), saved_loc[1]))

        Path(self.journal_path).write_text(sorted_text, encoding="utf-8")

        for err in ledgerkit.checks.run_basic_checks(journal):
            self.app.notify(err.message, severity="warning")

        self._last_saved_text = sorted_text
        self.post_message(self.SaveCompleted())
        self.post_message(self.FileModifiedChanged(modified=False))
        self.app.notify("Saved", severity="information")

    # ------------------------------------------------------------------
    # Key actions — search
    # ------------------------------------------------------------------

    def action_open_search(self) -> None:
        """Open search bar (Ctrl+F), or advance to next match if bar already open."""
        from ledgerkit_editor.widgets.search_bar import SearchBar  # noqa: PLC0415

        bar = self.query_one("#search-bar", SearchBar)
        if bar.display:
            bar.advance(direction=1)
        else:
            bar.open_bar()

    # ------------------------------------------------------------------
    # Key actions — view filter
    # ------------------------------------------------------------------

    def action_cycle_view_filter(self) -> None:
        """Cycle editor view: All → Cleared → Unreconciled → All (Ctrl+L)."""
        import ledgerkit  # noqa: PLC0415

        textarea = self.query_one("#journal_textarea", LedgerTextArea)

        if self._view_filter_mode == 0:
            # Entering a filtered view — snapshot the full journal and the
            # non-transaction blocks so directives/comments survive mode-0 restore.
            self._filter_journal, _ = ledgerkit.parse_string_lenient(textarea.text)
            from ledgerkit_editor.utils.ledger_io import split_journal_segments  # noqa: PLC0415
            self._filter_non_txn_blocks, _ = split_journal_segments(
                textarea.text, self._filter_journal.transactions  # type: ignore[union-attr]
            )
        else:
            # Already filtered — merge edits before switching.
            self._merge_filtered_edits(textarea)

        self._view_filter_mode = (self._view_filter_mode + 1) % 3
        self._apply_view_filter(textarea)

    def _apply_view_filter(self, textarea: LedgerTextArea) -> None:
        """Rebuild textarea content from _filter_journal for the current mode."""
        import ledgerkit  # noqa: PLC0415

        journal = self._filter_journal

        if self._view_filter_mode == 0:
            # Restore full journal, preserving directives/comments/blank-line
            # separators captured in _filter_non_txn_blocks at filter entry.
            if journal is not None:
                blocks = self._filter_non_txn_blocks
                txns = journal.transactions
                if blocks and len(blocks) == len(txns) + 1:
                    # Exact match: weave non-txn blocks between transactions.
                    txn_texts = [ledgerkit.transaction_to_text(t) for t in txns]
                    parts = [blocks[0]]
                    for i, txn_text in enumerate(txn_texts):
                        parts.append(txn_text)
                        parts.append(blocks[i + 1])
                    full_text = "".join(parts)
                elif blocks:
                    # Count mismatch (txns added/deleted in filtered view):
                    # preserve preamble, fall back to journal_to_text for body.
                    full_text = blocks[0] + ledgerkit.journal_to_text(journal)
                else:
                    full_text = ledgerkit.journal_to_text(journal)
            else:
                full_text = textarea.text
            self._filter_journal = None
            self._filter_non_txn_blocks = []
            self._filter_visible_indices = []
            textarea.load_text(full_text)
        else:
            if journal is None:
                return
            want_cleared = self._view_filter_mode == 1
            visible: list[tuple[int, object]] = [
                (i, tx) for i, tx in enumerate(journal.transactions)
                if (tx.cleared if want_cleared else not tx.cleared)  # type: ignore[union-attr]
            ]
            self._filter_visible_indices = [i for i, _ in visible]
            parts = [ledgerkit.transaction_to_text(tx) for _, tx in visible]
            filtered_text = "\n".join(parts)
            textarea.load_text(filtered_text)

        self._update_filter_bar()

    def _merge_filtered_edits(self, textarea: LedgerTextArea) -> None:
        """Merge textarea edits back into _filter_journal before a filter change."""
        import ledgerkit  # noqa: PLC0415

        if self._filter_journal is None:
            return
        visible_journal, _ = ledgerkit.parse_string_lenient(textarea.text)
        visible_txs = visible_journal.transactions
        all_txs: list = list(self._filter_journal.transactions)  # type: ignore[union-attr]

        # Replace tracked slots with edited versions.
        for slot, idx in enumerate(self._filter_visible_indices):
            if slot < len(visible_txs):
                all_txs[idx] = visible_txs[slot]

        # Append any newly added transactions beyond the original visible count.
        new_txs = visible_txs[len(self._filter_visible_indices):]
        all_txs.extend(new_txs)

        # Remove deleted transactions (visible slots with no counterpart in edited view).
        deleted = self._filter_visible_indices[len(visible_txs):]
        for idx in sorted(deleted, reverse=True):
            if idx < len(all_txs):
                del all_txs[idx]

        all_txs.sort(key=lambda tx: tx.date)  # type: ignore[union-attr]
        self._filter_journal.transactions = all_txs  # type: ignore[union-attr]

    def _update_filter_bar(self) -> None:
        """Refresh the ViewFilterBar label after a filter change."""
        try:
            self.query_one(ViewFilterBar).set_mode(self._view_filter_mode)
        except Exception:  # noqa: BLE001
            pass

    # ------------------------------------------------------------------
    # Key actions — navigation and editing
    # ------------------------------------------------------------------

    def action_select_all(self) -> None:
        """Select all text in the editor (Ctrl+A)."""
        from textual.document._document import Selection  # noqa: PLC0415

        textarea = self.query_one("#journal_textarea", TextArea)
        lines = textarea.text.splitlines()
        if not lines:
            return
        last_row = len(lines) - 1
        textarea.selection = Selection((0, 0), (last_row, len(lines[last_row])))

    def action_autofill(self) -> None:
        """Duplicate current or all selected transactions to end of file (Ctrl+G).

        Single cursor: duplicates the one transaction block at the cursor.
        Multi-line selection (e.g. from repeated Ctrl+T): duplicates every
        transaction block whose header falls within the selection range.
        Each duplicate gets today's date on its header line.
        """
        from datetime import date as _date  # noqa: PLC0415

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

    def action_prev_transaction(self) -> None:
        """Move cursor to the previous transaction header, or prev search match if bar open."""
        from ledgerkit_editor.widgets.search_bar import SearchBar  # noqa: PLC0415

        bar = self.query_one("#search-bar", SearchBar)
        if bar.display:
            bar.advance(direction=-1)
            return
        textarea = self.query_one("#journal_textarea", LedgerTextArea)
        row, _ = textarea.cursor_location
        line_infos = textarea._highlighter._line_infos
        for i in range(row - 1, -1, -1):
            if i < len(line_infos) and line_infos[i].kind == LineKind.XACT_HEADER:
                textarea.move_cursor((i, 0))
                return

    def action_next_transaction(self) -> None:
        """Move cursor to the next transaction header, or next search match if bar open."""
        from ledgerkit_editor.widgets.search_bar import SearchBar  # noqa: PLC0415

        bar = self.query_one("#search-bar", SearchBar)
        if bar.display:
            bar.advance(direction=1)
            return
        textarea = self.query_one("#journal_textarea", LedgerTextArea)
        row, _ = textarea.cursor_location
        line_infos = textarea._highlighter._line_infos
        for i in range(row + 1, len(line_infos)):
            if line_infos[i].kind == LineKind.XACT_HEADER:
                textarea.move_cursor((i, 0))
                return

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

    def action_cursor_to_start(self) -> None:
        """Move cursor to the very start of the file (Ctrl+Home)."""
        self.query_one("#journal_textarea", TextArea).move_cursor((0, 0))

    def action_cursor_to_end(self) -> None:
        """Move cursor to the very end of the file (Ctrl+End)."""
        textarea = self.query_one("#journal_textarea", TextArea)
        lines = textarea.text.splitlines()
        last_row = max(0, len(lines) - 1)
        last_col = len(lines[last_row]) if lines else 0
        textarea.move_cursor((last_row, last_col))

    def action_insert_today(self) -> None:
        """Insert today's date at the cursor position (Ctrl+D)."""
        self.query_one("#journal_textarea", TextArea).insert(_date.today().isoformat() + " ")

    def action_date_shift_up(self) -> None:
        """Shift the date sub-field under the cursor up by 1 (Shift+Up)."""
        self._shift_date_by(+1)

    def action_date_shift_down(self) -> None:
        """Shift the date sub-field under the cursor down by 1 (Shift+Down)."""
        self._shift_date_by(-1)

    def _shift_date_by(self, delta: int) -> None:
        """Shift the date sub-field under the cursor, or fall through to selection."""
        textarea = self.query_one("#journal_textarea", LedgerTextArea)
        row, col = textarea.cursor_location
        line_infos = textarea._highlighter._line_infos

        def _fallthrough() -> None:
            if delta > 0:
                textarea.action_cursor_up(select=True)
            else:
                textarea.action_cursor_down(select=True)

        if row >= len(line_infos) or line_infos[row].kind != LineKind.XACT_HEADER:
            _fallthrough()
            return

        lines = textarea.text.splitlines()
        line = lines[row] if row < len(lines) else ""
        m = _TXN_HEADER_RE.match(line)
        if not m:
            _fallthrough()
            return

        subfield = _date_subfield_at_col(col)
        if subfield is None:
            _fallthrough()
            return

        date_str = m.group(1)
        new_date_str = _shift_date_str(date_str, subfield, delta)
        textarea.replace(new_date_str, (row, 0), (row, len(date_str)))
        textarea.move_cursor((row, col), select=False)
