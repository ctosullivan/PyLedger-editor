"""Smart date parsing for the filter popup and transaction editing.

Supports:
  - ISO 8601 strings: "2024-01-15"
  - Year-month shorthand: "2024-01" (a whole calendar month)
  - Named periods: "today", "yesterday", "this week", "last week",
    "this month", "last month", "this year", "last year"
  - Year-to-date: "ytd"
  - Quarter shorthands: "q1", "q2", "q3", "q4" (current year)
  - Month name, with or without a year: "september", "sep 2026",
    "September 2026" (bare month name defaults to the current year)
  - Relative offsets: "-7d", "-1m", "+1w"

Returns datetime.date objects. All parsing is relative to the date at call time
(i.e. datetime.date.today()), not a fixed session date.

Every named-period phrase above (i.e. everything except a plain ISO date,
the "2024-01" shorthand, and a relative offset) is a bounded SPAN, not a
single point — see _period_bounds(). parse_date() itself only ever returns
the span's *start* (for backward-compatible single-date use); the bounded
end is what parse_date_range() uses to auto-fill the other side of a
date-from/date-to pair when only one field names a period: "last month"
alone in Date From auto-fills Date To with the last day of that month,
rather than staying open-ended from its first day onward. A plain ISO
date, "2024-01", or a relative offset ("-7d") stays open-ended when used
alone — they're single points in time with no separate "other end" of
their own (well, "2024-01" over the SAME field also has a natural end —
see _period_bounds — but as a value it still reads as "a month", handled
identically to the named periods for auto-fill purposes).
"""

from __future__ import annotations

import calendar
import datetime
import re

__all__ = ["DateParseError", "parse_date", "parse_date_range"]


class DateParseError(ValueError):
    """Raised when a date string cannot be parsed by any supported pattern."""


# ---------------------------------------------------------------------------
# ISO 8601 exact date pattern.
# Purpose: match a fully-specified calendar date in YYYY-MM-DD format.
#
# Group breakdown:
#   (1) \d{4}  — four-digit year
#   (2) \d{2}  — two-digit month (01–12)
#   (3) \d{2}  — two-digit day (01–31)
#
# Edge cases:
#   - No validation of calendar correctness (e.g. 2024-02-30 would match).
#     Downstream datetime.date() constructor raises ValueError for invalid dates.
#   - Separator must be '-'; '/' and '.' variants are not supported here.
# ---------------------------------------------------------------------------
_ISO_DATE = re.compile(r"^(\d{4})-(\d{2})-(\d{2})$")

# ---------------------------------------------------------------------------
# Year-month shorthand, e.g. "2024-01" — a whole calendar month, no day.
#
# Group breakdown:
#   (1) \d{4}   — four-digit year
#   (2) \d{1,2} — month, 1 or 2 digits (matches this module's general
#       tolerance for unpadded numbers elsewhere, e.g. relative offsets)
#
# Edge cases:
#   - Does not match a full "2024-01-15" — that's _ISO_DATE (3 parts)
#   - Month is range-checked (1-12) by the caller, not this pattern
# ---------------------------------------------------------------------------
_YEAR_MONTH = re.compile(r"^(\d{4})-(\d{1,2})$")

# ---------------------------------------------------------------------------
# Relative date offset pattern, e.g. "-7d", "+1m", "+2w", "-1y".
#
# Group breakdown:
#   (1) [+-]   — direction: '+' for a date after today, '-' for before
#   (2) \d+    — magnitude (may be more than one digit, e.g. "-30d")
#   (3) [dwmy] — unit: d=days, w=weeks, m=months, y=years
#
# Edge cases:
#   - "+0d" is valid (magnitude 0) and resolves to exactly `today`
#   - No support for combined units ("-1m2d"); each string is a single unit
#   - Unit letters are lowercase only — parse_date() already lowercases the
#     full input before this pattern is tried, so "+1M" also matches
# ---------------------------------------------------------------------------
_RELATIVE_OFFSET = re.compile(r"^([+-])(\d+)([dwmy])$")

# ---------------------------------------------------------------------------
# Quarter shorthand pattern, e.g. "q1".."q4" (current year).
#
# Group breakdown:
#   (1) [1-4] — the quarter number
#
# Edge cases:
#   - Case-insensitive in practice: parse_date() lowercases input first
#   - "q5" and bare "q" do not match
# ---------------------------------------------------------------------------
_QUARTER = re.compile(r"^q([1-4])$")

