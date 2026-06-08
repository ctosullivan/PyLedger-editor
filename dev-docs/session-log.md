# Development Session Log

This file preserves the Human/Claude session log entries from the development
of ledgerkit-editor prior to the v1.0.0 restructuring of `CHANGELOG.md`.

---

## [Unreleased] (pre-1.0.0)

- Human: Upgrade ledgerkit vendor to v0.2.0 and add test coverage for the new comprehensive hledger fixtures.
- Claude: Upgraded `vendor/ledgerkit` from v0.1.0 to v0.2.0 (fetched from `github.com/ctosullivan/ledgerkit` main branch). Updated `pyproject.toml` dep to `ledgerkit==0.2.0` and regenerated `requirements.txt`. Fixed the absolute `include` path in `tests/fixtures/comprehensive-hledger-test.journal` to a relative path (`include comprehensive-hledger-test-commodities.journal`) so `ledgerkit.load()` can resolve it. Updated `action_save` in `transaction_table.py` to import `ParseWarning` from `ledgerkit.parser` and show `ParseWarning` items at `"information"` severity (vs `"warning"` for hard `ParseError`). Created `tests/test_comprehensive_hledger.py` with 36 tests across 8 classes covering: clean fixture load, `ParseWarning` vs `ParseError` distinction, `Transaction.date2` secondary date, `Posting.cost_raw` cost annotations, new amount formats (scientific notation, space digit groups, quoted commodities, sign-after-symbol), `Y`/`D`/`apply account` directives, lot annotation stripping, and balance assertions. All 36 new tests pass.

- Human: Comma (group separator) in amounts not being preserved on save.
- Claude: Two bugs fixed. (1) `extract_commodity_styles` used the *first-seen* amount per commodity; if that amount was small (e.g. `10.00 EUR`, no comma needed), later amounts with commas (e.g. `1,500.00 EUR`) would lose their separators. Fixed by adding a "prefer richest format" pass: after building base styles via `Journal.commodity_styles`, the function now scans all postings and upgrades any commodity whose base style has no group separator when a later amount does. (2) `action_save` was using `self._commodity_styles` frozen at `on_mount` time, so edits that added commas to previously comma-less amounts were ignored. Fixed by computing styles per-save with `extract_commodity_styles(journal)` from the current text. As a side effect, `on_mount` is simplified: no longer creates an `EditorDocument` (which used the strict `parse_string` and could fail on lenient-only files); now loads text directly with `Path.read_text`. Added `test_prefers_richer_format_over_first_seen`.

- Human: Commodity formatting not being preserved on save after Phase 3 implementation.
- Claude: Fixed `apply_commodity_styles` producing `£-300.00` (symbol-then-minus) for negative prefix amounts, a form the ledgerkit parser rejects with ParseError — causing transactions to be silently dropped on the second save. `CommodityStyle.format()` returns the hledger-convention `SYMBOL-NUMBER` form; we now normalise both the `_PREFIX_RE` (sign="-") and `_NEGATIVE_PREFIX_RE` branches to emit `-SYMBOL+NUMBER` (e.g. `-£300.00`) which round-trips through `_parse_amount` correctly. Updated three tests: `test_negative_prefix_reformatted_symbol_first`, `test_negative_prefix_reformatted_minus_first`, and `test_roundtrip_from_fixture`.

- Human: Download latest version of vendor package (pyledger → ledgerkit), rename project to ledgerkit-editor (ledger_editor → ledgerkit_editor), and implement commodity formatting propagation on save.
- Claude: Phase 1 — swapped vendor/pyledger for vendor/ledgerkit (v0.1.0 from github.com/ctosullivan/ledgerkit); updated all `import PyLedger` → `import ledgerkit` across src and all API call sites; updated pyproject.toml dependency, requirements.txt, CLAUDE.md, CONTRIBUTING.md, README.md, dev-docs/architecture.md, dev-docs/api-spec.md, dev-docs/SYNC.md, knowledge_base/ (new ledgerkit_api_notes.md), ROADMAP.md. Phase 2 — renamed src/ledger_editor → src/ledgerkit_editor; updated all 26 source+test files; updated pyproject.toml name/console-script to `ledgerkit-editor`; updated CLAUDE.md folder structure. Phase 3 — added `src/ledgerkit_editor/utils/commodity_format.py` with `extract_commodity_styles` (delegates to `Journal.commodity_styles`) and `apply_commodity_styles` (regex-based post-processor); wired into `JournalEditor.on_mount` (detect on load) and `action_save` (apply before column re-alignment); added `tests/fixtures/multicommodity.journal` and `tests/test_commodity_format.py` (33 tests); updated dev-docs/api-spec.md with commodity_format module section.

