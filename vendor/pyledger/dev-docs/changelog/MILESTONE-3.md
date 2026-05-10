# Milestone 3 — Editor Readiness & Multi-Commodity

Archived: 2026-05-09

Commits (oldest first):

---

### chore: release v0.3.0 and mark Milestone 2 done

**Human:** Mark Milestone 2 complete, archive its changelog entries, include limited multi-commodity support in Milestone 3 scope, bump version to 0.3.0.
**Claude:** Created `dev-docs/changelog/MILESTONE-2.md` with all five Milestone 2 commits (oldest first). Replaced those entries in `CHANGELOG.md` with a summary link. Marked Milestone 2 `[DONE]` in `ROADMAP.md`; added limited multi-commodity support to Milestone 3 candidate scope. Bumped `__version__` and `pyproject.toml` from `0.2.1` to `0.3.0`.

---

### feat: Milestone 3 — lenient parser, multi-commodity balance, tree mode, CheckError.line_number

**Human:** Implement Milestone 3: add `parse_string_lenient` for on-keystroke live parsing, add `CheckError.line_number` for clickable editor diagnostics, fix multi-commodity elision (one elided posting now generates N postings for N commodities), and change `balance()` to return `dict[str, dict[str, Decimal]]` with an optional `tree=True` mode returning `list[BalanceRow]`.

**Claude:** Added `Posting.inferred` field and `BalanceRow` dataclass to `models.py`. Added public `resolve_elision()` to `parser.py` that handles the N-commodity elided posting case; refactored parser body into `_parse_string_impl` with `skip_until_blank` error-recovery state; added `parse_string_lenient()` that never raises. Added `line_number: int | None = None` to `CheckError` and propagated it in all six check functions; removed the multi-commodity ambiguity error from `_check_txn_balanced` (one elided posting is always valid regardless of commodity count). Replaced `_infer_elided_posting_amount` with `resolve_elision()` in `reports.py`; updated `balance()` to return per-commodity nested dict and added `_build_balance_tree()` helper; updated `register()` and `balance_from_spec()`. Updated `cli.py` balance display to hledger-style: account name only on the last commodity line per account, negative amounts in ANSI red. Re-exported `BalanceRow`, `parse_string_lenient`, `resolve_elision` from `__init__.py`; bumped `__version__` to `"0.4.0"`. Added `tests/fixtures/multicommodity.journal`, `TestResolveElision` (11 tests), `TestParseStringLenient` (10 tests), `TestCheckErrorLineNumber` (6 tests), `TestBalanceMultiCommodity` (15 tests). Updated all existing balance assertions for the new nested-dict return type.

---

### feat: editor-readiness — SourceSpan, writer.py, editor_model.py, per-transaction validation

**Human:** Implement the five editor-readiness areas so that an external TUI package can load a journal with source positions, validate single transactions, serialise transactions to text, and apply add/update/delete changes to the in-memory document before writing back to disk.

**Claude:** Added `SourceSpan` dataclass to `models.py`; attached `source_span`, `raw_text`, and `inline_comment` fields (all `compare=False`) to `Transaction`, and `inline_comment` to `Posting`. Extended `_parse_string_impl` with `source_file` parameter, `all_lines` pre-split for `raw_text` extraction, `current_txn_last_lineno` / `last_posting_in_txn` tracking, and a `_flush_txn` helper that populates `SourceSpan` and `raw_text` on every flush path (blank line, new header, EOF). Standalone `;` comment lines inside a transaction block now attach to `Posting.inline_comment` (or `Transaction.inline_comment` before the first posting). Added `source_file: str = "(string)"` parameter to `parse_string` and `parse_string_lenient`; updated `loader.py` to pass the resolved absolute path. Added `check_transaction_autobalanced` to `checks.py` as a thin wrapper over `_check_txn_balanced`. Created `PyLedger/writer.py` with `transaction_to_text` (amount alignment, inline comments, all flags) and `journal_to_text`. Created `PyLedger/editor_model.py` with `EditorDocument` (load, add/update/delete with arithmetic span refresh, save, reload, validate). Updated `__init__.py` with new exports; updated `dev-docs/api-spec.md`; created `dev-docs/editor-readiness-decisions.md`. Added 56 new tests across `test_writer.py` (new), `test_editor_model.py` (new), `test_checks`, and `test_parser`. All 461 tests pass.
