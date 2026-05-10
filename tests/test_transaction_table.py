"""Tests for ledger_editor.widgets.transaction_table (JournalEditor)."""

from pathlib import Path
import shutil

from ledger_editor.app import LedgerApp
from ledger_editor.widgets.transaction_table import (
    JournalEditor,
    _cycle_flag_in_header,
    _extract_account_from_line,
    _find_transaction_block,
)
from textual.widgets import TextArea

FIXTURES = Path(__file__).parent / "fixtures"


# ---------------------------------------------------------------------------
# Pure-function unit tests (no Textual event loop required)
# ---------------------------------------------------------------------------


class TestCycleFlagInHeader:
    """Unit tests for the _cycle_flag_in_header helper."""

    def test_no_flag_becomes_pending(self) -> None:
        result = _cycle_flag_in_header("2024-01-01 Groceries")
        assert result == "2024-01-01 ! Groceries"

    def test_pending_becomes_cleared(self) -> None:
        result = _cycle_flag_in_header("2024-01-01 ! Groceries")
        assert result == "2024-01-01 * Groceries"

    def test_cleared_becomes_uncleared(self) -> None:
        result = _cycle_flag_in_header("2024-01-01 * Groceries")
        assert result == "2024-01-01 Groceries"

    def test_code_field_preserved(self) -> None:
        result = _cycle_flag_in_header("2024-01-01 * (INV-42) Description")
        assert result == "2024-01-01 (INV-42) Description"

    def test_posting_line_returned_unchanged(self) -> None:
        line = "    expenses:food    £42.50"
        assert _cycle_flag_in_header(line) == line


class TestExtractAccountFromLine:
    """Unit tests for the _extract_account_from_line helper."""

    def test_posting_line_with_amount_returns_account(self) -> None:
        assert _extract_account_from_line("    expenses:food    £42.50") == "expenses:food"

    def test_posting_line_no_amount_returns_account(self) -> None:
        assert _extract_account_from_line("    assets:bank:checking") == "assets:bank:checking"

    def test_header_line_returns_none(self) -> None:
        assert _extract_account_from_line("2024-01-01 * Groceries") is None

    def test_blank_line_returns_none(self) -> None:
        assert _extract_account_from_line("") is None


# ---------------------------------------------------------------------------
# Async widget tests (require Textual run_test harness)
# ---------------------------------------------------------------------------


