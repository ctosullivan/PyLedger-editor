"""View-filter engine for JournalEditor (Ctrl+L cleared/uncleared cycle).

Split out of transaction_table.py (Phase 2 of the next-release plan — see
planning/next-release-phase-plan.md) once that module passed the Module Size
Rule threshold.

Also the engine the Transaction Filter feature (Ctrl+O, Phase 3) is planned
to reuse: parse-hide-merge-restore is the same mechanism regardless of
whether visibility is decided by cleared state or by a criteria predicate.
_apply_view_filter's cleared/uncleared branch is where that generalisation
will happen — see the class docstring below.
"""

from __future__ import annotations

from ledgerkit_editor.widgets.ledger_textarea import LedgerTextArea
from ledgerkit_editor.widgets.view_filter_bar import ViewFilterBar

__all__ = ["ViewFilterMixin"]


class ViewFilterMixin:
    """JournalEditor mixin providing the Ctrl+L view-filter cycle.

    Expects "#journal_textarea" (a LedgerTextArea) and a ViewFilterBar child,
    exactly as JournalEditor.compose() provides. Also expects the host to
    initialise this instance state (currently done in JournalEditor.__init__,
    since mixins here don't own __init__ — see date_shift.DateShiftMixin for
    the same convention):

        self._view_filter_mode: int = 0          # 0=All, 1=Cleared, 2=Unreconciled
        self._filter_journal: object | None = None
        self._filter_visible_indices: list[int] = []
        self._filter_non_txn_blocks: list[str] = []
    """

    def action_cycle_view_filter(self) -> None:
        """Cycle editor view: All → Cleared → Unreconciled → All (Ctrl+L)."""
        import ledgerkit  # noqa: PLC0415

        textarea = self.query_one("#journal_textarea", LedgerTextArea)

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

    def _apply_view_filter(self, textarea: LedgerTextArea) -> None:
        """Rebuild textarea content from _filter_journal for the current mode."""
        import ledgerkit  # noqa: PLC0415

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
            else:
                full_text = textarea.text
            self._filter_journal = None
            self._filter_non_txn_blocks = []
            self._filter_visible_indices = []
            textarea.load_text(full_text)
        else:
            if journal is None:
                return
            want_cleared = self._view_filter_mode == 1
            visible: list[tuple[int, object]] = [
                (i, tx) for i, tx in enumerate(journal.transactions)
                if (tx.cleared if want_cleared else not tx.cleared)  # type: ignore[union-attr]
            ]
            self._filter_visible_indices = [i for i, _ in visible]
            parts = [ledgerkit.transaction_to_text(tx) for _, tx in visible]
            filtered_text = "\n".join(parts)
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
            self.query_one(ViewFilterBar).set_mode(self._view_filter_mode)
        except Exception:  # noqa: BLE001
            pass
