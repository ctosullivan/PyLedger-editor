# Editor Architecture

> **Note on staleness (2026-09-08):** "Module Responsibilities" below was
> rewritten to match the actual current `src/ledgerkit_editor/` tree as of
> the Phase 2 module split (see `planning/next-release-phase-plan.md`).
> "Layout", "Data Flow", and "ledgerkit Integration Points" below that,
> however, still describe the pre-v0.8.0 multi-panel architecture
> (`BalanceSidebar`, `RegisterPanel`) that was removed in v0.8.0 — the app
> is now a single-pane text editor with no side panels (see `ROADMAP.md`
> "Window Panes — Removed in v0.8.0"). Those sections are pending a full
> refresh; treat their message-flow diagrams as historical, not current.

## Module Responsibilities

```
src/ledgerkit_editor/
├── app.py                     — LedgerApp (Textual App root); composes
│                                 Header, file-path bar, JournalEditor, Footer;
│                                 owns the transaction filter popup (Ctrl+O)
├── widgets/
│   ├── transaction_table.py   — JournalEditor: TextArea-based text editor;
│   │                            loads raw journal text; Ctrl+S sorts+saves;
│   │                            BINDINGS, message classes, cursor tracking —
│   │                            deliberately thin, delegates larger concerns
│   │                            to the three mixins below (Module Size Rule
│   │                            split, Phase 2 of the next-release plan)
│   ├── date_shift.py          — DateShiftMixin: Shift+Up/Down date-field
│   │                            shifting (transaction headers and P price
│   │                            directives), plus the pure regex/arithmetic
│   │                            helpers it's built from
│   ├── transaction_blocks.py  — TransactionBlocksMixin: Ctrl+T (select/
│   │                            extend block), Ctrl+G (duplicate to end),
│   │                            Ctrl+R (single/bulk cleared toggle)
│   ├── view_filter.py         — ViewFilterMixin: shared parse → hide → merge
│   │                            edits back → restore engine for BOTH Ctrl+L
│   │                            (fixed cleared/uncleared cycle) and Ctrl+O
│   │                            (arbitrary predicate); the two are mutually
│   │                            exclusive — apply_criteria_filter() /
│   │                            action_cycle_view_filter() each exit the
│   │                            other before taking over
│   ├── view_filter_bar.py     — ViewFilterBar: 1-row status bar showing
│   │                            whichever of Ctrl+L/Ctrl+O is active
│   ├── ledger_textarea.py     — LedgerTextArea: TextArea subclass wiring in
│   │                            LedgerHighlighter syntax highlighting and
│   │                            search-match highlighting
│   ├── search_bar.py          — SearchBar: Ctrl+F incremental search bar,
│   │                            match highlighting, Ctrl+C copies the match
│   └── filter_popup.py        — FilterPopup: Ctrl+O overlay; builds a
│                                 validated predicate (smart dates via
│                                 utils/date_parser, account/payee via
│                                 utils/query_match) and posts FilterApplied/
│                                 FilterCleared — handled by LedgerApp
│                                 (app.py), not JournalEditor, since
│                                 FilterPopup is a sibling in the DOM, not a
│                                 child (messages bubble to the App)
├── highlighting/
│   ├── highlighter.py         — LedgerHighlighter: pure-Python, no-Textual-
│   │                            imports regex-based syntax highlighter
│   ├── theme_bridge.py        — Builds a Textual TextAreaTheme from the
│   │                            active app theme's CSS variables
│   └── tokens.py               — ledger.* token name constants
├── themes/                     — Bundled Theme + TextAreaTheme definitions
│                                 (currently Monokai Pro)
├── keybindings/
│   ├── office.py               — OfficeBindings mixin: MS Office / Excel action stubs
│   └── emacs_ledger.py         — EmacsLedgerBindings mixin: Emacs Ledger-mode stubs
├── commands/__init__.py        — Command + CommandHistory (Layer 2 undo/redo stack)
│                                 and command palette provider stubs
└── utils/
    ├── date_parser.py          — Smart date string → datetime.date; ISO 8601,
    │                             named periods, quarters, and relative
    │                             offsets ("-7d", "+1m", "+2w", "-1y")
    ├── query_match.py          — Local reimplementation of ledgerkit's
    │                             substring-or-regex Query matching
    │                             convention (its own version is private,
    │                             not exported — see the module docstring);
    │                             build_transaction_predicate() is what
    │                             FilterPopup ultimately hands to
    │                             ViewFilterMixin.apply_criteria_filter()
    ├── ledger_io.py            — Thin wrappers over ledgerkit.load()/journal_to_text();
    │                             align_posting_amounts() (column-52 amount formatting);
    │                             split_journal_segments() (directive/comment preservation)
    ├── commodity_format.py     — Infers and re-applies per-commodity display
    │                             formats (prefix/suffix, decimals, grouping)
    ├── atomic_edit.py          — atomic_edit() context manager (collapses N replace()
    │                             calls into one undo entry via EditHistory._undo_stack)
    └── file_resolver.py        — Journal file resolution (CLI → env → default → None)
```

## Layout (historical — see staleness note above)

```
Screen (horizontal)
├── JournalEditor     (TextArea, width: 1fr, left)
└── #right_panel      (Vertical container, width: 48, right)
    ├── BalanceSidebar  (Tree, height: 2fr, top)
    └── RegisterPanel   (DataTable, height: 14, bottom)
```

## Data Flow (historical — see staleness note above)

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

## ledgerkit Integration Points (historical — see staleness note above)

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
