"""LedgerTextArea: TextArea subclass with hledger syntax highlighting.

Overrides TextArea._build_highlight_map() (private Textual 8.2.5 API,
widgets/_text_area.py:697) to inject ledger-specific highlights after the
base tree-sitter pass. If this method is renamed in a future Textual release,
move the injection into an equivalent post-edit hook.

Textual's _highlights dict uses UTF-8 byte column offsets (inherited from
tree-sitter). Python's re module returns Unicode codepoint offsets. For
ASCII-only lines these are identical; for lines containing multibyte currency
symbols (£, €, ₹) the offsets diverge. _build_cp_to_byte() converts each
span produced by LedgerHighlighter before it is written to _highlights.

Search highlights are injected in a second pass via set_search_matches().
"""

from __future__ import annotations

from textual import events
from textual.widgets import TextArea

from ledger_editor.highlighting import LedgerHighlighter, build_textarea_theme
from ledger_editor.highlighting import tokens as _tok
from ledger_editor.highlighting.highlighter import LineKind

__all__ = ["LedgerTextArea"]

# A Location is (row, col) — 0-indexed, matching Textual's TextArea convention.
Location = tuple[int, int]


def _build_cp_to_byte(line: str) -> list[int]:
    """Return a list mapping each codepoint index to its UTF-8 byte offset.

    Index i is the byte offset of codepoint i. Index len(line) is the total
    byte length of the line (one-past-end sentinel), matching the exclusive-end
    convention used by Textual's highlight spans.
    """
    result = [0] * (len(line) + 1)
    b = 0
    for i, ch in enumerate(line):
        result[i] = b
        b += len(ch.encode("utf-8"))
    result[len(line)] = b
    return result


