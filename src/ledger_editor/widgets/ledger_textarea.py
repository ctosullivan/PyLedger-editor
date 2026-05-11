"""LedgerTextArea: TextArea subclass with hledger syntax highlighting.

Overrides TextArea._build_highlight_map() (private Textual 8.2.5 API,
widgets/_text_area.py:697) to inject ledger-specific highlights after the
base tree-sitter pass. If this method is renamed in a future Textual release,
move the injection into an equivalent post-edit hook.

Two highlight layers are produced on every rebuild:
  Layer 1 — field-level token spans (date, flag, account, amount, etc.)
  Layer 2 — block-level background spans (cleared/pending/uncleared overlay)

Both layers write into self._highlights, which Textual reads during render.
"""

from __future__ import annotations

from textual import events
from textual.widgets import TextArea

from ledger_editor.highlighting import LedgerHighlighter, build_textarea_theme
from ledger_editor.highlighting import tokens as _tok
from ledger_editor.highlighting.highlighter import LineKind

__all__ = ["LedgerTextArea"]


class LedgerTextArea(TextArea):
    """TextArea subclass that adds hledger journal syntax highlighting.

    Drop-in replacement for TextArea in JournalEditor.compose(). All existing
    query_one(..., TextArea) calls continue to work via subclass compatibility.
    """

    def __init__(self, *args: object, **kwargs: object) -> None:
        # Must be set before super().__init__() because TextArea.__init__ calls
        # _set_document() which calls _build_highlight_map() synchronously.
        self._highlighter = LedgerHighlighter()
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
        """
        if event.key == "enter":
            row, _ = self.cursor_location
            line_infos = self._highlighter._line_infos
            if row < len(line_infos) and line_infos[row].kind in (
                LineKind.XACT_HEADER, LineKind.POSTING
            ):
                event.prevent_default()
                self.insert("\n    ")

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
        # Performance note: _scan() is O(N lines). For journals up to ~1 000
        # lines this is well within one frame budget (~16 ms). If profiling
        # shows overruns on larger files, move invalidate() into a
        # @work(thread=True) worker with debouncing.
        super()._build_highlight_map()

        self._highlighter.invalidate(self.text)
        lines = self.text.splitlines()
        for line_idx, line_text in enumerate(lines):
            spans = self._highlighter.get_highlights(line_idx, line_text)
            self._highlights[line_idx].extend(spans)

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
