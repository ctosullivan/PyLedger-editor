"""Tests for PyLedger/editor_model.py."""

import datetime
import tempfile
import unittest
from decimal import Decimal
from pathlib import Path

from PyLedger.checks import CheckError
from PyLedger.editor_model import EditorDocument
from PyLedger.models import Amount, Posting, Transaction

FIXTURE = Path(__file__).parent / "fixtures" / "sample.journal"


def _make_txn(date_str, description, account1, amount1_str, account2):
    """Helper: build a balanced two-posting Transaction."""
    year, month, day = (int(p) for p in date_str.split("-"))
    # amount1_str is like "£100.00" (prefix) or "-£100.00" (negative prefix)
    neg = amount1_str.startswith("-")
    s = amount1_str.lstrip("-")
    sym = ""
    while s and not s[0].isdigit():
        sym += s[0]
        s = s[1:]
    qty1 = Decimal(s.replace(",", "")) * (-1 if neg else 1)
    qty2 = -qty1
    return Transaction(
        date=datetime.date(year, month, day),
        description=description,
        postings=[
            Posting(account=account1, amount=Amount(qty1, sym)),
            Posting(account=account2, amount=Amount(qty2, sym)),
        ],
    )


class TestEditorDocumentLoad(unittest.TestCase):

    def test_load_sample_journal(self):
        doc = EditorDocument(str(FIXTURE))
        self.assertFalse(doc.dirty)
        self.assertEqual(len(doc.journal.transactions), 5)

    def test_lines_populated(self):
        doc = EditorDocument(str(FIXTURE))
        # sample.journal has 23 non-empty lines (trailing newline → splitlines gives 23)
        self.assertEqual(len(doc.lines), 23)

    def test_source_span_populated(self):
        doc = EditorDocument(str(FIXTURE))
        for txn in doc.journal.transactions:
            self.assertIsNotNone(txn.source_span, f"source_span is None for {txn.description!r}")

    def test_source_span_file(self):
        doc = EditorDocument(str(FIXTURE))
        expected_path = str(Path(FIXTURE).resolve())
        for txn in doc.journal.transactions:
            self.assertEqual(txn.source_span.file, expected_path)

    def test_source_span_lines(self):
        """Verify exact line ranges for each transaction in sample.journal."""
        doc = EditorDocument(str(FIXTURE))
        txns = doc.journal.transactions
        # sample.journal layout (1-based):
        #  1: comment, 2: comment, 3: blank
        #  4-6: Opening balance, 7: blank
        #  8-10: Salary, 11: blank
        # 12-14: Supermarket, 15: blank
        # 16-18: Transfer to savings, 19: blank
        # 20-23: Coffee shop (3 postings)
        expected = [
            ("Opening balance", 4, 6),
            ("Salary", 8, 10),
            ("Supermarket", 12, 14),
            ("Transfer to savings", 16, 18),
            ("Coffee shop", 20, 23),
        ]
        for i, (desc, start, end) in enumerate(expected):
            span = txns[i].source_span
            self.assertEqual(span.start_line, start, f"{desc}: start_line")
            self.assertEqual(span.end_line, end, f"{desc}: end_line")

    def test_raw_text_populated(self):
        doc = EditorDocument(str(FIXTURE))
        for txn in doc.journal.transactions:
            self.assertIsNotNone(txn.raw_text)
            self.assertTrue(txn.raw_text.startswith(str(txn.date)))

    def test_inline_comment_on_transaction(self):
        doc = EditorDocument(str(FIXTURE))
        coffee = doc.journal.transactions[4]
        self.assertEqual(coffee.description, "Coffee shop")
        self.assertEqual(coffee.inline_comment, "business meeting")


