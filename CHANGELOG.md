# Changelog

All notable changes to Ledger Editor are documented here.

Format per entry:

```
- Human: <what the user directed>
- Claude: <what was implemented>
```

---

## [Unreleased]

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
- Claude: Deleted 5 widget files (`balance_sidebar.py`, `register_panel.py`, `reconcile_bar.py`, `reconcile_summary.py`, `reconcile_actions.py`) and 2 test files (`test_balance_sidebar.py`, `test_register_panel.py`). Rewrote `transaction_table.py`: removed `ReconcileMixin`, all reconcile state attrs and message classes (`ReconcileModeEntered`, `ReconcileModeExited`, `TransactionClearedToggled`, `LiveChanged`, `CursorAccountChanged`), removed debounce timer, removed reconcile BINDINGS (`ctrl+i`, `ctrl+enter`), simplified `action_blur_editor` / `action_toggle_cleared` / `action_select_all`; added `_view_filter_mode`, `_filter_journal`, `_filter_visible_indices` state attrs; added `action_cycle_view_filter()`, `_apply_view_filter()`, `_merge_filtered_edits()`, `_update_filter_bar()`; `action_save()` merges filtered edits before writing. Created `view_filter_bar.py` (ViewFilterBar, 1-row status bar showing current filter mode). Rewrote `app.py`: removed `BalanceSidebar`, `RegisterPanel`, `Vertical` imports; removed right-panel CSS and all sidebar/reconcile message handlers; JournalEditor now full-width (`width: 1fr`). Fixed `widgets/__init__.py` to export only surviving widgets. Moved `_find_transaction_header_above` from deleted `reconcile_actions.py` into `search_bar.py` (only remaining caller). Added 12 new tests in `test_view_filter.py`. Updated `docs/shortcuts.md` and `knowledge_base/keybindings.md`. Suite: 175/175.

---

## [0.7.2] — UAT Round 2 Fixes — 2026-05-17

- Human: UAT of v0.7.1 revealed: F3/Shift+F3/Alt+F3 collide with Windows OS shortcuts; Ctrl+Shift+R (reconcile) not working in Windows Terminal; requested Ctrl+G duplicate-multiple-transactions when selection spans multiple blocks.
- Claude: Search navigation rework — removed `f3`, `shift+f3`, `alt+f3` bindings and `open_search_reverse` action; made `action_open_search` context-sensitive (open if closed, advance if open); made `action_toggle_cleared` check search bar visibility first (Ctrl+R = prev match when bar visible); rebound Ctrl+Shift+F to `search_prev` (priority=True) replacing `open_search_reverse`. Reconcile binding — changed Ctrl+Shift+R → Ctrl+Shift+C in both JournalEditor and BalanceSidebar (C for Clearing; avoids Windows Terminal intercept). Ctrl+G multi-block — `action_autofill` now detects multi-line selection via `textarea.selection`; walks `line_infos` to find XACT_HEADER rows in selection range, deduplicates with `seen` set, duplicates all blocks with today's date; single-cursor path unchanged. Updated `docs/shortcuts.md`, `knowledge_base/keybindings.md`, `CONTEXT.md`. Suite: 178/178.

---

## [0.7.1] — UAT Round 1 Bug Fixes — 2026-05-17

- Human: UAT of v0.7.0 revealed: Ctrl+F did nothing; register panel blank with Tab focus broken; reconcile Ctrl+R crashed silently; FilterPopup docstrings still referenced old Ctrl+Shift+F binding. Also requested a comprehensive keybindings knowledge-base document.
- Claude: Bug 1 — added `priority=True` to all 5 search bindings in `JournalEditor.BINDINGS` (`ctrl+f`, `ctrl+shift+f`, `f3`, `shift+f3`, `alt+f3`) so JournalEditor captures them before LedgerTextArea's inherited `delete_word_right`. Bug 2 — fixed `ContentSwitcher(initial="register_table")` and `watch_reconcile_mode` string from `"register-view"` → `"register_table"` to match `DataTable(id="register_table")`; reactive init watcher had been hiding all children. Bug 3 — fixed `textarea.replace()` calls in `_action_reconcile_toggle_cleared` and `action_reconcile_mark_all_cleared` from `Selection` object to positional `(from_location, to_location)` tuples; removed stale `from textual.document._document import Selection` imports. Bug 4 — updated module and class docstrings in `filter_popup.py` from `Ctrl+Shift+F` → `Ctrl+Shift+P`. New: `knowledge_base/keybindings.md` — full map of all TextArea inherited bindings, project bindings per widget, collision table, `priority=True` pattern, free Ctrl+ keys, terminal compatibility notes. Suite: 178/178.

