# Editor Architecture

## Module Responsibilities

```
src/ledger_editor/
├── app.py                  — LedgerApp (Textual App root); composes layout,
│                             wires message handlers (SaveCompleted,
│                             CursorAccountChanged, AccountSelected)
├── widgets/
│   ├── transaction_table.py — JournalEditor: TextArea-based text editor;
│   │                          loads raw journal text; posts CursorAccountChanged
│   │                          on cursor move; Ctrl+S sorts+saves via journal_to_text
│   ├── balance_sidebar.py  — BalanceSidebar: reads PyLedger balance(tree=True)
│   │                          asynchronously; Tree widget on the right panel;
│   │                          posts AccountSelected on node click
│   ├── register_panel.py   — RegisterPanel: DataTable showing the 10 most recent
│   │                          postings for the active account; updated by
│   │                          CursorAccountChanged and AccountSelected messages
│   └── filter_popup.py     — FilterPopup: overlay triggered by Ctrl+Shift+F
├── keybindings/
│   ├── office.py           — OfficeBindings mixin: MS Office / Excel action stubs
│   └── emacs_ledger.py     — EmacsLedgerBindings mixin: Emacs Ledger-mode stubs
├── commands/__init__.py    — Command palette provider stubs
└── utils/
    ├── date_parser.py      — Smart date string → datetime.date
    ├── ledger_io.py        — Thin wrappers over PyLedger.load() and EditorDocument
    └── file_resolver.py    — Journal file resolution (CLI → env → default → None)
```

## Layout

```
Screen (horizontal)
├── JournalEditor     (TextArea, width: 1fr, left)
└── #right_panel      (Vertical container, width: 48, right)
    ├── BalanceSidebar  (Tree, height: 2fr, top)
    └── RegisterPanel   (DataTable, height: 14, bottom)
```

## Data Flow

```
Journal file on disk
        │
        ▼
JournalEditor (TextArea)
        │  loads raw text via EditorDocument.lines
        │
        ├── Ctrl+S:
        │     parse_string_lenient(text) → sort → journal_to_text()
        │     → Path.write_text()  → SaveCompleted →
        │           BalanceSidebar.refresh_balances()
        │
        ├── Shift+C: _cycle_flag_in_header(line) → textarea.replace()
        │
        └── cursor move: _account_at_cursor() → CursorAccountChanged
                │
                ▼
          RegisterPanel.show_account(account)
                │
                └── journal.register(query=Query(account=...))
                      → last 10 RegisterRow entries → DataTable

        BalanceSidebar (separate PyLedger.load() on each refresh)
                │  journal.balance(tree=True) → Tree nodes
                │
                └── node click → AccountSelected →
                        RegisterPanel.show_account(account)
```

## PyLedger Integration Points

| Editor action | PyLedger API |
|---|---|
| Open file | `PyLedger.EditorDocument(path)` → `.lines` for raw text |
| Balance sidebar | `PyLedger.load(path)` → `journal.balance(tree=True)` |
| Validate / sort on save | `PyLedger.parse_string_lenient(text)` → `journal_to_text()` |
| Post-save checks | `PyLedger.checks.run_basic_checks(journal)` |
| Register panel | `journal.register(query=PyLedger.Query(account=...))` |

## Key Design Decisions

- The TextArea is the **live text buffer** — `EditorDocument` is only used for
  the initial file load; saves write directly via `Path.write_text`.
- `journal_to_text()` does **not** preserve directives or comments — this is a
  known v0.5.0 limitation documented in `knowledge_base/`.
- `Query(account=X)` uses substring/regex matching (hledger semantics), so child
  accounts (e.g. `expenses:food:organic`) also appear in the register.
- `running_balance` in RegisterPanel is a plain `Decimal` with no commodity symbol.
- Validation errors on save produce notifications but do **not** block the write.
- Shift+C cycles 3 states: uncleared → pending → cleared → uncleared.

See `knowledge_base/design_decisions.md` for full rationale.
