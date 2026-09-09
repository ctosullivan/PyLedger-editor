"""Tab autocomplete for JournalEditor (Phase 4a of the next-release plan).

Suggests account names (on a posting line, while typing the account) and
payee/description names (on a transaction header, past the date/flag/code)
from a JournalIndex (utils/journal_index.py) built on file load and after
each save.

Deliberately Tab-cycling (bash-style: Tab inserts the first match, Tab
again cycles to the next) rather than an Up/Down-navigable dropdown — see
AutocompleteMixin's docstring for why. The suggestion bar itself
(AutocompletePopup, autocomplete_popup.py) never takes focus; this mixin
drives it entirely, so the cursor never leaves the LedgerTextArea.
"""

from __future__ import annotations

from ledgerkit_editor.highlighting.highlighter import LineKind, _XACT_HEADER_RE

__all__ = ["AutocompleteMixin", "_completion_context"]


def _completion_context(
    line: str, col: int, kind: LineKind
) -> tuple[str, str, int] | None:
    """Return (index_kind, partial_text, start_col) for the completable token
    under the cursor, or None if the cursor isn't in a completable position.

    index_kind is "account" for a POSTING line, while the cursor is still
    within the account-name portion (before the 2-space/tab amount
    separator) — matching _extract_account_from_line's own notion of where
    the account name ends. It's "payee" for an XACT_HEADER line, but only
    once the cursor has reached the payee/description field (i.e. past the
    date, cleared/pending flag, and any (CODE)) — completing a date or flag
    makes no sense. Any other line kind, or a cursor outside those windows,
    returns None.
    """
    if kind == LineKind.POSTING:
        stripped = line.lstrip()
        indent = len(line) - len(stripped)
        if col < indent:
            return None
        from ledgerkit_editor.widgets.transaction_table import _POSTING_SPLIT_RE  # noqa: PLC0415

        sep = _POSTING_SPLIT_RE.search(stripped)
        account_end = indent + (sep.start() if sep else len(stripped))
        if col > account_end:
            return None
        return ("account", line[indent:col], indent)

    if kind == LineKind.XACT_HEADER:
        m = _XACT_HEADER_RE.match(line)
        if not m:
            return None
        payee_start = m.start(4)
        payee_text = m.group(4) or ""
        payee_end = payee_start + len(payee_text.rstrip())
        if col < payee_start or col > payee_end:
            return None
        return ("payee", line[payee_start:col], payee_start)

    return None


