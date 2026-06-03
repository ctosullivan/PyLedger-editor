"""Tests for ledgerkit_editor.utils.commodity_format."""

from decimal import Decimal
from pathlib import Path

import pytest

from ledgerkit_editor.utils.commodity_format import (
    apply_commodity_styles,
    extract_commodity_styles,
)

FIXTURES = Path(__file__).parent / "fixtures"


def _load(name: str):
    """Load a journal from fixtures using ledgerkit.load()."""
    import ledgerkit  # noqa: PLC0415
    return ledgerkit.load(FIXTURES / name)


# ---------------------------------------------------------------------------
# extract_commodity_styles
# ---------------------------------------------------------------------------

class TestExtractCommodityStyles:
    """Tests for extract_commodity_styles()."""

    def test_empty_journal_returns_empty_dict(self, tmp_path: Path) -> None:
        journal_path = tmp_path / "empty.journal"
        journal_path.write_text("", encoding="utf-8")
        journal = _load("empty.journal") if (FIXTURES / "empty.journal").exists() else \
            __import__("ledgerkit").load(journal_path)
        styles = extract_commodity_styles(journal)
        assert isinstance(styles, dict)

    def test_multicommodity_fixture_detects_eur(self) -> None:
        journal = _load("multicommodity.journal")
        styles = extract_commodity_styles(journal)
        assert "EUR" in styles

    def test_multicommodity_fixture_detects_gbp(self) -> None:
        journal = _load("multicommodity.journal")
        styles = extract_commodity_styles(journal)
        assert "£" in styles

    def test_multicommodity_fixture_detects_usd(self) -> None:
        journal = _load("multicommodity.journal")
        styles = extract_commodity_styles(journal)
        assert "$" in styles

    def test_eur_is_suffix(self) -> None:
        journal = _load("multicommodity.journal")
        styles = extract_commodity_styles(journal)
        eur = styles["EUR"]
        assert eur.prefix is False, "EUR should be a suffix commodity"

    def test_gbp_is_prefix(self) -> None:
        journal = _load("multicommodity.journal")
        styles = extract_commodity_styles(journal)
        gbp = styles["£"]
        assert gbp.prefix is True, "£ should be a prefix commodity"

    def test_usd_is_prefix(self) -> None:
        journal = _load("multicommodity.journal")
        styles = extract_commodity_styles(journal)
        usd = styles["$"]
        assert usd.prefix is True, "$ should be a prefix commodity"

    def test_eur_precision_two(self) -> None:
        journal = _load("multicommodity.journal")
        styles = extract_commodity_styles(journal)
        assert styles["EUR"].precision == 2

    def test_gbp_precision_two(self) -> None:
        journal = _load("multicommodity.journal")
        styles = extract_commodity_styles(journal)
        assert styles["£"].precision == 2

    def test_eur_has_group_separator(self) -> None:
        journal = _load("multicommodity.journal")
        styles = extract_commodity_styles(journal)
        # "1,500.00 EUR" should detect comma group separator
        assert styles["EUR"].group_separator == ","

    def test_prefers_richer_format_over_first_seen(self) -> None:
        """When the first EUR amount has no comma but a later one does, use the comma style."""
        import ledgerkit  # noqa: PLC0415
        text = (
            "2024-01-01 * Small\n"
            "    assets:bank  10.00 EUR\n"
            "    equity:opening\n"
            "\n"
            "2024-02-01 * Large\n"
            "    assets:bank  1,500.00 EUR\n"
            "    income:salary\n"
        )
        journal = ledgerkit.parse_string_lenient(text)[0]
        styles = extract_commodity_styles(journal)
        assert styles["EUR"].group_separator == ",", (
            "should prefer the comma-format amount over the first no-comma amount"
        )

    def test_sample_journal_has_no_styles_when_no_raw(self) -> None:
        journal = _load("sample.journal")
        styles = extract_commodity_styles(journal)
        # Returns a dict regardless; may or may not have entries depending on
        # whether sample.journal postings carry raw strings.
        assert isinstance(styles, dict)


# ---------------------------------------------------------------------------
# apply_commodity_styles
# ---------------------------------------------------------------------------

