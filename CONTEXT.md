## Current Task

Initial project scaffold is complete. Next: implement widget and keybinding logic
(pending open questions answered — see knowledge_base/design_decisions.md).

## Where We Are

Scaffold committed as v0.0.1. All stub files are in place. `pytest` passes.
Ready to begin implementing TransactionTable and BalanceSidebar widgets.

## Decisions In Flight

None — all scaffold decisions are resolved and recorded in design_decisions.md.

## Files Currently Relevant

- src/ledger_editor/widgets/transaction_table.py — primary editing surface stub
- src/ledger_editor/widgets/balance_sidebar.py — balance tree widget stub
- knowledge_base/design_decisions.md — resolved decisions
- knowledge_base/pyledger_api_notes.md — PyLedger v0.5.0 API reference
- vendor/pyledger/dev-docs/api-spec.md — authoritative API contracts

## Blockers / Open Questions

None currently.

## What NOT To Revisit

- Transaction status model: uses `cleared: bool` and `pending: bool` (NOT `flag: str`)
- Shift+C cycle: 3-state (uncleared → pending → cleared → uncleared)
- Ctrl+D: duplicate once to bottom only (not fill-all)
- Ctrl+S tidy: sort by date + re-align whitespace + warn-and-save
- Test runner: pytest + pytest-asyncio

## Recent Git State

(Run `git log --oneline -5` to populate)
