# Changelog

All notable changes to Ledger Editor are documented here.

Format per entry:

```
- Human: <what the user directed>
- Claude: <what was implemented>
```

---

## [Unreleased]

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