# ---------------------------------------------------------------------------
# Month name, with an optional 4-digit year, e.g. "september", "sep 2026",
# "september 2026". A bare month name defaults to the current year.
#
# Group breakdown:
#   (1) [a-z]+  — the month word (looked up case-insensitively in
#       _MONTH_NAMES below; the regex itself accepts any run of letters,
#       so an unknown word like "foobar" matches the pattern but is
#       rejected by the _MONTH_NAMES lookup in _period_bounds)
#   (2) \d{4}   — optional four-digit year, separated by whitespace
#
# Edge cases:
#   - "september2026" (no space) does not match — a space is required
#     before the year
#   - Every OTHER named-period keyword ("today", "ytd", "last month", ...)
#     is checked earlier in _period_bounds and never reaches this pattern,
#     since none of them independently also happen to be a valid month
#     name/abbreviation
# ---------------------------------------------------------------------------
_MONTH_YEAR = re.compile(r"^([a-z]+)(?:\s+(\d{4}))?$")

_MONTH_NAMES: dict[str, int] = {
    "january": 1, "jan": 1,
    "february": 2, "feb": 2,
    "march": 3, "mar": 3,
    "april": 4, "apr": 4,
    "may": 5,
    "june": 6, "jun": 6,
    "july": 7, "jul": 7,
    "august": 8, "aug": 8,
    "september": 9, "sep": 9, "sept": 9,
    "october": 10, "oct": 10,
    "november": 11, "nov": 11,
    "december": 12, "dec": 12,
}


def _add_months(d: datetime.date, months: int) -> datetime.date:
    """Return d shifted by `months`, clamping the day to the target month's length.

    Mirrors the month-end clamping convention used by the editor's own
    Shift+Up/Down date-field shifting (widgets/date_shift.py's
    _shift_date_str), for consistency: Jan 31 + 1 month → Feb 28/29, not an
    error and not silently rolling into March.
    """
    total = (d.year * 12 + d.month - 1) + months
    new_year, new_month0 = divmod(total, 12)
    new_month = new_month0 + 1
    max_day = calendar.monthrange(new_year, new_month)[1]
    return datetime.date(new_year, new_month, min(d.day, max_day))


def _month_span(year: int, month: int) -> tuple[datetime.date, datetime.date]:
    """Return (first day, last day) of the given calendar month."""
    last_day = calendar.monthrange(year, month)[1]
    return (datetime.date(year, month, 1), datetime.date(year, month, last_day))


def _period_bounds(
    text: str, today: datetime.date
) -> tuple[datetime.date, datetime.date] | None:
    """Return (start, end) if text is a bounded calendar-period phrase.

    A "period phrase" is a named span with a natural beginning and end:
    "today", "yesterday", "this week", "last week", "this month",
    "last month", "this year", "last year", "ytd", "q1".."q4", a month
    name with or without a year ("september", "sep 2026"), or the
    "2024-01" year-month shorthand. Returns None for anything that's a
    single point in time rather than a span: a full ISO date, or a
    relative offset like "-7d" — those have no separate "end" distinct
    from the date itself, so the caller should keep using parse_date() for
    them (an open-ended bound is the correct/expected behaviour for
    "everything from 7 days ago onward").

    "ytd" is bounded by `today`, not December 31st — "year to date" means
    up to now, not the whole year (unlike "last year"/"this year", which
    are treated as complete spans even though "this year" technically
    extends into the future beyond today — matching how "this month"
    behaves the same way for symmetry, and how hledger's own period
    expressions work).

    Weeks start on Monday (ISO 8601 convention, matching hledger's default).

    Used by parse_date_range() to auto-fill the *other* bound when only one
    smart-date field is given a period phrase and the other is left blank —
    see that function's docstring for the exact rule. Also used by
    parse_date() itself, which returns just the start of whatever span this
    returns.
    """
    text = text.strip().lower()

    if text in ("today", "now"):
        return (today, today)

    if text == "yesterday":
        y = today - datetime.timedelta(days=1)
        return (y, y)

    if text == "this week":
        monday = today - datetime.timedelta(days=today.weekday())
        return (monday, monday + datetime.timedelta(days=6))

    if text == "last week":
        this_monday = today - datetime.timedelta(days=today.weekday())
        last_monday = this_monday - datetime.timedelta(days=7)
        return (last_monday, last_monday + datetime.timedelta(days=6))

    if text == "this month":
        return _month_span(today.year, today.month)

    if text == "last month":
        last_month_end = today.replace(day=1) - datetime.timedelta(days=1)
        return _month_span(last_month_end.year, last_month_end.month)

    if text == "this year":
        return (datetime.date(today.year, 1, 1), datetime.date(today.year, 12, 31))

    if text == "last year":
        return (
            datetime.date(today.year - 1, 1, 1),
            datetime.date(today.year - 1, 12, 31),
        )

    if text == "ytd":
        return (datetime.date(today.year, 1, 1), today)

    m = _QUARTER.match(text)
    if m:
        quarter = int(m.group(1))
        start_month = (quarter - 1) * 3 + 1
        end_month = start_month + 2
        start, _ = _month_span(today.year, start_month)
        _, end = _month_span(today.year, end_month)
        return (start, end)

    m = _YEAR_MONTH.match(text)
    if m:
        year, month = int(m.group(1)), int(m.group(2))
        if not 1 <= month <= 12:
            return None
        return _month_span(year, month)

    m = _MONTH_YEAR.match(text)
    if m:
        month_word, year_str = m.groups()
        month = _MONTH_NAMES.get(month_word)
        if month is None:
            return None
        year = int(year_str) if year_str else today.year
        return _month_span(year, month)

    return None