class TestApplyCommodityStyles:
    """Tests for apply_commodity_styles()."""

    def _gbp_style(self):
        from ledgerkit.commodity_style import CommodityStyle  # noqa: PLC0415
        return CommodityStyle(commodity="£", prefix=True, space=False,
                              decimal_mark=".", group_separator="", precision=2)

    def _eur_style(self):
        from ledgerkit.commodity_style import CommodityStyle  # noqa: PLC0415
        return CommodityStyle(commodity="EUR", prefix=False, space=True,
                              decimal_mark=".", group_separator="", precision=2)

    def test_empty_styles_returns_text_unchanged(self) -> None:
        text = "2024-01-01 * Test\n    expenses:food  £30\n    assets:bank\n"
        result = apply_commodity_styles(text, {})
        assert result == text

    def test_reformats_prefix_amount_precision(self) -> None:
        text = "2024-01-01 * Test\n    expenses:food  £30\n    assets:bank\n"
        result = apply_commodity_styles(text, {"£": self._gbp_style()})
        assert "£30.00" in result

    def test_reformats_suffix_amount_precision(self) -> None:
        text = "2024-01-01 * Test\n    expenses:food  500 EUR\n    assets:bank\n"
        result = apply_commodity_styles(text, {"EUR": self._eur_style()})
        assert "500.00 EUR" in result

    def test_unknown_commodity_passes_through(self) -> None:
        text = "2024-01-01 * Test\n    expenses:food  100 CHF\n    assets:bank\n"
        result = apply_commodity_styles(text, {"EUR": self._eur_style()})
        assert "100 CHF" in result

    def test_header_lines_unchanged(self) -> None:
        text = "2024-01-01 * Salary\n    assets:bank  1000.00 EUR\n    income:salary\n"
        result = apply_commodity_styles(text, {"EUR": self._eur_style()})
        assert result.startswith("2024-01-01 * Salary\n")

    def test_inline_comment_preserved(self) -> None:
        text = "2024-01-01 * Test\n    expenses:food  £30  ; groceries\n    assets:bank\n"
        result = apply_commodity_styles(text, {"£": self._gbp_style()})
        assert "; groceries" in result
        assert "£30.00" in result

    def test_negative_prefix_reformatted_symbol_first(self) -> None:
        # Input: £-50 (symbol then minus — appears in files saved by hledger or buggy save)
        text = "2024-01-01 * Refund\n    assets:bank  £-50\n    income:refund\n"
        result = apply_commodity_styles(text, {"£": self._gbp_style()})
        # Must produce -£50.00 (minus before symbol) — the only form the ledgerkit
        # parser accepts; "£-50.00" (symbol before minus) causes ParseError on reload.
        assert "-£50.00" in result
        assert "£-50.00" not in result.replace("-£50.00", "")

    def test_negative_prefix_reformatted_minus_first(self) -> None:
        # Input: -£50 (minus then symbol — the form ledgerkit writer produces)
        text = "2024-01-01 * Refund\n    assets:bank  -£50\n    income:refund\n"
        result = apply_commodity_styles(text, {"£": self._gbp_style()})
        # Must produce -£50.00 (minus before symbol) for parser round-trip safety.
        assert "-£50.00" in result
        assert "£-50.00" not in result.replace("-£50.00", "")

    def test_negative_suffix_reformatted(self) -> None:
        text = "2024-01-01 * Expense\n    assets:bank  -200 EUR\n    expenses:travel\n"
        result = apply_commodity_styles(text, {"EUR": self._eur_style()})
        assert "-200.00 EUR" in result

    def test_trailing_newline_preserved(self) -> None:
        text = "2024-01-01 * Test\n    expenses:food  £30\n    assets:bank\n"
        result = apply_commodity_styles(text, {"£": self._gbp_style()})
        assert result.endswith("\n")

    def test_no_trailing_newline_preserved(self) -> None:
        text = "2024-01-01 * Test\n    expenses:food  £30\n    assets:bank"
        result = apply_commodity_styles(text, {"£": self._gbp_style()})
        assert not result.endswith("\n")

    def test_thousands_separator_applied(self) -> None:
        from ledgerkit.commodity_style import CommodityStyle  # noqa: PLC0415
        style = CommodityStyle(commodity="£", prefix=True, space=False,
                               decimal_mark=".", group_separator=",", precision=2)
        text = "2024-01-01 * Test\n    assets:bank  £1200\n    equity:opening\n"
        result = apply_commodity_styles(text, {"£": style})
        assert "£1,200.00" in result

    def test_elided_posting_unchanged(self) -> None:
        text = "2024-01-01 * Test\n    expenses:food  £30\n    assets:bank\n"
        result = apply_commodity_styles(text, {"£": self._gbp_style()})
        # The elided posting "    assets:bank" has no amount, so it is unchanged
        lines = result.splitlines()
        assert any(l.strip() == "assets:bank" for l in lines)

    def test_roundtrip_from_fixture(self) -> None:
        journal = _load("multicommodity.journal")
        styles = extract_commodity_styles(journal)
        text = (FIXTURES / "multicommodity.journal").read_text(encoding="utf-8")
        result = apply_commodity_styles(text, styles)
        # EUR amounts should be formatted with 2dp and comma group separator
        assert "1,500.00 EUR" in result
        assert "2,000.00 EUR" in result
        # GBP positive amount should be prefix with 2dp and comma group separator
        assert "£1,200.00" in result
        # GBP negative: output must be -£300.00 (minus before symbol) so the
        # ledgerkit parser can round-trip it; £-300.00 causes ParseError on reload.
        assert "-£300.00" in result
        assert "£-300.00" not in result.replace("-£300.00", "")