class TestJournalEditorWidget:
    """Async integration tests for JournalEditor using Textual's test harness."""

    async def test_editor_loads_text(self) -> None:
        """After mount the TextArea should contain the raw journal content."""
        app = LedgerApp(FIXTURES / "sample.journal")
        async with app.run_test(size=(120, 30)) as pilot:
            editor = pilot.app.query_one(JournalEditor)
            text = editor.query_one("#journal_textarea", TextArea).text
            assert "2024-01-10" in text
            assert "Opening balances" in text
            assert "expenses:food" in text

    async def test_save_writes_to_disk(self, tmp_path: Path) -> None:
        """Ctrl+S rewrites the file; key transaction content is preserved."""
        journal = tmp_path / "test.journal"
        shutil.copy(FIXTURES / "sample.journal", journal)

        app = LedgerApp(journal)
        async with app.run_test(size=(120, 30)) as pilot:
            editor = pilot.app.query_one(JournalEditor)
            editor.action_save()
            await pilot.pause()

        content = journal.read_text(encoding="utf-8")
        assert "2024-01-10" in content
        assert "Opening balances" in content

    async def test_save_sorts_transactions(self, tmp_path: Path) -> None:
        """Saving an out-of-order journal rewrites it sorted by date."""
        journal = tmp_path / "oot.journal"
        journal.write_text(
            "2024-01-15 Groceries\n"
            "    expenses:food    £42.50\n"
            "    assets:bank:checking\n"
            "\n"
            "2024-01-10 * Opening balances\n"
            "    assets:bank:checking    £1000.00\n"
            "    equity:opening-balances\n",
            encoding="utf-8",
        )

        app = LedgerApp(journal)
        async with app.run_test(size=(120, 30)) as pilot:
            editor = pilot.app.query_one(JournalEditor)
            editor.action_save()
            await pilot.pause()

        lines = journal.read_text(encoding="utf-8").splitlines()
        first_date = next(l for l in lines if l.startswith("2024-"))
        assert "2024-01-10" in first_date

    async def test_save_posts_save_completed(self, tmp_path: Path) -> None:
        """action_save() posts JournalEditor.SaveCompleted."""
        journal = tmp_path / "test.journal"
        shutil.copy(FIXTURES / "sample.journal", journal)

        received: list = []
        app = LedgerApp(journal)
        async with app.run_test(size=(120, 30)) as pilot:
            editor = pilot.app.query_one(JournalEditor)
            _orig = editor.post_message

            def _spy(msg: object) -> bool:
                if isinstance(msg, JournalEditor.SaveCompleted):
                    received.append(msg)
                return _orig(msg)  # type: ignore[arg-type]

            editor.post_message = _spy  # type: ignore[method-assign]
            editor.action_save()
            await pilot.pause()

        assert received, "SaveCompleted was not posted"

    async def test_toggle_cleared_on_header_line(self) -> None:
        """Ctrl+Shift+A on a header line cycles the flag character."""
        app = LedgerApp(FIXTURES / "sample.journal")
        async with app.run_test(size=(120, 30)) as pilot:
            editor = pilot.app.query_one(JournalEditor)
            textarea = editor.query_one("#journal_textarea", TextArea)

            lines = textarea.text.splitlines()
            # Find the Groceries header (uncleared, no flag)
            groceries_row = next(
                i for i, l in enumerate(lines)
                if "Groceries" in l and not l[0].isspace()
            )
            textarea.move_cursor((groceries_row, 0))
            editor.action_toggle_cleared()

            new_line = textarea.text.splitlines()[groceries_row]
            assert "!" in new_line

    async def test_toggle_cleared_on_posting_line(self) -> None:
        """Ctrl+Shift+A on a posting line leaves the text unchanged."""
        app = LedgerApp(FIXTURES / "sample.journal")
        async with app.run_test(size=(120, 30)) as pilot:
            editor = pilot.app.query_one(JournalEditor)
            textarea = editor.query_one("#journal_textarea", TextArea)

            lines = textarea.text.splitlines()
            posting_row = next(i for i, l in enumerate(lines) if l and l[0].isspace())
            original_line = lines[posting_row]
            textarea.move_cursor((posting_row, 0))
            editor.action_toggle_cleared()
            await pilot.pause()  # flush SelectionChanged before teardown

            assert textarea.text.splitlines()[posting_row] == original_line

    async def test_cursor_account_changed_on_posting(self) -> None:
        """Moving cursor to a posting line posts CursorAccountChanged with the account."""
        app = LedgerApp(FIXTURES / "sample.journal")
        async with app.run_test(size=(120, 30)) as pilot:
            editor = pilot.app.query_one(JournalEditor)
            textarea = editor.query_one("#journal_textarea", TextArea)

            lines = textarea.text.splitlines()
            food_row = next(i for i, l in enumerate(lines) if "expenses:food" in l)
            textarea.move_cursor((food_row, 0))
            await pilot.pause()

            assert editor._current_account == "expenses:food"

    async def test_cursor_account_changed_on_header(self) -> None:
        """Moving cursor to a header line posts CursorAccountChanged with None."""
        app = LedgerApp(FIXTURES / "sample.journal")
        async with app.run_test(size=(120, 30)) as pilot:
            editor = pilot.app.query_one(JournalEditor)
            textarea = editor.query_one("#journal_textarea", TextArea)

            lines = textarea.text.splitlines()
            header_row = next(i for i, l in enumerate(lines) if l.startswith("2024-"))
            textarea.move_cursor((header_row, 0))
            await pilot.pause()

            assert editor._current_account is None

    async def test_select_to_block_end(self, tmp_path: Path) -> None:
        """Ctrl+Shift+Down from the header selects to the last posting line."""
        journal = tmp_path / "block.journal"
        journal.write_text(
            "2024-01-15 Groceries\n"
            "    expenses:food    £42.50\n"
            "    assets:bank:checking\n"
            "\n"
            "2024-01-10 * Opening balances\n"
            "    assets:bank:checking    £1000.00\n"
            "    equity:opening-balances\n",
            encoding="utf-8",
        )
        app = LedgerApp(journal)
        async with app.run_test(size=(120, 30)) as pilot:
            editor = pilot.app.query_one(JournalEditor)
            textarea = editor.query_one("#journal_textarea", TextArea)

            textarea.move_cursor((0, 0))
            editor.action_select_to_block_end()
            await pilot.pause()

            sel = textarea.selection
            assert sel.start == (0, 0)
            assert sel.end[0] == 2  # last posting of the first transaction

    async def test_select_to_block_start(self, tmp_path: Path) -> None:
        """Ctrl+Shift+Up from a posting line selects back to the header."""
        journal = tmp_path / "block.journal"
        journal.write_text(
            "2024-01-15 Groceries\n"
            "    expenses:food    £42.50\n"
            "    assets:bank:checking\n"
            "\n"
            "2024-01-10 * Opening balances\n"
            "    assets:bank:checking    £1000.00\n"
            "    equity:opening-balances\n",
            encoding="utf-8",
        )
        app = LedgerApp(journal)
        async with app.run_test(size=(120, 30)) as pilot:
            editor = pilot.app.query_one(JournalEditor)
            textarea = editor.query_one("#journal_textarea", TextArea)

            textarea.move_cursor((1, 0))  # first posting line
            editor.action_select_to_block_start()
            await pilot.pause()

            sel = textarea.selection
            assert sel.start == (0, 0)  # header line
            assert sel.end == (1, 0)    # cursor stayed at posting line


