"""Context manager for collapsing multiple TextArea edits into one undo entry."""

from __future__ import annotations

from contextlib import contextmanager
from typing import TYPE_CHECKING, Iterator

if TYPE_CHECKING:
    from textual.widgets import TextArea

__all__ = ["atomic_edit"]


@contextmanager
def atomic_edit(text_area: "TextArea") -> Iterator[None]:
    """Collapse all TextArea edits made within this block into a single undo entry.

    Each call to TextArea.replace() with multi-character text automatically
    creates its own checkpoint in EditHistory, so repeated replace() calls (e.g.
    bulk-toggle-cleared) leave N entries on the undo stack and require N Ctrl+Z
    presses.  Wrapping those calls in atomic_edit() merges the new entries into
    one, so a single Ctrl+Z reverses the entire operation.

    Uses text_area.history._undo_stack (EditHistory private API, Textual 0.83.0).
    Raises RuntimeError if the attribute is absent — this signals a Textual
    version incompatibility and must not be silenced.

    Usage:
        with atomic_edit(textarea):
            textarea.replace(...)
            textarea.replace(...)
        # Ctrl+Z now reverses both replaces in one press.
    """
    history = text_area.history
    if not hasattr(history, "_undo_stack"):
        raise RuntimeError(
            "atomic_edit: EditHistory._undo_stack not found. "
            "Verify Textual version is 0.83.0."
        )
    stack = history._undo_stack
    before_len = len(stack)
    yield
    new_count = len(stack) - before_len
    if new_count <= 1:
        return
    # Pop the new batches (most-recent first from deque.pop()), restore
    # chronological order, then flatten all Edit lists into one batch.
    new_batches = [stack.pop() for _ in range(new_count)]
    new_batches.reverse()
    combined = [edit for batch in new_batches for edit in batch]
    stack.append(combined)
