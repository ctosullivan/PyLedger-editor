"""Tests for the Ctrl+O transaction filter (FilterPopup + JournalEditor wiring).

Covers the criteria-filter path end-to-end: FilterPopup builds and posts a
validated predicate; LedgerApp (not JournalEditor — FilterPopup is a
sibling, not a child, see app.py's on_filter_popup_filter_applied) relays it
to JournalEditor.apply_criteria_filter(). Combining with Ctrl+L (they share
view_filter.py's engine) is also covered here, in TestFilterCombination.
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

    async def test_last_month_alone_is_bounded_to_that_month(
        self, tmp_path: Path
    ) -> None:
        """UAT finding: Date From = "last month" with Date To blank was
        showing everything since the 1st of last month (open-ended,
        including this month), not just last month. Fixed in
        date_parser.parse_date_range()'s period auto-fill."""
        import datetime

        today = datetime.date.today()
        last_month_end = today.replace(day=1) - datetime.timedelta(days=1)
        last_month_start = last_month_end.replace(day=1)
        # A day safely inside last month, and a day safely inside this
        # month, regardless of which day of the month "today" actually is.
        in_last_month = last_month_start + datetime.timedelta(
            days=min(4, (last_month_end - last_month_start).days)
        )
        this_month_day = today.replace(day=1)

        journal_text = (
            f"{in_last_month.isoformat()} Last Month Txn\n"
            "    expenses:misc    £10.00\n"
            "    assets:bank:checking\n"
            "\n"
            f"{this_month_day.isoformat()} This Month Txn\n"
            "    expenses:misc    £20.00\n"
            "    assets:bank:checking\n"
        )
        journal = tmp_path / "test.journal"
        journal.write_text(journal_text, encoding="utf-8")

        app = LedgerApp(journal)
        async with app.run_test(size=(120, 30)) as pilot:
            await _open_filter_and_fill(pilot, **{"date-from": "last month"})
            popup = pilot.app.query_one(FilterPopup)
            popup.apply_filter()
            await pilot.pause()

            editor = pilot.app.query_one(JournalEditor)
            textarea = editor.query_one("#journal_textarea", TextArea)
            assert "Last Month Txn" in textarea.text
            assert "This Month Txn" not in textarea.text

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

    async def test_empty_filter_is_a_true_noop(self, tmp_path: Path) -> None:
        """UAT finding: an all-blank Apply was reformatting the document
        (losing source spacing) and marking it modified, even though
        nothing was actually being filtered. Empty Apply must leave the
        text byte-for-byte unchanged."""
        journal = tmp_path / "test.journal"
        journal.write_text(THREE_TXN_JOURNAL, encoding="utf-8")

        app = LedgerApp(journal)
        async with app.run_test(size=(120, 30)) as pilot:
            editor = pilot.app.query_one(JournalEditor)
            textarea = editor.query_one("#journal_textarea", TextArea)
            original_text = textarea.text
            assert original_text == THREE_TXN_JOURNAL

            await _open_filter_and_fill(pilot)
            popup = pilot.app.query_one(FilterPopup)
            popup.apply_filter()
            await pilot.pause()

            assert textarea.text == original_text
            assert editor._active_predicate is None
            assert editor._view_filter_mode == 0

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

    async def test_clear_button_empties_input_fields(self, tmp_path: Path) -> None:
        """UAT finding: Clear should reset the popup's own text fields, not
        just the applied filter."""
        journal = tmp_path / "test.journal"
        journal.write_text(THREE_TXN_JOURNAL, encoding="utf-8")

        app = LedgerApp(journal)
        async with app.run_test(size=(120, 30)) as pilot:
            await _open_filter_and_fill(
                pilot, account="rent", payee="Rent", **{"date-from": "2024-01-01"}
            )
            popup = pilot.app.query_one(FilterPopup)

            await pilot.click("#btn-clear")
            await pilot.pause()

            assert popup.query_one("#account", Input).value == ""
            assert popup.query_one("#payee", Input).value == ""
            assert popup.query_one("#date-from", Input).value == ""
            assert popup.query_one("#date-to", Input).value == ""

    async def test_empty_apply_clears_an_active_filter(self, tmp_path: Path) -> None:
        """Applying with every field blank while a filter IS active clears
        it, same as the Clear button — an empty Apply isn't a "match
        everything" filter, it means "no filter"."""
        journal = tmp_path / "test.journal"
        journal.write_text(THREE_TXN_JOURNAL, encoding="utf-8")

        app = LedgerApp(journal)
        async with app.run_test(size=(120, 30)) as pilot:
            editor = pilot.app.query_one(JournalEditor)
            predicate = lambda tx: tx.description == "Rent"  # noqa: E731
            editor.apply_criteria_filter(predicate)
            await pilot.pause()

            await _open_filter_and_fill(pilot)
            popup = pilot.app.query_one(FilterPopup)
            popup.apply_filter()
            await pilot.pause()

            textarea = editor.query_one("#journal_textarea", TextArea)
            assert "Groceries" in textarea.text
            assert editor._active_predicate is None