class LedgerTextArea(TextArea):
    """TextArea subclass that adds hledger journal syntax and search highlighting.

    Drop-in replacement for TextArea in JournalEditor.compose(). All existing
    query_one(..., TextArea) calls continue to work via subclass compatibility.
    """

    def __init__(self, *args: object, **kwargs: object) -> None:
        # Must be set before super().__init__() because TextArea.__init__ calls
        # _set_document() which calls _build_highlight_map() synchronously.
        self._highlighter = LedgerHighlighter()
        self._search_matches: list[tuple[Location, Location]] = []
        self._search_current: int = -1
        super().__init__(*args, **kwargs)  # type: ignore[arg-type]

    # ------------------------------------------------------------------
    # Key handling — auto-indent
    # ------------------------------------------------------------------

    def _on_key(self, event: events.Key) -> None:
        """Auto-indent on Enter for transaction header and posting lines.

        Textual dispatches _on_key to EVERY class in the MRO independently, so
        simply returning early is not enough — TextArea._on_key would still run
        and insert its own plain newline. event.prevent_default() sets
        _no_default_action which breaks Textual's MRO dispatch loop before it
        reaches TextArea._on_key.

        For all other keys (or wrong line kind) we do nothing: Textual's dispatch
        system reaches TextArea._on_key naturally. No super() call here —
        that would double-invoke the parent.

        TAB is claimed for focus cycling, so auto-indent uses Enter instead.

        Col-0 guard: pressing Enter at the very start of a header line inserts a
        blank separator line before the transaction — auto-indent must not fire
        there, otherwise the date gets pushed down with a 4-space prefix.
        """
        if event.key == "enter":
            row, col = self.cursor_location
            line_infos = self._highlighter._line_infos
            if row < len(line_infos):
                kind = line_infos[row].kind
                if kind == LineKind.POSTING or (
                    kind == LineKind.XACT_HEADER and col > 0
                ):
                    event.prevent_default()
                    self.insert("\n    ")
                    # event.prevent_default() skips Textual's normal key-dispatch
                    # path, which includes a scroll-to-cursor step.
                    # move_cursor(same_pos) is a reactive no-op; scroll_cursor_visible()
                    # scrolls unconditionally regardless of cursor position change.
                    self.scroll_cursor_visible()

    # ------------------------------------------------------------------
    # Mount
    # ------------------------------------------------------------------

    def _on_mount(self, event: events.Mount) -> None:
        """Extend TextArea mount to register an initial ledger theme."""
        super()._on_mount(event)
        # Build a generic bridge theme from the current app palette so there
        # is visible colouring immediately, before LedgerApp.on_mount() has a
        # chance to register and activate the bundled Monokai Pro theme.
        ta_theme = build_textarea_theme(self.app)
        self.register_theme(ta_theme)
        self.theme = "ledger"

    # ------------------------------------------------------------------
    # App theme change — overrides TextArea._app_theme_changed
    # ------------------------------------------------------------------

    def _app_theme_changed(self) -> None:
        """Switch the ledger TextAreaTheme whenever the app theme changes.

        Called by the watcher registered in TextArea._on_mount (Textual 8.2.5,
        _text_area.py:1787). Overriding here is sufficient; no extra
        self.watch() call is needed.
        """
        self._rebuild_ledger_theme()

    # ------------------------------------------------------------------
    # Highlight injection — overrides TextArea._build_highlight_map
    # ------------------------------------------------------------------

    def _build_highlight_map(self) -> None:
        # Overrides TextArea._build_highlight_map() (private API, Textual 8.2.5,
        # widgets/_text_area.py:697). Calls super() first, which clears
        # self._highlights and runs any tree-sitter grammar (none is set here,
        # so it returns immediately after clearing). We then inject custom spans.
        #
        # LedgerHighlighter.get_highlights() returns codepoint column offsets.
        # Textual's _highlights uses UTF-8 byte offsets (matching tree-sitter).
        # _build_cp_to_byte() converts each span before writing to _highlights so
        # that multibyte currency symbols (£, €, ₹) are aligned correctly.
        #
        # Performance note: _scan() is O(N lines). For journals up to ~1 000
        # lines this is well within one frame budget (~16 ms). If profiling
        # shows overruns on larger files, move invalidate() into a
        # @work(thread=True) worker with debouncing.
        super()._build_highlight_map()

        self._highlighter.invalidate(self.text)
        lines = self.text.splitlines()

        # Syntax highlighting pass — ledger token colours from LedgerHighlighter.
        for line_idx, line_text in enumerate(lines):
            spans = self._highlighter.get_highlights(line_idx, line_text)
            if not spans:
                continue
            ctb = _build_cp_to_byte(line_text)
            for start_cp, end_cp, tok in spans:
                start_b = ctb[start_cp]
                end_b = ctb[end_cp] if end_cp is not None else None
                self._highlights[line_idx].append((start_b, end_b, tok))

        # Search highlight pass — injected on top of syntax highlights.
        for i, (start, end) in enumerate(self._search_matches):
            tok = _tok.SEARCH_CURRENT if i == self._search_current else _tok.SEARCH_MATCH
            self._inject_search_span(lines, start, end, tok)

    def _inject_search_span(
        self,
        lines: list[str],
        start: Location,
        end: Location,
        tok: str,
    ) -> None:
        """Append one search match span to _highlights, covering start..end.

        Handles both single-line and (rare) multi-line matches. Column indices
        are codepoint-based and must be converted to byte offsets for Textual.

        Args:
            lines: the full splitlines() of the current text.
            start: (row, col) of the match start (inclusive).
            end: (row, col) of the match end (exclusive past last char).
            tok: token name to use (SEARCH_MATCH or SEARCH_CURRENT).
        """
        start_row, start_col = start
        end_row, end_col = end
        for line_idx in range(start_row, end_row + 1):
            if line_idx >= len(lines):
                break
            line_text = lines[line_idx]
            ctb = _build_cp_to_byte(line_text)
            n = len(ctb) - 1  # last valid byte position (exclusive-end sentinel)
            if line_idx == start_row:
                s_b = ctb[min(start_col, n)]
            else:
                s_b = 0
            if line_idx == end_row:
                e_b = ctb[min(end_col, n)]
            else:
                e_b = None  # None means: extend highlight to end of line
            self._highlights[line_idx].append((s_b, e_b, tok))

    def set_search_matches(
        self,
        matches: list[tuple[Location, Location]],
        current: int,
    ) -> None:
        """Update search highlight state and repaint the widget.

        Called by SearchBar whenever the match list or current index changes.
        Replaces _highlights search spans by re-running _build_highlight_map()
        (which re-injects syntax highlights first, then search highlights on top).

        Args:
            matches: list of (start_location, end_location) pairs.
            current: index into matches for the currently focused match, or -1.
        """
        self._search_matches = matches
        self._search_current = current
        self._build_highlight_map()
        self.refresh()

    # ------------------------------------------------------------------
    # Theme management
    # ------------------------------------------------------------------

    def _rebuild_ledger_theme(self) -> None:
        """Activate the correct TextAreaTheme for the current app theme.

        Two paths:
          Static path — app.theme is in TEXTAREA_THEME_MAP, meaning a bundled
            TextAreaTheme exists with pixel-perfect colours. Register_all() has
            already put it into the TextArea's theme registry.
          Generic bridge path — app.theme is not in the map. Build a new
            TextAreaTheme from the app's CSS variables and register it as
            "ledger", replacing the previous bridge build.
        """
        from ledger_editor.themes import TEXTAREA_THEME_MAP

        ta_name = TEXTAREA_THEME_MAP.get(self.app.theme)
        if ta_name is not None:
            self.theme = ta_name
        else:
            ta_theme = build_textarea_theme(self.app)
            self.register_theme(ta_theme)
            self.theme = "ledger"
