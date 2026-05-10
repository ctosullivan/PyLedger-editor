"""Main editing surface: a grid of transaction postings.

Each transaction produces a header row (date, flag, description) followed by
one posting row per posting. An Input widget below the DataTable appears when
a cell enters edit mode; the DataTable scrolls freely while the Input bar
stays pinned at the bottom.
"""

from __future__ import annotations

import dataclasses
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
import datetime
from pathlib import Path

from textual.app import ComposeResult
from textual.coordinate import Coordinate
from textual.message import Message
from textual.widget import Widget
from textual.widgets import DataTable, Input

__all__ = ["TransactionTable"]

# Column indices (DataTable has 5 columns)
_COL_DATE = 0
_COL_FLAG = 1
_COL_DESC = 2
_COL_ACCOUNT = 3
_COL_AMOUNT = 4

# Editable columns per row type. Flag (col 1) is toggled via Shift+C, not direct edit.
_HEADER_EDITABLE: frozenset[int] = frozenset({_COL_DATE, _COL_DESC})
_POSTING_EDITABLE: frozenset[int] = frozenset({_COL_ACCOUNT, _COL_AMOUNT})


@dataclass
class _RowMeta:
    """Maps a DataTable row back to a journal transaction and posting."""

    txn_idx: int
    posting_idx: int | None  # None = header row; -1 = blank separator between transactions


def _flag_str(txn: object) -> str:
    """Return the status character for a transaction: '*', '!', or ' '."""
    if txn.cleared:  # type: ignore[attr-defined]
        return "*"
    if txn.pending:  # type: ignore[attr-defined]
        return "!"
    return " "


def _fmt_amount(amount: object) -> str:
    """Render an Amount as 'COMMODITY QUANTITY', e.g. '£42.50' or '£-42.50'."""
    return f"{amount.commodity}{amount.quantity:,.2f}"  # type: ignore[attr-defined]


def _parse_amount(text: str) -> object:
    """Parse a display amount string back into an Amount dataclass.

    Accepts:  "£42.50"  "£-42.50"  "-£42.50"  "42.50 EUR"
    Raises ValueError for unrecognisable input.
    """
    from PyLedger.models import Amount  # noqa: PLC0415

    text = text.strip()
    if not text:
        raise ValueError("Empty amount string")

    # Detect and remove a leading minus sign before the commodity prefix.
    negative = text.startswith("-")
    if negative:
        text = text[1:]

    # Consume any leading non-digit characters as the commodity prefix (e.g. £, $).
    i = 0
    while i < len(text) and not text[i].isdigit() and text[i] != "-":
        i += 1
    commodity_prefix = text[:i]
    rest = text[i:]

    # Handle commodity-embedded minus (e.g. "£-42.50" — commodity already stripped).
    if rest.startswith("-"):
        negative = not negative
        rest = rest[1:]

    # Split "42.50 EUR" into numeric part and optional trailing commodity code.
    parts = rest.split()
    if len(parts) >= 2 and not parts[1][0].isdigit():
        qty_str, commodity_suffix = parts[0], parts[1]
    else:
        qty_str = parts[0] if parts else rest
        commodity_suffix = ""

    commodity = commodity_prefix or commodity_suffix
    quantity = Decimal(qty_str.replace(",", ""))
    if negative:
        quantity = -quantity

    return Amount(quantity=quantity, commodity=commodity)


