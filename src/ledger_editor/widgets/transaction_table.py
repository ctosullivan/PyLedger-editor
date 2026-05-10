"""Main editing surface: a grid of transaction postings.

Each row corresponds to one journal posting. Supports in-place per-field
editing with live validation via PyLedger.parse_string_lenient() and
PyLedger.check_transaction_autobalanced().

Drives all keybinding actions defined in the keybindings package.
"""

from __future__ import annotations

from pathlib import Path

from textual.widget import Widget
from textual.widgets import Label

__all__ = ["TransactionTable"]


class TransactionTable(Widget):
    """Tabular editing surface for hledger journal transactions.

    Rows map to postings within transactions. Transactions are separated by
    a blank row. In-place editing updates an PyLedger.EditorDocument instance
    which serialises changes back to text via PyLedger.transaction_to_text().

    Keybinding actions (Ctrl+S, Shift+C, Tab autocomplete, date increment,
    field navigation, etc.) are wired to this widget's action handlers.
    See keybindings/office.py and keybindings/emacs_ledger.py for the full
    list.

    Args:
        journal_path: Absolute path to the journal file being edited.
    """

    def __init__(self, journal_path: Path) -> None:
        super().__init__()
        self.journal_path = journal_path

    def compose(self):
        """Placeholder compose — will render a DataTable of postings."""
        yield Label(f"Editing: {self.journal_path}\n(table not yet implemented)")

    # ------------------------------------------------------------------
    # Cleared / pending toggle (Shift+C)
    # 3-state cycle: uncleared → pending → cleared → uncleared
    #   (cleared=False, pending=False) → (cleared=False, pending=True)
    #   → (cleared=True, pending=False) → (cleared=False, pending=False)
    # ------------------------------------------------------------------

    def action_toggle_cleared(self) -> None:
        """Cycle the selected transaction through uncleared → pending → cleared.

        Uses Transaction.cleared and Transaction.pending booleans (not a flag field).
        Serialises via PyLedger.transaction_to_text() and writes via EditorDocument.
        """
        # TODO: implement 3-state toggle on selected transaction(s)

    # ------------------------------------------------------------------
    # Save (Ctrl+S): sort by date, re-align whitespace, warn-and-save
    # ------------------------------------------------------------------

    def action_save(self) -> None:
        """Sort transactions by date, re-align whitespace, then save.

        Runs PyLedger checks after tidying. Validation errors are displayed
        as warnings in a notification bar but do not block the write.
        Uses PyLedger.EditorDocument.save() for the file write.
        """
        # TODO: implement sort + align + warn-and-save

    # ------------------------------------------------------------------
    # Autofill (Ctrl+D): duplicate selected transaction once to bottom
    # ------------------------------------------------------------------

    def action_autofill(self) -> None:
        """Copy the selected transaction to a new entry at the bottom of the ledger.

        Date is adjusted to today. Appends via PyLedger.EditorDocument.add_transaction().
        """
        # TODO: implement duplicate-once autofill
