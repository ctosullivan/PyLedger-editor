"""Tests for LedgerTextArea (ledger_textarea.py), in particular the
scroll_cursor_visible() context-margin override.

Textual's TextArea._watch_selection() calls scroll_cursor_visible() on every
move_cursor(), so this override — not the individual navigation actions —
is the single place responsible for how much context is kept around the
cursor when scrolling in either direction.
"""
from pathlib import Path
from unittest.mock import patch

from ledgerkit_editor.app import LedgerApp
from ledgerkit_editor.widgets.ledger_textarea import LedgerTextArea
from ledgerkit_editor.widgets.transaction_table import JournalEditor

FIXTURES = Path(__file__).parent / "fixtures"


class TestScrollCursorVisiblePadding:
    """scroll_cursor_visible() must reserve equal context above and below."""

    async def test_spacing_top_equals_bottom(self) -> None:
        """Direct call: the Spacing passed to scroll_to_region is symmetric."""
        app = LedgerApp(FIXTURES / "sample.journal")
        async with app.run_test(size=(120, 30)) as pilot:
            editor = pilot.app.query_one(JournalEditor)
            textarea = editor.query_one("#journal_textarea", LedgerTextArea)

            with patch.object(
                textarea, "scroll_to_region", wraps=textarea.scroll_to_region
            ) as spy:
                textarea.scroll_cursor_visible()

            spacing = spy.call_args.kwargs["spacing"]
            assert spacing.top == spacing.bottom == 4

    async def test_prev_transaction_navigation_uses_symmetric_spacing(
        self, tmp_path: Path
    ) -> None:
        """Shift+PgUp (action_prev_transaction) moves the cursor via
        move_cursor(), which must reach this same symmetric-margin override —
        not some other, unpadded scroll path — when navigating upward."""
        journal = tmp_path / "many.journal"
        journal.write_text(
            "\n\n".join(
                f"2024-01-{i:02d} Transaction {i}\n"
                f"    expenses:misc    {i}.00\n"
                f"    assets:bank:checking"
                for i in range(1, 15)
            )
            + "\n",
            encoding="utf-8",
        )

        app = LedgerApp(journal)
        async with app.run_test(size=(80, 14)) as pilot:
            editor = pilot.app.query_one(JournalEditor)
            textarea = editor.query_one("#journal_textarea", LedgerTextArea)

            # Move to the last transaction header first (scrolls down).
            for _ in range(13):
                editor.action_next_transaction()
            await pilot.pause()

            with patch.object(
                textarea, "scroll_to_region", wraps=textarea.scroll_to_region
            ) as spy:
                editor.action_prev_transaction()
                await pilot.pause()

            assert spy.call_args is not None, "expected a scroll_to_region call"
            spacing = spy.call_args.kwargs["spacing"]
            assert spacing.top == spacing.bottom == 4
