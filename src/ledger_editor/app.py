"""Root Textual application for the ledger editor.

Composes the main layout: JournalEditor (text editing surface, left) and a
right panel containing BalanceSidebar (top) and RegisterPanel (bottom).
FilterPopup overlays on demand via Ctrl+Shift+F.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
from typing import ClassVar

# Ensure vendor/pyledger is on sys.path so 'import PyLedger' resolves to
# vendor/pyledger/pyLedger/ on Windows (case-insensitive filesystem).
_VENDOR = Path(__file__).parent.parent.parent.parent / "vendor" / "pyledger"
if _VENDOR.exists() and str(_VENDOR) not in sys.path:
    sys.path.insert(0, str(_VENDOR))

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.widgets import Footer, Header

from ledger_editor.themes import register_all
from ledger_editor.themes.monokai_pro import THEME_NAME
from ledger_editor.utils.file_resolver import resolve_journal_file
from ledger_editor.widgets.balance_sidebar import BalanceSidebar
from ledger_editor.widgets.filter_popup import FilterPopup
from ledger_editor.widgets.ledger_textarea import LedgerTextArea
from ledger_editor.widgets.register_panel import RegisterPanel
from ledger_editor.widgets.transaction_table import JournalEditor

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
    COMMAND_PALETTE_DISPLAY: ClassVar[str] = "Ctrl+P"
    CSS_PATH = ["themes/monokai_pro.tcss"]
    BINDINGS = [
        Binding("ctrl+shift+f", "toggle_filter", "Filter", priority=True, key_display="Ctrl+Shift+F"),
    ]
    CSS = """
    Screen {
        layout: horizontal;
    }
    JournalEditor {
        width: 65%;
    }
    #right_panel {
        width: 35%;
        min-width: 40;
        border-left: solid $primary;
    }
    BalanceSidebar {
        height: 1fr;
        border-bottom: solid $primary;
    }
    RegisterPanel {
        height: 1fr;
    }
    """

    def __init__(self, journal_path: Path) -> None:
        """Initialise the app with a resolved journal file path.

        Args:
            journal_path: Absolute path to the .journal or .ledger file to edit.
        """
        super().__init__()
        self.journal_path = journal_path

    def on_mount(self) -> None:
        """Register bundled themes and activate Monokai Pro as the default."""
        editor = self.query_one(JournalEditor)
        ledger_textarea = editor.query_one("#journal_textarea", LedgerTextArea)
        register_all(self, ledger_textarea)
        if os.environ.get("TEXTUAL_THEME") is None:
            self.theme = THEME_NAME

    def compose(self) -> ComposeResult:
        """Build the initial widget tree."""
        yield Header()
        yield JournalEditor(self.journal_path)
        with Vertical(id="right_panel"):
            yield BalanceSidebar(self.journal_path)
            yield RegisterPanel(self.journal_path)
        yield Footer()

    def on_journal_editor_save_completed(self) -> None:
        """Refresh account balances whenever the journal is saved."""
        self.query_one(BalanceSidebar).refresh_balances()

    def on_journal_editor_cursor_account_changed(
        self, event: JournalEditor.CursorAccountChanged
    ) -> None:
        """Update the register panel when the cursor moves to a new account."""
        results = self.query(RegisterPanel)
        if results:
            results.first().show_account(event.account)

    def on_balance_sidebar_account_selected(
        self, event: BalanceSidebar.AccountSelected
    ) -> None:
        """Update the register panel when the user selects an account in the sidebar."""
        results = self.query(RegisterPanel)
        if results:
            results.first().show_account(event.account)

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
