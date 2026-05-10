# Changelog

All notable changes to Ledger Editor are documented here.

Format per entry:

```
- Human: <what the user directed>
- Claude: <what was implemented>
```

---

## [Unreleased]

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
