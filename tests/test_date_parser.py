"""Tests for ledgerkit_editor.utils.date_parser."""

import datetime

import pytest

from ledgerkit_editor.utils.date_parser import DateParseError, parse_date, parse_date_range

TODAY = datetime.date(2024, 6, 15)


class TestParseDate:
    """Tests for parse_date()."""

    def test_today(self) -> None:
        assert parse_date("today", TODAY) == TODAY

    def test_now_alias(self) -> None:
        assert parse_date("now", TODAY) == TODAY

    def test_yesterday(self) -> None:
        assert parse_date("yesterday", TODAY) == datetime.date(2024, 6, 14)

    def test_ytd(self) -> None:
        assert parse_date("ytd", TODAY) == datetime.date(2024, 1, 1)

    def test_last_month(self) -> None:
        assert parse_date("last month", TODAY) == datetime.date(2024, 5, 1)

    def test_last_month_january(self) -> None:
        jan15 = datetime.date(2024, 1, 15)
        assert parse_date("last month", jan15) == datetime.date(2023, 12, 1)

    def test_last_year(self) -> None:
        assert parse_date("last year", TODAY) == datetime.date(2023, 1, 1)

    def test_this_year(self) -> None:
        assert parse_date("this year", TODAY) == datetime.date(2024, 1, 1)

    def test_this_week(self) -> None:
        # TODAY = 2024-06-15 (Saturday); week starts Monday 2024-06-10.
        assert parse_date("this week", TODAY) == datetime.date(2024, 6, 10)

    def test_last_week(self) -> None:
        assert parse_date("last week", TODAY) == datetime.date(2024, 6, 3)

    def test_this_month(self) -> None:
        assert parse_date("this month", TODAY) == datetime.date(2024, 6, 1)

    def test_year_month_shorthand(self) -> None:
        assert parse_date("2026-02", TODAY) == datetime.date(2026, 2, 1)

    def test_year_month_shorthand_unpadded(self) -> None:
        assert parse_date("2026-2", TODAY) == datetime.date(2026, 2, 1)

    def test_month_name_with_year(self) -> None:
        assert parse_date("september 2026", TODAY) == datetime.date(2026, 9, 1)

    def test_month_name_abbreviation_with_year(self) -> None:
        assert parse_date("sep 2026", TODAY) == datetime.date(2026, 9, 1)

    def test_month_name_bare_defaults_to_current_year(self) -> None:
        assert parse_date("september", TODAY) == datetime.date(2024, 9, 1)

    def test_month_name_case_insensitive(self) -> None:
        assert parse_date("September 2026", TODAY) == datetime.date(2026, 9, 1)

    def test_unknown_month_name_raises(self) -> None:
        with pytest.raises(DateParseError):
            parse_date("smarch 2026", TODAY)

    def test_quarter_q1(self) -> None:
        assert parse_date("q1", TODAY) == datetime.date(2024, 1, 1)

    def test_quarter_q2(self) -> None:
        assert parse_date("q2", TODAY) == datetime.date(2024, 4, 1)

    def test_quarter_q3(self) -> None:
        assert parse_date("q3", TODAY) == datetime.date(2024, 7, 1)

    def test_quarter_q4(self) -> None:
        assert parse_date("q4", TODAY) == datetime.date(2024, 10, 1)

    def test_iso_date(self) -> None:
        assert parse_date("2024-03-22", TODAY) == datetime.date(2024, 3, 22)

    def test_whitespace_stripped(self) -> None:
        assert parse_date("  today  ", TODAY) == TODAY

    def test_case_insensitive(self) -> None:
        assert parse_date("TODAY", TODAY) == TODAY

    def test_unknown_string_raises(self) -> None:
        with pytest.raises(DateParseError):
            parse_date("next week", TODAY)

    def test_invalid_iso_calendar_raises(self) -> None:
        with pytest.raises(DateParseError):
            parse_date("2024-02-30", TODAY)


