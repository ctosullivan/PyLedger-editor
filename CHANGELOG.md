# Changelog

All notable changes to Ledger Editor are documented here.

Format per entry:

```
- Human: <what the user directed>
- Claude: <what was implemented>
```

---

## [Unreleased]

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
