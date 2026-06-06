"""Tests against the comprehensive hledger fixture.

Exercises ledgerkit v0.2.0 features: ParseWarning, Transaction.date2,
Posting.cost_raw, new amount formats (scientific notation, space digit groups,
quoted commodities, sign-after-symbol), and new directives (Y, D, apply account).

The fixture file is loaded two ways:
- ledgerkit.load(MAIN_FIXTURE) — resolves the include directive so commodity
  declarations are active for EUR decimal-mark handling.
- parse_string_lenient on a per-test inline string — for isolated feature tests
  where the full file context is not needed.
"""

from __future__ import annotations

import datetime
from decimal import Decimal
from pathlib import Path

import pytest

import ledgerkit
from ledgerkit.parser import ParseError, ParseWarning, parse_string_lenient

FIXTURES = Path(__file__).parent / "fixtures"
MAIN_FIXTURE = FIXTURES / "comprehensive-hledger-test.journal"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _load_full() -> ledgerkit.Journal:
    """Load the full comprehensive fixture via ledgerkit.load (resolves include)."""
    return ledgerkit.load(MAIN_FIXTURE)


def _parse(text: str, default_year: int = 2024):
    """Convenience wrapper for parse_string_lenient with default_year."""
    return parse_string_lenient(text, default_year=default_year)


# ---------------------------------------------------------------------------
# 1. Fixture loads cleanly
# ---------------------------------------------------------------------------

class TestFixtureLoadsClean:
    def test_loads_without_exception(self) -> None:
        """ledgerkit.load() on the full fixture must not raise."""
        journal = _load_full()
        assert journal is not None

    def test_produces_transactions(self) -> None:
        journal = _load_full()
        assert len(journal.transactions) > 0

    def test_lenient_parse_no_hard_errors(self) -> None:
        """parse_string_lenient on the fixture text produces zero hard ParseErrors."""
        text = MAIN_FIXTURE.read_text(encoding="utf-8")
        _, errors = _parse(text)
        hard = [e for e in errors if not isinstance(e, ParseWarning)]
        assert hard == [], f"Unexpected hard errors: {hard}"

    def test_lenient_parse_transaction_count_matches_load(self) -> None:
        text = MAIN_FIXTURE.read_text(encoding="utf-8")
        j_lenient, _ = _parse(text)
        j_load = _load_full()
        assert len(j_lenient.transactions) == len(j_load.transactions)


# ---------------------------------------------------------------------------
# 2. ParseWarning vs ParseError
# ---------------------------------------------------------------------------

class TestParseWarningVsParseError:
    def test_parse_warning_is_subclass_of_parse_error(self) -> None:
        assert issubclass(ParseWarning, ParseError)

    def test_periodic_rule_produces_parse_warning(self) -> None:
        """~ periodic transaction rules produce ParseWarning, not ParseError."""
        text = "~ monthly budget goals\n    (expenses:rent)    $500\n"
        _, errors = _parse(text)
        assert any(isinstance(e, ParseWarning) for e in errors)

    def test_auto_posting_rule_produces_parse_warning(self) -> None:
        """= auto-posting rules produce ParseWarning, not ParseError."""
        text = "= expenses:food\n    (budget:food-spent)   *1.0\n"
        _, errors = _parse(text)
        assert any(isinstance(e, ParseWarning) for e in errors)

    def test_fixture_has_warnings_not_hard_errors(self) -> None:
        """The fixture's ~ and = blocks produce warnings; no hard errors."""
        text = MAIN_FIXTURE.read_text(encoding="utf-8")
        _, errors = _parse(text)
        warnings = [e for e in errors if isinstance(e, ParseWarning)]
        hard = [e for e in errors if not isinstance(e, ParseWarning)]
        assert len(warnings) >= 2
        assert hard == []

    def test_periodic_rule_warning_message(self) -> None:
        text = "~ monthly budget goals\n    (expenses:rent)    $500\n"
        _, errors = _parse(text)
        w = next(e for e in errors if isinstance(e, ParseWarning))
        msg = str(w).lower()
        assert "periodic" in msg or "~" in msg

    def test_auto_posting_rule_warning_message(self) -> None:
        text = "= expenses:food\n    (budget:food-spent)   *1.0\n"
        _, errors = _parse(text)
        w = next(e for e in errors if isinstance(e, ParseWarning))
        msg = str(w).lower()
        assert "auto" in msg or "=" in msg

    def test_parse_warning_carries_line_number(self) -> None:
        """ParseWarning must expose a line_number attribute."""
        text = "~ monthly budget goals\n    (expenses:rent)    $500\n"
        _, errors = _parse(text)
        w = next(e for e in errors if isinstance(e, ParseWarning))
        assert w.line_number is not None


