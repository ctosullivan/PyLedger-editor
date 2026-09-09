"""View-filter engine for JournalEditor: Ctrl+L cleared/uncleared cycle and
the Ctrl+O criteria filter (Phase 3 of the next-release plan).

Split out of transaction_table.py (Phase 2) once that module passed the
Module Size Rule threshold. Ctrl+L and Ctrl+O are two INDEPENDENT
dimensions that COMBINE with AND when both are active — e.g. "Cleared
only" narrowed further by a Ctrl+O account filter shows only transactions
that are both cleared AND match the account. Either can be adjusted or
cleared without disturbing the other. (Originally implemented as mutually
exclusive in Phase 3 — reversed 2026-09-09 per UAT feedback; see
planning/next-release-phase-plan.md's Phase 3 "Interaction with Ctrl+L"
note for the history.)
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

        self._view_filter_mode: int = 0          # 0=All, 1=Cleared, 2=Unreconciled
                                                   # — Ctrl+L's own dimension ONLY;
                                                   #   independent of _active_predicate
        self._filter_journal: object | None = None
        self._filter_visible_indices: list[int] = []
        self._filter_non_txn_blocks: list[str] = []
        self._active_predicate: Callable[[object], bool] | None = None
        # ^ Ctrl+O's own dimension. None means no criteria filter active.
        #   Combines (AND) with _view_filter_mode in _apply_view_filter — see
        #   the _filter_is_active property for what "any filter active" means.
    """

    @property
    def _filter_is_active(self) -> bool:
        """True if either dimension (Ctrl+L's mode or Ctrl+O's predicate)
        is currently filtering the view."""
        return self._view_filter_mode != 0 or self._active_predicate is not None

    def action_cycle_view_filter(self) -> None:
        """Cycle editor view: All → Cleared → Unreconciled → All (Ctrl+L).

        Combines (AND) with any active Ctrl+O criteria filter rather than
        replacing it — the two dimensions are independent (see class
        docstring). Snapshots the full journal only when entering filtered
        mode from a state where NEITHER dimension was active; otherwise
        merges pending edits before recomputing visibility.
        """
        textarea = self.query_one("#journal_textarea", LedgerTextArea)

        if self._filter_is_active:
            self._merge_filtered_edits(textarea)
        else:
            self._snapshot_journal(textarea)

        self._view_filter_mode = (self._view_filter_mode + 1) % 3
        self._apply_view_filter(textarea)

    def apply_criteria_filter(self, predicate: Callable[[object], bool]) -> None:
        """Set (or replace) the Ctrl+O criteria predicate.

        Combines (AND) with any active Ctrl+L cleared/uncleared mode
        rather than replacing it. Snapshots the full journal only when
        entering filtered mode from a state where NEITHER dimension was
        active; otherwise merges pending edits before recomputing
        visibility with the new predicate.

        Args:
            predicate: called with each ledgerkit Transaction; True keeps it
                visible. Typically built by
                ledgerkit_editor.utils.query_match.build_transaction_predicate().
        """
        textarea = self.query_one("#journal_textarea", LedgerTextArea)

        if self._filter_is_active:
            self._merge_filtered_edits(textarea)
        else:
            self._snapshot_journal(textarea)

        self._active_predicate = predicate
        self._apply_view_filter(textarea)

    def clear_criteria_filter(self) -> None:
        """Remove just the Ctrl+O criteria predicate.

        Any active Ctrl+L cleared/uncleared mode is left untouched — this
        only fully restores the full journal if Ctrl+L was also at "All".
        No-op if no criteria filter is currently active.
        """
        if self._active_predicate is None:
            return
        textarea = self.query_one("#journal_textarea", LedgerTextArea)
        self._merge_filtered_edits(textarea)
        self._active_predicate = None
        self._apply_view_filter(textarea)

    def _snapshot_journal(self, textarea: LedgerTextArea) -> None:
        """Parse and snapshot the full journal when entering filtered mode
        from a state where neither Ctrl+L nor Ctrl+O was active — shared by
        action_cycle_view_filter and apply_criteria_filter."""
        import ledgerkit  # noqa: PLC0415
        from ledgerkit_editor.utils.ledger_io import split_journal_segments  # noqa: PLC0415

        self._filter_journal, _ = ledgerkit.parse_string_lenient(textarea.text)
        self._filter_non_txn_blocks, _ = split_journal_segments(
            textarea.text, self._filter_journal.transactions  # type: ignore[union-attr]
        )

    def _apply_view_filter(self, textarea: LedgerTextArea) -> None:
        """Rebuild textarea content for the current combined filter state.

        Restores the full journal when NEITHER dimension is active.
        Otherwise shows transactions matching BOTH the Ctrl+L cleared-mode
        (if != 0) AND the Ctrl+O predicate (if set) — an AND combination,
        not either replacing the other. Both branches re-apply the same
        commodity-formatting and column-alignment pass action_save() uses,
        so entering/exiting a filter doesn't itself change the document's
        formatting or trip the modified indicator (UAT: an empty/no-op
        filter round-trip was previously reformatting amounts).
        """
        import ledgerkit  # noqa: PLC0415
        from ledgerkit_editor.utils.commodity_format import (  # noqa: PLC0415
            apply_commodity_styles,
            extract_commodity_styles,
        )
        from ledgerkit_editor.utils.ledger_io import align_posting_amounts  # noqa: PLC0415

        journal = self._filter_journal

        if not self._filter_is_active:
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

            def _matches(tx: object) -> bool:
                if self._view_filter_mode != 0:
                    want_cleared = self._view_filter_mode == 1
                    if bool(tx.cleared) != want_cleared:  # type: ignore[union-attr]
                        return False
                if self._active_predicate is not None and not self._active_predicate(tx):
                    return False
                return True

            visible: list[tuple[int, object]] = [
                (i, tx) for i, tx in enumerate(journal.transactions) if _matches(tx)
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
        """Refresh the ViewFilterBar label to describe whichever
        dimension(s) are currently active, combined, plus a
        visible/total transaction count while a filter is active."""
        try:
            bar = self.query_one(ViewFilterBar)
        except Exception:  # noqa: BLE001
            return

        visible_count: int | None = None
        total_count: int | None = None
        if self._filter_is_active and self._filter_journal is not None:
            total_count = len(self._filter_journal.transactions)  # type: ignore[union-attr]
            visible_count = len(self._filter_visible_indices)

        bar.set_combined(
            self._view_filter_mode,
            self._active_predicate is not None,
            visible_count,
            total_count,
        )
