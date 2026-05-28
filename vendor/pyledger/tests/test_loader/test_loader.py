"""Tests for PyLedger.loader — load_journal, include directive, merge_journals."""

import os
import pathlib
import tempfile
import textwrap
import unittest

from PyLedger.loader import load_journal, merge_journals
from PyLedger.parser import ParseError

FIXTURES = pathlib.Path(__file__).parent.parent / "fixtures"
SAMPLE_JOURNAL = FIXTURES / "sample.journal"


def _write_temp(content: str, suffix: str = ".journal") -> pathlib.Path:
    """Write content to a named temp file and return its Path (caller must delete)."""
    f = tempfile.NamedTemporaryFile(
        suffix=suffix, mode="w", encoding="utf-8", delete=False
    )
    f.write(content)
    f.close()
    return pathlib.Path(f.name)


class TestLoadJournalBasic(unittest.TestCase):
    """Basic load_journal behaviour on flat files with no includes."""

    def test_loads_sample_journal(self):
        j = load_journal(SAMPLE_JOURNAL)
        self.assertEqual(len(j.transactions), 5)
        self.assertEqual(j.included_files, 0)

    def test_returns_journal_type(self):
        from PyLedger.models import Journal
        j = load_journal(SAMPLE_JOURNAL)
        self.assertIsInstance(j, Journal)

    def test_source_file_is_set(self):
        j = load_journal(SAMPLE_JOURNAL)
        self.assertIsNotNone(j.source_file)

    def test_source_file_is_absolute(self):
        j = load_journal(SAMPLE_JOURNAL)
        self.assertTrue(pathlib.Path(j.source_file).is_absolute())

    def test_source_file_matches_root(self):
        j = load_journal(SAMPLE_JOURNAL)
        self.assertEqual(pathlib.Path(j.source_file), SAMPLE_JOURNAL.resolve())

    def test_file_not_found_raises(self):
        with self.assertRaises(FileNotFoundError):
            load_journal(FIXTURES / "nonexistent.journal")

    def test_csv_extension_raises(self):
        with self.assertRaises(ParseError) as ctx:
            load_journal("myfile.csv")
        self.assertIn("unsupported file format", str(ctx.exception))

    def test_timeclock_extension_raises(self):
        with self.assertRaises(ParseError) as ctx:
            load_journal("myfile.timeclock")
        self.assertIn("unsupported file format", str(ctx.exception))

    def test_j_alias_raises(self):
        """hledger accepts .j as a journal alias; PyLedger v1 does not."""
        with self.assertRaises(ParseError) as ctx:
            load_journal("myfile.j")
        self.assertIn("unsupported file format", str(ctx.exception))

    def test_journal_extension_accepted(self):
        load_journal(SAMPLE_JOURNAL)

    def test_ledger_extension_accepted(self):
        content = textwrap.dedent("""\
            2024-01-05 Salary
                assets:bank  £100.00
                income:salary  -£100.00
        """)
        tmp = _write_temp(content, suffix=".ledger")
        try:
            j = load_journal(tmp)
            self.assertEqual(len(j.transactions), 1)
        finally:
            os.unlink(tmp)

    def test_accepts_pathlike(self):
        j = load_journal(str(SAMPLE_JOURNAL))
        self.assertEqual(len(j.transactions), 5)


