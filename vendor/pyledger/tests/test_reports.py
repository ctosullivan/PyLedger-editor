"""Tests for PyLedger.reports — full Milestone 2 suite.

Covers: Query, pattern matching, accounts(), balance(), register(), stats(),
ReportSpec/ReportSection dataclasses, and balance_from_spec().

Primary fixture: tests/fixtures/filtered.journal
  Transactions: 6 (2024-01-01 to 2024-03-05, 64-day span)
  Accounts:
    assets:bank:checking      balance: £9,641.00
    equity:opening-balances   balance: -£5,000.00
    income:salary             balance: -£6,000.00  (last salary posting is elided)
    expenses:housing:rent     balance: £1,200.00
    expenses:food:groceries   balance: £150.00
    expenses:food:coffee      balance: £9.00

Secondary fixture for stats tests: tests/fixtures/sample.journal (5 transactions).
"""

import dataclasses
import datetime
import os
import unittest
from decimal import Decimal

from PyLedger.loader import load_journal
from PyLedger.models import Amount, Journal, Posting, Query, Transaction
from PyLedger.parser import parse_string
from PyLedger.reports import (
    JournalStats,
    _matches_pattern,
    _posting_matches,
    accounts,
    balance,
    balance_from_spec,
    register,
    stats,
)

import PyLedger


FIXTURES_DIR = os.path.join(os.path.dirname(__file__), "fixtures")
SAMPLE_JOURNAL = os.path.join(FIXTURES_DIR, "sample.journal")
FILTERED_JOURNAL = os.path.join(FIXTURES_DIR, "filtered.journal")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _txn(
    date: str,
    description: str,
    postings: list[tuple[str, str | None]],
) -> Transaction:
    """Build a Transaction from a date string, description, and posting tuples.

    Each posting tuple is (account, amount_str) where amount_str may be None
    for elided postings. Amount strings are parsed as "QUANTITY COMMODITY" or
    "SYMBOLQUANTITY" (e.g. "£10.00", "10.00 GBP").
    """
    ps = []
    for acct, amt_str in postings:
        if amt_str is None:
            ps.append(Posting(account=acct))
        elif amt_str.startswith("£") or amt_str.startswith("-£"):
            neg = amt_str.startswith("-")
            qty_str = amt_str.lstrip("-£")
            qty = Decimal(qty_str) * (-1 if neg else 1)
            ps.append(Posting(account=acct, amount=Amount(qty, "£")))
        else:
            parts = amt_str.split()
            ps.append(Posting(account=acct, amount=Amount(Decimal(parts[0]), parts[1])))
    return Transaction(
        date=datetime.date.fromisoformat(date),
        description=description,
        postings=ps,
    )


def _journal(*txns: Transaction) -> Journal:
    return Journal(transactions=list(txns))


# ---------------------------------------------------------------------------
# _matches_pattern
# ---------------------------------------------------------------------------

class TestMatchesPattern(unittest.TestCase):
    """Unit tests for the _matches_pattern helper."""

    def test_plain_substring_match(self):
        self.assertTrue(_matches_pattern("food", "expenses:food:groceries"))

    def test_plain_substring_case_insensitive(self):
        self.assertTrue(_matches_pattern("FOOD", "expenses:food:groceries"))

    def test_plain_substring_no_match(self):
        self.assertFalse(_matches_pattern("housing", "expenses:food:groceries"))

    def test_regex_metachar_dot(self):
        # '.' is a metacharacter → regex mode, matches any char
        self.assertTrue(_matches_pattern("food.groceries", "expenses:food:groceries"))

    def test_regex_anchored_start(self):
        self.assertTrue(_matches_pattern("^expenses", "expenses:food:groceries"))

    def test_regex_anchored_start_no_match(self):
        self.assertFalse(_matches_pattern("^income", "expenses:food:groceries"))

    def test_regex_pipe_or(self):
        self.assertTrue(_matches_pattern("food|housing", "expenses:food:groceries"))
        self.assertTrue(_matches_pattern("food|housing", "expenses:housing:rent"))
        self.assertFalse(_matches_pattern("food|housing", "income:salary"))

    def test_regex_case_insensitive(self):
        self.assertTrue(_matches_pattern("EXPENSES:FOOD", "expenses:food:groceries"))


# ---------------------------------------------------------------------------
# _posting_matches
# ---------------------------------------------------------------------------

