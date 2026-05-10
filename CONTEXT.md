## Current Task

Layout and register UX polish complete (v0.4.0). All 96 tests passing.

## Where We Are

96/96 pytest passing. Three UAT Round 3 issues resolved:
1. Toggle cleared rebound: Ctrl+R (was Ctrl+Shift+A — still not working in UAT).
2. Transaction block selection rebound: Ctrl+T selects entire block (was Alt+Shift+Up/Down — still not working in UAT). Single action: selects header through last posting regardless of cursor position.
3. Ctrl+Shift+Home/End: removed from scope (bindings and action methods deleted).

Launch: `.\run_uat.ps1` or `.venv\Scripts\python.exe -m ledger_editor <file>`

## Decisions In Flight

None.

## Files Currently Relevant

- src/ledger_editor/app.py — COMMAND_PALETTE_DISPLAY; priority Ctrl+Shift+F binding; width: 80 right panel
- src/ledger_editor/widgets/transaction_table.py — all JournalEditor bindings; _find_transaction_block; block-select + nav actions
- src/ledger_editor/widgets/balance_sidebar.py — priority Tab/Shift+Tab focus bindings
- src/ledger_editor/widgets/register_panel.py — priority Tab/Shift+Tab focus bindings
- tests/test_transaction_table.py — 96 tests (9 pure, 12 async)
- docs/shortcuts.md — full updated keybinding reference

## What NOT To Revisit

- Transaction status model: uses `cleared: bool` and `pending: bool` (NOT `flag: str`)
- Ctrl+Shift+C and Ctrl+Shift+A bindings are GONE — toggle cleared is now Ctrl+R
- Ctrl+Shift+Up/Down and Alt+Shift+Up/Down for block selection are GONE — use Ctrl+T
- Ctrl+Shift+Home/End are GONE — removed from scope
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
