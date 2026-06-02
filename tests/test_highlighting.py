"""Tests for the hledger syntax highlighting module.

All tests in this file are pure Python — no Textual event loop required.
"""

from __future__ import annotations

import pytest

from ledgerkit_editor.highlighting import tokens
from ledgerkit_editor.highlighting.highlighter import (
    LedgerHighlighter,
    LineInfo,
    LineKind,
)
from ledgerkit_editor.highlighting.theme_bridge import build_textarea_theme


# ---------------------------------------------------------------------------
# Token name constants
# ---------------------------------------------------------------------------


class TestTokenConstants:
    def test_date_constant(self) -> None:
        assert tokens.DATE == "ledger.date"

    def test_flag_cleared(self) -> None:
        assert tokens.FLAG_CLEARED == "ledger.flag.cleared"

    def test_flag_pending(self) -> None:
        assert tokens.FLAG_PENDING == "ledger.flag.pending"

    def test_block_tokens_have_block_prefix(self) -> None:
        for t in (tokens.BLOCK_CLEARED, tokens.BLOCK_PENDING, tokens.BLOCK_UNCLEARED):
            assert t.startswith("ledger.block.")

    def test_all_token_names_start_with_ledger(self) -> None:
        public = [v for k, v in vars(tokens).items() if not k.startswith("_")]
        for name in public:
            assert name.startswith("ledger."), f"Token {name!r} lacks 'ledger.' prefix"


# ---------------------------------------------------------------------------
# LedgerHighlighter — line classification (scanner)
# ---------------------------------------------------------------------------

BLANK_LINE = ""
COMMENT_LINE = "; this is a comment"
COMMENT_HASH = "# another comment"
DIRECTIVE_LINE = "account assets:bank:checking"
CLEARED_HEADER = "2024-01-10 * Opening balances"
PENDING_HEADER = "2024-01-10 ! Groceries"
UNCLEARED_HEADER = "2024-01-15 Groceries"
POSTING_LINE = "    expenses:food    £42.50"
ELIDED_POSTING = "    assets:bank:checking"
NEGATIVE_POSTING = "    assets:bank:checking    -42.50 USD"
ZERO_POSTING = "    assets:savings    0 EUR"


def _scan(text: str) -> list[LineInfo]:
    h = LedgerHighlighter()
    h.invalidate(text)
    return h._line_infos


class TestScanner:
    def test_blank_line_classified(self) -> None:
        infos = _scan("\n")
        assert infos[0].kind == LineKind.BLANK

    def test_comment_line_classified(self) -> None:
        infos = _scan(COMMENT_LINE)
        assert infos[0].kind == LineKind.COMMENT

    def test_hash_comment_classified(self) -> None:
        infos = _scan(COMMENT_HASH)
        assert infos[0].kind == LineKind.COMMENT

    def test_directive_classified(self) -> None:
        infos = _scan(DIRECTIVE_LINE)
        assert infos[0].kind == LineKind.DIRECTIVE

    def test_cleared_header_classified(self) -> None:
        infos = _scan(CLEARED_HEADER)
        assert infos[0].kind == LineKind.XACT_HEADER
        assert infos[0].cleared is True
        assert infos[0].pending is False

    def test_pending_header_classified(self) -> None:
        infos = _scan(PENDING_HEADER)
        assert infos[0].kind == LineKind.XACT_HEADER
        assert infos[0].pending is True
        assert infos[0].cleared is False

    def test_uncleared_header_classified(self) -> None:
        infos = _scan(UNCLEARED_HEADER)
        assert infos[0].kind == LineKind.XACT_HEADER
        assert infos[0].cleared is False
        assert infos[0].pending is False

    def test_posting_classified(self) -> None:
        text = f"{CLEARED_HEADER}\n{POSTING_LINE}"
        infos = _scan(text)
        assert infos[1].kind == LineKind.POSTING

    def test_posting_inherits_cleared_state(self) -> None:
        text = f"{CLEARED_HEADER}\n{POSTING_LINE}\n{ELIDED_POSTING}"
        infos = _scan(text)
        assert infos[1].cleared is True
        assert infos[2].cleared is True

    def test_posting_inherits_pending_state(self) -> None:
        text = f"{PENDING_HEADER}\n{POSTING_LINE}"
        infos = _scan(text)
        assert infos[1].pending is True

    def test_blank_resets_state(self) -> None:
        text = f"{CLEARED_HEADER}\n{POSTING_LINE}\n\n{UNCLEARED_HEADER}\n{ELIDED_POSTING}"
        infos = _scan(text)
        # Line 4 (index 4) is the posting after the blank + uncleared header
        assert infos[4].kind == LineKind.POSTING
        assert infos[4].cleared is False

    def test_multi_posting_state_propagation(self) -> None:
        text = (
            "2024-01-10 * Cleared\n"
            "    expenses:food    42.00\n"
            "    assets:bank\n"
        )
        infos = _scan(text)
        assert infos[0].cleared is True
        assert infos[1].cleared is True
        assert infos[2].cleared is True


