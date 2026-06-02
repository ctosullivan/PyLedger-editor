"""Tests for the date-shifting helpers in transaction_table.py.

Covers _date_subfield_at_col (column-to-subfield mapping) and _shift_date_str
(arithmetic + separator preservation), including overflow and edge cases.
"""
import pytest

from ledgerkit_editor.widgets.transaction_table import (
    _date_subfield_at_col,
    _shift_date_str,
)


# ---------------------------------------------------------------------------
# _date_subfield_at_col
# ---------------------------------------------------------------------------

class TestDateSubfieldAtCol:
    def test_year_cols(self):
        for col in range(4):
            assert _date_subfield_at_col(col) == "year"

    def test_month_cols(self):
        for col in range(4, 7):
            assert _date_subfield_at_col(col) == "month"

    def test_day_cols(self):
        for col in range(7, 10):
            assert _date_subfield_at_col(col) == "day"

    def test_past_date_returns_none(self):
        for col in [10, 11, 20, 99]:
            assert _date_subfield_at_col(col) is None


# ---------------------------------------------------------------------------
# _shift_date_str — day shifts
# ---------------------------------------------------------------------------

class TestShiftDay:
    def test_increment_normal(self):
        assert _shift_date_str("2024-01-15", "day", +1) == "2024-01-16"

    def test_decrement_normal(self):
        assert _shift_date_str("2024-01-15", "day", -1) == "2024-01-14"

    def test_month_overflow(self):
        assert _shift_date_str("2024-01-31", "day", +1) == "2024-02-01"

    def test_year_overflow(self):
        assert _shift_date_str("2024-12-31", "day", +1) == "2025-01-01"

    def test_year_underflow(self):
        assert _shift_date_str("2024-01-01", "day", -1) == "2023-12-31"

    def test_separator_slash_preserved(self):
        assert _shift_date_str("2024/01/15", "day", +1) == "2024/01/16"


# ---------------------------------------------------------------------------
# _shift_date_str — month shifts
# ---------------------------------------------------------------------------

class TestShiftMonth:
    def test_increment_normal(self):
        assert _shift_date_str("2024-03-10", "month", +1) == "2024-04-10"

    def test_decrement_normal(self):
        assert _shift_date_str("2024-03-10", "month", -1) == "2024-02-10"

    def test_december_rollover(self):
        assert _shift_date_str("2024-12-10", "month", +1) == "2025-01-10"

    def test_january_underflow(self):
        assert _shift_date_str("2024-01-10", "month", -1) == "2023-12-10"

    def test_month_end_clamp_feb_non_leap(self):
        # Jan 31 + 1 month → Feb 28 (2023 is not a leap year)
        assert _shift_date_str("2023-01-31", "month", +1) == "2023-02-28"

    def test_month_end_clamp_feb_leap(self):
        # Jan 31 + 1 month → Feb 29 (2024 is a leap year)
        assert _shift_date_str("2024-01-31", "month", +1) == "2024-02-29"

    def test_month_end_clamp_30_day_month(self):
        # March 31 + 1 month → April 30
        assert _shift_date_str("2024-03-31", "month", +1) == "2024-04-30"

    def test_separator_slash_preserved(self):
        assert _shift_date_str("2024/03/10", "month", +1) == "2024/04/10"


# ---------------------------------------------------------------------------
# _shift_date_str — year shifts
# ---------------------------------------------------------------------------

class TestShiftYear:
    def test_increment_normal(self):
        assert _shift_date_str("2024-06-15", "year", +1) == "2025-06-15"

    def test_decrement_normal(self):
        assert _shift_date_str("2024-06-15", "year", -1) == "2023-06-15"

    def test_leap_day_clamp_to_non_leap(self):
        # Feb 29 on leap year → Feb 28 on non-leap year
        assert _shift_date_str("2024-02-29", "year", +1) == "2025-02-28"

    def test_leap_day_to_leap_year(self):
        # Feb 29 on 2024 → Feb 29 on 2028 (both leap)
        assert _shift_date_str("2024-02-29", "year", +4) == "2028-02-29"

    def test_separator_slash_preserved(self):
        assert _shift_date_str("2024/06/15", "year", +1) == "2025/06/15"