class TestPostingMatches(unittest.TestCase):
    """Unit tests for the _posting_matches helper."""

    def setUp(self):
        self.txn = _txn("2024-02-10", "Supermarket", [
            ("expenses:food:groceries", "£150.00"),
            ("assets:bank:checking", "-£150.00"),
        ])
        self.food_posting = self.txn.postings[0]
        self.bank_posting = self.txn.postings[1]

    def test_none_query_matches_all(self):
        self.assertTrue(_posting_matches(self.food_posting, self.txn, None))
        self.assertTrue(_posting_matches(self.bank_posting, self.txn, None))

    def test_empty_query_matches_all(self):
        q = Query()
        self.assertTrue(_posting_matches(self.food_posting, self.txn, q))

    def test_account_filter_match(self):
        q = Query(account="expenses")
        self.assertTrue(_posting_matches(self.food_posting, self.txn, q))

    def test_account_filter_no_match(self):
        q = Query(account="expenses")
        self.assertFalse(_posting_matches(self.bank_posting, self.txn, q))

    def test_not_account_filter(self):
        q = Query(not_account="assets")
        self.assertTrue(_posting_matches(self.food_posting, self.txn, q))
        self.assertFalse(_posting_matches(self.bank_posting, self.txn, q))

    def test_depth_filter_includes_shallow(self):
        # expenses:food:groceries has depth 3; depth=3 should include it
        q = Query(depth=3)
        self.assertTrue(_posting_matches(self.food_posting, self.txn, q))

    def test_depth_filter_excludes_deep(self):
        # expenses:food:groceries has depth 3; depth=2 should exclude it
        q = Query(depth=2)
        self.assertFalse(_posting_matches(self.food_posting, self.txn, q))

    def test_date_from_filter(self):
        q = Query(date_from=datetime.date(2024, 2, 10))
        self.assertTrue(_posting_matches(self.food_posting, self.txn, q))
        q_after = Query(date_from=datetime.date(2024, 2, 11))
        self.assertFalse(_posting_matches(self.food_posting, self.txn, q_after))

    def test_date_to_filter(self):
        q = Query(date_to=datetime.date(2024, 2, 10))
        self.assertTrue(_posting_matches(self.food_posting, self.txn, q))
        q_before = Query(date_to=datetime.date(2024, 2, 9))
        self.assertFalse(_posting_matches(self.food_posting, self.txn, q_before))

    def test_payee_filter(self):
        q = Query(payee="Supermarket")
        self.assertTrue(_posting_matches(self.food_posting, self.txn, q))
        q_no = Query(payee="Coffee")
        self.assertFalse(_posting_matches(self.food_posting, self.txn, q_no))


# ---------------------------------------------------------------------------
# accounts()
# ---------------------------------------------------------------------------

class TestAccountsReport(unittest.TestCase):

    def setUp(self):
        self.journal = load_journal(FILTERED_JOURNAL)

    def test_all_accounts_no_query(self):
        result = accounts(self.journal)
        self.assertEqual(result, sorted([
            "assets:bank:checking",
            "equity:opening-balances",
            "income:salary",
            "expenses:housing:rent",
            "expenses:food:groceries",
            "expenses:food:coffee",
        ]))

    def test_returns_sorted(self):
        result = accounts(self.journal)
        self.assertEqual(result, sorted(result))

    def test_account_substring_filter(self):
        result = accounts(self.journal, query=Query(account="expenses"))
        self.assertEqual(result, [
            "expenses:food:coffee",
            "expenses:food:groceries",
            "expenses:housing:rent",
        ])

    def test_account_regex_filter(self):
        result = accounts(self.journal, query=Query(account="^income"))
        self.assertEqual(result, ["income:salary"])

    def test_date_range_filter(self):
        # Only Feb transactions touch expenses:housing:rent, expenses:food:*
        result = accounts(
            self.journal,
            query=Query(
                date_from=datetime.date(2024, 2, 1),
                date_to=datetime.date(2024, 2, 28),
            ),
        )
        self.assertIn("expenses:housing:rent", result)
        self.assertIn("expenses:food:groceries", result)
        self.assertIn("expenses:food:coffee", result)
        # No salary transactions in Feb → income:salary not present
        self.assertNotIn("income:salary", result)

    def test_no_match_returns_empty(self):
        result = accounts(self.journal, query=Query(account="nonexistent:account"))
        self.assertEqual(result, [])

    def test_method_on_journal_matches_function(self):
        self.assertEqual(self.journal.accounts(), accounts(self.journal))