---

## [0.7.0] — 2026-05-13

- Human: v0.7.0 planning prompt — five feature areas as a single batch: (1) incremental search bar with match highlighting; (2) file-path display with modified indicator; (3) reconciliation mode with ReconcileStatusBar and ReconcileSummary; (4) live widget updates tuning; (5) register efficiency fixes.
- Claude: Step 0 — split `reconcile_actions.py` from `transaction_table.py` (ReconcileMixin + pure helpers; approved by user before implementation). Step 1 — register efficiency fixes: same-account guard + 250 ms debounce in `show_account()`; module-level `@lru_cache(maxsize=32)` keyed on `(path, account, mtime)` for disk reads; live-update path bypasses cache and uses `parse_string_lenient` directly; `PAGE_SIZE = 500` pagination with scroll-triggered load-more; `ContentSwitcher` added to `RegisterPanel` for reconcile/register view switching. Step 2 — debounce reduced from 0.8 s → 0.25 s; `_in_reconcile_mode` flag suppresses live debounce during reconcile; `action_save()` cancels pending timer before write. Step 3 — `#file-path-bar` Static widget in `LedgerApp.compose()` shows resolved path; appends " · modified" on every text change via `FileModifiedChanged` message; cleared on save. Step 4 — `SearchBar` widget (incremental search, `Ctrl+F`/`Ctrl+Shift+F`, `F3`/`Shift+F3`/`Alt+F3`, `Escape`); pure helpers `_build_offset_table()` and `_offset_to_location()` for O(log N) offset → location conversion; `LedgerTextArea.set_search_matches()` injects `ledger.search.match` / `ledger.search.current` spans into `_highlights` via a second pass in `_build_highlight_map()`; Monokai Pro search styles added; `FilterPopup` binding moved from `Ctrl+Shift+F` → `Ctrl+Shift+P` to free `Ctrl+Shift+F` for reverse search. Step 5 — `ReconcileMixin` with `enter_reconcile_mode()` / `exit_reconcile_mode()` / `_apply_reconcile_changes()`; `ReconcileStatusBar` (account | checked | target input | Δ); `ReconcileSummary` (cleared balance, unreconciled, pending, Δ vs target); reconcile entry points in `BalanceSidebar` (`Ctrl+Shift+R`) and `JournalEditor` (`Ctrl+Shift+R` on posting line); `Ctrl+Enter` commit / `Escape` cancel. Step 6 — updated `docs/shortcuts.md`, `dev-docs/api-spec.md`, `ROADMAP.md`, `CLAUDE.md`, `CONTEXT.md`. All token names prefixed `ledger.*`; `JournalEditor.on_mount()` now explicitly focuses the textarea. Suite: 178/178.

---

## [0.6.0] — 2026-05-12

- Human: Insert-date binding Ctrl+M also inserts a newline (Ctrl+M = Enter in
  terminals); rebind to Ctrl+D. Enter at buffer bottom loses cursor from view.
  Date insert should append a trailing space.
- Claude: Rebound insert_today from `ctrl+m` to `ctrl+d` with `priority=True`
  (overrides TextArea's delete-char handler; Delete/Backspace still available).
  `action_insert_today` inserts `date.today().isoformat() + " "` (trailing space
  for immediate payee entry). Fixed scroll: after `event.prevent_default()` +
  `self.insert()` in `LedgerTextArea._on_key`, Textual's scroll-to-cursor step is
  skipped; replaced `self.move_cursor(self.cursor_location)` (reactive no-op when
  cursor position is unchanged) with `self.scroll_cursor_visible()` (unconditional
  scroll). Updated `docs/shortcuts.md`. Suite: 178/178.

- Human: UAT round 2 — amount last digit white, 1-char suffix commodity white,
  Enter at col 0 indents date, Ctrl+T should extend selection, Ctrl+R
  order-sensitive, Ctrl+Shift+F can't close popup, sidebars only refresh on
  save; new: Ctrl+M insert today's date (initially bound to Ctrl+; which
  did not register in terminal).
