"""Persistent sidebar widget displaying account balances.

Fetches balances via journal.balance(tree=True) on app start and after every
Ctrl+S save. Renders as a scrollable Tree with one node per account.
"""

from __future__ import annotations

from decimal import Decimal
from pathlib import Path

from textual import work
from textual.app import ComposeResult
from textual.widget import Widget
from textual.widgets import Tree

__all__ = ["BalanceSidebar"]


def _fmt_amounts(amounts: dict[str, Decimal]) -> str:
    """Format a commodity→balance dict as a compact display string.

    Returns e.g. '£1,000.00' or '£500.00  EUR200.00' for multi-commodity.
    """
    return "  ".join(
        f"{commodity}{qty:,.2f}" for commodity, qty in sorted(amounts.items())
    )


class BalanceSidebar(Widget):
    """Scrollable account-balance tree displayed on the left of the editor.

    Refreshes asynchronously via a thread worker so the editing surface
    remains responsive during PyLedger I/O. Call refresh_balances() to
    trigger a reload; it is also called automatically on mount.

    Args:
        journal_path: Absolute path to the journal file being edited.
    """

    DEFAULT_CSS = """
    BalanceSidebar {
        layout: vertical;
    }
    BalanceSidebar > Tree {
        height: 1fr;
    }
    """

    def __init__(self, journal_path: Path) -> None:
        """Initialise with the resolved absolute journal file path.

        Args:
            journal_path: Absolute path to the .journal or .ledger file.
        """
        super().__init__()
        self.journal_path = journal_path

    def compose(self) -> ComposeResult:
        """Render an empty Tree that refresh_balances() populates."""
        tree: Tree[None] = Tree("Balances")
        tree.root.expand()
        yield tree

    def on_mount(self) -> None:
        """Trigger an initial balance fetch when the widget first appears."""
        self.refresh_balances()

    @work(thread=True)
    def refresh_balances(self) -> None:
        """Reload account balances from disk and rebuild the Tree.

        Runs in a background thread to avoid blocking the UI event loop.
        Schedules _render_tree() on the main thread via call_from_thread.
        """
        import PyLedger  # noqa: PLC0415

        journal = PyLedger.load(self.journal_path)
        rows = journal.balance(tree=True)
        self.app.call_from_thread(self._render_tree, rows)

    def _render_tree(self, rows: list) -> None:
        """Rebuild the Tree widget from a list of BalanceRow objects.

        Must be called on the main thread (use call_from_thread from workers).
        Each BalanceRow's depth drives the Tree indentation; only the leaf
        account segment is shown as the label to avoid path repetition.
        """
        tree = self.query_one(Tree)
        tree.root.remove_children()

        # node_map tracks the TreeNode for each full account path so that
        # deeper accounts can attach to the correct parent.
        node_map: dict[str, object] = {}

        for row in rows:
            parts = row.account.split(":")
            leaf_label = parts[-1]
            amount_str = _fmt_amounts(row.amounts)
            label = f"{leaf_label}  {amount_str}" if amount_str else leaf_label

            if row.depth == 0:
                parent = tree.root
            else:
                parent_key = ":".join(parts[:-1])
                parent = node_map.get(parent_key, tree.root)

            node = parent.add(label)  # type: ignore[union-attr]
            node.expand()
            node_map[row.account] = node