class TestFilterCombination:
    """Ctrl+L and Ctrl+O are independent dimensions that COMBINE with AND —
    reversed from Phase 3's original "replace" (mutually exclusive)
    semantics, per UAT feedback. See planning/next-release-phase-plan.md's
    Phase 3 "Interaction with Ctrl+L" note for the history."""

    async def test_criteria_filter_narrows_an_active_ctrl_l_filter(
        self, tmp_path: Path
    ) -> None:
        """Unreconciled-only alone shows Groceries + Rent; adding a Ctrl+O
        predicate for just "Rent" narrows it further (AND), rather than
        discarding the Ctrl+L mode."""
        journal = tmp_path / "test.journal"
        journal.write_text(THREE_TXN_JOURNAL, encoding="utf-8")

        app = LedgerApp(journal)
        async with app.run_test(size=(120, 30)) as pilot:
            editor = pilot.app.query_one(JournalEditor)
            editor.action_cycle_view_filter()  # -> Cleared (1)
            editor.action_cycle_view_filter()  # -> Unreconciled (2)
            await pilot.pause()
            assert editor._view_filter_mode == 2
            textarea = editor.query_one("#journal_textarea", TextArea)
            assert "Groceries" in textarea.text
            assert "Rent" in textarea.text
            assert "Opening balances" not in textarea.text

            predicate = lambda tx: tx.description == "Rent"  # noqa: E731
            editor.apply_criteria_filter(predicate)
            await pilot.pause()

            assert editor._active_predicate is not None
            assert editor._view_filter_mode == 2  # Ctrl+L mode untouched
            assert "Rent" in textarea.text
            assert "Groceries" not in textarea.text  # narrowed by Ctrl+O
            assert "Opening balances" not in textarea.text

    async def test_ctrl_l_narrows_an_active_criteria_filter(
        self, tmp_path: Path
    ) -> None:
        """A Ctrl+O predicate matching everything, then narrowed by Ctrl+L's
        Cleared-only mode on top — not replaced by it."""
        journal = tmp_path / "test.journal"
        journal.write_text(THREE_TXN_JOURNAL, encoding="utf-8")

        app = LedgerApp(journal)
        async with app.run_test(size=(120, 30)) as pilot:
            editor = pilot.app.query_one(JournalEditor)
            predicate = lambda tx: True  # noqa: E731
            editor.apply_criteria_filter(predicate)
            await pilot.pause()
            textarea = editor.query_one("#journal_textarea", TextArea)
            assert "Opening balances" in textarea.text
            assert "Groceries" in textarea.text
            assert "Rent" in textarea.text

            editor.action_cycle_view_filter()  # -> Cleared, combines with predicate

            await pilot.pause()

            assert editor._active_predicate is not None  # NOT cleared by Ctrl+L
            assert editor._view_filter_mode == 1
            assert "Opening balances" in textarea.text
            assert "Groceries" not in textarea.text
            assert "Rent" not in textarea.text

    async def test_clearing_ctrl_o_leaves_ctrl_l_mode_active(
        self, tmp_path: Path
    ) -> None:
        journal = tmp_path / "test.journal"
        journal.write_text(THREE_TXN_JOURNAL, encoding="utf-8")

        app = LedgerApp(journal)
        async with app.run_test(size=(120, 30)) as pilot:
            editor = pilot.app.query_one(JournalEditor)
            editor.action_cycle_view_filter()  # -> Cleared (1)
            await pilot.pause()
            predicate = lambda tx: tx.description == "Nonexistent"  # noqa: E731
            editor.apply_criteria_filter(predicate)
            await pilot.pause()
            textarea = editor.query_one("#journal_textarea", TextArea)
            assert textarea.text.strip() == ""  # AND of both -> nothing matches

            editor.clear_criteria_filter()
            await pilot.pause()

            assert editor._active_predicate is None
            assert editor._view_filter_mode == 1  # Ctrl+L mode preserved
            assert "Opening balances" in textarea.text
            assert "Groceries" not in textarea.text

    async def test_cycling_ctrl_l_back_to_all_leaves_ctrl_o_active(
        self, tmp_path: Path
    ) -> None:
        journal = tmp_path / "test.journal"
        journal.write_text(THREE_TXN_JOURNAL, encoding="utf-8")

        app = LedgerApp(journal)
        async with app.run_test(size=(120, 30)) as pilot:
            editor = pilot.app.query_one(JournalEditor)
            predicate = lambda tx: tx.description == "Rent"  # noqa: E731
            editor.apply_criteria_filter(predicate)
            await pilot.pause()
            editor.action_cycle_view_filter()  # -> Cleared (1)
            editor.action_cycle_view_filter()  # -> Unreconciled (2)
            editor.action_cycle_view_filter()  # -> All (0)
            await pilot.pause()

            assert editor._view_filter_mode == 0
            assert editor._active_predicate is not None  # Ctrl+O still active
            textarea = editor.query_one("#journal_textarea", TextArea)
            assert "Rent" in textarea.text
            assert "Groceries" not in textarea.text  # still narrowed by Ctrl+O

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

    async def test_view_filter_bar_shows_combined_label(self, tmp_path: Path) -> None:
        journal = tmp_path / "test.journal"
        journal.write_text(THREE_TXN_JOURNAL, encoding="utf-8")

        app = LedgerApp(journal)
        async with app.run_test(size=(120, 30)) as pilot:
            editor = pilot.app.query_one(JournalEditor)
            editor.action_cycle_view_filter()  # -> Cleared (1)
            await pilot.pause()
            predicate = lambda tx: True  # noqa: E731
            editor.apply_criteria_filter(predicate)
            await pilot.pause()

            bar = editor.query_one(ViewFilterBar)
            label = str(bar.query_one("#filter-label").content)
            assert "Cleared only" in label
            assert "Ctrl+O" in label


