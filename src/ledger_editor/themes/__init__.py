"""Bundled themes for Ledger Editor.

Call register_all(app, ledger_textarea) in LedgerApp.on_mount() before
setting app.theme, so every bundled theme is available when needed.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from textual.theme import BUILTIN_THEMES, Theme

from ledger_editor.themes.monokai_pro import (
    MONOKAI_PRO_APP_THEME,
    MONOKAI_PRO_TEXTAREA_THEME,
    TEXTAREA_THEME_NAME,
    THEME_NAME,
)

if TYPE_CHECKING:
    from textual.app import App
    from ledger_editor.widgets.ledger_textarea import LedgerTextArea

__all__ = [
    "BUNDLED_THEMES",
    "TEXTAREA_THEME_MAP",
    "VALID_THEMES",
    "register_all",
]

# All bundled Textual App themes.
BUNDLED_THEMES: list[Theme] = [MONOKAI_PRO_APP_THEME]

# Every accepted theme name: Textual built-ins plus project-bundled themes.
# Computed at import time from BUILTIN_THEMES so new Textual releases and new
# bundled entries are picked up automatically.
VALID_THEMES: frozenset[str] = frozenset(BUILTIN_THEMES) | {t.name for t in BUNDLED_THEMES}

# Maps app theme name → TextAreaTheme name for the static (non-bridge) path.
# When app.theme is in this dict, _rebuild_ledger_theme() uses the pre-built
# TextAreaTheme directly instead of approximating via CSS variables.
TEXTAREA_THEME_MAP: dict[str, str] = {
    THEME_NAME: TEXTAREA_THEME_NAME,
}


def register_all(app: "App", ledger_textarea: "LedgerTextArea") -> None:
    """Register all bundled app themes and TextArea themes.

    Must be called before setting app.theme to any bundled theme name.

    Args:
        app: The running Textual App instance.
        ledger_textarea: The LedgerTextArea widget to register TA themes on.
    """
    for theme in BUNDLED_THEMES:
        app.register_theme(theme)

    ledger_textarea.register_theme(MONOKAI_PRO_TEXTAREA_THEME)