class AutocompleteMixin:
    """JournalEditor mixin providing Tab autocomplete.

    Expects "#journal_textarea" (LedgerTextArea) and an AutocompletePopup
    child, both provided by JournalEditor.compose(). Also expects the host
    to initialise (see date_shift.DateShiftMixin for the same convention —
    mixins here don't own __init__):

        self._journal_index: JournalIndex = JournalIndex()
        self._autocomplete_anchor: tuple[int, int] | None = None

    and to call rebuild_journal_index() after loading text and after each
    save (JournalEditor.on_mount / action_save) — the index is a snapshot,
    not recomputed per keystroke, since journals can run to 10,000+
    transactions (see utils/journal_index.py's module docstring).

    Deliberately Tab-cycling rather than a Up/Down-navigable dropdown:
    Up/Down are ordinary cursor-movement keys used constantly throughout
    the editor. Binding them globally at the JournalEditor level (the same
    way Shift+Up/Down already is, for date shifting) would intercept them
    everywhere JournalEditor is an ancestor in the DOM — including while
    the search bar's Input has focus, since SearchBar is a child of
    JournalEditor — for a feature (popup navigation) that only matters in
    one specific, currently-rare state. Tab avoids that risk entirely: it's
    the one key this mixin needs to claim, and Phase 1's bug-fix work
    already established that Tab is otherwise a near-no-op in this
    single-pane editor (no second panel left to cycle focus to).
    """

    def rebuild_journal_index(self) -> None:
        """Recompute self._journal_index from the current TextArea text."""
        from ledgerkit_editor.utils.journal_index import build_journal_index  # noqa: PLC0415
        from ledgerkit_editor.widgets.ledger_textarea import LedgerTextArea  # noqa: PLC0415

        textarea = self.query_one("#journal_textarea", LedgerTextArea)
        self._journal_index = build_journal_index(textarea.text)

    def action_autocomplete(self) -> None:
        """Tab: insert/cycle a completion, or fall through to focus-cycling."""
        from ledgerkit_editor.widgets.autocomplete_popup import AutocompletePopup  # noqa: PLC0415
        from ledgerkit_editor.widgets.ledger_textarea import LedgerTextArea  # noqa: PLC0415

        textarea = self.query_one("#journal_textarea", LedgerTextArea)
        popup = self.query_one(AutocompletePopup)

        if not textarea.has_focus:
            # Tab pressed while some other widget (e.g. the search input)
            # has focus — autocomplete doesn't apply; behave like ordinary
            # Tab always did before this mixin existed.
            self.app.action_focus_next()
            return

        if popup.is_showing and self._autocomplete_cursor_matches(textarea, popup):
            self._cycle_autocomplete(textarea, popup)
            return

        self._start_autocomplete(textarea, popup)

    def _start_autocomplete(self, textarea, popup) -> None:
        """Compute candidates for the token at the cursor and insert the first.

        Falls through to normal focus-cycling (hiding any stale popup
        first) when the cursor isn't in a completable position or there are
        no matches — Tab behaves exactly as it did before this mixin
        existed in that case.
        """
        row, col = textarea.cursor_location
        line_infos = textarea._highlighter._line_infos

        def _fallthrough() -> None:
            popup.hide()
            self.app.action_focus_next()

        if row >= len(line_infos):
            _fallthrough()
            return

        lines = textarea.text.splitlines()
        line = lines[row] if row < len(lines) else ""
        ctx = _completion_context(line, col, line_infos[row].kind)
        if ctx is None:
            _fallthrough()
            return

        index_kind, partial, start_col = ctx
        candidates = (
            self._journal_index.matching_accounts(partial)
            if index_kind == "account"
            else self._journal_index.matching_payees(partial)
        )
        if not candidates:
            _fallthrough()
            return

        first = candidates[0]
        textarea.replace(first, (row, start_col), (row, col))
        textarea.move_cursor((row, start_col + len(first)), select=False)
        popup.show(candidates)
        self._autocomplete_anchor = (row, start_col)

    def _cycle_autocomplete(self, textarea, popup) -> None:
        """Replace the currently-inserted candidate with the next one."""
        row, anchor_col = self._autocomplete_anchor  # type: ignore[misc]
        current = popup.selected_candidate or ""
        next_candidate = popup.cycle_next()
        if next_candidate is None:
            return
        end_col = anchor_col + len(current)
        textarea.replace(next_candidate, (row, anchor_col), (row, end_col))
        textarea.move_cursor((row, anchor_col + len(next_candidate)), select=False)

    def _autocomplete_cursor_matches(self, textarea, popup) -> bool:
        """True if the cursor is still right after the just-inserted candidate.

        Distinguishes "Tab again to cycle" from "the user moved on (typed
        more, moved the cursor) and this Tab is a fresh request" — if the
        cursor isn't exactly where the last insertion left it, this is a
        new completion, not a continuation.
        """
        if self._autocomplete_anchor is None:
            return False
        row, anchor_col = self._autocomplete_anchor
        current = popup.selected_candidate or ""
        return textarea.cursor_location == (row, anchor_col + len(current))

    def dismiss_autocomplete(self) -> None:
        """Hide the suggestion bar and forget the current anchor, if any."""
        from ledgerkit_editor.widgets.autocomplete_popup import AutocompletePopup  # noqa: PLC0415

        try:
            popup = self.query_one(AutocompletePopup)
        except Exception:  # noqa: BLE001
            return
        popup.hide()
        self._autocomplete_anchor = None
