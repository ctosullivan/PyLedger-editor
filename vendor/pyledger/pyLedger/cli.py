"""Command-line interface for PyLedger.

Parses arguments, loads the journal, calls reports, and formats output.
Entry point: main() — wired to `pyLedger` via pyproject.toml.
"""

from __future__ import annotations

import argparse
import contextlib
import os
import sys
import time
from decimal import Decimal
from pathlib import Path

# Captured as early as possible so elapsed time includes import overhead.
_PROGRAM_START = time.perf_counter()

from PyLedger import __version__


COMMANDS = ("balance", "register", "accounts", "print", "stats", "check")

_ANSI_RED   = "\033[31m"
_ANSI_RESET = "\033[0m"


# Formats a quantity+commodity pair in hledger style:
#   positive → £5,000.00   negative → £-3,000.00
# Commodity symbol is always placed before the sign.
def _fmt_amount(quantity: Decimal, commodity: str) -> str:
    if quantity < 0:
        return f"{commodity}-{abs(quantity):,.2f}"
    return f"{commodity}{quantity:,.2f}"


# Formats the running balance; shows bare "0" (no commodity) when zero,
# matching hledger's convention for balanced-transaction nets.
def _fmt_balance(balance: Decimal, commodity: str) -> str:
    if balance == 0:
        return "0"
    return _fmt_amount(balance, commodity)


# Abbreviates a colon-separated account name to fit within max_width by
# progressively shortening leading components (never the last component).
# First pass: shorten each oversized leading component to 2 chars.
# Second pass: shorten to 1 char if still too long.
# Matches hledger's visual shortening — e.g. "expenses:food:rent" → "ex:food:rent".
def _abbreviate_account(account: str, max_width: int = 20) -> str:
    if len(account) <= max_width:
        return account
    parts = account.split(":")
    for min_len in (2, 1):
        for i in range(len(parts) - 1):
            if len(parts[i]) > min_len:
                parts[i] = parts[i][:min_len]
                if len(":".join(parts)) <= max_width:
                    return ":".join(parts)
    return ":".join(parts)



def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="PyLedger",
        description="Plain-text accounting (hledger-compatible)",
    )
    p.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    p.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Show more detailed output (stats: commodity names)",
    )
    p.add_argument(
        "-1",
        dest="one_line",
        action="store_true",
        help="Show a single tab-separated line of output (stats only)",
    )
    p.add_argument(
        "-o", "--output-file",
        metavar="FILE",
        help="Write output to FILE instead of stdout",
    )
    p.add_argument(
        "-f", "--file",
        metavar="FILE",
        dest="files",
        action="append",
        help="Read data from FILE, or stdin if -. May be specified more than once.",
    )
    p.add_argument(
        "-s", "--strict",
        action="store_true",
        help="Enable strict mode: also check that accounts and commodities are declared",
    )
    p.add_argument(
        "-I", "--ignore-assertions",
        dest="ignore_assertions",
        action="store_true",
        help="Disable balance assertion checking",
    )
    p.add_argument(
        "command",
        choices=COMMANDS,
        help=f"Report to run: {', '.join(COMMANDS)}",
    )
    p.add_argument(
        "journal",
        nargs="*",
        help=(
            "Journal file (shorthand for -f; all commands except check), "
            "or check names (check command only)"
        ),
    )
    return p


def _resolve_files(args: argparse.Namespace) -> list[str]:
    """Return the ordered list of files to load from parsed CLI arguments.

    Resolution order:
      1. ``-f``/``--file`` flags (all of them, in order given)
      2. Positional arguments when command is not ``check`` (backward-compatible
         shorthand for a single journal file)
      3. ``$LEDGER_FILE`` environment variable
      4. ``~/.hledger.journal`` if it exists

    For the ``check`` command all positional arguments are treated as check names,
    not journal files; the journal file must come from ``-f`` or the environment.

    Raises:
        SystemExit(1): if both ``-f`` and a positional file are given, or if no
            file can be determined.
    """
    is_check = getattr(args, "command", None) == "check"
    # args.journal is a list (nargs="*"); non-empty only when positionals given
    positional_file = args.journal[0] if (args.journal and not is_check) else None

    if args.files and positional_file:
        print(
            "pyLedger: cannot combine -f/--file flags with a positional "
            "journal argument",
            file=sys.stderr,
        )
        raise SystemExit(1)
    if args.files:
        return args.files
    if positional_file:
        return [positional_file]
    env = os.environ.get("LEDGER_FILE")
    if env:
        return [env]
    default = Path.home() / ".hledger.journal"
    if default.exists():
        return [str(default)]
    print(
        "pyLedger: no journal file specified; use -f FILE or set $LEDGER_FILE",
        file=sys.stderr,
    )
    raise SystemExit(1)


