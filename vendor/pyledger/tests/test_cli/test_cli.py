"""Tests for PyLedger.cli — -f/--file flag, _resolve_files, and multi-file loading."""

import os
import pathlib
import sys
import tempfile
import textwrap
import unittest
from io import StringIO
from unittest.mock import patch

from PyLedger.cli import _resolve_files, main

FIXTURES = pathlib.Path(__file__).parent.parent / "fixtures"
SAMPLE_JOURNAL = FIXTURES / "sample.journal"
FILTERED_JOURNAL = FIXTURES / "filtered.journal"
ASSERTIONS_PASS = FIXTURES / "assertions_pass.journal"
ASSERTIONS_FAIL = FIXTURES / "assertions_fail.journal"

_SIMPLE_JOURNAL = textwrap.dedent("""\
    2024-01-01 Simple
        assets:bank  £10.00
        income:other  -£10.00
""")

_SIMPLE_JOURNAL_2 = textwrap.dedent("""\
    2024-02-01 Another
        assets:bank  £5.00
        income:other  -£5.00
""")


def _write_temp(content: str, suffix: str = ".journal") -> pathlib.Path:
    f = tempfile.NamedTemporaryFile(
        suffix=suffix, mode="w", encoding="utf-8", delete=False
    )
    f.write(content)
    f.close()
    return pathlib.Path(f.name)


class _FakeArgs:
    """Minimal stand-in for argparse.Namespace for _resolve_files tests."""

    def __init__(self, files=None, journal=None, command="stats"):
        self.files = files
        # journal is now a list (nargs="*") — default to empty list
        self.journal = journal if journal is not None else []
        self.command = command


class TestResolveFiles(unittest.TestCase):
    """Unit tests for the _resolve_files helper."""

    def test_files_flag_returned(self):
        args = _FakeArgs(files=["/a.journal", "/b.journal"])
        self.assertEqual(_resolve_files(args), ["/a.journal", "/b.journal"])

    def test_positional_returned(self):
        args = _FakeArgs(journal=["/a.journal"])
        self.assertEqual(_resolve_files(args), ["/a.journal"])

    def test_both_flags_raises(self):
        args = _FakeArgs(files=["/a.journal"], journal=["/b.journal"])
        with self.assertRaises(SystemExit) as ctx:
            _resolve_files(args)
        self.assertEqual(ctx.exception.code, 1)

    def test_env_ledger_file_used(self):
        args = _FakeArgs()
        with patch.dict(os.environ, {"LEDGER_FILE": "/env.journal"}, clear=False):
            result = _resolve_files(args)
        self.assertEqual(result, ["/env.journal"])

    def test_no_file_no_env_raises(self):
        args = _FakeArgs()
        with patch.dict(os.environ, {}, clear=True):
            # Patch Path.home() so ~/.hledger.journal won't accidentally exist
            with patch("PyLedger.cli.Path") as mock_path_cls:
                mock_home = mock_path_cls.home.return_value
                mock_home.__truediv__ = lambda self, other: mock_home
                mock_home.exists.return_value = False
                with self.assertRaises(SystemExit) as ctx:
                    _resolve_files(args)
        self.assertEqual(ctx.exception.code, 1)

    def test_env_takes_precedence_over_default(self):
        args = _FakeArgs()
        with patch.dict(os.environ, {"LEDGER_FILE": "/env.journal"}, clear=False):
            result = _resolve_files(args)
        self.assertEqual(result[0], "/env.journal")


