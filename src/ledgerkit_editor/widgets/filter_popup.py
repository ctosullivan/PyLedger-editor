"""Transaction filter popup overlay (Ctrl+O).

Provides date-range, account, and payee filters. Applies to JournalEditor
without closing the popup, reusing the same view-filter engine Ctrl+L uses
(ViewFilterMixin, widgets/view_filter.py) — the two combine (AND) rather
than being mutually exclusive. Smart date parsing delegates to
ledgerkit_editor.utils.date_parser; account and payee fields follow
ledgerkit.Query's own substring-or-regex convention, mirrored locally in
ledgerkit_editor.utils.query_match (see that module's docstring for why
it's a local copy rather than an import). Tab in the Account/Payee fields
also autocompletes against JournalEditor's own account/payee index — see
action_complete_field().
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
    apply with every field blank) for that. The Clear button also empties
    the input fields themselves, not just the applied filter.

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
                              the transaction matches. Tab completes/cycles
                              known account names — see action_complete_field().
        payee               : Same substring-or-regex convention, matched
                              against the transaction description. Tab
                              completes/cycles known payee names.
    """

    BINDINGS = [
        Binding("ctrl+o", "close_self", "Close filter", show=False, priority=True),
        Binding("escape", "close_self", "Close filter", show=False, priority=True),
        # Tab: complete the focused Account/Payee field against
        # JournalEditor's account/payee index — see action_complete_field().
        # priority=True so it's caught here rather than doing plain
        # Input-to-Input focus-cycling (Tab's usual behaviour) first.
        Binding("tab", "complete_field", "Autocomplete", show=False, priority=True),
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

    def __init__(self, *args: object, **kwargs: object) -> None:
        super().__init__(*args, **kwargs)  # type: ignore[arg-type]
        # (field_id, candidates, selected_index) for Tab-cycling in
        # action_complete_field() — None means no completion in progress.
        self._field_completion: tuple[str, list[str], int] | None = None

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

    def action_complete_field(self) -> None:
        """Tab: complete the focused Account/Payee field's whole value
        against JournalEditor's account/payee index, cycling to the next
        match on repeated presses — the same bash-style convention as Tab
        autocomplete in the main editor (widgets/autocomplete.py), just
        applied to a single-line Input's entire value rather than a
        partial token within a larger line.

        Falls through to ordinary Tab focus-cycling when: the focused
        widget isn't the Account or Payee Input (e.g. a Date field, or
        nothing), JournalEditor can't be found, or there are no matches
        for the current text — matching AutocompleteMixin's own
        no-match-falls-through behaviour.
        """
        from ledgerkit_editor.widgets.transaction_table import JournalEditor  # noqa: PLC0415

        focused = self.app.focused
        field_id = getattr(focused, "id", None)
        if field_id not in ("account", "payee") or not isinstance(focused, Input):
            self.app.action_focus_next()
            return
        input_widget = focused

        if (
            self._field_completion is not None
            and self._field_completion[0] == field_id
            and input_widget.value == self._field_completion[1][self._field_completion[2]]
        ):
            # Continuation: cycle to the next candidate from last time.
            _, candidates, index = self._field_completion
            index = (index + 1) % len(candidates)
            next_value = candidates[index]
            input_widget.value = next_value
            input_widget.cursor_position = len(next_value)
            self._field_completion = (field_id, candidates, index)
            return

        try:
            editor = self.app.query_one(JournalEditor)
        except Exception:  # noqa: BLE001
            self.app.action_focus_next()
            return

        partial = input_widget.value
        index = editor._journal_index
        candidates = (
            index.matching_accounts(partial) if field_id == "account"
            else index.matching_payees(partial)
        )
        if not candidates:
            self._field_completion = None
            self.app.action_focus_next()
            return

        first = candidates[0]
        input_widget.value = first
        input_widget.cursor_position = len(first)
        self._field_completion = (field_id, candidates, 0)

    def on_input_submitted(self, event: Input.Submitted) -> None:
        """Enter in any field applies the filter, same as the Apply button."""
        self.apply_filter()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Apply or Clear button pressed."""
        if event.button.id == "btn-apply":
            self.apply_filter()
        elif event.button.id == "btn-clear":
            self._clear_fields()
            self.post_message(self.FilterCleared())

    def _clear_fields(self) -> None:
        """Reset every input field to empty (Clear button)."""
        for field_id in ("#date-from", "#date-to", "#account", "#payee"):
            self.query_one(field_id, Input).value = ""

    def apply_filter(self) -> None:
        """Read field values, build a validated predicate, and post FilterApplied.

        Empty date/account/payee fields become None (no filter on that
        dimension). If EVERY field is empty, this is treated as "no filter"
        rather than a "match everything" filter that still round-trips the
        text through ledgerkit's re-serialisation — posting FilterCleared
        instead (a no-op if nothing was active) so an empty Apply never
        reformats the document or marks it modified. Smart dates are parsed
        via date_parser.parse_date_range(); a DateParseError is caught and
        shown as a notification without posting anything. Account/payee
        become a ledgerkit.Query passed through
        query_match.build_transaction_predicate(), which raises re.error
        immediately for an invalid regex — also caught and shown as a
        notification.
        """
        import ledgerkit  # noqa: PLC0415
        from ledgerkit_editor.utils.date_parser import DateParseError, parse_date_range  # noqa: PLC0415
        from ledgerkit_editor.utils.query_match import build_transaction_predicate  # noqa: PLC0415

        date_from_text = self.query_one("#date-from", Input).value.strip() or None
        date_to_text = self.query_one("#date-to", Input).value.strip() or None
        account_text = self.query_one("#account", Input).value.strip() or None
        payee_text = self.query_one("#payee", Input).value.strip() or None

        if not any((date_from_text, date_to_text, account_text, payee_text)):
            self.post_message(self.FilterCleared())
            return

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
