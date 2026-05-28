"""Tests for PyLedger.checks — check functions and CLI integration."""

import datetime
import os
import pathlib
import sys
import textwrap
import unittest
from decimal import Decimal
from io import StringIO
from unittest.mock import patch

from PyLedger.checks import (
    CheckError,
    BASIC_CHECK_NAMES,
    STRICT_CHECK_NAMES,
    OTHER_CHECK_NAMES,
    check_parseable,
    check_autobalanced,
    check_assertions,
    check_accounts,
    check_commodities,
    check_payees,
    check_ordereddates,
    check_uniqueleafnames,
    check_transaction_autobalanced,
    run_basic_checks,
    run_strict_checks,
    run_checks,
)
from PyLedger.models import Amount, BalanceAssertion, Journal, Posting, Transaction
from PyLedger.parser import parse_string

FIXTURES = pathlib.Path(__file__).parent.parent / "fixtures"
SAMPLE_JOURNAL = FIXTURES / "sample.journal"
STRICT_VALID = FIXTURES / "strict_valid.journal"
STRICT_MISSING_ACCOUNTS = FIXTURES / "strict_missing_accounts.journal"
STRICT_MISSING_COMMODITY = FIXTURES / "strict_missing_commodity.journal"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _txn(
    date: str,
    description: str,
    *postings: tuple[str, str | None],
) -> Transaction:
    """Create a Transaction with named postings for testing.

    Each posting is (account, amount_str) where amount_str is a parseable
    amount string like '£10.00' or '-$5.00', or None for an elided posting.
    """
    from PyLedger.parser import _parse_amount

    parsed_postings = []
    for account, amount_str in postings:
        if amount_str is None:
            parsed_postings.append(Posting(account=account, amount=None))
        else:
            parsed_postings.append(
                Posting(account=account, amount=_parse_amount(amount_str, 0))
            )
    return Transaction(
        date=datetime.date.fromisoformat(date),
        description=description,
        postings=parsed_postings,
    )


def _journal(*transactions: Transaction, **kwargs) -> Journal:
    return Journal(transactions=list(transactions), **kwargs)


# ---------------------------------------------------------------------------
# check_parseable
# ---------------------------------------------------------------------------

class TestCheckParseable(unittest.TestCase):
    def test_always_passes(self):
        j = _journal()
        self.assertEqual(check_parseable(j), [])

    def test_passes_non_empty_journal(self):
        j = parse_string("2024-01-01 Test\n    assets  £10\n    income  -£10\n")
        self.assertEqual(check_parseable(j), [])


# ---------------------------------------------------------------------------
# check_autobalanced
# ---------------------------------------------------------------------------

class TestCheckAutobalanced(unittest.TestCase):
    def test_balanced_passes(self):
        t = _txn("2024-01-01", "A", ("assets", "£10.00"), ("income", "-£10.00"))
        self.assertEqual(check_autobalanced(_journal(t)), [])

    def test_unbalanced_fails(self):
        t = _txn("2024-01-01", "Bad", ("assets", "£10.00"), ("income", "£5.00"))
        errors = check_autobalanced(_journal(t))
        self.assertEqual(len(errors), 1)
        self.assertEqual(errors[0].check_name, "autobalanced")
        self.assertIn("not balanced", errors[0].message)

    def test_single_elided_posting_passes(self):
        t = _txn("2024-01-01", "Elided", ("assets", "£10.00"), ("income", None))
        self.assertEqual(check_autobalanced(_journal(t)), [])

    def test_multiple_elided_postings_fails(self):
        t = _txn("2024-01-01", "Multi-elided",
                 ("assets", None), ("income", None))
        errors = check_autobalanced(_journal(t))
        self.assertEqual(len(errors), 1)
        self.assertIn("multiple elided", errors[0].message)

    def test_elided_with_multi_commodity_now_valid(self):
        # hledger rule: one elided posting is valid regardless of commodity count.
        # resolve_elision() generates N synthetic postings — one per commodity.
        t = _txn("2024-01-01", "Multi-ccy",
                 ("assets", "£10.00"), ("other", "$5.00"), ("bridge", None))
        errors = check_autobalanced(_journal(t))
        self.assertEqual(errors, [])

    def test_multi_commodity_no_elided_balanced(self):
        # Two commodities, each balanced independently
        t = _txn("2024-01-01", "Balanced-multi",
                 ("assets:gbp", "£10.00"), ("income:gbp", "-£10.00"),
                 ("assets:usd", "$5.00"), ("income:usd", "-$5.00"))
        self.assertEqual(check_autobalanced(_journal(t)), [])

    def test_multi_commodity_no_elided_unbalanced(self):
        t = _txn("2024-01-01", "Unbal-multi",
                 ("assets:gbp", "£10.00"), ("income:gbp", "-£5.00"))
        errors = check_autobalanced(_journal(t))
        self.assertEqual(len(errors), 1)

    def test_empty_journal_passes(self):
        self.assertEqual(check_autobalanced(_journal()), [])

    def test_sample_journal_passes(self):
        from PyLedger.loader import load_journal
        j = load_journal(SAMPLE_JOURNAL)
        self.assertEqual(check_autobalanced(j), [])


