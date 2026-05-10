"""Tests for ledger_editor.widgets.balance_sidebar."""

from pathlib import Path

from ledger_editor.app import LedgerApp
from ledger_editor.widgets.balance_sidebar import BalanceSidebar, _fmt_amounts

FIXTURES = Path(__file__).parent / "fixtures"


class TestFmtAmounts:
    """Unit tests for the _fmt_amounts formatting helper."""

    def test_single_commodity(self) -> None:
        from decimal import Decimal

        assert _fmt_amounts({"£": Decimal("1000.00")}) == "£1,000.00"

    def test_multi_commodity_sorted(self) -> None:
        from decimal import Decimal

        result = _fmt_amounts({"USD": Decimal("50.00"), "EUR": Decimal("30.00")})
        assert result == "EUR30.00  USD50.00"

    def test_empty_dict(self) -> None:
        assert _fmt_amounts({}) == ""


class TestBalanceSidebarWidget:
    """Async integration tests for BalanceSidebar using Textual's test harness."""

    async def test_refresh_balances_populates_tree(self) -> None:
        """After refresh, the Tree should have nodes for the accounts in sample.journal."""
        app = LedgerApp(FIXTURES / "sample.journal")
        async with app.run_test(size=(120, 30)) as pilot:
            sidebar = pilot.app.query_one(BalanceSidebar)
            # Wait for the background thread worker to complete and the UI to update.
            await pilot.pause(0.5)
            await pilot.pause()

            from textual.widgets import Tree

            tree = sidebar.query_one(Tree)
            # Tree root should have children after a successful balance fetch.
            assert len(list(tree.root.children)) > 0

    async def test_sidebar_has_tree_widget(self) -> None:
        """BalanceSidebar always contains a Tree widget."""
        app = LedgerApp(FIXTURES / "sample.journal")
        async with app.run_test(size=(120, 30)) as pilot:
            sidebar = pilot.app.query_one(BalanceSidebar)
            from textual.widgets import Tree

            assert sidebar.query_one(Tree) is not None

    async def test_node_selected_posts_account_selected(self) -> None:
        """Selecting a tree node posts AccountSelected with the account path."""
        app = LedgerApp(FIXTURES / "sample.journal")
        async with app.run_test(size=(120, 30)) as pilot:
            sidebar = pilot.app.query_one(BalanceSidebar)
            await pilot.pause(0.5)
            await pilot.pause()

            received: list[BalanceSidebar.AccountSelected] = []
            _orig = sidebar.post_message

            def _spy(msg: object) -> bool:
                if isinstance(msg, BalanceSidebar.AccountSelected):
                    received.append(msg)
                return _orig(msg)  # type: ignore[arg-type]

            sidebar.post_message = _spy  # type: ignore[method-assign]

            from textual.widgets import Tree

            tree = sidebar.query_one(Tree)
            first_node = next(iter(tree.root.children), None)
            assert first_node is not None, "Tree has no nodes after balance fetch"

            # Simulate node selection
            sidebar.on_tree_node_selected(Tree.NodeSelected(first_node))
            await pilot.pause()

        assert received, "AccountSelected was not posted"
        assert received[0].account is not None
