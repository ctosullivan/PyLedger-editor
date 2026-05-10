"""Root Textual application for the ledger editor.

Composes the main layout: BalanceSidebar (persistent left panel) and
TransactionTable (central editing surface). FilterPopup overlays on demand.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Ensure vendor/pyledger is on sys.path so 'import PyLedger' resolves to
# vendor/pyledger/pyLedger/ on Windows (case-insensitive filesystem).
_VENDOR = Path(__file__).parent.parent.parent.parent / "vendor" / "pyledger"
if _VENDOR.exists() and str(_VENDOR) not in sys.path:
    sys.path.insert(0, str(_VENDOR))

from textual.app import App, ComposeResult
from textual.widgets import Footer, Header

from ledger_editor.utils.file_resolver import resolve_journal_file
from ledger_editor.widgets.balance_sidebar import BalanceSidebar
from ledger_editor.widgets.filter_popup import FilterPopup
from ledger_editor.widgets.transaction_table import TransactionTable

__all__ = ["LedgerApp", "main"]


class LedgerApp(App[None]):
    """Top-level Textual application for the plain-text ledger editor.

    Keyboard bindings are split across two mixin modules:
    - ledger_editor.keybindings.office   (MS Office / Excel conventions)
    - ledger_editor.keybindings.emacs_ledger (Emacs Ledger-mode conventions)

    Both are wired up in the CSS binding declarations; the action handlers
    live in those modules and are composed into this class via mixins once
    implemented.
    """

    TITLE = "Ledger Editor"
    CSS = """
    Screen {
        layout: horizontal;
    }
    BalanceSidebar {
        width: 30;
        min-width: 20;
        border-right: solid $primary;
    }
    TransactionTable {
        width: 1fr;
    }
    """

    def __init__(self, journal_path: Path) -> None:
        """Initialise the app with a resolved journal file path.

        Args:
            journal_path: Absolute path to the .journal or .ledger file to edit.
        """
        super().__init__()
        self.journal_path = journal_path

    def compose(self) -> ComposeResult:
        """Build the initial widget tree."""
        yield Header()
        yield BalanceSidebar(self.journal_path)
        yield TransactionTable(self.journal_path)
        yield Footer()

    def action_toggle_filter(self) -> None:
        """Open or close the transaction filter popup (Ctrl+Shift+F)."""
        existing = self.query(FilterPopup)
        if existing:
            existing.first().remove()
        else:
            self.mount(FilterPopup())


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse CLI arguments for the ledger-editor entry point."""
    parser = argparse.ArgumentParser(
        prog="ledger-editor",
        description="Terminal-based plain-text ledger editor (hledger format).",
    )
    parser.add_argument(
        "file",
        nargs="?",
        metavar="FILE",
        help="Path to the .journal or .ledger file to edit.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    """Entry point wired up in pyproject.toml [project.scripts].

    Resolves the journal file via CLI argument → $LEDGER_FILE → ~/.hledger.journal
    → interactive prompt, then launches the Textual app.
    """
    args = _parse_args(argv)
    journal_path = resolve_journal_file(args.file)
    if journal_path is None:
        print(
            "No journal file found. Pass a path as an argument, set $LEDGER_FILE, "
            "or create ~/.hledger.journal.",
            file=sys.stderr,
        )
        sys.exit(1)
    app = LedgerApp(journal_path)
    app.run()