# ---------------------------------------------------------------------------
# Pure-function unit tests for _find_transaction_block
# ---------------------------------------------------------------------------


_MULTI_TXN = [
    "2024-01-01 Opening",       # row 0 — header
    "    assets:bank  £1000",   # row 1 — posting
    "    equity:opening",       # row 2 — posting
    "",                         # row 3 — blank separator
    "2024-01-15 Groceries",     # row 4 — header
    "    expenses:food  £42",   # row 5 — posting
    "    assets:bank",          # row 6 — posting
]


class TestFindTransactionBlock:
    """Unit tests for the _find_transaction_block helper."""

    def test_cursor_on_header_line(self) -> None:
        assert _find_transaction_block(_MULTI_TXN, 0) == (0, 2)

    def test_cursor_on_posting_line(self) -> None:
        assert _find_transaction_block(_MULTI_TXN, 1) == (0, 2)

    def test_cursor_on_blank_line_finds_upper_block(self) -> None:
        # Blank line between transactions — walks up into the preceding block.
        assert _find_transaction_block(_MULTI_TXN, 3) == (0, 2)

    def test_cursor_on_second_transaction(self) -> None:
        assert _find_transaction_block(_MULTI_TXN, 5) == (4, 6)

    def test_empty_lines_list(self) -> None:
        assert _find_transaction_block([], 0) == (0, 0)


class TestNavigationActions:
    """Async tests for the Ctrl+Home/End and Ctrl+A navigation actions."""

    async def test_cursor_to_start(self) -> None:
        """action_cursor_to_start() moves cursor to (0, 0)."""
        app = LedgerApp(FIXTURES / "sample.journal")
        async with app.run_test(size=(120, 30)) as pilot:
            editor = pilot.app.query_one(JournalEditor)
            textarea = editor.query_one("#journal_textarea", TextArea)

            lines = textarea.text.splitlines()
            textarea.move_cursor((len(lines) - 1, 0))
            editor.action_cursor_to_start()
            await pilot.pause()

            assert textarea.cursor_location == (0, 0)

    async def test_cursor_to_end(self) -> None:
        """action_cursor_to_end() moves cursor to the last line."""
        app = LedgerApp(FIXTURES / "sample.journal")
        async with app.run_test(size=(120, 30)) as pilot:
            editor = pilot.app.query_one(JournalEditor)
            textarea = editor.query_one("#journal_textarea", TextArea)

            textarea.move_cursor((0, 0))
            editor.action_cursor_to_end()
            await pilot.pause()

            lines = textarea.text.splitlines()
            assert textarea.cursor_location[0] == len(lines) - 1

    async def test_select_all(self) -> None:
        """action_select_all() selects from (0,0) to end of last line."""
        app = LedgerApp(FIXTURES / "sample.journal")
        async with app.run_test(size=(120, 30)) as pilot:
            editor = pilot.app.query_one(JournalEditor)
            textarea = editor.query_one("#journal_textarea", TextArea)

            editor.action_select_all()
            await pilot.pause()

            lines = textarea.text.splitlines()
            sel = textarea.selection
            assert sel.start == (0, 0)
            assert sel.end == (len(lines) - 1, len(lines[-1]))
