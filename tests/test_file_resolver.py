"""Tests for ledger_editor.utils.file_resolver."""

import os
from pathlib import Path

import pytest

from ledger_editor.utils.file_resolver import resolve_journal_file


class TestResolveJournalFile:
    """Tests for resolve_journal_file()."""

    def test_cli_path_takes_priority(self, tmp_path: Path) -> None:
        journal = tmp_path / "test.journal"
        journal.write_text("; empty\n")
        result = resolve_journal_file(str(journal))
        assert result == journal.resolve()

    def test_cli_path_missing_falls_through(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        env_journal = tmp_path / "env.journal"
        env_journal.write_text("; empty\n")
        monkeypatch.setenv("LEDGER_FILE", str(env_journal))
        result = resolve_journal_file(str(tmp_path / "nonexistent.journal"))
        assert result == env_journal.resolve()

    def test_env_var_used_when_no_cli(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        env_journal = tmp_path / "ledger_file.journal"
        env_journal.write_text("; empty\n")
        monkeypatch.setenv("LEDGER_FILE", str(env_journal))
        result = resolve_journal_file(None)
        assert result == env_journal.resolve()

    def test_returns_none_when_nothing_found(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.delenv("LEDGER_FILE", raising=False)
        # Patch home to a temp dir with no .hledger.journal
        monkeypatch.setenv("HOME", str(tmp_path))
        monkeypatch.setenv("USERPROFILE", str(tmp_path))
        result = resolve_journal_file(None)
        assert result is None