class TestFileFlagCLI(unittest.TestCase):
    """Integration tests for the -f/--file flag via main()."""

    def test_f_flag_loads_journal(self):
        code = main(["-f", str(SAMPLE_JOURNAL), "stats"])
        self.assertEqual(code, 0)

    def test_f_flag_long_form(self):
        code = main(["--file", str(SAMPLE_JOURNAL), "stats"])
        self.assertEqual(code, 0)

    def test_positional_still_works(self):
        code = main(["stats", str(SAMPLE_JOURNAL)])
        self.assertEqual(code, 0)

    def test_f_flag_multiple_merges(self):
        tmp1 = _write_temp(_SIMPLE_JOURNAL)
        tmp2 = _write_temp(_SIMPLE_JOURNAL_2)
        try:
            buf = StringIO()
            with patch("sys.stdout", buf):
                code = main(["-f", str(tmp1), "-f", str(tmp2), "print"])
            self.assertEqual(code, 0)
            output = buf.getvalue()
            self.assertIn("Simple", output)
            self.assertIn("Another", output)
        finally:
            os.unlink(str(tmp1))
            os.unlink(str(tmp2))

    def test_f_flag_and_positional_errors(self):
        code = main(["-f", str(SAMPLE_JOURNAL), "stats", str(SAMPLE_JOURNAL)])
        self.assertEqual(code, 1)

    def test_f_flag_nonexistent_file_errors(self):
        code = main(["-f", "/no/such/file.journal", "stats"])
        self.assertEqual(code, 1)

    def test_f_flag_stdin(self):
        with patch("sys.stdin", StringIO(_SIMPLE_JOURNAL)):
            buf = StringIO()
            with patch("sys.stdout", buf):
                code = main(["-f", "-", "print"])
        self.assertEqual(code, 0)
        self.assertIn("Simple", buf.getvalue())

    def test_env_fallback_ledger_file(self):
        tmp = _write_temp(_SIMPLE_JOURNAL)
        try:
            with patch.dict(os.environ, {"LEDGER_FILE": str(tmp)}, clear=False):
                code = main(["stats"])
            self.assertEqual(code, 0)
        finally:
            os.unlink(str(tmp))

    def test_no_file_no_env_exits_with_message(self):
        with patch.dict(os.environ, {}, clear=True):
            with patch("PyLedger.cli.Path") as mock_path_cls:
                mock_home = mock_path_cls.home.return_value
                mock_home.__truediv__ = lambda self, other: mock_home
                mock_home.exists.return_value = False
                buf = StringIO()
                with patch("sys.stderr", buf):
                    code = main(["stats"])
        self.assertEqual(code, 1)
        self.assertIn("no journal file specified", buf.getvalue())


class TestFileFlagOutput(unittest.TestCase):
    """Verify output content when using -f flag."""

    def test_stats_source_file_reflects_f_flag(self):
        buf = StringIO()
        with patch("sys.stdout", buf):
            main(["-f", str(SAMPLE_JOURNAL), "stats"])
        output = buf.getvalue()
        self.assertIn("Main file", output)

    def test_multiple_f_included_files_summed(self):
        root = FIXTURES / "root_with_include.journal"
        buf = StringIO()
        with patch("sys.stdout", buf):
            main(["-f", str(SAMPLE_JOURNAL), "-f", str(root), "stats"])
        output = buf.getvalue()
        # root_with_include has 1 included file; sample has 0 → total 1
        self.assertIn("Included files      : 1", output)


class TestBalanceOutput(unittest.TestCase):
    """Verify balance CLI output format against filtered.journal."""

    def _run_balance(self) -> str:
        buf = StringIO()
        with patch("sys.stdout", buf):
            code = main(["-f", str(FILTERED_JOURNAL), "balance"])
        self.assertEqual(code, 0)
        return buf.getvalue()

    def test_balance_exits_zero(self):
        self.assertEqual(main(["-f", str(FILTERED_JOURNAL), "balance"]), 0)

    def test_amount_format_positive(self):
        output = self._run_balance()
        self.assertIn("£9,641.00", output)

    def test_amount_format_negative(self):
        # Commodity precedes minus sign: £-5,000.00 not -£5,000.00
        output = self._run_balance()
        self.assertIn("£-5,000.00", output)

    def test_account_after_amount(self):
        # hledger format: amount first, then account (reversed from old PyLedger)
        output = self._run_balance()
        for line in output.splitlines():
            if "assets:bank:checking" in line:
                self.assertLess(line.index("£"), line.index("assets"))

    def test_separator_line_present(self):
        output = self._run_balance()
        self.assertIn("----", output)

    def test_grand_total_zero_shown_bare(self):
        # Balanced journal: grand total is 0, displayed without commodity symbol
        output = self._run_balance()
        lines = [l.strip() for l in output.splitlines()]
        self.assertIn("0", lines)

    def test_row_count(self):
        # 6 accounts + separator + total = 8 lines
        output = self._run_balance()
        non_empty = [l for l in output.splitlines() if l.strip()]
        self.assertEqual(len(non_empty), 8)