# ---------------------------------------------------------------------------
# check_accounts
# ---------------------------------------------------------------------------

class TestCheckAccounts(unittest.TestCase):
    def test_declared_accounts_pass(self):
        t = _txn("2024-01-01", "A", ("assets:bank", "£10.00"), ("income", "-£10.00"))
        j = _journal(t, declared_accounts=["assets:bank", "income"])
        self.assertEqual(check_accounts(j), [])

    def test_undeclared_account_fails(self):
        t = _txn("2024-01-01", "A", ("assets:bank", "£10.00"), ("income", "-£10.00"))
        j = _journal(t, declared_accounts=["income"])  # assets:bank missing
        errors = check_accounts(j)
        self.assertEqual(len(errors), 1)
        self.assertIn("assets:bank", errors[0].message)

    def test_no_declarations_reports_first(self):
        t = _txn("2024-01-01", "A", ("assets:bank", "£10.00"), ("income", "-£10.00"))
        j = _journal(t)  # no declared_accounts
        errors = check_accounts(j)
        # hledger stops at the first undeclared account (posting order)
        self.assertEqual(len(errors), 1)
        self.assertIn("assets:bank", errors[0].message)

    def test_each_undeclared_reported_once(self):
        t1 = _txn("2024-01-01", "A", ("missing", "£10.00"), ("income", "-£10.00"))
        t2 = _txn("2024-01-02", "B", ("missing", "£5.00"), ("income", "-£5.00"))
        j = _journal(t1, t2, declared_accounts=["income"])
        errors = check_accounts(j)
        # "missing" should appear only once
        self.assertEqual(len(errors), 1)

    def test_case_sensitive(self):
        t = _txn("2024-01-01", "A", ("Assets:Bank", "£10.00"), ("income", "-£10.00"))
        j = _journal(t, declared_accounts=["assets:bank", "income"])  # different case
        errors = check_accounts(j)
        self.assertEqual(len(errors), 1)
        self.assertIn("Assets:Bank", errors[0].message)

    def test_empty_journal_passes(self):
        self.assertEqual(check_accounts(_journal()), [])


# ---------------------------------------------------------------------------
# check_commodities
# ---------------------------------------------------------------------------

class TestCheckCommodities(unittest.TestCase):
    def test_declared_commodity_passes(self):
        t = _txn("2024-01-01", "A", ("assets", "£10.00"), ("income", "-£10.00"))
        j = _journal(t, declared_commodities=["£"])
        self.assertEqual(check_commodities(j), [])

    def test_undeclared_commodity_fails(self):
        t = _txn("2024-01-01", "A", ("assets", "£10.00"), ("income", "-£10.00"))
        j = _journal(t)  # no declared_commodities
        errors = check_commodities(j)
        self.assertEqual(len(errors), 1)
        self.assertIn("£", errors[0].message)

    def test_zero_amount_no_commodity_exempt(self):
        # Posting with empty-string commodity (zero amount) should not flag
        t = Transaction(
            date=datetime.date(2024, 1, 1),
            description="Zero",
            postings=[
                Posting(account="assets", amount=Amount(Decimal("0"), "")),
                Posting(account="income", amount=Amount(Decimal("0"), "")),
            ],
        )
        j = _journal(t)
        self.assertEqual(check_commodities(j), [])

    def test_each_undeclared_reported_once(self):
        t1 = _txn("2024-01-01", "A", ("assets", "£5.00"), ("income", "-£5.00"))
        t2 = _txn("2024-01-02", "B", ("assets", "£3.00"), ("income", "-£3.00"))
        j = _journal(t1, t2)
        errors = check_commodities(j)
        self.assertEqual(len(errors), 1)

    def test_empty_journal_passes(self):
        self.assertEqual(check_commodities(_journal()), [])


