"""Tests for ledger_editor.utils.ledger_io."""

from pathlib import Path

import pytest

from ledger_editor.utils.ledger_io import (
    align_posting_amounts,
    load_journal,
    split_journal_segments,
    split_preamble,
)

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


class TestSplitPreamble:
    """Tests for split_preamble()."""

    def test_preamble_and_transactions(self) -> None:
        text = (
            "P 2024-01-01 USD EUR 0.92\n"
            "account assets:bank\n"
            "\n"
            "2024-01-15 Groceries\n"
            "    expenses:food  £10\n"
            "    assets:bank   -£10\n"
        )
        preamble, body = split_preamble(text)
        assert preamble == "P 2024-01-01 USD EUR 0.92\naccount assets:bank\n\n"
        assert body.startswith("2024-01-15")

    def test_empty_preamble_when_transaction_first(self) -> None:
        text = "2024-01-01 Payment\n    expenses:food  £5\n    assets:bank  -£5\n"
        preamble, body = split_preamble(text)
        assert preamble == ""
        assert body == text

    def test_no_transactions_returns_full_text_as_preamble(self) -> None:
        text = "P 2024-01-01 USD EUR 0.92\n; just a comment\n"
        preamble, body = split_preamble(text)
        assert preamble == text
        assert body == ""

    def test_empty_string(self) -> None:
        preamble, body = split_preamble("")
        assert preamble == ""
        assert body == ""

    def test_preamble_preserved_through_split_rejoin(self) -> None:
        text = (
            "; file header\n"
            "P 2024-01-01 EUR USD 1.08\n"
            "\n"
            "2024-03-01 Later\n"
            "    expenses:misc  $5\n"
            "    assets:bank   -$5\n"
            "\n"
            "2024-01-10 Earlier\n"
            "    expenses:food  $10\n"
            "    assets:bank   -$10\n"
        )
        preamble, body = split_preamble(text)
        rejoined = preamble + body
        assert rejoined == text


class TestSplitJournalSegments:
    """Tests for split_journal_segments()."""

    # Helper: build a minimal Transaction-like object with a source_span.
    @staticmethod
    def _txn(start_line: int, end_line: int) -> object:
        """Return a duck-typed stand-in for Transaction with a SourceSpan."""
        import datetime

        class _Span:
            def __init__(self, s: int, e: int) -> None:
                self.start_line = s
                self.end_line = e

        class _Txn:
            def __init__(self, s: int, e: int) -> None:
                self.source_span = _Span(s, e)
                self.date = datetime.date(2024, 1, 1)

        return _Txn(start_line, end_line)

    def test_no_transactions_returns_whole_text_as_single_block(self) -> None:
        text = "P 2024-01-01 USD EUR 0.92\n; comment\n"
        non_txn, txn = split_journal_segments(text, [])
        assert non_txn == [text]
        assert txn == []

    def test_preamble_and_single_transaction(self) -> None:
        text = "P 2024-01-01 USD EUR 0.92\n\n2024-01-15 Pay\n    exp  £5\n    bank -£5\n"
        # Preamble = lines 1-2 (1-based). Transaction header on line 3, postings 4-5.
        txns = [self._txn(3, 5)]
        non_txn, txn_blocks = split_journal_segments(text, txns)
        assert len(non_txn) == 2
        assert len(txn_blocks) == 1
        assert non_txn[0] == "P 2024-01-01 USD EUR 0.92\n\n"
        assert txn_blocks[0].startswith("2024-01-15")
        assert non_txn[1] == ""  # no trailing content

    def test_interleaved_directive_becomes_inter_txn_block(self) -> None:
        text = (
            "2024-01-15 First\n"         # line 1
            "    exp  £5\n"              # line 2
            "    bank -£5\n"             # line 3
            "\n"                         # line 4 (blank separator)
            "P 2024-02-01 USD EUR 0.95\n"  # line 5 (directive between transactions)
            "\n"                         # line 6
            "2024-02-15 Second\n"        # line 7
            "    exp  £10\n"             # line 8
            "    bank -£10\n"            # line 9
        )
        txns = [self._txn(1, 3), self._txn(7, 9)]
        non_txn, txn_blocks = split_journal_segments(text, txns)
        assert len(non_txn) == 3
        assert len(txn_blocks) == 2
        assert non_txn[0] == ""                          # empty preamble
        assert "P 2024-02-01" in non_txn[1]             # directive preserved in inter-block
        assert non_txn[2] == ""                          # empty trailing
        assert txn_blocks[0].startswith("2024-01-15")
        assert txn_blocks[1].startswith("2024-02-15")

    def test_roundtrip_reassembly_equals_original(self) -> None:
        text = (
            "P 2024-01-01 USD EUR 0.92\n"
            "\n"
            "2024-01-15 First\n"
            "    exp  £5\n"
            "    bank -£5\n"
            "\n"
            "P 2024-02-01 USD EUR 0.95\n"
            "\n"
            "2024-02-15 Second\n"
            "    exp  £10\n"
            "    bank -£10\n"
        )
        txns = [self._txn(3, 5), self._txn(9, 11)]
        non_txn, txn_blocks = split_journal_segments(text, txns)
        # Reassemble: non_txn[0] + txn[0] + non_txn[1] + txn[1] + non_txn[2]
        reassembled = non_txn[0]
        for i, block in enumerate(txn_blocks):
            reassembled += block + non_txn[i + 1]
        assert reassembled == text

    def test_fallback_when_source_span_none(self) -> None:
        text = (
            "P 2024-01-01 USD EUR 0.92\n"
            "\n"
            "2024-01-15 First\n"
            "    exp  £5\n"
            "    bank -£5\n"
        )

        class _NoSpanTxn:
            source_span = None

        non_txn, txn_blocks = split_journal_segments(text, [_NoSpanTxn()])
        # Fallback: preamble preserved, inter/trailing blocks empty
        assert non_txn[0] == "P 2024-01-01 USD EUR 0.92\n\n"
        assert all(b == "" for b in non_txn[1:])
        assert all(b == "" for b in txn_blocks)
