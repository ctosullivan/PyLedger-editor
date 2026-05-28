"""Tests for PyLedger.parser — directive parsing."""

import datetime
import unittest
from decimal import Decimal

from PyLedger.models import Journal
from PyLedger.parser import ParseError, parse_string


# ---------------------------------------------------------------------------
# account directive
# ---------------------------------------------------------------------------

class TestAccountDirective(unittest.TestCase):
    def test_account_directive_stored(self):
        j = parse_string("account assets:bank\n")
        self.assertEqual(j.declared_accounts, ["assets:bank"])

    def test_multiple_account_directives(self):
        j = parse_string("account assets:bank\naccount income:salary\n")
        self.assertEqual(j.declared_accounts, ["assets:bank", "income:salary"])

    def test_account_semicolon_comment_stripped(self):
        j = parse_string("account assets:bank  ; checking account\n")
        self.assertEqual(j.declared_accounts, ["assets:bank"])

    def test_account_hash_comment_stripped(self):
        j = parse_string("account assets:bank  # checking account\n")
        self.assertEqual(j.declared_accounts, ["assets:bank"])

    def test_account_single_space_semicolon_in_name(self):
        # Single space before ';' → ';' is part of the name (no separator)
        j = parse_string("account a:b ; note\n")
        self.assertEqual(j.declared_accounts, ["a:b ; note"])

    def test_account_subdirectives_skipped(self):
        text = "account assets:bank\n    format something\n    ; a note\n"
        j = parse_string(text)
        # Only the account name is stored; subdirectives do not create extra entries
        self.assertEqual(j.declared_accounts, ["assets:bank"])

    def test_account_directive_inside_block_comment_ignored(self):
        text = "comment\naccount assets:bank\nend comment\n"
        j = parse_string(text)
        self.assertEqual(j.declared_accounts, [])

    def test_account_directive_does_not_affect_transactions(self):
        text = (
            "account assets:bank\n"
            "account income:salary\n"
            "\n"
            "2024-01-01 Pay\n"
            "    assets:bank  £10.00\n"
            "    income:salary  -£10.00\n"
        )
        j = parse_string(text)
        self.assertEqual(len(j.transactions), 1)
        self.assertEqual(j.declared_accounts, ["assets:bank", "income:salary"])


# ---------------------------------------------------------------------------
# commodity directive
# ---------------------------------------------------------------------------

class TestCommodityDirective(unittest.TestCase):
    def test_prefix_symbol(self):
        j = parse_string("commodity £1,000.00\n")
        self.assertEqual(j.declared_commodities, ["£"])

    def test_prefix_dollar(self):
        j = parse_string("commodity $1,000.00\n")
        self.assertEqual(j.declared_commodities, ["$"])

    def test_suffix_symbol(self):
        j = parse_string("commodity 1,000.00 EUR\n")
        self.assertEqual(j.declared_commodities, ["EUR"])

    def test_suffix_symbol_USD(self):
        j = parse_string("commodity 1.00 USD\n")
        self.assertEqual(j.declared_commodities, ["USD"])

    def test_bare_symbol_sigil(self):
        j = parse_string("commodity $\n")
        self.assertEqual(j.declared_commodities, ["$"])

    def test_bare_symbol_word(self):
        j = parse_string("commodity INR\n")
        self.assertEqual(j.declared_commodities, ["INR"])

    def test_quoted_symbol(self):
        j = parse_string('commodity "AAPL 2023"\n')
        self.assertEqual(j.declared_commodities, ["AAPL 2023"])

    def test_quoted_empty_symbol(self):
        j = parse_string('commodity ""\n')
        self.assertEqual(j.declared_commodities, [""])

    def test_no_symbol_numeric_only(self):
        # e.g. "commodity 1000." declares the no-symbol commodity
        j = parse_string("commodity 1000.\n")
        self.assertEqual(j.declared_commodities, [""])

    def test_commodity_semicolon_comment_stripped(self):
        j = parse_string("commodity $  ; US dollar\n")
        self.assertEqual(j.declared_commodities, ["$"])

    def test_commodity_hash_comment_stripped(self):
        j = parse_string("commodity $  # US dollar\n")
        self.assertEqual(j.declared_commodities, ["$"])

    def test_format_subdirective_skipped(self):
        text = "commodity INR\n    format INR 1,00,00,000.00\n"
        j = parse_string(text)
        self.assertEqual(j.declared_commodities, ["INR"])

    def test_commodity_inside_block_comment_ignored(self):
        text = "comment\ncommodity £\nend comment\n"
        j = parse_string(text)
        self.assertEqual(j.declared_commodities, [])


