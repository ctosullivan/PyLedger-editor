# Changelog

All notable changes to ledgerkit-editor are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).
Versions follow [Semantic Versioning](https://semver.org/).

## [Unreleased]

## [1.1.1] — 2026-09-09

### Fixed
- `Ctrl+O` filter popup: pressing `Tab` in an **empty** Account or Payee field now moves focus to the next field, instead of autocompleting to the first known account/payee name. Root cause: an empty prefix matches every entry in the index (by design, for the non-empty case), so `action_complete_field()` was treating "nothing typed yet" the same as "match everything."
  **Human:** "in the filter view if the account or payee field is empty, tab should move to the next field."
  **Claude:** `FilterPopup.action_complete_field()` now checks `input_widget.value` and falls through to `action_focus_next()` before attempting any completion when the field is empty. 2 new tests.
- `Ctrl+O` filter popup now retains its field text (typed but not yet applied, or already applied) across a close/reopen — previously closing the popup (`Ctrl+O` or `Escape`) and reopening it always started every field blank again, even though closing was already documented to leave an *applied* filter untouched; the fields themselves just weren't part of that state.
  **Human:** "When the filter view is closed and then opened again it should retain the current filters."
  **Claude:** Added `FilterPopup.field_values()` (reads all four Input values) and an `initial_values` constructor parameter (pre-fills them on `compose()`). `LedgerApp` now holds `_filter_field_values`, captured from the popup via `field_values()` right before `action_toggle_filter()` removes it, and passed back in as `initial_values` on the next open. 3 new tests.

## [1.1.0] — 2026-09-09

### Added
- `Ctrl+O`'s Date From/Date To fields now recognise a much wider range of smart dates: calendar-week phrases (`this week`, `last week`, weeks start Monday), `this month` (alongside the existing `last month`), `this year` (alongside `last year`), a year-month shorthand for a whole calendar month (`2026-02`, or unpadded `2026-2`), and a month name with or without a year (`september`, `sep 2026`, `September 2026` — a bare month name defaults to the current year). All of these are bounded periods, so used alone in one field they auto-fill the other side the same way `last month`/`ytd`/`q1`-`q4` already did.
  **Human:** "the Filter should recognise calendar months and smart dates such as this week, last week, this month, last year, September 2026, 2026-02 etc."
  **Claude:** Added `_YEAR_MONTH` and `_MONTH_YEAR` regexes plus a `_MONTH_NAMES` lookup and `_month_span()` helper to `date_parser.py`, and extended `_period_bounds()` to resolve all of the above to a `(start, end)` span; `parse_date()` was refactored to delegate to `_period_bounds()` for every named-period case instead of duplicating the logic, which is behaviour-preserving (all 46 pre-existing `test_date_parser.py` tests passed unchanged before the ~20 new tests were added). `docs/shortcuts.md` and the filter popup's Date From/Date To input placeholders updated to match.

- The view-filter status bar now shows a **visible/total transaction count** whenever any filter is active — e.g. "View: Cleared only + Filtered (Ctrl+O) (2/17)" — so you can see how much of the journal a filter is excluding without counting rows by hand. No count is shown for "All transactions" (nothing is being filtered, so it'd be redundant). Reflects live edits: adding/removing a transaction while filtered updates the total the next time the count is recomputed.
  **Human:** "Filter view should show number of transactions that have been filtered based on current filter from total transactions (i.e. 10/20)."
  **Claude:** Extended `ViewFilterBar.set_combined()` with optional `visible_count`/`total_count` parameters, appending `" (N/M)"` when both are given. `ViewFilterMixin._update_filter_bar()` computes them from `len(self._filter_journal.transactions)` / `len(self._filter_visible_indices)` whenever `_filter_is_active`, passing `None`/`None` otherwise. 4 new tests, including one confirming the count reflects real AND-narrowing (2/3 cleared → 1/3 once also narrowed by a Ctrl+O predicate).

- Tab autocomplete now also works in the Ctrl+O filter popup's Account and Payee fields, completing/cycling against the same account/payee index the main editor uses. No visible suggestion bar there (the popup doesn't have room) — the field's value just updates in place on each `Tab`, same bash-style cycling convention as the main editor. `Tab` in the Date fields is unaffected.
  **Human:** "tab autocomplete should also be available from the filter view if possible."
  **Claude:** Added `FilterPopup.action_complete_field()` (bound to `Tab`, `priority=True`) — a simpler, single-field variant of `AutocompleteMixin.action_autocomplete` for a whole `Input` value rather than a token within a multi-line `TextArea`. Reads `JournalEditor._journal_index` live via `self.app.query_one(JournalEditor)` at each Tab press (not cached at construction, so it can't go stale if the index is rebuilt — e.g. by a `Ctrl+S` — while the popup is open). Falls through to ordinary Tab focus-cycling for the Date fields, when `JournalEditor` can't be found, or when there's no match. 5 new tests.

### Fixed
- Investigated a UAT report that a transaction added while a `Ctrl+O` filter was active "was not saved as expected." Reproduced against the actual `LedgerApp` test harness four separate ways (direct API save, direct API + two `Ctrl+L` cycles, full UI + `Ctrl+S`, full UI + two `Ctrl+L` presses + `Ctrl+S`) and in every case the new transaction was correctly present in the saved file — no defect found in the merge/filter/save engine. The actual root cause was that `uat-testing/1.1.0-round3-checklist.md`'s own expected-value wording was misleading: it told testers to expect the *visible* count to go "from 6 to 7" after pressing `Ctrl+L` twice, but each `Ctrl+L` press also changes which cleared-state is required (ANDed with the still-active date filter), so the visible set's composition differs at each step rather than simply gaining one row — which reads as "the addition didn't take" even though it did.
  **Human:** UAT: "transaction added from filter was not saved as expected," reporting round-3 checklist step 1.
  **Claude:** Corrected the checklist wording to recommend `Ctrl+S` as the direct persistence check and explain the `Ctrl+L`-cycling nuance rather than asserting a specific intermediate count. Added `tests/test_filter_popup.py::TestFilterPopupEditPersistence` (2 tests) as a permanent regression guard for "add while `Ctrl+O`-filtered, then save" and "...then `Ctrl+L`-cycle twice, then save."
- `Ctrl+O`'s Date From/Date To fields now bound a named period ("last month", "today", "yesterday", "last year", "q1"–"q4", "ytd") to that whole period when used **alone** in one field, instead of leaving it open-ended. `Date From = "last month"` (Date To blank) previously resolved to a single date (the 1st of last month) used as a floor with no ceiling — showing last month *and* everything since, including the current month — rather than last month only. `ytd` is bounded by today, not December 31st (it means "year to date", not "the whole year"). A plain ISO date or a relative offset (`-7d`) used alone is unaffected — those are single points in time, not spans with a natural other end, so they correctly stay open-ended.
  **Human:** UAT: "last month should display transactions for the last calendar month only", clarified via follow-up question to mean a bounded (start, end) range matching hledger's own period-expression convention, not the "most recent 30 days" or "current month" readings that were also plausible from the original report's wording.
  **Claude:** Added `date_parser._period_bounds()` (returns the (start, end) span for a period phrase) and made `parse_date_range()` auto-fill the blank side of the pair from it — symmetric in both directions (a period phrase in Date To alone now also produces a bounded range, not just its historical start-of-period value). 15 new tests in `test_date_parser.py`; one pre-existing test (`test_to_only`, `Date To = "today"` alone) had its expected value updated to reflect the corrected, and now intentional, behaviour. `dev-docs/api-spec.md`'s `parse_date_range` entry updated to match (protected file — approved).

- Ctrl+O with every filter field blank was reformatting the document (losing source amount spacing) and marking the file "modified" even though nothing was actually being filtered — it went through the same parse-and-re-serialise round-trip a real filter uses, which doesn't preserve original spacing on its own. An all-blank Apply is now treated as "no filter" (equivalent to Clear) rather than a "match everything" filter, so it's a true no-op. Separately, entering/exiting a *real* filter (Ctrl+L or a non-empty Ctrl+O) now re-applies the same commodity-formatting + column-alignment pass `Ctrl+S` uses, so the visible formatting stays consistent across a filter round-trip instead of reverting to ledgerkit's unaligned default output.
  **Human:** UAT on `release/1.1.0`: "an empty filter is removing the transaction formatting (amount alignments etc) and causing the file to appear modified following filter removal."
  **Claude:** `FilterPopup.apply_filter()` now posts `FilterCleared` instead of `FilterApplied` when every field is blank. `ViewFilterMixin._apply_view_filter()` now runs `extract_commodity_styles()`/`apply_commodity_styles()`/`align_posting_amounts()` on both the restore and filtered-view text, matching `action_save()`'s pipeline.
- The Ctrl+O filter popup's Clear button now also empties its own input fields, not just the applied filter.
  **Human:** UAT comment: "when clear is selected in the Transaction Filter popup, the text already entered in the filter fields should also be cleared."
  **Claude:** Added `FilterPopup._clear_fields()`, called from the Clear button handler.
- `Ctrl+O` is now reliably visible in the footer. Textual's `Footer` is a horizontally-scrolling container with an invisible scrollbar (`scrollbar-size: 0 0`) — a binding that doesn't fit the visible width silently scrolls out of sight rather than being hidden or dropped. `Ctrl+O` is an App-level binding, appended after `JournalEditor`'s own bindings in the footer's rendering order, making it the first casualty of a full row on a typical terminal width.
  **Human:** UAT comment: "the CTRL+O shortcut should be displayed in the bottom toolbar - replace the CTRL+S shortcut if no space."
  **Claude:** Set `show=False` on the `ctrl+s` binding (freeing up footer width; Ctrl+S doesn't need the reminder) — implemented exactly as suggested rather than a more invasive footer-layout change.
- The Tab-autocomplete suggestion bar wasn't visible ("seems to be behind editor window") even though the completion itself worked. Root cause: `AutocompletePopup`'s CSS declared `height: 1` together with `border-top: solid $primary` — the border alone consumes the widget's only row, leaving zero rows for the candidate labels to actually render in.
  **Human:** UAT: "suggestion bar does not appear (seems to be behind editor window), however matches do autocomplete."
  **Claude:** Changed `AutocompletePopup`'s `height` from `1` to `2` (1 row border + 1 row content). New regression test asserts `popup.region.height == 2` after `show()`.

### Changed
- `Ctrl+O`'s Transaction Filter and `Ctrl+L`'s cleared/uncleared cycle now **combine (AND)** instead of being mutually exclusive. Originally shipped in Phase 3 as "replace" (applying one exited the other); UAT found this mentally awkward, so they're now two independent dimensions — e.g. `Ctrl+L` "Cleared only" narrowed further by a `Ctrl+O` account/date/payee filter shows only transactions matching *both*, rather than the second one discarding the first. Either can be adjusted or cleared without disturbing the other: cycling `Ctrl+L` back to All leaves an active `Ctrl+O` filter in place, and clearing the `Ctrl+O` filter leaves any active `Ctrl+L` mode in place. The status bar composes a combined description (e.g. "View: Cleared only + Filtered (Ctrl+O)").
  **Human:** UAT comment: "desired behavior for Filter / Ctrl+L mutual is for them not to be mutually exclusive - plan to update accordingly," followed up with "implement changes & mutual exclusivity change."
  **Claude:** Added `ViewFilterMixin._filter_is_active` (true if either dimension is active); `_apply_view_filter`'s filtered branch now ANDs the cleared-mode check with the criteria predicate via a local `_matches()` closure instead of the predicate overriding it. `action_save()`'s merge-before-save check updated to use `_filter_is_active` too (previously checked only `_view_filter_mode`, which would have missed a Ctrl+O-only filter). Added `ViewFilterBar.set_combined()` to compose the status-bar label. Renamed and rewrote `tests/test_filter_popup.py::TestFilterMutualExclusivity` → `TestFilterCombination`, plus new coverage for both partial-clear directions. Updated `planning/next-release-phase-plan.md`, `docs/shortcuts.md`, `dev-docs/architecture.md`, and `dev-docs/api-spec.md` (protected file — approved) to match.

### Docs
- Fixed the drift flagged (but left unedited, pending approval) in the previous entry: `CLAUDE.md`'s "Folder Structure" section and `dev-docs/api-spec.md` both still documented `balance_sidebar.py`, `register_panel.py`, and the `reconcile_*.py` widgets removed in v0.8.0, and both were missing every module added since (the four `JournalEditor` mixins, `filter_popup.py`'s current Ctrl+O behaviour, `autocomplete_popup.py`, `view_filter_bar.py`, `query_match.py`, `journal_index.py`). Both are protected files (`CLAUDE.md`'s Unauthorised Change Rule) — explicit approval was requested and given before editing either.
  **Human:** "fix both files" (in response to the flagged drift), plus a request for an updated UAT checklist, an updated UAT sample journal if needed, and saved venv-setup/dev-install instructions.
  **Claude:** Rewrote `CLAUDE.md`'s Folder Structure tree and `dev-docs/api-spec.md`'s widget sections against the actual `src/ledgerkit_editor/` tree — removed the five stale sections, added accurate ones for `DateShiftMixin`, `TransactionBlocksMixin`, `ViewFilterMixin`, `AutocompleteMixin`, `AutocompletePopup`, `ViewFilterBar`, `query_match`, and `journal_index`, and updated `FilterPopup`/`SearchBar`/`LedgerApp` for their current message classes and actions.

### Added
- Two repeatable-process Claude Code skills, Phases 5–6 of `planning/next-release-phase-plan.md`: `.claude/skills/polish-codebase/SKILL.md` (an opt-in, non-functional-change pass — dead code, duplication, efficiency, `CLAUDE.md` convention compliance — with a hard behavior-unchanged gate; delegates the mechanical review to `/code-review` and `/simplify` rather than reinventing them) and `.claude/skills/document-package/SKILL.md` (a documentation-drift audit covering every doc in the repo, backstopping — not replacing — the existing same-response Documentation Sync Rule). Both are opt-in; neither runs automatically. `CONTRIBUTING.md` points at both.
  **Human:** Implement the remainder of the next-release plan; Phases 5–6 cover "A repeatable process and accompanying Claude skill ... to polish and simplify" and "... to document the package in a best practice manner."
  **Claude:** Wrote both `SKILL.md` files per the plan's process descriptions. Then ran `document-package`'s audit as its own pilot (see the plan's "Documentation drift found during investigation" for what it was built to catch) and fixed what it found: `dev-docs/architecture.md`'s Layout/Data Flow/ledgerkit-Integration-Points sections (still described the pre-v0.8.0 `BalanceSidebar`/`RegisterPanel` architecture, months after removal), `ROADMAP.md`'s "What Is Shipped" header (stuck at v0.8.2; a `Shift+Up/Down` checklist item left unchecked despite shipping in v1.0.0), `README.md`'s "Planned / In Progress" section (listed the same removed side-panel features as if still planned), `knowledge_base/keybindings.md` (missing `Shift+Up/Down`/`Tab`/`Ctrl+Z`/`Ctrl+Y` bindings entirely; wrongly claimed `Ctrl+C`/`Ctrl+Z` are unsafe to bind — corrected with what Phase 1's Ctrl+C fix actually proved), and `CONTRIBUTING.md` (said "Python 3.11+", contradicting `pyproject.toml`'s actual `>=3.9`). `CLAUDE.md`'s Folder Structure and `dev-docs/api-spec.md` are both protected files with the same class of drift (still reference the removed widgets) — flagged in `AI-README.md` and this entry, not edited, pending explicit approval per the Unauthorised Change Rule. Added `AI-README.md` at the repo root — a dense, portable, agent-efficient project primer, meant to be pasted cold into a fresh AI session.

- Tab autocomplete for account and payee names — Milestone B (Phase 4a) in `ROADMAP.md`, Phase 4 of `planning/next-release-phase-plan.md`. On a posting line, `Tab` completes the account name being typed against every account declared with an `account` directive plus every account actually used anywhere in the journal; on a transaction header, past the date/flag/code, it completes the payee/description against declared `payee` directives plus every transaction description. Pressing `Tab` again cycles to the next match (bash-style), rather than an `Up`/`Down`-navigable dropdown — see `widgets/autocomplete.py`'s docstring for why that was deliberately scoped out. `Escape` dismisses the suggestion bar. The name index is a snapshot rebuilt on file load and after each `Ctrl+S`, not per keystroke (journals can run to 10,000+ transactions — see `ROADMAP.md` Milestone D). `Tab` itself was reclaimed for this — it was already established (Phase 1) to be a near-no-op focus-cycle in this single-pane editor. Phase 4b (`Alt+P`/`Alt+N` historical-account/template suggestion) was deferred to keep this scoped.
  **Human:** Implement the remainder of the next-release plan; Phase 4 covers "Tab autocompletion based on information in the ledger file - such as suggesting account names, transaction classification etc."
  **Claude:** Added `utils/journal_index.py` (pure `JournalIndex`/`build_journal_index()`, using `ledgerkit.Journal.declared_accounts`/`.declared_payees`), `widgets/autocomplete_popup.py` (`AutocompletePopup` — bottom-docked, never-focusable, same pattern as `SearchBar` rather than `FilterPopup`'s floating overlay, so the cursor never leaves the `LedgerTextArea`), and `widgets/autocomplete.py` (`AutocompleteMixin` + the pure `_completion_context()` that decides what, if anything, is completable at the cursor). 34 new tests across `test_journal_index.py` and a new `test_autocomplete.py` (397 → 431 total).

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
