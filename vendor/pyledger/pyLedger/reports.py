"""Report generators for PyLedger.

Each function accepts a Journal and returns structured data — not formatted
strings. Formatting is handled by cli.py.
"""

from __future__ import annotations

import datetime
import re
from dataclasses import dataclass, replace
from decimal import Decimal

from PyLedger.models import (
    BalanceRow,
    Journal,
    Posting,
    Query,
    RegisterRow,
    ReportSection,
    ReportSpec,
    ReportSectionResult,
    Transaction,
)
from PyLedger.parser import resolve_elision


@dataclass
class JournalStats:
    """Summary statistics for a journal.

    Contains only deterministic journal data. Runtime stats (elapsed time,
    txns/s) are measured and formatted by the CLI layer, not stored here.
    """

    source_file: str | None
    included_files: int
    transaction_count: int
    date_range: tuple[datetime.date, datetime.date] | None  # (first, last)
    last_txn_date: datetime.date | None
    last_txn_days_ago: int | None  # (today - last_txn_date).days
    txns_span_days: int | None  # (last - first).days + 1
    txns_per_day: float  # transaction_count / txns_span_days, else 0.0
    txns_last_30_days: int
    txns_per_day_last_30: float
    txns_last_7_days: int
    txns_per_day_last_7: float
    payee_count: int  # unique descriptions
    account_count: int
    account_depth: int  # max colon-segment depth across all accounts
    commodity_count: int
    commodities: list[str]  # sorted commodity symbols (shown in verbose mode)
    price_count: int  # len(journal.prices)


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------

# Detects whether a user-supplied pattern contains any regex metacharacter,
# used to decide between plain substring matching and re.search().
#
# Purpose: distinguish plain strings like "expenses:food" from regex patterns
#          like "^expenses" or "food.*". Any character that has special meaning
#          in a Python regex triggers regex mode.
#
# Group breakdown: no capture groups — result used only as a boolean via .search().
#
# Edge cases:
#   - A lone '.' is treated as a regex wildcard (matches any character), matching
#     hledger's behaviour where '.' in an account filter is a metacharacter.
#   - Backslash sequences like '\\(' are detected because '\\' is in the set,
#     so escaped literals always go through regex mode.
#   - An empty pattern never contains a metacharacter → plain substring mode.
_REGEX_META = re.compile(r'[\\^$.()\[\]{}*+?|]')


def _matches_pattern(pattern: str, value: str) -> bool:
    """Return True if pattern matches value using hledger substring/regex rules.

    If pattern contains any regex metacharacter it is compiled as a regex and
    matched via re.search (partial match, case-insensitive). Otherwise it is
    treated as a plain case-insensitive substring match.
    """
    if _REGEX_META.search(pattern):
        return bool(re.search(pattern, value, re.IGNORECASE))
    return pattern.lower() in value.lower()


def _posting_matches(
    posting: Posting,
    txn: Transaction,
    query: Query | None,
) -> bool:
    """Return True if the posting should be included given the query.

    Transaction-level filters (date, payee) are checked against txn.
    Posting-level filters (account, not_account, depth) are checked against posting.

    A None query or a Query() with all None fields always returns True.
    """
    if query is None:
        return True
    if query.date_from is not None and txn.date < query.date_from:
        return False
    if query.date_to is not None and txn.date > query.date_to:
        return False
    if query.payee is not None and not _matches_pattern(query.payee, txn.description):
        return False
    if query.account is not None and not _matches_pattern(query.account, posting.account):
        return False
    if query.not_account is not None and _matches_pattern(query.not_account, posting.account):
        return False
    if query.depth is not None and len(posting.account.split(":")) > query.depth:
        return False
    return True


def _aggregate_posting_amounts(
    pairs: list[tuple[str, Decimal]],
) -> dict[str, Decimal]:
    """Sum (account_name, quantity) pairs into an account → balance dict."""
    result: dict[str, Decimal] = {}
    for account, qty in pairs:
        result[account] = result.get(account, Decimal(0)) + qty
    return result


