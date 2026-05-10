"""Tests for ledger_editor.utils.ledger_io."""

from pathlib import Path

import pytest

from ledger_editor.utils.ledger_io import load_journal

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