# ---------------------------------------------------------------------------
# check_payees
# ---------------------------------------------------------------------------

class TestCheckPayees(unittest.TestCase):
    def test_declared_payee_passes(self):
        t = _txn("2024-01-01", "Supermarket", ("assets", "£5.00"), ("income", "-£5.00"))
        j = _journal(t, declared_payees=["Supermarket"])
        self.assertEqual(check_payees(j), [])

    def test_undeclared_payee_fails(self):
        t = _txn("2024-01-01", "Unknown Shop", ("assets", "£5.00"), ("income", "-£5.00"))
        j = _journal(t, declared_payees=["Supermarket"])
        errors = check_payees(j)
        self.assertEqual(len(errors), 1)
        self.assertIn("Unknown Shop", errors[0].message)

    def test_no_declarations_flags_all(self):
        t1 = _txn("2024-01-01", "Shop A", ("assets", "£5.00"), ("income", "-£5.00"))
        t2 = _txn("2024-01-02", "Shop B", ("assets", "£5.00"), ("income", "-£5.00"))
        j = _journal(t1, t2)
        errors = check_payees(j)
        self.assertEqual(len(errors), 2)

    def test_each_payee_reported_once(self):
        t1 = _txn("2024-01-01", "Shop", ("assets", "£5.00"), ("income", "-£5.00"))
        t2 = _txn("2024-01-02", "Shop", ("assets", "£3.00"), ("income", "-£3.00"))
        j = _journal(t1, t2, declared_payees=[])
        errors = check_payees(j)
        self.assertEqual(len(errors), 1)

    def test_empty_journal_passes(self):
        self.assertEqual(check_payees(_journal()), [])


# ---------------------------------------------------------------------------
# check_ordereddates
# ---------------------------------------------------------------------------

class TestCheckOrdereddates(unittest.TestCase):
    def _make_txn(self, date: str) -> Transaction:
        return Transaction(
            date=datetime.date.fromisoformat(date),
            description="T",
            postings=[],
        )

    def test_ordered_passes(self):
        j = _journal(self._make_txn("2024-01-01"), self._make_txn("2024-01-02"))
        self.assertEqual(check_ordereddates(j), [])

    def test_same_date_passes(self):
        j = _journal(self._make_txn("2024-01-01"), self._make_txn("2024-01-01"))
        self.assertEqual(check_ordereddates(j), [])

    def test_out_of_order_fails(self):
        j = _journal(self._make_txn("2024-01-10"), self._make_txn("2024-01-05"))
        errors = check_ordereddates(j)
        self.assertEqual(len(errors), 1)
        self.assertIn("out of order", errors[0].message)

    def test_empty_journal_passes(self):
        self.assertEqual(check_ordereddates(_journal()), [])

    def test_sample_journal_passes(self):
        from PyLedger.loader import load_journal
        j = load_journal(SAMPLE_JOURNAL)
        self.assertEqual(check_ordereddates(j), [])


# ---------------------------------------------------------------------------
# check_uniqueleafnames
# ---------------------------------------------------------------------------

class TestCheckUniqueLeafnames(unittest.TestCase):
    def _make_journal(self, *account_names: str) -> Journal:
        txns = []
        for name in account_names:
            txns.append(Transaction(
                date=datetime.date(2024, 1, 1),
                description="T",
                postings=[Posting(account=name, amount=None)],
            ))
        return Journal(transactions=txns)

    def test_unique_leaves_passes(self):
        j = self._make_journal("assets:bank:checking", "income:salary", "expenses:food")
        self.assertEqual(check_uniqueleafnames(j), [])

    def test_duplicate_leaf_fails(self):
        j = self._make_journal("assets:bank:checking", "savings:checking")
        errors = check_uniqueleafnames(j)
        self.assertEqual(len(errors), 1)
        self.assertIn("checking", errors[0].message)

    def test_empty_journal_passes(self):
        self.assertEqual(check_uniqueleafnames(_journal()), [])


