"""Tests for SearchBar (search_bar.py), in particular Ctrl+C copy behaviour.

Ctrl+C while the search bar has focus must copy the current match's text
from the journal, not fall through to Textual's default App-level "press
ctrl+q to quit" binding — see action_copy_match's docstring for why that
fallthrough happens in the first place (Input.action_copy() raises
SkipAction when the Input itself has no text selection).
"""
from pathlib import Path

from ledgerkit_editor.app import LedgerApp
from ledgerkit_editor.widgets.search_bar import SearchBar
from ledgerkit_editor.widgets.transaction_table import JournalEditor
from textual.widgets import Input

FIXTURES = Path(__file__).parent / "fixtures"


class TestSearchBarCopy:
    """Ctrl+C behaviour while the search bar's Input has focus."""

    async def test_copy_active_match_via_ctrl_c(self) -> None:
        """With a match highlighted and nothing selected in the Input,
        Ctrl+C copies the matched journal text to the clipboard."""
        app = LedgerApp(FIXTURES / "sample.journal")
        async with app.run_test(size=(120, 30)) as pilot:
            editor = pilot.app.query_one(JournalEditor)
            search_bar = editor.query_one(SearchBar)
            input_widget = search_bar.query_one("#search-input", Input)

            editor.action_open_search()
            await pilot.pause()
            input_widget.value = "food"
            await pilot.pause()

            assert search_bar._current != -1, "expected a match on 'food'"

            await pilot.press("ctrl+c")
            await pilot.pause()

            assert pilot.app.clipboard.lower() == "food"

    async def test_real_input_selection_not_overridden(self) -> None:
        """If the user has actually selected text inside the search box
        itself, Ctrl+C copies that selection rather than the match."""
        app = LedgerApp(FIXTURES / "sample.journal")
        async with app.run_test(size=(120, 30)) as pilot:
            editor = pilot.app.query_one(JournalEditor)
            search_bar = editor.query_one(SearchBar)
            input_widget = search_bar.query_one("#search-input", Input)

            editor.action_open_search()
            await pilot.pause()
            input_widget.value = "food"
            await pilot.pause()
            input_widget.select_all()

            await pilot.press("ctrl+c")
            await pilot.pause()

            assert pilot.app.clipboard == "food"

    async def test_copy_with_no_matches_is_noop(self) -> None:
        """No active match: Ctrl+C does nothing and does not raise."""
        app = LedgerApp(FIXTURES / "sample.journal")
        async with app.run_test(size=(120, 30)) as pilot:
            editor = pilot.app.query_one(JournalEditor)
            search_bar = editor.query_one(SearchBar)
            input_widget = search_bar.query_one("#search-input", Input)

            editor.action_open_search()
            await pilot.pause()
            input_widget.value = "zzzznomatch"
            await pilot.pause()

            assert search_bar._current == -1

            await pilot.press("ctrl+c")
            await pilot.pause()

            assert pilot.app.clipboard == ""

    async def test_action_copy_match_direct_no_matches(self) -> None:
        """Calling action_copy_match() directly with zero matches is a no-op."""
        app = LedgerApp(FIXTURES / "sample.journal")
        async with app.run_test(size=(120, 30)) as pilot:
            editor = pilot.app.query_one(JournalEditor)
            search_bar = editor.query_one(SearchBar)

            search_bar.action_copy_match()  # should not raise

            assert pilot.app.clipboard == ""
