"""Pure-unit tests for Command and CommandHistory (no Textual dependency)."""

from __future__ import annotations

from ledger_editor.commands import Command, CommandHistory


def _make_cmd(log: list[str], name: str) -> Command:
    return Command(
        execute=lambda: log.append(f"do:{name}"),
        undo=lambda: log.append(f"undo:{name}"),
        description=name,
    )


class TestCommandHistory:
    def test_execute_appends_to_done(self) -> None:
        h = CommandHistory()
        log: list[str] = []
        h.execute(_make_cmd(log, "A"))
        assert len(h._done) == 1
        assert log == ["do:A"]

    def test_execute_clears_undone(self) -> None:
        h = CommandHistory()
        log: list[str] = []
        cmd_a = _make_cmd(log, "A")
        h.execute(cmd_a)
        h.undo()
        h.execute(_make_cmd(log, "B"))
        assert len(h._undone) == 0

    def test_undo_calls_cmd_undo_and_moves_to_undone(self) -> None:
        h = CommandHistory()
        log: list[str] = []
        h.execute(_make_cmd(log, "A"))
        result = h.undo()
        assert result is not None
        assert result.description == "A"
        assert "undo:A" in log
        assert len(h._done) == 0
        assert len(h._undone) == 1

    def test_undo_on_empty_returns_none(self) -> None:
        h = CommandHistory()
        assert h.undo() is None

    def test_redo_calls_cmd_execute_and_moves_to_done(self) -> None:
        h = CommandHistory()
        log: list[str] = []
        h.execute(_make_cmd(log, "A"))
        h.undo()
        log.clear()
        result = h.redo()
        assert result is not None
        assert "do:A" in log
        assert len(h._done) == 1
        assert len(h._undone) == 0

    def test_redo_on_empty_returns_none(self) -> None:
        h = CommandHistory()
        assert h.redo() is None

    def test_max_size_respected(self) -> None:
        h = CommandHistory(_max_size=3)
        log: list[str] = []
        for i in range(5):
            h.execute(_make_cmd(log, str(i)))
        assert len(h._done) == 3
        assert h._done[0].description == "2"

    def test_can_undo_reflects_state(self) -> None:
        h = CommandHistory()
        assert not h.can_undo
        log: list[str] = []
        h.execute(_make_cmd(log, "A"))
        assert h.can_undo
        h.undo()
        assert not h.can_undo

    def test_can_redo_reflects_state(self) -> None:
        h = CommandHistory()
        log: list[str] = []
        h.execute(_make_cmd(log, "A"))
        assert not h.can_redo
        h.undo()
        assert h.can_redo
        h.redo()
        assert not h.can_redo
