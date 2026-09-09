"""Account and payee name index for Tab autocompletion (Phase 4a).

Built from a full-journal scan — declared `account`/`payee` directives
(ledgerkit.Journal.declared_accounts / .declared_payees) plus every account
actually used on a posting and every transaction description — not
incrementally per keystroke. Journals can run to 10,000+ transactions (see
ROADMAP.md Milestone D's performance note), so the index is deliberately a
cached snapshot, explicitly rebuilt by the caller (JournalEditor rebuilds it
on file load and after Ctrl+S — see widgets/autocomplete.py) rather than
recomputed on every character typed.
"""

from __future__ import annotations

from dataclasses import dataclass, field

__all__ = ["JournalIndex", "build_journal_index"]


@dataclass
class JournalIndex:
    """Sorted, deduplicated account and payee names from a journal."""

    accounts: list[str] = field(default_factory=list)
    payees: list[str] = field(default_factory=list)

    def matching_accounts(self, prefix: str, limit: int = 8) -> list[str]:
        """Return up to `limit` accounts starting with prefix (case-insensitive)."""
        return _prefix_match(self.accounts, prefix, limit)

    def matching_payees(self, prefix: str, limit: int = 8) -> list[str]:
        """Return up to `limit` payees starting with prefix (case-insensitive)."""
        return _prefix_match(self.payees, prefix, limit)


def _prefix_match(names: list[str], prefix: str, limit: int) -> list[str]:
    """Return up to `limit` names starting with prefix, shortest match first.

    Shortest-first (then alphabetical) surfaces the most general match —
    e.g. typing "exp" against ["expenses", "expenses:food",
    "expenses:food:organic"] offers "expenses" before its own sub-accounts,
    which matches how people usually want to complete a partial account
    name (finish the current segment before drilling into children).
    An empty prefix matches everything (up to limit), in the same order.
    """
    lowered = prefix.lower()
    matches = [n for n in names if n.lower().startswith(lowered)]
    matches.sort(key=lambda n: (len(n), n.lower()))
    return matches[:limit]


def build_journal_index(text: str) -> JournalIndex:
    """Parse raw journal text and build a JournalIndex from it.

    Uses ledgerkit.parse_string_lenient so a syntactically broken journal
    still yields whatever could be parsed, consistent with how the rest of
    the editor treats parse errors (surfaced as notifications, never
    blocking). Returns an empty JournalIndex if parsing fails entirely.
    """
    import ledgerkit  # noqa: PLC0415

    try:
        journal, _errors = ledgerkit.parse_string_lenient(text)
    except Exception:  # noqa: BLE001
        return JournalIndex()

    accounts: set[str] = {a for a in journal.declared_accounts if a}
    payees: set[str] = {p for p in journal.declared_payees if p}
    for tx in journal.transactions:
        if tx.description:
            payees.add(tx.description)
        for posting in tx.postings:
            if posting.account:
                accounts.add(posting.account)

    return JournalIndex(accounts=sorted(accounts), payees=sorted(payees))
