"""Tests for the Ctrl+O transaction filter (FilterPopup + JournalEditor wiring).

Covers the criteria-filter path end-to-end: FilterPopup builds and posts a
validated predicate; LedgerApp (not JournalEditor — FilterPopup is a
sibling, not a child, see app.py's on_filter_popup_filter_applied) relays it
to JournalEditor.apply_criteria_filter(). Mutual exclusivity with Ctrl+L is
also covered here since it lives in the same engine (view_filter.py).
"""
from pathlib import Path

from ledgerkit_editor.app import LedgerApp
from ledgerkit_editor.widgets.filter_popup import FilterPopup
from ledgerkit_editor.widgets.transaction_table import JournalEditor
from ledgerkit_editor.widgets.view_filter_bar import ViewFilterBar
from textual.widgets import Input, TextArea

THREE_TXN_JOURNAL = (
    "2024-01-10 * Opening balances\n"
    "    assets:bank:checking    £1000.00\n"
    "    equity:opening-balances\n"
    "\n"
    "2024-01-15 Groceries\n"
    "    expenses:food    £42.50\n"
    "    assets:bank:checking\n"
    "\n"
    "2024-02-01 Rent\n"
    "    expenses:rent    £900.00\n"
    "    assets:bank:checking\n"
)


async def _open_filter_and_fill(pilot, **fields: str) -> None:
    """Open the Ctrl+O popup and fill the given field id -> value pairs."""
    app = pilot.app
    app.action_toggle_filter()
    await pilot.pause()
    popup = app.query_one(FilterPopup)
    for field_id, value in fields.items():
        popup.query_one(f"#{field_id}", Input).value = value


class TestFilterPopupApply:
    async def test_account_filter_shows_only_matching_transactions(
        self, tmp_path: Path
    ) -> None:
        journal = tmp_path / "test.journal"
        journal.write_text(THREE_TXN_JOURNAL, encoding="utf-8")

        app = LedgerApp(journal)
        async with app.run_test(size=(120, 30)) as pilot:
            await _open_filter_and_fill(pilot, account="expenses:food")
            popup = pilot.app.query_one(FilterPopup)
            popup.apply_filter()
            await pilot.pause()

            editor = pilot.app.query_one(JournalEditor)
            textarea = editor.query_one("#journal_textarea", TextArea)
            assert "Groceries" in textarea.text
            assert "Rent" not in textarea.text
            assert "Opening balances" not in textarea.text

    async def test_date_range_filter(self, tmp_path: Path) -> None:
        journal = tmp_path / "test.journal"
        journal.write_text(THREE_TXN_JOURNAL, encoding="utf-8")

        app = LedgerApp(journal)
        async with app.run_test(size=(120, 30)) as pilot:
            await _open_filter_and_fill(
                pilot, **{"date-from": "2024-01-11", "date-to": "2024-01-31"}
            )
            popup = pilot.app.query_one(FilterPopup)
            popup.apply_filter()
            await pilot.pause()

            editor = pilot.app.query_one(JournalEditor)
            textarea = editor.query_one("#journal_textarea", TextArea)
            assert "Groceries" in textarea.text
            assert "Opening balances" not in textarea.text
            assert "Rent" not in textarea.text

    async def test_payee_regex_filter(self, tmp_path: Path) -> None:
        journal = tmp_path / "test.journal"
        journal.write_text(THREE_TXN_JOURNAL, encoding="utf-8")

        app = LedgerApp(journal)
        async with app.run_test(size=(120, 30)) as pilot:
            await _open_filter_and_fill(pilot, payee="^Rent$")
            popup = pilot.app.query_one(FilterPopup)
            popup.apply_filter()
            await pilot.pause()

            editor = pilot.app.query_one(JournalEditor)
            textarea = editor.query_one("#journal_textarea", TextArea)
            assert "Rent" in textarea.text
            assert "Groceries" not in textarea.text

    async def test_empty_filter_shows_everything(self, tmp_path: Path) -> None:
        journal = tmp_path / "test.journal"
        journal.write_text(THREE_TXN_JOURNAL, encoding="utf-8")

        app = LedgerApp(journal)
        async with app.run_test(size=(120, 30)) as pilot:
            await _open_filter_and_fill(pilot)
            popup = pilot.app.query_one(FilterPopup)
            popup.apply_filter()
            await pilot.pause()

            editor = pilot.app.query_one(JournalEditor)
            textarea = editor.query_one("#journal_textarea", TextArea)
            assert "Groceries" in textarea.text
            assert "Rent" in textarea.text
            assert "Opening balances" in textarea.text

    async def test_invalid_regex_does_not_apply_filter(self, tmp_path: Path) -> None:
        journal = tmp_path / "test.journal"
        journal.write_text(THREE_TXN_JOURNAL, encoding="utf-8")

        app = LedgerApp(journal)
        async with app.run_test(size=(120, 30)) as pilot:
            await _open_filter_and_fill(pilot, account="expenses:(")
            popup = pilot.app.query_one(FilterPopup)
            popup.apply_filter()
            await pilot.pause()

            editor = pilot.app.query_one(JournalEditor)
            textarea = editor.query_one("#journal_textarea", TextArea)
            # Nothing hidden — the invalid regex was rejected before applying.
            assert "Groceries" in textarea.text
            assert "Rent" in textarea.text
            assert "Opening balances" in textarea.text

    async def test_invalid_smart_date_does_not_apply_filter(self, tmp_path: Path) -> None:
        journal = tmp_path / "test.journal"
        journal.write_text(THREE_TXN_JOURNAL, encoding="utf-8")

        app = LedgerApp(journal)
        async with app.run_test(size=(120, 30)) as pilot:
            await _open_filter_and_fill(pilot, **{"date-from": "not a date"})
            popup = pilot.app.query_one(FilterPopup)
            popup.apply_filter()
            await pilot.pause()

            editor = pilot.app.query_one(JournalEditor)
            textarea = editor.query_one("#journal_textarea", TextArea)
            assert "Groceries" in textarea.text
            assert "Opening balances" in textarea.text