# ---------------------------------------------------------------------------
# balance()
# ---------------------------------------------------------------------------

class TestBalanceReport(unittest.TestCase):

    def setUp(self):
        self.journal = load_journal(FILTERED_JOURNAL)

    def test_all_balances_no_query(self):
        result = balance(self.journal)
        self.assertEqual(result["assets:bank:checking"]["£"], Decimal("9641.00"))
        self.assertEqual(result["equity:opening-balances"]["£"], Decimal("-5000.00"))
        self.assertEqual(result["income:salary"]["£"], Decimal("-6000.00"))
        self.assertEqual(result["expenses:housing:rent"]["£"], Decimal("1200.00"))
        self.assertEqual(result["expenses:food:groceries"]["£"], Decimal("150.00"))
        self.assertEqual(result["expenses:food:coffee"]["£"], Decimal("9.00"))

    def test_six_accounts_returned(self):
        self.assertEqual(len(balance(self.journal)), 6)

    def test_account_substring_filter(self):
        result = balance(self.journal, query=Query(account="expenses"))
        self.assertIn("expenses:housing:rent", result)
        self.assertIn("expenses:food:groceries", result)
        self.assertIn("expenses:food:coffee", result)
        self.assertNotIn("assets:bank:checking", result)
        self.assertNotIn("income:salary", result)

    def test_depth_1_truncation(self):
        result = balance(self.journal, query=Query(depth=1))
        # All account names should be single-segment
        for acct in result:
            self.assertEqual(len(acct.split(":")), 1)
        # expenses subtotal = 1200 + 150 + 9 = 1359
        self.assertEqual(result["expenses"]["£"], Decimal("1359.00"))
        # income subtotal = -6000
        self.assertEqual(result["income"]["£"], Decimal("-6000.00"))
        # assets subtotal = 9641
        self.assertEqual(result["assets"]["£"], Decimal("9641.00"))

    def test_depth_2_truncation(self):
        result = balance(self.journal, query=Query(depth=2))
        self.assertIn("expenses:food", result)
        self.assertIn("expenses:housing", result)
        self.assertNotIn("expenses:food:groceries", result)
        # expenses:food = 150 + 9 = 159
        self.assertEqual(result["expenses:food"]["£"], Decimal("159.00"))

    def test_not_account_exclusion(self):
        result = balance(self.journal, query=Query(not_account="assets"))
        self.assertNotIn("assets:bank:checking", result)
        self.assertIn("income:salary", result)
        self.assertIn("expenses:food:coffee", result)

    def test_elided_posting_amount_inferred(self):
        # The last Salary transaction has income:salary as an elided posting.
        # Its inferred amount should be -£3,000.00, so total income:salary = -6000.
        result = balance(self.journal)
        self.assertEqual(result["income:salary"]["£"], Decimal("-6000.00"))

    def test_zero_balance_not_excluded(self):
        # A transaction with exactly offsetting postings should have zero balance.
        journal = _journal(
            _txn("2024-01-01", "Zero sum", [
                ("assets:cash", "£100.00"),
                ("assets:cash", "-£100.00"),
            ])
        )
        result = balance(journal)
        self.assertIn("assets:cash", result)
        self.assertEqual(result["assets:cash"]["£"], Decimal("0"))

    def test_method_on_journal_matches_function(self):
        via_method = self.journal.balance()
        via_function = balance(self.journal)
        self.assertEqual(via_method, via_function)

    def test_balance_is_balanced(self):
        # Sum of all amounts in a balanced journal must equal zero per commodity.
        result = balance(self.journal)
        total = sum(qty for d in result.values() for qty in d.values())
        self.assertEqual(total, Decimal("0"))


# ---------------------------------------------------------------------------
# register()
# ---------------------------------------------------------------------------

