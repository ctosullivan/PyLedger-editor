"""Date shifting (Shift+Up/Down) for JournalEditor.

Split out of transaction_table.py (Phase 2 of the next-release plan — see
planning/next-release-phase-plan.md) once that module passed the Module Size
Rule threshold. Pure regex/arithmetic helpers live here alongside
DateShiftMixin, the JournalEditor mixin that wires them to the widget's
cursor and TextArea. _TXN_HEADER_RE also lives here (rather than in
transaction_table.py) since it's fundamentally about locating a header's
date field; transaction_table.py imports it back for flag-cycling and
autofill, which need the same (date, flag, rest) split but aren't
date-shift concerns themselves.
"""

from __future__ import annotations

import calendar
import re
from datetime import date as _date
from datetime import timedelta

from ledgerkit_editor.highlighting.highlighter import LineKind
from ledgerkit_editor.widgets.ledger_textarea import LedgerTextArea

__all__ = [
    "DateShiftMixin",
    "_DATE_FIELD_START",
    "_DATE_PARSE_RE",
    "_PRICE_DIRECTIVE_RE",
    "_TXN_HEADER_RE",
    "_date_subfield_at_col",
    "_normalize_date_str",
    "_shift_date_str",
]

# ---------------------------------------------------------------------------
# Regex patterns
# ---------------------------------------------------------------------------

# Purpose: parse an hledger transaction header line to extract and cycle the
#   status flag while preserving the date, code, description, and comments.
# Group breakdown:
#   group 1 — date segment (YYYY-MM-DD or YYYY/MM/DD; month/day accept 1 or 2
#             digits so an unpadded date like "2026-9-1" still matches)
#   group 2 — status flag (* or !) — absent (None) when the transaction is uncleared
#   group 3 — remainder: optional code (INV-42), description, inline comment
# Edge cases: date-only lines match with empty group 3; posting lines (leading
#   whitespace) must never be passed here — the caller is responsible for that
#   guard. Group 1 may be shorter than 10 chars for unpadded dates — callers
#   that shift the date normalise it to zero-padded form first (see
#   _normalize_date_str).
_TXN_HEADER_RE = re.compile(
    r"^(\d{4}[-/]\d{1,2}[-/]\d{1,2})\s*(\*|!)?\s*(.*)"
)

# Matches a P (market price) directive line and captures its date argument.
# Purpose: locate the date portion of a price directive so Shift+Up/Down can
#   shift it the same way it shifts a transaction header date — P directives
#   are classified as the generic LineKind.DIRECTIVE by the highlighter (see
#   highlighting/highlighter.py's _DIRECTIVE_RE), which does not expose where
#   the date starts, so this dedicated regex is needed to find it.
# Group breakdown:
#   (1) \d{4}[-/]\d{1,2}[-/]\d{1,2} — the directive's date argument; month/day
#       accept 1 or 2 digits, same as _TXN_HEADER_RE
# Edge cases:
#   - "P 2026-09-01 EUR 1.08 USD" — group 1 = "2026-09-01" (commodity/rate
#     ignored; only the date span is needed for shifting)
#   - "P 2026-9-1 EUR 1.08 USD" — group 1 = "2026-9-1" (unpadded; normalised
#     by _normalize_date_str before shifting)
#   - Requires exactly one or more spaces between "P" and the date; a bare
#     "P" with no date does not match, so it falls through to plain selection
_PRICE_DIRECTIVE_RE = re.compile(r"^P\s+(\d{4}[-/]\d{1,2}[-/]\d{1,2})\b")

# Purpose: parse an hledger date string of the form YYYY<sep>M[M]<sep>D[D],
#   where <sep> is any single character (typically '-', '/', or '.'), into
#   year/month/day components. Month and day accept 1 or 2 digits so unpadded
#   dates like "2026-9-1" parse alongside the canonical zero-padded form.
# Group breakdown:
#   (1) \d{4}   — four-digit year
#   (2) .       — first separator (captured, not assumed to be '-')
#   (3) \d{1,2} — month, 1 or 2 digits
#   (4) .       — second separator (captured independently of group 2)
#   (5) \d{1,2} — day, 1 or 2 digits
# Edge cases:
#   - "2026-9-1" matches: groups = ("2026", "-", "9", "-", "1")
#   - Mismatched separators like "2024-01/15" still match (group 2 != group
#     4); _shift_date_str deliberately normalises output to use group 2's
#     separator for both positions, matching its pre-existing behaviour
#   - date_str must be exactly year-sep-month-sep-day with no extra
#     characters ($ anchor); callers slice out just the date substring first
_DATE_PARSE_RE = re.compile(r"^(\d{4})(.)(\d{1,2})(.)(\d{1,2})$")

# Column each sub-field starts at within a canonical zero-padded 10-char date
# (YYYY-MM-DD). Used to reposition the cursor within a subfield after
# _normalize_date_str pads a date, since padding can change every column
# after the year.
_DATE_FIELD_START = {"year": 0, "month": 5, "day": 8}


# ---------------------------------------------------------------------------
# Pure helpers
# ---------------------------------------------------------------------------