class TestIncludeBasic(unittest.TestCase):
    """include directive — basic single-level include."""

    def test_include_relative_path(self):
        j = load_journal(FIXTURES / "root_with_include.journal")
        self.assertEqual(len(j.transactions), 2)

    def test_included_files_count_one(self):
        j = load_journal(FIXTURES / "root_with_include.journal")
        self.assertEqual(j.included_files, 1)

    def test_transactions_from_both_files_present(self):
        j = load_journal(FIXTURES / "root_with_include.journal")
        descriptions = [t.description for t in j.transactions]
        self.assertIn("Root transaction", descriptions)
        self.assertIn("Included transaction", descriptions)

    def test_include_does_not_duplicate_root_transactions(self):
        j = load_journal(FIXTURES / "root_with_include.journal")
        root_txns = [t for t in j.transactions if t.description == "Root transaction"]
        self.assertEqual(len(root_txns), 1)

    def test_source_file_is_root_file(self):
        j = load_journal(FIXTURES / "root_with_include.journal")
        expected = (FIXTURES / "root_with_include.journal").resolve()
        self.assertEqual(pathlib.Path(j.source_file), expected)

    def test_include_absolute_path(self):
        included = _write_temp(textwrap.dedent("""\
            2024-06-01 Absolute included
                assets:bank  £10.00
                income:other  -£10.00
        """))
        root = _write_temp(
            f"include {included}\n\n"
            "2024-06-02 Root txn\n"
            "    assets:bank  £5.00\n"
            "    income:other  -£5.00\n"
        )
        try:
            j = load_journal(root)
            self.assertEqual(len(j.transactions), 2)
            self.assertEqual(j.included_files, 1)
        finally:
            os.unlink(str(included))
            os.unlink(str(root))


class TestIncludeRecursive(unittest.TestCase):
    """include directive — recursive / nested includes."""

    def test_nested_three_levels(self):
        j = load_journal(FIXTURES / "nested_a.journal")
        self.assertEqual(len(j.transactions), 3)

    def test_included_files_count_nested(self):
        j = load_journal(FIXTURES / "nested_a.journal")
        self.assertEqual(j.included_files, 2)

    def test_ordering_preserved(self):
        # includes are at the top of each fixture file, so included content
        # appears before each file's own transactions: C then B then A
        j = load_journal(FIXTURES / "nested_a.journal")
        descriptions = [t.description for t in j.transactions]
        self.assertEqual(descriptions, [
            "Nested C transaction",
            "Nested B transaction",
            "Nested A transaction",
        ])

    def test_include_at_top_of_file(self):
        included = _write_temp(
            "2024-07-01 First\n    assets:bank  £1.00\n    income:other  -£1.00\n"
        )
        root = _write_temp(
            f"include {included}\n"
            "2024-07-02 Second\n    assets:bank  £2.00\n    income:other  -£2.00\n"
        )
        try:
            j = load_journal(root)
            self.assertEqual(j.transactions[0].description, "First")
            self.assertEqual(j.transactions[1].description, "Second")
        finally:
            os.unlink(str(included))
            os.unlink(str(root))

    def test_include_at_end_of_file(self):
        included = _write_temp(
            "2024-07-02 Last\n    assets:bank  £2.00\n    income:other  -£2.00\n"
        )
        root = _write_temp(
            "2024-07-01 First\n    assets:bank  £1.00\n    income:other  -£1.00\n"
            f"\ninclude {included}\n"
        )
        try:
            j = load_journal(root)
            self.assertEqual(j.transactions[-1].description, "Last")
        finally:
            os.unlink(str(included))
            os.unlink(str(root))


