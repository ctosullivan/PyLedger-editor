"""Tests for ledgerkit_editor.utils.query_match.

Uses real ledgerkit Query/Transaction/Posting objects (not stand-ins) so
these tests catch any drift between our locally-duplicated matching
semantics and the real ledgerkit.Query contract — see query_match.py's
module docstring on why this is duplicated rather than imported.
"""
import datetime

import pytest
from ledgerkit import Query
from ledgerkit.models import Posting, Transaction

from ledgerkit_editor.utils.query_match import build_transaction_predicate, matches_pattern


def _tx(date: str, description: str, *accounts: str) -> Transaction:
    return Transaction(
        date=datetime.date.fromisoformat(date),
        description=description,
        postings=[Posting(account=a) for a in accounts],
    )


class TestMatchesPattern:
    def test_plain_substring_case_insensitive(self) -> None:
        assert matches_pattern("food", "Expenses:Food:Groceries")

    def test_plain_substring_no_match(self) -> None:
        assert not matches_pattern("rent", "expenses:food")

    def test_regex_metacharacter_triggers_regex_mode(self) -> None:
        assert matches_pattern("^expenses", "expenses:food")
        assert not matches_pattern("^expenses", "assets:expenses")

    def test_regex_alternation(self) -> None:
        assert matches_pattern("food|rent", "expenses:rent")

    def test_invalid_regex_raises(self) -> None:
        with pytest.raises(Exception):  # re.error
            matches_pattern("expenses:(", "expenses:food")


class TestBuildTransactionPredicate:
    def test_no_filters_matches_everything(self) -> None:
        predicate = build_transaction_predicate(Query())
        assert predicate(_tx("2024-01-01", "Groceries", "expenses:food"))

    def test_date_from(self) -> None:
        predicate = build_transaction_predicate(
            Query(date_from=datetime.date(2024, 2, 1))
        )
        assert not predicate(_tx("2024-01-15", "X", "expenses:food"))
        assert predicate(_tx("2024-02-15", "X", "expenses:food"))

    def test_date_to(self) -> None:
        predicate = build_transaction_predicate(
            Query(date_to=datetime.date(2024, 1, 31))
        )
        assert predicate(_tx("2024-01-15", "X", "expenses:food"))
        assert not predicate(_tx("2024-02-01", "X", "expenses:food"))

    def test_date_range_inclusive_bounds(self) -> None:
        predicate = build_transaction_predicate(
            Query(date_from=datetime.date(2024, 1, 1), date_to=datetime.date(2024, 1, 31))
        )
        assert predicate(_tx("2024-01-01", "X", "expenses:food"))
        assert predicate(_tx("2024-01-31", "X", "expenses:food"))

    def test_payee_substring(self) -> None:
        predicate = build_transaction_predicate(Query(payee="grocer"))
        assert predicate(_tx("2024-01-01", "Weekly Groceries", "expenses:food"))
        assert not predicate(_tx("2024-01-01", "Rent", "expenses:rent"))

    def test_payee_regex(self) -> None:
        predicate = build_transaction_predicate(Query(payee="^Rent$"))
        assert predicate(_tx("2024-01-01", "Rent", "expenses:rent"))
        assert not predicate(_tx("2024-01-01", "Rent payment", "expenses:rent"))

    def test_account_matches_if_any_posting_matches(self) -> None:
        predicate = build_transaction_predicate(Query(account="expenses:food"))
        assert predicate(_tx("2024-01-01", "X", "assets:bank", "expenses:food"))
        assert not predicate(_tx("2024-01-01", "X", "assets:bank", "expenses:rent"))

    def test_account_regex_matches_subaccounts(self) -> None:
        predicate = build_transaction_predicate(Query(account="^expenses:food"))
        assert predicate(_tx("2024-01-01", "X", "expenses:food:organic"))
        assert not predicate(_tx("2024-01-01", "X", "expenses:household:food"))

    def test_not_account_excludes(self) -> None:
        predicate = build_transaction_predicate(Query(not_account="expenses:rent"))
        assert predicate(_tx("2024-01-01", "X", "expenses:food"))
        assert not predicate(_tx("2024-01-01", "X", "expenses:rent"))

    def test_depth_limits_posting_match(self) -> None:
        predicate = build_transaction_predicate(Query(account="expenses", depth=1))
        # depth=1 excludes any posting with more than 1 colon-segment
        assert predicate(_tx("2024-01-01", "X", "expenses"))
        assert not predicate(_tx("2024-01-01", "X", "expenses:food:organic"))

    def test_combined_date_payee_account(self) -> None:
        predicate = build_transaction_predicate(
            Query(
                date_from=datetime.date(2024, 1, 1),
                date_to=datetime.date(2024, 1, 31),
                payee="grocer",
                account="expenses:food",
            )
        )
        assert predicate(_tx("2024-01-15", "Groceries", "expenses:food"))
        assert not predicate(_tx("2024-02-15", "Groceries", "expenses:food"))  # date fails
        assert not predicate(_tx("2024-01-15", "Rent", "expenses:food"))  # payee fails
        assert not predicate(_tx("2024-01-15", "Groceries", "expenses:rent"))  # account fails

    def test_invalid_account_regex_raises_immediately(self) -> None:
        with pytest.raises(Exception):  # re.error, raised at build time
            build_transaction_predicate(Query(account="expenses:("))

    def test_invalid_payee_regex_raises_immediately(self) -> None:
        with pytest.raises(Exception):  # re.error
            build_transaction_predicate(Query(payee="Rent("))
