"""View filter status bar for JournalEditor.

Always visible at the top of the editor pane. Shows the active transaction
filter — Ctrl+L's fixed All/Cleared/Unreconciled cycle, an arbitrary label
for the Ctrl+O criteria filter, or (since the two combine with AND rather
than being mutually exclusive) both at once via set_combined(). This widget
only displays the current state; JournalEditor (widgets/view_filter.py)
decides what's active.
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

    def set_combined(
        self,
        mode: int,
        criteria_active: bool,
        visible_count: int | None = None,
        total_count: int | None = None,
    ) -> None:
        """Update for the current Ctrl+L mode AND whether a Ctrl+O criteria
        filter is also active, composing one label describing both.

        Ctrl+L and Ctrl+O combine (AND) rather than being mutually
        exclusive — this is the label update JournalEditor calls after any
        change to either dimension, so the two never show a stale or
        one-sided description of what's actually filtering the view.

        Args:
            visible_count / total_count: when both given (only meaningful
                while a filter is actually active — mode != 0 or
                criteria_active), appends "(visible/total)" so the user can
                see how much of the journal a filter is actually excluding
                without counting rows by hand.
        """
        self.current_mode = mode
        base = _LABELS.get(mode, _LABELS[0])
        if not criteria_active:
            label = base
        elif mode == 0:
            label = "View: Filtered (Ctrl+O)"
        else:
            label = f"{base} + Filtered (Ctrl+O)"
        if visible_count is not None and total_count is not None:
            label = f"{label} ({visible_count}/{total_count})"
        self.query_one("#filter-label", Static).update(label)