def _build_balance_tree(
    totals: dict[str, dict[str, Decimal]],
) -> list[BalanceRow]:
    """Convert a flat account→commodity→net dict into a sorted tree row list.

    Collects all implicit parent accounts (all colon-prefixes of every account
    name in `totals`), computes aggregate amounts (own postings + all
    descendants) for each, and returns a list of BalanceRow sorted
    alphabetically by account name.

    is_subtotal is True for accounts not present in `totals` directly (pure
    intermediate parents with no direct postings of their own).
    """
    all_accounts: set[str] = set(totals.keys())
    for account in list(totals.keys()):
        parts = account.split(":")
        for i in range(1, len(parts)):
            all_accounts.add(":".join(parts[:i]))

    rows: list[BalanceRow] = []
    for account in sorted(all_accounts):
        prefix = account + ":"
        agg: dict[str, Decimal] = {}
        for src, amounts in totals.items():
            if src == account or src.startswith(prefix):
                for commodity, qty in amounts.items():
                    agg[commodity] = agg.get(commodity, Decimal(0)) + qty
        rows.append(BalanceRow(
            account=account,
            depth=account.count(":"),
            amounts=agg,
            is_subtotal=(account not in totals),
        ))
    return rows


# ---------------------------------------------------------------------------
# Report functions
# ---------------------------------------------------------------------------

def accounts(journal: Journal, query: Query | None = None) -> list[str]:
    """Return a sorted list of all unique account names in the journal.

    Args:
        journal: The parsed journal.
        query: Optional filter. When None or Query(), all accounts are returned.

    Returns:
        Sorted list of account name strings that appear in at least one
        matching posting.
    """
    seen: set[str] = set()
    for txn in journal.transactions:
        for posting in txn.postings:
            if _posting_matches(posting, txn, query):
                seen.add(posting.account)
    return sorted(seen)


def balance(
    journal: Journal,
    query: Query | None = None,
    tree: bool = False,
) -> dict[str, dict[str, Decimal]] | list[BalanceRow]:
    """Return per-commodity net balances for each account.

    Args:
        journal: The parsed journal.
        query: Optional filter. When None or Query(), all postings are included.
        tree: When True, returns list[BalanceRow] with implicit parent accounts
              and aggregate subtotals. When False (default), returns a flat
              dict[str, dict[str, Decimal]] mapping account name to a
              commodity→net dict.

    Returns:
        When tree=False: dict mapping account name to {commodity: net_balance}.
        When tree=True: list[BalanceRow] sorted alphabetically, including
        implicit parent accounts with is_subtotal=True.

    Note on depth: depth in the query causes account names to be *truncated*
    (rolled up) rather than excluded — matching hledger's --depth behaviour.
    expenses:food:groceries at depth=2 contributes to expenses:food.
    """
    # Strip depth from the query before _posting_matches so deep postings are
    # not excluded, then apply truncation to the account name manually.
    matching_query = (
        replace(query, depth=None)
        if query is not None and query.depth is not None
        else query
    )
    totals: dict[str, dict[str, Decimal]] = {}
    for txn in journal.transactions:
        for posting in resolve_elision(txn):
            if not _posting_matches(posting, txn, matching_query):
                continue
            if posting.amount is None:
                continue
            account = posting.account
            if query is not None and query.depth is not None:
                account = ":".join(account.split(":")[:query.depth])
            commodity = posting.amount.commodity
            if account not in totals:
                totals[account] = {}
            totals[account][commodity] = (
                totals[account].get(commodity, Decimal(0)) + posting.amount.quantity
            )
    if tree:
        return _build_balance_tree(totals)
    return totals


def register(
    journal: Journal,
    query: Query | None = None,
) -> list[RegisterRow]:
    """Return a chronological list of register rows.

    Args:
        journal: The parsed journal.
        query: Optional filter. When None or Query(), all postings are included.

    Returns:
        List of RegisterRow objects in journal order. running_balance is the
        cumulative sum of amount.quantity across all rows in output order.
    """
    rows: list[RegisterRow] = []
    running: Decimal = Decimal(0)
    for txn in sorted(journal.transactions, key=lambda t: t.date):
        for posting in resolve_elision(txn):
            if not _posting_matches(posting, txn, query):
                continue
            if posting.amount is None:
                continue
            running += posting.amount.quantity
            rows.append(RegisterRow(
                date=txn.date,
                description=txn.description,
                account=posting.account,
                amount=posting.amount,
                running_balance=running,
            ))
    return rows


