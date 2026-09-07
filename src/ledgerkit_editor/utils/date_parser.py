"""Smart date parsing for the filter popup and transaction editing.

Supports:
  - ISO 8601 strings: "2024-01-15"
  - Named periods: "today", "yesterday", "last month", "last year"
  - Year-to-date: "ytd"
  - Quarter shorthands: "q1", "q2", "q3", "q4" (current year)
  - Relative offsets: "-7d", "-1m", "+1w"

Returns datetime.date objects. All parsing is relative to the date at call time
(i.e. datetime.date.today()), not a fixed session date.
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

    m = re.match(r"^q([1-4])$", text)
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


def parse_date_range(
    from_text: str | None,
    to_text: str | None,
    today: datetime.date | None = None,
) -> tuple[datetime.date | None, datetime.date | None]:
    """Parse an optional date-from and date-to pair.

    Args:
        from_text: Start of range string, or None (no lower bound).
        to_text:   End of range string, or None (no upper bound).
        today:     Override for the current date, useful in tests.

    Returns:
        Tuple (date_from, date_to), either element may be None.

    Raises:
        DateParseError: if either non-None string fails to parse.
    """
    date_from = parse_date(from_text, today) if from_text else None
    date_to = parse_date(to_text, today) if to_text else None
    return date_from, date_to
