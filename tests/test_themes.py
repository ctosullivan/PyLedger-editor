"""Integration tests for LedgerTextArea theming and syntax highlighting.

These tests require the Textual event loop (pytest-asyncio, asyncio_mode=auto).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from ledgerkit_editor.app import LedgerApp
from ledgerkit_editor.highlighting import tokens
from ledgerkit_editor.themes.monokai_pro import TEXTAREA_THEME_NAME, THEME_NAME
from ledgerkit_editor.widgets.ledger_textarea import LedgerTextArea
from ledgerkit_editor.widgets.transaction_table import JournalEditor

FIXTURES = Path(__file__).parent / "fixtures"

SAMPLE_JOURNAL = (
    "2024-01-10 * Cleared transaction\n"
    "    expenses:food    £42.00\n"
    "    assets:bank\n"
    "\n"
    "2024-01-15 ! Pending transaction\n"
    "    expenses:rent    £500.00\n"
    "    assets:bank\n"
    "\n"
    "2024-01-20 Uncleared transaction\n"
    "    expenses:misc    £10.00\n"
    "    assets:bank\n"
)


@pytest.fixture
def journal_file(tmp_path: Path) -> Path:
    """Write a sample journal to a temp file and return its path."""
    p = tmp_path / "test.journal"
    p.write_text(SAMPLE_JOURNAL, encoding="utf-8")
    return p


class TestLedgerTextAreaHighlights:
    """Verify that _highlights is populated with ledger token spans."""

    async def test_date_span_in_highlights(self, journal_file: Path) -> None:
        """After loading a journal, _highlights must contain a ledger.date span."""
        app = LedgerApp(journal_file)
        async with app.run_test(size=(120, 30)) as pilot:
            editor = pilot.app.query_one(JournalEditor)
            textarea = editor.query_one("#journal_textarea", LedgerTextArea)
            await pilot.pause()

            # Find a header line index
            lines = textarea.text.splitlines()
            header_idx = next(
                i for i, l in enumerate(lines)
                if "Cleared transaction" in l
            )
            line_spans = textarea._highlights.get(header_idx, [])
            token_names = {span[2] for span in line_spans}
            assert tokens.DATE in token_names

    async def test_no_block_spans_in_cleared_posting(self, journal_file: Path) -> None:
        """Block background tinting has been removed — no block tokens in highlights."""
        app = LedgerApp(journal_file)
        async with app.run_test(size=(120, 30)) as pilot:
            editor = pilot.app.query_one(JournalEditor)
            textarea = editor.query_one("#journal_textarea", LedgerTextArea)
            await pilot.pause()

            lines = textarea.text.splitlines()
            posting_idx = next(
                i for i, l in enumerate(lines)
                if l.startswith("    expenses:food")
            )
            line_spans = textarea._highlights.get(posting_idx, [])
            token_names = {span[2] for span in line_spans}
            assert tokens.BLOCK_CLEARED not in token_names
            assert tokens.BLOCK_PENDING not in token_names
            assert tokens.BLOCK_UNCLEARED not in token_names

    async def test_no_block_spans_in_pending_posting(self, journal_file: Path) -> None:
        """Block background tinting has been removed — no block tokens in highlights."""
        app = LedgerApp(journal_file)
        async with app.run_test(size=(120, 30)) as pilot:
            editor = pilot.app.query_one(JournalEditor)
            textarea = editor.query_one("#journal_textarea", LedgerTextArea)
            await pilot.pause()

            lines = textarea.text.splitlines()
            posting_idx = next(
                i for i, l in enumerate(lines)
                if l.startswith("    expenses:rent")
            )
            line_spans = textarea._highlights.get(posting_idx, [])
            token_names = {span[2] for span in line_spans}
            assert tokens.BLOCK_CLEARED not in token_names
            assert tokens.BLOCK_PENDING not in token_names
            assert tokens.BLOCK_UNCLEARED not in token_names


class TestLedgerTextAreaThemeSwitching:
    """Verify _rebuild_ledger_theme() selects the correct TextAreaTheme."""

    async def test_monokai_pro_default_theme(self, journal_file: Path) -> None:
        """Default launch with no TEXTUAL_THEME env var uses monokai-pro-ledger."""
        app = LedgerApp(journal_file)
        async with app.run_test(size=(120, 30)) as pilot:
            await pilot.pause()
            editor = pilot.app.query_one(JournalEditor)
            textarea = editor.query_one("#journal_textarea", LedgerTextArea)
            assert textarea.theme == TEXTAREA_THEME_NAME

    async def test_switch_to_textual_dark_uses_bridge(
        self, journal_file: Path
    ) -> None:
        """After switching app.theme to textual-dark, TextArea uses the bridge theme."""
        app = LedgerApp(journal_file)
        async with app.run_test(size=(120, 30)) as pilot:
            await pilot.pause()
            pilot.app.theme = "textual-dark"
            await pilot.pause()

            editor = pilot.app.query_one(JournalEditor)
            textarea = editor.query_one("#journal_textarea", LedgerTextArea)
            assert textarea.theme == "ledger"

    async def test_switch_back_to_monokai_restores_static_theme(
        self, journal_file: Path
    ) -> None:
        """Switching back to monokai-pro re-activates the static TextAreaTheme."""
        app = LedgerApp(journal_file)
        async with app.run_test(size=(120, 30)) as pilot:
            await pilot.pause()
            pilot.app.theme = "textual-dark"
            await pilot.pause()
            pilot.app.theme = THEME_NAME
            await pilot.pause()

            editor = pilot.app.query_one(JournalEditor)
            textarea = editor.query_one("#journal_textarea", LedgerTextArea)
            assert textarea.theme == TEXTAREA_THEME_NAME

    async def test_highlights_rebuilt_after_edit(self, journal_file: Path) -> None:
        """After editing text, _highlights still contains ledger.date spans."""
        app = LedgerApp(journal_file)
        async with app.run_test(size=(120, 30)) as pilot:
            editor = pilot.app.query_one(JournalEditor)
            textarea = editor.query_one("#journal_textarea", LedgerTextArea)
            await pilot.pause()

            # Trigger a text change via the TextArea API
            textarea.load_text("2024-06-01 New payee\n    expenses:food    £1.00\n    assets:bank\n")
            await pilot.pause()

            line_spans = textarea._highlights.get(0, [])
            token_names = {span[2] for span in line_spans}
            assert tokens.DATE in token_names
