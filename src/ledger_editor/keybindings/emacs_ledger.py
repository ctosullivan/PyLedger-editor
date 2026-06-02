"""Emacs Ledger-mode keyboard convention action stubs.

All actions are declared here as stubs. They will be wired into TransactionTable
via Textual's BINDINGS list and action_* handler methods.

Shortcut reference (full table in docs/shortcuts.md):
  Tab                     Autocomplete account name / payee from known entries
  Shift+Up / Shift+Down   Shift the date sub-field under the cursor (year/month/day)
  Shift+Alt+Up / Down     Increment / decrement date by one month (reserved)
  Ctrl+Right / Left       Skip to next / previous field (date→payee→account→amount)
  Ctrl+Up / Down          Move to next / previous transaction block
  Ctrl+Shift+Right/Left   Select to end / start of current field
  Ctrl+Shift+Up/Down      Select entire transaction block above / below
  Alt+P / Alt+N           Insert previous / next matching transaction (M-p / M-n)
  Ctrl+Enter              Finalise / commit current transaction entry
  Ctrl+K                  Kill (delete) to end of line

Known terminal-emulator conflicts are documented in knowledge_base/design_decisions.md.
"""

from __future__ import annotations

__all__ = ["EmacsLedgerBindings"]


class EmacsLedgerBindings:
    """Mixin providing Emacs Ledger-mode keyboard action stubs.

    Compose into a Textual App or Widget subclass alongside OfficeBindings.
    """

    def action_autocomplete(self) -> None:
        """Autocomplete account name or payee from Journal.declared_accounts (Tab).

        Uses PyLedger.load(path).declared_accounts and journal.accounts() for
        completion candidates. Falls back to all accounts seen in postings.
        """
        # TODO: implement Tab autocomplete

    def action_date_shift_up(self) -> None:
        """Shift up the date sub-field under the cursor (Shift+Up).

        Increments the year, month, or day — whichever the cursor column is over.
        Implemented directly in JournalEditor; this stub documents the intent.
        """
        # Implemented in JournalEditor._shift_date_by(+1)

    def action_date_shift_down(self) -> None:
        """Shift down the date sub-field under the cursor (Shift+Down).

        Decrements the year, month, or day — whichever the cursor column is over.
        Implemented directly in JournalEditor; this stub documents the intent.
        """
        # Implemented in JournalEditor._shift_date_by(-1)

    def action_date_increment_month(self) -> None:
        """Increment the date field by one month (Shift+Alt+Up)."""
        # TODO: implement

    def action_date_decrement_month(self) -> None:
        """Decrement the date field by one month (Shift+Alt+Down)."""
        # TODO: implement

    def action_field_next(self) -> None:
        """Move focus to the next field: date → payee → account → amount (Ctrl+Right)."""
        # TODO: implement

    def action_field_prev(self) -> None:
        """Move focus to the previous field (Ctrl+Left)."""
        # TODO: implement

    def action_txn_next(self) -> None:
        """Move cursor to the next transaction block (Ctrl+Down)."""
        # TODO: implement

    def action_txn_prev(self) -> None:
        """Move cursor to the previous transaction block (Ctrl+Up)."""
        # TODO: implement

    def action_select_to_field_end(self) -> None:
        """Select from cursor to end of current field (Ctrl+Shift+Right)."""
        # TODO: implement

    def action_select_to_field_start(self) -> None:
        """Select from cursor to start of current field (Ctrl+Shift+Left)."""
        # TODO: implement

    def action_select_txn_above(self) -> None:
        """Select the entire transaction block above the cursor (Ctrl+Shift+Up)."""
        # TODO: implement

    def action_select_txn_below(self) -> None:
        """Select the entire transaction block below the cursor (Ctrl+Shift+Down)."""
        # TODO: implement

    def action_insert_prev_matching(self) -> None:
        """Insert the previous matching transaction template (Alt+P / Emacs M-p)."""
        # TODO: implement

    def action_insert_next_matching(self) -> None:
        """Insert the next matching transaction template (Alt+N / Emacs M-n)."""
        # TODO: implement

    def action_commit_transaction(self) -> None:
        """Finalise and commit the current transaction entry (Ctrl+Enter)."""
        # TODO: implement

    def action_kill_line(self) -> None:
        """Delete from cursor to end of current line (Ctrl+K)."""
        # TODO: implement
