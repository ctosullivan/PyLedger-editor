## Current Task

Milestone 1 (Core Editing Surface) is implemented. All Milestone 1 items are
functionally complete. Ready for user review or to begin Milestone 2.

## Where We Are

All Milestone 1 widgets are implemented and tested (78/78 pytest). The app can be
launched with `.venv\Scripts\python.exe -m ledger_editor <file.journal>`.

Next step (when directed): begin Milestone 2 — Keybindings & Autocomplete.

## Decisions In Flight

None — all Milestone 1 decisions are resolved.

## Files Currently Relevant

- src/ledger_editor/widgets/transaction_table.py — full DataTable implementation
- src/ledger_editor/widgets/balance_sidebar.py — Tree-based balance sidebar
- src/ledger_editor/app.py — BINDINGS + SaveCompleted handler wired
- tests/test_transaction_table.py — 18 tests (pure function + async widget)
- tests/test_balance_sidebar.py — 5 tests

## Blockers / Open Questions

None currently.

## What NOT To Revisit

- Transaction status model: uses `cleared: bool` and `pending: bool` (NOT `flag: str`)
- Shift+C cycle: 3-state (uncleared → pending → cleared → uncleared)
- Ctrl+D: duplicate once to bottom only (not fill-all — this is Milestone 2)
- Ctrl+S tidy: sort by date + EditorDocument.save() + run_basic_checks + notify
- Test runner: `.venv\Scripts\python.exe -m pytest --tb=short`
- `balance(tree=True)` returns `list[BalanceRow]` — confirmed implemented in v0.5.0
- `run_basic_checks` is at `PyLedger.checks.run_basic_checks` (not top-level export)
- Textual version is 0.83.0 (not 8.2.5 as written in CLAUDE.md — that appears to be a typo)

## Recent Git State

(Run `git log --oneline -5` to populate)