class TestFilterPopupClear:
    async def test_clear_restores_full_journal(self, tmp_path: Path) -> None:
        journal = tmp_path / "test.journal"
        journal.write_text(THREE_TXN_JOURNAL, encoding="utf-8")

        app = LedgerApp(journal)
        async with app.run_test(size=(120, 30)) as pilot:
            editor = pilot.app.query_one(JournalEditor)
            predicate = lambda tx: tx.description == "Rent"  # noqa: E731
            editor.apply_criteria_filter(predicate)
            await pilot.pause()
            textarea = editor.query_one("#journal_textarea", TextArea)
            assert "Groceries" not in textarea.text

            editor.clear_criteria_filter()
            await pilot.pause()
            assert "Groceries" in textarea.text
            assert "Rent" in textarea.text
            assert "Opening balances" in textarea.text
            assert editor._active_predicate is None
            assert editor._view_filter_mode == 0


class TestFilterMutualExclusivity:
    """Ctrl+L and Ctrl+O share one engine and are mutually exclusive."""

    async def test_criteria_filter_exits_active_ctrl_l_filter(
        self, tmp_path: Path
    ) -> None:
        journal = tmp_path / "test.journal"
        journal.write_text(THREE_TXN_JOURNAL, encoding="utf-8")

        app = LedgerApp(journal)
        async with app.run_test(size=(120, 30)) as pilot:
            editor = pilot.app.query_one(JournalEditor)
            editor.action_cycle_view_filter()  # -> Cleared only (mode 1)
            await pilot.pause()
            assert editor._view_filter_mode == 1
            assert editor._active_predicate is None

            predicate = lambda tx: tx.description == "Rent"  # noqa: E731
            editor.apply_criteria_filter(predicate)
            await pilot.pause()

            assert editor._active_predicate is not None
            textarea = editor.query_one("#journal_textarea", TextArea)
            assert "Rent" in textarea.text
            assert "Groceries" not in textarea.text
            assert "Opening balances" not in textarea.text

    async def test_ctrl_l_exits_active_criteria_filter(self, tmp_path: Path) -> None:
        journal = tmp_path / "test.journal"
        journal.write_text(THREE_TXN_JOURNAL, encoding="utf-8")

        app = LedgerApp(journal)
        async with app.run_test(size=(120, 30)) as pilot:
            editor = pilot.app.query_one(JournalEditor)
            predicate = lambda tx: tx.description == "Rent"  # noqa: E731
            editor.apply_criteria_filter(predicate)
            await pilot.pause()
            assert editor._active_predicate is not None

            editor.action_cycle_view_filter()  # exits criteria filter, -> Cleared only
            await pilot.pause()

            assert editor._active_predicate is None
            assert editor._view_filter_mode == 1
            textarea = editor.query_one("#journal_textarea", TextArea)
            # Cleared only: "Opening balances" (*) visible, others not.
            assert "Opening balances" in textarea.text
            assert "Groceries" not in textarea.text

    async def test_view_filter_bar_shows_criteria_label(self, tmp_path: Path) -> None:
        journal = tmp_path / "test.journal"
        journal.write_text(THREE_TXN_JOURNAL, encoding="utf-8")

        app = LedgerApp(journal)
        async with app.run_test(size=(120, 30)) as pilot:
            editor = pilot.app.query_one(JournalEditor)
            predicate = lambda tx: True  # noqa: E731
            editor.apply_criteria_filter(predicate)
            await pilot.pause()

            bar = editor.query_one(ViewFilterBar)
            label = bar.query_one("#filter-label")
            assert "Ctrl+O" in str(label.content)


class TestFilterAppMessageWiring:
    """FilterPopup posts messages LedgerApp relays to JournalEditor."""

    async def test_toggle_filter_mounts_and_removes_popup(self, tmp_path: Path) -> None:
        journal = tmp_path / "test.journal"
        journal.write_text(THREE_TXN_JOURNAL, encoding="utf-8")

        app = LedgerApp(journal)
        async with app.run_test(size=(120, 30)) as pilot:
            assert not pilot.app.query(FilterPopup)
            pilot.app.action_toggle_filter()
            await pilot.pause()
            assert pilot.app.query(FilterPopup)
            pilot.app.action_toggle_filter()
            await pilot.pause()
            assert not pilot.app.query(FilterPopup)

    async def test_closing_popup_does_not_clear_applied_filter(
        self, tmp_path: Path
    ) -> None:
        journal = tmp_path / "test.journal"
        journal.write_text(THREE_TXN_JOURNAL, encoding="utf-8")

        app = LedgerApp(journal)
        async with app.run_test(size=(120, 30)) as pilot:
            await _open_filter_and_fill(pilot, account="expenses:rent")
            popup = pilot.app.query_one(FilterPopup)
            popup.apply_filter()
            await pilot.pause()

            popup.action_close_self()
            await pilot.pause()

            editor = pilot.app.query_one(JournalEditor)
            assert editor._active_predicate is not None
            textarea = editor.query_one("#journal_textarea", TextArea)
            assert "Rent" in textarea.text
            assert "Groceries" not in textarea.text
