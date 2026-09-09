"""Tab-autocomplete suggestion bar for JournalEditor (Phase 4a).

Docked at the bottom of the editor, hidden by default — the same pattern as
SearchBar (search_bar.py), not FilterPopup's floating overlay. A fixed dock
position is far simpler to get right and verify reliably than pixel-perfect
cursor-relative positioning would be; the tradeoff is that suggestions don't
literally hover next to the cursor. Revisit as a visual-polish item later if
that's wanted (see planning/next-release-phase-plan.md Phase 4).

Never takes focus (`can_focus = False`) — JournalEditor's own Tab/Escape
bindings drive it directly (see widgets/autocomplete.py's AutocompleteMixin),
so the cursor never leaves the LedgerTextArea while suggestions are showing.
Cycling through candidates is Tab-repeat (bash-style), not Up/Down — see
AutocompleteMixin's docstring for why Up/Down navigation was deliberately
left out of this first cut.
"""

from __future__ import annotations

from textual.widget import Widget
from textual.widgets import Label

__all__ = ["AutocompletePopup"]


class AutocompletePopup(Widget):
    """Bottom-docked, non-focusable Tab-autocomplete suggestion bar."""

    can_focus = False

    DEFAULT_CSS = """
    AutocompletePopup {
        dock: bottom;
        height: 2;
        background: $surface;
        border-top: solid $primary;
        display: none;
        layout: horizontal;
        padding: 0 1;
    }
    AutocompletePopup > .candidate {
        padding: 0 1;
        color: $text-muted;
    }
    AutocompletePopup > .candidate-selected {
        background: $primary;
        color: $text;
        text-style: bold;
    }
    """

    def __init__(self, *args: object, **kwargs: object) -> None:
        super().__init__(*args, **kwargs)  # type: ignore[arg-type]
        self._candidates: list[str] = []
        self._selected: int = 0
        self.display = False

    @property
    def candidates(self) -> list[str]:
        """The current candidate list (a copy — callers must not mutate)."""
        return list(self._candidates)

    @property
    def selected_candidate(self) -> str | None:
        """The currently highlighted candidate, or None if not showing."""
        if not self._candidates:
            return None
        return self._candidates[self._selected]

    @property
    def is_showing(self) -> bool:
        return bool(self._candidates) and bool(self.display)

    def show(self, candidates: list[str]) -> None:
        """Reveal the bar with candidates, selecting the first one.

        No-op (stays hidden) if candidates is empty.
        """
        if not candidates:
            self.hide()
            return
        self._candidates = candidates
        self._selected = 0
        self._rebuild()
        self.display = True

    def hide(self) -> None:
        """Hide the bar and clear its candidates."""
        self.display = False
        self._candidates = []
        self._selected = 0
        self.remove_children()

    def cycle_next(self) -> str | None:
        """Advance to the next candidate (wrapping around) and return it.

        Returns None if there are no candidates to cycle through.
        """
        if not self._candidates:
            return None
        self._selected = (self._selected + 1) % len(self._candidates)
        self._rebuild()
        return self.selected_candidate

    def _rebuild(self) -> None:
        self.remove_children()
        labels = [
            Label(
                name,
                classes="candidate candidate-selected" if i == self._selected else "candidate",
            )
            for i, name in enumerate(self._candidates)
        ]
        if labels:
            self.mount_all(labels)
