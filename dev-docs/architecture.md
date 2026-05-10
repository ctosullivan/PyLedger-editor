# Editor Architecture

## Module Responsibilities

```
src/ledger_editor/
├── app.py                  — LedgerApp (Textual App root); composes layout
│                             and wires top-level keybindings
├── widgets/
│   ├── balance_sidebar.py  — BalanceSidebar: reads PyLedger balance(tree=True)
│   │                         asynchronously; renders a collapsible account tree
│   ├── transaction_table.py — TransactionTable: primary editing surface;
│   │                          all keybinding actions are dispatched here;
│   │                          wraps PyLedger.EditorDocument for in-memory state
│   └── filter_popup.py    — FilterPopup: overlay triggered by Ctrl+Shift+F;
│                             builds PyLedger.Query and posts to TransactionTable
├── keybindings/
│   ├── office.py           — OfficeBindings mixin: MS Office / Excel action stubs
│   └── emacs_ledger.py     — EmacsLedgerBindings mixin: Emacs Ledger-mode stubs
├── commands/__init__.py    — Command palette provider stubs
└── utils/
    ├── date_parser.py      — Smart date string → datetime.date
    ├── ledger_io.py        — Thin wrappers over PyLedger.load() and EditorDocument
    └── file_resolver.py    — Journal file resolution (CLI → env → default → None)
```

## Data Flow

```
Journal file on disk
        │
        ▼
PyLedger.EditorDocument(path)    ← wraps load + in-memory line buffer
        │
        ├──► journal.balance(tree=True) ──► BalanceSidebar (read-only)
        │
        └──► TransactionTable (read-write)
                  │
                  ├── Ctrl+S: sort + align → EditorDocument.save()
                  ├── Shift+C: toggle cleared/pending → EditorDocument.update_transaction()
                  ├── Ctrl+D: duplicate → EditorDocument.add_transaction()
                  └── Live edit: parse_string_lenient() + check_transaction_autobalanced()
                          │
                          └──► ValidationBar (warnings, non-blocking)
```

## PyLedger Integration Points

| Editor action | PyLedger API |
|---|---|
| Open file | `PyLedger.EditorDocument(path)` |
| Load for balance sidebar | `PyLedger.load(path)` → `journal.balance(tree=True)` |
| Validate live | `PyLedger.parse_string_lenient(text)` |
| Validate single txn | `PyLedger.check_transaction_autobalanced(txn)` |
| Serialise txn | `PyLedger.transaction_to_text(txn)` |
| Serialise journal | `PyLedger.journal_to_text(journal)` |
| In-memory edits | `EditorDocument.add_transaction()` / `.update_transaction()` / `.delete_transaction()` |
| Save to disk | `EditorDocument.save()` |
| Autocomplete | `journal.accounts()` + `journal.declared_accounts` |

## Key Design Decisions

- PyLedger is a **read-only vendor dependency** — never patched, never extended.
- `EditorDocument` is the single source of truth for in-memory state.
- Tidy on save = sort by date + re-align whitespace (not sort-only, not align-only).
- Validation errors on save produce warnings but do **not** block the write.
- Shift+C cycles 3 states: uncleared → pending → cleared → uncleared.

See `knowledge_base/design_decisions.md` for full rationale.
