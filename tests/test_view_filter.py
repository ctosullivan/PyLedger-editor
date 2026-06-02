"""Tests for the Ctrl+L view filter feature in JournalEditor."""

from pathlib import Path
from datetime import date as _date

from ledgerkit_editor.app import LedgerApp
from ledgerkit_editor.widgets.transaction_table import JournalEditor
from ledgerkit_editor.widgets.view_filter_bar import ViewFilterBar
from textual.widgets import TextArea

# A journal with preamble directives and an interleaved directive between transactions.
DIRECTIVE_JOURNAL = (
    "P 2024-01-01 USD EUR 0.92\n"
    "account assets:bank:checking\n"
    "; file header comment\n"
    "\n"
    "2024-01-10 * Opening balances\n"
    "    assets:bank:checking    £1000.00\n"
    "    equity:opening-balances\n"
    "\n"
    "P 2024-01-12 USD EUR 0.93\n"
    "\n"
    "2024-01-15 Groceries\n"
    "    expenses:food    £42.50\n"
    "    assets:bank:checking\n"
)

# A journal with one cleared and one uncleared transaction.
MIXED_JOURNAL = (
    "2024-01-10 * Opening balances\n"
    "    assets:bank:checking    £1000.00\n"
    "    equity:opening-balances\n"
    "\n"
    "2024-01-15 Groceries\n"
    "    expenses:food    £42.50\n"
    "    assets:bank:checking\n"
)

# Three transactions: two cleared, one uncleared.
THREE_TXN_JOURNAL = (
    "2024-01-10 * Opening balances\n"
    "    assets:bank:checking    £1000.00\n"
    "    equity:opening-balances\n"
    "\n"
    "2024-01-12 * Salary\n"
    "    assets:bank:checking    £2000.00\n"
    "    income:salary\n"
    "\n"
    "2024-01-15 Groceries\n"
    "    expenses:food    £42.50\n"
    "    assets:bank:checking\n"
)


class TestViewFilterCycle:
    """Tests for Ctrl+L mode cycling."""

    async def test_initial_mode_is_all(self, tmp_path: Path) -> None:
        """On startup the view filter mode is 0 (All)."""
        journal = tmp_path / "test.journal"
        journal.write_text(MIXED_JOURNAL, encoding="utf-8")

        app = LedgerApp(journal)
        async with app.run_test(size=(120, 30)) as pilot:
            editor = pilot.app.query_one(JournalEditor)
            assert editor._view_filter_mode == 0

    async def test_ctrl_l_advances_to_cleared(self, tmp_path: Path) -> None:
        """First Ctrl+L sets mode to 1 (Cleared only)."""
        journal = tmp_path / "test.journal"
        journal.write_text(MIXED_JOURNAL, encoding="utf-8")

        app = LedgerApp(journal)
        async with app.run_test(size=(120, 30)) as pilot:
            editor = pilot.app.query_one(JournalEditor)
            editor.action_cycle_view_filter()
            await pilot.pause()

            assert editor._view_filter_mode == 1

    async def test_ctrl_l_twice_advances_to_unreconciled(self, tmp_path: Path) -> None:
        """Two Ctrl+L presses set mode to 2 (Unreconciled only)."""
        journal = tmp_path / "test.journal"
        journal.write_text(MIXED_JOURNAL, encoding="utf-8")

        app = LedgerApp(journal)
        async with app.run_test(size=(120, 30)) as pilot:
            editor = pilot.app.query_one(JournalEditor)
            editor.action_cycle_view_filter()
            await pilot.pause()
            editor.action_cycle_view_filter()
            await pilot.pause()

            assert editor._view_filter_mode == 2

    async def test_ctrl_l_three_times_returns_to_all(self, tmp_path: Path) -> None:
        """Three Ctrl+L presses return to mode 0 (All)."""
        journal = tmp_path / "test.journal"
        journal.write_text(MIXED_JOURNAL, encoding="utf-8")

        app = LedgerApp(journal)
        async with app.run_test(size=(120, 30)) as pilot:
            editor = pilot.app.query_one(JournalEditor)
            for _ in range(3):
                editor.action_cycle_view_filter()
                await pilot.pause()

            assert editor._view_filter_mode == 0