- Claude: Fixed amount last-digit highlight: Textual's `_highlights` uses UTF-8
  byte column offsets (from tree-sitter), not Unicode codepoints; added
  `_build_cp_to_byte()` in `ledger_textarea.py` and convert each span in
  `_build_highlight_map()` before writing to `_highlights` — fixes multibyte
  symbols (£=2 bytes, €=3 bytes). Fixed 1-char suffix commodity: changed
  `[A-Z]{2,6}` → `[A-Z]{1,6}` in `_AMOUNT_RE`. Fixed Enter at col 0: added
  `col > 0` guard for `XACT_HEADER` in `_on_key` — pressing Enter at the very
  start of a header now inserts a plain newline (blank-line separator) instead
  of auto-indenting. Fixed Ctrl+T extend: `action_select_transaction_block`
  checks if the current selection ends at a block boundary and, if so, extends
  to include the next block; each press extends by one more transaction. Fixed
  Ctrl+R order sensitivity: normalized `start_row = min(sel.start[0],
  sel.end[0])` so reversed (bottom-to-top) selections bulk-toggle correctly.
  Fixed Ctrl+Shift+F close: added `priority=True` bindings for `ctrl+shift+f`
  and `escape` to `FilterPopup`, with `action_close_self` calling `self.remove()`.
  Added live sidebar/register refresh: `JournalEditor.on_text_area_changed`
  debounces 0.8 s then posts `LiveChanged(text, account)`; `LedgerApp` handles
  it by calling `BalanceSidebar.refresh_from_text()` and
  `RegisterPanel.refresh_account_from_text()`, both using
  `parse_string_lenient` so partial edits show best-effort data. Added
  `Ctrl+D` → `action_insert_today` (inserts today's ISO date + space at cursor;
  initial `Ctrl+;` didn't register, `Ctrl+M` conflicted with Enter, final binding
  is `Ctrl+D` with `priority=True`). Updated `docs/shortcuts.md`. Added 12 new
  tests (TestCommodity1Char, TestCpToByteMapping, TestBulkToggleReversedSelection,
  TestEnterAtCol0, TestSelectExtend, TestInsertToday). Suite: 178/178.

---

## [0.5.0] — 2026-05-11

- Human: Rebind duplicate-transaction (Ctrl+D → Ctrl+Shift+D → Ctrl+G); fix
  auto-indent inserting an extra blank line.
- Claude: Final binding: `Binding("ctrl+g", ...)` in `JournalEditor.BINDINGS`;
  updated `docs/shortcuts.md`. Fixed auto-indent double-newline: Textual's
  `_get_dispatch_methods` walks the full MRO and calls `_on_key` from every class
  independently, so an early `return` in `LedgerTextArea._on_key` still allowed
  `TextArea._on_key` to run and insert its own `\n`. Fix: call
  `event.prevent_default()` before `self.insert("\n    ")` — this sets
  `message._no_default_action = True`, which breaks the MRO dispatch loop before
  `TextArea._on_key` is reached. Removed `super()._on_key` call entirely (it would
  double-invoke the parent via MRO). Suite: 166/166.

- Human: UAT fixes — payee colour matching flag, amount digit artefacts, block
  background tinting interfering with Ctrl+T selection, ANSI theme crash, posting
  note colour wrong; new features: Enter auto-indent 4 spaces, Shift+PgUp/PgDown
  navigate transactions, Ctrl+D duplicate transaction with today's date, bulk
  Ctrl+R toggle-cleared for multi-transaction selections.
- Claude: Fixed `_highlight_header()` to always emit `PAYEE_UNCLEARED` regardless of
  cleared/pending state (payee no longer changes colour to match the `*`/`!` flag).
  Fixed `_highlight_amount_section()` to merge prefix commodity symbols (`£`, `$`,
  `€`) into the amount span instead of emitting a separate `COMMODITY` span, removing
  an adjacent-span colour artefact. Removed all block-level background span emission
  (`_block_span()`, `BLOCK_CLEARED`, `BLOCK_PENDING`, `BLOCK_UNCLEARED`) from
  `highlighter.py`, `theme_bridge.py`, and `monokai_pro.py` — block tinting was
  preventing the Textual selection colour from showing on Ctrl+T blocks. Fixed
  `build_textarea_theme()` to catch `rich.color.ColorParseError` when an ANSI theme
  returns `ansi_*` colour names (prevents crash on ANSI-Dark/Light switch). Changed
  `ledger.note` and `ledger.posting.note` in `MONOKAI_PRO_TEXTAREA_THEME` from purple
  to grey (`_COMMENT`) to match comment appearance. Added `_on_key()` to
  `LedgerTextArea` — Enter on a header or posting line inserts `\n    ` (4 spaces)
  instead of a bare newline, since TAB cycles focus. Added `action_prev_transaction()`
  / `action_next_transaction()` (Shift+PgUp/Down) to `JournalEditor` — navigate
  between transaction header lines via the highlighter's cached `_line_infos`.
  Added `action_autofill()` (Ctrl+D) — duplicates the current transaction block to
  the end of the file with today's date in the header. Enhanced `action_toggle_cleared()`
  to detect a multi-row selection and delegate to `_bulk_toggle_cleared()` — if all
  selected headers are `*` remove all flags, otherwise set all to `*`. Updated tests:
  inverted block-span assertions in test_highlighting.py and test_themes.py; updated
  payee token assertions; added TestAmountPrefixMerged, TestBridgeAnsiColors,
  TestAutofill, TestPrevNextTransaction, TestBulkToggleCleared. Suite: 166/166.

