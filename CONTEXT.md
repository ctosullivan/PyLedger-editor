# CONTEXT.md — Session Working Memory

## Current Task

Inline comment handling in `align_posting_amounts()` fixed: posting lines with
inline comments (no amount, or suffix-currency amount + comment) now handled
correctly. 206 tests pass.

## Where We Are

All code changes done. Tests passing. Not yet committed.

## Decisions In Flight

- `atomic_edit()` accesses `text_area.history._undo_stack` (EditHistory private API,
  Textual 0.83.0). This is intentional and documented with a RuntimeError guard. If
  Textual is upgraded, check that `_undo_stack` still exists on `EditHistory`.
- `JournalEditor` is a `Widget` (not `TextArea` subclass), so `action_undo`/`action_redo`
  fall through to `self.query_one("#journal_textarea", TextArea).action_undo/redo()`.
  Adding `priority=True` Ctrl+Z / Ctrl+Y bindings to JournalEditor ensures these
  intercept before LedgerTextArea's native bindings handle them.
- `align_posting_amounts()` is a pure post-processing step on `journal_to_text()` output;
  it does not touch the vendor code and has no knowledge of PyLedger types.

## Files Changed This Session

| File | Change |
|---|---|
| `pyproject.toml` | `requires-python = ">=3.8"`, Black target `py38` |
| `CLAUDE.md` | "Target Python" 3.11+ → 3.8+ |
| `src/ledger_editor/highlighting/highlighter.py` | `Span = tuple[...]` → `Tuple[...]` (typing import) |
| `src/ledger_editor/utils/ledger_io.py` | Added `align_posting_amounts()` + regex; **fixed formula** (right-align, last char at col 52); **fixed inline comment handling** (peel `  ;` before regex, reattach after) |
| `src/ledger_editor/utils/__init__.py` | Exported `align_posting_amounts` |
| `src/ledger_editor/utils/atomic_edit.py` | **New**: `atomic_edit()` context manager |
| `src/ledger_editor/commands/__init__.py` | Replaced stub with `Command` + `CommandHistory` |
| `src/ledger_editor/widgets/transaction_table.py` | (1) `action_save`: added `align_posting_amounts()` call; (2) `action_autofill`: `load_text()` → `replace()` for undo; (3) `_bulk_toggle_cleared`: wrapped in `atomic_edit()`; (4) `__init__`: added `_command_history`; (5) added `action_undo`/`action_redo` overrides; (6) BINDINGS: added `ctrl+z` / `ctrl+y` with priority=True |
| `src/ledger_editor/widgets/ledger_textarea.py` | Added `scroll_cursor_visible()` override with `Spacing(bottom=4)` |
| `tests/test_ledger_io.py` | Added `TestAlignPostingAmounts`; **fixed** helper; added multi-transaction, space-in-account, and inline-comment tests |
| `tests/test_atomic_edit.py` | **New** |
| `tests/test_command_history.py` | **New** |
| `tests/test_undo_redo.py` | **New** |
| `dev-docs/api-spec.md` | Added `align_posting_amounts`, `atomic_edit`, `Command`, `CommandHistory`, updated JournalEditor entry |
| `dev-docs/architecture.md` | Added two-layer undo section; updated module tree and data-flow |
| `docs/shortcuts.md` | Added Ctrl+Z/Ctrl+Y; updated Ctrl+S and Ctrl+G descriptions |
| `CHANGELOG.md` | New `[Unreleased]` entries |
| `ROADMAP.md` | Added undo/redo and alignment to "What Is Shipped" |

## What NOT To Revisit

- ReconcileMixin / reconcile mode — deliberately removed in v0.8.0
- BalanceSidebar / RegisterPanel — deliberately removed in v0.8.0
- The 65%/35% split layout — replaced by full-width editor in v0.8.0
- `FilterPopup.apply_filter()` — out-of-scope stub; do not touch

## Authoritative Settled Facts

- `Transaction` uses `cleared: bool` and `pending: bool` (no `flag: str` field)
- `journal_to_text()` does NOT preserve standalone comment lines or directives (PyLedger v0.5.0 limitation); it DOES preserve `Posting.inline_comment` as `  ; {text}` appended to the posting line
- `align_posting_amounts()` peels inline comments (`  ;`) before regex matching and reattaches them after — this handles both the "no amount, only comment" and "suffix-currency + comment" cases correctly
- `Ctrl+S` writes via `Path.write_text(sorted_text, encoding="utf-8")` — not `EditorDocument.save()`
- `Ctrl+R` is toggle-cleared. `Ctrl+T` selects transaction block. Neither binding changed.
- `JournalEditor` is a `Widget`, not a `TextArea` subclass; it contains `LedgerTextArea` as child
- `atomic_edit()` uses `text_area.history._undo_stack` (not `text_area._undo_stack`)
- TextArea has `Binding("ctrl+z", "undo", ...)` and `Binding("ctrl+y", "redo", ...)`
  inherited by LedgerTextArea; JournalEditor's priority=True bindings intercept first

## Blockers / Open Questions

None.

## Recent Git State

```
9c76028 chore: ignore run.ps1 and run_uat.ps1 (local dev scripts)
(above session's changes not yet committed)
```
