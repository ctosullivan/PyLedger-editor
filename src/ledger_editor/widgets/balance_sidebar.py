"""Persistent sidebar widget displaying account balances.

Fetches balances via PyLedger.reports.balance(tree=True) on app start and after
every Ctrl+S save. Renders as a scrollable tree with collapsible parent accounts.
"""

from __future__ import annotations

from pathlib import Path

from textual.widget import Widget
from textual.widgets import Label

__all__ = ["BalanceSidebar"]


class BalanceSidebar(Widget):
    """Scrollable account-balance tree displayed on the left of the editor.

    Refreshes asynchronously so the editing surface remains responsive
    during PyLedger I/O. Triggered on startup and after every Ctrl+S save.

    Args:
        journal_path: Absolute path to the journal file being edited.
    """

    def __init__(self, journal_path: Path) -> None:
        super().__init__()
        self.journal_path = journal_path

    def compose(self):
        """Placeholder compose — will render a Tree of BalanceRow entries."""
        yield Label("Balances\n(loading…)")

    async def refresh_balances(self) -> None:
        """Reload and re-render account balances from the journal file.

        Calls PyLedger.load(journal_path).balance(tree=True) and rebuilds
        the Tree widget. Must be awaited; runs in a worker to avoid blocking.
        """
        # TODO: implement using PyLedger.load() and balance(tree=True)
        # Returns list[PyLedger.BalanceRow]; each row has .account, .depth,
        # .amounts (dict[commodity, Decimal]), .is_subtotal