# ---------------------------------------------------------------------------
# run_basic_checks, run_strict_checks, run_checks
# ---------------------------------------------------------------------------

class TestRunChecks(unittest.TestCase):
    def _balanced_journal(self) -> Journal:
        t = _txn("2024-01-01", "T", ("assets", "£10.00"), ("income", "-£10.00"))
        return _journal(t)

    def test_run_basic_checks_passes(self):
        j = self._balanced_journal()
        self.assertEqual(run_basic_checks(j), [])

    def test_run_basic_checks_fails_on_unbalanced(self):
        t = _txn("2024-01-01", "Bad", ("assets", "£10.00"), ("income", "£5.00"))
        j = _journal(t)
        errors = run_basic_checks(j)
        self.assertTrue(any(e.check_name == "autobalanced" for e in errors))

    def test_run_strict_checks_includes_basic(self):
        t = _txn("2024-01-01", "Bad", ("assets", "£10.00"), ("income", "£5.00"))
        j = _journal(t)
        errors = run_strict_checks(j)
        names = {e.check_name for e in errors}
        self.assertIn("autobalanced", names)

    def test_run_checks_unknown_name_raises(self):
        j = self._balanced_journal()
        with self.assertRaises(ValueError):
            run_checks(j, names=["nonexistent"])

    def test_run_basic_checks_skip_assertions(self):
        # Failing assertion is suppressed when skip=frozenset({"assertions"})
        j = parse_string(
            "2024-01-01 Test\n"
            "    assets:bank  £10 = £999\n"
            "    income       -£10\n"
        )
        errors_without_skip = run_basic_checks(j)
        errors_with_skip = run_basic_checks(j, skip=frozenset({"assertions"}))
        self.assertTrue(any(e.check_name == "assertions" for e in errors_without_skip))
        self.assertFalse(any(e.check_name == "assertions" for e in errors_with_skip))

    def test_run_checks_no_args_runs_basic(self):
        j = self._balanced_journal()
        self.assertEqual(run_checks(j), [])

    def test_run_checks_with_other_check(self):
        txn1 = Transaction(
            date=datetime.date(2024, 1, 10),
            description="Late",
            postings=[],
        )
        txn2 = Transaction(
            date=datetime.date(2024, 1, 5),
            description="Early",
            postings=[],
        )
        j = _journal(txn1, txn2)
        errors = run_checks(j, names=["ordereddates"])
        self.assertTrue(any(e.check_name == "ordereddates" for e in errors))

    def test_run_checks_dedup_when_also_in_strict(self):
        # accounts is a strict check; if strict=True, it should not be run twice
        t = _txn("2024-01-01", "T", ("assets", "£10.00"), ("income", "-£10.00"))
        j = _journal(t)
        errors = run_checks(j, names=["accounts"], strict=True)
        acct_errors = [e for e in errors if e.check_name == "accounts"]
        # Each undeclared account should appear once, not twice
        account_messages = [e.message for e in acct_errors]
        for msg in account_messages:
            self.assertEqual(account_messages.count(msg), 1)


# ---------------------------------------------------------------------------
# check_assertions
# ---------------------------------------------------------------------------

def _posting_with_assertion(
    account: str,
    amount_str: str | None,
    assertion_str: str,
    *,
    inclusive: bool = False,
    sole_commodity: bool = False,
) -> Posting:
    """Helper: build a Posting with a BalanceAssertion for direct check tests."""
    from PyLedger.parser import _parse_amount
    amount = _parse_amount(amount_str, 0) if amount_str else None
    return Posting(
        account=account,
        amount=amount,
        balance_assertion=BalanceAssertion(
            amount=_parse_amount(assertion_str, 0),
            inclusive=inclusive,
            sole_commodity=sole_commodity,
        ),
    )


