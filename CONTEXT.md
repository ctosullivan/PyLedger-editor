## Current Task

UAT Batch 3 fixes complete. All 97 tests passing. Ready for re-UAT or Milestone 3.

## Where We Are

97/97 pytest passing. Six UAT Round 2 issues resolved:
1. Command palette caret fixed — `COMMAND_PALETTE_DISPLAY = "Ctrl+P"` on LedgerApp.
2. Toggle-cleared rebound: Ctrl+Shift+A (was Ctrl+Shift+C — Textual collision).
3. Block selection rebound: Alt+Shift+Up/Down (was Ctrl+Shift+Up/Down — Windows Terminal intercepts those).
4. Ctrl+Home/End added — moves cursor to start/end of file.
5. Ctrl+A overrides TextArea default (which was cursor_line_start) — now selects all.
6. Ctrl+Shift+Home/End added — selects from cursor to file start/end.
7. Tab focus cycle fixed — priority=True Tab/Shift+Tab bindings on BalanceSidebar and RegisterPanel; cycle is TextArea → Tree → DataTable → TextArea.

Launch: `.\run_uat.ps1` or `.venv\Scripts\python.exe -m ledger_editor <file>`

## Decisions In Flight

None.

## Files Currently Relevant

- src/ledger_editor/app.py — COMMAND_PALETTE_DISPLAY; priority Ctrl+Shift+F binding; width: 80 right panel
- src/ledger_editor/widgets/transaction_table.py — all JournalEditor bindings; _find_transaction_block; block-select + nav actions
- src/ledger_editor/widgets/balance_sidebar.py — priority Tab/Shift+Tab focus bindings
- src/ledger_editor/widgets/register_panel.py — priority Tab/Shift+Tab focus bindings
- tests/test_transaction_table.py — 27 tests (9 pure, 13 async)
- docs/shortcuts.md — full updated keybinding reference

## What NOT To Revisit

- Transaction status model: uses `cleared: bool` and `pending: bool` (NOT `flag: str`)
- Shift+C and Ctrl+Shift+C bindings are GONE — toggle cleared is now Ctrl+Shift+A
- Ctrl+Shift+Up/Down for block selection is GONE — use Alt+Shift+Up/Down (terminal conflict)
- Ctrl+S: writes via `Path.write_text(journal_to_text(...))` NOT `EditorDocument.save()`
- `run_basic_checks` is at `PyLedger.checks.run_basic_checks` (not top-level export)
- `journal_to_text()` does NOT preserve comments/directives — known v0.5.0 limitation
- `Query(account=X)` uses substring/regex (child accounts also match) — correct hledger behaviour
- `running_balance` in RegisterPanel is a plain Decimal with no commodity symbol
- Textual version is 0.83.0 (CLAUDE.md says "8.2.5" — that is a typo)
- Test runner: `.venv\Scripts\python.exe -m pytest --tb=short`
- `Label.renderable` does not exist in Textual 0.83.0 — use `panel._current_account` in tests
- App message handlers use `self.query(WidgetClass)` (not `query_one`) to guard against teardown races
- DataTable cells do not word-wrap — wider panel (80 chars text editor) is the mitigation
- `Ctrl+A` in Textual 0.83.0 TextArea defaults to `cursor_line_start` — we override with priority=True select_all
- `Ctrl+Shift+Left/Right` in TextArea does word-by-word selection (does NOT snap to end of line — expected behaviour)
- FilterPopup `apply_filter()` is a TODO stub — no actual filtering implemented; planned as Milestone 3

## Recent Git State

(Run `git log --oneline -5` to populate)
