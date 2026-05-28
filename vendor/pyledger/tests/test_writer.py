"""Tests for PyLedger/writer.py."""

import datetime
import unittest
from decimal import Decimal
from pathlib import Path

from PyLedger.models import Amount, Journal, Posting, Transaction
from PyLedger.parser import parse_string
from PyLedger.writer import journal_to_text, transaction_to_text


def _txn(date_str, description, postings, **kwargs):
    """Build a Transaction by parsing a minimal journal text snippet."""
    lines = [f"{date_str} {description}"]
    for account, amount_str in postings:
        if amount_str is None:
            lines.append(f"    {account}")
        else:
            lines.append(f"    {account}  {amount_str}")
    text = "\n".join(lines) + "\n"
    j = parse_string(text)
    txn = j.transactions[0]
    # Apply any kwargs as attribute overrides
    for k, v in kwargs.items():
        setattr(txn, k, v)
    return txn


class TestTransactionToText(unittest.TestCase):

    def test_simple_two_posting_transaction(self):
        txn = _txn("2024-01-01", "Opening balance", [
            ("assets:bank:checking", "£2000.00"),
            ("equity:opening-balances", "-£2000.00"),
        ])
        text = transaction_to_text(txn)
        self.assertTrue(text.endswith("\n"), "must end with newline")
        lines = text.rstrip("\n").splitlines()
        self.assertEqual(lines[0], "2024-01-01 Opening balance")
        self.assertIn("assets:bank:checking", lines[1])
        self.assertIn("equity:opening-balances", lines[2])
        self.assertIn("£2000.00", lines[1])
        self.assertIn("-£2000.00", lines[2])

    def test_cleared_flag(self):
        txn = _txn("2024-01-05", "Salary", [
            ("assets:bank:checking", "£3500.00"),
            ("income:salary", "-£3500.00"),
        ], cleared=True)
        text = transaction_to_text(txn)
        first_line = text.splitlines()[0]
        self.assertIn("*", first_line)
        self.assertTrue(first_line.startswith("2024-01-05 *"))

    def test_pending_flag(self):
        txn = _txn("2024-01-15", "Transfer", [
            ("assets:bank:savings", "£500.00"),
            ("assets:bank:checking", "-£500.00"),
        ], pending=True)
        first_line = transaction_to_text(txn).splitlines()[0]
        self.assertIn("!", first_line)
        self.assertTrue(first_line.startswith("2024-01-15 !"))

    def test_elided_posting(self):
        txn = Transaction(
            date=datetime.date(2024, 2, 1),
            description="Rent",
            postings=[
                Posting(account="expenses:housing", amount=Amount(Decimal("1200"), "£")),
                Posting(account="assets:bank:checking"),  # elided
            ],
        )
        text = transaction_to_text(txn)
        lines = text.rstrip("\n").splitlines()
        # elided posting line has no amount
        self.assertEqual(lines[2].strip(), "assets:bank:checking")

    def test_inline_comment_header(self):
        txn = Transaction(
            date=datetime.date(2024, 1, 20),
            description="Coffee shop",
            postings=[
                Posting(account="expenses:food:coffee", amount=Amount(Decimal("4.50"), "£")),
                Posting(account="assets:bank:checking", amount=Amount(Decimal("-4.50"), "£")),
            ],
            inline_comment="business meeting",
        )
        first_line = transaction_to_text(txn).splitlines()[0]
        self.assertIn("; business meeting", first_line)

    def test_inline_comment_posting(self):
        posting = Posting(
            account="expenses:food:coffee",
            amount=Amount(Decimal("4.50"), "£"),
            inline_comment="latte",
        )
        txn = Transaction(
            date=datetime.date(2024, 1, 20),
            description="Coffee",
            postings=[
                posting,
                Posting(account="assets:bank:checking", amount=Amount(Decimal("-4.50"), "£")),
            ],
        )
        text = transaction_to_text(txn)
        posting_line = text.splitlines()[1]
        self.assertIn("; latte", posting_line)

    def test_amount_alignment(self):
        """Amounts should be right-aligned so decimal points line up."""
        txn = Transaction(
            date=datetime.date(2024, 1, 1),
            description="Test",
            postings=[
                Posting(account="assets:checking", amount=Amount(Decimal("1000.00"), "£")),
                Posting(account="income:salary", amount=Amount(Decimal("-1000.00"), "£")),
            ],
        )
        text = transaction_to_text(txn)
        lines = text.splitlines()
        # Find position of the £ symbol in each posting line
        pos1 = lines[1].index("£")
        pos2 = lines[2].index("£") if "£" in lines[2] else lines[2].index("-£") + 1
        # The numeric part after the symbol should be at the same right-edge
        # (amounts are right-aligned, so right edges align)
        right1 = len(lines[1])
        right2 = len(lines[2])
        self.assertEqual(right1, right2, "amount right-edges should align")

    def test_multi_commodity(self):
        txn = Transaction(
            date=datetime.date(2024, 3, 1),
            description="Multi-commodity",
            postings=[
                Posting(account="assets:stocks", amount=Amount(Decimal("10"), "AAPL")),
                Posting(account="assets:bank:checking", amount=Amount(Decimal("-1790.00"), "£")),
            ],
        )
        text = transaction_to_text(txn)
        self.assertIn("AAPL", text)
        self.assertIn("£", text)

    def test_roundtrip_simple(self):
        """parse_string(transaction_to_text(txn)) must produce an equivalent transaction."""
        txn = _txn("2024-01-01", "Opening balance", [
            ("assets:bank:checking", "£2000.00"),
            ("equity:opening-balances", "-£2000.00"),
        ])
        text = transaction_to_text(txn)
        j2 = parse_string(text)
        self.assertEqual(len(j2.transactions), 1)
        t2 = j2.transactions[0]
        self.assertEqual(t2.date, txn.date)
        self.assertEqual(t2.description, txn.description)
        self.assertEqual(len(t2.postings), 2)
        self.assertEqual(t2.postings[0].account, "assets:bank:checking")
        self.assertEqual(t2.postings[0].amount, Amount(Decimal("2000.00"), "£"))

    def test_roundtrip_with_flags_and_comments(self):
        txn = Transaction(
            date=datetime.date(2024, 1, 5),
            description="Salary",
            postings=[
                Posting(account="assets:bank:checking", amount=Amount(Decimal("3500.00"), "£")),
                Posting(account="income:salary", amount=Amount(Decimal("-3500.00"), "£")),
            ],
            cleared=True,
            inline_comment="quarterly bonus",
        )
        text = transaction_to_text(txn)
        j2 = parse_string(text)
        t2 = j2.transactions[0]
        self.assertTrue(t2.cleared)
        self.assertEqual(t2.comment, "quarterly bonus")


class TestJournalToText(unittest.TestCase):

    def test_journal_to_text_roundtrip(self):
        """journal_to_text output must re-parse to the same transaction count."""
        fixture = Path(__file__).parent / "fixtures" / "sample.journal"
        j = parse_string(fixture.read_text(encoding="utf-8"))
        text = journal_to_text(j)
        j2 = parse_string(text)
        self.assertEqual(len(j.transactions), len(j2.transactions))

    def test_journal_to_text_empty(self):
        j = Journal()
        self.assertEqual(journal_to_text(j), "\n")

    def test_journal_to_text_separator(self):
        """Transactions must be separated by exactly one blank line."""
        j = parse_string(
            "2024-01-01 A\n    assets:a  £10\n    equity:e  -£10\n\n"
            "2024-01-02 B\n    assets:b  £20\n    equity:e  -£20\n"
        )
        text = journal_to_text(j)
        # The two blocks should be separated by exactly one blank line (\n\n)
        self.assertIn("\n\n", text)
        # No triple blank lines
        self.assertNotIn("\n\n\n", text)


if __name__ == "__main__":
    unittest.main()
