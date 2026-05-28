# Context — 2026-05-28

## Current Task
Bugfix shipped: column-0 `;`/`#` comments inside open transaction blocks now correctly ignored.

## Where We Are
Released as v0.5.1. No pending work.

## Decisions In Flight
None.

## Files Currently Relevant
None — work complete.

## Blockers / Open Questions
None.

## What NOT To Revisit
- `lstrip()` approach for comment detection — replaced by `is_indented = line[0:1].isspace()` gate; do not revert.
- `#` is intentionally not an inline comment delimiter (only `;` is). This matches hledger spec.

## Recent Git State
```
fix: correct column-0 comment handling inside open transaction blocks
8b5fc81 chore: release v0.5.0 and mark Milestone 3 done
d393b8c feat: Milestone 3 — lenient parser, multi-commodity balance, tree mode, CheckError.line_number
d012bfe chore: release v0.3.0 and mark Milestone 2 done
6ca9fb0 chore: release v0.3.0 and mark Milestone 2 done
```
