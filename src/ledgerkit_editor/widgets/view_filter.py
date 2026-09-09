"""View-filter engine for JournalEditor: Ctrl+L cleared/uncleared cycle and
the Ctrl+O criteria filter (Phase 3 of the next-release plan).

Split out of transaction_table.py (Phase 2) once that module passed the
Module Size Rule threshold. Both Ctrl+L and Ctrl+O share the same
parse-hide-merge-restore engine — only how "which transactions are visible"
is decided differs: Ctrl+L uses the fixed cleared/uncleared check,
Ctrl+O uses an arbitrary predicate built by
ledgerkit_editor.utils.query_match.build_transaction_predicate(). The two
are mutually exclusive: activating either one first exits the other (see
apply_criteria_filter / action_cycle_view_filter).
"""

from __future__ import annotations

from typing import Callable

from ledgerkit_editor.widgets.ledger_textarea import LedgerTextArea
from ledgerkit_editor.widgets.view_filter_bar import ViewFilterBar

__all__ = ["ViewFilterMixin"]


class ViewFilterMixin:
    """JournalEditor mixin providing the Ctrl+L and Ctrl+O view filters.

    Expects "#journal_textarea" (a LedgerTextArea) and a ViewFilterBar child,
    exactly as JournalEditor.compose() provides. Also expects the host to
    initialise this instance state (currently done in JournalEditor.__init__,
    since mixins here don't own __init__ — see date_shift.DateShiftMixin for
    the same convention):

        self._view_filter_mode: int = 0          # 0=All, nonzero=filtered
        self._filter_journal: object | None = None
        self._filter_visible_indices: list[int] = []
        self._filter_non_txn_blocks: list[str] = []
        self._active_predicate: Callable[[object], bool] | None = None
        # ^ Ctrl+O sets this; when set, it overrides the cleared/uncleared
        #   check for _view_filter_mode != 0 (see _apply_view_filter). None
        #   means "no criteria filter active" — Ctrl+L's fixed 3-mode cycle
        #   applies as before.
    """

    def action_cycle_view_filter(self) -> None:
        """Cycle editor view: All → Cleared → Unreconciled → All (Ctrl+L).

        If a Ctrl+O criteria filter is active, this first exits it (restoring
        the full journal) and starts a fresh Ctrl+L cycle — the two filter
        mechanisms are mutually exclusive.
        """
        import ledgerkit  # noqa: PLC0415

        textarea = self.query_one("#journal_textarea", LedgerTextArea)

        if self._active_predicate is not None:
            self._exit_active_filter(textarea)

        if self._view_filter_mode == 0:
            # Entering a filtered view — snapshot the full journal and the
            # non-transaction blocks so directives/comments survive mode-0 restore.
            self._filter_journal, _ = ledgerkit.parse_string_lenient(textarea.text)
            from ledgerkit_editor.utils.ledger_io import split_journal_segments  # noqa: PLC0415
            self._filter_non_txn_blocks, _ = split_journal_segments(
                textarea.text, self._filter_journal.transactions  # type: ignore[union-attr]
            )
        else:
            # Already filtered — merge edits before switching.
            self._merge_filtered_edits(textarea)

        self._view_filter_mode = (self._view_filter_mode + 1) % 3
        self._apply_view_filter(textarea)

    def apply_criteria_filter(self, predicate: Callable[[object], bool]) -> None:
        """Enter (or replace) a Ctrl+O criteria-filter view using predicate.

        If a Ctrl+L cleared/uncleared filter is active, or a different
        criteria filter was already active, this first exits it (restoring
        the full journal, merging any edits) before applying the new one.

        Args:
            predicate: called with each ledgerkit Transaction; True keeps it
                visible. Typically built by
                ledgerkit_editor.utils.query_match.build_transaction_predicate().
        """
        import ledgerkit  # noqa: PLC0415

        textarea = self.query_one("#journal_textarea", LedgerTextArea)

        if self._view_filter_mode != 0 or self._active_predicate is not None:
            self._exit_active_filter(textarea)

        self._filter_journal, _ = ledgerkit.parse_string_lenient(textarea.text)
        from ledgerkit_editor.utils.ledger_io import split_journal_segments  # noqa: PLC0415
        self._filter_non_txn_blocks, _ = split_journal_segments(
            textarea.text, self._filter_journal.transactions  # type: ignore[union-attr]
        )
        self._active_predicate = predicate
        # Any nonzero value marks "a filter is showing a subset" for
        # action_save's merge-before-save check; the actual visibility rule
        # for mode != 0 is _active_predicate when set, not this number.
        self._view_filter_mode = 1
        self._apply_view_filter(textarea)

    def clear_criteria_filter(self) -> None:
        """Exit an active Ctrl+O criteria filter, restoring the full journal.

        No-op if no criteria filter is currently active.
        """
        if self._active_predicate is None:
            return
        textarea = self.query_one("#journal_textarea", LedgerTextArea)
        self._exit_active_filter(textarea)

    def _exit_active_filter(self, textarea: LedgerTextArea) -> None:
        """Merge edits and restore the full journal, clearing all filter state.

        Shared by action_cycle_view_filter and apply_criteria_filter/
        clear_criteria_filter whenever either mechanism needs to fully exit
        whatever filter (of either kind) is currently active before doing
        anything else.
        """
        self._merge_filtered_edits(textarea)
        self._active_predicate = None
        self._view_filter_mode = 0
        self._apply_view_filter(textarea)

    def _apply_view_filter(self, textarea: LedgerTextArea) -> None:
        """Rebuild textarea content from _filter_journal for the current mode.

        Both branches below re-apply the same commodity-formatting and
        column-alignment pass action_save() uses (utils.commodity_format /
        utils.ledger_io.align_posting_amounts), so that entering or exiting
        a filter doesn't itself change the document's formatting or trip
        the modified indicator — UAT found this: opening the criteria
        filter with every field blank was reformatting amounts and marking
        the file "modified" purely from the parse -> transaction_to_text()
        round-trip, which doesn't preserve source spacing on its own.
        """
        import ledgerkit  # noqa: PLC0415
        from ledgerkit_editor.utils.commodity_format import (  # noqa: PLC0415
            apply_commodity_styles,
            extract_commodity_styles,
        )
        from ledgerkit_editor.utils.ledger_io import align_posting_amounts  # noqa: PLC0415

        journal = self._filter_journal

        if self._view_filter_mode == 0:
            # Restore full journal, preserving directives/comments/blank-line
            # separators captured in _filter_non_txn_blocks at filter entry.
            if journal is not None:
                blocks = self._filter_non_txn_blocks
                txns = journal.transactions
                if blocks and len(blocks) == len(txns) + 1:
                    # Exact match: weave non-txn blocks between transactions.
                    txn_texts = [ledgerkit.transaction_to_text(t) for t in txns]
                    parts = [blocks[0]]
                    for i, txn_text in enumerate(txn_texts):
                        parts.append(txn_text)
                        parts.append(blocks[i + 1])
                    full_text = "".join(parts)
                elif blocks:
                    # Count mismatch (txns added/deleted in filtered view):
                    # preserve preamble, fall back to journal_to_text for body.
                    full_text = blocks[0] + ledgerkit.journal_to_text(journal)
                else:
                    full_text = ledgerkit.journal_to_text(journal)
                commodity_styles = extract_commodity_styles(journal)
                full_text = apply_commodity_styles(full_text, commodity_styles)
                full_text = align_posting_amounts(full_text)
            else:
                full_text = textarea.text
            self._filter_journal = None
            self._filter_non_txn_blocks = []
            self._filter_visible_indices = []
            textarea.load_text(full_text)
        else:
            if journal is None:
                return
            if self._active_predicate is not None:
                visible: list[tuple[int, object]] = [
                    (i, tx) for i, tx in enumerate(journal.transactions)
                    if self._active_predicate(tx)
                ]
            else:
                want_cleared = self._view_filter_mode == 1
                visible = [
                    (i, tx) for i, tx in enumerate(journal.transactions)
                    if (tx.cleared if want_cleared else not tx.cleared)  # type: ignore[union-attr]
                ]
            self._filter_visible_indices = [i for i, _ in visible]
            parts = [ledgerkit.transaction_to_text(tx) for _, tx in visible]
            filtered_text = "\n".join(parts)
            commodity_styles = extract_commodity_styles(journal)
            filtered_text = apply_commodity_styles(filtered_text, commodity_styles)
            filtered_text = align_posting_amounts(filtered_text)
            textarea.load_text(filtered_text)

        self._update_filter_bar()

    def _merge_filtered_edits(self, textarea: LedgerTextArea) -> None:
        """Merge textarea edits back into _filter_journal before a filter change."""
        import ledgerkit  # noqa: PLC0415

        if self._filter_journal is None:
            return
        visible_journal, _ = ledgerkit.parse_string_lenient(textarea.text)
        visible_txs = visible_journal.transactions
        all_txs: list = list(self._filter_journal.transactions)  # type: ignore[union-attr]

        # Replace tracked slots with edited versions.
        for slot, idx in enumerate(self._filter_visible_indices):
            if slot < len(visible_txs):
                all_txs[idx] = visible_txs[slot]

        # Append any newly added transactions beyond the original visible count.
        new_txs = visible_txs[len(self._filter_visible_indices):]
        all_txs.extend(new_txs)

        # Remove deleted transactions (visible slots with no counterpart in edited view).
        deleted = self._filter_visible_indices[len(visible_txs):]
        for idx in sorted(deleted, reverse=True):
            if idx < len(all_txs):
                del all_txs[idx]

        all_txs.sort(key=lambda tx: tx.date)  # type: ignore[union-attr]
        self._filter_journal.transactions = all_txs  # type: ignore[union-attr]

    def _update_filter_bar(self) -> None:
        """Refresh the ViewFilterBar label after a filter change."""
        try:
            bar = self.query_one(ViewFilterBar)
            if self._active_predicate is not None:
                bar.set_label("View: Filtered (Ctrl+O)")
            else:
                bar.set_mode(self._view_filter_mode)
        except Exception:  # noqa: BLE001
            pass