class TestIncludeGlob(unittest.TestCase):
    """include directive — glob pattern expansion."""

    def test_glob_star_matches_multiple_files(self):
        j = load_journal(FIXTURES / "root_with_glob.journal")
        self.assertEqual(len(j.transactions), 2)

    def test_included_files_count_from_glob(self):
        j = load_journal(FIXTURES / "root_with_glob.journal")
        self.assertEqual(j.included_files, 2)

    def test_glob_question_mark(self):
        j = load_journal(FIXTURES / "root_with_glob.journal")
        descriptions = {t.description for t in j.transactions}
        self.assertIn("Glob one transaction", descriptions)
        self.assertIn("Glob two transaction", descriptions)

    def test_glob_no_matches_raises(self):
        root = _write_temp("include no_match_at_all_*.journal\n")
        try:
            with self.assertRaises(ParseError) as ctx:
                load_journal(root)
            self.assertIn("no files matched", str(ctx.exception))
        finally:
            os.unlink(str(root))

    def test_glob_excludes_current_file(self):
        # root_with_glob.journal pattern "glob_*.journal" should not match
        # itself (it doesn't start with "glob_"), but this test confirms the
        # loader never includes the root file even if a glob would match it.
        tmp = _write_temp(
            "2024-08-01 Self txn\n    assets:bank  £1.00\n    income:other  -£1.00\n",
            suffix=".journal",
        )
        # Build a root that globs for its own name pattern; since it's a temp
        # file with a random name, just verify included_files doesn't count self.
        tmp_dir = tmp.parent
        tmp_name = tmp.name
        root_content = f"include {tmp_name}\n"
        root = tmp_dir / ("root_" + tmp_name)
        root.write_text(root_content, encoding="utf-8")
        try:
            j = load_journal(root)
            # The included file (tmp) is separate from root — it should be counted once.
            self.assertEqual(j.included_files, 1)
        finally:
            os.unlink(str(tmp))
            os.unlink(str(root))


class TestIncludePathResolution(unittest.TestCase):
    """include directive — path resolution (relative, absolute, tilde)."""

    def test_relative_resolves_to_containing_dir(self):
        # Create a subdirectory structure: tmpdir/sub/a.journal → ../b.journal
        with tempfile.TemporaryDirectory() as tmpdir:
            sub = pathlib.Path(tmpdir) / "sub"
            sub.mkdir()
            b = pathlib.Path(tmpdir) / "b.journal"
            b.write_text(
                "2024-09-02 B txn\n    assets:bank  £2.00\n    income:other  -£2.00\n",
                encoding="utf-8",
            )
            a = sub / "a.journal"
            a.write_text(
                "include ../b.journal\n"
                "2024-09-01 A txn\n    assets:bank  £1.00\n    income:other  -£1.00\n",
                encoding="utf-8",
            )
            j = load_journal(a)
            descriptions = [t.description for t in j.transactions]
            self.assertIn("B txn", descriptions)
            self.assertIn("A txn", descriptions)

    def test_absolute_path_works(self):
        included = _write_temp(
            "2024-09-10 Absolute\n    assets:bank  £5.00\n    income:other  -£5.00\n"
        )
        root = _write_temp(f"include {included.resolve()}\n")
        try:
            j = load_journal(root)
            self.assertEqual(j.transactions[0].description, "Absolute")
        finally:
            os.unlink(str(included))
            os.unlink(str(root))


class TestIncludeErrors(unittest.TestCase):
    """include directive — error cases."""

    def test_circular_include_raises(self):
        with self.assertRaises(ParseError) as ctx:
            load_journal(FIXTURES / "circular_a.journal")
        self.assertIn("circular", str(ctx.exception).lower())

    def test_unsupported_extension_in_include_raises(self):
        root = _write_temp("include somefile.csv\n")
        try:
            with self.assertRaises(ParseError) as ctx:
                load_journal(root)
            self.assertIn("unsupported file format", str(ctx.exception))
        finally:
            os.unlink(str(root))

    def test_format_prefix_raises(self):
        root = _write_temp("include timedot:notes.journal\n")
        try:
            with self.assertRaises(ParseError) as ctx:
                load_journal(root)
            self.assertIn("format prefix", str(ctx.exception))
        finally:
            os.unlink(str(root))

    def test_format_prefix_csv_raises(self):
        root = _write_temp("include csv:data.journal\n")
        try:
            with self.assertRaises(ParseError) as ctx:
                load_journal(root)
            self.assertIn("format prefix", str(ctx.exception))
        finally:
            os.unlink(str(root))

    def test_included_file_not_found_raises(self):
        root = _write_temp("include ghost_nonexistent_file.journal\n")
        try:
            with self.assertRaises((FileNotFoundError, ParseError)):
                load_journal(root)
        finally:
            os.unlink(str(root))

    def test_parse_error_attributes_to_included_file(self):
        # Included file contains a malformed transaction (missing postings).
        broken = _write_temp(
            "not a valid journal line\n"
            "2024-10-01 Bad txn\n"
        )
        root = _write_temp(f"include {broken}\n")
        try:
            # parse_string silently skips unknown top-level lines,
            # so use a definitely-broken posting to trigger ParseError.
            broken.write_text(
                "2024-10-01 Bad txn\n"
                "    assets:bank  £10.00\n"
                "    TOOOMANY  POSTING  COLUMNS\n",
                encoding="utf-8",
            )
            with self.assertRaises(ParseError) as ctx:
                load_journal(root)
            err = str(ctx.exception)
            self.assertIn(str(broken.name), err)
        finally:
            os.unlink(str(broken))
            os.unlink(str(root))