# ---------------------------------------------------------------------------
# LedgerHighlighter — get_highlights
# ---------------------------------------------------------------------------


def _highlights(line: str, doc: str | None = None) -> list[tuple]:
    """Get highlight spans for a single-line document (or within a doc)."""
    h = LedgerHighlighter()
    doc_text = doc if doc is not None else line
    h.invalidate(doc_text)
    line_idx = doc_text.splitlines().index(line) if doc else 0
    return h.get_highlights(line_idx, line)


class TestHighlightHeader:
    def test_date_span_present(self) -> None:
        spans = _highlights(CLEARED_HEADER)
        token_names = [s[2] for s in spans]
        assert tokens.DATE in token_names

    def test_date_span_correct_range(self) -> None:
        spans = _highlights(CLEARED_HEADER)
        date_span = next(s for s in spans if s[2] == tokens.DATE)
        assert CLEARED_HEADER[date_span[0] : date_span[1]] == "2024-01-10"

    def test_cleared_flag_span(self) -> None:
        spans = _highlights(CLEARED_HEADER)
        token_names = [s[2] for s in spans]
        assert tokens.FLAG_CLEARED in token_names

    def test_pending_flag_span(self) -> None:
        spans = _highlights(PENDING_HEADER)
        token_names = [s[2] for s in spans]
        assert tokens.FLAG_PENDING in token_names

    def test_no_flag_on_uncleared(self) -> None:
        spans = _highlights(UNCLEARED_HEADER)
        token_names = [s[2] for s in spans]
        assert tokens.FLAG_CLEARED not in token_names
        assert tokens.FLAG_PENDING not in token_names

    def test_payee_always_uncleared_token_on_cleared(self) -> None:
        spans = _highlights(CLEARED_HEADER)
        token_names = [s[2] for s in spans]
        assert tokens.PAYEE_UNCLEARED in token_names
        assert tokens.PAYEE_CLEARED not in token_names

    def test_payee_always_uncleared_token_on_pending(self) -> None:
        spans = _highlights(PENDING_HEADER)
        token_names = [s[2] for s in spans]
        assert tokens.PAYEE_UNCLEARED in token_names
        assert tokens.PAYEE_PENDING not in token_names

    def test_payee_uncleared_token(self) -> None:
        spans = _highlights(UNCLEARED_HEADER)
        token_names = [s[2] for s in spans]
        assert tokens.PAYEE_UNCLEARED in token_names

    def test_inline_note_highlighted(self) -> None:
        line = "2024-01-10 * Payee  ; inline note"
        spans = _highlights(line)
        token_names = [s[2] for s in spans]
        assert tokens.NOTE in token_names

    def test_code_field_highlighted(self) -> None:
        line = "2024-01-10 (INV-42) Payee"
        spans = _highlights(line)
        token_names = [s[2] for s in spans]
        assert tokens.CODE in token_names

    def test_no_block_spans_on_header(self) -> None:
        for header in (CLEARED_HEADER, PENDING_HEADER, UNCLEARED_HEADER):
            spans = _highlights(header)
            token_names = [s[2] for s in spans]
            assert tokens.BLOCK_CLEARED not in token_names
            assert tokens.BLOCK_PENDING not in token_names
            assert tokens.BLOCK_UNCLEARED not in token_names