class TestViewFilterContent:
    """Tests that the correct transactions are shown for each filter mode."""

    async def test_cleared_filter_shows_only_cleared_transactions(
        self, tmp_path: Path
    ) -> None:
        """Mode 1 shows only transactions marked with '*'."""
        journal = tmp_path / "test.journal"
        journal.write_text(MIXED_JOURNAL, encoding="utf-8")

        app = LedgerApp(journal)
        async with app.run_test(size=(120, 30)) as pilot:
            editor = pilot.app.query_one(JournalEditor)
            textarea = editor.query_one("#journal_textarea", TextArea)

            editor.action_cycle_view_filter()
            await pilot.pause()

            text = textarea.text
            assert "Opening balances" in text
            assert "Groceries" not in text

    async def test_unreconciled_filter_shows_only_uncleared_transactions(
        self, tmp_path: Path
    ) -> None:
        """Mode 2 shows only transactions not marked with '*'."""
        journal = tmp_path / "test.journal"
        journal.write_text(MIXED_JOURNAL, encoding="utf-8")

        app = LedgerApp(journal)
        async with app.run_test(size=(120, 30)) as pilot:
            editor = pilot.app.query_one(JournalEditor)
            textarea = editor.query_one("#journal_textarea", TextArea)

            editor.action_cycle_view_filter()
            await pilot.pause()
            editor.action_cycle_view_filter()
            await pilot.pause()

            text = textarea.text
            assert "Opening balances" not in text
            assert "Groceries" in text

    async def test_all_mode_shows_all_transactions(self, tmp_path: Path) -> None:
        """Returning to mode 0 restores all transactions."""
        journal = tmp_path / "test.journal"
        journal.write_text(THREE_TXN_JOURNAL, encoding="utf-8")

        app = LedgerApp(journal)
        async with app.run_test(size=(120, 30)) as pilot:
            editor = pilot.app.query_one(JournalEditor)
            textarea = editor.query_one("#journal_textarea", TextArea)

            # Cycle through all modes back to All.
            for _ in range(3):
                editor.action_cycle_view_filter()
                await pilot.pause()

            text = textarea.text
            assert "Opening balances" in text
            assert "Salary" in text
            assert "Groceries" in text


class TestViewFilterBar:
    """Tests that the ViewFilterBar mode updates correctly."""

    async def test_filter_bar_shows_all_on_startup(self, tmp_path: Path) -> None:
        """ViewFilterBar current_mode is 0 (All) at startup."""
        journal = tmp_path / "test.journal"
        journal.write_text(MIXED_JOURNAL, encoding="utf-8")

        app = LedgerApp(journal)
        async with app.run_test(size=(120, 30)) as pilot:
            editor = pilot.app.query_one(JournalEditor)
            bar = editor.query_one(ViewFilterBar)
            assert bar.current_mode == 0

    async def test_filter_bar_updates_on_cycle(self, tmp_path: Path) -> None:
        """ViewFilterBar current_mode reflects mode after each Ctrl+L press."""
        journal = tmp_path / "test.journal"
        journal.write_text(MIXED_JOURNAL, encoding="utf-8")

        app = LedgerApp(journal)
        async with app.run_test(size=(120, 30)) as pilot:
            editor = pilot.app.query_one(JournalEditor)
            bar = editor.query_one(ViewFilterBar)

            editor.action_cycle_view_filter()
            await pilot.pause()
            assert bar.current_mode == 1

            editor.action_cycle_view_filter()
            await pilot.pause()
            assert bar.current_mode == 2

            editor.action_cycle_view_filter()
            await pilot.pause()
            assert bar.current_mode == 0


class TestViewFilterSave:
    """Tests that saving while filtered writes the full journal."""

    async def test_save_in_filtered_view_writes_all_transactions(
        self, tmp_path: Path
    ) -> None:
        """Ctrl+S while in Cleared filter writes all transactions to disk."""
        journal = tmp_path / "test.journal"
        journal.write_text(MIXED_JOURNAL, encoding="utf-8")

        app = LedgerApp(journal)
        async with app.run_test(size=(120, 30)) as pilot:
            editor = pilot.app.query_one(JournalEditor)

            # Enter Cleared filter — only cleared transactions visible.
            editor.action_cycle_view_filter()
            await pilot.pause()

            # Save — should write all transactions.
            editor.action_save()
            await pilot.pause()

        content = journal.read_text(encoding="utf-8")
        assert "Opening balances" in content
        assert "Groceries" in content

    async def test_save_exits_filtered_view(self, tmp_path: Path) -> None:
        """Ctrl+S while filtered returns editor to All mode."""
        journal = tmp_path / "test.journal"
        journal.write_text(MIXED_JOURNAL, encoding="utf-8")

        app = LedgerApp(journal)
        async with app.run_test(size=(120, 30)) as pilot:
            editor = pilot.app.query_one(JournalEditor)
            textarea = editor.query_one("#journal_textarea", TextArea)

            editor.action_cycle_view_filter()
            await pilot.pause()

            editor.action_save()
            await pilot.pause()

            assert editor._view_filter_mode == 0
            text = textarea.text
            assert "Opening balances" in text
            assert "Groceries" in text


