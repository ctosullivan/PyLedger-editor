"""Command palette stubs and application-level undo/redo infrastructure."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Optional

__all__ = ["Command", "CommandHistory"]


@dataclass
class Command:
    """An invertible operation on application or model state.

    Both ``execute`` and ``undo`` must be synchronous callables that complete
    quickly (< 16 ms).  Heavy work (disk I/O, journal re-parse) must be
    dispatched via Textual workers by the caller, not inside these callables.
    """

    execute: Callable[[], None]
    undo: Callable[[], None]
    description: str
    """Short human-readable label shown in notify() on undo/redo."""


@dataclass
class CommandHistory:
    """Application-level undo/redo stack for operations that affect both buffer
    text and in-memory model objects.

    This is separate from TextArea's native EditHistory (_undo_stack).  The two
    stacks are kept in sync by JournalEditor: action_undo / action_redo consult
    CommandHistory first and fall through to TextArea native undo if it has no
    entries.
    """

    _max_size: int = 100
    _done: list[Command] = field(default_factory=list)
    _undone: list[Command] = field(default_factory=list)

    def execute(self, cmd: Command) -> None:
        """Execute a command and push it onto the undo stack."""
        cmd.execute()
        self._done.append(cmd)
        self._undone.clear()
        if len(self._done) > self._max_size:
            self._done.pop(0)

    def undo(self) -> Optional[Command]:
        """Undo the most recent command and move it to the redo stack."""
        if not self._done:
            return None
        cmd = self._done.pop()
        cmd.undo()
        self._undone.append(cmd)
        return cmd

    def redo(self) -> Optional[Command]:
        """Redo the most recently undone command."""
        if not self._undone:
            return None
        cmd = self._undone.pop()
        cmd.execute()
        self._done.append(cmd)
        return cmd

    @property
    def can_undo(self) -> bool:
        """True if there is at least one command on the undo stack."""
        return bool(self._done)

    @property
    def can_redo(self) -> bool:
        """True if there is at least one command on the redo stack."""
        return bool(self._undone)


# TODO: register command palette providers via Textual's CommandPalette API
# Examples of planned commands:
#   "Open file"        — resolve_journal_file, reload EditorDocument
#   "Save"             — trigger action_save
#   "Filter..."        — open FilterPopup
#   "Go to account"    — jump cursor to first posting for an account
#   "Toggle cleared"   — action_toggle_cleared on selection