class TestMergeJournals(unittest.TestCase):
    """merge_journals — combining multiple Journal objects."""

    def _make_journal(self, descriptions, source_file=None, included_files=0):
        from PyLedger.parser import parse_string
        lines = []
        for i, desc in enumerate(descriptions, 1):
            lines.append(f"2024-0{i}-01 {desc}")
            lines.append("    assets:bank  £1.00")
            lines.append("    income:other  -£1.00")
            lines.append("")
        j = parse_string("\n".join(lines))
        j.source_file = source_file
        j.included_files = included_files
        return j

    def test_merge_single_journal(self):
        j = self._make_journal(["Alpha"])
        result = merge_journals([j])
        self.assertIs(result, j)

    def test_merge_empty_raises(self):
        with self.assertRaises(ValueError):
            merge_journals([])

    def test_merge_two_journals_transaction_count(self):
        j1 = self._make_journal(["Alpha", "Beta"])
        j2 = self._make_journal(["Gamma"])
        result = merge_journals([j1, j2])
        self.assertEqual(len(result.transactions), 3)

    def test_merge_transaction_order_preserved(self):
        j1 = self._make_journal(["Alpha", "Beta"])
        j2 = self._make_journal(["Gamma"])
        result = merge_journals([j1, j2])
        descs = [t.description for t in result.transactions]
        self.assertEqual(descs, ["Alpha", "Beta", "Gamma"])

    def test_merge_source_file_is_first(self):
        j1 = self._make_journal(["A"], source_file="/path/to/first.journal")
        j2 = self._make_journal(["B"], source_file="/path/to/second.journal")
        result = merge_journals([j1, j2])
        self.assertEqual(result.source_file, "/path/to/first.journal")

    def test_merge_included_files_summed(self):
        j1 = self._make_journal(["A"], included_files=2)
        j2 = self._make_journal(["B"], included_files=1)
        result = merge_journals([j1, j2])
        self.assertEqual(result.included_files, 3)

    def test_merge_prices_combined(self):
        from PyLedger.models import Journal, PriceDirective, Amount
        from decimal import Decimal
        import datetime
        price1 = PriceDirective(
            date=datetime.date(2024, 1, 1),
            commodity="AAPL",
            price=Amount(Decimal("100.00"), "$"),
        )
        price2 = PriceDirective(
            date=datetime.date(2024, 2, 1),
            commodity="AAPL",
            price=Amount(Decimal("110.00"), "$"),
        )
        j1 = Journal(transactions=[], prices=[price1])
        j2 = Journal(transactions=[], prices=[price2])
        result = merge_journals([j1, j2])
        self.assertEqual(len(result.prices), 2)

    def test_merge_three_journals(self):
        j1 = self._make_journal(["A"])
        j2 = self._make_journal(["B"])
        j3 = self._make_journal(["C"])
        result = merge_journals([j1, j2, j3])
        self.assertEqual(len(result.transactions), 3)
        descs = [t.description for t in result.transactions]
        self.assertEqual(descs, ["A", "B", "C"])

    def test_merge_with_real_files(self):
        j1 = load_journal(SAMPLE_JOURNAL)
        j2 = load_journal(FIXTURES / "root_with_include.journal")
        result = merge_journals([j1, j2])
        self.assertEqual(
            len(result.transactions),
            len(j1.transactions) + len(j2.transactions),
        )


