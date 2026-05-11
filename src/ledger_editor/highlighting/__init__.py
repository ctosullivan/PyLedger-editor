"""Syntax highlighting for hledger journal files.

Provides the LedgerHighlighter (pure-Python scanner), build_textarea_theme
(CSS-variable bridge), and the token name constants in tokens.py.
"""

from ledger_editor.highlighting.highlighter import LedgerHighlighter, LineInfo, LineKind
from ledger_editor.highlighting.theme_bridge import build_textarea_theme
from ledger_editor.highlighting import tokens

__all__ = [
    "LedgerHighlighter",
    "LineInfo",
    "LineKind",
    "build_textarea_theme",
    "tokens",
]
