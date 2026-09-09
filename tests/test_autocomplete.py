"""Tests for Tab autocomplete: _completion_context (pure) and the full
Tab-press-through-JournalEditor integration (Textual pilot harness).
"""
from pathlib import Path

from ledgerkit_editor.app import LedgerApp
from ledgerkit_editor.highlighting.highlighter import LineKind
from ledgerkit_editor.widgets.autocomplete import _completion_context
from ledgerkit_editor.widgets.autocomplete_popup import AutocompletePopup
from ledgerkit_editor.widgets.transaction_table import JournalEditor
from textual.widgets import Input, TextArea

FIXTURES = Path(__file__).parent / "fixtures"

JOURNAL = (
    "account expenses:food\n"
    "\n"
    "2024-01-10 * Opening balances\n"
    "    assets:bank:checking    £1000.00\n"
    "    equity:opening-balances\n"
    "\n"
    "2024-01-15 Groceries\n"
    "    expenses:food:organic    £42.50\n"
    "    assets:bank:checking\n"
)


# ---------------------------------------------------------------------------
# _completion_context — pure, no Textual event loop required
# ---------------------------------------------------------------------------


class TestCompletionContext:
    def test_posting_line_within_account_name(self) -> None:
        line = "    expenses:fo"
        ctx = _completion_context(line, len(line), LineKind.POSTING)
        assert ctx == ("account", "expenses:fo", 4)

    def test_posting_line_at_start_of_account(self) -> None:
        line = "    "
        ctx = _completion_context(line, 4, LineKind.POSTING)
        assert ctx == ("account", "", 4)

    def test_posting_line_past_amount_separator_returns_none(self) -> None:
        line = "    expenses:food    £42.50"
        col = line.index("£") + 1
        assert _completion_context(line, col, LineKind.POSTING) is None

    def test_posting_line_cursor_before_indent_returns_none(self) -> None:
        line = "    expenses:food"
        assert _completion_context(line, 2, LineKind.POSTING) is None

    def test_header_line_cursor_in_date_returns_none(self) -> None:
        line = "2024-01-15 Groceries"
        assert _completion_context(line, 3, LineKind.XACT_HEADER) is None

    def test_header_line_cursor_in_flag_returns_none(self) -> None:
        line = "2024-01-15 * Groceries"
        assert _completion_context(line, 12, LineKind.XACT_HEADER) is None

    def test_header_line_cursor_in_payee(self) -> None:
        line = "2024-01-15 Groc"
        ctx = _completion_context(line, len(line), LineKind.XACT_HEADER)
        assert ctx == ("payee", "Groc", 11)

    def test_header_line_cursor_past_payee_returns_none(self) -> None:
        line = "2024-01-15 Groceries  ; a note"
        assert _completion_context(line, len(line), LineKind.XACT_HEADER) is None

    def test_blank_line_returns_none(self) -> None:
        assert _completion_context("", 0, LineKind.BLANK) is None

    def test_comment_line_returns_none(self) -> None:
        assert _completion_context("; comment", 3, LineKind.COMMENT) is None

    def test_directive_line_returns_none(self) -> None:
        assert _completion_context("account expenses:food", 10, LineKind.DIRECTIVE) is None


# ---------------------------------------------------------------------------
# Integration — real Tab key dispatch through JournalEditor
# ---------------------------------------------------------------------------