class TestParseDateRelativeOffset:
    """Tests for the "-7d" / "+1m" / "+2w" / "-1y" relative offset grammar."""

    def test_days_back(self) -> None:
        assert parse_date("-7d", TODAY) == datetime.date(2024, 6, 8)

    def test_days_forward(self) -> None:
        assert parse_date("+7d", TODAY) == datetime.date(2024, 6, 22)

    def test_multi_digit_magnitude(self) -> None:
        assert parse_date("-30d", TODAY) == datetime.date(2024, 5, 16)

    def test_weeks_forward(self) -> None:
        assert parse_date("+1w", TODAY) == datetime.date(2024, 6, 22)

    def test_weeks_back(self) -> None:
        assert parse_date("-2w", TODAY) == datetime.date(2024, 6, 1)

    def test_months_back(self) -> None:
        assert parse_date("-1m", TODAY) == datetime.date(2024, 5, 15)

    def test_months_forward(self) -> None:
        assert parse_date("+2m", TODAY) == datetime.date(2024, 8, 15)

    def test_years_forward(self) -> None:
        assert parse_date("+1y", TODAY) == datetime.date(2025, 6, 15)

    def test_years_back(self) -> None:
        assert parse_date("-1y", TODAY) == datetime.date(2023, 6, 15)

    def test_zero_magnitude_is_today(self) -> None:
        assert parse_date("+0d", TODAY) == TODAY

    def test_month_end_clamp_non_leap(self) -> None:
        # Jan 31 + 1 month -> Feb 28 (2023 is not a leap year)
        assert parse_date("+1m", datetime.date(2023, 1, 31)) == datetime.date(2023, 2, 28)

    def test_month_end_clamp_leap(self) -> None:
        # Jan 31 + 1 month -> Feb 29 (2024 is a leap year)
        assert parse_date("+1m", datetime.date(2024, 1, 31)) == datetime.date(2024, 2, 29)

    def test_uppercase_unit_matches(self) -> None:
        # parse_date() lowercases the full input before this grammar is tried.
        assert parse_date("+1M", TODAY) == datetime.date(2024, 7, 15)

    def test_combined_units_not_supported(self) -> None:
        with pytest.raises(DateParseError):
            parse_date("-1m2d", TODAY)


class TestParseDateRange:
    """Tests for parse_date_range()."""

    def test_both_none(self) -> None:
        assert parse_date_range(None, None, TODAY) == (None, None)

    def test_from_only_iso_date_stays_open_ended(self) -> None:
        # A plain ISO date is a single point, not a period — no auto-fill.
        result = parse_date_range("2024-01-01", None, TODAY)
        assert result == (datetime.date(2024, 1, 1), None)

    def test_to_only_iso_date_stays_open_ended(self) -> None:
        result = parse_date_range(None, "2024-12-31", TODAY)
        assert result == (None, datetime.date(2024, 12, 31))

    def test_from_only_relative_offset_stays_open_ended(self) -> None:
        # A relative offset is also a single point, not a period.
        result = parse_date_range("-7d", None, TODAY)
        assert result == (TODAY - datetime.timedelta(days=7), None)

    def test_both_present(self) -> None:
        result = parse_date_range("2024-01-01", "2024-12-31", TODAY)
        assert result == (datetime.date(2024, 1, 1), datetime.date(2024, 12, 31))


