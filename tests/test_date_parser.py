"""Tests for ledger_editor.utils.date_parser."""

import datetime

import pytest

from ledger_editor.utils.date_parser import DateParseError, parse_date, parse_date_range

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


class TestParseDateRange:
    """Tests for parse_date_range()."""

    def test_both_none(self) -> None:
        assert parse_date_range(None, None, TODAY) == (None, None)

    def test_from_only(self) -> None:
        result = parse_date_range("2024-01-01", None, TODAY)
        assert result == (datetime.date(2024, 1, 1), None)

    def test_to_only(self) -> None:
        result = parse_date_range(None, "today", TODAY)
        assert result == (None, TODAY)

    def test_both_present(self) -> None:
        result = parse_date_range("2024-01-01", "2024-12-31", TODAY)
        assert result == (datetime.date(2024, 1, 1), datetime.date(2024, 12, 31))