class TestStatsIntegration(unittest.TestCase):
    """included_files propagates correctly to JournalStats."""

    def test_stats_included_files_zero_flat_file(self):
        j = load_journal(SAMPLE_JOURNAL)
        self.assertEqual(j.stats().included_files, 0)

    def test_stats_included_files_reflects_loader(self):
        j = load_journal(FIXTURES / "root_with_include.journal")
        self.assertEqual(j.stats().included_files, 1)

    def test_stats_included_files_nested(self):
        j = load_journal(FIXTURES / "nested_a.journal")
        self.assertEqual(j.stats().included_files, 2)


class TestPublicAPI(unittest.TestCase):
    """PyLedger public API still works via the load alias."""

    def test_pyledger_load_alias_works(self):
        import PyLedger
        j = PyLedger.load(SAMPLE_JOURNAL)
        self.assertEqual(len(j.transactions), 5)

    def test_pyledger_load_returns_journal(self):
        import PyLedger
        from PyLedger.models import Journal
        j = PyLedger.load(SAMPLE_JOURNAL)
        self.assertIsInstance(j, Journal)

    def test_parse_string_skips_include_lines(self):
        from PyLedger.parser import parse_string
        text = (
            "include other.journal\n"
            "2024-01-01 Test\n"
            "    assets:bank  £10\n"
            "    equity\n"
        )
        j = parse_string(text)
        self.assertEqual(len(j.transactions), 1)


class TestMergeJournalsDeclared(unittest.TestCase):
    """merge_journals should concatenate declared_* fields from all journals."""

    def _make_journal(
        self,
        accounts: list | None = None,
        commodities: list | None = None,
        payees: list | None = None,
        tags: list | None = None,
    ):
        from PyLedger.models import Journal
        return Journal(
            declared_accounts=accounts or [],
            declared_commodities=commodities or [],
            declared_payees=payees or [],
            declared_tags=tags or [],
        )

    def test_merge_declared_accounts_concatenated(self):
        j1 = self._make_journal(accounts=["assets:bank"])
        j2 = self._make_journal(accounts=["income:salary"])
        result = merge_journals([j1, j2])
        self.assertEqual(result.declared_accounts, ["assets:bank", "income:salary"])

    def test_merge_declared_commodities_concatenated(self):
        j1 = self._make_journal(commodities=["£"])
        j2 = self._make_journal(commodities=["EUR"])
        result = merge_journals([j1, j2])
        self.assertEqual(result.declared_commodities, ["£", "EUR"])

    def test_merge_declared_payees_concatenated(self):
        j1 = self._make_journal(payees=["Shop A"])
        j2 = self._make_journal(payees=["Shop B"])
        result = merge_journals([j1, j2])
        self.assertEqual(result.declared_payees, ["Shop A", "Shop B"])

    def test_merge_declared_tags_concatenated(self):
        j1 = self._make_journal(tags=["project"])
        j2 = self._make_journal(tags=["type"])
        result = merge_journals([j1, j2])
        self.assertEqual(result.declared_tags, ["project", "type"])

    def test_merge_declared_fields_empty_when_none(self):
        j1 = self._make_journal()
        j2 = self._make_journal()
        result = merge_journals([j1, j2])
        self.assertEqual(result.declared_accounts, [])
        self.assertEqual(result.declared_commodities, [])
        self.assertEqual(result.declared_payees, [])
        self.assertEqual(result.declared_tags, [])

    def test_merge_single_journal_preserves_declared_fields(self):
        j = self._make_journal(accounts=["assets:bank"], commodities=["£"])
        result = merge_journals([j])
        self.assertIs(result, j)  # single-journal fast path returns original
        self.assertEqual(result.declared_accounts, ["assets:bank"])


if __name__ == "__main__":
    unittest.main()