# ---------------------------------------------------------------------------
# 3. Transaction.date2 — secondary date
# ---------------------------------------------------------------------------

class TestDate2Field:
    def test_secondary_date_parsed(self) -> None:
        """2024-02-20=2024-02-22 sets date=2024-02-20 and date2=2024-02-22."""
        text = (
            "2024-02-20=2024-02-22 * (CHK-204) deferred payment\n"
            "    expenses:fees              $3.00\n"
            "    assets:bank:checking\n"
        )
        j, errors = _parse(text)
        hard = [e for e in errors if not isinstance(e, ParseWarning)]
        assert hard == []
        txn = j.transactions[0]
        assert txn.date == datetime.date(2024, 2, 20)
        assert txn.date2 == datetime.date(2024, 2, 22)

    def test_no_secondary_date_is_none(self) -> None:
        """Transactions without =DATE2 syntax have date2=None."""
        text = (
            "2024-01-01 test\n"
            "    assets:bank:checking    $100\n"
            "    equity:opening-balances\n"
        )
        j, _ = _parse(text)
        assert j.transactions[0].date2 is None

    def test_date2_in_full_fixture(self) -> None:
        """The main fixture has exactly one transaction with date2 set."""
        journal = _load_full()
        txns_with_date2 = [t for t in journal.transactions if t.date2 is not None]
        assert len(txns_with_date2) == 1
        t = txns_with_date2[0]
        assert t.date == datetime.date(2024, 2, 20)
        assert t.date2 == datetime.date(2024, 2, 22)


# ---------------------------------------------------------------------------
# 4. Posting.cost_raw — cost annotations
# ---------------------------------------------------------------------------

class TestCostRawField:
    def test_unit_cost_annotation(self) -> None:
        """10 AAPL @ $180.00 → amount=10 AAPL, cost_raw='$180.00'."""
        text = (
            "2024-01-15 * buy shares\n"
            "    assets:investments    10 AAPL @ $180.00\n"
            "    assets:bank:checking\n"
        )
        j, errors = _parse(text)
        hard = [e for e in errors if not isinstance(e, ParseWarning)]
        assert hard == []
        p = j.transactions[0].postings[0]
        assert p.amount is not None
        assert p.amount.quantity == Decimal("10")
        assert p.amount.commodity == "AAPL"
        assert p.cost_raw == "$180.00"

    def test_total_cost_annotation(self) -> None:
        """5 AAPL @@ $920.00 → cost_raw='$920.00'."""
        text = (
            "2024-01-16 * buy shares at total cost\n"
            "    assets:investments    5 AAPL @@ $920.00\n"
            "    assets:bank:savings    $-920.00\n"
        )
        j, errors = _parse(text)
        hard = [e for e in errors if not isinstance(e, ParseWarning)]
        assert hard == []
        p = j.transactions[0].postings[0]
        assert p.cost_raw == "$920.00"

    def test_no_cost_annotation_is_none(self) -> None:
        """A plain posting with no @ has cost_raw=None."""
        text = (
            "2024-01-01 test\n"
            "    assets:bank    $100\n"
            "    equity:opening-balances\n"
        )
        j, _ = _parse(text)
        assert j.transactions[0].postings[0].cost_raw is None

    def test_cost_raw_in_full_fixture(self) -> None:
        """AAPL @ postings in the main fixture have cost_raw set."""
        journal = _load_full()
        aapl_cost_postings = [
            p
            for t in journal.transactions
            for p in t.postings
            if p.amount and p.amount.commodity == "AAPL" and p.cost_raw is not None
        ]
        assert len(aapl_cost_postings) >= 2


# ---------------------------------------------------------------------------
# 5. New amount formats
# ---------------------------------------------------------------------------