class TestEditorDocumentAddTransaction(unittest.TestCase):

    def setUp(self):
        self.doc = EditorDocument(str(FIXTURE))

    def test_add_transaction_end(self):
        """Adding a transaction dated after all existing ones appends it."""
        txn = _make_txn("2024-03-01", "New expense",
                        "expenses:misc", "£50.00", "assets:bank:checking")
        self.doc.add_transaction(txn)
        self.assertTrue(self.doc.dirty)
        self.assertEqual(len(self.doc.journal.transactions), 6)
        self.assertIsNotNone(txn.source_span)
        self.assertGreater(txn.source_span.start_line, 23)

    def test_add_transaction_end_span_correct(self):
        txn = _make_txn("2024-03-01", "New expense",
                        "expenses:misc", "£50.00", "assets:bank:checking")
        self.doc.add_transaction(txn)
        # The new transaction should occupy exactly len(transaction_to_text lines) lines
        from PyLedger.writer import transaction_to_text
        expected_lines = len(transaction_to_text(txn).splitlines())
        span_len = txn.source_span.end_line - txn.source_span.start_line + 1
        self.assertEqual(span_len, expected_lines)

    def test_add_transaction_middle_shifts_later_spans(self):
        """Adding mid-journal shifts all later transactions' spans."""
        original_last_span = self.doc.journal.transactions[-1].source_span
        txn = _make_txn("2024-01-03", "Mid insert",
                        "expenses:food", "£10.00", "assets:bank:checking")
        self.doc.add_transaction(txn)
        # The Coffee shop transaction (originally last) should have shifted
        coffee = next(t for t in self.doc.journal.transactions if t.description == "Coffee shop")
        self.assertGreater(coffee.source_span.start_line, original_last_span.start_line)

    def test_add_transaction_lines_length_increases(self):
        original_len = len(self.doc.lines)
        txn = _make_txn("2024-03-01", "Test",
                        "expenses:misc", "£5.00", "assets:bank:checking")
        self.doc.add_transaction(txn)
        self.assertGreater(len(self.doc.lines), original_len)


class TestEditorDocumentUpdateTransaction(unittest.TestCase):

    def setUp(self):
        self.doc = EditorDocument(str(FIXTURE))

    def test_update_transaction_content(self):
        original = self.doc.journal.transactions[0]  # Opening balance
        span = original.source_span
        updated = Transaction(
            date=original.date,
            description="Updated opening",
            postings=list(original.postings),
        )
        self.doc.update_transaction(original, updated)
        self.assertTrue(self.doc.dirty)
        # The description in lines should have changed
        header_line = self.doc.lines[span.start_line - 1]
        self.assertIn("Updated opening", header_line)

    def test_update_transaction_same_size_no_shift(self):
        """Updating to a transaction with the same number of lines causes no shift."""
        original = self.doc.journal.transactions[0]
        later = self.doc.journal.transactions[1]
        later_start_before = later.source_span.start_line

        updated = Transaction(
            date=original.date,
            description="Updated opening",
            postings=list(original.postings),
        )
        self.doc.update_transaction(original, updated)
        # Later transaction's span should not shift (same size)
        later_after = next(
            t for t in self.doc.journal.transactions if t.description == "Salary"
        )
        self.assertEqual(later_after.source_span.start_line, later_start_before)

    def test_update_transaction_larger_shifts_later(self):
        """Adding a posting to a transaction shifts all subsequent transactions."""
        original = self.doc.journal.transactions[0]  # 2 postings → 3 lines
        later_start_before = self.doc.journal.transactions[1].source_span.start_line

        extra_posting = Posting(
            account="equity:other",
            amount=Amount(Decimal("0"), "£"),
        )
        updated = Transaction(
            date=original.date,
            description=original.description,
            postings=list(original.postings) + [extra_posting],
        )
        self.doc.update_transaction(original, updated)
        salary = next(
            t for t in self.doc.journal.transactions if t.description == "Salary"
        )
        self.assertGreater(salary.source_span.start_line, later_start_before)

    def test_update_transaction_span_updated(self):
        original = self.doc.journal.transactions[0]
        updated = Transaction(
            date=original.date,
            description=original.description,
            postings=list(original.postings),
        )
        self.doc.update_transaction(original, updated)
        self.assertIsNotNone(updated.source_span)
        self.assertEqual(updated.source_span.start_line, original.source_span.start_line)


class TestEditorDocumentDeleteTransaction(unittest.TestCase):

    def setUp(self):
        self.doc = EditorDocument(str(FIXTURE))

    def test_delete_transaction(self):
        txn = self.doc.journal.transactions[0]
        self.doc.delete_transaction(txn)
        self.assertTrue(self.doc.dirty)
        self.assertEqual(len(self.doc.journal.transactions), 4)

    def test_delete_transaction_shifts_later_spans(self):
        """Deleting a transaction shifts all later transactions' spans backward."""
        first = self.doc.journal.transactions[0]
        second_start_before = self.doc.journal.transactions[1].source_span.start_line
        first_size = first.source_span.end_line - first.source_span.start_line + 1 + 1  # +1 blank

        self.doc.delete_transaction(first)
        salary = self.doc.journal.transactions[0]  # was second, now first
        self.assertEqual(salary.source_span.start_line, second_start_before - first_size)

    def test_delete_removes_blank_separator(self):
        """Deleting a transaction also removes the trailing blank separator line."""
        original_lines = len(self.doc.lines)
        txn = self.doc.journal.transactions[0]
        block_size = txn.source_span.end_line - txn.source_span.start_line + 1

        self.doc.delete_transaction(txn)
        # Should have removed the block + the blank separator
        self.assertLessEqual(len(self.doc.lines), original_lines - block_size)

    def test_delete_all_transactions(self):
        txns = list(self.doc.journal.transactions)
        for txn in txns:
            self.doc.delete_transaction(txn)
        self.assertEqual(len(self.doc.journal.transactions), 0)