class TestParseDateRangePeriodAutoFill:
    """A bounded period phrase ("last month", "today", "q1", "ytd", ...)
    used alone auto-fills the other bound with that same period's other
    end, rather than staying open — see _period_bounds()."""

    def test_from_only_today_becomes_just_today(self) -> None:
        result = parse_date_range("today", None, TODAY)
        assert result == (TODAY, TODAY)

    def test_to_only_today_becomes_just_today(self) -> None:
        # Symmetric: a period phrase in the "to" field auto-fills "from"
        # with the period's start, not just its own (start-based) value.
        result = parse_date_range(None, "today", TODAY)
        assert result == (TODAY, TODAY)

    def test_from_only_yesterday(self) -> None:
        y = TODAY - datetime.timedelta(days=1)
        assert parse_date_range("yesterday", None, TODAY) == (y, y)

    def test_from_only_last_month_bounded_to_that_month(self) -> None:
        # TODAY = 2024-06-15 -> last month = May 2024, whole month.
        result = parse_date_range("last month", None, TODAY)
        assert result == (datetime.date(2024, 5, 1), datetime.date(2024, 5, 31))

    def test_to_only_last_month_bounded_to_that_month(self) -> None:
        result = parse_date_range(None, "last month", TODAY)
        assert result == (datetime.date(2024, 5, 1), datetime.date(2024, 5, 31))

    def test_from_only_last_year_bounded_to_that_year(self) -> None:
        result = parse_date_range("last year", None, TODAY)
        assert result == (datetime.date(2023, 1, 1), datetime.date(2023, 12, 31))

    def test_from_only_quarter_bounded_to_that_quarter(self) -> None:
        # TODAY's year = 2024; q1 = Jan-Mar.
        result = parse_date_range("q1", None, TODAY)
        assert result == (datetime.date(2024, 1, 1), datetime.date(2024, 3, 31))

    def test_from_only_q4_bounded_correctly(self) -> None:
        result = parse_date_range("q4", None, TODAY)
        assert result == (datetime.date(2024, 10, 1), datetime.date(2024, 12, 31))

    def test_from_only_ytd_bounded_by_today_not_year_end(self) -> None:
        # "year to date" means up to now, not through Dec 31.
        result = parse_date_range("ytd", None, TODAY)
        assert result == (datetime.date(2024, 1, 1), TODAY)

    def test_explicit_both_fields_not_overridden(self) -> None:
        # Auto-fill only kicks in when the OTHER field is blank.
        result = parse_date_range("last month", "today", TODAY)
        assert result == (datetime.date(2024, 5, 1), TODAY)

    def test_month_boundary_across_year_change(self) -> None:
        jan_today = datetime.date(2024, 1, 15)
        result = parse_date_range("last month", None, jan_today)
        assert result == (datetime.date(2023, 12, 1), datetime.date(2023, 12, 31))

    def test_from_only_this_week_bounded_to_that_week(self) -> None:
        result = parse_date_range("this week", None, TODAY)
        assert result == (datetime.date(2024, 6, 10), datetime.date(2024, 6, 16))

    def test_from_only_last_week_bounded_to_that_week(self) -> None:
        result = parse_date_range("last week", None, TODAY)
        assert result == (datetime.date(2024, 6, 3), datetime.date(2024, 6, 9))

    def test_from_only_this_month_bounded_to_that_month(self) -> None:
        result = parse_date_range("this month", None, TODAY)
        assert result == (datetime.date(2024, 6, 1), datetime.date(2024, 6, 30))

    def test_from_only_this_year_bounded_to_that_year(self) -> None:
        result = parse_date_range("this year", None, TODAY)
        assert result == (datetime.date(2024, 1, 1), datetime.date(2024, 12, 31))

    def test_from_only_year_month_shorthand_bounded(self) -> None:
        result = parse_date_range("2026-02", None, TODAY)
        assert result == (datetime.date(2026, 2, 1), datetime.date(2026, 2, 28))

    def test_to_only_year_month_shorthand_bounded(self) -> None:
        result = parse_date_range(None, "2026-02", TODAY)
        assert result == (datetime.date(2026, 2, 1), datetime.date(2026, 2, 28))

    def test_from_only_month_name_with_year_bounded(self) -> None:
        result = parse_date_range("september 2026", None, TODAY)
        assert result == (datetime.date(2026, 9, 1), datetime.date(2026, 9, 30))

    def test_from_only_bare_month_name_bounded_to_current_year(self) -> None:
        result = parse_date_range("december", None, TODAY)
        assert result == (datetime.date(2024, 12, 1), datetime.date(2024, 12, 31))

    def test_leap_year_february_bounded_correctly(self) -> None:
        result = parse_date_range("2024-02", None, TODAY)
        assert result == (datetime.date(2024, 2, 1), datetime.date(2024, 2, 29))