class TestCheckAssertions(unittest.TestCase):

    def test_no_assertions_passes(self):
        t = _txn("2024-01-01", "T", ("assets", "£10"), ("income", "-£10"))
        self.assertEqual(check_assertions(_journal(t)), [])

    def test_empty_journal_passes(self):
        self.assertEqual(check_assertions(_journal()), [])

    def test_single_commodity_assertion_pass(self):
        # After posting £10 the balance should be £10
        txn = Transaction(
            date=datetime.date(2024, 1, 1),
            description="T",
            postings=[
                _posting_with_assertion("assets:bank", "£10", "£10"),
                Posting(account="income", amount=Amount(Decimal("-10"), "£")),
            ],
        )
        self.assertEqual(check_assertions(_journal(txn)), [])

    def test_single_commodity_assertion_fail(self):
        txn = Transaction(
            date=datetime.date(2024, 1, 1),
            description="T",
            postings=[
                _posting_with_assertion("assets:bank", "£10", "£999"),
                Posting(account="income", amount=Amount(Decimal("-10"), "£")),
            ],
        )
        errors = check_assertions(_journal(txn))
        self.assertEqual(len(errors), 1)
        self.assertEqual(errors[0].check_name, "assertions")
        self.assertIn("assets:bank", errors[0].message)
        self.assertIn("£10", errors[0].message)
        self.assertIn("£999", errors[0].message)

    def test_cumulative_balance_over_two_transactions(self):
        # Two transactions to same account; assertion checks running total
        txn1 = Transaction(
            date=datetime.date(2024, 1, 1),
            description="First",
            postings=[
                _posting_with_assertion("assets:bank", "£500", "£500"),
                Posting(account="equity", amount=Amount(Decimal("-500"), "£")),
            ],
        )
        txn2 = Transaction(
            date=datetime.date(2024, 1, 15),
            description="Second",
            postings=[
                _posting_with_assertion("assets:bank", "-£80", "£420"),
                Posting(account="expenses", amount=Amount(Decimal("80"), "£")),
            ],
        )
        self.assertEqual(check_assertions(_journal(txn1, txn2)), [])

    def test_sole_commodity_pass(self):
        # Account has only £; == assertion succeeds
        txn = Transaction(
            date=datetime.date(2024, 1, 1),
            description="T",
            postings=[
                _posting_with_assertion("assets:bank", "£10", "£10", sole_commodity=True),
                Posting(account="income", amount=Amount(Decimal("-10"), "£")),
            ],
        )
        self.assertEqual(check_assertions(_journal(txn)), [])

    def test_sole_commodity_fail_other_commodity_present(self):
        # Account has both £ and $; == £10 assertion fails due to non-zero $
        txn1 = Transaction(
            date=datetime.date(2024, 1, 1),
            description="Dollars",
            postings=[
                Posting(account="assets:bank", amount=Amount(Decimal("5"), "$")),
                Posting(account="income", amount=Amount(Decimal("-5"), "$")),
            ],
        )
        txn2 = Transaction(
            date=datetime.date(2024, 1, 2),
            description="Assertion",
            postings=[
                _posting_with_assertion("assets:bank", "£10", "£10", sole_commodity=True),
                Posting(account="income", amount=Amount(Decimal("-10"), "£")),
            ],
        )
        errors = check_assertions(_journal(txn1, txn2))
        # At minimum one error for the sole-commodity violation ($5 still present)
        self.assertTrue(any(e.check_name == "assertions" for e in errors))
        self.assertTrue(any("sole-commodity" in e.message for e in errors))

    def test_inclusive_assertion_sums_subaccounts(self):
        # assets:bank = £300, assets:bank:savings = £200; =* £500 should pass
        txn = Transaction(
            date=datetime.date(2024, 1, 1),
            description="T",
            postings=[
                Posting(account="assets:bank", amount=Amount(Decimal("300"), "£")),
                Posting(account="assets:bank:savings", amount=Amount(Decimal("200"), "£")),
                _posting_with_assertion("assets:bank", None, "£500", inclusive=True),
                Posting(account="equity", amount=Amount(Decimal("-500"), "£")),
            ],
        )
        self.assertEqual(check_assertions(_journal(txn)), [])

    def test_inclusive_assertion_fail(self):
        txn = Transaction(
            date=datetime.date(2024, 1, 1),
            description="T",
            postings=[
                Posting(account="assets:bank", amount=Amount(Decimal("300"), "£")),
                Posting(account="assets:bank:savings", amount=Amount(Decimal("200"), "£")),
                _posting_with_assertion("assets:bank", None, "£999", inclusive=True),
                Posting(account="equity", amount=Amount(Decimal("-500"), "£")),
            ],
        )
        errors = check_assertions(_journal(txn))
        self.assertEqual(len(errors), 1)
        self.assertIn("assets:bank", errors[0].message)

    def test_date_order_not_parse_order(self):
        # txn2 is parsed first (higher source_line) but has an earlier date.
        # After processing in date order: txn2 (Jan 1) then txn1 (Jan 10).
        # Assertion in txn1 sees the running total after both, which is £150.
        txn1 = Transaction(
            date=datetime.date(2024, 1, 10),
            description="Later date, parsed first",
            source_line=1,
            postings=[
                _posting_with_assertion("assets:bank", "£100", "£150"),
                Posting(account="income", amount=Amount(Decimal("-100"), "£")),
            ],
        )
        txn2 = Transaction(
            date=datetime.date(2024, 1, 1),
            description="Earlier date, parsed second",
            source_line=100,
            postings=[
                Posting(account="assets:bank", amount=Amount(Decimal("50"), "£")),
                Posting(account="equity", amount=Amount(Decimal("-50"), "£")),
            ],
        )
        # journal stores txn1 then txn2 (parse order), but check must sort by date
        self.assertEqual(check_assertions(_journal(txn1, txn2)), [])

    def test_fixture_assertions_pass(self):
        from PyLedger.loader import load_journal
        j = load_journal(FIXTURES / "assertions_pass.journal")
        self.assertEqual(check_assertions(j), [])

    def test_fixture_assertions_fail(self):
        from PyLedger.loader import load_journal
        j = load_journal(FIXTURES / "assertions_fail.journal")
        errors = check_assertions(j)
        self.assertEqual(len(errors), 1)
        self.assertIn("assets:checking", errors[0].message)


