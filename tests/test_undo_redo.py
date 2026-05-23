"""Pilot tests for undo/redo behaviour in JournalEditor."""

from __future__ import annotations

from pathlib import Path

from ledger_editor.app import LedgerApp
from ledger_editor.widgets.transaction_table import JournalEditor
from textual.widgets import TextArea

FIXTURES = Path(__file__).parent / "fixtures"

TWO_TXN_JOURNAL = (
    "2024-01-10 * Opening balances\n"
    "    assets:bank:checking    £1000.00\n"
    "    equity:opening-balances\n"
    "\n"
    "2024-01-15 Groceries\n"
    "    expenses:food    £42.50\n"
    "    assets:bank:checking\n"
)


class TestAutofillUndo:
    """action_autofill (Ctrl+G) must be reversible with a single Ctrl+Z."""

    async def test_ctrl_z_reverses_autofill(self, tmp_path: Path) -> None:
        """Ctrl+Z after Ctrl+G restores the document to its pre-autofill state."""
        journal = tmp_path / "undo.journal"
        journal.write_text(TWO_TXN_JOURNAL, encoding="utf-8")

        app = LedgerApp(journal)
        async with app.run_test(size=(120, 30)) as pilot:
            editor = pilot.app.query_one(JournalEditor)
            textarea = editor.query_one("#journal_textarea", TextArea)

            original_text = textarea.text
            lines = textarea.text.splitlines()
            header_row = next(i for i, l in enumerate(lines) if "Groceries" in l)
            textarea.move_cursor((header_row, 0))

            editor.action_autofill()
            await pilot.pause()

            assert textarea.text != original_text, "Autofill should have changed text"

            editor.action_undo()
            await pilot.pause()

            assert textarea.text == original_text, (
                "Single Ctrl+Z should fully reverse autofill"
            )

    async def test_command_history_empty_undo_falls_through(self, tmp_path: Path) -> None:
        """When CommandHistory is empty, Ctrl+Z delegates to TextArea native undo."""
        journal = tmp_path / "fallthrough.journal"
        journal.write_text(TWO_TXN_JOURNAL, encoding="utf-8")

        app = LedgerApp(journal)
        async with app.run_test(size=(120, 30)) as pilot:
            editor = pilot.app.query_one(JournalEditor)

            assert not editor._command_history.can_undo
            editor.action_undo()
            await pilot.pause()

    async def test_autofill_undo_does_not_consume_prior_native_edits(
        self, tmp_path: Path
    ) -> None:
        """Native text edits before Ctrl+G remain on the undo stack after Ctrl+G is undone."""
        journal = tmp_path / "stack.journal"
        journal.write_text(TWO_TXN_JOURNAL, encoding="utf-8")

        app = LedgerApp(journal)
        async with app.run_test(size=(120, 30)) as pilot:
            editor = pilot.app.query_one(JournalEditor)
            textarea = editor.query_one("#journal_textarea", TextArea)

            # Move to end of first header and type a character to create a native undo entry.
            textarea.move_cursor((0, len(textarea.text.splitlines()[0])))
            await pilot.press("x")
            await pilot.pause()
            after_typing = textarea.text

            # Autofill, then undo it.
            lines = textarea.text.splitlines()
            header_row = next(i for i, l in enumerate(lines) if "Groceries" in l)
            textarea.move_cursor((header_row, 0))
            editor.action_autofill()
            await pilot.pause()

            editor.action_undo()
            await pilot.pause()

            # The document should be back to the state after typing "x", not the original.
            assert textarea.text == after_typing, (
                "After undoing autofill, the pre-autofill state (with typed 'x') should be restored"
            )
