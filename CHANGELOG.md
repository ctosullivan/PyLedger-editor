# Changelog

All notable changes to ledgerkit-editor are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).
Versions follow [Semantic Versioning](https://semver.org/).

## [Unreleased]

### Added
- Transaction Filter (`Ctrl+O`) is now fully implemented — Milestone A in `ROADMAP.md`, Phase 3 of `planning/next-release-phase-plan.md`. The popup's Date-from/Date-to fields accept smart dates (ISO 8601, `today`/`yesterday`/`last month`/`last year`/`ytd`, `q1`-`q4`, and now relative offsets like `-7d`/`+1m`/`+2w`/`-1y`, previously an unimplemented `TODO` in `date_parser.py`). Account and Payee fields follow hledger's own substring-or-regex convention (a pattern with any regex metacharacter is compiled and matched via `re.search`, otherwise it's a case-insensitive substring match) — this is where "Python regex" support comes from, matched intentionally to `ledgerkit.Query`'s own semantics rather than inventing a separate mode toggle. Applying a filter reuses the same show/edit/merge-back engine `Ctrl+L` already used (generalised — see "Changed" below); the two are mutually exclusive, and an invalid date or regex is rejected with a notification rather than applied.
  **Human:** Implement the remainder of the next-release plan; Phase 3 specifically covers "Filter transactions ... should support smart dates and Python regex."
  **Claude:** Implemented relative-offset parsing in `date_parser.py`; added `utils/query_match.py` (a local, documented reimplementation of `ledgerkit.reports._matches_pattern`/`_posting_matches`, which are private and not exported — see that module's docstring for why this isn't just imported); generalised `ViewFilterMixin` (`view_filter.py`) to accept an arbitrary predicate via a new `apply_criteria_filter()`/`clear_criteria_filter()` pair, alongside the existing `Ctrl+L` cycle; wired `FilterPopup` to build and post a pre-validated predicate, handled by `LedgerApp` (not `JournalEditor` — `FilterPopup` is a DOM sibling, not a child, so its messages bubble to the App). Added `Apply`/`Clear` buttons to the popup (previously only `Ctrl+L`-style Enter-does-nothing). 44 new tests across `test_date_parser.py`, `test_query_match.py`, and a new `test_filter_popup.py` (353 → 397 total).

### Changed
- `widgets/transaction_table.py` (944 lines — well over the Module Size Rule's 300–500 line guidance) split into four files: `transaction_table.py` (JournalEditor skeleton — BINDINGS, message classes, init/mount, save, cursor tracking; now 428 lines), `date_shift.py` (`DateShiftMixin` — Shift+Up/Down), `transaction_blocks.py` (`TransactionBlocksMixin` — Ctrl+T/Ctrl+G/Ctrl+R), `view_filter.py` (`ViewFilterMixin` — Ctrl+L). `JournalEditor` now inherits from all three mixins. No behaviour change — the full test suite (353 tests) passes unchanged; only test imports of the moved private helpers were updated to their new module paths.
  **Human:** Implement Phase 2 of the next-release plan (`planning/next-release-phase-plan.md`) — the module-size split, already approved as part of the plan's "Open decisions."
  **Claude:** Performed the split exactly as proposed in the plan (file-for-file), using the same mixin pattern already established by `keybindings/office.py`/`keybindings/emacs_ledger.py`. Updated `dev-docs/architecture.md`'s "Module Responsibilities" tree to match; flagged (but did not rewrite) that document's other, pre-v0.8.0-stale sections for the Phase 6 documentation-audit skill.

## [1.0.2] — 2026-09-08

### Fixed
- `P` price-directive lines are now syntax-highlighted field-by-field — the date, commodity, and rate (amount + its own commodity) each get their own colour, matching the level of detail given to transaction headers and postings. Previously a `P` line only got the flat "directive keyword + one uniform argument colour" treatment shared by every other directive, so the date/commodity/rate were visually indistinguishable from each other.
  **Human:** UAT for the 1.0.2 bug-fix batch passed; one further change: "a P directive transaction should be formatted ... in terms of syntax-highlighting - currently it has non[e]."
  **Claude:** Added `_PRICE_DIRECTIVE_HIGHLIGHT_RE` and `LedgerHighlighter._highlight_price_directive()`, which `_highlight_directive()` now tries first for any directive line; reuses the existing `_highlight_amount_section()` helper for the rate so P-directive amounts get the same positive/negative/zero colouring as posting amounts. Falls back to the generic flat highlighting for a `P` line too terse to match the full `P DATE COMMODITY RATE` grammar.

- Shift+Up/Down now shift the date in a `P` price-directive line (e.g. `P 2026-09-01 EUR 1.08 USD`), not just a transaction header date. Previously the date-shift logic only recognised `LineKind.XACT_HEADER` lines, so `P` directives — classified as generic `LineKind.DIRECTIVE` — silently fell through to text selection.
  **Human:** Implement Phase 1 of the next-release plan (`planning/next-release-phase-plan.md`), bug 1.1: "dates in P declarations are not being treated as dates."
  **Claude:** Added `_PRICE_DIRECTIVE_RE` to locate a `P` directive's date span, and extended `JournalEditor._shift_date_by()` to shift it the same way as a header date, sharing the existing `_shift_date_str`/`_normalize_date_str` helpers.

- Shift+Up/Down now recognise and correctly shift dates without a leading zero (e.g. `2026-9-1`), expanding them to zero-padded canonical form (`2026-09-01`) as part of the same keypress. Previously `_XACT_HEADER_RE`/`_TXN_HEADER_RE`/`_DATE_PARSE_RE` all hard-required 2-digit month/day, so an unpadded date wasn't even recognised as a transaction header — it fell through to `LineKind.UNKNOWN` with no highlighting and no date-shift support.
  **Human:** Implement Phase 1, bug 1.2: "dates where there is no leading zero ... are not being recognized as valid dates."
  **Claude:** Widened the three date regexes to accept 1–2 digit month/day; generalised `_date_subfield_at_col()` to derive field boundaries from the date string's own layout instead of a fixed 10-char assumption; added `_normalize_date_str()` to zero-pad before shifting.

- Ctrl+C while the search bar's input has focus now copies the currently highlighted search match's text to the clipboard, instead of falling through to Textual's built-in "press Ctrl+Q to quit" notification. Root cause: `Input.action_copy()` raises `SkipAction` when nothing is selected inside the input itself (the match is only highlighted in the journal `TextArea`, never selected in the search box), letting the non-priority key walk reach `App`'s default `ctrl+c → help_quit` binding.
  **Human:** Implement Phase 1, bug 1.3: "CTRL+C is then intercepted by the CLI as the quit command."
  **Claude:** Added `SearchBar.action_copy_match()` (non-priority, so a real text selection made inside the search box still copies normally via `Input`'s own binding first) that copies the active match's text via `LedgerTextArea.get_text_range()`.

- `Shift+PgUp` and jumping to a previous search match now keep the same 4-line context margin above the cursor that `Shift+PgDown`/next-match already kept below it. Previously `LedgerTextArea.scroll_cursor_visible()` only reserved bottom spacing, so upward navigation could scroll the cursor flush against the top of the viewport.
  **Human:** Implement Phase 1, bug 1.4: "not enough padding is provided ... more padding should be allowed similar to when SHIFT+PGDOWN is entered."
  **Claude:** Changed `scroll_cursor_visible()`'s `Spacing` from `bottom=4` to `top=4, bottom=4`.

## [1.0.1] — 2026-06-10

### Fixed
- `.tcss` theme file missing from pip-installed wheel; added `[tool.setuptools.package-data]` to `pyproject.toml` so `ledgerkit_editor/**/*.tcss` is included in the distribution.

## [1.0.0] — 2026-06-08

### Added
- Full-screen TextArea-based journal editor (`JournalEditor`) loading raw hledger
  journal text with Ctrl+S save (sort-by-date + amount alignment + directive preservation)
- hledger syntax highlighting — dates, payees, accounts, amounts, commodities,
  comments, directives — via pure-Python `LedgerHighlighter` (single O(N) scan)
- Monokai Pro default theme with runtime theme switching (`--theme=THEME` CLI flag)
- Incremental search bar with match highlighting (`Ctrl+F`, `Shift+PgUp/Down`)
- View filter cycling — All / Cleared-only / Unreconciled-only (`Ctrl+L`), with
  full directive preservation across filter round-trips
- Transaction block selection and duplication (`Ctrl+T`, `Ctrl+G`)
- Cleared/pending status toggle — single transaction (3-state cycle) and bulk
  selection (`Ctrl+R`)
- Insert today's date at cursor (`Ctrl+D`)
- Cursor-position-aware date shifting on header lines (`Shift+Up` / `Shift+Down`)
- Undo / Redo (`Ctrl+Z` / `Ctrl+Y`) via two-layer stack (CommandHistory + TextArea EditHistory)
- Atomic edit context manager (`utils/atomic_edit.py`) for multi-replace undo batching
- `--line=N` / `+N` CLI argument to open at a specific line on launch
- File path display with modified indicator in header
- Commodity format preservation on save — infers prefix/suffix, spacing, decimal mark,
  group separator, and precision from first-seen amounts and re-applies on each save
  (`utils/commodity_format.py`)
- Journal file resolution: CLI arg → `$LEDGER_FILE` → `~/.hledger.journal` → prompt
- Filter popup overlay stub (`Ctrl+O`)
- Command palette (`Ctrl+P`)
- 318-test pytest suite (`asyncio_mode = auto`), covering all widgets, keybindings,
  highlight engine, commodity formatting, date parsing, date shifting, undo/redo,
  view filter, file resolution, themes, and comprehensive hledger format fixtures
- GitHub Actions CI workflow (`.github/workflows/ci.yml`) — runs full test suite on
  push/PR across Python 3.9, 3.11, and 3.13
- GitHub Actions publish workflow (`.github/workflows/publish.yml`) — builds and
  publishes to TestPyPI then PyPI on version tag, using OIDC trusted publishing

### Changed
- Dependency on `ledgerkit` now satisfied via PyPI (`ledgerkit==1.0.0.dev1`);
  vendor directory removed
- Project renamed from `PyLedger-editor` to `ledgerkit-editor`
- Python floor raised from `>=3.8` to `>=3.9` (required by Textual 8.x)
- Dev dependencies moved into `[project.optional-dependencies] dev` in `pyproject.toml`;
  `requirements-dev.txt` removed
- `conftest.py` simplified — no longer manipulates `sys.path` (ledgerkit is a normal install)

## [0.0.1] — 2026-05-10

### Added
- Initial project scaffold: directory structure, stub source files, `pyproject.toml`,
  `CLAUDE.md`, `CONTEXT.md`, `CONTRIBUTING.md`, `ROADMAP.md`, knowledge_base files,
  dev-docs stubs, `sample.journal` fixture, and initial pytest suite
- Sparse git checkout of PyLedger v0.5.0 vendor tree

---

[Unreleased]: https://github.com/ctosullivan/ledgerkit-editor/compare/v1.0.0...HEAD
[1.0.0]: https://github.com/ctosullivan/ledgerkit-editor/compare/v0.0.1...v1.0.0
[0.0.1]: https://github.com/ctosullivan/ledgerkit-editor/releases/tag/v0.0.1