# ---------------------------------------------------------------------------
# payee directive
# ---------------------------------------------------------------------------

class TestPayeeDirective(unittest.TestCase):
    def test_payee_stored(self):
        j = parse_string("payee Whole Foods\n")
        self.assertEqual(j.declared_payees, ["Whole Foods"])

    def test_payee_semicolon_comment_stripped(self):
        j = parse_string("payee Whole Foods  ; grocery store\n")
        self.assertEqual(j.declared_payees, ["Whole Foods"])

    def test_payee_hash_comment_stripped(self):
        j = parse_string("payee Whole Foods  # grocery store\n")
        self.assertEqual(j.declared_payees, ["Whole Foods"])

    def test_payee_single_space_semicolon_kept(self):
        # Single space before ';' → ';' is NOT the 2-space separator
        j = parse_string("payee Smith & Jones ; law firm\n")
        self.assertEqual(j.declared_payees, ["Smith & Jones ; law firm"])

    def test_payee_quoted_empty(self):
        j = parse_string('payee ""\n')
        self.assertEqual(j.declared_payees, [""])

    def test_payee_quoted_name(self):
        j = parse_string('payee "Smith & Co"\n')
        self.assertEqual(j.declared_payees, ["Smith & Co"])

    def test_payee_inside_block_comment_ignored(self):
        text = "comment\npayee Supermarket\nend comment\n"
        j = parse_string(text)
        self.assertEqual(j.declared_payees, [])

    def test_multiple_payees(self):
        j = parse_string("payee Shop A\npayee Shop B\n")
        self.assertEqual(j.declared_payees, ["Shop A", "Shop B"])


# ---------------------------------------------------------------------------
# tag directive
# ---------------------------------------------------------------------------

class TestTagDirective(unittest.TestCase):
    def test_tag_stored(self):
        j = parse_string("tag item-id\n")
        self.assertEqual(j.declared_tags, ["item-id"])

    def test_tag_semicolon_comment_stripped(self):
        j = parse_string("tag item-id  ; identifies purchase items\n")
        self.assertEqual(j.declared_tags, ["item-id"])

    def test_tag_hash_comment_stripped(self):
        j = parse_string("tag item-id  # identifies purchase items\n")
        self.assertEqual(j.declared_tags, ["item-id"])

    def test_tag_single_space_semicolon_kept(self):
        # Single space before ';' is NOT the 2-space separator
        j = parse_string("tag weird;tag\n")
        self.assertEqual(j.declared_tags, ["weird;tag"])

    def test_tag_subdirective_skipped(self):
        text = "tag item-id\n    some subdirective\n"
        j = parse_string(text)
        self.assertEqual(j.declared_tags, ["item-id"])

    def test_multiple_tags(self):
        j = parse_string("tag receipt\ntag project\n")
        self.assertEqual(j.declared_tags, ["receipt", "project"])

    def test_tag_inside_block_comment_ignored(self):
        text = "comment\ntag should-be-ignored\nend comment\n"
        j = parse_string(text)
        self.assertEqual(j.declared_tags, [])


# ---------------------------------------------------------------------------
# decimal-mark directive
# ---------------------------------------------------------------------------

