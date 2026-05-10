"""Register panel: shows the 10 most recent postings for the active account.

The active account is set by calling show_account(), which is invoked by the
app in response to JournalEditor.CursorAccountChanged and
BalanceSidebar.AccountSelected messages.
"""

from __future__ import annotations

from pathlib import Path

from textual import work
from textual.app import ComposeResult
from textual.binding import Binding
from textual.widget import Widget
from textual.widgets import DataTable, Label

__all__ = ["RegisterPanel"]


def _fmt_register_amount(amount: object) -> str:
    """Format a RegisterRow.amount (Amount dataclass) for display.

    Handles prefix-symbol currencies (e.g. £42.50, -£42.50) and suffix-code
    currencies (e.g. 42.50 EUR). Returns a plain decimal string when the
    amount carries no commodity symbol.
    """
    sym = amount.commodity  # type: ignore[attr-defined]
    qty = amount.quantity   # type: ignore[attr-defined]
    if not sym:
        return f"{qty:,.2f}"
    if sym[0].isalpha():                        # suffix commodity (EUR, USD)
        return f"{qty:,.2f} {sym}"
    if qty < 0:                                 # prefix symbol, negative
        return f"-{sym}{(-qty):,.2f}"
    return f"{sym}{qty:,.2f}"                   # prefix symbol, positive


class RegisterPanel(Widget):
    """DataTable showing the 10 most recent postings for the active account.

    Call show_account(account) to change the displayed account. Refreshes
    asynchronously; stale results from a previous account are discarded.

    Args:
        journal_path: Absolute path to the journal file to query.
    """

    DEFAULT_CSS = """
    RegisterPanel {
        layout: vertical;
    }
    RegisterPanel > Label {
        height: 1;
        padding: 0 1;
        color: $text-muted;
    }
    RegisterPanel > DataTable {
        height: 1fr;
    }
    """

    BINDINGS = [
        Binding("tab", "focus_next_panel", "Focus editor", show=False, priority=True),
        Binding("shift+tab", "focus_prev_panel", "Focus balance", show=False, priority=True),
    ]

    def __init__(self, journal_path: Path) -> None:
        """Initialise with the resolved absolute journal file path.

        Args:
            journal_path: Absolute path to the .journal or .ledger file to query.
        """
        super().__init__()
        self.journal_path = journal_path
        self._current_account: str | None = None

    def compose(self) -> ComposeResult:
        """Render a label and an empty DataTable."""
        yield Label("Register: (no account selected)", id="register_label")
        table = DataTable(id="register_table")
        table.cursor_type = "row"
        table.show_cursor = False
        yield table

    def on_mount(self) -> None:
        """Add columns to the DataTable after the widget is mounted."""
        self.query_one("#register_table", DataTable).add_columns(
            "Date", "Description", "Amount", "Balance"
        )

    def show_account(self, account: str | None) -> None:
        """Set the account to display and trigger an async data refresh.

        Passing None clears the table and resets the label.
        """
        self._current_account = account
        label_text = f"Register: {account}" if account else "Register: (no account selected)"
        self.query_one("#register_label", Label).update(label_text)
        if account:
            self._load_register(account)
        else:
            self._clear_table()

    def _clear_table(self) -> None:
        self.query_one("#register_table", DataTable).clear()

    @work(thread=True, exclusive=True)
    def _load_register(self, account: str) -> None:
        """Fetch register rows for account in a background thread.

        Uses exclusive=True so a new call automatically cancels any in-flight
        worker from a previous account selection.
        """
        import PyLedger  # noqa: PLC0415

        journal = PyLedger.load(self.journal_path)
        rows = journal.register(query=PyLedger.Query(account=account))
        last_10 = rows[-10:]
        self.app.call_from_thread(self._render_rows, last_10, account)

    def _render_rows(self, rows: list, for_account: str) -> None:
        """Rebuild the DataTable on the main thread.

        Discards the result if a newer account was selected while the worker
        was running (stale-result guard).
        """
        if for_account != self._current_account:
            return
        table = self.query_one("#register_table", DataTable)
        table.clear()
        for row in rows:
            table.add_row(
                str(row.date),
                row.description,
                _fmt_register_amount(row.amount),
                str(row.running_balance),
            )

    def action_focus_next_panel(self) -> None:
        """Move focus forward: RegisterPanel → JournalEditor TextArea."""
        from textual.widgets import TextArea  # noqa: PLC0415

        self.app.query_one("#journal_textarea", TextArea).focus()

    def action_focus_prev_panel(self) -> None:
        """Move focus backward: RegisterPanel → BalanceSidebar Tree."""
        from ledger_editor.widgets.balance_sidebar import BalanceSidebar  # noqa: PLC0415
        from textual.widgets import Tree  # noqa: PLC0415

        self.app.query_one(BalanceSidebar).query_one(Tree).focus()