class TestFilterPopupAutocomplete:
    """Tab in the Account/Payee fields completes against JournalEditor's
    account/payee index — the same bash-style cycling convention as the
    main editor's Tab autocomplete (FilterPopup.action_complete_field)."""

    async def test_tab_completes_account_field(self, tmp_path: Path) -> None:
        journal = tmp_path / "test.journal"
        journal.write_text(THREE_TXN_JOURNAL, encoding="utf-8")

        app = LedgerApp(journal)
        async with app.run_test(size=(120, 30)) as pilot:
            app.action_toggle_filter()
            await pilot.pause()
            popup = app.query_one(FilterPopup)
            account_field = popup.query_one("#account", Input)
            account_field.value = "expenses:"
            account_field.focus()
            await pilot.pause()

            await pilot.press("tab")
            await pilot.pause()

            # Shortest match, alphabetical tiebreak: "expenses:food" before
            # "expenses:rent" (both 13 chars).
            assert account_field.value == "expenses:food"

    async def test_tab_again_cycles_account_candidate(self, tmp_path: Path) -> None:
        journal = tmp_path / "test.journal"
        journal.write_text(THREE_TXN_JOURNAL, encoding="utf-8")

        app = LedgerApp(journal)
        async with app.run_test(size=(120, 30)) as pilot:
            app.action_toggle_filter()
            await pilot.pause()
            popup = app.query_one(FilterPopup)
            account_field = popup.query_one("#account", Input)
            account_field.value = "expenses:"
            account_field.focus()
            await pilot.pause()

            await pilot.press("tab")
            await pilot.pause()
            first = account_field.value

            await pilot.press("tab")
            await pilot.pause()
            second = account_field.value

            assert second != first
            assert second in ("expenses:food", "expenses:rent")

    async def test_tab_completes_payee_field(self, tmp_path: Path) -> None:
        journal = tmp_path / "test.journal"
        journal.write_text(THREE_TXN_JOURNAL, encoding="utf-8")

        app = LedgerApp(journal)
        async with app.run_test(size=(120, 30)) as pilot:
            app.action_toggle_filter()
            await pilot.pause()
            popup = app.query_one(FilterPopup)
            payee_field = popup.query_one("#payee", Input)
            payee_field.value = "Groc"
            payee_field.focus()
            await pilot.pause()

            await pilot.press("tab")
            await pilot.pause()

            assert payee_field.value == "Groceries"

    async def test_tab_with_no_match_falls_through(self, tmp_path: Path) -> None:
        journal = tmp_path / "test.journal"
        journal.write_text(THREE_TXN_JOURNAL, encoding="utf-8")

        app = LedgerApp(journal)
        async with app.run_test(size=(120, 30)) as pilot:
            app.action_toggle_filter()
            await pilot.pause()
            popup = app.query_one(FilterPopup)
            account_field = popup.query_one("#account", Input)
            account_field.value = "zzz_no_such_account"
            account_field.focus()
            await pilot.pause()

            await pilot.press("tab")
            await pilot.pause()

            assert account_field.value == "zzz_no_such_account"

    async def test_tab_on_date_field_does_not_complete(self, tmp_path: Path) -> None:
        """Only Account/Payee complete; Date fields fall through untouched."""
        journal = tmp_path / "test.journal"
        journal.write_text(THREE_TXN_JOURNAL, encoding="utf-8")

        app = LedgerApp(journal)
        async with app.run_test(size=(120, 30)) as pilot:
            app.action_toggle_filter()
            await pilot.pause()
            popup = app.query_one(FilterPopup)
            date_field = popup.query_one("#date-from", Input)
            date_field.value = "2024"
            date_field.focus()
            await pilot.pause()

            await pilot.press("tab")
            await pilot.pause()

            assert date_field.value == "2024"


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
