"""Tests for the date-shifting helpers in date_shift.py.

Covers _date_subfield_at_col (column-to-subfield mapping, now derived from
the date string's own layout rather than a fixed width), _normalize_date_str
(zero-padding an unpadded date), and _shift_date_str (arithmetic + separator
preservation), including overflow and edge cases.
"""
import pytest

from ledgerkit_editor.widgets.date_shift import (
    _date_subfield_at_col,
    _normalize_date_str,
    _shift_date_str,
)


# ---------------------------------------------------------------------------
# _date_subfield_at_col
# ---------------------------------------------------------------------------

class TestDateSubfieldAtCol:
    def test_year_cols(self):
        for col in range(4):
            assert _date_subfield_at_col("2024-01-15", col) == "year"

    def test_month_cols(self):
        for col in range(4, 7):
            assert _date_subfield_at_col("2024-01-15", col) == "month"

    def test_day_cols(self):
        for col in range(7, 10):
            assert _date_subfield_at_col("2024-01-15", col) == "day"

    def test_past_date_returns_none(self):
        for col in [10, 11, 20, 99]:
            assert _date_subfield_at_col("2024-01-15", col) is None

    def test_negative_col_returns_none(self):
        assert _date_subfield_at_col("2024-01-15", -1) is None

    def test_not_a_date_returns_none(self):
        assert _date_subfield_at_col("not-a-date", 0) is None

    # Unpadded dates: field boundaries shrink to match the actual layout.
    def test_unpadded_month_and_day(self):
        # "2026-9-1": year=0-3, sep=4, month=5, sep=6, day=7
        assert _date_subfield_at_col("2026-9-1", 0) == "year"
        assert _date_subfield_at_col("2026-9-1", 4) == "month"  # separator
        assert _date_subfield_at_col("2026-9-1", 5) == "month"
        assert _date_subfield_at_col("2026-9-1", 6) == "day"  # separator
        assert _date_subfield_at_col("2026-9-1", 7) == "day"
        assert _date_subfield_at_col("2026-9-1", 8) is None

    def test_unpadded_month_only(self):
        # "2026-9-01": year=0-3, sep=4, month=5, sep=6, day=7-8
        assert _date_subfield_at_col("2026-9-01", 5) == "month"
        assert _date_subfield_at_col("2026-9-01", 6) == "day"  # separator
        assert _date_subfield_at_col("2026-9-01", 8) == "day"
        assert _date_subfield_at_col("2026-9-01", 9) is None


# ---------------------------------------------------------------------------
# _normalize_date_str
# ---------------------------------------------------------------------------

class TestNormalizeDateStr:
    def test_pads_month_and_day(self):
        assert _normalize_date_str("2026-9-1") == "2026-09-01"

    def test_pads_month_only(self):
        assert _normalize_date_str("2026-9-15") == "2026-09-15"

    def test_pads_day_only(self):
        assert _normalize_date_str("2026-09-1") == "2026-09-01"

    def test_already_padded_unchanged(self):
        assert _normalize_date_str("2026-09-01") == "2026-09-01"

    def test_preserves_slash_separator(self):
        assert _normalize_date_str("2026/9/1") == "2026/09/01"

    def test_not_a_date_returned_unchanged(self):
        assert _normalize_date_str("not-a-date") == "not-a-date"


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

    def test_unpadded_input_produces_padded_output(self):
        # "2026-9-1" is not zero-padded; output must always be canonical.
        assert _shift_date_str("2026-9-1", "day", +1) == "2026-09-02"


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
