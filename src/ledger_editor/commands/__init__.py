"""Command palette action stubs for the ledger editor.

Actions registered here appear in the Textual command palette (Ctrl+P by default).
Each action stub will be wired to a handler in LedgerApp or TransactionTable.
"""

from __future__ import annotations

__all__: list[str] = []

# TODO: register command palette providers via Textual's CommandPalette API
# Examples of planned commands:
#   "Open file"        — resolve_journal_file, reload EditorDocument
#   "Save"             — trigger action_save
#   "Filter..."        — open FilterPopup
#   "Go to account"    — jump cursor to first posting for an account
#   "Toggle cleared"   — action_toggle_cleared on selection