def main(argv: list[str] | None = None) -> int:
    """Entry point for the pyLedger CLI.

    Args:
        argv: Argument list (defaults to sys.argv[1:] when None).

    Returns:
        Exit code (0 = success, 1 = error).
    """
    parser = _build_parser()
    args = parser.parse_args(argv)

    try:
        file_list = _resolve_files(args)
    except SystemExit as exc:
        return int(exc.code) if exc.code is not None else 1

    try:
        from PyLedger.loader import load_journal, load_journal_stdin, merge_journals
        from PyLedger.models import Journal

        loaded: list[Journal] = []
        for f in file_list:
            if f == "-":
                loaded.append(load_journal_stdin())
            else:
                loaded.append(load_journal(f))
        journal = merge_journals(loaded)
    except FileNotFoundError as exc:
        print(f"pyLedger: file not found: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:
        print(f"pyLedger: {exc}", file=sys.stderr)
        return 1

    # --- Default basic-check gate (runs before every command) ---
    from PyLedger import checks as _checks

    _skip: frozenset[str] = (
        frozenset({"assertions"}) if getattr(args, "ignore_assertions", False) else frozenset()
    )

    basic_errors = _checks.run_basic_checks(journal, skip=_skip)
    if basic_errors:
        for e in basic_errors:
            print(f"pyLedger: {e.message}", file=sys.stderr)
        return 1

    # --- Strict-mode checks (-s/--strict) ---
    if args.strict:
        strict_only = [
            e for e in _checks.run_strict_checks(journal, skip=_skip)
            if e.check_name not in _checks.BASIC_CHECK_NAMES
        ]
        if strict_only:
            for e in strict_only:
                print(f"pyLedger: {e.message}", file=sys.stderr)
            return 1

    # --- check command (no output on success; errors → stderr + exit 1) ---
    if args.command == "check":
        check_names = args.journal  # positional args are check names for this command
        try:
            errors = _checks.run_checks(
                journal, names=list(check_names), strict=args.strict, skip=_skip
            )
        except ValueError as exc:
            print(f"pyLedger: {exc}", file=sys.stderr)
            return 1
        if errors:
            for e in errors:
                print(f"pyLedger: {e.message}", file=sys.stderr)
            return 1
        return 0

    outfile = None
    if args.output_file:
        try:
            outfile = open(args.output_file, "w", encoding="utf-8")
        except OSError as exc:
            print(f"pyLedger: cannot open output file: {exc}", file=sys.stderr)
            return 1

    try:
        import PyLedger.reports as reports

        with contextlib.redirect_stdout(outfile) if outfile else contextlib.nullcontext():
            if args.command == "balance":
                result = reports.balance(journal)
                # result: dict[str, dict[str, Decimal]] — account → commodity → net

                # Flatten to (account, commodity, qty) rows; sorted alphabetically.
                # Zero-balance commodity lines are omitted (matching hledger behaviour).
                lines: list[tuple[str, str, Decimal]] = [
                    (acct, comm, qty)
                    for acct in sorted(result)
                    for comm, qty in sorted(result[acct].items())
                    if qty != 0
                ]

                if not lines:
                    pass
                else:
                    # Per-commodity grand totals (from filtered lines only).
                    commodity_totals: dict[str, Decimal] = {}
                    for _, comm, qty in lines:
                        commodity_totals[comm] = commodity_totals.get(comm, Decimal(0)) + qty

                    formatted_amts = [_fmt_amount(qty, comm) for _, comm, qty in lines]
                    # Only show non-zero commodity totals; a single bare "0" when all net zero.
                    nonzero_totals = [
                        (comm, qty)
                        for comm, qty in sorted(commodity_totals.items())
                        if qty != 0
                    ]
                    total_strs = [_fmt_amount(qty, comm) for comm, qty in nonzero_totals]
                    col_w = max(
                        20,
                        *(len(s) for s in formatted_amts),
                        *(len(s) for s in total_strs),
                    )

                    # Determine the last (account, commodity) row index per account
                    # so the account name is printed only on that row.
                    acct_last_idx: dict[str, int] = {
                        acct: i for i, (acct, _, _) in enumerate(lines)
                    }

                    for i, ((acct, comm, qty), amt_str) in enumerate(
                        zip(lines, formatted_amts)
                    ):
                        padded = f"{amt_str:>{col_w}}"
                        if qty < 0:
                            padded = f"{_ANSI_RED}{padded}{_ANSI_RESET}"
                        if i == acct_last_idx[acct]:
                            print(f"{padded}  {acct}")
                        else:
                            print(padded)

                    print("-" * col_w)
                    if nonzero_totals:
                        for (comm, total), tot_str in zip(nonzero_totals, total_strs):
                            tot = f"{tot_str:>{col_w}}"
                            if total < 0:
                                tot = f"{_ANSI_RED}{tot}{_ANSI_RESET}"
                            print(tot)
                    else:
                        print(f"{'0':>{col_w}}")

            elif args.command == "register":
                rows = reports.register(journal)
                prev_key: tuple | None = None
                for row in rows:
                    cur_key = (row.date, row.description)
                    is_first = cur_key != prev_key
                    date_str = str(row.date) if is_first else ""
                    desc_str = row.description if is_first else ""
                    acct_str = _abbreviate_account(row.account)
                    commodity = row.amount.commodity

                    # Right-align before colorising — ANSI escape codes have nonzero
                    # string length but zero display width, so padding must come first.
                    amt_str = f"{_fmt_amount(row.amount.quantity, commodity):>12}"
                    if row.amount.quantity < 0:
                        amt_str = f"{_ANSI_RED}{amt_str}{_ANSI_RESET}"

                    bal_str = f"{_fmt_balance(row.running_balance, commodity):>13}"
                    if row.running_balance < 0:
                        bal_str = f"{_ANSI_RED}{bal_str}{_ANSI_RESET}"

                    print(
                        f"{date_str:10} {desc_str:21}  {acct_str:<22}  {amt_str}  {bal_str}"
                    )
                    prev_key = cur_key

            elif args.command == "accounts":
                for name in reports.accounts(journal):
                    print(name)

            elif args.command == "print":
                for txn in sorted(journal.transactions, key=lambda t: t.date):
                    flag = " * " if txn.cleared else " ! " if txn.pending else " "
                    print(f"{txn.date}{flag}{txn.description}")
                    for posting in txn.postings:
                        if posting.amount:
                            print(
                                f"    {posting.account:<40}"
                                f"  {posting.amount.commodity}{posting.amount.quantity}"
                            )
                        else:
                            print(f"    {posting.account}")
                    print()

            elif args.command == "stats":
                s = reports.stats(journal)
                elapsed = time.perf_counter() - _PROGRAM_START
                txns_per_s = s.transaction_count / elapsed if elapsed > 0 else 0.0

                span_str = (
                    f"{s.date_range[0]} to {s.date_range[1]} ({s.txns_span_days} days)"
                    if s.date_range else "(none)"
                )
                last_str = (
                    f"{s.last_txn_date} ({s.last_txn_days_ago} days ago)"
                    if s.last_txn_date else "(none)"
                )
                commodity_str = (
                    f"{s.commodity_count} ({', '.join(s.commodities)})"
                    if args.verbose and s.commodities else str(s.commodity_count)
                )

                elapsed_str = f"{elapsed:.2f}" if elapsed >= 0.01 else f"{elapsed:.3f}"
                if args.one_line:
                    print("\t".join([
                        __version__,
                        s.source_file or "(none)",
                        f"{elapsed_str} s elapsed",
                        f"{txns_per_s:.0f} txns/s",
                    ]))
                else:
                    print(f"Main file           : {s.source_file or '(none)'}")
                    print(f"Included files      : {s.included_files}")
                    print(f"Txns span           : {span_str}")
                    print(f"Last txn            : {last_str}")
                    print(f"Txns                : {s.transaction_count} ({s.txns_per_day:.1f} per day)")
                    print(f"Txns last 30 days   : {s.txns_last_30_days} ({s.txns_per_day_last_30:.1f} per day)")
                    print(f"Txns last 7 days    : {s.txns_last_7_days} ({s.txns_per_day_last_7:.1f} per day)")
                    print(f"Payees/descriptions : {s.payee_count}")
                    print(f"Accounts            : {s.account_count} (depth {s.account_depth})")
                    print(f"Commodities         : {commodity_str}")
                    print(f"Market prices       : {s.price_count}")
                    print(f"Runtime stats       : {elapsed_str} s elapsed, {txns_per_s:.0f} txns/s")

    except NotImplementedError:
        print(
            f"pyLedger: '{args.command}' is not yet implemented",
            file=sys.stderr,
        )
        return 1
    except Exception as exc:
        print(f"pyLedger: {exc}", file=sys.stderr)
        return 1
    finally:
        if outfile:
            outfile.close()

    return 0


if __name__ == "__main__":
    sys.exit(main())
