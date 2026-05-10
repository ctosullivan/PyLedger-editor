"""Journal serialiser for PyLedger.

Converts Transaction and Journal objects back to hledger journal-format text.
No file I/O; no imports from parser, loader, checks, or cli.
"""

from __future__ import annotations

from PyLedger.models import Amount, Journal, Transaction


def _fmt_amount(amount: Amount) -> str:
    """Format an Amount to its hledger journal string representation.

    Prefix-symbol style (£, $, €, ...) for non-alpha commodities; suffix-symbol
    style (30.00 EUR) for alpha-initial commodity codes.
    """
    qty = amount.quantity
    sym = amount.commodity
    if not sym:
        return str(qty)
    if sym[0].isalpha():
        return f"{qty} {sym}"
    if qty < 0:
        return f"-{sym}{-qty}"
    return f"{sym}{qty}"


def transaction_to_text(txn: Transaction) -> str:
    """Serialise a Transaction to a journal-format string.

    The returned string ends with a single newline. When parsed by
    parse_string(), the result round-trips to an equivalent Transaction
    (same date, flag, description, postings, amounts, comments;
    source_span and raw_text are not checked).
    """
    # --- Header line ---
    parts: list[str] = [str(txn.date)]
    if txn.cleared:
        parts.append("*")
    elif txn.pending:
        parts.append("!")
    if txn.code:
        parts.append(f"({txn.code})")
    if txn.description:
        parts.append(txn.description)
    header = " ".join(parts)
    if txn.inline_comment is not None:
        header += f"  ; {txn.inline_comment}"

    # --- Posting lines ---
    # Build amount strings first to calculate alignment.
    amount_strs: list[str | None] = [
        _fmt_amount(p.amount) if p.amount is not None else None
        for p in txn.postings
    ]

    # Find the widest amount string and the widest account name (among postings
    # that carry an explicit amount) to determine the alignment column.
    max_amt_w = max((len(s) for s in amount_strs if s is not None), default=0)
    acct_lens_with_amount = [
        len(p.account)
        for p, s in zip(txn.postings, amount_strs)
        if s is not None
    ]
    max_acct_w = max(acct_lens_with_amount, default=0)
    # amount_col = position of the first character of the (right-justified)
    # amount block, counting from the start of the posting line (4-space indent
    # + longest account + minimum 2 spaces).
    amount_col = 4 + max_acct_w + 2

    posting_lines: list[str] = []
    for posting, amt_str in zip(txn.postings, amount_strs):
        if amt_str is None:
            line = f"    {posting.account}"
        else:
            gap = amount_col - 4 - len(posting.account)
            line = f"    {posting.account}{' ' * gap}{amt_str.rjust(max_amt_w)}"
        if posting.inline_comment is not None:
            line += f"  ; {posting.inline_comment}"
        posting_lines.append(line)

    return "\n".join([header] + posting_lines) + "\n"


def journal_to_text(journal: Journal) -> str:
    """Serialise all transactions in journal.transactions to text.

    Transactions are separated by blank lines; the output ends with a single
    newline. Directives (account, commodity, payee, P) are not serialised in
    v1 — callers that need full round-trip fidelity should work with the raw
    source file rather than re-serialising the Journal.
    """
    if not journal.transactions:
        return "\n"
    blocks = [transaction_to_text(t).rstrip("\n") for t in journal.transactions]
    return "\n\n".join(blocks) + "\n"
