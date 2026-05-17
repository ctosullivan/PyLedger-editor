# CONTEXT.md — Session Working Memory

## Current Task
v0.8.0 major refactor complete: balance sidebar, register panel, and all reconcile
machinery removed; app is now a pure hledger text editor with a Ctrl+L view filter.

## Where We Are
All code complete and tests passing (175/175). Ready for UAT.

## Decisions In Flight
None.

## Files Currently Relevant

| File | Role |
|---|---|
| `src/ledger_editor/app.py` | LedgerApp — full-width JournalEditor, no right panel |
| `src/ledger_editor/widgets/transaction_table.py` | JournalEditor — main editor, Ctrl+L filter, search |
| `src/ledger_editor/widgets/view_filter_bar.py` | ViewFilterBar — 1-row filter status display |
| `src/ledger_editor/widgets/search_bar.py` | SearchBar — now contains `_find_transaction_header_above` (moved from deleted reconcile_actions.py) |
| `src/ledger_editor/widgets/ledger_textarea.py` | LedgerTextArea — syntax highlighting, search highlights |
| `src/ledger_editor/widgets/filter_popup.py` | FilterPopup — Ctrl+Shift+P overlay (unchanged) |
| `tests/test_view_filter.py` | 12 new tests for Ctrl+L filter feature |

## What Was Removed
- `balance_sidebar.py`, `register_panel.py` — right panel widgets
- `reconcile_bar.py`, `reconcile_summary.py`, `reconcile_actions.py` — reconcile machinery
- `tests/test_balance_sidebar.py`, `tests/test_register_panel.py`
- From transaction_table.py: ReconcileMixin, all _reconcile_* state, debounce timer,
  LiveChanged, CursorAccountChanged, ReconcileModeEntered, ReconcileModeExited,
  TransactionClearedToggled messages, Ctrl+I and Ctrl+Enter bindings

## What Was Added
- `view_filter_bar.py`: ViewFilterBar widget (Ctrl+L mode indicator)
- Ctrl+L binding + `action_cycle_view_filter()` in JournalEditor
- `_apply_view_filter()`, `_merge_filtered_edits()` for snapshot/merge logic
- `action_save()` merges filter before writing full journal

## View Filter Design
- Mode 0=All, 1=Cleared only, 2=Unreconciled only
- `_filter_journal`: PyLedger Journal snapshot from when filter was entered
- `_filter_visible_indices`: list[int] tracking which tx indices are visible
- Merge strategy: slot-by-slot replacement, extend for additions, delete for removals
- Ctrl+S while filtered: merge + restore All mode first, then save full journal

## Blockers / Open Questions
None. Awaiting UAT.

## What NOT To Revisit
- ReconcileMixin / reconcile mode — deliberately removed by design
- BalanceSidebar / RegisterPanel — deliberately removed by design
- The 65%/35% split layout — replaced by full-width editor

## Recent Git State
```
359114a feat: UAT round 2 fixes, Ctrl+D insert-date, scroll fix (v0.6.0)
375beee feat: hledger syntax highlighting, Monokai Pro theme, UAT fixes (v0.5.0)
4908d58 feat: scrollable register panel, 65% editor width (v0.4.0)
463d5b8 fix: rebind toggle-cleared to Ctrl+R, block-select to Ctrl+T
ee2b358 feat: UAT fixes — keybindings, navigation, focus cycle (v0.3.0)
```
(All v0.7.x–v0.8.0 work is uncommitted)
