# Roadmap

Milestones track the editor's development phases. A milestone is only marked
`[DONE]` on explicit user instruction — never inferred by Claude.

---

## Milestone 0 — Initial Scaffold `[DONE — 2026-05-10]`

- [x] Virtual environment and pinned dependencies (textual==8.2.5, pyledger==0.5)
- [x] Sparse vendor checkout of PyLedger v0.5.0 (read-only)
- [x] Project structure: src/, tests/, vendor/, knowledge_base/, docs/, dev-docs/
- [x] Stub source files for all widgets, keybindings, utils
- [x] pyproject.toml, requirements.txt, .gitignore
- [x] CLAUDE.md, CONTEXT.md, CONTRIBUTING.md, CHANGELOG.md
- [x] knowledge_base/ pre-populated from vendor source
- [x] Initial pytest suite (structural smoke tests pass)
- [x] git init + v0.0.1 tag

## Milestone 1 — Core Editing Surface

- [ ] `TransactionTable` widget: render journal postings in a scrollable grid
- [ ] In-place editing: date, description, account, amount fields
- [ ] `BalanceSidebar` widget: tree-mode balance display via `balance(tree=True)`
- [ ] `Ctrl+S`: sort by date + re-align whitespace + warn-and-save
- [ ] `Shift+C`: 3-state cleared toggle (uncleared → pending → cleared)
- [ ] Field navigation: `Ctrl+←/→` (next/prev field)
- [ ] Transaction navigation: `Ctrl+↑/↓` (next/prev transaction block)

## Milestone 2 — Keybindings & Autocomplete

- [ ] Full MS Office keybinding set (Ctrl+A/C/V/X/D/F/R)
- [ ] Full Emacs Ledger-mode keybinding set (Tab, Shift+Arrow, Alt+P/N, Ctrl+K)
- [ ] Tab autocomplete from declared_accounts + all posting accounts
- [ ] `Ctrl+D` autofill: duplicate once to bottom, date → today
- [ ] `Alt+P` / `Alt+N`: previous/next matching transaction template

## Milestone 3 — Filter Popup & Search

- [ ] `FilterPopup` widget: date range, account glob, payee, amount range
- [ ] Smart date parsing: "last month", "ytd", "q1", ISO 8601, relative offsets
- [ ] Live filter applied to TransactionTable without closing popup
- [ ] Forward / reverse search (`Ctrl+F` / `Ctrl+R`)

## Milestone 4 — Polish & Robustness

- [ ] Full pytest suite with Textual test harness (pilot testing)
- [ ] Async balance refresh after every save
- [ ] Error/warning notification bar for validation failures
- [ ] Command palette integration
- [ ] Performance: large journals (10k+ transactions)
