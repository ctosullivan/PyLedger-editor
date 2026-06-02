"""Tests for the atomic_edit() context manager."""

from __future__ import annotations

from collections import deque
from unittest.mock import MagicMock

import pytest

from ledgerkit_editor.utils.atomic_edit import atomic_edit


def _mock_edit(text: str = "x") -> MagicMock:
    """Return a minimal mock that looks like a Textual Edit object."""
    e = MagicMock()
    e.text = text
    return e


def _fake_textarea(stack_contents: list[list[MagicMock]]) -> MagicMock:
    """Build a fake TextArea-like object whose history._undo_stack is a deque."""
    history = MagicMock()
    history._undo_stack = deque(stack_contents)
    ta = MagicMock()
    ta.history = history
    return ta


class TestAtomicEdit:
    def test_two_edits_collapsed_into_one(self) -> None:
        ta = _fake_textarea([])
        with atomic_edit(ta):
            ta.history._undo_stack.append([_mock_edit("a")])
            ta.history._undo_stack.append([_mock_edit("b")])
        assert len(ta.history._undo_stack) == 1
        assert len(ta.history._undo_stack[-1]) == 2

    def test_zero_edits_leaves_stack_unchanged(self) -> None:
        initial = [_mock_edit("pre")]
        ta = _fake_textarea([[initial[0]]])
        with atomic_edit(ta):
            pass
        assert len(ta.history._undo_stack) == 1

    def test_one_edit_left_as_is(self) -> None:
        ta = _fake_textarea([])
        edit = _mock_edit("only")
        with atomic_edit(ta):
            ta.history._undo_stack.append([edit])
        assert len(ta.history._undo_stack) == 1
        assert ta.history._undo_stack[-1] == [edit]

    def test_chronological_order_preserved(self) -> None:
        ta = _fake_textarea([])
        e1, e2, e3 = _mock_edit("1"), _mock_edit("2"), _mock_edit("3")
        with atomic_edit(ta):
            ta.history._undo_stack.append([e1])
            ta.history._undo_stack.append([e2])
            ta.history._undo_stack.append([e3])
        combined = ta.history._undo_stack[-1]
        assert combined == [e1, e2, e3]

    def test_missing_undo_stack_raises_runtime_error(self) -> None:
        ta = MagicMock()
        ta.history = MagicMock(spec=[])  # spec=[] means no attributes
        with pytest.raises(RuntimeError, match="_undo_stack"):
            with atomic_edit(ta):
                pass

    def test_pre_existing_entries_untouched(self) -> None:
        existing = [_mock_edit("old")]
        ta = _fake_textarea([[existing[0]]])
        with atomic_edit(ta):
            ta.history._undo_stack.append([_mock_edit("new1")])
            ta.history._undo_stack.append([_mock_edit("new2")])
        assert len(ta.history._undo_stack) == 2
        assert ta.history._undo_stack[0] == [existing[0]]
