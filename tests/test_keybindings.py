"""Tests for ledger_editor.keybindings action stubs.

These are structural / smoke tests confirming the action methods exist and
are callable. Behavioural tests will be added when the widget implementations
are complete.
"""

from ledger_editor.keybindings.emacs_ledger import EmacsLedgerBindings
from ledger_editor.keybindings.office import OfficeBindings


class ConcreteOffice(OfficeBindings):
    """Minimal concrete subclass for instantiation in tests."""


class ConcreteEmacs(EmacsLedgerBindings):
    """Minimal concrete subclass for instantiation in tests."""


class TestOfficeBindingsExist:
    """Verify all Office action stubs are present."""

    def setup_method(self) -> None:
        self.obj = ConcreteOffice()

    def test_select_all(self) -> None:
        self.obj.action_select_all()

    def test_copy(self) -> None:
        self.obj.action_copy()

    def test_paste(self) -> None:
        self.obj.action_paste()

    def test_cut(self) -> None:
        self.obj.action_cut()

    def test_autofill(self) -> None:
        self.obj.action_autofill()

    def test_save(self) -> None:
        self.obj.action_save()

    def test_search_forward(self) -> None:
        self.obj.action_search_forward()

    def test_search_reverse(self) -> None:
        self.obj.action_search_reverse()

    def test_toggle_filter(self) -> None:
        self.obj.action_toggle_filter()

    def test_toggle_cleared(self) -> None:
        self.obj.action_toggle_cleared()


class TestEmacsBindingsExist:
    """Verify all Emacs Ledger-mode action stubs are present."""

    def setup_method(self) -> None:
        self.obj = ConcreteEmacs()

    def test_autocomplete(self) -> None:
        self.obj.action_autocomplete()

    def test_date_increment_day(self) -> None:
        self.obj.action_date_increment_day()

    def test_date_decrement_day(self) -> None:
        self.obj.action_date_decrement_day()

    def test_date_increment_month(self) -> None:
        self.obj.action_date_increment_month()

    def test_date_decrement_month(self) -> None:
        self.obj.action_date_decrement_month()

    def test_field_next(self) -> None:
        self.obj.action_field_next()

    def test_field_prev(self) -> None:
        self.obj.action_field_prev()

    def test_txn_next(self) -> None:
        self.obj.action_txn_next()

    def test_txn_prev(self) -> None:
        self.obj.action_txn_prev()

    def test_select_to_field_end(self) -> None:
        self.obj.action_select_to_field_end()

    def test_select_to_field_start(self) -> None:
        self.obj.action_select_to_field_start()

    def test_select_txn_above(self) -> None:
        self.obj.action_select_txn_above()

    def test_select_txn_below(self) -> None:
        self.obj.action_select_txn_below()

    def test_insert_prev_matching(self) -> None:
        self.obj.action_insert_prev_matching()

    def test_insert_next_matching(self) -> None:
        self.obj.action_insert_next_matching()

    def test_commit_transaction(self) -> None:
        self.obj.action_commit_transaction()

    def test_kill_line(self) -> None:
        self.obj.action_kill_line()