class TestViewFilterEditing:
    """Tests for editing within a filtered view."""

    async def test_edit_in_cleared_filter_preserved_on_return_to_all(
        self, tmp_path: Path
    ) -> None:
        """Editing a cleared transaction's description while filtered survives returning to All."""
        journal = tmp_path / "test.journal"
        journal.write_text(MIXED_JOURNAL, encoding="utf-8")

        app = LedgerApp(journal)
        async with app.run_test(size=(120, 30)) as pilot:
            editor = pilot.app.query_one(JournalEditor)
            textarea = editor.query_one("#journal_textarea", TextArea)

            # Enter Cleared filter.
            editor.action_cycle_view_filter()
            await pilot.pause()

            # Locate and modify the "Opening balances" header line.
            lines = textarea.text.splitlines()
            header_row = next(i for i, l in enumerate(lines) if "Opening balances" in l)
            new_header = lines[header_row].replace("Opening balances", "Initial deposit")
            textarea.replace(new_header, (header_row, 0), (header_row, len(lines[header_row])))
            await pilot.pause()

            # Return to All.
            editor.action_cycle_view_filter()  # → Unreconciled
            await pilot.pause()
            editor.action_cycle_view_filter()  # → All
            await pilot.pause()

            text = textarea.text
            assert "Initial deposit" in text
            assert "Groceries" in text


class TestViewFilterDirectivePreservation:
    """Directives, aliases, and comments survive filter cycling."""

    async def test_preamble_directives_survive_full_cycle(
        self, tmp_path: Path
    ) -> None:
        """P directives and account decls before the first transaction are intact after 3× Ctrl+L."""
        journal = tmp_path / "test.journal"
        journal.write_text(DIRECTIVE_JOURNAL, encoding="utf-8")

        app = LedgerApp(journal)
        async with app.run_test(size=(120, 30)) as pilot:
            editor = pilot.app.query_one(JournalEditor)
            textarea = editor.query_one("#journal_textarea", TextArea)

            for _ in range(3):
                editor.action_cycle_view_filter()
                await pilot.pause()

            text = textarea.text
            assert "P 2024-01-01 USD EUR 0.92" in text
            assert "account assets:bank:checking" in text

    async def test_preamble_comment_survives_full_cycle(
        self, tmp_path: Path
    ) -> None:
        """Standalone column-0 comment before first transaction survives 3× Ctrl+L."""
        journal = tmp_path / "test.journal"
        journal.write_text(DIRECTIVE_JOURNAL, encoding="utf-8")

        app = LedgerApp(journal)
        async with app.run_test(size=(120, 30)) as pilot:
            editor = pilot.app.query_one(JournalEditor)
            textarea = editor.query_one("#journal_textarea", TextArea)

            for _ in range(3):
                editor.action_cycle_view_filter()
                await pilot.pause()

            assert "; file header comment" in textarea.text

    async def test_interleaved_directive_survives_full_cycle(
        self, tmp_path: Path
    ) -> None:
        """P directive between two transactions survives 3× Ctrl+L."""
        journal = tmp_path / "test.journal"
        journal.write_text(DIRECTIVE_JOURNAL, encoding="utf-8")

        app = LedgerApp(journal)
        async with app.run_test(size=(120, 30)) as pilot:
            editor = pilot.app.query_one(JournalEditor)
            textarea = editor.query_one("#journal_textarea", TextArea)

            for _ in range(3):
                editor.action_cycle_view_filter()
                await pilot.pause()

            assert "P 2024-01-12 USD EUR 0.93" in textarea.text

    async def test_directives_survive_save_from_filtered_view(
        self, tmp_path: Path
    ) -> None:
        """Directives are written to disk when Ctrl+S is pressed in a filtered view."""
        journal = tmp_path / "test.journal"
        journal.write_text(DIRECTIVE_JOURNAL, encoding="utf-8")

        app = LedgerApp(journal)
        async with app.run_test(size=(120, 30)) as pilot:
            editor = pilot.app.query_one(JournalEditor)

            editor.action_cycle_view_filter()  # → Cleared
            await pilot.pause()
            editor.action_save()
            await pilot.pause()

        content = journal.read_text(encoding="utf-8")
        assert "P 2024-01-01 USD EUR 0.92" in content
        assert "account assets:bank:checking" in content
        assert "P 2024-01-12 USD EUR 0.93" in content
        assert "; file header comment" in content