class TestDecimalMarkDirective(unittest.TestCase):
    def _simple_journal(self, amount_line: str) -> "Journal":
        text = (
            f"2024-01-01 Test\n"
            f"    assets  {amount_line}\n"
            f"    income  \n"
        )
        return parse_string(text)

    def test_default_period_decimal(self):
        j = parse_string("2024-01-01 T\n    a  £1,234.56\n    b\n")
        amt = j.transactions[0].postings[0].amount
        assert amt is not None
        self.assertEqual(amt.quantity, Decimal("1234.56"))

    def test_explicit_period_decimal(self):
        text = "decimal-mark .\n2024-01-01 T\n    a  £1,234.56\n    b\n"
        j = parse_string(text)
        amt = j.transactions[0].postings[0].amount
        assert amt is not None
        self.assertEqual(amt.quantity, Decimal("1234.56"))

    def test_comma_decimal_basic(self):
        text = "decimal-mark ,\n2024-01-01 T\n    a  £100,50\n    b\n"
        j = parse_string(text)
        amt = j.transactions[0].postings[0].amount
        assert amt is not None
        self.assertEqual(amt.quantity, Decimal("100.50"))

    def test_comma_decimal_with_thousands(self):
        text = "decimal-mark ,\n2024-01-01 T\n    a  £1.234,56\n    b\n"
        j = parse_string(text)
        amt = j.transactions[0].postings[0].amount
        assert amt is not None
        self.assertEqual(amt.quantity, Decimal("1234.56"))

    def test_comma_decimal_suffix_commodity(self):
        text = "decimal-mark ,\n2024-01-01 T\n    a  1.234,56 EUR\n    b\n"
        j = parse_string(text)
        p = j.transactions[0].postings[0]
        amt = p.amount
        assert amt is not None
        self.assertEqual(amt.quantity, Decimal("1234.56"))
        self.assertEqual(amt.commodity, "EUR")

    def test_comma_decimal_negative(self):
        text = "decimal-mark ,\n2024-01-01 T\n    a  £1,50\n    b  -£1,50\n"
        j = parse_string(text)
        amt = j.transactions[0].postings[1].amount
        assert amt is not None
        self.assertEqual(amt.quantity, Decimal("-1.50"))

    def test_decimal_mark_applies_from_directive_forward(self):
        # Postings before the directive use period-decimal, after use comma-decimal
        text = (
            "2024-01-01 Before\n"
            "    a  £1,234.56\n"
            "    b\n"
            "\n"
            "decimal-mark ,\n"
            "\n"
            "2024-01-02 After\n"
            "    a  £1.234,56\n"
            "    b\n"
        )
        j = parse_string(text)
        amt0 = j.transactions[0].postings[0].amount
        amt1 = j.transactions[1].postings[0].amount
        assert amt0 is not None and amt1 is not None
        self.assertEqual(amt0.quantity, Decimal("1234.56"))
        self.assertEqual(amt1.quantity, Decimal("1234.56"))

    def test_decimal_mark_semicolon_comment_stripped(self):
        text = "decimal-mark .  ; period decimal\n2024-01-01 T\n    a  $1.50\n    b\n"
        j = parse_string(text)
        amt = j.transactions[0].postings[0].amount
        assert amt is not None
        self.assertEqual(amt.quantity, Decimal("1.50"))

    def test_decimal_mark_hash_comment_stripped(self):
        text = "decimal-mark .  # period decimal\n2024-01-01 T\n    a  $1.50\n    b\n"
        j = parse_string(text)
        amt = j.transactions[0].postings[0].amount
        assert amt is not None
        self.assertEqual(amt.quantity, Decimal("1.50"))

    def test_invalid_decimal_mark_raises(self):
        from PyLedger.parser import ParseError
        with self.assertRaises(ParseError):
            parse_string("decimal-mark ;\n")

    def test_decimal_mark_inside_block_comment_ignored(self):
        # directive inside block comment must not change decimal_mark state
        text = (
            "comment\n"
            "decimal-mark ,\n"
            "end comment\n"
            "2024-01-01 T\n"
            "    a  £1,234.56\n"  # should still parse as period-decimal (default)
            "    b\n"
        )
        j = parse_string(text)
        amt = j.transactions[0].postings[0].amount
        assert amt is not None
        self.assertEqual(amt.quantity, Decimal("1234.56"))


# ---------------------------------------------------------------------------
# P directive
# ---------------------------------------------------------------------------

