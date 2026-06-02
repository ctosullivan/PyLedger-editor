# Editor Architecture

## Module Responsibilities

```
src/ledgerkit_editor/
├── app.py                  — LedgerApp (Textual App root); composes layout,
│                             wires message handlers (SaveCompleted,
│                             CursorAccountChanged, AccountSelected)
├── widgets/
│   ├── transaction_table.py — JournalEditor: TextArea-based text editor;
│   │                          loads raw journal text; posts CursorAccountChanged
│   │                          on cursor move; Ctrl+S sorts+saves via journal_to_text
│   ├── balance_sidebar.py  — BalanceSidebar: reads ledgerkit balance(tree=True)
│   │                          asynchronously; Tree widget on the right panel;
│   │                          posts AccountSelected on node click
│   ├── register_panel.py   — RegisterPanel: DataTable showing the 10 most recent
│   │                          postings for the active account; updated by
│   │                          CursorAccountChanged and AccountSelected messages
│   └── filter_popup.py     — FilterPopup: overlay triggered by Ctrl+Shift+F
├── keybindings/
│   ├── office.py           — OfficeBindings mixin: MS Office / Excel action stubs
│   └── emacs_ledger.py     — EmacsLedgerBindings mixin: Emacs Ledger-mode stubs
├── commands/__init__.py    — Command + CommandHistory (Layer 2 undo/redo stack)
│                             and command palette provider stubs
└── utils/
    ├── date_parser.py      — Smart date string → datetime.date
    ├── ledger_io.py        — Thin wrappers over ledgerkit.load() and EditorDocument;
    │                         align_posting_amounts() (column-52 amount formatting)
    ├── atomic_edit.py      — atomic_edit() context manager (collapses N replace()
    │                         calls into one undo entry via EditHistory._undo_stack)
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
        │     → align_posting_amounts() → Path.write_text()
        │     → SaveCompleted → BalanceSidebar.refresh_balances()
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

        BalanceSidebar (separate ledgerkit.load() on each refresh)
                │  journal.balance(tree=True) → Tree nodes
                │
                └── node click → AccountSelected →
                        RegisterPanel.show_account(account)
```

## ledgerkit Integration Points

| Editor action | ledgerkit API |
|---|---|
| Open file | `ledgerkit.EditorDocument(path)` → `.lines` for raw text |
| Balance sidebar | `ledgerkit.load(path)` → `journal.balance(tree=True)` |
| Validate / sort on save | `ledgerkit.parse_string_lenient(text)` → `journal_to_text()` |
| Post-save checks | `ledgerkit.checks.run_basic_checks(journal)` |
| Register panel | `journal.register(query=ledgerkit.Query(account=...))` |

## Two-Layer Undo Stack

JournalEditor maintains two separate undo stacks:

| Layer | Stack | What it covers | Undo trigger |
|---|---|---|---|
| 1 — Text | `LedgerTextArea.history._undo_stack` (Textual EditHistory) | All free-form typing; `action_autofill` (via single `replace()`) | `Ctrl+Z` fallthrough |
| 2 — Model | `JournalEditor._command_history` (CommandHistory) | Future operations that mutate both buffer text and in-memory model objects | `Ctrl+Z` first priority |

`atomic_edit()` (`utils/atomic_edit.py`) collapses multiple `replace()` calls (e.g. `_bulk_toggle_cleared`) into one Layer-1 entry so a single `Ctrl+Z` reverses the whole operation.

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
- Amount column alignment (column 52) is a post-processing step in `action_save()`;
  it does not modify ledgerkit's `journal_to_text()` output in-place.

See `knowledge_base/design_decisions.md` for full rationale.
