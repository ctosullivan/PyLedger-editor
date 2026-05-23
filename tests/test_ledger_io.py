"""Tests for ledger_editor.utils.ledger_io."""

from pathlib import Path

import pytest

from ledger_editor.utils.ledger_io import align_posting_amounts, load_journal

FIXTURES = Path(__file__).parent / "fixtures"


class TestLoadJournal:
    """Tests for load_journal()."""

    def test_loads_sample_journal(self) -> None:
        journal = load_journal(FIXTURES / "sample.journal")
        assert len(journal.transactions) == 2

    def test_first_transaction_cleared(self) -> None:
        journal = load_journal(FIXTURES / "sample.journal")
        txn = journal.transactions[0]
        assert txn.cleared is True
        assert txn.pending is False

    def test_second_transaction_uncleared(self) -> None:
        journal = load_journal(FIXTURES / "sample.journal")
        txn = journal.transactions[1]
        assert txn.cleared is False
        assert txn.pending is False

    def test_missing_file_raises(self, tmp_path: Path) -> None:
        with pytest.raises(FileNotFoundError):
            load_journal(tmp_path / "nonexistent.journal")


class TestAlignPostingAmounts:
    """Tests for align_posting_amounts()."""

    def _amount_end_col(self, line: str) -> int:
        """Return the 1-indexed column of the last character of the amount, or -1.

        Requires 2+ space separator so balance-completing postings (no amount) and
        account names containing single spaces are handled correctly.
        """
        import re
        m = re.match(r"^(    )(.+?)( {2,})(\S.*)$", line)
        if not m:
            return -1
        return len(m.group(1)) + len(m.group(2)) + len(m.group(3)) + len(m.group(4))

    def test_amount_ends_at_column_52(self) -> None:
        text = "2024-01-01 Groceries\n    expenses:food  50.00 EUR\n    assets:bank  -50.00 EUR\n"
        out = align_posting_amounts(text)
        for line in out.splitlines():
            col = self._amount_end_col(line)
            if col != -1:
                assert col == 52, f"Expected amount end at col 52, got {col}: {line!r}"

    def test_multi_transaction_amounts_all_end_at_52(self) -> None:
        text = (
            "2024-01-01 Groceries\n"
            "    expenses:food  £45.00\n"
            "    assets:bank  £-45.00\n"
            "\n"
            "2024-01-02 Big purchase\n"
            "    expenses:electronics  £1,234.00\n"
            "    assets:bank  £-1,234.00\n"
        )
        out = align_posting_amounts(text)
        for line in out.splitlines():
            col = self._amount_end_col(line)
            if col != -1:
                assert col == 52, f"Expected amount end at col 52, got {col}: {line!r}"

    def test_account_name_with_spaces_aligned(self) -> None:
        text = (
            "2024-01-01 Opening\n"
            "    Assets:Bank:AIB Cormac  537.10 EUR\n"
            "    Assets:Bank:ANZ Offset  $289.60\n"
            "    equity:opening/closing balances\n"
        )
        out = align_posting_amounts(text)
        for line in out.splitlines():
            col = self._amount_end_col(line)
            if col != -1:
                assert col == 52, f"Expected amount end at col 52, got {col}: {line!r}"
        assert "    equity:opening/closing balances" in out

    def test_long_account_falls_back_to_two_spaces(self) -> None:
        long_account = "expenses:" + "x" * 50
        text = f"2024-01-01 Test\n    {long_account}  100.00\n"
        out = align_posting_amounts(text)
        import re
        for line in out.splitlines():
            m = re.match(r"^(    )(\S+)( +)(\S.*)$", line)
            if m:
                assert len(m.group(3)) == 2

    def test_comment_lines_unchanged(self) -> None:
        text = "2024-01-01 Test\n    expenses:food  50.00 EUR\n    ; a posting note\n"
        out = align_posting_amounts(text)
        assert "    ; a posting note" in out

    def test_balance_completing_posting_unchanged(self) -> None:
        text = "2024-01-01 Test\n    expenses:food  50.00 EUR\n    assets:bank\n"
        out = align_posting_amounts(text)
        assert "    assets:bank\n" in out

    def test_trailing_newline_preserved(self) -> None:
        text = "2024-01-01 Test\n    expenses:food  50.00 EUR\n"
        assert align_posting_amounts(text).endswith("\n")

    def test_no_trailing_newline_preserved(self) -> None:
        text = "2024-01-01 Test\n    expenses:food  50.00 EUR"
        assert not align_posting_amounts(text).endswith("\n")

    def test_custom_column_parameter(self) -> None:
        text = "2024-01-01 Test\n    expenses:food  50.00 EUR\n"
        out = align_posting_amounts(text, column=60)
        for line in out.splitlines():
            col = self._amount_end_col(line)
            if col != -1:
                assert col == 60

    def test_header_lines_unchanged(self) -> None:
        text = "2024-01-01 Groceries\n    expenses:food  50.00 EUR\n"
        out = align_posting_amounts(text)
        assert out.splitlines()[0] == "2024-01-01 Groceries"

    def test_prefix_currency_amount_aligned(self) -> None:
        text = "2024-01-01 Test\n    expenses:food  $50.00\n"
        out = align_posting_amounts(text)
        col = self._amount_end_col(out.splitlines()[1])
        assert col == 52

    def test_posting_no_amount_inline_comment_unchanged(self) -> None:
        text = "2024-01-01 Test\n    expenses:food  ; inline comment\n"
        out = align_posting_amounts(text)
        assert "    expenses:food  ; inline comment" in out

    def test_posting_amount_with_inline_comment_aligned(self) -> None:
        text = "2024-01-01 Test\n    expenses:food  50.00 EUR  ; a note\n"
        out = align_posting_amounts(text)
        posting_line = next(l for l in out.splitlines() if "expenses:food" in l)
        amount_part = posting_line.split("  ;")[0]
        col = self._amount_end_col(amount_part)
        assert col == 52
        assert "; a note" in posting_line
