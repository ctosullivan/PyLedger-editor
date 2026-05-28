"""Incremental search bar for JournalEditor.

Docked at the bottom of the editor; hidden by default. Ctrl+F opens it (or
advances to next match if already open). Ctrl+Shift+F / Ctrl+R go to the
previous match. Escape dismisses the bar and clears all highlights.
"""

from __future__ import annotations

import bisect
import re

from textual.app import ComposeResult
from textual.widget import Widget
from textual.widgets import Button, Input, Label

from ledger_editor.highlighting.highlighter import LineInfo, LineKind  # noqa: F401

__all__ = ["SearchBar"]


def _find_transaction_header_above(
    line_infos: list[LineInfo], row: int
) -> int | None:
    """Return the row of the nearest XACT_HEADER at or above row, or None."""
    for i in range(min(row, len(line_infos) - 1), -1, -1):
        if line_infos[i].kind == LineKind.XACT_HEADER:
            return i
    return None

# Type alias matching Textual's Location = (row, col), 0-indexed.
Location = tuple[int, int]


def _build_offset_table(text: str) -> list[int]:
    """Return a list of codepoint offsets where each line begins.

    Index i is the codepoint offset of the first character of line i (0-based).
    The sentinel at index len(lines) is len(text), enabling binary search to
    find a line index from any absolute codepoint offset.

    Pure function — no Textual dependency. Fully unit-testable.

    Args:
        text: the full journal text (may contain '\n' newlines).
    """
    offsets = [0]
    for i, ch in enumerate(text):
        if ch == "\n":
            offsets.append(i + 1)
    return offsets


def _offset_to_location(offset: int, table: list[int]) -> Location:
    """Convert an absolute codepoint offset into a (row, col) location.

    Uses binary search (O(log N)) into the line-start offset table produced by
    _build_offset_table(). The column is a codepoint index within the line.

    Pure function — no Textual dependency. Fully unit-testable.

    Args:
        offset: absolute codepoint offset in the full text.
        table: list of line-start offsets from _build_offset_table().
    """
    row = bisect.bisect_right(table, offset) - 1
    row = max(0, row)
    col = offset - table[row]
    return (row, col)


