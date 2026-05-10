# Changelog — Milestone 2: Core Reports

Archived on: 2026-05-03
GitHub commits: 1493424 · 2bf467e · acc93a3 · 5b9d383 · 786a198


### [1493424] — 2026-04-26 — chore: release v0.2.0 and start Milestone 2

**Human:** Bump version to 0.2.0 and mark Milestone 2 (Core Reports) as in progress.
**Claude:** Updated `__version__` in `PyLedger/__init__.py` and `version` in `pyproject.toml` from `0.1.2` to `0.2.0`. Updated `ROADMAP.md` to mark Milestone 2 `[IN PROGRESS]`.

---

### [2bf467e] — 2026-04-27 — chore: add knowledge base and CONTEXT.md

**Human:** Establish a permanent project knowledge base (`knowledge/`) and a session working-memory file (`CONTEXT.md`), and update `CLAUDE.md` to maintain both going forward.

**Claude:** Created `knowledge/DECISIONS.md` (8 entries covering non-obvious calls from Milestone 1), `knowledge/EDGE_CASES.md` (11 entries), `knowledge/ANTIPATTERNS.md` (4 entries), and `knowledge/DOMAIN_RULES.md` (9 domain rules). Created `CONTEXT.md` with current Milestone 2 state. Updated `CLAUDE.md` with a new Knowledge Base section, a Context File section (with maintenance instructions), and added `knowledge/` and `CONTEXT.md` to the folder structure diagram.

---

### [acc93a3] — 2026-05-02 — feat: implement Milestone 2 core reports with Query, ReportSpec, and hledger-aligned CLI output

**Human:** Implement Milestone 2 as specified in the planning prompt: `Query` dataclass for filtering, full implementations of `balance`, `register`, `accounts`, and `stats`, plus the `ReportSpec`/`ReportSection`/`ReportSectionResult` dataclass foundation and a `balance_from_spec` proof-of-concept function. Align `balance` and `register` CLI output to hledger format.

**Claude:** Added `Query`, `RegisterRow`, `ReportSection`, `ReportSpec`, and `ReportSectionResult` dataclasses to `models.py`. Moved `RegisterRow` from `reports.py` to `models.py`. Implemented `accounts()`, `balance()` (with depth-as-rollup semantics), `register()`, and `balance_from_spec()` in `reports.py`; extended `stats()` to accept an optional `query=` parameter with partial filter support. Rewrote balance and register CLI display with commodity-prefixed amounts, right-aligned columns, red negatives, running balance column, and account abbreviation. Added 92 report tests and 15 CLI tests. Updated `dev-docs/api-spec.md`, `ROADMAP.md`, `docs/python-api.md`.

---

### [5b9d383] — 2026-05-03 — feat: implement balance assertions (=, ==, =*, ==*)

**Human:** Implement hledger-style balance assertions and include in Milestone 2.

**Claude:** Added `BalanceAssertion` dataclass to `models.py` (fields: `amount`, `inclusive`, `sole_commodity`) and a new `balance_assertion` field on `Posting`. Extended `_parse_posting` in `parser.py` with `_ASSERTION_MARKER_RE` to detect and parse `=`, `==`, `=*`, `==*` markers inline in posting amount tokens. Added `check_assertions` to `checks.py` — processes postings in date order (then parse order), maintains per-account per-commodity running balances, validates all four assertion variants including sole-commodity and subaccount-inclusive checks. Added `"assertions"` to `BASIC_CHECK_NAMES` (runs automatically like `autobalanced`). Added `skip: frozenset[str] | None` parameter to `run_basic_checks`, `run_strict_checks`, `run_checks`. Added `-I`/`--ignore-assertions` CLI flag. Created `assertions_pass.journal` and `assertions_fail.journal` fixtures. Added `TestCheckAssertions` (12 tests) and `TestBalanceAssertions` (6 CLI tests). Updated `dev-docs/hledger-compatibility.md`, `dev-docs/api-spec.md`, `ROADMAP.md`, `knowledge/DECISIONS.md`. Balance assignments (elided amount + assertion) are parsed but not validated — deferred.

---

### [786a198] — 2026-05-03 — fix: accept trailing decimal point in amounts ($1,350,000.)

**Human:** Real journal file failed with `invalid amount: '$1,350,000.'`; hledger accepts trailing decimal points.
**Claude:** Changed `(?:\.\d+)?` → `(?:\.\d*)?` in `_AMOUNT` and `(?:,\d+)?` → `(?:,\d*)?` in `_AMOUNT_COMMA` in `parser.py`. Added two tests (`TestTrailingDecimal`). Documented as EC-013 in `knowledge/EDGE_CASES.md`.