- Human: Implement hledger journal syntax highlighting and Monokai Pro as the
  default app theme; all colours derived from the active Textual theme so
  runtime theme switching recolours the editor automatically.
- Claude: Added `ledger_editor.highlighting` package (`tokens.py`, `highlighter.py`,
  `theme_bridge.py`) with a pure-Python `LedgerHighlighter` (single O(N) scan) and
  `build_textarea_theme()` CSS-variable bridge. Added `ledger_editor.themes` package
  with `MONOKAI_PRO_APP_THEME` (`textual.theme.Theme`), `MONOKAI_PRO_TEXTAREA_THEME`
  (`TextAreaTheme`), TCSS overrides, and `register_all()`. Introduced
  `LedgerTextArea(TextArea)` in `widgets/ledger_textarea.py` that overrides
  `_build_highlight_map()` (private Textual 8.2.5 API) to inject 20 ledger token
  spans and block-level background overlays per edit cycle. Added `LedgerApp.on_mount`
  and `CSS_PATH`; Monokai Pro is the hardcoded default (overridable via
  `TEXTUAL_THEME`). Swapped `TextArea` → `LedgerTextArea` in `JournalEditor.compose`.
  Key deviation: `TextArea.highlight_range()` and `_get_line_syntax_highlights()` do
  not exist in Textual 8.2.5 — block highlights are injected via `_build_highlight_map`
  instead. TCSS class prefix is `-theme-monokai-pro` (added automatically by Textual).
  Added 61 tests (54 pure, 7 pilot). Suite: 157/157.

- Human: Widen text editor panel to 65% of screen width; make register panel
  scrollable with most recent transaction visible at bottom.
- Claude: Changed `JournalEditor` CSS width from `80%` → `65%` and `#right_panel`
  from `20%` → `35%`. Removed the `rows[-10:]` cap in `_load_register` so all
  postings are loaded. Added `table.scroll_end(animate=False)` at the end of
  `_render_rows` to pin the view to the most recent row on load. Updated module
  and class docstrings. Updated `test_show_account_limits_to_10_rows` →
  `test_show_account_loads_all_rows` (asserts `row_count > 10`). Suite: 96/96.
  Version bumped to 0.4.0.

- Human: UAT Round 3 — Ctrl+Shift+A still not working, rebind to Ctrl+R (reconcile);
  Alt+Shift+Up/Down still not working, replace with single Ctrl+T (select transaction
  block); Ctrl+Shift+Home/End out of scope, remove.
- Claude: Changed toggle-cleared binding `ctrl+shift+a` → `ctrl+r` (key_display "Ctrl+R").
  Removed `alt+shift+up/down` directional block-select bindings and replaced with
  single `ctrl+t` → `action_select_transaction_block` (selects header through last
  posting regardless of cursor position within block). Removed `ctrl+shift+home` and
  `ctrl+shift+end` bindings and their action methods entirely. Replaced the two
  directional async tests with a single `test_select_transaction_block` test.
  Updated `docs/shortcuts.md`. Suite: 96/96.

- Human: Fix UAT Round 2 issues: keep command palette but show "Ctrl+P" not caret;
  change Ctrl+Shift+C → Ctrl+Shift+A (collision); fix block selection keys
  Ctrl+Shift+Up/Down → Alt+Shift+Up/Down (Windows Terminal interception); add
  Ctrl+Home/End, Ctrl+A (select all), Ctrl+Shift+Home/End; fix Tab focus cycle
  to include RegisterPanel's DataTable.