- Human: Add `--line=N` (and `+N` vi/emacs convention) and `--theme=THEME` CLI arguments so pyledger-ui can open the editor at the correct transaction line and with a matching color theme.
- Claude: Added `VALID_THEMES` frozenset to `themes/__init__.py` (derived from `textual.theme.BUILTIN_THEMES` plus bundled themes at import time). Extended `_parse_args` in `app.py` with `--line` and `--theme` flags; pre-processes argv to extract bare `+N` tokens before argparse sees them (`--line` wins on conflict). Extended `LedgerApp.__init__` with `start_line` and `theme_name` kwargs; `on_mount` now resolves theme as `self._theme_name or THEME_NAME`. Extended `JournalEditor.__init__` with `start_line`; `on_mount` calls `textarea.move_cursor((row, 0))` after `load_text` when `start_line` is set, clamping to valid range. Added 13 tests in `tests/test_parse_args.py`.

- Human: Shift+Up/Down should shift the date sub-field (year, month, or day) under the cursor on transaction header lines, overriding the default text-selection behaviour.
- Claude: Added `_date_subfield_at_col` and `_shift_date_str` pure helpers to `transaction_table.py`; added `action_date_shift_up`, `action_date_shift_down`, and `_shift_date_by` to `JournalEditor`; wired `shift+up` / `shift+down` bindings with `priority=True` (falls back to selection when cursor is not on a date field); stdlib-only arithmetic via `calendar` + `datetime`; updated `emacs_ledger.py` stubs and `docs/shortcuts.md`; added 20 unit tests in `tests/test_date_shift.py`.

---

- Human: Directives and account aliases are lost when cycling through the reconcile view filter (Ctrl+L); comments must also be preserved.
- Claude: Added `_filter_non_txn_blocks: list[str]` to `JournalEditor`. When entering a filtered view, `action_cycle_view_filter()` now calls `split_journal_segments()` to snapshot the non-transaction content (P directives, account/commodity/payee declarations, standalone comments, blank-line separators) alongside `_filter_journal`. `_apply_view_filter()` mode-0 restore path uses these blocks to weave directives back between sorted transaction texts instead of calling the directive-stripping `journal_to_text()`. Falls back to preamble-only or `journal_to_text` if transaction count changed in filtered view. Save from filtered view (Ctrl+S) inherits the fix automatically. Added 4 tests in `TestViewFilterDirectivePreservation`.

---

- Human: Fix invisible ▲/▼ navigation buttons in the search bar.
- Claude: The `border: tall` rule from the global Button theme consumed both rows of the 1-row-high buttons, making them invisible. Added `border: none; padding: 0 1` to the base `SearchBar Button` CSS and added Monokai Pro-scoped overrides (`background: $panel; color: $foreground`) with a hover state (`background: $primary; color: $background`).

- Human: When Ctrl+F search bar is open, Tab should cycle only between the find input and the editor — not through the ▲/▼ navigation buttons.
- Claude: Added `on_mount` to `SearchBar` that sets `can_focus = False` on both navigation buttons, removing them from the tab order while leaving them fully clickable.

- Human: Update PyLedger vendor to v0.5.1 which correctly handles column-0 `;`/`#` comment lines inside open transaction blocks.
- Claude: Removed write-lock, deleted stub vendor/pyledger, fresh-cloned ctosullivan/PyLedger main branch (commit b2d10be), applied Windows casing fix (pyLedger → PyLedger), removed cloned .git so vendor files remain tracked in main repo, reinstalled in venv, updated pyproject.toml (`PyLedger==0.5.0` → `==0.5.1`), CLAUDE.md, requirements.txt, and knowledge_base/pyledger_api_notes.md.

---

- Human: P directives (and other hledger directives) are discarded when the journal is saved via Ctrl+S; they should be retained, including directives interleaved between transactions.
- Claude: Added `split_journal_segments(text, transactions) → tuple[list[str], list[str]]` to `ledger_editor.utils.ledger_io`. Uses Transaction.source_span to identify precise transaction line ranges and extract all non-transaction content (directives, comments, blank-line separators) into positional blocks. Updated `action_save()` to use `split_journal_segments` + per-transaction `transaction_to_text` serialisation + interleaved reassembly, replacing `journal_to_text`. Added `TestSplitJournalSegments` (6 tests). Also added `split_preamble` (used as fallback when source_span is unavailable).