class TestAutocompleteIntegration:
    async def test_tab_completes_account_and_shows_popup(self, tmp_path: Path) -> None:
        journal = tmp_path / "test.journal"
        journal.write_text(JOURNAL, encoding="utf-8")

        app = LedgerApp(journal)
        async with app.run_test(size=(120, 30)) as pilot:
            editor = pilot.app.query_one(JournalEditor)
            textarea = editor.query_one("#journal_textarea", TextArea)
            popup = editor.query_one(AutocompletePopup)

            # Add a new posting line starting "expenses:" on a fresh transaction.
            lines = textarea.text.splitlines()
            end_row = len(lines)
            textarea.move_cursor((end_row - 1, len(lines[-1])))
            textarea.insert("\n    expenses:")
            row = end_row
            col = len("    expenses:")
            textarea.move_cursor((row, col))

            await pilot.press("tab")
            await pilot.pause()

            new_line = textarea.text.splitlines()[row]
            assert new_line.startswith("    expenses:")
            assert popup.is_showing
            assert popup.selected_candidate in popup.candidates

    async def test_popup_is_tall_enough_to_show_its_border_and_content(
        self, tmp_path: Path
    ) -> None:
        """UAT finding: the bar wasn't visible ("seems to be behind editor
        window") even though completion itself worked. Root cause:
        height: 1 with a border-top leaves zero rows for content — the
        border alone consumes the only available row. Must be >= 2."""
        journal = tmp_path / "test.journal"
        journal.write_text(JOURNAL, encoding="utf-8")

        app = LedgerApp(journal)
        async with app.run_test(size=(120, 30)) as pilot:
            editor = pilot.app.query_one(JournalEditor)
            popup = editor.query_one(AutocompletePopup)

            popup.show(["expenses:food", "expenses:food:organic"])
            await pilot.pause()

            # region/outer_size include the border; size is the inner
            # content box (excludes it) — with height:2 and a 1-row
            # border-top, the content box gets exactly 1 row, which is
            # what actually matters: at the old height:1, content got 0
            # rows and nothing could render, regardless of the border
            # itself still reserving space.
            assert popup.region.height == 2
            assert popup.size.height >= 1
            assert popup.query(".candidate")

    async def test_tab_again_cycles_candidate(self, tmp_path: Path) -> None:
        journal = tmp_path / "test.journal"
        journal.write_text(JOURNAL, encoding="utf-8")

        app = LedgerApp(journal)
        async with app.run_test(size=(120, 30)) as pilot:
            editor = pilot.app.query_one(JournalEditor)
            textarea = editor.query_one("#journal_textarea", TextArea)
            popup = editor.query_one(AutocompletePopup)

            lines = textarea.text.splitlines()
            row = len(lines)
            textarea.move_cursor((row - 1, len(lines[-1])))
            textarea.insert("\n    expenses:")
            textarea.move_cursor((row, len("    expenses:")))

            await pilot.press("tab")
            await pilot.pause()
            assert len(popup.candidates) >= 2, (
                "fixture should have >=2 expenses: accounts for a cycle test"
            )
            first = popup.selected_candidate

            await pilot.press("tab")
            await pilot.pause()
            second = popup.selected_candidate

            assert second != first
            new_line = textarea.text.splitlines()[row]
            assert new_line == f"    {second}"

    async def test_tab_completes_payee(self, tmp_path: Path) -> None:
        journal = tmp_path / "test.journal"
        journal.write_text(JOURNAL, encoding="utf-8")

        app = LedgerApp(journal)
        async with app.run_test(size=(120, 30)) as pilot:
            editor = pilot.app.query_one(JournalEditor)
            textarea = editor.query_one("#journal_textarea", TextArea)
            popup = editor.query_one(AutocompletePopup)

            lines = textarea.text.splitlines()
            row = len(lines)
            textarea.move_cursor((row - 1, len(lines[-1])))
            textarea.insert("\n2024-03-01 Groc")
            textarea.move_cursor((row, len("2024-03-01 Groc")))

            await pilot.press("tab")
            await pilot.pause()

            new_line = textarea.text.splitlines()[row]
            assert new_line == "2024-03-01 Groceries"
            assert popup.is_showing

    async def test_tab_with_no_match_falls_through_without_error(
        self, tmp_path: Path
    ) -> None:
        journal = tmp_path / "test.journal"
        journal.write_text(JOURNAL, encoding="utf-8")

        app = LedgerApp(journal)
        async with app.run_test(size=(120, 30)) as pilot:
            editor = pilot.app.query_one(JournalEditor)
            textarea = editor.query_one("#journal_textarea", TextArea)
            popup = editor.query_one(AutocompletePopup)

            lines = textarea.text.splitlines()
            row = len(lines)
            textarea.move_cursor((row - 1, len(lines[-1])))
            textarea.insert("\n    zzz_no_such_account")
            textarea.move_cursor((row, len("    zzz_no_such_account")))

            original = textarea.text
            await pilot.press("tab")
            await pilot.pause()

            assert textarea.text == original
            assert not popup.is_showing

    async def test_escape_dismisses_popup(self, tmp_path: Path) -> None:
        journal = tmp_path / "test.journal"
        journal.write_text(JOURNAL, encoding="utf-8")

        app = LedgerApp(journal)
        async with app.run_test(size=(120, 30)) as pilot:
            editor = pilot.app.query_one(JournalEditor)
            textarea = editor.query_one("#journal_textarea", TextArea)
            popup = editor.query_one(AutocompletePopup)

            lines = textarea.text.splitlines()
            row = len(lines)
            textarea.move_cursor((row - 1, len(lines[-1])))
            textarea.insert("\n    expenses:")
            textarea.move_cursor((row, len("    expenses:")))

            await pilot.press("tab")
            await pilot.pause()
            assert popup.is_showing

            await pilot.press("escape")
            await pilot.pause()
            assert not popup.is_showing

    async def test_typing_after_completion_starts_fresh_on_next_tab(
        self, tmp_path: Path
    ) -> None:
        """Typing more text after a completion means the next Tab is a new
        request, not a cycle continuation (cursor no longer matches the
        anchor position — see AutocompleteMixin._autocomplete_cursor_matches)."""
        journal = tmp_path / "test.journal"
        journal.write_text(JOURNAL, encoding="utf-8")

        app = LedgerApp(journal)
        async with app.run_test(size=(120, 30)) as pilot:
            editor = pilot.app.query_one(JournalEditor)
            textarea = editor.query_one("#journal_textarea", TextArea)
            popup = editor.query_one(AutocompletePopup)

            lines = textarea.text.splitlines()
            row = len(lines)
            textarea.move_cursor((row - 1, len(lines[-1])))
            textarea.insert("\n    expenses:")
            textarea.move_cursor((row, len("    expenses:")))

            await pilot.press("tab")
            await pilot.pause()
            first_candidates = popup.candidates
            assert len(first_candidates) >= 2  # cycling would be meaningful here

            textarea.insert("x")  # user keeps typing after the completion
            await pilot.pause()

            await pilot.press("tab")
            await pilot.pause()
            # "...foodx" matches nothing in this fixture, so the second Tab
            # must fall through (text unchanged) rather than wrongly
            # cycling to the *previous* completion's next candidate.
            assert textarea.text.splitlines()[row] == "    expenses:foodx"
            assert not popup.is_showing

    async def test_tab_in_search_input_does_not_touch_textarea(
        self, tmp_path: Path
    ) -> None:
        journal = tmp_path / "test.journal"
        journal.write_text(JOURNAL, encoding="utf-8")

        app = LedgerApp(journal)
        async with app.run_test(size=(120, 30)) as pilot:
            editor = pilot.app.query_one(JournalEditor)
            textarea = editor.query_one("#journal_textarea", TextArea)
            original = textarea.text

            editor.action_open_search()
            await pilot.pause()

            await pilot.press("tab")
            await pilot.pause()

            assert textarea.text == original

    async def test_save_rebuilds_index_with_newly_typed_account(
        self, tmp_path: Path
    ) -> None:
        journal = tmp_path / "test.journal"
        journal.write_text(JOURNAL, encoding="utf-8")

        app = LedgerApp(journal)
        async with app.run_test(size=(120, 30)) as pilot:
            editor = pilot.app.query_one(JournalEditor)
            textarea = editor.query_one("#journal_textarea", TextArea)

            # Brand-new account not in the index yet.
            new_block = (
                "\n2024-03-01 New Vendor\n"
                "    expenses:new_category_xyz    £5.00\n"
                "    assets:bank:checking\n"
            )
            textarea.move_cursor((len(textarea.text.splitlines()) - 1, 0))
            end_row = len(textarea.text.splitlines()) - 1
            end_col = len(textarea.text.splitlines()[-1])
            textarea.replace(new_block, (end_row, end_col), (end_row, end_col))
            await pilot.pause()

            assert "new_category_xyz" not in editor._journal_index.accounts

            editor.action_save()
            await pilot.pause()

            assert any(
                "new_category_xyz" in a for a in editor._journal_index.accounts
            )
