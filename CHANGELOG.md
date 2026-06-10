# Changelog

All notable changes to ledgerkit-editor are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).
Versions follow [Semantic Versioning](https://semver.org/).

## [Unreleased]

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