class TestRegisterReport(unittest.TestCase):

    def setUp(self):
        self.journal = load_journal(FILTERED_JOURNAL)
        self.rows = register(self.journal)

    def test_row_count_no_query(self):
        # 6 transactions, each with 2 postings = 12 rows
        self.assertEqual(len(self.rows), 12)

    def test_rows_in_journal_order(self):
        dates = [r.date for r in self.rows]
        self.assertEqual(dates, sorted(dates))

    def test_first_row(self):
        row = self.rows[0]
        self.assertEqual(row.date, datetime.date(2024, 1, 1))
        self.assertEqual(row.description, "Opening balance")

    def test_running_balance_accumulates(self):
        # running_balance for each row = cumulative sum of all prior amounts + this one
        running = Decimal(0)
        for row in self.rows:
            running += row.amount.quantity
            self.assertEqual(row.running_balance, running)

    def test_running_balance_final(self):
        # Sum of all posting amounts in a balanced journal = 0
        self.assertEqual(self.rows[-1].running_balance, Decimal("0"))

    def test_date_filter(self):
        rows = register(
            self.journal,
            query=Query(
                date_from=datetime.date(2024, 2, 1),
                date_to=datetime.date(2024, 2, 28),
            ),
        )
        # Feb has 3 transactions × 2 postings = 6 rows
        self.assertEqual(len(rows), 6)
        for row in rows:
            self.assertGreaterEqual(row.date, datetime.date(2024, 2, 1))
            self.assertLessEqual(row.date, datetime.date(2024, 2, 28))

    def test_account_filter(self):
        rows = register(self.journal, query=Query(account="expenses"))
        for row in rows:
            self.assertIn("expenses", row.account)

    def test_elided_posting_inferred_in_row(self):
        # The last Salary txn has income:salary as elided posting.
        # Its row should have amount.quantity == -3000.
        rows = register(self.journal, query=Query(account="income:salary"))
        salary_rows = [r for r in rows if r.account == "income:salary"]
        self.assertEqual(len(salary_rows), 2)
        amounts = sorted(r.amount.quantity for r in salary_rows)
        # Both salary postings should be -3000
        self.assertEqual(amounts, [Decimal("-3000.00"), Decimal("-3000.00")])

    def test_method_on_journal_matches_function(self):
        via_method = self.journal.register()
        via_function = register(self.journal)
        self.assertEqual(len(via_method), len(via_function))
        for m, f in zip(via_method, via_function):
            self.assertEqual(m.date, f.date)
            self.assertEqual(m.account, f.account)
            self.assertEqual(m.running_balance, f.running_balance)


# ---------------------------------------------------------------------------
# stats() — all existing tests preserved + query=None parity
# ---------------------------------------------------------------------------

class TestStatsSampleJournal(unittest.TestCase):
    """stats() against tests/fixtures/sample.journal."""

    def setUp(self):
        self.journal = load_journal(SAMPLE_JOURNAL)
        self.s = stats(self.journal)

    def test_transaction_count(self):
        self.assertEqual(self.s.transaction_count, 5)

    def test_included_files(self):
        self.assertEqual(self.s.included_files, 0)

    def test_date_range(self):
        self.assertEqual(self.s.date_range, (datetime.date(2024, 1, 1), datetime.date(2024, 1, 20)))

    def test_txns_span_days(self):
        # 2024-01-01 to 2024-01-20 inclusive = 20 days
        self.assertEqual(self.s.txns_span_days, 20)

    def test_account_depth(self):
        # assets:bank:checking has depth 3
        self.assertGreaterEqual(self.s.account_depth, 3)

    def test_commodity_count(self):
        self.assertEqual(self.s.commodity_count, 1)

    def test_commodities_list(self):
        self.assertIn("£", self.s.commodities)

    def test_price_count(self):
        self.assertEqual(self.s.price_count, 0)

    def test_payee_count(self):
        # 5 unique descriptions in sample.journal
        self.assertEqual(self.s.payee_count, 5)

    def test_account_count(self):
        # assets:bank:checking, equity:opening-balances, income:salary,
        # expenses:food:groceries, assets:bank:savings, expenses:food:coffee = 6
        self.assertEqual(self.s.account_count, 6)

    def test_source_file_set(self):
        self.assertIsNotNone(self.s.source_file)


class TestStatsEmptyJournal(unittest.TestCase):
    """stats() with no transactions."""

    def setUp(self):
        self.s = stats(parse_string(""))

    def test_transaction_count(self):
        self.assertEqual(self.s.transaction_count, 0)

    def test_date_range_none(self):
        self.assertIsNone(self.s.date_range)

    def test_last_txn_date_none(self):
        self.assertIsNone(self.s.last_txn_date)

    def test_txns_span_days_none(self):
        self.assertIsNone(self.s.txns_span_days)

    def test_account_count_zero(self):
        self.assertEqual(self.s.account_count, 0)

    def test_commodity_count_zero(self):
        self.assertEqual(self.s.commodity_count, 0)

    def test_txns_per_day_zero(self):
        self.assertEqual(self.s.txns_per_day, 0.0)

    def test_payee_count_zero(self):
        self.assertEqual(self.s.payee_count, 0)