class TestAmountFormats:
    def test_scientific_notation(self) -> None:
        """1E3 EUR parses to quantity=1000, commodity='EUR'."""
        text = (
            "2024-03-03 * scientific notation\n"
            "    test:sci     1E3 EUR\n"
            "    test:sci2   -1E3 EUR\n"
        )
        j, errors = _parse(text)
        hard = [e for e in errors if not isinstance(e, ParseWarning)]
        assert hard == []
        p = j.transactions[0].postings[0]
        assert p.amount.quantity == Decimal("1E+3")
        assert p.amount.commodity == "EUR"

    def test_space_digit_group_separator(self) -> None:
        """1 000 000 JPY parses to quantity=1000000, commodity='JPY'."""
        text = (
            "2024-02-25 * large transfer\n"
            "    assets:bank:savings    1 000 000 JPY\n"
            "    equity:opening-balances\n"
        )
        j, errors = _parse(text)
        hard = [e for e in errors if not isinstance(e, ParseWarning)]
        assert hard == []
        p = j.transactions[0].postings[0]
        assert p.amount.quantity == Decimal("1000000")
        assert p.amount.commodity == "JPY"

    def test_quoted_commodity(self) -> None:
        """3 \"Chocolate Frogs\" parses to quantity=3, commodity='Chocolate Frogs'."""
        text = (
            '2024-02-02 * receive gift\n'
            '    assets:cash:pouch    3 "Chocolate Frogs"\n'
            '    revenues:gifts\n'
        )
        j, errors = _parse(text)
        hard = [e for e in errors if not isinstance(e, ParseWarning)]
        assert hard == []
        p = j.transactions[0].postings[0]
        assert p.amount.quantity == Decimal("3")
        assert p.amount.commodity == "Chocolate Frogs"

    def test_sign_after_prefix_symbol(self) -> None:
        """$-300 (sign after prefix symbol) parses to quantity=-300, commodity='$'."""
        text = (
            "2024-01-01 * test\n"
            "    assets:bank    $-300\n"
            "    equity:opening-balances\n"
        )
        j, errors = _parse(text)
        hard = [e for e in errors if not isinstance(e, ParseWarning)]
        assert hard == []
        p = j.transactions[0].postings[0]
        assert p.amount.quantity == Decimal("-300")
        assert p.amount.commodity == "$"

    def test_scientific_notation_in_full_fixture(self) -> None:
        """The full fixture's scientific notation amounts parse without errors."""
        journal = _load_full()
        sci_postings = [
            p
            for t in journal.transactions
            for p in t.postings
            if p.amount and "E" in str(p.amount.raw or "")
        ]
        assert len(sci_postings) >= 1

    def test_space_digit_groups_in_full_fixture(self) -> None:
        """The full fixture's 1 000 000 JPY entry parses to qty=1000000."""
        journal = _load_full()
        jpy_postings = [
            p
            for t in journal.transactions
            for p in t.postings
            if p.amount and p.amount.commodity == "JPY"
        ]
        assert len(jpy_postings) >= 1
        assert jpy_postings[0].amount.quantity == Decimal("1000000")


# ---------------------------------------------------------------------------
# 6. Directives: Y, D, apply account
# ---------------------------------------------------------------------------

class TestDirectives:
    def test_y_directive_yearless_date(self) -> None:
        """Y 2024 makes yearless dates like 03/15 resolve to 2024-03-15."""
        text = "Y 2024\n\n03/15 * yearless date\n    expenses:fees    $2.00\n    assets:wallet\n"
        j, errors = _parse(text, default_year=None)
        hard = [e for e in errors if not isinstance(e, ParseWarning)]
        assert hard == []
        assert j.transactions[0].date == datetime.date(2024, 3, 15)

    def test_d_directive_default_commodity(self) -> None:
        """D $1,000.00 makes no-symbol amounts use $ commodity."""
        text = (
            "D $1,000.00\n\n"
            "2024-01-01 * test\n"
            "    expenses:fees    2.00\n"
            "    assets:wallet\n"
        )
        j, errors = _parse(text)
        hard = [e for e in errors if not isinstance(e, ParseWarning)]
        assert hard == []
        p = j.transactions[0].postings[0]
        assert p.amount is not None
        assert p.amount.commodity == "$"
        assert p.amount.quantity == Decimal("2.00")

    def test_apply_account_prefixes_accounts(self) -> None:
        """apply account demo:apply prepends the prefix to all postings in the block."""
        text = (
            "apply account demo:apply\n"
            "2024-04-01 * demo\n"
            "    bank      $50\n"
            "    income   $-50\n"
            "end apply account\n"
        )
        j, errors = _parse(text)
        hard = [e for e in errors if not isinstance(e, ParseWarning)]
        assert hard == []
        accounts = {p.account for p in j.transactions[0].postings}
        assert "demo:apply:bank" in accounts
        assert "demo:apply:income" in accounts

    def test_apply_account_in_full_fixture(self) -> None:
        """The main fixture uses apply account; resulting accounts are prefixed."""
        journal = _load_full()
        all_accounts = {p.account for t in journal.transactions for p in t.postings}
        assert "demo:apply:bank" in all_accounts or "demo:apply:income" in all_accounts

    def test_yearless_date_in_full_fixture(self) -> None:
        """The main fixture has a yearless date entry (03/15) that resolves to 2024-03-15."""
        journal = _load_full()
        dates = [t.date for t in journal.transactions]
        assert datetime.date(2024, 3, 15) in dates


