"""Pure-Python hledger journal syntax highlighter.

No Textual imports — this module is intentionally framework-agnostic so that
the integration layer (LedgerTextArea) is the only place that touches Textual
internals.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum, auto
from typing import Optional, Tuple

from ledger_editor.highlighting import tokens

__all__ = ["LedgerHighlighter", "LineInfo", "LineKind"]

# ---------------------------------------------------------------------------
# Regex patterns
# ---------------------------------------------------------------------------

# Matches a transaction header line in hledger journal format.
# Purpose: identify lines that open a transaction block, and extract each
#          named field so the highlighter can apply a distinct token to each.
#
# Group breakdown:
#   (1) \d{4}[-/]\d{2}[-/]\d{2} — ISO date (YYYY-MM-DD or YYYY/MM/DD), required
#   (2) [*!]                     — status flag: * = cleared, ! = pending;
#                                  absent (None) means uncleared
#   (3) [^)]*                    — code text inside parens (parens consumed too),
#                                  e.g. "(INV-42)"; absent when no code present
#   (4) [^;]*                    — payee / description: everything up to the
#                                  first ';' (greedy, may include trailing spaces)
#   (5) ;.*                      — full inline comment including the leading ';'
#
# Edge cases:
#   - Date-only header "2024-01-01" matches with groups 2–5 absent
#   - Flag without code: "2024-01-01 * Payee" — group 3 is None
#   - Code without flag: "2024-01-01 (INV-42) Payee" — group 2 is None
#   - Empty payee after flag: "2024-01-01 *" — group 4 is "" after strip
#   - Posting lines (leading whitespace) are never passed here; caller guards
_XACT_HEADER_RE = re.compile(
    r"^(\d{4}[-/]\d{2}[-/]\d{2})"  # group 1: date
    r"\s*([*!])?"                    # group 2: optional flag
    r"\s*(\([^)]*\))?"              # group 3: optional (CODE) including parens
    r"\s*([^;]*)"                   # group 4: payee (everything before ';')
    r"(;.*)?$"                      # group 5: optional inline comment with ';'
)

# Matches an hledger directive keyword at the start of a non-indented line.
# Purpose: distinguish directive lines from transaction headers so the scanner
#          does not treat them as opening a transaction block.
#
# Group breakdown:
#   (1) account|commodity|...  — the directive keyword (multi-word variants included)
#   (2) .*                     — the rest of the line (arguments / declared name)
#
# Edge cases:
#   - "D EUR" — group 1="D", group 2="EUR" (default commodity directive)
#   - "apply account Home" — matched by "apply\s+\w+" alternative
#   - "end apply account" — matched by "end\s+\w+" alternative
#   - Unknown keywords fall through; the scanner falls back to UNKNOWN
_DIRECTIVE_RE = re.compile(
    r"^(account|commodity|include|alias|payee|tag"
    r"|apply\s+\w+|end(?:\s+\w+)+"
    r"|[DPY])(?:\s+(.*))?$"
)

# Matches a standalone comment line in hledger journal format.
# Purpose: skip these lines in the transaction scanner so they don't reset
#          or advance clearing-state tracking.
#
# Group breakdown: none — a boolean match is sufficient for classification.
#
# Edge cases:
#   - A line with only ";" is a valid comment
#   - "#" and "%" are also hledger comment chars; "*" is NOT included here
#     because a bare "*" without a date prefix is ambiguous and uncommon
_COMMENT_RE = re.compile(r"^[;#%]")

# Matches an hledger amount value within the amount section of a posting line.
# Purpose: locate the numeric part and commodity of an amount to classify it
#          as positive, negative, or zero, and to separately identify the
#          commodity token for colouring.
#
# Group breakdown:
#   (1) -            — optional leading minus sign; presence means negative
#   (2) [$€£¥₹]     — optional prefix currency symbol (appears before digits)
#   (3) [\d,]+\.?\d* — numeric value: integers, optional thousands commas,
#                      optional decimal part (e.g. "1,234.50", "42", "0.5")
#   (4) [A-Z]{1,6}   — optional suffix commodity code matched after whitespace
#                      (e.g. "X", "USD", "EUR", "BTC", "AAPL")
#
# Edge cases:
#   - "$42.50"    — group 1 absent, group 2="$", group 3="42.50", group 4 absent
#   - "-100 USD"  — group 1="-", group 2 absent, group 3="100", group 4="USD"
#   - "1,234 EUR" — group 3="1,234" (commas in integer part)
#   - "0"         — group 3="0", classified as zero
#   - No match on elided postings; the caller must handle None return
_AMOUNT_RE = re.compile(
    r"(-?)"              # group 1: optional minus
    r"([$€£¥₹])?"       # group 2: optional prefix symbol
    r"([\d,]+\.?\d*)"   # group 3: numeric digits
    r"(?:\s+([A-Z]{1,6}))?"  # group 4: optional suffix commodity code
)

# Matches an inline note (comment) within a posting or header line.
# Purpose: locate the ';' delimiter that starts a posting note so the note
#          text can be given a distinct colour from the amount.
#
# Group breakdown: no capture groups — match position is used directly.
#
# Edge cases:
#   - A bare ";" with no text after it matches and highlights the semicolon
#   - Leading whitespace before ";" is not consumed; caller slices from match start
_NOTE_RE = re.compile(r";")

# Separator between account name and amount in a posting line.
# Purpose: find the boundary between account and amount so each can be
#          highlighted separately. hledger requires ≥2 spaces or a tab.
#
# Group breakdown: none — match positions are used directly.
#
# Edge cases:
#   - Single space in account name ("savings account") does not split
#   - A tab character is an alternative to the two-space rule
_POSTING_SEP_RE = re.compile(r"  +|\t")


# ---------------------------------------------------------------------------
# Data types
# ---------------------------------------------------------------------------


class LineKind(Enum):
    """Classification of a single journal line."""
    BLANK = auto()
    COMMENT = auto()
    DIRECTIVE = auto()
    XACT_HEADER = auto()
    POSTING = auto()
    UNKNOWN = auto()


@dataclass
class LineInfo:
    """Pre-computed classification and state for one journal line."""
    kind: LineKind
    cleared: bool = False
    pending: bool = False


# ---------------------------------------------------------------------------
# Highlighter
# ---------------------------------------------------------------------------

Span = Tuple[int, Optional[int], str]


class LedgerHighlighter:
    """Regex-based syntax highlighter for hledger journal files.

    All highlighting is derived from a single O(N) scan of the full document
    text, so per-line highlight queries are O(1) lookups into the cached
    result.
    """

    def __init__(self) -> None:
        self._line_infos: list[LineInfo] = []

    def invalidate(self, text: str) -> None:
        """Re-scan the full document text and cache the result.

        Call this whenever the document text changes. The scan is O(N) in
        the number of lines.

        Args:
            text: The complete current document text.
        """
        self._line_infos = self._scan(text)

    def _scan(self, text: str) -> list[LineInfo]:
        """Single-pass line classifier that tracks transaction state."""
        lines = text.splitlines()
        result: list[LineInfo] = []
        current_cleared = False
        current_pending = False

        for line in lines:
            if not line or not line.strip():
                result.append(LineInfo(kind=LineKind.BLANK))
                current_cleared = False
                current_pending = False
                continue

            if line[0].isspace():
                result.append(
                    LineInfo(
                        kind=LineKind.POSTING,
                        cleared=current_cleared,
                        pending=current_pending,
                    )
                )
                continue

            if _COMMENT_RE.match(line):
                result.append(LineInfo(kind=LineKind.COMMENT))
                continue

            if _XACT_HEADER_RE.match(line):
                flag_match = _XACT_HEADER_RE.match(line)
                flag = flag_match.group(2) if flag_match else None
                cleared = flag == "*"
                pending = flag == "!"
                current_cleared = cleared
                current_pending = pending
                result.append(
                    LineInfo(
                        kind=LineKind.XACT_HEADER,
                        cleared=cleared,
                        pending=pending,
                    )
                )
                continue

            if _DIRECTIVE_RE.match(line):
                result.append(LineInfo(kind=LineKind.DIRECTIVE))
                current_cleared = False
                current_pending = False
                continue

            result.append(LineInfo(kind=LineKind.UNKNOWN))
            current_cleared = False
            current_pending = False

        return result

    def get_highlights(
        self, line_index: int, line_text: str
    ) -> list[Span]:
        """Return syntax highlight spans for one line.

        Returns a list of (start_col, end_col, token_name) tuples using
        Unicode codepoint offsets. end_col may be None to mean end-of-line.

        Note: column offsets are codepoint-based (from re.Match positions).
        For the rare case of multibyte unicode characters (e.g. currency
        symbols in commodity positions), these may not align exactly with the
        byte offsets expected by Textual's renderer; ASCII content is unaffected.

        Args:
            line_index: Zero-based line number in the document.
            line_text: The raw text of that line (no trailing newline).
        """
        if line_index >= len(self._line_infos):
            return []

        info = self._line_infos[line_index]

        if info.kind == LineKind.XACT_HEADER:
            return self._highlight_header(line_text, info)
        if info.kind == LineKind.POSTING:
            return self._highlight_posting(line_text, info)
        if info.kind == LineKind.COMMENT:
            return self._highlight_comment(line_text)
        if info.kind == LineKind.DIRECTIVE:
            return self._highlight_directive(line_text)

        return []

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _highlight_header(self, line_text: str, info: LineInfo) -> list[Span]:
        """Return spans for a transaction header line."""
        spans: list[Span] = []

        m = _XACT_HEADER_RE.match(line_text)
        if not m:
            return spans

        # Date
        spans.append((m.start(1), m.end(1), tokens.DATE))

        # Flag
        if m.group(2):
            tok = tokens.FLAG_CLEARED if m.group(2) == "*" else tokens.FLAG_PENDING
            spans.append((m.start(2), m.end(2), tok))

        # Code — group 3 includes the surrounding parens
        if m.group(3) is not None:
            spans.append((m.start(3), m.end(3), tokens.CODE))

        # Payee — always use PAYEE_UNCLEARED; cleared/pending state is communicated
        # by the flag token alone (using distinct payee colours per state caused the
        # payee to appear the same colour as the flag character).
        payee_raw = m.group(4) or ""
        payee_stripped = payee_raw.rstrip()
        if payee_stripped:
            spans.append((m.start(4), m.start(4) + len(payee_stripped), tokens.PAYEE_UNCLEARED))

        # Inline note — group 5 includes the leading ';'
        if m.group(5) is not None:
            spans.append((m.start(5), None, tokens.NOTE))

        return spans

    def _highlight_posting(self, line_text: str, info: LineInfo) -> list[Span]:
        """Return spans for a posting line."""
        spans: list[Span] = []

        stripped = line_text.lstrip()
        indent = len(line_text) - len(stripped)

        sep = _POSTING_SEP_RE.search(stripped)
        if sep:
            account_end = indent + sep.start()
            amount_start = indent + sep.end()
        else:
            account_end = indent + len(stripped)
            amount_start = None

        # Account
        account_text = stripped[: sep.start() if sep else len(stripped)].rstrip()
        if account_text:
            spans.append((indent, indent + len(account_text), tokens.ACCOUNT))

        # Amount + commodity + posting note
        if amount_start is not None:
            amount_text = line_text[amount_start:]
            spans.extend(self._highlight_amount_section(amount_start, amount_text))

        return spans

    def _highlight_amount_section(
        self, section_start: int, section_text: str
    ) -> list[Span]:
        """Return spans for the amount portion of a posting line."""
        spans: list[Span] = []

        # Find a note marker first to split amount from note
        note_m = _NOTE_RE.search(section_text)
        amount_text = section_text[: note_m.start()] if note_m else section_text

        # Try to find a numeric amount
        am = _AMOUNT_RE.search(amount_text)
        if am:
            sign = am.group(1)
            prefix_sym = am.group(2)
            number = am.group(3)
            suffix_code = am.group(4)

            # Amount span: include the prefix symbol (£/$) in the amount colour rather
            # than emitting a separate COMMODITY span. Adjacent prefix+amount spans of
            # different colours cause off-by-one artefacts with multibyte symbols.
            if prefix_sym:
                num_col_start = section_start + am.start(2)   # start at £/$
            elif sign == "-":
                num_col_start = section_start + am.start(1)   # start at -
            else:
                num_col_start = section_start + am.start(3)   # start at first digit
            num_col_end = section_start + am.end(3)
            stripped_num = number.replace(",", "").lstrip("0") or "0"
            try:
                value = float(stripped_num)
            except ValueError:
                value = 0.0

            if sign == "-" or value < 0:
                amount_tok = tokens.AMOUNT_NEGATIVE
            elif value == 0.0:
                amount_tok = tokens.AMOUNT_ZERO
            else:
                amount_tok = tokens.AMOUNT_POSITIVE
            spans.append((num_col_start, num_col_end, amount_tok))

            # Commodity suffix code (e.g. "USD")
            if suffix_code and am.group(4):
                # am.start(4) points into section_text; group 4 is after whitespace
                sfx_start = section_start + am.start(4)
                spans.append((sfx_start, sfx_start + len(suffix_code.strip()), tokens.COMMODITY))

        # Posting note
        if note_m:
            note_col = section_start + note_m.start()
            spans.append((note_col, None, tokens.POSTING_NOTE))

        return spans

    def _highlight_comment(self, line_text: str) -> list[Span]:
        """Return spans for a standalone comment line."""
        return [(0, None, tokens.COMMENT)]

    def _highlight_directive(self, line_text: str) -> list[Span]:
        """Return spans for a directive line."""
        spans: list[Span] = []
        m = _DIRECTIVE_RE.match(line_text)
        if not m:
            return spans

        spans.append((m.start(1), m.end(1), tokens.DIRECTIVE))
        if m.group(2) is not None and m.group(2).strip():
            spans.append((m.start(2), None, tokens.DIRECTIVE_ARG))

        return spans