---

- Human: Posting line with no amount but an inline comment (e.g. `    expenses:food  ; memo`) was being aligned as if the comment were an amount field.
- Claude: Inline comments (`  ; ...`) are now peeled from the posting line before regex matching and reattached after; a body with no `( {2,})` separator is correctly skipped. Added `test_posting_no_amount_inline_comment_unchanged` test.

---

- Human: Postings with suffix-currency amounts and inline comments (e.g. `    expenses:food  50.00 EUR  ; note`) were misaligned — the greedy account-name regex consumed amount words as account, leaving only `; note` as the "amount".
- Claude: Same inline-comment pre-peel fix resolves this; the regex now operates on the comment-free body only. Added `test_posting_amount_with_inline_comment_aligned` test.

---

- Human: Alignment only applied to transactions whose account names have no spaces; accounts like "Assets:Bank:AIB Cormac" were silently skipped.
- Claude: Root cause: regex Group 2 `([^;]\S*)` stopped at the first space, so multi-word account names never matched `( {2,})`. Fixed to `([^\s;]\S*(?:[ ]\S+)*)` which chains (exactly-one-space + non-space-word) groups until a double-space separator stops it. Updated regex block comment to document the new pattern and its disambiguation rule. Added `test_account_name_with_spaces_aligned` test covering multi-word accounts and balance-completing postings side-by-side. Updated `_amount_end_col` helper to use `(.+?)( {2,})` so it also handles space-containing accounts without false-positives on balance-completing postings.

---

- Human: Amount alignment formula placed amount start at col 52; correct behaviour is right-edge (last character) at col 52 — amounts of different lengths were ending at different columns (ragged right edge across transactions).
- Claude: Fixed formula in `align_posting_amounts()` from `max(2, column - len(indent) - len(account))` to `max(2, (column - len(amount)) - len(indent) - len(account))` so the last character of each amount lands at column 52. Updated regex block comment to include the corrected formula. Rewrote tests: renamed `_amount_col` helper to `_amount_end_col` (measures last-char column); renamed `test_amount_starts_at_column_52` to `test_amount_ends_at_column_52`; added `test_multi_transaction_amounts_all_end_at_52` which verifies amounts with different lengths across multiple transactions all share a common right edge.

---

- Human: (1) On save, right-align posting amounts to column 52 (emacs ledger-mode style). (2) Fix undo/redo broken for Ctrl+G (copy transaction to bottom) — establish atomic_edit() and CommandHistory infrastructure for all custom commands. (3) Add at least 4 lines of visible context below the cursor when it moves (scroll margin). (4) Downgrade minimum Python requirement to 3.8 and fix any 3.9+ runtime-incompatible code.
- Claude: (1) Added `align_posting_amounts(text, column=52)` in `ledger_io.py`; called in `action_save()` between `journal_to_text()` and `load_text()`; exports updated in `utils/__init__.py`. (2a) Fixed `action_autofill` to use `textarea.replace(new_text, (0, 0), doc_end)` instead of `textarea.load_text(new_text)` — load_text clears EditHistory; replace() creates one undoable batch. (2b) Created `utils/atomic_edit.py` with `atomic_edit()` context manager that collapses N replace() calls into one EditHistory batch; applied to `_bulk_toggle_cleared`. (2c) Replaced commands/__init__.py stub with `Command` dataclass and `CommandHistory` (Layer 2 undo stack); added `_command_history` attribute to JournalEditor; added `action_undo`/`action_redo` overrides with CommandHistory→TextArea fallthrough; added `ctrl+z`/`ctrl+y` to JournalEditor.BINDINGS with priority=True. (3) Overrode `scroll_cursor_visible()` in `LedgerTextArea` to pass `Spacing(bottom=4)` to `scroll_to_region()`. (4) Fixed `pyproject.toml` requires-python to `>=3.8` and Black target to `py38`; fixed `highlighter.py` runtime generic `Span = tuple[...]` → `Span = Tuple[...]` from typing; updated CLAUDE.md "Target Python" to 3.8+.

---

## [0.8.2-meta] — Version bump & documentation — 2026-05-17

