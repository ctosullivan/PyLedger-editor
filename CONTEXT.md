# CONTEXT.md — Session Working Memory

## Current Task

Full directive preservation on Ctrl+S save: preamble + interleaved directives between transactions.

## Where We Are

All code changes done. 216 tests pass.

## Decisions In Flight

- `atomic_edit()` accesses `text_area.history._undo_stack` (EditHistory private API,
  Textual 0.83.0). This is intentional and documented with a RuntimeError guard. If
  Textual is upgraded, check that `_undo_stack` still exists on `EditHistory`.
- `split_journal_segments` uses `Transaction.source_span` for precise line ranges.
  If source_span is None for any transaction, it falls back to `split_preamble`
  semantics (preamble-only, empty inter/trailing blocks).
- `action_save()` now uses `transaction_to_text(t)` per-transaction instead of
  `journal_to_text(journal)`. The Journal object is still kept for `run_basic_checks`.
- Non-txn blocks maintain their POSITIONAL structure (block i is between the i-th and
  (i+1)-th transaction in the SORTED output). Directives move to the structural gap
  between their adjacent transactions in sorted order, not to the original adjacent
  transactions. This is the most defensible semantics for the general sort case.

## Files Changed This Session

| File | Change |
|---|---|
| `vendor/pyledger/` | Full directory replaced: fresh clone of ctosullivan/PyLedger@b2d10be (v0.5.1), .git removed, Windows casing fixed |
| `pyproject.toml` | `PyLedger==0.5.0` → `PyLedger==0.5.1` |
| `CLAUDE.md` | "PyLedger v0.5.0" → "PyLedger v0.5.1" |
| `requirements.txt` | Refreshed via `pip freeze` |
| `knowledge_base/pyledger_api_notes.md` | Updated version, path casing, added v0.5.1 change notes |
| `src/ledger_editor/utils/ledger_io.py` | Added `_TXN_DATE_RE`, `split_preamble()`, `split_journal_segments()`; updated `__all__` and `TYPE_CHECKING` imports |
| `src/ledger_editor/widgets/transaction_table.py` | `action_save()`: use `split_journal_segments` + per-transaction `transaction_to_text` + interleaved reassembly |
| `tests/test_ledger_io.py` | Added `TestSplitPreamble` (5 tests) and `TestSplitJournalSegments` (6 tests); updated imports |
| `dev-docs/api-spec.md` | Added `split_preamble` and `split_journal_segments` signatures |
| `CHANGELOG.md` | Two new `[Unreleased]` entries |

## What NOT To Revisit

- ReconcileMixin / reconcile mode — deliberately removed in v0.8.0
- BalanceSidebar / RegisterPanel — deliberately removed in v0.8.0
- The 65%/35% split layout — replaced by full-width editor in v0.8.0
- `FilterPopup.apply_filter()` — out-of-scope stub; do not touch

## Authoritative Settled Facts

- `Transaction` uses `cleared: bool` and `pending: bool` (no `flag: str` field)
- `journal_to_text()` does NOT preserve directives or standalone comments; the editor
  no longer calls it for save output — it calls `transaction_to_text()` per transaction
  and weaves non-txn blocks between them
- `split_journal_segments(text, txns)` extracts non-txn content using SourceSpan line
  ranges (1-based inclusive); len(non_txn_blocks) == len(txn_blocks) + 1
- `align_posting_amounts()` peels inline comments before matching and reattaches after
- `Ctrl+S` writes via `Path.write_text(sorted_text, encoding="utf-8")`
- PyLedger v0.5.1: column-0 `;`/`#` lines inside open transaction blocks are correctly
  discarded (not captured); no API changes vs v0.5.0
- `SourceSpan.start_line` and `.end_line` are 1-based inclusive; 0-based exclusive end
  = `end_line` (same numeric value as 1-based inclusive end)

## Blockers / Open Questions

None.

## Recent Git State

```
29b96e1 chore: ignore all .ps1 files
14896c7 feat: amount alignment, two-layer undo/redo, scroll margin, Python 3.8 compat
(above session's changes not yet committed)
```