class TestHighlightPosting:
    def _posting_highlights(self, posting: str, flag: str = "*") -> list[tuple]:
        doc = f"2024-01-10 {flag} Header\n{posting}"
        h = LedgerHighlighter()
        h.invalidate(doc)
        return h.get_highlights(1, posting)

    def test_account_highlighted(self) -> None:
        spans = self._posting_highlights("    expenses:food    42.50")
        token_names = [s[2] for s in spans]
        assert tokens.ACCOUNT in token_names

    def test_positive_amount(self) -> None:
        spans = self._posting_highlights("    expenses:food    42.50")
        token_names = [s[2] for s in spans]
        assert tokens.AMOUNT_POSITIVE in token_names

    def test_negative_amount(self) -> None:
        spans = self._posting_highlights("    assets:bank    -42.50")
        token_names = [s[2] for s in spans]
        assert tokens.AMOUNT_NEGATIVE in token_names

    def test_zero_amount(self) -> None:
        spans = self._posting_highlights("    assets:savings    0 EUR")
        token_names = [s[2] for s in spans]
        assert tokens.AMOUNT_ZERO in token_names

    def test_elided_posting_no_amount_token(self) -> None:
        spans = self._posting_highlights("    assets:bank:checking")
        token_names = [s[2] for s in spans]
        assert tokens.AMOUNT_POSITIVE not in token_names
        assert tokens.AMOUNT_NEGATIVE not in token_names
        assert tokens.AMOUNT_ZERO not in token_names

    def test_commodity_suffix(self) -> None:
        spans = self._posting_highlights("    expenses:food    42.50 EUR")
        token_names = [s[2] for s in spans]
        assert tokens.COMMODITY in token_names

    def test_posting_note(self) -> None:
        spans = self._posting_highlights("    expenses:food    42.50  ; note text")
        token_names = [s[2] for s in spans]
        assert tokens.POSTING_NOTE in token_names

    def test_no_block_spans_on_posting(self) -> None:
        for flag in ("*", "!", ""):
            posting = "    expenses:food    42.50"
            if flag:
                spans = self._posting_highlights(posting, flag=flag)
            else:
                spans = self._posting_highlights(posting)
            token_names = [s[2] for s in spans]
            assert tokens.BLOCK_CLEARED not in token_names
            assert tokens.BLOCK_PENDING not in token_names
            assert tokens.BLOCK_UNCLEARED not in token_names


class TestHighlightComment:
    def test_comment_token(self) -> None:
        spans = _highlights("; this is a comment")
        token_names = [s[2] for s in spans]
        assert tokens.COMMENT in token_names

    def test_comment_span_to_end_of_line(self) -> None:
        spans = _highlights("; comment")
        comment_span = next(s for s in spans if s[2] == tokens.COMMENT)
        assert comment_span[0] == 0
        assert comment_span[1] is None


class TestHighlightDirective:
    def test_directive_keyword(self) -> None:
        spans = _highlights("account assets:bank")
        token_names = [s[2] for s in spans]
        assert tokens.DIRECTIVE in token_names

    def test_directive_arg(self) -> None:
        spans = _highlights("account assets:bank")
        token_names = [s[2] for s in spans]
        assert tokens.DIRECTIVE_ARG in token_names

    def test_commodity_directive(self) -> None:
        spans = _highlights("commodity EUR")
        token_names = [s[2] for s in spans]
        assert tokens.DIRECTIVE in token_names


class TestHighlightBlank:
    def test_blank_returns_empty(self) -> None:
        h = LedgerHighlighter()
        h.invalidate("")
        assert h.get_highlights(0, "") == []

    def test_out_of_range_returns_empty(self) -> None:
        h = LedgerHighlighter()
        h.invalidate("2024-01-01 Payee")
        assert h.get_highlights(99, "") == []


# ---------------------------------------------------------------------------
# build_textarea_theme
# ---------------------------------------------------------------------------


