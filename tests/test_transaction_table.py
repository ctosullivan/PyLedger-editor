"""Tests for ledger_editor.widgets.transaction_table."""

from decimal import Decimal
from pathlib import Path
import shutil

import pytest

from ledger_editor.app import LedgerApp
from ledger_editor.widgets.transaction_table import (
    TransactionTable,
    _flag_str,
    _fmt_amount,
    _parse_amount,
)

FIXTURES = Path(__file__).parent / "fixtures"


# ---------------------------------------------------------------------------
# Pure-function unit tests (no Textual event loop required)
# ---------------------------------------------------------------------------


class TestParseAmount:
    """Unit tests for the _parse_amount helper."""

    def test_commodity_prefix(self) -> None:
        amount = _parse_amount("£42.50")
        assert amount.commodity == "£"
        assert amount.quantity == Decimal("42.50")

    def test_negative_leading_sign(self) -> None:
        amount = _parse_amount("-£42.50")
        assert amount.commodity == "£"
        assert amount.quantity == Decimal("-42.50")

    def test_negative_embedded_after_commodity(self) -> None:
        amount = _parse_amount("£-42.50")
        assert amount.commodity == "£"
        assert amount.quantity == Decimal("-42.50")

    def test_trailing_commodity_code(self) -> None:
        amount = _parse_amount("42.50 EUR")
        assert amount.commodity == "EUR"
        assert amount.quantity == Decimal("42.50")

    def test_thousands_separator_stripped(self) -> None:
        amount = _parse_amount("£1,000.00")
        assert amount.quantity == Decimal("1000.00")

    def test_empty_raises(self) -> None:
        with pytest.raises(ValueError):
            _parse_amount("")

    def test_invalid_text_raises(self) -> None:
        with pytest.raises(Exception):
            _parse_amount("not-a-number")


class TestFlagStr:
    """Unit tests for the _flag_str helper."""

    def _txn(self, cleared: bool, pending: bool) -> object:
        class T:
            pass

        t = T()
        t.cleared = cleared  # type: ignore[attr-defined]
        t.pending = pending  # type: ignore[attr-defined]
        return t

    def test_cleared_returns_asterisk(self) -> None:
        assert _flag_str(self._txn(cleared=True, pending=False)) == "*"

    def test_pending_returns_exclamation(self) -> None:
        assert _flag_str(self._txn(cleared=False, pending=True)) == "!"

    def test_uncleared_returns_space(self) -> None:
        assert _flag_str(self._txn(cleared=False, pending=False)) == " "


class TestFmtAmount:
    """Unit tests for the _fmt_amount helper."""

    def test_positive_amount(self) -> None:
        from PyLedger.models import Amount

        assert _fmt_amount(Amount(Decimal("42.50"), "£")) == "£42.50"

    def test_negative_amount(self) -> None:
        from PyLedger.models import Amount

        assert _fmt_amount(Amount(Decimal("-1000.00"), "£")) == "£-1,000.00"


# ---------------------------------------------------------------------------
# Async widget tests (require Textual run_test harness)
# ---------------------------------------------------------------------------


class TestTransactionTableWidget:
    """Async integration tests for TransactionTable using Textual's test harness."""

    async def test_row_meta_structure(self) -> None:
        """sample.journal: 2 txns × 2 postings → 7 rows (1 sep + 2 hdr + 4 posting)."""
        app = LedgerApp(FIXTURES / "sample.journal")
        async with app.run_test(size=(120, 30)) as pilot:
            table = pilot.app.query_one(TransactionTable)
            assert len(table._row_meta) == 7

    async def test_first_transaction_header_at_row_zero(self) -> None:
        app = LedgerApp(FIXTURES / "sample.journal")
        async with app.run_test(size=(120, 30)) as pilot:
            table = pilot.app.query_one(TransactionTable)
            meta = table._row_meta[0]
            assert meta.txn_idx == 0
            assert meta.posting_idx is None

    async def test_separator_row_between_transactions(self) -> None:
        app = LedgerApp(FIXTURES / "sample.journal")
        async with app.run_test(size=(120, 30)) as pilot:
            table = pilot.app.query_one(TransactionTable)
            separator_rows = [m for m in table._row_meta if m.posting_idx == -1]
            assert len(separator_rows) == 1

    async def test_toggle_cleared_uncleared_to_pending(self) -> None:
        """Groceries (txn 1) starts uncleared; one Shift+C press → pending."""
        app = LedgerApp(FIXTURES / "sample.journal")
        async with app.run_test(size=(120, 30)) as pilot:
            table = pilot.app.query_one(TransactionTable)
            from textual.widgets import DataTable

            # Row 4 = header for txn 1 (after: hdr_0, post_0_0, post_0_1, sep_1)
            table.query_one(DataTable).move_cursor(row=4)
            table.action_toggle_cleared()

            txn = table._doc.journal.transactions[1]
            assert txn.pending is True
            assert txn.cleared is False

    async def test_toggle_cleared_full_cycle(self) -> None:
        """Three Shift+C presses cycle back to the original uncleared state."""
        app = LedgerApp(FIXTURES / "sample.journal")
        async with app.run_test(size=(120, 30)) as pilot:
            table = pilot.app.query_one(TransactionTable)
            from textual.widgets import DataTable

            table.query_one(DataTable).move_cursor(row=4)

            txn = table._doc.journal.transactions[1]
            assert not txn.cleared and not txn.pending

            table.action_toggle_cleared()  # → pending
            txn = table._doc.journal.transactions[1]
            assert txn.pending and not txn.cleared

            table.action_toggle_cleared()  # → cleared
            txn = table._doc.journal.transactions[1]
            assert txn.cleared and not txn.pending

            table.action_toggle_cleared()  # → uncleared
            txn = table._doc.journal.transactions[1]
            assert not txn.cleared and not txn.pending

    async def test_save_sorts_transactions_by_date(self, tmp_path: Path) -> None:
        """Saving re-orders transactions into ascending date order."""
        out_of_order = tmp_path / "test.journal"
        shutil.copy(FIXTURES / "sample.journal", out_of_order)

        app = LedgerApp(out_of_order)
        async with app.run_test(size=(120, 30)) as pilot:
            table = pilot.app.query_one(TransactionTable)
            # Swap dates so txn 0 (2024-01-10) comes after txn 1 (2024-01-15)
            import dataclasses
            import datetime

            txns = table._doc.journal.transactions
            t0, t1 = txns[0], txns[1]
            table._doc.update_transaction(t0, dataclasses.replace(t0, date=datetime.date(2024, 1, 20)))

            table.action_save()
            await pilot.pause()

            saved_dates = [t.date for t in table._doc.journal.transactions]
            assert saved_dates == sorted(saved_dates)
