"""CSS-variable bridge: build a TextAreaTheme from the active Textual app theme.

Reads the app's resolved CSS variable palette (via App.get_css_variables()) and
maps each ledger token to the appropriate colour. Works with any Textual theme
that provides the 11 required base colour roles.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from rich.color import ColorParseError
from rich.style import Style
from textual._text_area_theme import TextAreaTheme

from ledger_editor.highlighting import tokens

if TYPE_CHECKING:
    from textual.app import App

__all__ = ["build_textarea_theme"]

# Fallback colours for themes that omit optional variables.
_TEXT_FALLBACK = "#888888"
_BG_FALLBACK = "transparent"

# Mapping from token name to the CSS variable key (no '$' prefix) that
# provides its foreground colour. Block tokens are handled separately
# since they set background rather than foreground.
_TOKEN_TO_CSS_VAR: dict[str, str] = {
    tokens.DATE: "primary",
    tokens.FLAG_CLEARED: "success",
    tokens.FLAG_PENDING: "warning",
    tokens.CODE: "accent",
    tokens.PAYEE_UNCLEARED: "foreground",
    tokens.PAYEE_CLEARED: "success",
    tokens.PAYEE_PENDING: "warning",
    tokens.NOTE: "secondary",
    tokens.ACCOUNT: "accent",
    tokens.AMOUNT_POSITIVE: "success",
    tokens.AMOUNT_NEGATIVE: "error",
    tokens.AMOUNT_ZERO: "foreground",
    tokens.COMMODITY: "primary",
    tokens.POSTING_NOTE: "secondary",
    tokens.COMMENT: "secondary",
    tokens.DIRECTIVE: "primary",
    tokens.DIRECTIVE_ARG: "foreground",
}

# Tokens rendered in bold.
_BOLD_TOKENS = frozenset({
    tokens.FLAG_CLEARED,
    tokens.FLAG_PENDING,
})


def build_textarea_theme(app: "App") -> TextAreaTheme:
    """Build a TextAreaTheme from the currently active Textual app theme.

    Reads the resolved CSS variables (without '$' prefix) and maps each ledger
    token to the appropriate colour role. Falls back to neutral greys for any
    variable missing from the theme (handles minimal third-party themes).

    Args:
        app: The running Textual App instance.

    Returns:
        A TextAreaTheme named "ledger" ready to register on a TextArea.
    """
    variables = app.get_css_variables()

    syntax_styles: dict[str, Style] = {}

    for token, css_var in _TOKEN_TO_CSS_VAR.items():
        color = variables.get(css_var, _TEXT_FALLBACK)
        bold = token in _BOLD_TOKENS
        try:
            syntax_styles[token] = Style(color=color, bold=bold)
        except ColorParseError:
            # ANSI themes return colour names like "ansi_blue" that Rich cannot
            # parse as hex/RGB colours. Fall back to a neutral grey.
            syntax_styles[token] = Style(color=_TEXT_FALLBACK, bold=bold)

    return TextAreaTheme(name="ledger", syntax_styles=syntax_styles)