class SearchBar(Widget):
    """Incremental search bar docked at the bottom of JournalEditor.

    Hidden (display: none) by default. Call open_bar() to reveal and focus.
    Calls LedgerTextArea.set_search_matches() to drive highlighting.
    """

    def __init__(self, *args: object, **kwargs: object) -> None:
        super().__init__(*args, **kwargs)  # type: ignore[arg-type]
        self._matches: list[tuple[Location, Location]] = []
        self._current: int = -1
        self._initial_direction: int = 1
        self.display = False

    def compose(self) -> ComposeResult:
        """Render the search input, match counter, and navigation buttons."""
        yield Input(id="search-input", placeholder="Search…")
        yield Label("", id="match-counter")
        yield Button("▲", id="btn-prev", variant="default")
        yield Button("▼", id="btn-next", variant="default")

    # ------------------------------------------------------------------
    # Public interface (called from JournalEditor actions)
    # ------------------------------------------------------------------

    def on_mount(self) -> None:
        """Remove navigation buttons from the tab order so Tab goes straight to the editor."""
        for btn in self.query(Button):
            btn.can_focus = False

    def open_bar(self, initial_direction: int = 1) -> None:
        """Reveal the search bar and focus the input field.

        Args:
            initial_direction: +1 for forward (Ctrl+F), -1 for reverse
                (Ctrl+Shift+F). Affects which direction the first F3 travels.
        """
        self._initial_direction = initial_direction
        self.display = True
        input_widget = self.query_one("#search-input", Input)
        input_widget.focus()
        # Re-compute matches for any text already in the input.
        if input_widget.value:
            self._compute_matches(input_widget.value)

    def dismiss(self) -> None:
        """Hide the bar and clear all search highlights."""
        from ledger_editor.widgets.ledger_textarea import LedgerTextArea  # noqa: PLC0415

        self.display = False
        self._matches = []
        self._current = -1
        try:
            textarea = self.app.query_one("#journal_textarea", LedgerTextArea)
            textarea.set_search_matches([], -1)
            textarea.focus()
        except Exception:  # noqa: BLE001
            pass

    def advance(self, direction: int = 1) -> None:
        """Move to the next (direction=+1) or previous (direction=-1) match."""
        self._advance(direction)

    def advance_to_transaction(self, direction: int = 1) -> None:
        """Jump to the next transaction block that contains a match."""
        self._advance_transaction(direction)

    # ------------------------------------------------------------------
    # Event handlers
    # ------------------------------------------------------------------

    def on_input_changed(self, event: Input.Changed) -> None:
        """Re-compute matches whenever the search pattern changes."""
        self._compute_matches(event.value)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Navigate forward (▼) or backward (▲) on button press."""
        if event.button.id == "btn-next":
            self._advance(1)
        elif event.button.id == "btn-prev":
            self._advance(-1)

    # ------------------------------------------------------------------
    # Internal match computation and navigation
    # ------------------------------------------------------------------

    def _compute_matches(self, pattern: str) -> None:
        """Find all occurrences of pattern in the journal text.

        Requires pattern to be at least 2 characters (shorter patterns
        produce too many matches to be useful and slow down the highlight
        rebuild). Clears highlights and shows 'Pattern too short' otherwise.

        Uses re.escape() to treat the pattern as a literal string — regex mode
        is out of scope for v0.7.0.

        Args:
            pattern: the raw text typed by the user in the search input.
        """
        from ledger_editor.widgets.ledger_textarea import LedgerTextArea  # noqa: PLC0415

        textarea = self.app.query_one("#journal_textarea", LedgerTextArea)

        if len(pattern) < 2:
            self._matches = []
            self._current = -1
            self._update_counter(pattern)
            textarea.set_search_matches([], -1)
            return

        text = textarea.text
        table = _build_offset_table(text)

        # Purpose: find all case-insensitive occurrences of the literal pattern
        #   in the full journal text as a single string (including newlines).
        # Group breakdown: no groups — match object provides .start()/.end().
        # Edge cases: re.escape() makes metacharacters literal; empty text
        #   produces zero matches; pattern shorter than 2 chars is excluded above.
        safe_pat = re.escape(pattern)
        self._matches = [
            (
                _offset_to_location(m.start(), table),
                _offset_to_location(m.end(), table),
            )
            for m in re.finditer(safe_pat, text, re.IGNORECASE)
        ]

        if self._matches:
            self._current = 0
            textarea.set_search_matches(self._matches, self._current)
            textarea.move_cursor(self._matches[0][0])
            textarea.scroll_cursor_visible()
        else:
            self._current = -1
            textarea.set_search_matches([], -1)

        self._update_counter(pattern)

    def _advance(self, direction: int) -> None:
        """Step to the next or previous match, wrapping around at the ends.

        Args:
            direction: +1 for forward, -1 for backward.
        """
        if not self._matches:
            return
        from ledger_editor.widgets.ledger_textarea import LedgerTextArea  # noqa: PLC0415

        self._current = (self._current + direction) % len(self._matches)
        textarea = self.app.query_one("#journal_textarea", LedgerTextArea)
        textarea.set_search_matches(self._matches, self._current)
        textarea.move_cursor(self._matches[self._current][0])
        textarea.scroll_cursor_visible()
        self._update_counter(self.query_one("#search-input", Input).value)

    def _advance_transaction(self, direction: int) -> None:
        """Jump to the next/previous transaction block containing a match.

        Skips matches in the same transaction block as the current cursor
        position, using the highlighter's line_infos to identify boundaries.

        Args:
            direction: +1 for forward, -1 for backward.
        """
        if not self._matches:
            return
        from ledger_editor.widgets.ledger_textarea import LedgerTextArea  # noqa: PLC0415

        textarea = self.app.query_one("#journal_textarea", LedgerTextArea)
        line_infos = textarea._highlighter._line_infos
        current_row = textarea.cursor_location[0]
        current_header = _find_transaction_header_above(line_infos, current_row)

        attempts = len(self._matches)
        idx = (self._current + direction) % len(self._matches)
        while attempts > 0:
            match_row = self._matches[idx][0][0]
            match_header = _find_transaction_header_above(line_infos, match_row)
            if match_header != current_header:
                self._current = idx
                textarea.set_search_matches(self._matches, self._current)
                textarea.move_cursor(self._matches[idx][0])
                textarea.scroll_cursor_visible()
                self._update_counter(
                    self.query_one("#search-input", Input).value
                )
                return
            idx = (idx + direction) % len(self._matches)
            attempts -= 1

    def _update_counter(self, pattern: str) -> None:
        """Refresh the 'N of M' / 'No matches' / 'Pattern too short' label."""
        label = self.query_one("#match-counter", Label)
        if len(pattern) < 2:
            label.update("Pattern too short")
        elif not self._matches:
            label.update("No matches")
        else:
            label.update(f"{self._current + 1} of {len(self._matches)}")