class TestEditorDocumentReload(unittest.TestCase):

    def test_reload_resets_dirty(self):
        doc = EditorDocument(str(FIXTURE))
        txn = _make_txn("2024-03-01", "Test",
                        "expenses:misc", "£5.00", "assets:bank:checking")
        doc.add_transaction(txn)
        self.assertTrue(doc.dirty)
        doc.reload()
        self.assertFalse(doc.dirty)

    def test_reload_restores_original(self):
        doc = EditorDocument(str(FIXTURE))
        txn = _make_txn("2024-03-01", "Test",
                        "expenses:misc", "£5.00", "assets:bank:checking")
        doc.add_transaction(txn)
        doc.reload()
        self.assertEqual(len(doc.journal.transactions), 5)


class TestEditorDocumentSave(unittest.TestCase):

    def test_save_writes_file(self):
        with tempfile.NamedTemporaryFile(
            suffix=".journal", delete=False, mode="w", encoding="utf-8"
        ) as f:
            f.write(FIXTURE.read_text(encoding="utf-8"))
            tmp_path = f.name

        try:
            doc = EditorDocument(tmp_path)
            txn = _make_txn("2024-03-01", "Saved transaction",
                            "expenses:misc", "£7.00", "assets:bank:checking")
            doc.add_transaction(txn)
            doc.save()
            self.assertFalse(doc.dirty)
            content = Path(tmp_path).read_text(encoding="utf-8")
            self.assertIn("Saved transaction", content)
        finally:
            Path(tmp_path).unlink(missing_ok=True)

    def test_save_reload_roundtrip(self):
        with tempfile.NamedTemporaryFile(
            suffix=".journal", delete=False, mode="w", encoding="utf-8"
        ) as f:
            f.write(FIXTURE.read_text(encoding="utf-8"))
            tmp_path = f.name

        try:
            doc = EditorDocument(tmp_path)
            txn = _make_txn("2024-03-01", "RT transaction",
                            "expenses:misc", "£8.00", "assets:bank:checking")
            doc.add_transaction(txn)
            doc.save()
            doc.reload()
            self.assertFalse(doc.dirty)
            self.assertEqual(len(doc.journal.transactions), 6)
        finally:
            Path(tmp_path).unlink(missing_ok=True)


class TestEditorDocumentValidate(unittest.TestCase):

    def test_validate_balanced(self):
        doc = EditorDocument(str(FIXTURE))
        txn = _make_txn("2024-01-01", "Balanced",
                        "assets:bank:checking", "£100.00", "equity:opening-balances")
        errors = doc.validate_transaction(txn)
        self.assertEqual(errors, [])

    def test_validate_unbalanced(self):
        doc = EditorDocument(str(FIXTURE))
        txn = Transaction(
            date=datetime.date(2024, 1, 1),
            description="Unbalanced",
            postings=[
                Posting(account="assets:bank:checking", amount=Amount(Decimal("100"), "£")),
                Posting(account="expenses:misc", amount=Amount(Decimal("50"), "£")),
            ],
        )
        errors = doc.validate_transaction(txn)
        self.assertEqual(len(errors), 1)
        self.assertIsInstance(errors[0], CheckError)
        self.assertEqual(errors[0].check_name, "autobalanced")

    def test_validate_elided(self):
        doc = EditorDocument(str(FIXTURE))
        txn = Transaction(
            date=datetime.date(2024, 1, 1),
            description="Elided",
            postings=[
                Posting(account="assets:bank:checking", amount=Amount(Decimal("100"), "£")),
                Posting(account="expenses:misc"),  # elided
            ],
        )
        errors = doc.validate_transaction(txn)
        self.assertEqual(errors, [])


if __name__ == "__main__":
    unittest.main()
