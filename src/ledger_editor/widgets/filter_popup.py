"""Transaction filter popup overlay (Ctrl+Shift+F).

Provides date-range, account-glob, payee-substring, and amount-range filters.
Applies to the TransactionTable without closing the popup. Smart date parsing
delegates to ledger_editor.utils.date_parser.
"""

from __future__ import annotations

from textual.app import ComposeResult
from textual.widget import Widget
from textual.widgets import Input, Label

__all__ = ["FilterPopup"]


class FilterPopup(Widget):
    """Overlay widget for filtering the transaction view.

    Triggered by Ctrl+Shift+F. Stays visible while active so the user can
    adjust filters interactively. Closed by a second Ctrl+Shift+F or Escape.

    Fields:
        date_from / date_to : Smart date strings ("last month", "ytd", "q1",
                              ISO 8601). Parsed by date_parser.parse_date().
        account             : Account glob pattern (e.g. "expenses:*").
        payee               : Substring match against transaction descriptions.
        amount_min / amount_max : Numeric range in the primary commodity.
    """

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
    """

    def compose(self) -> ComposeResult:
        """Render filter input fields."""
        yield Label("Transaction Filter  (Ctrl+Shift+F to close)", id="filter-title")
        yield Label("Date from:")
        yield Input(placeholder="e.g. last month / 2024-01-01 / ytd", id="date-from")
        yield Label("Date to:")
        yield Input(placeholder="e.g. today / 2024-12-31", id="date-to")
        yield Label("Account:")
        yield Input(placeholder="e.g. expenses:food", id="account")
        yield Label("Payee:")
        yield Input(placeholder="substring match", id="payee")

    def apply_filter(self) -> None:
        """Read field values, build a PyLedger.Query, and post to TransactionTable.

        Date strings are parsed by date_parser.parse_date(). Posts a message
        to the TransactionTable to trigger a filtered re-render.
        """
        # TODO: implement Query assembly and message dispatch
