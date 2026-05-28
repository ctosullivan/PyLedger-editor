"""Root Textual application for the ledger editor.

Composes the main layout: a file-path bar below the Header, then JournalEditor
(full-width editing surface). FilterPopup overlays on demand via Ctrl+Shift+P.
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
from textual.css.query import NoMatches
from textual.widgets import Footer, Header, Static

from ledger_editor.themes import register_all
from ledger_editor.themes.monokai_pro import THEME_NAME
from ledger_editor.utils.file_resolver import resolve_journal_file
from ledger_editor.widgets.filter_popup import FilterPopup
from ledger_editor.widgets.transaction_table import JournalEditor

__all__ = ["LedgerApp", "main"]


class LedgerApp(App[None]):
    """Top-level Textual application for the plain-text ledger editor."""

    TITLE = "Ledger Editor"
    COMMAND_PALETTE_DISPLAY: ClassVar[str] = "Ctrl+P"
    CSS_PATH = ["themes/monokai_pro.tcss"]
    BINDINGS = [
        Binding("ctrl+o", "toggle_filter", "Filter transactions",
                priority=True, key_display="Ctrl+O"),
    ]
    CSS = """
    Screen {
        layout: horizontal;
    }
    #file-path-bar {
        dock: top;
        height: 1;
        background: $surface;
        color: $text-muted;
        padding: 0 1;
    }
    JournalEditor {
        width: 1fr;
        layout: vertical;
    }
    ViewFilterBar {
        dock: top;
        height: 1;
        background: $surface;
        color: $text-muted;
        padding: 0 1;
    }
    SearchBar {
        dock: bottom;
        height: 3;
        background: $surface;
        border-top: solid $primary;
        display: none;
        layout: horizontal;
        padding: 0 1;
    }
    SearchBar Input {
        width: 1fr;
        height: 1;
        background: $panel;
        color: $text;
        border: none;
    }
    SearchBar #match-counter {
        width: auto;
        padding: 0 1;
        color: $text-muted;
    }
    SearchBar Button {
        width: auto;
        min-width: 3;
        height: 1;
        border: none;
        padding: 0 1;
    }
    """

    def __init__(self, journal_path: Path) -> None:
        """Initialise the app with a resolved journal file path."""
        super().__init__()
        self.journal_path = journal_path

    def on_mount(self) -> None:
        """Register bundled themes, activate Monokai Pro, and populate file-path bar."""
        from ledger_editor.widgets.ledger_textarea import LedgerTextArea  # noqa: PLC0415

        editor = self.query_one(JournalEditor)
        ledger_textarea = editor.query_one("#journal_textarea", LedgerTextArea)
        register_all(self, ledger_textarea)
        if os.environ.get("TEXTUAL_THEME") is None:
            self.theme = THEME_NAME
        self._update_file_path_bar(modified=False)

    def compose(self) -> ComposeResult:
        """Build the initial widget tree."""
        yield Header()
        yield Static("", id="file-path-bar")
        yield JournalEditor(self.journal_path)
        yield Footer()

    def _update_file_path_bar(self, modified: bool) -> None:
        """Refresh the path bar label, appending '· modified' when unsaved."""
        path_str = str(Path(self.journal_path).resolve())
        text = f"{path_str}  ·  modified" if modified else path_str
        try:
            self.query_one("#file-path-bar", Static).update(text)
        except NoMatches:
            pass

    # ------------------------------------------------------------------
    # Message handlers
    # ------------------------------------------------------------------

    def on_journal_editor_file_modified_changed(
        self, event: JournalEditor.FileModifiedChanged
    ) -> None:
        """Update the file-path bar with the modified indicator."""
        self._update_file_path_bar(modified=event.modified)

    def action_toggle_filter(self) -> None:
        """Open or close the transaction filter popup (Ctrl+Shift+P)."""
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
    """Entry point wired up in pyproject.toml [project.scripts]."""
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