class TestStatsDateRangeAndSpan(unittest.TestCase):
    """date_range, txns_span_days, and txns_per_day computed correctly."""

    def setUp(self):
        journal_text = """\
2024-03-01 First
    assets:cash  £10.00
    equity:open  -£10.00

2024-03-11 Second
    assets:cash  £20.00
    equity:open  -£20.00
"""
        self.s = stats(parse_string(journal_text))

    def test_date_range(self):
        self.assertEqual(
            self.s.date_range,
            (datetime.date(2024, 3, 1), datetime.date(2024, 3, 11)),
        )

    def test_txns_span_days(self):
        # 2024-03-01 to 2024-03-11 inclusive = 11 days
        self.assertEqual(self.s.txns_span_days, 11)

    def test_txns_per_day(self):
        # 2 transactions over 11 days
        self.assertAlmostEqual(self.s.txns_per_day, 2 / 11)

    def test_last_txn_date(self):
        self.assertEqual(self.s.last_txn_date, datetime.date(2024, 3, 11))

    def test_last_txn_days_ago_non_negative(self):
        self.assertGreaterEqual(self.s.last_txn_days_ago, 0)


class TestStatsMultipleCommodities(unittest.TestCase):
    """commodity_count and commodities list with two symbols."""

    def setUp(self):
        journal_text = """\
2024-01-01 Sterling purchase
    assets:gbp   £100.00
    assets:usd   -150.00 USD

2024-01-02 Another
    assets:gbp   £50.00
    assets:usd   -75.00 USD
"""
        self.s = stats(parse_string(journal_text))

    def test_commodity_count(self):
        self.assertEqual(self.s.commodity_count, 2)

    def test_commodities_contains_both(self):
        self.assertIn("£", self.s.commodities)
        self.assertIn("USD", self.s.commodities)

    def test_commodities_sorted(self):
        self.assertEqual(self.s.commodities, sorted(self.s.commodities))


class TestStatsPayeeDeduplication(unittest.TestCase):
    """payee_count deduplicates repeated descriptions."""

    def setUp(self):
        journal_text = """\
2024-01-01 Coffee
    expenses:coffee  £3.00
    assets:cash      -£3.00

2024-01-02 Coffee
    expenses:coffee  £3.50
    assets:cash      -£3.50

2024-01-03 Lunch
    expenses:food  £8.00
    assets:cash    -£8.00
"""
        self.s = stats(parse_string(journal_text))

    def test_payee_count(self):
        # "Coffee" appears twice but counts once; "Lunch" is distinct → 2
        self.assertEqual(self.s.payee_count, 2)


class TestStatsAccountDepth(unittest.TestCase):
    """account_depth equals the maximum colon-segment depth."""

    def setUp(self):
        journal_text = """\
2024-01-01 Deep account
    a:b:c:d  £1.00
    equity   -£1.00
"""
        self.s = stats(parse_string(journal_text))

    def test_account_depth(self):
        # a:b:c:d has 4 segments; equity has 1
        self.assertEqual(self.s.account_depth, 4)


class TestStatsModuleLevel(unittest.TestCase):
    """journal.stats() (method on Journal) returns same result as reports.stats()."""

    def test_module_level_call(self):
        journal = load_journal(SAMPLE_JOURNAL)
        via_function = stats(journal)
        via_method = journal.stats()
        self.assertEqual(via_function.transaction_count, via_method.transaction_count)
        self.assertEqual(via_function.account_count, via_method.account_count)
        self.assertEqual(via_function.commodities, via_method.commodities)
        self.assertEqual(via_function.date_range, via_method.date_range)

    def test_stats_query_none_identical_to_no_arg(self):
        journal = load_journal(SAMPLE_JOURNAL)
        self.assertEqual(
            stats(journal, query=None).transaction_count,
            stats(journal).transaction_count,
        )
        self.assertEqual(
            stats(journal, query=None).account_count,
            stats(journal).account_count,
        )

    def test_stats_date_filter_reduces_count(self):
        journal = load_journal(FILTERED_JOURNAL)
        # Full journal has 6 transactions; restrict to Jan only → 2
        result = stats(journal, query=Query(
            date_from=datetime.date(2024, 1, 1),
            date_to=datetime.date(2024, 1, 31),
        ))
        self.assertEqual(result.transaction_count, 2)


