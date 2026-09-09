"""Tests for ledgerkit_editor.utils.journal_index (pure, no Textual)."""

from ledgerkit_editor.utils.journal_index import JournalIndex, build_journal_index

JOURNAL = (
    "account expenses:food\n"
    "payee Landlord\n"
    "\n"
    "2024-01-10 * Opening balances\n"
    "    assets:bank:checking    £1000.00\n"
    "    equity:opening-balances\n"
    "\n"
    "2024-01-15 Groceries\n"
    "    expenses:food:organic    £42.50\n"
    "    assets:bank:checking\n"
    "\n"
    "2024-02-01 Groceries\n"
    "    expenses:food    £38.00\n"
    "    assets:bank:checking\n"
)


class TestBuildJournalIndex:
    def test_declared_account_included(self) -> None:
        idx = build_journal_index(JOURNAL)
        assert "expenses:food" in idx.accounts

    def test_declared_payee_included(self) -> None:
        idx = build_journal_index(JOURNAL)
        assert "Landlord" in idx.payees

    def test_posting_accounts_included(self) -> None:
        idx = build_journal_index(JOURNAL)
        assert "assets:bank:checking" in idx.accounts
        assert "equity:opening-balances" in idx.accounts
        assert "expenses:food:organic" in idx.accounts

    def test_transaction_descriptions_included(self) -> None:
        idx = build_journal_index(JOURNAL)
        assert "Groceries" in idx.payees
        assert "Opening balances" in idx.payees

    def test_deduplicated(self) -> None:
        idx = build_journal_index(JOURNAL)
        assert idx.accounts.count("expenses:food") == 1
        assert idx.payees.count("Groceries") == 1

    def test_sorted(self) -> None:
        idx = build_journal_index(JOURNAL)
        assert idx.accounts == sorted(idx.accounts)
        assert idx.payees == sorted(idx.payees)

    def test_empty_text_produces_empty_index(self) -> None:
        idx = build_journal_index("")
        assert idx.accounts == []
        assert idx.payees == []

    def test_unparseable_text_does_not_raise(self) -> None:
        idx = build_journal_index("this is not a journal at all\n@#$%^&")
        assert isinstance(idx, JournalIndex)


class TestMatchingAccounts:
    def test_prefix_match_case_insensitive(self) -> None:
        # Equal-length matches tie-break alphabetically (case-insensitive):
        # "expenses:food" < "expenses:rent".
        idx = JournalIndex(accounts=["Expenses:Food", "expenses:rent"])
        assert idx.matching_accounts("exp") == ["Expenses:Food", "expenses:rent"]

    def test_no_match(self) -> None:
        idx = JournalIndex(accounts=["expenses:food"])
        assert idx.matching_accounts("assets") == []

    def test_empty_prefix_matches_all_up_to_limit(self) -> None:
        idx = JournalIndex(accounts=["a", "b", "c"])
        assert idx.matching_accounts("", limit=2) == ["a", "b"]

    def test_shortest_match_first(self) -> None:
        idx = JournalIndex(
            accounts=["expenses:food:organic", "expenses:food", "expenses:food:takeaway"]
        )
        result = idx.matching_accounts("expenses:food")
        assert result[0] == "expenses:food"

    def test_limit_respected(self) -> None:
        idx = JournalIndex(accounts=[f"expenses:{i}" for i in range(20)])
        assert len(idx.matching_accounts("expenses", limit=5)) == 5


class TestMatchingPayees:
    def test_prefix_match(self) -> None:
        idx = JournalIndex(payees=["Groceries", "Gas Station", "Rent"])
        result = idx.matching_payees("g")
        assert set(result) == {"Groceries", "Gas Station"}

    def test_no_match_returns_empty(self) -> None:
        idx = JournalIndex(payees=["Groceries"])
        assert idx.matching_payees("zzz") == []
