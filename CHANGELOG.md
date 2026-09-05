# Changelog

All notable changes to ledgerkit-editor are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).
Versions follow [Semantic Versioning](https://semver.org/).

## [Unreleased]

### Fixed
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
