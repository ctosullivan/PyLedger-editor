# Roadmap

The project is in **early beta**. A milestone is only marked `[DONE]` on explicit
user instruction — never inferred by Claude.

---

## What Is Shipped (v0.8.2)

The editor is a full-screen, keyboard-driven plain-text hledger journal editor.

**Editing surface**
- Full-width `TextArea` editing surface (`JournalEditor`)
- hledger syntax highlighting: dates, flags, payees, accounts, amounts, commodities,
  comments, directives (20 token types)
- Monokai Pro as default app theme; CSS-variable bridge enables runtime theme switching
- Enter auto-indent on transaction header and posting lines

**File operations**
- `Ctrl+S` — sort by date, re-align whitespace, save; merges active view-filter
  edits before writing
- File-path bar with modified indicator

**Transaction editing**
- `Ctrl+R` — 3-state cleared cycle (uncleared → pending `!` → cleared `*`);
  bulk-toggle for multi-block selections (all cleared → all uncleared; otherwise → all `*`)
- `Ctrl+G` — duplicate current transaction block to end of file with today's date;
  multi-block selection duplicates all selected blocks
- `Ctrl+D` — insert today's date at cursor
- `Ctrl+T` — select current transaction block; repeated presses extend selection

**Navigation & search**
- `Ctrl+F` — incremental search bar with match highlighting (`N of M` counter)
- `Shift+PgUp / Shift+PgDown` — navigate previous/next transaction header; when
  search bar is open, navigate previous/next match instead
- `Ctrl+Home / Ctrl+End` — cursor to start/end of file
- `Ctrl+A` — select all

**View filter**
- `Ctrl+L` — cycle view: All transactions → Cleared only → Unreconciled only → All
- Edits made in a filtered view are merged back into the full journal on save or
  filter change

**Other**
- `Ctrl+O` — transaction filter popup (UI fields present; criteria filtering **not
  yet implemented** — stub only; pressing Enter shows a notification directing users
  to `Ctrl+L`)
- `Ctrl+P` — command palette

---

## Window Panes — Removed in v0.8.0

The `BalanceSidebar` (account tree view), `RegisterPanel` (posting history), and all
reconcile-mode machinery (`ReconcileMixin`, `ReconcileStatusBar`, `ReconcileSummary`,
`ReconcileActions`) were removed in v0.8.0. The app is now a pure text editor with
no side panels.

These features are not planned to return unless explicitly requested.

---

## Upcoming Milestones

### Milestone A — Transaction Filter (Ctrl+O)

The `FilterPopup` is a UI stub. `apply_filter()` is unimplemented.

- [ ] Assemble `PyLedger.Query` from date-from, date-to, account, payee fields
- [ ] Smart date parsing: "last month", "ytd", "q1", ISO 8601, relative offsets
- [ ] Apply filter: show only matching transactions in the editor
- [ ] Clear filter restores full journal

### Milestone B — Autocomplete & Templates

- [ ] Tab autocomplete from declared accounts + all posting accounts in the loaded journal
- [ ] `Alt+P` / `Alt+N` — insert previous/next matching transaction template
  (Emacs `ledger-mode` convention)

### Milestone C — Emacs Ledger-mode Date Editing

- [ ] `Shift+Up / Shift+Down` — increment/decrement date by one day
- [ ] `Shift+Alt+Up / Shift+Alt+Down` — increment/decrement date by one month
- [ ] `Ctrl+K` — delete to end of line

### Milestone D — Performance & Polish

- [ ] Large journal support (10 000+ transactions without UI lag)
- [ ] Command palette: register all named actions
- [ ] Configurable keybinding profiles (MS Office / Emacs Ledger-mode stubs are in
  `src/ledger_editor/keybindings/`)