class TransactionTable(Widget):
    """Tabular editing surface for hledger journal transactions.

    Rows map to postings within transactions. Transaction header rows show
    date, flag, and description; posting rows show account and amount.
    EditorDocument is the single source of truth; all mutations go through
    its update_transaction / save methods.

    Args:
        journal_path: Absolute path to the journal file being edited.
    """

    BINDINGS = [
        ("ctrl+s", "save", "Save"),
        ("shift+c", "toggle_cleared", "Toggle cleared"),
        ("ctrl+left", "prev_field", "Prev field"),
        ("ctrl+right", "next_field", "Next field"),
        ("ctrl+up", "prev_transaction", "Prev txn"),
        ("ctrl+down", "next_transaction", "Next txn"),
        ("escape", "cancel_edit", "Cancel edit"),
    ]

    DEFAULT_CSS = """
    TransactionTable {
        layout: vertical;
    }
    TransactionTable > DataTable {
        height: 1fr;
    }
    TransactionTable > Input {
        height: 3;
        display: none;
    }
    TransactionTable > Input.editing {
        display: block;
    }
    """

    class SaveCompleted(Message):
        """Posted after a successful Ctrl+S save so the sidebar can refresh."""

    def __init__(self, journal_path: Path) -> None:
        """Initialise with the resolved absolute journal file path.

        Args:
            journal_path: Absolute path to the .journal or .ledger file to edit.
        """
        super().__init__()
        self.journal_path = journal_path
        self._row_meta: list[_RowMeta] = []
        self._editing: bool = False
        self._edit_coord: Coordinate | None = None
        self._doc = None  # set by _load() after mount

    def compose(self) -> ComposeResult:
        """Render the transaction DataTable and a hidden edit Input bar."""
        table = DataTable()
        table.cursor_type = "cell"
        yield table
        yield Input(id="cell_input", placeholder="Edit — Enter to confirm, Escape to cancel")

    def on_mount(self) -> None:
        """Load the journal and populate the table on first render."""
        self._load()

    # ------------------------------------------------------------------
    # Data loading and table construction
    # ------------------------------------------------------------------

    def _load(self) -> None:
        import PyLedger  # noqa: PLC0415

        self._doc = PyLedger.EditorDocument(str(self.journal_path))
        self._rebuild_table()

    def _rebuild_table(self, *, preserve_cursor: bool = False) -> None:
        """Clear and repopulate the DataTable from the current EditorDocument state."""
        table = self.query_one(DataTable)
        saved_row = table.cursor_row if preserve_cursor else 0
        saved_col = table.cursor_column if preserve_cursor else 0

        table.clear(columns=True)
        table.add_columns("Date", "*", "Description", "Account", "Amount")
        self._row_meta = []

        for txn_idx, txn in enumerate(self._doc.journal.transactions):
            if txn_idx > 0:
                table.add_row("", "", "", "", "", key=f"sep_{txn_idx}")
                self._row_meta.append(_RowMeta(txn_idx=txn_idx, posting_idx=-1))

            table.add_row(
                str(txn.date),
                _flag_str(txn),
                txn.description,
                "",
                "",
                key=f"hdr_{txn_idx}",
            )
            self._row_meta.append(_RowMeta(txn_idx=txn_idx, posting_idx=None))

            for p_idx, posting in enumerate(txn.postings):
                amount_str = _fmt_amount(posting.amount) if posting.amount is not None else ""
                table.add_row(
                    "", "", "",
                    posting.account,
                    amount_str,
                    key=f"post_{txn_idx}_{p_idx}",
                )
                self._row_meta.append(_RowMeta(txn_idx=txn_idx, posting_idx=p_idx))

        if preserve_cursor and self._row_meta:
            table.move_cursor(
                row=min(saved_row, len(self._row_meta) - 1),
                column=saved_col,
            )

    # ------------------------------------------------------------------
    # Cursor helpers
    # ------------------------------------------------------------------

    def _current_meta(self) -> _RowMeta | None:
        """Return the _RowMeta for the DataTable's current cursor row, or None."""
        table = self.query_one(DataTable)
        row = table.cursor_row
        if 0 <= row < len(self._row_meta):
            return self._row_meta[row]
        return None

    # ------------------------------------------------------------------
    # Cell editing
    # ------------------------------------------------------------------

    def on_data_table_cell_selected(self, event: DataTable.CellSelected) -> None:
        """Open the edit Input when the user presses Enter on a cell."""
        self._start_edit(event.coordinate)

    def _start_edit(self, coord: Coordinate) -> None:
        if self._editing or not (0 <= coord.row < len(self._row_meta)):
            return

        meta = self._row_meta[coord.row]
        if meta.posting_idx == -1:
            return

        col = coord.column
        editable = _HEADER_EDITABLE if meta.posting_idx is None else _POSTING_EDITABLE
        if col not in editable:
            return

        table = self.query_one(DataTable)
        current_value = str(table.get_cell_at(coord) or "").strip()

        cell_input = self.query_one("#cell_input", Input)
        cell_input.value = current_value
        cell_input.add_class("editing")
        cell_input.focus()
        self._editing = True
        self._edit_coord = coord

    def on_input_submitted(self, event: Input.Submitted) -> None:
        """Commit the edit when the user presses Enter in the Input bar."""
        if not self._editing or self._edit_coord is None:
            return
        event.stop()
        self._commit_edit(event.value)

    def _commit_edit(self, new_value: str) -> None:
        coord = self._edit_coord
        meta = self._row_meta[coord.row]
        original = self._doc.journal.transactions[meta.txn_idx]
        col = coord.column

        try:
            if meta.posting_idx is None:  # header row
                if col == _COL_DATE:
                    updated = dataclasses.replace(
                        original, date=datetime.date.fromisoformat(new_value.strip())
                    )
                else:  # _COL_DESC
                    updated = dataclasses.replace(original, description=new_value.strip())
            else:  # posting row
                postings = list(original.postings)
                posting = postings[meta.posting_idx]
                if col == _COL_ACCOUNT:
                    new_posting = dataclasses.replace(posting, account=new_value.strip())
                else:  # _COL_AMOUNT
                    if not new_value.strip():
                        new_posting = dataclasses.replace(posting, amount=None)
                    else:
                        new_posting = dataclasses.replace(
                            posting, amount=_parse_amount(new_value.strip())
                        )
                postings[meta.posting_idx] = new_posting
                updated = dataclasses.replace(original, postings=postings)

            self._doc.update_transaction(original, updated)
        except (ValueError, InvalidOperation) as exc:
            self.app.notify(f"Invalid value: {exc}", severity="error")
            self._cancel_edit()
            return

        self._cancel_edit()
        self._rebuild_table(preserve_cursor=True)

    def _cancel_edit(self) -> None:
        cell_input = self.query_one("#cell_input", Input)
        cell_input.remove_class("editing")
        self.query_one(DataTable).focus()
        self._editing = False
        self._edit_coord = None

    # ------------------------------------------------------------------
    # Key actions
    # ------------------------------------------------------------------

    def action_cancel_edit(self) -> None:
        """Discard any in-progress edit and return focus to the DataTable."""
        if self._editing:
            self._cancel_edit()

    def action_toggle_cleared(self) -> None:
        """Cycle the selected transaction: uncleared → pending → cleared → uncleared.

        Uses Transaction.cleared and Transaction.pending booleans.
        Only the flag cell is refreshed — the full table is not rebuilt.
        """
        meta = self._current_meta()
        if meta is None or meta.posting_idx == -1:
            return

        original = self._doc.journal.transactions[meta.txn_idx]

        if not original.cleared and not original.pending:
            updated = dataclasses.replace(original, pending=True)
        elif original.pending:
            updated = dataclasses.replace(original, cleared=True, pending=False)
        else:
            updated = dataclasses.replace(original, cleared=False, pending=False)

        self._doc.update_transaction(original, updated)

        hdr_row_idx = next(
            i for i, m in enumerate(self._row_meta)
            if m.txn_idx == meta.txn_idx and m.posting_idx is None
        )
        self.query_one(DataTable).update_cell_at(
            Coordinate(hdr_row_idx, _COL_FLAG), _flag_str(updated)
        )

    def action_save(self) -> None:
        """Sort by date, write to disk, run basic checks, then post SaveCompleted."""
        import PyLedger  # noqa: PLC0415

        self._doc.journal.transactions.sort(key=lambda t: t.date)
        self._doc.save()

        for err in PyLedger.checks.run_basic_checks(self._doc.journal):
            self.app.notify(err.message, severity="warning")

        self._rebuild_table(preserve_cursor=True)
        self.post_message(self.SaveCompleted())
        self.app.notify("Saved", severity="information")

    def action_prev_field(self) -> None:
        """Move the cursor left to the previous editable column in the current row."""
        table = self.query_one(DataTable)
        meta = self._current_meta()
        if meta is None or meta.posting_idx == -1:
            return
        editable = sorted(_HEADER_EDITABLE if meta.posting_idx is None else _POSTING_EDITABLE)
        prev_cols = [c for c in editable if c < table.cursor_column]
        if prev_cols:
            table.move_cursor(column=prev_cols[-1])

    def action_next_field(self) -> None:
        """Move the cursor right to the next editable column in the current row."""
        table = self.query_one(DataTable)
        meta = self._current_meta()
        if meta is None or meta.posting_idx == -1:
            return
        editable = sorted(_HEADER_EDITABLE if meta.posting_idx is None else _POSTING_EDITABLE)
        next_cols = [c for c in editable if c > table.cursor_column]
        if next_cols:
            table.move_cursor(column=next_cols[0])

    def action_prev_transaction(self) -> None:
        """Jump the cursor to the header row of the previous transaction."""
        meta = self._current_meta()
        if meta is None or meta.txn_idx == 0:
            return
        target_row = next(
            (i for i, m in enumerate(self._row_meta)
             if m.txn_idx == meta.txn_idx - 1 and m.posting_idx is None),
            None,
        )
        if target_row is not None:
            self.query_one(DataTable).move_cursor(row=target_row)

    def action_next_transaction(self) -> None:
        """Jump the cursor to the header row of the next transaction."""
        meta = self._current_meta()
        if meta is None:
            return
        target_row = next(
            (i for i, m in enumerate(self._row_meta)
             if m.txn_idx == meta.txn_idx + 1 and m.posting_idx is None),
            None,
        )
        if target_row is not None:
            self.query_one(DataTable).move_cursor(row=target_row)
