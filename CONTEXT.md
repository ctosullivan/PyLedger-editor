# CONTEXT.md — Session Working Memory

## Current Task
v0.8.2 complete. Documentation and version bump committed and pushed.

## Where We Are
All code changes done, tests passing. Version bumped to 0.8.2. README, ROADMAP,
CHANGELOG updated. Changes committed and pushed to origin/master.

## Decisions In Flight
None.

## Files Currently Relevant

| File | Role |
|---|---|
| `pyproject.toml` | Version bumped from 0.6.0 → 0.8.2 |
| `README.md` | Rewritten: beta warning, accurate features, GitHub install with vendor/pyledger note |
| `ROADMAP.md` | Rewritten: "What Is Shipped" summary, Window Panes Removed note, upcoming milestones |
| `src/ledger_editor/widgets/ledger_textarea.py` | Removed `BINDINGS` class variable and `Binding` import (v0.8.2) |
| `src/ledger_editor/themes/monokai_pro.tcss` | Added `SearchBar Input` and `SearchBar Input:focus` rules (v0.8.2) |
| `src/ledger_editor/widgets/transaction_table.py` | Removed search-bar branch from `action_toggle_cleared` (v0.8.2) |
| `src/ledger_editor/widgets/filter_popup.py` | Added `on_mount` to focus `#date-from` (v0.8.2) |

## What Was Changed (v0.8.2 code)

1. **LedgerTextArea.BINDINGS removed** — The v0.8.1 addition used wrong action names and
   shadowed JournalEditor's visible `ctrl+d` and `ctrl+f` bindings.

2. **SearchBar Input CSS** — Added two monokai-pro-specific rules in `monokai_pro.tcss`
   with higher specificity than the general Input and Input:focus rules. `border: none`
   allows the 1-row height to display text without clipping.

3. **Ctrl+R always toggles cleared** — Removed the `bar.display` search-bar check from
   `action_toggle_cleared`. Ctrl+R no longer navigates search matches.

4. **FilterPopup auto-focus** — Added `on_mount` to FilterPopup that focuses `#date-from`
   on open. Ensures Escape routes to the popup's `close_self` binding.

5. **FilterPopup Account field Enter** — Fixed as side-effect of #4.

## What Was Changed (v0.8.2-meta docs)

- `pyproject.toml` version `0.6.0` → `0.8.2`
- `README.md` rewritten: beta warning, accurate feature list, GitHub install instructions
- `ROADMAP.md` rewritten: replaces stale milestone checklist with current state

## What NOT To Revisit
- ReconcileMixin / reconcile mode — deliberately removed in v0.8.0
- BalanceSidebar / RegisterPanel — deliberately removed in v0.8.0
- The 65%/35% split layout — replaced by full-width editor in v0.8.0

## Recent Git State
```
(committed and pushed after v0.8.2 doc/meta changes)
359114a feat: UAT round 2 fixes, Ctrl+D insert-date, scroll fix (v0.6.0)
```

## Blockers / Open Questions
None. Awaiting UAT of v0.8.2 code changes (search bar CSS fix in focus state).