# ---------------------------------------------------------------------------
# ReportSpec and ReportSection dataclasses
# ---------------------------------------------------------------------------

class TestReportSpecDataclasses(unittest.TestCase):

    def test_frozen_report_section(self):
        section = PyLedger.ReportSection(name="Expenses", accounts=("expenses",))
        with self.assertRaises(dataclasses.FrozenInstanceError):
            section.name = "Changed"  # type: ignore[misc]

    def test_frozen_report_spec(self):
        spec = PyLedger.ReportSpec(
            name="Test",
            sections=(PyLedger.ReportSection("S", accounts=("a",)),),
        )
        with self.assertRaises(dataclasses.FrozenInstanceError):
            spec.name = "Changed"  # type: ignore[misc]

    def test_report_section_result_is_mutable(self):
        from PyLedger.reports import ReportSectionResult
        section = PyLedger.ReportSection(name="S", accounts=("a",))
        result = ReportSectionResult(section=section, rows={}, subtotal=Decimal(0))
        result.subtotal = Decimal(42)  # must not raise
        self.assertEqual(result.subtotal, Decimal(42))

    def test_import_from_pyledger(self):
        # All new public symbols must be importable from the top-level package.
        from PyLedger import (  # noqa: F401
            Query,
            ReportSection,
            ReportSpec,
            ReportSectionResult,
            balance_from_spec,
        )

    def test_construct_multi_section_spec(self):
        spec = PyLedger.ReportSpec(
            name="Income Statement",
            sections=(
                PyLedger.ReportSection("Income", accounts=("income",), invert=True),
                PyLedger.ReportSection("Expenses", accounts=("expenses",)),
            ),
        )
        self.assertEqual(len(spec.sections), 2)
        self.assertEqual(spec.sections[0].name, "Income")
        self.assertTrue(spec.sections[0].invert)
        self.assertFalse(spec.sections[1].invert)


# ---------------------------------------------------------------------------
# balance_from_spec()
# ---------------------------------------------------------------------------

