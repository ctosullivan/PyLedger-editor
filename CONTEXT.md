# CONTEXT.md — Session Working Memory

## Current Task

Fix directive/comment loss when cycling through the reconcile view filter (Ctrl+L).

## Where We Are

All code changes done. 220 tests pass. Not yet committed.

## Decisions In Flight

- `_filter_non_txn_blocks` is snapshotted from the raw textarea text at filter-entry time
  (mode 0 → 1), using `split_journal_segments` which relies on `Transaction.source_span`.
- The mode-0 restore path weaves blocks between transactions using `transaction_to_text`
  per transaction (same as `action_save`), preserving the normalized formatting.
- If transaction count changes in the filtered view (adds/deletes), the restore falls back
  to preamble-only (if available) or `journal_to_text` — directives may be lost in that
  edge case, but it is safe and was the previous behaviour.
- `_filter_non_txn_blocks` is cleared alongside `_filter_journal` when mode resets to 0.
- The filtered display (modes 1 and 2) remains transactions-only — directives are NOT
  shown in filtered views, which is intentional.
- `atomic_edit()` accesses `text_area.history._undo_stack` (Textual private API).
- `split_journal_segments` uses `Transaction.source_span` (1-based inclusive lines).
- `journal_to_text()` is no longer used in either `action_save` or `_apply_view_filter`
  mode-0; it remains as a fallback only.

## Files Changed This Session (cumulative from session start)

| File | Change |
|---|---|
| `vendor/pyledger/` | Full directory replaced: ctosullivan/PyLedger@b2d10be (v0.5.1) |
| `pyproject.toml` | `PyLedger==0.5.0` → `==0.5.1`; ledger-editor `0.8.2` → `0.9.0` |
| `CLAUDE.md` | PyLedger version reference updated |
| `requirements.txt` | Refreshed |
| `knowledge_base/pyledger_api_notes.md` | v0.5.1 notes added |
| `src/ledger_editor/utils/ledger_io.py` | Added `split_preamble`, `split_journal_segments`, `_TXN_DATE_RE` |
| `src/ledger_editor/widgets/transaction_table.py` | `action_save`: segment-based reassembly; `__init__`: `_filter_non_txn_blocks`; `action_cycle_view_filter`: snapshot non-txn blocks; `_apply_view_filter` mode-0: weave restore |
| `tests/test_ledger_io.py` | `TestSplitPreamble` + `TestSplitJournalSegments` |
| `tests/test_view_filter.py` | `DIRECTIVE_JOURNAL` fixture + `TestViewFilterDirectivePreservation` (4 tests) |
| `dev-docs/api-spec.md` | `split_preamble` + `split_journal_segments` signatures |
| `CHANGELOG.md` | 3 new `[Unreleased]` entries |

## What NOT To Revisit

- ReconcileMixin / reconcile mode — deliberately removed in v0.8.0
- BalanceSidebar / RegisterPanel — deliberately removed in v0.8.0
- The 65%/35% split layout — replaced by full-width editor in v0.8.0
- `FilterPopup.apply_filter()` — out-of-scope stub; do not touch

## Authoritative Settled Facts

- `Transaction` uses `cleared: bool` and `pending: bool`
- `journal_to_text()` does not preserve directives; the editor no longer calls it for
  save output or mode-0 restore — it calls `transaction_to_text()` per transaction
- `split_journal_segments(text, txns)` extracts non-txn blocks using SourceSpan
- `SourceSpan.start_line` / `.end_line` are 1-based inclusive
- `_filter_non_txn_blocks` length = `len(_filter_journal.transactions) + 1`
- Filtered view (modes 1 and 2) is transactions-only — no directives shown in filter

## Blockers / Open Questions

None.

## Recent Git State

```
5f86436 feat: preserve directives on save; update PyLedger to v0.5.1
29b96e1 chore: ignore all .ps1 files
(above session's post-commit changes not yet committed)
```
