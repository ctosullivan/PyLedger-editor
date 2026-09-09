"""Smart date parsing for the filter popup and transaction editing.

Supports:
  - ISO 8601 strings: "2024-01-15"
  - Named periods: "today", "yesterday", "last month", "last year"
  - Year-to-date: "ytd"
  - Quarter shorthands: "q1", "q2", "q3", "q4" (current year)
  - Relative offsets: "-7d", "-1m", "+1w"

Returns datetime.date objects. All parsing is relative to the date at call time
(i.e. datetime.date.today()), not a fixed session date.

parse_date_range() treats the named-period phrases above as bounded spans,
not just single points: "last month" alone in Date From auto-fills Date To
with the last day of that month, so the filter is confined to that month
rather than staying open-ended from its first day onward. See
_period_bounds() and parse_date_range()'s own docstring. A plain ISO date
or a relative offset ("-7d") stays open-ended when used alone — they're
single points in time with no separate "other end" of their own.
"""

from __future__ import annotations

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


def _add_months(d: datetime.date, months: int) -> datetime.date:
    """Return d shifted by `months`, clamping the day to the target month's length.

    Mirrors the month-end clamping convention used by the editor's own
    Shift+Up/Down date-field shifting (widgets/date_shift.py's
    _shift_date_str), for consistency: Jan 31 + 1 month → Feb 28/29, not an
    error and not silently rolling into March.
    """
    import calendar

    total = (d.year * 12 + d.month - 1) + months
    new_year, new_month0 = divmod(total, 12)
    new_month = new_month0 + 1
    max_day = calendar.monthrange(new_year, new_month)[1]
    return datetime.date(new_year, new_month, min(d.day, max_day))


def parse_date(text: str, today: datetime.date | None = None) -> datetime.date:
    """Parse a smart date string into a datetime.date.

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

    if text in ("today", "now"):
        return today

    if text == "yesterday":
        return today - datetime.timedelta(days=1)

    if text == "ytd":
        return datetime.date(today.year, 1, 1)

    if text == "last month":
        first_of_this_month = today.replace(day=1)
        return (first_of_this_month - datetime.timedelta(days=1)).replace(day=1)

    if text == "last year":
        return datetime.date(today.year - 1, 1, 1)

    m = _QUARTER.match(text)
    if m:
        quarter = int(m.group(1))
        start_month = (quarter - 1) * 3 + 1
        return datetime.date(today.year, start_month, 1)

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


def _period_bounds(
    text: str, today: datetime.date
) -> tuple[datetime.date, datetime.date] | None:
    """Return (start, end) if text is a bounded calendar-period phrase.

    A "period phrase" is a named span with a natural beginning and end —
    "last month", "last year", "q1".."q4", "today", "yesterday", "ytd".
    Returns None for anything that's a single point in time rather than a
    span: an ISO date, or a relative offset like "-7d" — those have no
    separate "end" distinct from the date itself, so the caller should keep
    using parse_date() for them (an open-ended bound is the correct/
    expected behaviour for "everything from 7 days ago onward").

    "ytd" is bounded by `today`, not December 31st — "year to date" means
    up to now, not the whole year (unlike "last year", which is complete).

    Used by parse_date_range() to auto-fill the *other* bound when only one
    smart-date field is given a period phrase and the other is left blank —
    see that function's docstring for the exact rule.
    """
    text = text.strip().lower()

    if text in ("today", "now"):
        return (today, today)

    if text == "yesterday":
        y = today - datetime.timedelta(days=1)
        return (y, y)

    if text == "ytd":
        return (datetime.date(today.year, 1, 1), today)

    if text == "last month":
        first_of_this_month = today.replace(day=1)
        last_month_end = first_of_this_month - datetime.timedelta(days=1)
        return (last_month_end.replace(day=1), last_month_end)

    if text == "last year":
        return (
            datetime.date(today.year - 1, 1, 1),
            datetime.date(today.year - 1, 12, 31),
        )

    m = _QUARTER.match(text)
    if m:
        import calendar

        quarter = int(m.group(1))
        start_month = (quarter - 1) * 3 + 1
        end_month = start_month + 2
        start = datetime.date(today.year, start_month, 1)
        end = datetime.date(
            today.year, end_month, calendar.monthrange(today.year, end_month)[1]
        )
        return (start, end)

    return None


def parse_date_range(
    from_text: str | None,
    to_text: str | None,
    today: datetime.date | None = None,
) -> tuple[datetime.date | None, datetime.date | None]:
    """Parse an optional date-from and date-to pair.

    A bounded calendar-period phrase (see _period_bounds — "last month",
    "q1", "ytd", "today", etc.) used in ONE field with the other field left
    entirely blank auto-fills that other bound from the same period, so
    e.g. Date From = "last month" alone resolves to the whole of last
    month (1st through last day), not an open-ended "from the 1st of last
    month onward" that silently includes everything since. Filling in both
    fields explicitly is never overridden — auto-fill only kicks in when
    the other field is blank. A relative offset ("-7d") or plain ISO date
    used alone stays open-ended, matching prior behaviour — those are
    single points in time, not spans with their own natural other end.

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
