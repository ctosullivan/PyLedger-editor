# PyLedger Roadmap

Milestones track the planned development path. Each milestone corresponds to one
or more GitHub commits and should leave the codebase in a releasable, tested state.

**Status key:** `[DONE]` · `[IN PROGRESS]` · `[PLANNED]` · `[BACKLOG]`

---

## Milestone 0 — Project Foundation `[DONE]`

Establish the project structure, tooling contracts, and data models so that all
subsequent work has a clean, documented base to build on.

**Scope:**
- Project scaffold: folder structure, `pyproject.toml`, `CLAUDE.md` rules
- Core data models: `Amount`, `Posting`, `Transaction`, `Journal`
- Initial documentation: `dev-docs/architecture.md`, `dev-docs/api-spec.md`,
  `dev-docs/hledger-compatibility.md`, `dev-docs/SYNC.md`
- Developer tooling: `.gitignore`, test conventions (`tests/README.md`),
  sample fixture (`tests/fixtures/sample.journal`)

**Exit criteria:** All models importable; `python -m unittest tests.test_parser -v` runs
with no errors (empty suite passes).

---

## Milestone 1 — Journal Parser `[DONE]`

Implement a working parser so that `.journal` files can be loaded into memory as
`Journal` objects, including key hledger directives.

**Scope:**
- `parse_string(text) -> Journal` — pure text parser ✅
- `load_journal(path) -> Journal` — file loader with include support (in `loader.py`) ✅
- `ParseError` with line-number context ✅
- Transaction header parsing (date, flag, code, description, comment) ✅
- Posting parsing (prefix/suffix commodity, thousands separator, elided amount,
  double-space separator rule) ✅
- Simple date formats: all three separators (`-`, `/`, `.`), optional leading
  zeros, year-omitted with inference ✅
- Block comments (`comment` / `end comment` directive) ✅
- **P directive** (`P DATE COMMODITY PRICE`) — market price declarations stored
  in `Journal.prices` as `PriceDirective` objects ✅
- **alias directive** (`alias OLD=NEW` / `alias /REGEX/=REPLACEMENT` /
  `end aliases`) — account names rewritten at parse time within the current file ✅
- **include directive** (`include other.journal`) — embeds entries and directives
  from another `.journal` or `.ledger` file inline; relative, absolute, tilde,
  and glob paths supported; circular include detection; format-prefix rejection ✅
- **account directive** (`account ACCOUNT`) — declares an account name; stored
  in `Journal.declared_accounts` ✅
- **commodity directive** (`commodity $1,000.00` / `commodity EUR`) — declares a
  commodity symbol; stored in `Journal.declared_commodities` ✅
- **payee directive** (`payee PAYEE`) — declares a payee name; stored in
  `Journal.declared_payees` ✅
- **Validation / checks module** (`checks.py`) — `CheckError`, individual check
  functions (`autobalanced`, `accounts`, `commodities`, `payees`,
  `ordereddates`, `uniqueleafnames`), and runners ✅
- **Default autobalanced gate** — all CLI commands validate transaction balance
  before executing ✅
- **`-s`/`--strict` flag** — additionally checks that all accounts and
  commodities are declared ✅
- **`check [NAME...]` command** — run individual or grouped checks on demand ✅
- Module-level API: `Journal` report methods (`.balance()`, `.register()`,
  `.accounts()`, `.stats()`); `PyLedger.load()` convenience function;
  `python -m PyLedger` entry point ✅
- Regex documentation rule enforced on all patterns ✅
- `dev-docs/hledger-compatibility.md` updated with transaction block structure,
  P directive, alias directive, include directive, account/commodity/payee
  directives, and validation checks table ✅

**Exit criteria:**
- `python -m unittest tests.test_parser tests.test_reports tests.test_loader tests.test_checks tests.test_cli -v` — all 213 tests pass ✅
- `python -m PyLedger print tests/fixtures/sample.journal` outputs all
  5 transactions correctly ✅
- P directives parsed and stored in `journal.prices` ✅
- Account aliases applied correctly against a fixture covering both simple and
  regex alias forms ✅
- `include` directive resolves relative, absolute, tilde, and glob paths;
  included file entries appear in the resulting `Journal` as if written inline ✅
- `python -m PyLedger -s -f tests/fixtures/strict_valid.journal stats` exits 0 ✅
- Unbalanced transaction causes exit 1 on any command ✅
- `python -m PyLedger check ordereddates -f tests/fixtures/sample.journal` runs cleanly ✅

---

## Milestone 2 — Core Reports `[DONE]`

Implement the `Query` filter dataclass, all four report functions, and the
`ReportSpec` / `ReportSection` foundation for custom report layouts.

**Scope:**
- `Query` dataclass in `models.py` — filter criteria for all report functions ✅
- `accounts(journal, query=None) -> list[str]` — fully implemented ✅
- `balance(journal, query=None) -> dict[str, Decimal]` — fully implemented ✅
- `register(journal, query=None) -> list[RegisterRow]` — fully implemented ✅
- `stats(journal, query=None) -> JournalStats` — extended with partial query support ✅
- `RegisterRow` dataclass moved to `models.py` ✅
- `ReportSection`, `ReportSpec` (frozen), `ReportSectionResult` dataclasses in `models.py` ✅
- `balance_from_spec(journal, spec, query=None)` — proof-of-concept implementation ✅
- All new types re-exported from `PyLedger.__init__` ✅
- `tests/fixtures/filtered.journal` — 6-transaction, 64-day fixture with elided posting ✅
- Full test suite for all new functionality (`tests/test_reports.py`) — 92 tests ✅
- `dev-docs/api-spec.md` updated to mark all functions `[IMPLEMENTED]` ✅
- `docs/python-api.md` updated with `Query` and `ReportSpec` worked examples ✅
- **Balance assertions** — inline `=`, `==`, `=*`, `==*` syntax parsed and validated ✅
  - `BalanceAssertion` dataclass in `models.py`; `Posting.balance_assertion` field ✅
  - `check_assertions` added to `checks.py` as a basic check (date-order, all variants) ✅
  - `-I`/`--ignore-assertions` CLI flag ✅
  - `assertions_pass.journal` and `assertions_fail.journal` fixtures ✅