# ---------------------------------------------------------------------------
# CLI integration — default basic-check gate
# ---------------------------------------------------------------------------

_UNBALANCED_JOURNAL = textwrap.dedent("""\
    2024-01-01 Bad transaction
        assets:bank  £50.00
        expenses:food  £50.00
""")

_BALANCED_JOURNAL = textwrap.dedent("""\
    2024-01-01 Good transaction
        assets:bank  £50.00
        income:salary  -£50.00
""")

_DECLARED_JOURNAL = textwrap.dedent("""\
    account assets:bank
    account income:salary
    commodity £

    2024-01-01 Good transaction
        assets:bank  £50.00
        income:salary  -£50.00
""")


def _write_temp(content: str, suffix: str = ".journal") -> pathlib.Path:
    import tempfile
    f = tempfile.NamedTemporaryFile(
        suffix=suffix, mode="w", encoding="utf-8", delete=False
    )
    f.write(content)
    f.close()
    return pathlib.Path(f.name)


class TestCLIDefaultAutobalanced(unittest.TestCase):
    """Default basic-check gate fires on every CLI command."""

    def test_unbalanced_journal_exits_1_on_stats(self):
        tmp = _write_temp(_UNBALANCED_JOURNAL)
        try:
            buf = StringIO()
            with patch("sys.stderr", buf):
                from PyLedger.cli import main
                code = main(["-f", str(tmp), "stats"])
            self.assertEqual(code, 1)
            self.assertIn("not balanced", buf.getvalue())
        finally:
            os.unlink(str(tmp))

    def test_unbalanced_journal_exits_1_on_print(self):
        tmp = _write_temp(_UNBALANCED_JOURNAL)
        try:
            from PyLedger.cli import main
            code = main(["-f", str(tmp), "print"])
            self.assertEqual(code, 1)
        finally:
            os.unlink(str(tmp))

    def test_balanced_journal_exits_0_on_stats(self):
        tmp = _write_temp(_BALANCED_JOURNAL)
        try:
            buf = StringIO()
            with patch("sys.stdout", buf):
                from PyLedger.cli import main
                code = main(["-f", str(tmp), "stats"])
            self.assertEqual(code, 0)
        finally:
            os.unlink(str(tmp))

    def test_sample_journal_passes_by_default(self):
        from PyLedger.cli import main
        code = main(["-f", str(SAMPLE_JOURNAL), "stats"])
        self.assertEqual(code, 0)


