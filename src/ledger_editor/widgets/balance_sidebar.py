"""Persistent sidebar widget displaying account balances.

Fetches balances via journal.balance(tree=True) on app start and after every
Ctrl+S save. Renders as a scrollable Tree with one node per account. Selecting
a node posts AccountSelected so the register panel can update.
"""

from __future__ import annotations

from decimal import Decimal
from pathlib import Path

from textual import work
from textual.app import ComposeResult
from textual.binding import Binding
from textual.message import Message
from textual.widget import Widget
from textual.widgets import TextArea, Tree

__all__ = ["BalanceSidebar"]


def _fmt_amounts(amounts: dict[str, Decimal]) -> str:
    """Format a commodity→balance dict as a compact display string.

    Returns e.g. '£1,000.00' or '£500.00  EUR200.00' for multi-commodity.
    """
    return "  ".join(
        f"{commodity}{qty:,.2f}" for commodity, qty in sorted(amounts.items())
    )


class BalanceSidebar(Widget):
    """Scrollable account-balance tree displayed on the right panel of the editor.

    Refreshes asynchronously via a thread worker so the editing surface
    remains responsive during PyLedger I/O. Call refresh_balances() to
    trigger a reload; it is also called automatically on mount.

    Selecting a tree node posts AccountSelected so downstream widgets (e.g.
    RegisterPanel) can update to show that account's register.

    Args:
        journal_path: Absolute path to the journal file being edited.
    """

    DEFAULT_CSS = """
    BalanceSidebar {
        layout: vertical;
    }
    BalanceSidebar > Tree {
        height: 1fr;
        padding: 0 1;
    }
    """

    BINDINGS = [
        Binding("tab", "focus_next_panel", "Focus register", show=False, priority=True),
        Binding("shift+tab", "focus_prev_panel", "Focus editor", show=False, priority=True),
    ]

    class AccountSelected(Message):
        """Posted when the user selects an account node in the balance tree."""

        def __init__(self, account: str | None) -> None:
            super().__init__()
            self.account = account

    def __init__(self, journal_path: Path) -> None:
        """Initialise with the resolved absolute journal file path.

        Args:
            journal_path: Absolute path to the .journal or .ledger file.
        """
        super().__init__()
        self.journal_path = journal_path

    def compose(self) -> ComposeResult:
        """Render an empty Tree that refresh_balances() populates."""
        tree: Tree[str | None] = Tree("Balances")
        tree.root.expand()
        yield tree

    def on_mount(self) -> None:
        """Trigger an initial balance fetch when the widget first appears."""
        self.refresh_balances()

    def on_tree_node_selected(self, event: Tree.NodeSelected) -> None:
        """Post AccountSelected with the full account path of the clicked node."""
        self.post_message(self.AccountSelected(event.node.data))

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
        account segment is shown as the label to avoid path repetition. The
        full account path is stored as node data for AccountSelected messages.
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

            node = parent.add(label, data=row.account)  # type: ignore[union-attr]
            node.expand()
            node_map[row.account] = node

    def action_focus_next_panel(self) -> None:
        """Move focus forward: BalanceSidebar → RegisterPanel DataTable."""
        from ledger_editor.widgets.register_panel import RegisterPanel  # noqa: PLC0415
        from textual.widgets import DataTable

        self.app.query_one(RegisterPanel).query_one(DataTable).focus()

    def action_focus_prev_panel(self) -> None:
        """Move focus backward: BalanceSidebar → JournalEditor TextArea."""
        self.app.query_one("#journal_textarea", TextArea).focus()
