# Editor Architecture

> Last audited 2026-09-08 against the actual `src/ledgerkit_editor/` tree,
> by `.claude/skills/document-package/SKILL.md`'s pilot run (see
> `planning/next-release-phase-plan.md` Phase 6). Previous drift this pass
> corrected: "Layout"/"Data Flow"/"ledgerkit Integration Points" described
> the pre-v0.8.0 `BalanceSidebar`/`RegisterPanel` architecture, removed in
> v0.8.0 (see `ROADMAP.md` "Window Panes — Removed in v0.8.0") — the app
> has been a single-pane text editor with no side panels since. Re-run that
> skill periodically; don't let this note itself go stale.

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
│   │                            to the four mixins below (Module Size Rule
│   │                            split, Phase 2 of the next-release plan)
│   ├── date_shift.py          — DateShiftMixin: Shift+Up/Down date-field
│   │                            shifting (transaction headers and P price
│   │                            directives), plus the pure regex/arithmetic
│   │                            helpers it's built from
│   ├── transaction_blocks.py  — TransactionBlocksMixin: Ctrl+T (select/
│   │                            extend block), Ctrl+G (duplicate to end),
│   │                            Ctrl+R (single/bulk cleared toggle)
│   ├── autocomplete.py        — AutocompleteMixin: Tab account/payee
│   │                            autocomplete (Phase 4a), bash-style
│   │                            Tab-cycling rather than a Up/Down dropdown
│   │                            — see the module docstring for why; also
│   │                            _completion_context(), the pure function
│   │                            deciding whether/what to complete at the
│   │                            cursor
│   ├── autocomplete_popup.py  — AutocompletePopup: bottom-docked, never-
│   │                            focusable suggestion bar (same docked-and-
│   │                            hidden pattern as search_bar.py, not
│   │                            filter_popup.py's floating overlay — driven
│   │                            entirely by AutocompleteMixin)
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
    ├── journal_index.py        — JournalIndex + build_journal_index(): account
    │                             and payee name index for Tab autocomplete,
    │                             from Journal.declared_accounts/declared_payees
    │                             plus every posting account / transaction
    │                             description seen — a snapshot, rebuilt by
    │                             JournalEditor on load and after each save,
    │                             not per keystroke
    ├── ledger_io.py            — Thin wrappers over ledgerkit.load()/journal_to_text();
    │                             align_posting_amounts() (column-52 amount formatting);
    │                             split_journal_segments() (directive/comment preservation)
    ├── commodity_format.py     — Infers and re-applies per-commodity display
    │                             formats (prefix/suffix, decimals, grouping)
    ├── atomic_edit.py          — atomic_edit() context manager (collapses N replace()
    │                             calls into one undo entry via EditHistory._undo_stack)
    └── file_resolver.py        — Journal file resolution (CLI → env → default → None)
