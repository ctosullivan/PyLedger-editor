"""Root Textual application for the ledger editor.

Composes the main layout: a file-path bar below the Header, then JournalEditor
(full-width editing surface). FilterPopup overlays on demand via Ctrl+Shift+P.
"""

from __future__ import annotations

import argparse
import os
import re
import sys
from pathlib import Path
from typing import ClassVar

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.css.query import NoMatches
from textual.widgets import Footer, Header, Static

from ledgerkit_editor.themes import VALID_THEMES, register_all
from ledgerkit_editor.themes.monokai_pro import THEME_NAME
from ledgerkit_editor.utils.file_resolver import resolve_journal_file
from ledgerkit_editor.widgets.filter_popup import FilterPopup
from ledgerkit_editor.widgets.transaction_table import JournalEditor

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

    def __init__(
        self,
        journal_path: Path,
        start_line: int | None = None,
        theme_name: str | None = None,
    ) -> None:
        """Initialise the app with a resolved journal file path.

        Args:
            journal_path: Resolved path to the .journal or .ledger file.
            start_line: 1-indexed line to place the cursor on after open.
            theme_name: Registered theme name to activate; defaults to monokai-pro.
        """
        super().__init__()
        self.journal_path = journal_path
        self._start_line = start_line
        self._theme_name = theme_name

    def on_mount(self) -> None:
        """Register bundled themes, activate Monokai Pro, and populate file-path bar."""
        from ledgerkit_editor.widgets.ledger_textarea import LedgerTextArea  # noqa: PLC0415

        editor = self.query_one(JournalEditor)
        ledger_textarea = editor.query_one("#journal_textarea", LedgerTextArea)
        register_all(self, ledger_textarea)
        if os.environ.get("TEXTUAL_THEME") is None:
            self.theme = self._theme_name or THEME_NAME
        self._update_file_path_bar(modified=False)

    def compose(self) -> ComposeResult:
        """Build the initial widget tree."""
        yield Header()
        yield Static("", id="file-path-bar")
        yield JournalEditor(self.journal_path, start_line=self._start_line)
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
    raw = list(sys.argv[1:] if argv is None else argv)

    # Extract +N tokens before argparse; it does not handle the bare + prefix.
    # +N is the traditional $EDITOR convention (vi, emacs) used by shell
    # scripts and tools that invoke editors via: $EDITOR +N file.
    #
    # Purpose: match a bare "+<digits>" token anywhere in argv.
    # Group 1: the decimal line number.
    # Edge cases: "+0" matches (clamped to row 0 at use-site); "+N file"
    #             adjacent to a filename leaves the filename intact.
    plus_line: int | None = None
    filtered: list[str] = []
    for token in raw:
        m = re.fullmatch(r"\+(\d+)", token)
        if m:
            plus_line = int(m.group(1))
        else:
            filtered.append(token)

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
    parser.add_argument(
        "--line",
        type=int,
        metavar="N",
        default=None,
        help="Open with cursor at line N (1-indexed). Also accepts +N positional form.",
    )
    parser.add_argument(
        "--theme",
        metavar="THEME",
        default=None,
        choices=sorted(VALID_THEMES),
        help="Color theme to activate at startup (default: monokai-pro).",
    )
    args = parser.parse_args(filtered)
    # --line takes precedence; +N is the fallback when --line is absent.
    if args.line is None and plus_line is not None:
        args.line = plus_line
    return args


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
    app = LedgerApp(journal_path, start_line=args.line, theme_name=args.theme)
    app.run()