class TestPDirective(unittest.TestCase):
    """Tests for P (market price) directive parsing."""

    def test_basic_p_directive(self):
        text = "P 2024-03-01 AAPL $179.00\n"
        j = parse_string(text)
        self.assertEqual(len(j.prices), 1)
        p = j.prices[0]
        self.assertEqual(p.date, datetime.date(2024, 3, 1))
        self.assertEqual(p.commodity, "AAPL")
        self.assertEqual(p.price.quantity, Decimal("179.00"))
        self.assertEqual(p.price.commodity, "$")

    def test_multiple_p_directives(self):
        text = "P 2009-01-01 EUR $1.35\nP 2010-01-01 EUR $1.40\n"
        j = parse_string(text)
        self.assertEqual(len(j.prices), 2)
        self.assertEqual(j.prices[0].price.quantity, Decimal("1.35"))
        self.assertEqual(j.prices[1].price.quantity, Decimal("1.40"))
        self.assertEqual(j.prices[0].date.year, 2009)
        self.assertEqual(j.prices[1].date.year, 2010)

    def test_p_directive_prefix_symbol(self):
        text = "P 2024-01-01 EUR $1.35\n"
        j = parse_string(text)
        self.assertEqual(j.prices[0].price.commodity, "$")
        self.assertEqual(j.prices[0].price.quantity, Decimal("1.35"))

    def test_p_directive_suffix_symbol(self):
        text = "P 2024-01-01 EUR 1.35 USD\n"
        j = parse_string(text)
        self.assertEqual(j.prices[0].price.commodity, "USD")
        self.assertEqual(j.prices[0].price.quantity, Decimal("1.35"))

    def test_p_directive_semicolon_comment_stripped(self):
        text = "P 2024-01-01 € $1.35  ; source: ECB\n"
        j = parse_string(text)
        self.assertEqual(len(j.prices), 1)
        self.assertEqual(j.prices[0].price.quantity, Decimal("1.35"))
        self.assertEqual(j.prices[0].price.commodity, "$")

    def test_p_directive_hash_comment_stripped(self):
        text = "P 2024-01-01 € $1.35  # source: ECB\n"
        j = parse_string(text)
        self.assertEqual(len(j.prices), 1)
        self.assertEqual(j.prices[0].price.quantity, Decimal("1.35"))
        self.assertEqual(j.prices[0].price.commodity, "$")

    def test_p_directive_inside_block_comment_ignored(self):
        text = "comment\nP 2024-01-01 AAPL $100.00\nend comment\n"
        j = parse_string(text)
        self.assertEqual(j.prices, [])

    def test_p_directive_invalid_date_raises(self):
        text = "P 2024-99-01 EUR $1.00\n"
        with self.assertRaises(ParseError):
            parse_string(text)

    def test_p_directive_invalid_amount_raises(self):
        text = "P 2024-01-01 AAPL notanumber\n"
        with self.assertRaises(ParseError):
            parse_string(text)

    def test_p_directive_does_not_affect_transactions(self):
        text = (
            "P 2024-01-01 EUR $1.35\n"
            "\n"
            "2024-01-10 Groceries\n"
            "    expenses:food  $50.00\n"
            "    assets:bank\n"
        )
        j = parse_string(text)
        self.assertEqual(len(j.prices), 1)
        self.assertEqual(len(j.transactions), 1)
        self.assertEqual(j.prices[0].commodity, "EUR")
        self.assertEqual(j.transactions[0].description, "Groceries")


# ---------------------------------------------------------------------------
# alias directive
# ---------------------------------------------------------------------------