class TestBuildTextareaTheme:
    """Unit tests for the CSS-variable bridge."""

    def _make_mock_app(self, overrides: dict | None = None) -> object:
        """Return a minimal mock app with a known get_css_variables() return."""
        default_vars = {
            "primary": "#78DCE8",
            "secondary": "#AB9DF2",
            "warning": "#FFD866",
            "error": "#FF6188",
            "success": "#A9DC76",
            "accent": "#FC9867",
            "foreground": "#FCFCFA",
            "background": "#2D2A2E",
            "surface": "#3D3A3E",
            "panel": "#403E41",
        }
        if overrides:
            default_vars.update(overrides)

        class _MockApp:
            def get_css_variables(self) -> dict:
                return default_vars

        return _MockApp()

    def test_theme_named_ledger(self) -> None:
        app = self._make_mock_app()
        theme = build_textarea_theme(app)  # type: ignore[arg-type]
        assert theme.name == "ledger"

    def test_date_maps_to_primary(self) -> None:
        app = self._make_mock_app({"primary": "#AABBCC"})
        theme = build_textarea_theme(app)  # type: ignore[arg-type]
        style = theme.syntax_styles.get(tokens.DATE)
        assert style is not None
        # Rich lowercases hex values in its string representation
        assert "#aabbcc" in str(style.color).lower()

    def test_flag_cleared_is_bold(self) -> None:
        app = self._make_mock_app()
        theme = build_textarea_theme(app)  # type: ignore[arg-type]
        style = theme.syntax_styles.get(tokens.FLAG_CLEARED)
        assert style is not None
        assert style.bold

    def test_flag_pending_is_bold(self) -> None:
        app = self._make_mock_app()
        theme = build_textarea_theme(app)  # type: ignore[arg-type]
        style = theme.syntax_styles.get(tokens.FLAG_PENDING)
        assert style is not None
        assert style.bold

    def test_missing_variable_uses_fallback(self) -> None:
        app = self._make_mock_app()
        # Remove 'primary' so DATE falls back to the text fallback colour.
        theme = build_textarea_theme(app)  # type: ignore[arg-type]
        assert tokens.DATE in theme.syntax_styles

    def test_foreground_tokens_all_present(self) -> None:
        import ledgerkit_editor.highlighting.tokens as t
        app = self._make_mock_app()
        theme = build_textarea_theme(app)  # type: ignore[arg-type]
        # Block tokens are intentionally omitted from the bridge theme.
        block_tokens = {t.BLOCK_CLEARED, t.BLOCK_PENDING, t.BLOCK_UNCLEARED}
        foreground_tokens = [
            v for k, v in vars(t).items()
            if not k.startswith("_") and v not in block_tokens
        ]
        for tok in foreground_tokens:
            assert tok in theme.syntax_styles, f"Token {tok!r} missing from theme"

    def test_ansi_color_names_do_not_crash(self) -> None:
        """ANSI themes return colour names like 'ansi_blue' that Rich cannot parse.

        build_textarea_theme() must catch ColorParseError and fall back to a
        neutral grey rather than propagating the exception.
        """
        class _AnsiApp:
            def get_css_variables(self) -> dict:
                return {k: "ansi_blue" for k in (
                    "primary", "secondary", "warning", "error", "success",
                    "accent", "foreground", "background", "surface", "panel",
                )}

        theme = build_textarea_theme(_AnsiApp())  # type: ignore[arg-type]
        # All foreground tokens should fall back to the text fallback grey
        style = theme.syntax_styles.get(tokens.DATE)
        assert style is not None
        assert "#888888" in str(style.color).lower()


# ---------------------------------------------------------------------------
# Amount prefix symbol merged into amount span
# ---------------------------------------------------------------------------