def parse_date(text: str, today: datetime.date | None = None) -> datetime.date:
    """Parse a smart date string into a datetime.date.

    Any bounded period phrase (see _period_bounds) resolves to its start —
    e.g. "last month" gives the 1st of last month, "september 2026" gives
    2026-09-01. Use parse_date_range() instead of two separate parse_date()
    calls when you want the *whole* span a period phrase names, since that
    function auto-fills the other bound from the same period rather than
    leaving it open-ended.

    Args:
        text:  Human-friendly or ISO date string (see module docstring).
        today: Override for the current date, useful in tests.

    Returns:
        Resolved datetime.date.

    Raises:
        DateParseError: if the string matches none of the supported patterns.
    """
    if today is None:
        today = datetime.date.today()

    text = text.strip().lower()

    bounds = _period_bounds(text, today)
    if bounds is not None:
        return bounds[0]

    m = _ISO_DATE.match(text)
    if m:
        try:
            return datetime.date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
        except ValueError as exc:
            raise DateParseError(f"Invalid calendar date: {text!r}") from exc

    m = _RELATIVE_OFFSET.match(text)
    if m:
        sign, magnitude_str, unit = m.groups()
        magnitude = int(magnitude_str)
        delta = magnitude if sign == "+" else -magnitude
        if unit == "d":
            return today + datetime.timedelta(days=delta)
        if unit == "w":
            return today + datetime.timedelta(weeks=delta)
        if unit == "m":
            return _add_months(today, delta)
        # unit == "y"
        return _add_months(today, delta * 12)

    raise DateParseError(f"Unrecognised date string: {text!r}")


def parse_date_range(
    from_text: str | None,
    to_text: str | None,
    today: datetime.date | None = None,
) -> tuple[datetime.date | None, datetime.date | None]:
    """Parse an optional date-from and date-to pair.

    A bounded calendar-period phrase (see _period_bounds — "last month",
    "q1", "ytd", "today", "september 2026", "2024-01", etc.) used in ONE
    field with the other field left entirely blank auto-fills that other
    bound from the same period, so e.g. Date From = "last month" alone
    resolves to the whole of last month (1st through last day), not an
    open-ended "from the 1st of last month onward" that silently includes
    everything since. Filling in both fields explicitly is never
    overridden — auto-fill only kicks in when the other field is blank. A
    relative offset ("-7d") or plain ISO date used alone stays open-ended,
    matching prior behaviour — those are single points in time, not spans
    with their own natural other end.

    Args:
        from_text: Start of range string, or None (no lower bound).
        to_text:   End of range string, or None (no upper bound).
        today:     Override for the current date, useful in tests.

    Returns:
        Tuple (date_from, date_to), either element may be None.

    Raises:
        DateParseError: if either non-None string fails to parse.
    """
    if today is None:
        today = datetime.date.today()

    from_bounds = _period_bounds(from_text, today) if from_text else None
    to_bounds = _period_bounds(to_text, today) if to_text else None

    date_from = from_bounds[0] if from_bounds is not None else (
        parse_date(from_text, today) if from_text else None
    )
    date_to = to_bounds[1] if to_bounds is not None else (
        parse_date(to_text, today) if to_text else None
    )

    if not to_text and from_bounds is not None:
        date_to = from_bounds[1]
    if not from_text and to_bounds is not None:
        date_from = to_bounds[0]

    return date_from, date_to
