"""View filter status bar for JournalEditor.

Always visible at the top of the editor pane. Shows the active transaction
filter (All / Cleared / Unreconciled). Ctrl+L (handled by JournalEditor)
cycles the mode; this widget only displays the current state.
"""

from __future__ import annotations

from textual.app import ComposeResult
from textual.widget import Widget
from textual.widgets import Static

__all__ = ["ViewFilterBar"]

_LABELS: dict[int, str] = {
    0: "View: All transactions",
    1: "View: Cleared only",
    2: "View: Unreconciled only",
}


class ViewFilterBar(Widget):
    """1-row status bar showing the active transaction view filter."""

    DEFAULT_CSS = """
    ViewFilterBar {
        height: 1;
        background: $surface;
        color: $text-muted;
        padding: 0 1;
    }
    """

    def __init__(self, *args: object, **kwargs: object) -> None:
        super().__init__(*args, **kwargs)  # type: ignore[arg-type]
        self.current_mode: int = 0

    def compose(self) -> ComposeResult:
        yield Static(_LABELS[0], id="filter-label")

    def set_mode(self, mode: int) -> None:
        """Update the displayed label for the given filter mode."""
        self.current_mode = mode
        self.query_one("#filter-label", Static).update(_LABELS.get(mode, _LABELS[0]))