class TestAliasDirective(unittest.TestCase):
    def _txn(self, text: str) -> "Journal":
        return parse_string(text)

    def test_basic_alias_exact_match(self):
        text = "alias checking = assets:bank\n\n2024-01-01 T\n    checking  $10\n    income\n"
        j = self._txn(text)
        self.assertEqual(j.transactions[0].postings[0].account, "assets:bank")

    def test_basic_alias_subaccount(self):
        text = "alias checking = assets:bank\n\n2024-01-01 T\n    checking:savings  $10\n    income\n"
        j = self._txn(text)
        self.assertEqual(j.transactions[0].postings[0].account, "assets:bank:savings")

    def test_basic_alias_no_match_non_prefix(self):
        text = "alias checking = assets:bank\n\n2024-01-01 T\n    other:checking  $10\n    income\n"
        j = self._txn(text)
        self.assertEqual(j.transactions[0].postings[0].account, "other:checking")

    def test_basic_alias_no_match_unrelated(self):
        text = "alias expenses = costs\n\n2024-01-01 T\n    income  $10\n    assets\n"
        j = self._txn(text)
        self.assertEqual(j.transactions[0].postings[0].account, "income")

    def test_regex_alias_basic_substitution(self):
        text = "alias /expenses/ = costs\n\n2024-01-01 T\n    expenses:food  $10\n    income\n"
        j = self._txn(text)
        self.assertEqual(j.transactions[0].postings[0].account, "costs:food")

    def test_regex_alias_capture_groups(self):
        text = (
            r"alias /^(.+):bank:([^:]+)/ = \1:\2"
            "\n\n2024-01-01 T\n    assets:bank:checking  $10\n    income\n"
        )
        j = self._txn(text)
        self.assertEqual(j.transactions[0].postings[0].account, "assets:checking")

    def test_regex_alias_case_insensitive(self):
        text = "alias /EXPENSES/ = costs\n\n2024-01-01 T\n    expenses:food  $10\n    income\n"
        j = self._txn(text)
        self.assertEqual(j.transactions[0].postings[0].account, "costs:food")

    def test_multiple_aliases_lifo_order(self):
        # LIFO: most-recently-defined alias (costs→budget) is applied FIRST.
        # "expenses" does not match costs→budget, then matches expenses→costs.
        # Result: "expenses" → "costs" (not "budget").
        text = (
            "alias expenses = costs\n"
            "alias costs = budget\n"
            "\n"
            "2024-01-01 T\n"
            "    expenses  $10\n"
            "    income\n"
        )
        j = self._txn(text)
        self.assertEqual(j.transactions[0].postings[0].account, "costs")

    def test_end_aliases_clears_rules(self):
        text = (
            "alias a = A\n"
            "\n"
            "2024-01-01 First\n"
            "    a  $1\n"
            "    b\n"
            "\n"
            "end aliases\n"
            "\n"
            "2024-01-02 Second\n"
            "    a  $1\n"
            "    b\n"
        )
        j = self._txn(text)
        self.assertEqual(j.transactions[0].postings[0].account, "A")
        self.assertEqual(j.transactions[1].postings[0].account, "a")

    def test_end_aliases_without_prior_aliases(self):
        text = "end aliases\n\n2024-01-01 T\n    a  $1\n    b\n"
        j = self._txn(text)
        self.assertEqual(j.transactions[0].postings[0].account, "a")

    def test_alias_applies_to_account_directive(self):
        text = "alias old = new\naccount old:sub\n"
        j = self._txn(text)
        self.assertIn("new:sub", j.declared_accounts)
        self.assertNotIn("old:sub", j.declared_accounts)

    def test_alias_inside_block_comment_ignored(self):
        text = (
            "comment\n"
            "alias a = A\n"
            "end comment\n"
            "\n"
            "2024-01-01 T\n"
            "    a  $1\n"
            "    b\n"
        )
        j = self._txn(text)
        self.assertEqual(j.transactions[0].postings[0].account, "a")

    def test_alias_semicolon_comment_stripped(self):
        text = "alias old = new  ; this is a comment\n\n2024-01-01 T\n    old  $1\n    b\n"
        j = self._txn(text)
        self.assertEqual(j.transactions[0].postings[0].account, "new")

    def test_alias_hash_comment_stripped(self):
        text = "alias old = new  # this is a comment\n\n2024-01-01 T\n    old  $1\n    b\n"
        j = self._txn(text)
        self.assertEqual(j.transactions[0].postings[0].account, "new")

    def test_end_aliases_with_comment(self):
        text = (
            "alias a = A\n"
            "\n"
            "2024-01-01 Before\n"
            "    a  $1\n"
            "    b\n"
            "\n"
            "end aliases  ; clear all\n"
            "\n"
            "2024-01-02 After\n"
            "    a  $1\n"
            "    b\n"
        )
        j = self._txn(text)
        self.assertEqual(j.transactions[0].postings[0].account, "A")
        self.assertEqual(j.transactions[1].postings[0].account, "a")

    def test_transactions_before_alias_unaffected(self):
        text = (
            "2024-01-01 Before\n"
            "    a  $1\n"
            "    b\n"
            "\n"
            "alias a = A\n"
            "\n"
            "2024-01-02 After\n"
            "    a  $1\n"
            "    b\n"
        )
        j = self._txn(text)
        self.assertEqual(j.transactions[0].postings[0].account, "a")
        self.assertEqual(j.transactions[1].postings[0].account, "A")

    def test_invalid_regex_alias_raises(self):
        with self.assertRaises(ParseError):
            parse_string("alias /[invalid/ = x\n")


if __name__ == "__main__":
    unittest.main()
