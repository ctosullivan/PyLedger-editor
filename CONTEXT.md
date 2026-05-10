## Current Task

Milestone 2 (Text Editor + Register Panel) is implemented. All items are
functionally complete. Ready for user UAT or to begin Milestone 3.

## Where We Are

87/87 pytest passing. The app now shows raw hledger text in a TextArea editor.
The right panel has BalanceSidebar (top) and RegisterPanel (bottom). Selecting
an account (by cursor or tree click) updates the register panel.

Launch: `.\run_uat.ps1` or `.venv\Scripts\python.exe -m ledger_editor <file>`

## Decisions In Flight

None.

## Files Currently Relevant

- src/ledger_editor/widgets/transaction_table.py — JournalEditor (TextArea-based)
- src/ledger_editor/widgets/balance_sidebar.py — AccountSelected message added
- src/ledger_editor/widgets/register_panel.py — NEW: RegisterPanel widget
- src/ledger_editor/app.py — Vertical right panel, 3 message handlers
- tests/test_transaction_table.py — 17 tests (5+4 pure, 8 async)
- tests/test_balance_sidebar.py — 6 tests
- tests/test_register_panel.py — NEW: 9 tests (4 pure, 5 async)
- tests/fixtures/large.journal — NEW: 11 transactions for register limit test

## What NOT To Revisit

- Transaction status model: uses `cleared: bool` and `pending: bool` (NOT `flag: str`)
- Shift+C: operates on TextArea text in-place via `textarea.replace()`; posting lines ignored
- Ctrl+S: writes via `Path.write_text(journal_to_text(...))` NOT `EditorDocument.save()`
- `run_basic_checks` is at `PyLedger.checks.run_basic_checks` (not top-level export)
- `journal_to_text()` does NOT preserve comments/directives — known v0.5.0 limitation
- `Query(account=X)` uses substring/regex (child accounts also match) — correct hledger behaviour
- `running_balance` in RegisterPanel is a plain Decimal with no commodity symbol
- Textual version is 0.83.0 (CLAUDE.md says "8.2.5" — that is a typo)
- Test runner: `.venv\Scripts\python.exe -m pytest --tb=short`
- `Label.renderable` does not exist in Textual 0.83.0 — use `panel._current_account` in tests
- App message handlers use `self.query(WidgetClass)` (not `query_one`) to guard against teardown races

## Recent Git State

(Run `git log --oneline -5` to populate)
