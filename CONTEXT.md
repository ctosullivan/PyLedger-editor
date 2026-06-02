# CONTEXT.md — Session Working Memory

## Current Task
Migration to ledgerkit + project rename + commodity formatting — complete.

## Where We Are
All three phases implemented and 281 tests passing. No open tasks.

## Decisions In Flight
None.

## Files Currently Relevant
- `src/ledgerkit_editor/utils/commodity_format.py` — new module (Phase 3)
- `src/ledgerkit_editor/widgets/transaction_table.py` — wired commodity styles in on_mount + action_save
- `vendor/ledgerkit/` — new vendor package (v0.1.0, replaces pyledger)
- `tests/test_commodity_format.py` — new tests (25 tests)
- `tests/fixtures/multicommodity.journal` — new multi-commodity fixture

## Decisions Made This Session
- Negative prefix amounts: ledgerkit parser accepts `-£300.00` (minus first) as
  input but `CommodityStyle.format()` outputs `£-300.00` (symbol first). The
  commodity_format post-processor handles both input forms and normalises to the
  CommodityStyle output form. This matches ledgerkit's own writer convention.
- Project root directory (PyLedger-editor/) was NOT renamed — only the Python
  module inside src/ was renamed (ledger_editor → ledgerkit_editor). The GitHub
  repo URL stays as-is.
- `pyledger_api_notes.md` kept as historical reference; `ledgerkit_api_notes.md`
  is the authoritative current reference.
- vendor/pyledger_old deleted (rollback no longer available).

## What NOT To Revisit
- All PyLedger → ledgerkit renames are complete. Do not add back any PyLedger
  references.
- Phase 3 commodity formatting uses ledgerkit's `Journal.commodity_styles`
  property for detection — no custom detection logic needed.

## Recent Git State
5da045d feat: add --line=N and --theme=THEME CLI arguments; bump to v0.9.4
d6b9585 feat: cursor-position-aware date shifting with Shift+Up/Down; bump to v0.9.3
fad5fa4 fix: preserve directives/comments across filter-view cycle; bump to v0.9.2
3652c73 fix: search bar Tab focus and invisible nav buttons; bump to v0.9.1
5f86436 feat: preserve directives on save; update PyLedger to v0.5.1