class TestAmountPrefixMerged:
    """Prefix currency symbols (£, $) must be included in the amount span, not
    emitted as a separate COMMODITY span.  Only suffix commodity codes (USD, EUR)
    get a separate COMMODITY span."""

    def _posting_highlights(self, posting: str) -> list[tuple]:
        doc = f"2024-01-10 * Header\n{posting}"
        h = LedgerHighlighter()
        h.invalidate(doc)
        return h.get_highlights(1, posting)

    def test_gbp_prefix_no_separate_commodity_span(self) -> None:
        spans = self._posting_highlights("    expenses:food    £42.50")
        commodity_spans = [s for s in spans if s[2] == tokens.COMMODITY]
        assert len(commodity_spans) == 0, "No separate COMMODITY span for £ prefix"

    def test_dollar_prefix_no_separate_commodity_span(self) -> None:
        spans = self._posting_highlights("    expenses:food    $10.00")
        commodity_spans = [s for s in spans if s[2] == tokens.COMMODITY]
        assert len(commodity_spans) == 0, "No separate COMMODITY span for $ prefix"

    def test_amount_span_starts_at_prefix_symbol(self) -> None:
        posting = "    expenses:food    £42.50"
        spans = self._posting_highlights(posting)
        amount_spans = [s for s in spans if s[2] == tokens.AMOUNT_POSITIVE]
        assert len(amount_spans) == 1
        start = amount_spans[0][0]
        assert posting[start] == "£", f"Amount span should start at £, not {posting[start]!r}"

    def test_suffix_code_gets_commodity_span(self) -> None:
        spans = self._posting_highlights("    expenses:food    42.50 EUR")
        token_names = [s[2] for s in spans]
        assert tokens.COMMODITY in token_names

    def test_negative_gbp_includes_minus_in_span(self) -> None:
        posting = "    assets:bank    -£42.50"
        spans = self._posting_highlights(posting)
        # With prefix symbol the span starts at £, not at -
        amount_spans = [s for s in spans if s[2] == tokens.AMOUNT_NEGATIVE]
        assert len(amount_spans) == 1
        start = amount_spans[0][0]
        assert posting[start] in ("-", "£"), (
            f"Negative+prefix span should start at £ or -, got {posting[start]!r}"
        )


# ---------------------------------------------------------------------------
# Suffix commodity codes — single-character codes must get COMMODITY token
# ---------------------------------------------------------------------------


class TestCommodity1Char:
    """Suffix commodity codes of length 1 must be highlighted."""

    def _posting_highlights(self, posting: str) -> list[tuple]:
        doc = f"2024-01-10 Header\n{posting}"
        h = LedgerHighlighter()
        h.invalidate(doc)
        return h.get_highlights(1, posting)

    def test_single_char_suffix_gets_commodity_token(self) -> None:
        spans = self._posting_highlights("    expenses:food    100 X")
        token_names = [s[2] for s in spans]
        assert tokens.COMMODITY in token_names, "Single-char suffix 'X' must get COMMODITY span"

    def test_two_char_suffix_gets_commodity_token(self) -> None:
        spans = self._posting_highlights("    expenses:food    100 GB")
        token_names = [s[2] for s in spans]
        assert tokens.COMMODITY in token_names

    def test_three_char_suffix_unchanged(self) -> None:
        spans = self._posting_highlights("    expenses:food    100 USD")
        token_names = [s[2] for s in spans]
        assert tokens.COMMODITY in token_names


# ---------------------------------------------------------------------------
# _build_cp_to_byte — UTF-8 byte offset mapping
# ---------------------------------------------------------------------------


class TestCpToByteMapping:
    """_build_cp_to_byte must return correct byte offsets for multibyte chars."""

    def _ctb(self, text: str) -> list[int]:
        from ledgerkit_editor.widgets.ledger_textarea import _build_cp_to_byte
        return _build_cp_to_byte(text)

    def test_ascii_only(self) -> None:
        ctb = self._ctb("hello")
        assert ctb == [0, 1, 2, 3, 4, 5]

    def test_pound_sign_is_two_bytes(self) -> None:
        # £ = U+00A3 = 0xC2 0xA3 in UTF-8 (2 bytes)
        ctb = self._ctb("£")
        assert ctb[0] == 0   # £ starts at byte 0
        assert ctb[1] == 2   # one-past-end = byte 2

    def test_euro_sign_is_three_bytes(self) -> None:
        # € = U+20AC = 0xE2 0x82 0xAC in UTF-8 (3 bytes)
        ctb = self._ctb("€")
        assert ctb[0] == 0
        assert ctb[1] == 3

    def test_mixed_ascii_and_multibyte(self) -> None:
        # "£42" — £ is 2 bytes, then 2 ASCII chars
        ctb = self._ctb("£42")
        assert ctb[0] == 0   # £ at byte 0
        assert ctb[1] == 2   # 4 at byte 2
        assert ctb[2] == 3   # 2 at byte 3
        assert ctb[3] == 4   # sentinel

    def test_amount_span_end_byte_for_gbp(self) -> None:
        # "£42.50" has 6 codepoints but 7 bytes.
        # Codepoint offset 6 (one-past-end) must map to byte 7.
        ctb = self._ctb("£42.50")
        assert ctb[6] == 7, f"Expected 7, got {ctb[6]}"