class TestRegisterOutput(unittest.TestCase):
    """Verify register CLI output format against filtered.journal."""

    def _run_register(self) -> str:
        buf = StringIO()
        with patch("sys.stdout", buf):
            code = main(["-f", str(FILTERED_JOURNAL), "register"])
        self.assertEqual(code, 0)
        return buf.getvalue()

    def test_register_exits_zero(self):
        code = main(["-f", str(FILTERED_JOURNAL), "register"])
        self.assertEqual(code, 0)

    def test_register_row_count(self):
        output = self._run_register()
        non_empty = [l for l in output.splitlines() if l.strip()]
        self.assertEqual(len(non_empty), 12)

    def test_amount_format_positive(self):
        # Commodity precedes quantity; comma thousands separator; two decimal places
        output = self._run_register()
        self.assertIn("£5,000.00", output)

    def test_amount_format_negative(self):
        # Commodity precedes minus sign: £-5,000.00 not -£5,000.00
        output = self._run_register()
        self.assertIn("£-5,000.00", output)

    def test_running_balance_zero_shown_bare(self):
        # Balanced transactions net to 0 — displayed as bare "0" not "£0.00"
        output = self._run_register()
        lines = output.splitlines()
        # Every second line (continuation posting) should have the balance "0"
        self.assertTrue(any(l.rstrip().endswith("0") for l in lines))

    def test_date_blank_on_continuation_rows(self):
        # Only the first posting of each transaction shows a date
        output = self._run_register()
        lines = [l for l in output.splitlines() if l.strip()]
        # 6 transactions × 2 postings = 12 lines; 6 should start with a date
        date_lines = [l for l in lines if l[:4].strip().isdigit()]
        blank_lines = [l for l in lines if not l[:4].strip()]
        self.assertEqual(len(date_lines), 6)
        self.assertEqual(len(blank_lines), 6)

    def test_elided_posting_shown(self):
        # Last Salary transaction has an elided income:salary posting — must appear
        output = self._run_register()
        self.assertIn("£-3,000.00", output)
        # income:salary appears at least twice (two Salary transactions)
        self.assertGreaterEqual(output.count("income:salary"), 2)

    def test_long_account_abbreviated(self):
        # equity:opening-balances (23 chars) → eq:opening-balances
        output = self._run_register()
        self.assertIn("eq:opening-balances", output)
        self.assertNotIn("equity:opening-balances", output)


# ---------------------------------------------------------------------------
# Balance assertions: -I / --ignore-assertions flag
# ---------------------------------------------------------------------------

class TestBalanceAssertions(unittest.TestCase):
    """CLI-level tests for balance assertion checking and the -I flag."""

    def _run(self, *args: str) -> tuple[int, str, str]:
        """Run main() with the given args; return (exit_code, stdout, stderr)."""
        with patch("sys.argv", ["PyLedger", *args]):
            out = StringIO()
            err = StringIO()
            with patch("sys.stdout", out), patch("sys.stderr", err):
                code = main()
        return (code, out.getvalue(), err.getvalue())

    def test_passing_assertions_exits_zero(self):
        code, _out, _err = self._run("stats", "-f", str(ASSERTIONS_PASS))
        self.assertEqual(code, 0)

    def test_failing_assertion_exits_one(self):
        code, _out, err = self._run("stats", "-f", str(ASSERTIONS_FAIL))
        self.assertEqual(code, 1)
        self.assertIn("assertion", err.lower())

    def test_ignore_assertions_flag_suppresses_failure(self):
        code, _out, _err = self._run("-I", "stats", "-f", str(ASSERTIONS_FAIL))
        self.assertEqual(code, 0)

    def test_ignore_assertions_long_flag(self):
        code, _out, _err = self._run(
            "--ignore-assertions", "stats", "-f", str(ASSERTIONS_FAIL)
        )
        self.assertEqual(code, 0)

    def test_check_command_reports_assertion_error(self):
        code, _out, err = self._run("check", "assertions", "-f", str(ASSERTIONS_FAIL))
        self.assertEqual(code, 1)
        self.assertIn("assertion", err.lower())

    def test_check_command_passes_on_clean_journal(self):
        code, _out, _err = self._run("check", "assertions", "-f", str(ASSERTIONS_PASS))
        self.assertEqual(code, 0)


if __name__ == "__main__":
    unittest.main()