```

## Layout

```
Screen (LedgerApp.compose())
├── Header
├── #file-path-bar     (Static, 1 row — resolved file path + "· modified")
├── JournalEditor       (width: 1fr — the entire editing surface)
│   ├── ViewFilterBar    (1 row, docked top — shows Ctrl+L/Ctrl+O status)
│   ├── LedgerTextArea   (#journal_textarea, height: 1fr — the live buffer)
│   ├── SearchBar        (docked bottom, hidden until Ctrl+F)
│   └── AutocompletePopup (docked bottom, hidden until Tab completes something)
└── Footer

FilterPopup (Ctrl+O) mounts as a Screen-level overlay — a sibling of
JournalEditor, not a child of it, unlike SearchBar/AutocompletePopup above.
That's why its FilterApplied/FilterCleared messages are handled by
LedgerApp rather than JournalEditor (messages bubble to ancestors, and
JournalEditor isn't one — see Module Responsibilities' filter_popup.py entry).
```

No side panels remain (`BalanceSidebar`, `RegisterPanel`, and all
reconcile-mode widgets were removed in v0.8.0 — see `ROADMAP.md` "Window
Panes — Removed in v0.8.0"). `JournalEditor` is the entire editing surface.

## Data Flow

```
Journal file on disk
        │
        ▼  on_mount(): Path(self.journal_path).read_text()
LedgerTextArea (#journal_textarea) — the live text buffer
        │
        ├── Ctrl+S (action_save, transaction_table.py):
        │     ledgerkit.parse_string_lenient(text) → sort by date
        │     → transaction_to_text() per txn, interleaved with the
        │       directive/comment blocks split_journal_segments() preserved
        │     → apply_commodity_styles() → align_posting_amounts()
        │     → textarea.load_text(sorted_text) + Path.write_text()
        │     → rebuild_journal_index() (refreshes Tab-autocomplete data)
        │     → SaveCompleted / FileModifiedChanged messages
        │
        ├── Ctrl+R (TransactionBlocksMixin.action_toggle_cleared /
        │     _bulk_toggle_cleared, transaction_blocks.py):
        │     _cycle_flag_in_header(line) → textarea.replace(), single or
        │     atomic_edit()-wrapped for a bulk selection
        │
        ├── Shift+Up/Down (DateShiftMixin._shift_date_by, date_shift.py):
        │     locates the date span (header or P directive) → textarea.replace()
        │
        ├── Ctrl+L / Ctrl+O (ViewFilterMixin, view_filter.py):
        │     parse_string_lenient(text) → hide non-matching transactions
        │     (cleared-state check, or an arbitrary predicate from
        │     query_match.build_transaction_predicate()) → textarea.load_text()
        │     → edits merged back into the parsed Journal on exit or save
        │
        ├── Tab (AutocompleteMixin.action_autocomplete, autocomplete.py):
        │     _completion_context() → JournalIndex.matching_accounts()/
        │     matching_payees() → textarea.replace() + AutocompletePopup.show()
        │
        └── cursor move (on_text_area_selection_changed):
              _account_at_cursor() → self._current_account. Tracked but
              currently unconsumed by anything else — a holdover from the
              removed BalanceSidebar/RegisterPanel era, when it drove a
              CursorAccountChanged message. Not a bug; just note it if
              you're wondering why nothing reacts to it.
```

## ledgerkit Integration Points

| Editor action | ledgerkit API |
|---|---|
| Open file | `Path(journal_path).read_text()` — raw text, not via ledgerkit; `utils/ledger_io.py` also exposes `load_journal()`/`save_journal()` wrapping `ledgerkit.load()`/`journal_to_text()`, tested in `test_ledger_io.py`, but the live `JournalEditor` load/save path (below) doesn't call them — they're a stable public utility, not currently in the app's own data flow |
| Validate / sort / save | `ledgerkit.parse_string_lenient(text)` → `transaction_to_text()` per transaction (not the whole-journal `journal_to_text()` — that path is used only for the Ctrl+L "restore full journal" case when the transaction count didn't change) |
| Post-save checks | `ledgerkit.checks.run_basic_checks(journal)` |
| Commodity formatting | `Journal.commodity_styles` (via `utils/commodity_format.extract_commodity_styles()`) |
| Transaction Filter (Ctrl+O) | `ledgerkit.Query` built by `FilterPopup`, matched via `utils/query_match.build_transaction_predicate()` (a local reimplementation — see that module's docstring) |
| Tab autocomplete | `Journal.declared_accounts` / `.declared_payees` (`utils/journal_index.py`) |

## Two-Layer Undo Stack

JournalEditor maintains two separate undo stacks:

| Layer | Stack | What it covers | Undo trigger |
|---|---|---|---|
| 1 — Text | `LedgerTextArea.history._undo_stack` (Textual EditHistory) | All free-form typing; `action_autofill` (via single `replace()`) | `Ctrl+Z` fallthrough |
| 2 — Model | `JournalEditor._command_history` (CommandHistory) | Future operations that mutate both buffer text and in-memory model objects | `Ctrl+Z` first priority |

`atomic_edit()` (`utils/atomic_edit.py`) collapses multiple `replace()` calls (e.g. `_bulk_toggle_cleared`) into one Layer-1 entry so a single `Ctrl+Z` reverses the whole operation.

## Key Design Decisions

- The `LedgerTextArea` **is** the live text buffer — loaded via a direct
  `Path.read_text()`/`Path.write_text()` round-trip, not through
  `ledgerkit.EditorDocument` (see "ledgerkit Integration Points" above).
- `transaction_to_text()`/`journal_to_text()` do **not** preserve directives
  or comments on their own — `action_save()` works around this by
  interleaving `split_journal_segments()`'s preserved non-transaction
  blocks between sorted transaction texts (`utils/ledger_io.py`).
- `Query(account=X)` (and the local `query_match.matches_pattern()`) use
  substring/regex matching (hledger semantics), so child accounts (e.g.
  `expenses:food:organic`) also match a parent-account filter.
- Validation errors on save produce notifications but do **not** block the
  write.
- `Ctrl+R` cycles 3 states: uncleared → pending (`!`) → cleared (`*`) →
  uncleared, single transaction or bulk over a multi-block selection.
- Amount column alignment (column 52) is a post-processing step in
  `action_save()` (`align_posting_amounts()`); it does not modify
  ledgerkit's own text output in place.

See `knowledge_base/design_decisions.md` for full rationale.