class TestBalanceFromSpec(unittest.TestCase):

    def setUp(self):
        self.journal = load_journal(FILTERED_JOURNAL)

    def _income_expenses_spec(self) -> PyLedger.ReportSpec:
        return PyLedger.ReportSpec(
            name="Income Statement",
            sections=(
                PyLedger.ReportSection("Income",   accounts=("income",),   invert=True),
                PyLedger.ReportSection("Expenses", accounts=("expenses",)),
            ),
        )

    def test_single_section_rows_and_subtotal(self):
        spec = PyLedger.ReportSpec(
            name="Expenses only",
            sections=(
                PyLedger.ReportSection("Expenses", accounts=("expenses",)),
            ),
        )
        results = balance_from_spec(self.journal, spec)
        self.assertEqual(len(results), 1)
        section_result = results[0]
        self.assertIn("expenses:housing:rent", section_result.rows)
        self.assertIn("expenses:food:groceries", section_result.rows)
        self.assertIn("expenses:food:coffee", section_result.rows)
        # subtotal = 1200 + 150 + 9 = 1359
        self.assertEqual(section_result.subtotal, Decimal("1359.00"))

    def test_single_section_invert(self):
        spec = PyLedger.ReportSpec(
            name="Income",
            sections=(
                PyLedger.ReportSection("Income", accounts=("income",), invert=True),
            ),
        )
        results = balance_from_spec(self.journal, spec)
        section_result = results[0]
        # income:salary raw = -6000; inverted = +6000
        self.assertEqual(section_result.rows["income:salary"], Decimal("6000.00"))
        self.assertEqual(section_result.subtotal, Decimal("6000.00"))

    def test_multi_section_returns_one_result_per_section(self):
        spec = self._income_expenses_spec()
        results = balance_from_spec(self.journal, spec)
        self.assertEqual(len(results), 2)
        self.assertEqual(results[0].section.name, "Income")
        self.assertEqual(results[1].section.name, "Expenses")

    def test_multi_section_correct_values(self):
        spec = self._income_expenses_spec()
        results = balance_from_spec(self.journal, spec)
        income_result = results[0]
        expense_result = results[1]
        self.assertEqual(income_result.subtotal, Decimal("6000.00"))
        self.assertEqual(expense_result.subtotal, Decimal("1359.00"))

    def test_grand_total_arithmetic(self):
        spec = self._income_expenses_spec()
        results = balance_from_spec(self.journal, spec)
        grand_total = sum(r.subtotal for r in results)
        # income (inverted) = +6000, expenses = +1359; sum of all section subtotals = 7359
        self.assertEqual(grand_total, Decimal("7359.00"))

    def test_section_depth_overrides_outer_query(self):
        spec = PyLedger.ReportSpec(
            name="Expenses at depth 2",
            sections=(
                PyLedger.ReportSection("Expenses", accounts=("expenses",), depth=2),
            ),
        )
        # Outer query has no depth; section depth=2 truncates to expenses:food, expenses:housing
        results = balance_from_spec(self.journal, spec, query=Query(depth=3))
        section_result = results[0]
        self.assertIn("expenses:food", section_result.rows)
        self.assertIn("expenses:housing", section_result.rows)
        self.assertNotIn("expenses:food:groceries", section_result.rows)
        # expenses:food = 150 + 9 = 159
        self.assertEqual(section_result.rows["expenses:food"], Decimal("159.00"))

    def test_outer_query_date_filter_applies_to_all_sections(self):
        spec = self._income_expenses_spec()
        # Restrict to Jan only — only Opening balance and Salary txns
        results = balance_from_spec(
            self.journal,
            spec,
            query=Query(
                date_from=datetime.date(2024, 1, 1),
                date_to=datetime.date(2024, 1, 31),
            ),
        )
        income_result = results[0]
        expense_result = results[1]
        # Only one salary in Jan → income:salary raw = -3000, inverted = +3000
        self.assertEqual(income_result.subtotal, Decimal("3000.00"))
        # No expense transactions in Jan
        self.assertEqual(expense_result.subtotal, Decimal("0"))

    def test_section_exclude_omits_matching_accounts(self):
        spec = PyLedger.ReportSpec(
            name="Food only",
            sections=(
                PyLedger.ReportSection(
                    "Food",
                    accounts=("expenses",),
                    exclude=("housing",),
                ),
            ),
        )
        results = balance_from_spec(self.journal, spec)
        section_result = results[0]
        self.assertNotIn("expenses:housing:rent", section_result.rows)
        self.assertIn("expenses:food:groceries", section_result.rows)
        self.assertIn("expenses:food:coffee", section_result.rows)
        # subtotal = 150 + 9 = 159
        self.assertEqual(section_result.subtotal, Decimal("159.00"))

    def test_section_multiple_accounts_patterns_or_union(self):
        spec = PyLedger.ReportSpec(
            name="Income and Housing",
            sections=(
                PyLedger.ReportSection(
                    "Mixed",
                    accounts=("income:salary", "expenses:housing"),
                ),
            ),
        )
        results = balance_from_spec(self.journal, spec)
        section_result = results[0]
        self.assertIn("income:salary", section_result.rows)
        self.assertIn("expenses:housing:rent", section_result.rows)
        self.assertNotIn("expenses:food:groceries", section_result.rows)

    def test_elided_posting_inferred_in_spec(self):
        # income:salary in the last Salary txn is elided; spec should include it.
        spec = PyLedger.ReportSpec(
            name="Income",
            sections=(
                PyLedger.ReportSection("Income", accounts=("income",), invert=True),
            ),
        )
        results = balance_from_spec(self.journal, spec)
        # Both salary postings contribute; total inverted = +6000
        self.assertEqual(results[0].subtotal, Decimal("6000.00"))

    def test_empty_section_has_zero_subtotal(self):
        spec = PyLedger.ReportSpec(
            name="No match",
            sections=(
                PyLedger.ReportSection("Nothing", accounts=("nonexistent:account",)),
            ),
        )
        results = balance_from_spec(self.journal, spec)
        self.assertEqual(results[0].subtotal, Decimal("0"))
        self.assertEqual(results[0].rows, {})


# ---------------------------------------------------------------------------
# balance() — multi-commodity and tree mode
# ---------------------------------------------------------------------------

MULTICOMMODITY_JOURNAL = os.path.join(FIXTURES_DIR, "multicommodity.journal")