class TestCLIStrictFlag(unittest.TestCase):
    """CLI strict mode (-s) reports accounts/commodities errors."""

    def test_strict_fails_without_declarations(self):
        tmp = _write_temp(_BALANCED_JOURNAL)
        try:
            buf = StringIO()
            with patch("sys.stderr", buf):
                from PyLedger.cli import main
                code = main(["-s", "-f", str(tmp), "stats"])
            self.assertEqual(code, 1)
            output = buf.getvalue()
            self.assertIn("has not been declared", output)
            self.assertIn("assets:bank", output)
        finally:
            os.unlink(str(tmp))

    def test_strict_passes_with_full_declarations(self):
        tmp = _write_temp(_DECLARED_JOURNAL)
        try:
            buf = StringIO()
            with patch("sys.stdout", buf):
                from PyLedger.cli import main
                code = main(["-s", "-f", str(tmp), "stats"])
            self.assertEqual(code, 0)
        finally:
            os.unlink(str(tmp))

    def test_strict_fails_missing_account_declarations(self):
        buf = StringIO()
        with patch("sys.stderr", buf):
            from PyLedger.cli import main
            code = main(["-s", "-f", str(STRICT_MISSING_ACCOUNTS), "stats"])
        self.assertEqual(code, 1)
        output = buf.getvalue()
        self.assertIn("has not been declared", output)
        self.assertIn("assets:bank:checking", output)

    def test_strict_fails_missing_commodity_declarations(self):
        buf = StringIO()
        with patch("sys.stderr", buf):
            from PyLedger.cli import main
            code = main(["-s", "-f", str(STRICT_MISSING_COMMODITY), "stats"])
        self.assertEqual(code, 1)
        output = buf.getvalue()
        self.assertIn("has not been declared", output)
        self.assertIn("£", output)

    def test_strict_passes_valid_fixture(self):
        buf = StringIO()
        with patch("sys.stdout", buf):
            from PyLedger.cli import main
            code = main(["-s", "-f", str(STRICT_VALID), "stats"])
        self.assertEqual(code, 0)


class TestCLICheckCommand(unittest.TestCase):
    """check command runs checks and exits 0/1."""

    def test_check_no_args_passes_balanced(self):
        from PyLedger.cli import main
        code = main(["-f", str(SAMPLE_JOURNAL), "check"])
        self.assertEqual(code, 0)

    def test_check_ordereddates_passes_ordered(self):
        from PyLedger.cli import main
        code = main(["-f", str(SAMPLE_JOURNAL), "check", "ordereddates"])
        self.assertEqual(code, 0)

    def test_check_detects_out_of_order(self):
        content = textwrap.dedent("""\
            2024-01-10 Late
                assets  £10.00
                income  -£10.00

            2024-01-05 Early
                assets  £10.00
                income  -£10.00
        """)
        tmp = _write_temp(content)
        try:
            buf = StringIO()
            with patch("sys.stderr", buf):
                from PyLedger.cli import main
                code = main(["-f", str(tmp), "check", "ordereddates"])
            self.assertEqual(code, 1)
            self.assertIn("out of order", buf.getvalue())
        finally:
            os.unlink(str(tmp))

    def test_check_unknown_name_exits_1(self):
        from PyLedger.cli import main
        buf = StringIO()
        with patch("sys.stderr", buf):
            code = main(["-f", str(SAMPLE_JOURNAL), "check", "notacheck"])
        self.assertEqual(code, 1)
        self.assertIn("unknown check", buf.getvalue())

    def test_check_strict_flag_adds_strict_checks(self):
        tmp = _write_temp(_BALANCED_JOURNAL)
        try:
            buf = StringIO()
            with patch("sys.stderr", buf):
                from PyLedger.cli import main
                code = main(["-s", "-f", str(tmp), "check"])
            self.assertEqual(code, 1)
            output = buf.getvalue()
            self.assertIn("has not been declared", output)
            self.assertIn("assets:bank", output)
        finally:
            os.unlink(str(tmp))

    def test_check_silent_on_success(self):
        out_buf = StringIO()
        err_buf = StringIO()
        with patch("sys.stdout", out_buf), patch("sys.stderr", err_buf):
            from PyLedger.cli import main
            code = main(["-f", str(SAMPLE_JOURNAL), "check"])
        self.assertEqual(code, 0)
        self.assertEqual(out_buf.getvalue(), "")
        self.assertEqual(err_buf.getvalue(), "")


# ---------------------------------------------------------------------------
# CheckError.line_number propagation
# ---------------------------------------------------------------------------