def _date_subfield_at_col(date_str: str, col: int) -> str | None:
    """Return 'year', 'month', or 'day' for a cursor column within date_str.

    Field boundaries are derived from date_str's own separator positions
    (via _DATE_PARSE_RE) rather than assumed to be a fixed 10-char layout, so
    this also works for unpadded dates like "2026-9-1" before they've been
    normalised. Separators are assigned to the field on their right — e.g. in
    "2024-01-15" col 4 (the first '-') → month, col 7 (the second '-') → day.
    Returns None when col is negative or outside the date, or date_str
    doesn't match the date grammar at all.
    """
    if col < 0:
        return None
    m = _DATE_PARSE_RE.match(date_str)
    if not m:
        return None
    year, _sep1, month, _sep2, day = m.groups()
    month_start = len(year)  # separator index; assigned to "month"
    day_start = month_start + 1 + len(month)  # second separator index
    date_end = day_start + 1 + len(day)
    if col < month_start:
        return "year"
    if col < day_start:
        return "month"
    if col < date_end:
        return "day"
    return None


def _normalize_date_str(date_str: str) -> str:
    """Return date_str with month and day zero-padded to 2 digits.

    Always produces a canonical 10-character YYYY-MM-DD (or YYYY/MM/DD, per
    the original separator) string. Returns date_str unchanged if it doesn't
    match the date grammar. Used to expand an unpadded date (e.g. "2026-9-1")
    to "2026-09-01" the first time it's shifted with Shift+Up/Down.
    """
    m = _DATE_PARSE_RE.match(date_str)
    if not m:
        return date_str
    year, sep, month, _sep2, day = m.groups()
    return f"{year}{sep}{int(month):02d}{sep}{int(day):02d}"


def _shift_date_str(date_str: str, subfield: str, delta: int) -> str:
    """Return date_str with the given sub-field shifted by delta, separator preserved.

    Month-end overflow is clamped: Jan 31 + 1 month → Feb 28/29. Year shift
    clamps Feb 29 on a leap year to Feb 28 on a non-leap year. Accepts
    unpadded input (e.g. "2026-9-1") but always returns zero-padded output,
    since the day/month components are always formatted with :02d below.
    """
    m = _DATE_PARSE_RE.match(date_str)
    if not m:
        return date_str
    year, sep, month, _sep2, day = m.groups()
    y, mo, d = int(year), int(month), int(day)

    if subfield == "day":
        new = _date(y, mo, d) + timedelta(days=delta)
        return f"{new.year:04d}{sep}{new.month:02d}{sep}{new.day:02d}"

    if subfield == "month":
        total = (y * 12 + mo - 1) + delta
        new_y, new_m0 = divmod(total, 12)
        new_mo = new_m0 + 1
        max_d = calendar.monthrange(new_y, new_mo)[1]
        return f"{new_y:04d}{sep}{new_mo:02d}{sep}{min(d, max_d):02d}"

    # subfield == "year"
    new_y = y + delta
    max_d = calendar.monthrange(new_y, mo)[1]
    return f"{new_y:04d}{sep}{mo:02d}{sep}{min(d, max_d):02d}"


# ---------------------------------------------------------------------------
# Mixin
# ---------------------------------------------------------------------------


class DateShiftMixin:
    """JournalEditor mixin providing Shift+Up/Down date-field shifting.

    Expects to be mixed into a Textual Widget that hosts a LedgerTextArea at
    "#journal_textarea" (JournalEditor's own compose() provides this). Owns
    no instance state of its own — pure delegation from action_date_shift_up/
    down to _shift_date_by, which reads the widget's own textarea query.
    """

    def action_date_shift_up(self) -> None:
        """Shift the date sub-field under the cursor up by 1 (Shift+Up)."""
        self._shift_date_by(+1)

    def action_date_shift_down(self) -> None:
        """Shift the date sub-field under the cursor down by 1 (Shift+Down)."""
        self._shift_date_by(-1)

    def _shift_date_by(self, delta: int) -> None:
        """Shift the date sub-field under the cursor, or fall through to selection.

        Handles two line kinds: a transaction header (date starts at column 0)
        and a P price-directive (date starts after "P "). Either way, an
        unpadded date (e.g. "2026-9-1") is normalised to zero-padded form
        (e.g. "2026-09-01") as part of the same replace() — see
        _normalize_date_str — so the very first Shift+Up/Down both expands
        and shifts it.
        """
        textarea = self.query_one("#journal_textarea", LedgerTextArea)
        row, col = textarea.cursor_location
        line_infos = textarea._highlighter._line_infos

        def _fallthrough() -> None:
            if delta > 0:
                textarea.action_cursor_up(select=True)
            else:
                textarea.action_cursor_down(select=True)

        if row >= len(line_infos):
            _fallthrough()
            return

        lines = textarea.text.splitlines()
        line = lines[row] if row < len(lines) else ""
        kind = line_infos[row].kind

        date_str: str | None = None
        date_start_col = 0
        if kind == LineKind.XACT_HEADER:
            m = _TXN_HEADER_RE.match(line)
            if m:
                date_str = m.group(1)
                date_start_col = 0
        elif kind == LineKind.DIRECTIVE:
            m = _PRICE_DIRECTIVE_RE.match(line)
            if m:
                date_str = m.group(1)
                date_start_col = m.start(1)

        if date_str is None:
            _fallthrough()
            return

        col_in_date = col - date_start_col
        subfield = _date_subfield_at_col(date_str, col_in_date)
        if subfield is None:
            _fallthrough()
            return

        canonical_date_str = _normalize_date_str(date_str)
        new_date_str = _shift_date_str(canonical_date_str, subfield, delta)
        textarea.replace(
            new_date_str,
            (row, date_start_col),
            (row, date_start_col + len(date_str)),
        )
        new_col = date_start_col + _DATE_FIELD_START[subfield]
        textarea.move_cursor((row, new_col), select=False)