class TestBalanceMultiCommodity(unittest.TestCase):
    """balance() with multi-commodity journals and elided postings."""

    def setUp(self):
        self.journal = load_journal(MULTICOMMODITY_JOURNAL)

    def test_balance_returns_nested_dict(self):
        result = balance(self.journal)
        self.assertIsInstance(result, dict)
        for v in result.values():
            self.assertIsInstance(v, dict)

    def test_multicommodity_elided_resolves_correctly(self):
        # equity:opening-balances has one elided posting with 3 commodities.
        result = balance(self.journal)
        equity = result["equity:opening-balances"]
        self.assertIn("£", equity)
        self.assertIn("$", equity)
        self.assertIn("€", equity)
        # Each should be the negation of the total in that commodity.
        self.assertEqual(equity["£"], Decimal("-10000.00"))
        self.assertEqual(equity["$"], Decimal("-5000.00"))
        self.assertEqual(equity["€"], Decimal("-2000.00"))

    def test_balance_is_zero_per_commodity(self):
        result = balance(self.journal)
        totals: dict[str, Decimal] = {}
        for commodity_map in result.values():
            for comm, qty in commodity_map.items():
                totals[comm] = totals.get(comm, Decimal(0)) + qty
        for comm, total in totals.items():
            self.assertEqual(total, Decimal("0"), f"commodity {comm} does not net to 0")

    def test_single_commodity_account_has_one_key(self):
        result = balance(self.journal)
        self.assertEqual(set(result["expenses:rent"].keys()), {"£"})
        self.assertEqual(set(result["expenses:software"].keys()), {"$"})

    def test_balance_tree_returns_list(self):
        result = balance(self.journal, tree=True)
        self.assertIsInstance(result, list)

    def test_balance_tree_contains_balance_rows(self):
        from PyLedger.models import BalanceRow
        result = balance(self.journal, tree=True)
        for row in result:
            self.assertIsInstance(row, BalanceRow)

    def test_balance_tree_implicit_parents_present(self):
        result = balance(self.journal, tree=True)
        accounts_in_tree = {row.account for row in result}
        # "expenses" should appear as an implicit parent of expenses:rent, expenses:software etc.
        self.assertIn("expenses", accounts_in_tree)
        self.assertIn("assets", accounts_in_tree)

    def test_balance_tree_is_subtotal_for_implicit_parents(self):
        result = balance(self.journal, tree=True)
        expenses_row = next(r for r in result if r.account == "expenses")
        self.assertTrue(expenses_row.is_subtotal)

    def test_balance_tree_is_subtotal_false_for_leaf_accounts(self):
        result = balance(self.journal, tree=True)
        rent_row = next(r for r in result if r.account == "expenses:rent")
        self.assertFalse(rent_row.is_subtotal)

    def test_balance_tree_depth_correct(self):
        result = balance(self.journal, tree=True)
        depth_map = {row.account: row.depth for row in result}
        self.assertEqual(depth_map["expenses"], 0)
        self.assertEqual(depth_map["expenses:rent"], 1)

    def test_balance_tree_amounts_aggregate_descendants(self):
        # "expenses" subtotal should include rent (£), software ($), conference (€).
        result = balance(self.journal, tree=True)
        expenses = next(r for r in result if r.account == "expenses")
        self.assertIn("£", expenses.amounts)
        self.assertIn("$", expenses.amounts)
        self.assertIn("€", expenses.amounts)

    def test_balance_tree_alphabetical_order(self):
        result = balance(self.journal, tree=True)
        accounts_list = [row.account for row in result]
        self.assertEqual(accounts_list, sorted(accounts_list))

    def test_balance_flat_false_returns_dict(self):
        result = balance(self.journal, tree=False)
        self.assertIsInstance(result, dict)

    def test_register_multicommodity_elided_produces_multiple_rows(self):
        # The opening balances transaction has 1 elided posting with 3 commodities.
        # register() should produce 3 extra rows for the resolved elided posting.
        from PyLedger.reports import register
        rows = register(self.journal)
        equity_rows = [r for r in rows if r.account == "equity:opening-balances"]
        # 3 commodities → 3 synthetic postings → 3 rows for equity
        self.assertEqual(len(equity_rows), 3)
        commodities = {r.amount.commodity for r in equity_rows}
        self.assertEqual(commodities, {"£", "$", "€"})


if __name__ == "__main__":
    unittest.main()