# ---------------------------------------------------------------------------
# 7. Lot annotations stripped from amount
# ---------------------------------------------------------------------------

class TestLotAnnotations:
    def test_unit_cost_lot_annotation_stripped(self) -> None:
        """3 AAPL {$182.00} [2024-01-18] (lot-A) → amount=3 AAPL, no annotation in commodity."""
        text = (
            "2024-01-18 * reclassify\n"
            "    assets:lots    3 AAPL {$182.00} [2024-01-18] (lot-A)\n"
            "    assets:lot2   -3 AAPL\n"
        )
        j, errors = _parse(text)
        hard = [e for e in errors if not isinstance(e, ParseWarning)]
        assert hard == []
        p = j.transactions[0].postings[0]
        assert p.amount.quantity == Decimal("3")
        assert p.amount.commodity == "AAPL"
        assert "{" not in p.amount.commodity
        assert "$182" not in p.amount.commodity

    def test_total_cost_basis_annotation_stripped(self) -> None:
        """2 AAPL {{$370.00}} [2024-01-19] (lot-B) → amount=2 AAPL."""
        text = (
            "2024-01-19 * second lot\n"
            "    assets:lots    2 AAPL {{$370.00}} [2024-01-19] (lot-B)\n"
            "    assets:lot2   -2 AAPL\n"
        )
        j, errors = _parse(text)
        hard = [e for e in errors if not isinstance(e, ParseWarning)]
        assert hard == []
        p = j.transactions[0].postings[0]
        assert p.amount.quantity == Decimal("2")
        assert p.amount.commodity == "AAPL"

    def test_lot_annotation_cost_raw_is_none(self) -> None:
        """Lot annotations ({}) are stripped but do NOT populate cost_raw."""
        text = (
            "2024-01-18 * reclassify\n"
            "    assets:lots    3 AAPL {$182.00} [2024-01-18] (lot-A)\n"
            "    assets:lot2   -3 AAPL\n"
        )
        j, _ = _parse(text)
        p = j.transactions[0].postings[0]
        assert p.cost_raw is None


# ---------------------------------------------------------------------------
# 8. Balance assertions do not break parsing
# ---------------------------------------------------------------------------

class TestBalanceAssertions:
    def test_basic_balance_assertion(self) -> None:
        """$0 = $624.50 assertion: transaction is present in the journal."""
        text = (
            "2024-01-20 * reconcile\n"
            "    assets:bank:checking    $0 = $624.50\n"
        )
        j, errors = _parse(text)
        hard = [e for e in errors if not isinstance(e, ParseWarning)]
        assert hard == []
        assert any(t.date == datetime.date(2024, 1, 20) for t in j.transactions)

    def test_sole_commodity_assertion(self) -> None:
        """== sole-commodity assertion parses without hard error."""
        text = (
            "2024-03-01 * sole assertion\n"
            "    test:usd    $-1  == $-1\n"
            "    test:both\n"
        )
        j, errors = _parse(text)
        hard = [e for e in errors if not isinstance(e, ParseWarning)]
        assert hard == []
        assert len(j.transactions) == 1

    def test_subaccount_inclusive_assertion(self) -> None:
        """==* subaccount-inclusive assertion parses without hard error."""
        text = (
            "2024-03-02 * subaccount inclusive\n"
            "    equity:opening-balances\n"
            "    demo:assets:checking    $10\n"
            "    demo:assets:savings     $10\n"
            "    demo:assets             $0 ==* $20\n"
        )
        j, errors = _parse(text)
        hard = [e for e in errors if not isinstance(e, ParseWarning)]
        assert hard == []
        assert len(j.transactions) == 1

    def test_balance_assertions_in_full_fixture(self) -> None:
        """The full fixture contains balance assertions; load must still succeed."""
        journal = _load_full()
        assert len(journal.transactions) > 0
