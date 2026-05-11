"""Monokai Pro theme definitions for Ledger Editor.

Provides:
  - MONOKAI_PRO_APP_THEME: a Textual Theme with the full Monokai Pro colour
    palette mapped to the 11 required colour roles, plus 14 custom CSS variable
    overrides for widget chrome.
  - MONOKAI_PRO_TEXTAREA_THEME: a TextAreaTheme with all ledger semantic tokens
    mapped to exact Monokai Pro hex values, bypassing the CSS-variable bridge
    for pixel-perfect palette fidelity.

Comment colour note:
  Canonical Monokai Pro comment colour is #727072 (2.8:1 contrast — fails
  WCAG 2.1 AA). The value used here is #939293 (4.6:1 — passes AA at normal
  text size). To restore strict palette fidelity at the cost of accessibility,
  change both occurrences of #939293 below to #727072.
"""

from rich.style import Style
from textual._text_area_theme import TextAreaTheme
from textual.theme import Theme

THEME_NAME = "monokai-pro"
TEXTAREA_THEME_NAME = "monokai-pro-ledger"

# ---------------------------------------------------------------------------
# Monokai Pro canonical palette
# ---------------------------------------------------------------------------
_BG = "#2D2A2E"       # background
_FG = "#FCFCFA"       # foreground
_SURFACE = "#3D3A3E"  # slightly lighter surface (cleared block bg)
_PANEL = "#403E41"    # panel / pending block bg
_BOOST = "#5B595C"    # boost / selection highlight
_COMMENT = "#939293"  # accessibility-adjusted comment colour (see module docstring)
_RED = "#FF6188"      # error / negative amounts
_ORANGE = "#FC9867"   # accent / accounts / codes
_YELLOW = "#FFD866"   # warning / pending flag & payee
_GREEN = "#A9DC76"    # success / cleared flag, payee & positive amounts
_CYAN = "#78DCE8"     # primary / dates, directives, commodities
_PURPLE = "#AB9DF2"   # secondary / notes, comments

# ---------------------------------------------------------------------------
# App-level theme (chrome colours)
# ---------------------------------------------------------------------------
MONOKAI_PRO_APP_THEME = Theme(
    name=THEME_NAME,
    primary=_CYAN,
    secondary=_PURPLE,
    warning=_YELLOW,
    error=_RED,
    success=_GREEN,
    accent=_ORANGE,
    foreground=_FG,
    background=_BG,
    surface=_SURFACE,
    panel=_PANEL,
    boost=_BOOST,
    dark=True,
    variables={
        # Scrollbar chrome
        "scrollbar-corner-color": _SURFACE,
        "scrollbar-background": _BG,
        "scrollbar-background-hover": _SURFACE,
        "scrollbar-background-active": _PANEL,
        "scrollbar-color": _BOOST,
        "scrollbar-color-hover": _COMMENT,
        "scrollbar-color-active": _FG,
        # Links
        "link-color": _CYAN,
        "link-background": "transparent",
        "link-color-hover": _PURPLE,
        "link-background-hover": _SURFACE,
        # Block cursor (used in DataTable and similar widgets)
        "block-cursor-foreground": _BG,
        "block-cursor-background": _FG,
        "block-cursor-text-style": "b",
    },
)

# ---------------------------------------------------------------------------
# TextArea syntax theme (ledger token colours)
# ---------------------------------------------------------------------------
MONOKAI_PRO_TEXTAREA_THEME = TextAreaTheme(
    name=TEXTAREA_THEME_NAME,
    base_style=Style(color=_FG, bgcolor=_BG),
    syntax_styles={
        # Transaction header tokens
        "ledger.date": Style(color=_CYAN),
        "ledger.flag.cleared": Style(color=_GREEN, bold=True),
        "ledger.flag.pending": Style(color=_YELLOW, bold=True),
        "ledger.code": Style(color=_ORANGE),
        "ledger.payee.uncleared": Style(color=_FG),
        "ledger.payee.cleared": Style(color=_GREEN, bold=True),
        "ledger.payee.pending": Style(color=_YELLOW),
        "ledger.note": Style(color=_COMMENT),
        # Posting tokens
        "ledger.account": Style(color=_ORANGE),
        "ledger.amount.positive": Style(color=_GREEN),
        "ledger.amount.negative": Style(color=_RED),
        "ledger.amount.zero": Style(color=_FG),
        "ledger.commodity": Style(color=_CYAN),
        "ledger.posting.note": Style(color=_COMMENT),
        # Line-level tokens
        "ledger.comment": Style(color=_COMMENT),   # accessibility-adjusted
        "ledger.directive": Style(color=_CYAN),
        "ledger.directive.arg": Style(color=_FG),
    },
)
