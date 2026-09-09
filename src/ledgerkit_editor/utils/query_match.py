"""Local implementation of hledger's substring/regex matching convention.

Deliberately duplicated from ledgerkit.reports._matches_pattern and
_posting_matches, which are private (underscore-prefixed, never exported
from ledgerkit.__init__). Per this project's ledgerkit API Rule (CLAUDE.md),
importing private members of a pinned dependency is fragile — they can
change or disappear on any ledgerkit release with no deprecation notice.

See planning/next-release-phase-plan.md, Phase 3, open decision 2
(accepted): duplicate locally rather than depend on an unreleased upstream
export. If ledgerkit ever exports a public equivalent, prefer switching to
it and removing this module. Keep the matching semantics here in sync with
ledgerkit/reports.py's _matches_pattern if that ever changes — install
prints its file path via
`python -c "import inspect, ledgerkit; print(inspect.getfile(ledgerkit.reports))"`.
"""

from __future__ import annotations

import re
from typing import Callable

__all__ = ["build_transaction_predicate", "matches_pattern"]

# Purpose: detect whether a user-supplied pattern contains any regex
#   metacharacter, to decide between plain substring matching and
#   re.search() — mirrors ledgerkit.reports._REGEX_META exactly, so account
#   and payee filter fields behave identically to ledgerkit.Query's own
#   account/payee matching (the same convention hledger itself uses).
# Group breakdown: no capture groups — result used only as a boolean via .search().
# Edge cases:
#   - A lone '.' is treated as a regex wildcard (matches any character)
#   - Backslash sequences like '\(' are detected, so escaped literals always
#     go through regex mode
#   - An empty pattern never contains a metacharacter → plain substring mode
_REGEX_META = re.compile(r"[\\^$.()\[\]{}*+?|]")


def matches_pattern(pattern: str, value: str) -> bool:
    """Return True if pattern matches value using hledger substring/regex rules.

    If pattern contains any regex metacharacter it is compiled and matched
    via re.search (partial match, case-insensitive). Otherwise it is treated
    as a plain case-insensitive substring match.

    Raises:
        re.error: if pattern looks like regex but doesn't compile. Callers
            filtering many transactions should validate patterns once up
            front (see build_transaction_predicate) rather than relying on
            this raising mid-loop.
    """
    if _REGEX_META.search(pattern):
        return bool(re.search(pattern, value, re.IGNORECASE))
    return pattern.lower() in value.lower()


def _posting_matches(posting: object, query: object) -> bool:
    """Return True if a single posting satisfies query's posting-level fields.

    Mirrors ledgerkit.reports._posting_matches's account/not_account/depth
    checks. Transaction-level fields (date, payee) are the caller's
    responsibility — see build_transaction_predicate.
    """
    account = getattr(query, "account", None)
    not_account = getattr(query, "not_account", None)
    depth = getattr(query, "depth", None)
    if account is not None and not matches_pattern(account, posting.account):
        return False
    if not_account is not None and matches_pattern(not_account, posting.account):
        return False
    if depth is not None and len(posting.account.split(":")) > depth:
        return False
    return True


def build_transaction_predicate(query: object) -> Callable[[object], bool]:
    """Build a whole-transaction visibility predicate from a ledgerkit.Query.

    A transaction is visible if: its date falls within [date_from, date_to]
    (either bound may be None), its description matches `payee`, and — when
    any of account/not_account/depth is set — at least one of its postings
    matches all of them (mirroring hledger's "transaction matches if any
    posting matches the account query" convention).

    Args:
        query: a ledgerkit.Query (or any object exposing the same
            account/not_account/payee/date_from/date_to/depth attributes).

    Returns:
        A Callable[[Transaction], bool] suitable for
        ViewFilterMixin.apply_criteria_filter().

    Raises:
        re.error: immediately, if query.account, query.not_account, or
            query.payee looks like a regex pattern but fails to compile —
            validated once here rather than on first use inside the
            predicate, so the caller can catch and report it before
            filtering anything.
    """
    account = getattr(query, "account", None)
    not_account = getattr(query, "not_account", None)
    payee = getattr(query, "payee", None)
    date_from = getattr(query, "date_from", None)
    date_to = getattr(query, "date_to", None)
    depth = getattr(query, "depth", None)

    for pattern in (account, not_account, payee):
        if pattern and _REGEX_META.search(pattern):
            re.compile(pattern)  # raises re.error if invalid; result unused

    posting_filters_active = (
        account is not None or not_account is not None or depth is not None
    )

    def predicate(tx: object) -> bool:
        if date_from is not None and tx.date < date_from:
            return False
        if date_to is not None and tx.date > date_to:
            return False
        if payee is not None and not matches_pattern(payee, tx.description):
            return False
        if not posting_filters_active:
            return True
        return any(_posting_matches(p, query) for p in tx.postings)

    return predicate