- Claude: Set `COMMAND_PALETTE_DISPLAY = "Ctrl+P"` on `LedgerApp` (keeps palette,
  fixes footer display). Renamed toggle-cleared binding `ctrl+shift+c` →
  `ctrl+shift+a`. Changed block-select bindings from `ctrl+shift+up/down` to
  `alt+shift+up/down` (avoid Windows Terminal interception). Added five new
  `priority=True` bindings to `JournalEditor`: `ctrl+home/end` (cursor to
  file start/end), `ctrl+a` (select all, overrides TextArea's line-start default),
  `ctrl+shift+home/end` (select to file start/end). Added `BINDINGS` with
  `priority=True` Tab/Shift+Tab to `BalanceSidebar` and `RegisterPanel` to fix
  Tab focus cycle (TextArea → Tree → DataTable → TextArea). Added 3 async tests
  (`TestNavigationActions`); full suite 97/97.

- Human: Fix UAT-reported issues: Ctrl+Shift+F close popup; change Shift+C to
  Ctrl+Shift+C; fix footer caret symbols; widen right panel to 80 chars; add
  Ctrl+Shift+Up/Down transaction block selection.
- Claude: Added `priority=True` and `key_display="Ctrl+Shift+F"` to the App's
  filter binding (fixes close-when-focused). Changed `JournalEditor.BINDINGS`
  from bare tuples to `Binding` objects with `key_display` so the footer renders
  "Ctrl+S" / "Ctrl+Shift+C" instead of caret symbols; renamed `shift+c` binding
  to `ctrl+shift+c`. Widened `#right_panel` from 48 to 80 chars. Added
  `_find_transaction_block(lines, row)` pure helper and two new directional
  actions: `action_select_to_block_start` (`Ctrl+Shift+Up`, selects cursor→header)
  and `action_select_to_block_end` (`Ctrl+Shift+Down`, selects cursor→last posting),
  both with `priority=True` to override TextArea defaults. Added 7 tests (5 pure
  `TestFindTransactionBlock`, 2 async block-select); full suite 94/94.

- Human: Replace DataTable editor with a text editor (like eMacs Ledger Mode);
  move balance sidebar to the right; add a register panel.
- Claude: Replaced `TransactionTable` (DataTable) with `JournalEditor` (TextArea)
  in `transaction_table.py`. Editor loads raw hledger text, detects transaction
  components at the cursor, and posts `CursorAccountChanged` on every cursor move.
  `Ctrl+S` calls `parse_string_lenient` + `journal_to_text` + `Path.write_text`
  (no longer via `EditorDocument.save`). `Shift+C` cycles the flag character
  in-place via `textarea.replace()`. Moved `BalanceSidebar` to the right-hand
  `#right_panel` (`Vertical` container); added `AccountSelected` message and node
  `data` storage so clicking a tree node drives the register. Created new
  `RegisterPanel` widget (`register_panel.py`): `@work(thread=True, exclusive=True)`
  loads `journal.register(query=Query(account=...))` and shows the last 10 rows in
  a DataTable; wired to both `CursorAccountChanged` and `AccountSelected`. Updated
  `app.py` layout CSS and added three message handlers. Added 17+1+9 new tests
  (rewritten `test_transaction_table.py`, new `test_register_panel.py`, added
  `test_node_selected_posts_account_selected` to balance sidebar); full suite 87/87.

- Human: Implement Milestone 1 — Core Editing Surface.
- Claude: Implemented `TransactionTable` widget with `DataTable`-based grid (5
  columns: Date, Flag, Description, Account, Amount), `_RowMeta` row index,
  in-place cell editing via pinned `Input` bar, and all Milestone 1 key actions:
  `Ctrl+S` (sort-by-date + save + basic-checks notify), `Shift+C` (3-state
  cleared toggle), `Ctrl+←/→` (field navigation), `Ctrl+↑/↓` (transaction
  navigation), `Escape` (cancel edit). Implemented `BalanceSidebar` widget with
  Textual `Tree`, threaded `@work` refresh via `journal.balance(tree=True)`, and
  `call_from_thread` UI update. Wired `LedgerApp.on_transaction_table_save_completed`
  to call `refresh_balances()` after each save. Added 23 tests across
  `test_transaction_table.py` and `test_balance_sidebar.py`; full suite 78/78.

## [0.0.1] — 2026-05-10

- Human: Set up the initial project scaffold and development environment for a
  plain-text ledger editor with Textual and PyLedger v0.5.0.
- Claude: Created full project scaffold — directory structure, stub source files
  (app.py, widgets, keybindings, utils), pyproject.toml, requirements.txt,
  CLAUDE.md, CONTEXT.md, CONTRIBUTING.md, ROADMAP.md, all knowledge_base files,
  all dev-docs stubs, sample.journal fixture, and initial pytest suite. Performed
  sparse git checkout of PyLedger v0.5.0 vendor tree. Confirmed key API discrepancy:
  Transaction uses cleared: bool + pending: bool (not flag: str | None as originally
  specified). Recorded all resolved design decisions. Committed as v0.0.1.