def stats(journal: Journal, query: Query | None = None) -> JournalStats:
    """Return summary statistics for the journal.

    Args:
        journal: The parsed journal.
        query: Optional filter. When None or Query(), behaviour is identical to
               the original implementation (all transactions). When a date or
               payee filter is provided, statistics are computed over the
               matching transaction subset.

    Note: account-level filters (account, not_account, depth) in the query are
    not yet applied to stats fields — those fields still reflect the full
    journal.
    # TODO: Apply account-level query filters to account_count and account_depth.
    """
    today = datetime.date.today()
    txns = journal.transactions

    # Apply transaction-level query filters when provided.
    if query is not None:
        txns = [
            t for t in txns
            if (query.date_from is None or t.date >= query.date_from)
            and (query.date_to is None or t.date <= query.date_to)
            and (query.payee is None or _matches_pattern(query.payee, t.description))
        ]

    all_accounts: set[str] = {p.account for t in txns for p in t.postings}
    all_commodities: set[str] = {
        p.amount.commodity for t in txns for p in t.postings if p.amount is not None
    }
    dates = [t.date for t in txns]
    date_range = (min(dates), max(dates)) if dates else None
    last_txn_date = max(dates) if dates else None
    span_days = (date_range[1] - date_range[0]).days + 1 if date_range else None

    cutoff_30 = today - datetime.timedelta(days=30)
    cutoff_7 = today - datetime.timedelta(days=7)
    txns_30 = sum(1 for t in txns if t.date >= cutoff_30)
    txns_7 = sum(1 for t in txns if t.date >= cutoff_7)

    depth = max((len(a.split(":")) for a in all_accounts), default=0)

    return JournalStats(
        source_file=journal.source_file,
        included_files=journal.included_files,
        transaction_count=len(txns),
        date_range=date_range,
        last_txn_date=last_txn_date,
        last_txn_days_ago=(today - last_txn_date).days if last_txn_date else None,
        txns_span_days=span_days,
        txns_per_day=len(txns) / span_days if span_days else 0.0,
        txns_last_30_days=txns_30,
        txns_per_day_last_30=txns_30 / 30,
        txns_last_7_days=txns_7,
        txns_per_day_last_7=txns_7 / 7,
        payee_count=len({t.description for t in txns}),
        account_count=len(all_accounts),
        account_depth=depth,
        commodity_count=len(all_commodities),
        commodities=sorted(all_commodities),
        price_count=len(journal.prices),
    )


def balance_from_spec(
    journal: Journal,
    spec: ReportSpec,
    query: Query | None = None,
) -> list[ReportSectionResult]:
    """Compute a structured balance report driven by a ReportSpec.

    For each section in spec.sections:
      1. Apply the outer query's date and payee filters at transaction level.
      2. Include postings whose account matches any of section.accounts (OR logic).
      3. Exclude postings whose account matches any of section.exclude.
      4. Apply the outer query's account/not_account filters if set.
      5. Apply depth truncation: section.depth overrides query.depth.
      6. Aggregate using _aggregate_posting_amounts (shared with balance()).
      7. Apply sign inversion if section.invert is True.
      8. Return a ReportSectionResult per section.

    The outer query acts as a uniform time/payee filter across all sections.
    Section-level account patterns are OR-combined within each section.

    Args:
        journal: The parsed journal.
        spec: The report layout definition.
        query: Optional uniform filter (date range, payee). Applied across all
               sections before section-level account matching.

    Returns:
        One ReportSectionResult per section in spec.sections order.
    """
    results: list[ReportSectionResult] = []

    for section in spec.sections:
        pairs: list[tuple[str, Decimal]] = []

        for txn in journal.transactions:
            # Apply outer query transaction-level filters.
            if query is not None:
                if query.date_from is not None and txn.date < query.date_from:
                    continue
                if query.date_to is not None and txn.date > query.date_to:
                    continue
                if query.payee is not None and not _matches_pattern(query.payee, txn.description):
                    continue

            for posting in resolve_elision(txn):
                # Section account patterns: OR logic — posting must match at least one.
                if not any(_matches_pattern(pat, posting.account) for pat in section.accounts):
                    continue

                # Section exclude patterns: posting must not match any.
                if any(_matches_pattern(pat, posting.account) for pat in section.exclude):
                    continue

                # Outer query account/not_account filters.
                if query is not None:
                    if query.account is not None and not _matches_pattern(query.account, posting.account):
                        continue
                    if query.not_account is not None and _matches_pattern(query.not_account, posting.account):
                        continue

                if posting.amount is None:
                    continue

                # Depth: section.depth overrides query.depth.
                depth = section.depth if section.depth is not None else (
                    query.depth if query is not None else None
                )
                account = posting.account
                if depth is not None:
                    account = ":".join(account.split(":")[:depth])

                pairs.append((account, posting.amount.quantity))

        rows = _aggregate_posting_amounts(pairs)

        if section.invert:
            rows = {k: -v for k, v in rows.items()}

        subtotal = sum(rows.values(), Decimal(0))
        results.append(ReportSectionResult(section=section, rows=rows, subtotal=subtotal))

    return results
