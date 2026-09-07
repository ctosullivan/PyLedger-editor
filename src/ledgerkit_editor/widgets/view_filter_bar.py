"""View filter status bar for JournalEditor.

Always visible at the top of the editor pane. Shows the active transaction
filter — either the fixed All/Cleared/Unreconciled cycle (Ctrl+L, via
set_mode) or an arbitrary label for the Ctrl+O criteria filter (via
set_label, since that one isn't one of the three fixed modes). This widget
only displays the current state; JournalEditor (widgets/view_filter.py)
decides which of Ctrl+L/Ctrl+O is active.
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
        """Update the displayed label for the given Ctrl+L filter mode."""
        self.current_mode = mode
        self.query_one("#filter-label", Static).update(_LABELS.get(mode, _LABELS[0]))

    def set_label(self, text: str) -> None:
        """Set an arbitrary label directly — used by the Ctrl+O criteria
        filter, which isn't one of the three fixed Ctrl+L modes."""
        self.query_one("#filter-label", Static).update(text)
