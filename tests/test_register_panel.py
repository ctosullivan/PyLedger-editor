"""Tests for ledger_editor.widgets.register_panel."""

from decimal import Decimal
from pathlib import Path

from ledger_editor.app import LedgerApp
from ledger_editor.widgets.register_panel import RegisterPanel, _fmt_register_amount
from textual.widgets import DataTable

FIXTURES = Path(__file__).parent / "fixtures"


# ---------------------------------------------------------------------------
# Pure-function unit tests
# ---------------------------------------------------------------------------


class TestFmtRegisterAmount:
    """Unit tests for the _fmt_register_amount formatting helper."""

    def _amount(self, qty: str, commodity: str) -> object:
        from PyLedger.models import Amount

        return Amount(quantity=Decimal(qty), commodity=commodity)

    def test_prefix_commodity_positive(self) -> None:
        assert _fmt_register_amount(self._amount("42.50", "£")) == "£42.50"

    def test_prefix_commodity_negative(self) -> None:
        assert _fmt_register_amount(self._amount("-42.50", "£")) == "-£42.50"

    def test_suffix_commodity(self) -> None:
        assert _fmt_register_amount(self._amount("42.50", "EUR")) == "42.50 EUR"

    def test_no_commodity(self) -> None:
        assert _fmt_register_amount(self._amount("42.50", "")) == "42.50"


# ---------------------------------------------------------------------------
# Async widget tests
# ---------------------------------------------------------------------------


class TestRegisterPanelWidget:
    """Async integration tests for RegisterPanel using Textual's test harness."""

    async def test_empty_state_on_mount(self) -> None:
        """On mount no account is selected and the table is empty."""
        app = LedgerApp(FIXTURES / "sample.journal")
        async with app.run_test(size=(120, 40)) as pilot:
            panel = pilot.app.query_one(RegisterPanel)
            assert panel._current_account is None
            assert panel.query_one("#register_table", DataTable).row_count == 0

    async def test_show_account_updates_label(self) -> None:
        """show_account() sets _current_account to the given name."""
        app = LedgerApp(FIXTURES / "sample.journal")
        async with app.run_test(size=(120, 40)) as pilot:
            panel = pilot.app.query_one(RegisterPanel)
            panel.show_account("expenses:food")
            await pilot.pause()

            assert panel._current_account == "expenses:food"

    async def test_show_account_loads_rows(self) -> None:
        """show_account() populates the DataTable after the worker completes."""
        app = LedgerApp(FIXTURES / "sample.journal")
        async with app.run_test(size=(120, 40)) as pilot:
            panel = pilot.app.query_one(RegisterPanel)
            panel.show_account("expenses:food")
            await pilot.pause(0.5)
            await pilot.pause()

            assert panel.query_one("#register_table", DataTable).row_count > 0

    async def test_show_account_limits_to_10_rows(self) -> None:
        """RegisterPanel shows at most 10 rows even when more exist."""
        app = LedgerApp(FIXTURES / "large.journal")
        async with app.run_test(size=(120, 40)) as pilot:
            panel = pilot.app.query_one(RegisterPanel)
            panel.show_account("expenses:food")
            await pilot.pause(0.5)
            await pilot.pause()

            assert panel.query_one("#register_table", DataTable).row_count <= 10

    async def test_show_none_clears_table(self) -> None:
        """show_account(None) empties the DataTable and resets _current_account."""
        app = LedgerApp(FIXTURES / "sample.journal")
        async with app.run_test(size=(120, 40)) as pilot:
            panel = pilot.app.query_one(RegisterPanel)
            panel.show_account("expenses:food")
            await pilot.pause(0.5)
            await pilot.pause()

            panel.show_account(None)
            await pilot.pause()

            assert panel.query_one("#register_table", DataTable).row_count == 0
            assert panel._current_account is None
