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

    # TODO: implement relative offset parsing ("-7d", "+1m", "+1w")

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
