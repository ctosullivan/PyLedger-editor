"""Transaction filter popup overlay (Ctrl+O).

Provides date-range, account, and payee filters. Applies to JournalEditor
without closing the popup, reusing the same view-filter engine Ctrl+L uses
(ViewFilterMixin, widgets/view_filter.py) — the two are mutually exclusive.
Smart date parsing delegates to ledgerkit_editor.utils.date_parser; account
and payee fields follow ledgerkit.Query's own substring-or-regex convention,
mirrored locally in ledgerkit_editor.utils.query_match (see that module's
docstring for why it's a local copy rather than an import).
"""

from __future__ import annotations

import re

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal
from textual.message import Message
from textual.widget import Widget
from textual.widgets import Button, Input, Label

__all__ = ["FilterPopup"]


class FilterPopup(Widget):
    """Overlay widget for filtering the transaction view.

    Triggered by Ctrl+O. Stays visible while active so the user can adjust
    filters interactively. Closed by a second Ctrl+O or Escape — closing the
    popup does NOT clear an already-applied filter; use the Clear button (or
    apply an empty filter) for that.

    Fields:
        date_from / date_to : Smart date strings — ISO 8601, "today",
                              "yesterday", "last month", "last year", "ytd",
                              "q1".."q4", or a relative offset like "-7d" /
                              "+1m" / "-2w" / "+1y". Parsed by
                              date_parser.parse_date_range().
        account             : Account filter — plain substring, or a Python
                              regex if the text contains any regex
                              metacharacter (same convention hledger/
                              ledgerkit.Query use). Matches if ANY posting in
                              the transaction matches.
        payee               : Same substring-or-regex convention, matched
                              against the transaction description.
    """

    BINDINGS = [
        Binding("ctrl+o", "close_self", "Close filter", show=False, priority=True),
        Binding("escape", "close_self", "Close filter", show=False, priority=True),
    ]

    DEFAULT_CSS = """
    FilterPopup {
        layer: overlay;
        width: 60;
        height: auto;
        border: double $primary;
        background: $surface;
        padding: 1 2;
        offset: 50% 20%;
    }
    FilterPopup #filter-buttons {
        height: auto;
        align: right middle;
        margin-top: 1;
    }
    FilterPopup Button {
        margin-left: 1;
    }
    """

    class FilterApplied(Message):
        """Posted when a filter is successfully built and ready to apply.

        Carries an already-validated predicate (Callable[[Transaction],
        bool]) rather than the raw Query, so any DateParseError or invalid
        regex is caught and reported here in the popup — where the user's
        attention already is — rather than deeper in the handler.
        """

        def __init__(self, predicate: object) -> None:
            super().__init__()
            self.predicate = predicate

    class FilterCleared(Message):
        """Posted when the user clears the active filter (Clear button)."""

    def compose(self) -> ComposeResult:
        """Render filter input fields and Apply/Clear buttons."""
        yield Label("Transaction Filter  (Ctrl+O to close)", id="filter-title")
        yield Label("Date from:")
        yield Input(placeholder="e.g. last month / 2024-01-01 / -7d", id="date-from")
        yield Label("Date to:")
        yield Input(placeholder="e.g. today / 2024-12-31", id="date-to")
        yield Label("Account:")
        yield Input(placeholder="substring or /regex/, e.g. ^expenses:food", id="account")
        yield Label("Payee:")
        yield Input(placeholder="substring or regex", id="payee")
        with Horizontal(id="filter-buttons"):
            yield Button("Apply", id="btn-apply", variant="primary")
            yield Button("Clear", id="btn-clear")

    def on_mount(self) -> None:
        """Focus the first input field so Escape and keyboard entry work immediately."""
        self.query_one("#date-from", Input).focus()

    def action_close_self(self) -> None:
        """Remove the popup (Ctrl+O toggle or Escape). Leaves any applied filter active."""
        self.remove()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        """Enter in any field applies the filter, same as the Apply button."""
        self.apply_filter()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Apply or Clear button pressed."""
        if event.button.id == "btn-apply":
            self.apply_filter()
        elif event.button.id == "btn-clear":
            self.post_message(self.FilterCleared())

    def apply_filter(self) -> None:
        """Read field values, build a validated predicate, and post FilterApplied.

        Empty date/account/payee fields become None (no filter on that
        dimension) — an all-empty form is a valid, harmless "match
        everything" filter. Smart dates are parsed via
        date_parser.parse_date_range(); a DateParseError is caught and shown
        as a notification without posting anything. Account/payee become a
        ledgerkit.Query passed through query_match.build_transaction_predicate(),
        which raises re.error immediately for an invalid regex — also caught
        and shown as a notification.
        """
        import ledgerkit  # noqa: PLC0415
        from ledgerkit_editor.utils.date_parser import DateParseError, parse_date_range  # noqa: PLC0415
        from ledgerkit_editor.utils.query_match import build_transaction_predicate  # noqa: PLC0415

        date_from_text = self.query_one("#date-from", Input).value.strip() or None
        date_to_text = self.query_one("#date-to", Input).value.strip() or None
        account_text = self.query_one("#account", Input).value.strip() or None
        payee_text = self.query_one("#payee", Input).value.strip() or None

        try:
            date_from, date_to = parse_date_range(date_from_text, date_to_text)
        except DateParseError as exc:
            self.app.notify(str(exc), severity="warning")
            return

        query = ledgerkit.Query(
            account=account_text,
            payee=payee_text,
            date_from=date_from,
            date_to=date_to,
        )

        try:
            predicate = build_transaction_predicate(query)
        except re.error as exc:
            self.app.notify(f"Invalid regex in filter: {exc}", severity="warning")
            return

        self.post_message(self.FilterApplied(predicate))
