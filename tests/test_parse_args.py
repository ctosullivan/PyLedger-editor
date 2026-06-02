"""Tests for CLI argument parsing in ledgerkit_editor.app._parse_args."""

from __future__ import annotations

import pytest

from ledgerkit_editor.app import _parse_args


def test_defaults() -> None:
    args = _parse_args([])
    assert args.file is None
    assert args.line is None
    assert args.theme is None


def test_file_only() -> None:
    args = _parse_args(["a.journal"])
    assert args.file == "a.journal"
    assert args.line is None
    assert args.theme is None


def test_line_flag() -> None:
    args = _parse_args(["--line=42"])
    assert args.line == 42


def test_plus_n() -> None:
    args = _parse_args(["+42"])
    assert args.line == 42
    assert args.file is None


def test_plus_n_with_file_after() -> None:
    args = _parse_args(["a.journal", "+42"])
    assert args.line == 42
    assert args.file == "a.journal"


def test_plus_n_with_file_before() -> None:
    args = _parse_args(["+42", "a.journal"])
    assert args.line == 42
    assert args.file == "a.journal"


def test_line_flag_beats_plus_n() -> None:
    """--line takes precedence over a +N token when both are present."""
    args = _parse_args(["--line=10", "+99"])
    assert args.line == 10


def test_plus_n_zero() -> None:
    """'+0' is accepted; the caller clamps it to row 0."""
    args = _parse_args(["+0"])
    assert args.line == 0


def test_theme_valid() -> None:
    args = _parse_args(["--theme=nord"])
    assert args.theme == "nord"


def test_theme_monokai_pro() -> None:
    args = _parse_args(["--theme=monokai-pro"])
    assert args.theme == "monokai-pro"


def test_theme_textual_light() -> None:
    args = _parse_args(["--theme=textual-light"])
    assert args.theme == "textual-light"


def test_theme_invalid_exits() -> None:
    with pytest.raises(SystemExit):
        _parse_args(["--theme=bogus-theme-xyz"])


def test_all_args_combined() -> None:
    args = _parse_args(["a.journal", "--line=5", "--theme=gruvbox"])
    assert args.file == "a.journal"
    assert args.line == 5
    assert args.theme == "gruvbox"