- Human: Bump version to 0.8.2 in pyproject.toml; update README to reflect current project state (no window panes, stub filter popup, beta warning, GitHub install instructions); update ROADMAP to reflect current architecture.
- Claude: Bumped `pyproject.toml` version from `0.6.0` to `0.8.2`. Rewrote `README.md`: removed stale planned-features list; added early-beta / journal-corruption warning; accurate feature list (view filter, search, no sidebar/register panels); GitHub install instructions with explicit note that PyLedger must be installed from `vendor/pyledger/` (the PyPI package is a stub). Rewrote `ROADMAP.md`: replaced stale Milestone 1–4 checklist with accurate "What Is Shipped" summary, explicit "Window Panes Removed" section, and clean upcoming milestones (Transaction Filter, Autocomplete, Emacs date editing, Performance).

---

## [0.8.2] — UAT Fix Round — 2026-05-17

- Human: UAT of v0.8.1 found five issues: command palette shows invisible commands (Insert date, Search) and still has `^` symbols; search bar input text still invisible; Ctrl+R with search bar open should toggle cleared not navigate matches; Escape only closes FilterPopup when popup has focus; FilterPopup Enter in Account field shows no notification.
- Claude: Issue 1 — removed `LedgerTextArea.BINDINGS` entirely; the v0.8.1 approach was based on a wrong premise (TextArea built-ins are already all `show=False` in Textual 8.2.5); our added bindings for `ctrl+d` and `ctrl+f` were shadowing JournalEditor's visible bindings for those keys, making "Insert date" and "Search" invisible in the palette. Issue 2 — added `App.-theme-monokai-pro SearchBar Input { background: $panel; color: $foreground; border: none; }` to `monokai_pro.tcss`; the general `App.-theme-monokai-pro Input` rule (specificity 12) was overriding `SearchBar Input` in app.py (specificity 2) and applying `border: tall $boost` which clipped text within the 1-row height constraint. Issue 3 — removed the search-bar branch from `action_toggle_cleared` in `transaction_table.py`; Ctrl+R now always toggles cleared status. Issue 4 — added `on_mount` to `FilterPopup` that focuses `#date-from` on open, ensuring Escape is routed to the popup's own binding. Issue 5 — no additional code needed; was caused by the same focus problem as Issue 4. Updated `docs/shortcuts.md` and `knowledge_base/keybindings.md`.

---

## [0.8.1] — UAT Fix Round — 2026-05-17

- Human: UAT of v0.8.0 found five issues: command palette shows mixed `^F` / `Ctrl+F` keybinding notation; search bar input text invisible; Ctrl+Shift+F intercepted by Windows Terminal (want Shift+PgUp/PgDown for search navigation when bar is open); Ctrl+Shift+P intercepted (FilterPopup); FilterPopup Enter does nothing. Also: remove "Esc Unfocus" from footer, rename Ctrl+L footer label to "Filter cleared".
- Claude: Issue 1 — added `BINDINGS` class variable to `LedgerTextArea` that re-declares all TextArea built-in bindings with `show=False`; subclass BINDINGS take MRO precedence, suppressing them from the command palette and footer. Set `show=False` on `escape → blur_editor` in `JournalEditor.BINDINGS`. Renamed Ctrl+L description from "Filter view" to "Filter cleared". Issue 2 — added `background: $panel; color: $text; border: none;` to `SearchBar Input` CSS in `app.py`. Issue 3 — removed `ctrl+shift+f → search_prev` binding and `action_search_prev`; made `action_prev_transaction` and `action_next_transaction` context-sensitive: when search bar is open, they delegate to `bar.advance(direction=-1/+1)` instead of navigating transaction headers. Issue 4 — remapped FilterPopup from `ctrl+shift+p` to `ctrl+o` in `app.py` and `filter_popup.py`; updated title label. Issue 5 — added `on_input_submitted` handler to `FilterPopup` that shows an informational notification directing users to Ctrl+L. Updated `docs/shortcuts.md` and `knowledge_base/keybindings.md`.

---

## [0.8.0] — Major Refactor: Pure Editor + View Filter — 2026-05-17

- Human: Remove balance sidebar, register panel, and all reconcile-mode machinery. Make the app a pure hledger text editor. Replace reconcile mode with a Ctrl+L view filter that cycles the editor between All / Cleared / Unreconciled transactions.
- Claude: Deleted 5 widget files and rewrote `transaction_table.py`; added ViewFilterBar; updated app.py layout. Suite: 175/175.

---

## [0.7.x] — Feature development — 2026-05-12 to 2026-05-17

(Multiple UAT rounds — see git log for detail.)

---

## [0.0.1] — 2026-05-10

- Human: Set up the initial project scaffold and development environment for a plain-text ledger editor with Textual and PyLedger v0.5.0.
- Claude: Created full project scaffold.