class TestCheckErrorLineNumber(unittest.TestCase):
    """line_number field is propagated by check functions."""

    def test_checkerror_line_number_defaults_to_none(self):
        err = CheckError(check_name="test", message="msg")
        self.assertIsNone(err.line_number)

    def test_checkerror_line_number_can_be_set(self):
        err = CheckError(check_name="test", message="msg", line_number=42)
        self.assertEqual(err.line_number, 42)

    def test_autobalanced_error_carries_source_line(self):
        # Build a transaction with a known source_line that fails balance.
        t = Transaction(
            date=datetime.date(2024, 1, 1),
            description="Unbalanced",
            postings=[
                Posting(account="assets", amount=Amount(Decimal("10"), "£")),
            ],
            source_line=7,
        )
        errors = check_autobalanced(_journal(t))
        self.assertEqual(len(errors), 1)
        self.assertEqual(errors[0].line_number, 7)

    def test_autobalanced_multicommodity_elided_passes_with_no_line_number_issue(self):
        # Multi-commodity elided is now valid — no error, so no line_number to check.
        t = _txn("2024-01-01", "Multi-ccy",
                 ("a", "£10.00"), ("b", "$5.00"), ("equity", None))
        self.assertEqual(check_autobalanced(_journal(t)), [])

    def test_payees_error_carries_source_line(self):
        t = Transaction(
            date=datetime.date(2024, 1, 1),
            description="Undeclared Payee",
            postings=[Posting(account="a", amount=Amount(Decimal("1"), "£"))],
            source_line=15,
        )
        j = Journal(
            transactions=[t],
            declared_payees=["Other Payee"],
        )
        errors = check_payees(j)
        self.assertEqual(len(errors), 1)
        self.assertEqual(errors[0].line_number, 15)

    def test_ordereddates_error_carries_source_line(self):
        t1 = Transaction(
            date=datetime.date(2024, 2, 1),
            description="Later",
            postings=[Posting(account="a", amount=Amount(Decimal("1"), "£"))],
            source_line=10,
        )
        t2 = Transaction(
            date=datetime.date(2024, 1, 1),
            description="Earlier but placed after",
            postings=[Posting(account="a", amount=Amount(Decimal("1"), "£"))],
            source_line=20,
        )
        errors = check_ordereddates(_journal(t1, t2))
        self.assertEqual(len(errors), 1)
        self.assertEqual(errors[0].line_number, 20)

    def test_assertions_error_carries_source_line(self):
        text = (
            "2024-01-01 Opening\n"
            "    assets:bank  £100.00\n"
            "    equity\n"
            "\n"
            "2024-01-02 Check\n"
            "    assets:bank  £0 = £999.00\n"
            "    expenses  £0\n"
        )
        j = parse_string(text)
        errors = check_assertions(j)
        self.assertEqual(len(errors), 1)
        # line_number should be set (non-None)
        self.assertIsNotNone(errors[0].line_number)


class TestCheckTransactionAutobalanced(unittest.TestCase):
    """Tests for check_transaction_autobalanced (per-transaction validation)."""

    def _make_txn(self, postings):
        return Transaction(
            date=datetime.date(2024, 1, 1),
            description="Test",
            postings=postings,
        )

    def test_balanced_returns_empty(self):
        txn = self._make_txn([
            Posting(account="assets:bank", amount=Amount(Decimal("100"), "£")),
            Posting(account="expenses:food", amount=Amount(Decimal("-100"), "£")),
        ])
        self.assertEqual(check_transaction_autobalanced(txn), [])

    def test_unbalanced_returns_error(self):
        txn = self._make_txn([
            Posting(account="assets:bank", amount=Amount(Decimal("100"), "£")),
            Posting(account="expenses:food", amount=Amount(Decimal("-50"), "£")),
        ])
        errors = check_transaction_autobalanced(txn)
        self.assertEqual(len(errors), 1)
        self.assertEqual(errors[0].check_name, "autobalanced")
        self.assertIn("not balanced", errors[0].message)

    def test_elided_posting_returns_empty(self):
        txn = self._make_txn([
            Posting(account="assets:bank", amount=Amount(Decimal("100"), "£")),
            Posting(account="expenses:food"),  # elided — always considered balanced
        ])
        self.assertEqual(check_transaction_autobalanced(txn), [])


if __name__ == "__main__":
    unittest.main()
