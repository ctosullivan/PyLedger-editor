"""Main editing surface: a full-text editor for hledger journal files.

Shows raw journal text in a LedgerTextArea. Ctrl+L cycles the editor view
between All, Cleared, and Unreconciled transactions without leaving the editor.
Search bar (Ctrl+F) is implemented in SearchBar (search_bar.py). View filter bar
is implemented in ViewFilterBar (view_filter_bar.py).

JournalEditor itself stays deliberately thin — BINDINGS, message classes,
init/mount orchestration, save, and cursor tracking. Larger, more separable
concerns are provided via mixins (Module Size Rule split, Phase 2 of
planning/next-release-phase-plan.md):
  - DateShiftMixin (date_shift.py) — Shift+Up/Down date-field shifting
  - ViewFilterMixin (view_filter.py) — Ctrl+L cleared/uncleared cycle
  - TransactionBlocksMixin (transaction_blocks.py) — Ctrl+T/Ctrl+G/Ctrl+R
"""

from __future__ import annotations

import re
import time as _time
from datetime import date as _date
from pathlib import Path

from textual.app import ComposeResult
from textual.binding import Binding
from textual.message import Message
from textual.widget import Widget
from textual.widgets import TextArea

from ledgerkit_editor.highlighting.highlighter import LineKind
from ledgerkit_editor.widgets.date_shift import DateShiftMixin
from ledgerkit_editor.widgets.ledger_textarea import LedgerTextArea
from ledgerkit_editor.widgets.transaction_blocks import TransactionBlocksMixin
from ledgerkit_editor.widgets.view_filter import ViewFilterMixin
from ledgerkit_editor.widgets.view_filter_bar import ViewFilterBar

__all__ = ["JournalEditor"]

# Purpose: split an hledger posting line at the account/amount boundary.
#   hledger requires at least two spaces (or a tab) between the account name
#   and the amount so that account names with single spaces are unambiguous.
# Edge cases: elided postings (no amount) produce a single-element split,
#   returning the full stripped line as the account name. Caller must strip
#   the leading indent before splitting.
_POSTING_SPLIT_RE = re.compile(r"\s{2,}|\t")


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


class JournalEditor(DateShiftMixin, ViewFilterMixin, TransactionBlocksMixin, Widget):
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
        # View filter state (read/written by ViewFilterMixin, view_filter.py)
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

        When ledgerkit-editor is spawned by hledger-ui, Windows emits a console
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

    # ------------------------------------------------------------------
    # Key actions — save
    # ------------------------------------------------------------------

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
        from ledgerkit.parser import ParseWarning  # noqa: PLC0415

        journal, parse_errors = ledgerkit.parse_string_lenient(text)

        for err in parse_errors:
            severity = "information" if isinstance(err, ParseWarning) else "warning"
            self.app.notify(str(err), severity=severity)

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