**Deferred to Milestone 3:**
- CLI filter flags (`--account`, `--date`, `--payee`) wiring Query to the CLI
- Journal-comment-based `ReportSpec` parsing (`; report` / `; end report` syntax)
- Full `stats` query support (account-level filters on `account_count` / `account_depth`)
- Commodity valuation using `Journal.prices` (multi-commodity balance reports)

**Exit criteria:**
- `python -m unittest discover -s tests -t . -v` — all 363 tests pass ✅
- `from PyLedger import Query, ReportSpec, ReportSection, ReportSectionResult, balance_from_spec` succeeds ✅
- `balance`, `register`, `accounts`, `stats` each return correct results with no query ✅
- `balance(journal, query=Query(account="expenses"))` returns only expense rows ✅
- `balance(journal, query=Query(depth=1))` returns only top-level account balances ✅
- `balance_from_spec(journal, spec)` returns one `ReportSectionResult` per section ✅
- `stats(journal)` continues to produce identical output to Milestone 1 ✅
- `cli.py` unchanged from Milestone 1 state ✅

---

## Milestone 3 — Editor Readiness & Multi-Commodity `[DONE]`

Deliver multi-commodity balance reporting, a lenient parser for editor integrations,
and a complete in-memory editor layer so that a TUI package can load, mutate, and
save journal files without reaching into PyLedger internals.

**Completed scope:**
- `parse_string_lenient` — never-raises parser; returns `(Journal, list[ParseError])` ✅
- `CheckError.line_number` — 1-based source line on every check error ✅
- `balance()` returns `dict[str, dict[str, Decimal]]` (multi-commodity per account) ✅
- `balance(tree=True)` returns `list[BalanceRow]` with implicit parent aggregation ✅
- `resolve_elision()` public — N-commodity elided posting generates N inferred postings ✅
- `BalanceRow` dataclass in `models.py` ✅
- `SourceSpan` dataclass; `Transaction.source_span`, `raw_text`, `inline_comment` ✅
- `Posting.inline_comment` — inline `;` comment captured at parse time ✅
- `source_file` parameter on `parse_string` and `parse_string_lenient` ✅
- `check_transaction_autobalanced(txn)` — per-transaction validation without full journal ✅
- `writer.py` — `transaction_to_text`, `journal_to_text` ✅
- `editor_model.py` — `EditorDocument` (load / add / update / delete / save / reload / validate) ✅
- 461 tests across nine test modules ✅

**Deferred to future milestones:**
- CLI filter flags (`--account`, `--date`, `--payee`) wired to `Query`
- Journal-comment `ReportSpec` parsing (`; report` / `; end report` syntax)
- Full `stats` query support (account-level filters on `account_count` / `account_depth`)
- `pip install` packaging and `README.md` / `docs/` update with real usage examples

**Exit criteria met:**
- `python -m unittest discover -s tests -t . -v` — all 461 tests pass ✅
- `python -c "from PyLedger import writer, editor_model"` succeeds ✅
- `EditorDocument('tests/fixtures/sample.journal')` loads with `dirty=False`, 5 transactions ✅
- Round-trip smoke test: `journal_to_text` output re-parses to same transaction count ✅

---

## Future / Backlog `[BACKLOG]`

Items not scheduled for a milestone yet. Promote to a milestone when prioritised.

| Item | Notes |
|---|---|
| CLI filter flags (`--account`, `--date`, `--payee`) | Wire `Query` to CLI argument parser; deferred from Milestone 3 |
| Journal-comment `ReportSpec` parsing | `; report` / `; end report` block syntax; deferred from Milestone 3 |
| Full `stats` query support | Account-level filters on `account_count` / `account_depth`; deferred from Milestone 3 |
| `pip install` packaging & docs | `pip install -e .` smoke test; `README.md` and `docs/` real usage examples; deferred from Milestone 3 |
| `EditorDocument` include-directive support | Currently include directives are silently ignored; needs multi-file span tracking |
| Account type inference | Infer assets/liabilities/income/expenses from name prefix |
| Periodic/auto postings | Out of scope for v1 |
| Secondary dates | `2024-01-15=2024-01-20` |
| `stats`: peak live memory (`X MB live`) | Requires `psutil` (third-party) or platform-specific syscall; not in scope without user approval of the dependency |
| `stats`: peak allocated memory (`X MB alloc`) | Implementable via stdlib `tracemalloc`; deferred to keep scope small |
| `stats`: per-reporting-interval output | Show stats broken down by week/month/year; needs date-interval logic |

---

## Deciding What Goes Into a Milestone

Before starting a new milestone, the user specifies the scope. Claude then:
1. Confirms the scope against `dev-docs/hledger-compatibility.md` (supported features only)
2. Updates this file to move the milestone from `[PLANNED]` to `[IN PROGRESS]`
3. Implements, tests, and updates docs in the same response
4. Updates this file to `[DONE]` **only when the user explicitly confirms the
   milestone is complete**, and adds a `CHANGELOG.md` entry at that point
