"""Main editing surface: a full-text editor for hledger journal files.

Shows raw journal text in a TextArea. Recognises transaction header and
posting lines at the cursor position to drive the register panel via
CursorAccountChanged messages.
"""

from __future__ import annotations

import re
from pathlib import Path

from textual.app import ComposeResult
from textual.binding import Binding
from textual.message import Message
from textual.widget import Widget
from textual.widgets import TextArea

__all__ = ["JournalEditor"]

# Purpose: parse an hledger transaction header line to extract and cycle the
#   status flag while preserving the date, code, description, and comments.
# Group breakdown:
#   group 1 — date segment (YYYY-MM-DD or YYYY/MM/DD)
#   group 2 — status flag (* or !) — absent (None) when the transaction is uncleared
#   group 3 — remainder: optional code (INV-42), description, inline comment
# Edge cases: date-only lines match with empty group 3; posting lines (leading
#   whitespace) must never be passed here — the caller is responsible for that guard.
_TXN_HEADER_RE = re.compile(
    r"^(\d{4}[-/]\d{2}[-/]\d{2})\s*(\*|!)?\s*(.*)"
)

# Purpose: split an hledger posting line at the account/amount boundary.
#   hledger requires at least two spaces (or a tab) between the account name
#   and the amount so that account names with single spaces are unambiguous.
# Edge cases: elided postings (no amount) produce a single-element split,
#   returning the full stripped line as the account name. Caller must strip
#   the leading indent before splitting.
_POSTING_SPLIT_RE = re.compile(r"\s{2,}|\t")


def _cycle_flag_in_header(line: str) -> str:
    """Return line with the cleared/pending flag cycled: none → ! → * → none.

    Returns the original line unchanged if it does not match the header format.
    """
    m = _TXN_HEADER_RE.match(line)
    if not m:
        return line
    date_str, current_flag, rest = m.group(1), m.group(2), m.group(3)
    if current_flag is None:
        new_flag: str | None = "!"
    elif current_flag == "!":
        new_flag = "*"
    else:
        new_flag = None

    parts = [date_str]
    if new_flag:
        parts.append(new_flag)
    if rest:
        parts.append(rest)
    return " ".join(parts)


def _extract_account_from_line(line: str) -> str | None:
    """Return the account name from an hledger posting line, or None.

    Returns None for blank lines and non-posting lines (no leading whitespace).
    """
    if not line or not line[0].isspace():
        return None
    stripped = line.lstrip()
    if not stripped:
        return None
    parts = _POSTING_SPLIT_RE.split(stripped, maxsplit=1)
    account = parts[0].strip()
    return account if account else None


def _account_at_cursor(textarea: TextArea) -> str | None:
    """Return the account name at the TextArea's current cursor row, or None."""
    row, _ = textarea.cursor_location
    lines = textarea.text.splitlines()
    if row >= len(lines):
        return None
    return _extract_account_from_line(lines[row])


# Purpose: locate the start and end rows of the hledger transaction block
#   containing the given row. A block begins at the first non-indented,
#   non-blank line at or above `row` (the header) and ends at the last
#   consecutive indented line below the header (the postings).
# Returns: (start_row, end_row) — both are valid indices into `lines`.
# Edge cases: blank lines between postings are treated as block terminators;
#   a row with no header above it returns (0, end_row); an empty list
#   returns (0, 0); `row` is clamped to [0, len(lines)-1].
def _find_transaction_block(lines: list[str], row: int) -> tuple[int, int]:
    """Return (start_row, end_row) of the transaction block containing row."""
    if not lines:
        return (0, 0)
    row = max(0, min(row, len(lines) - 1))
    start = row
    while start > 0 and (not lines[start] or lines[start][0].isspace()):
        start -= 1
    end = start
    total = len(lines)
    while end + 1 < total:
        next_line = lines[end + 1]
        if not next_line or not next_line[0].isspace():
            break
        end += 1
    return (start, end)


class JournalEditor(Widget):
    """Full-text editor for hledger journal files.

    Loads the raw journal file into a TextArea. Recognises transaction header
    and posting lines at the cursor to post CursorAccountChanged messages.
    Ctrl+S validates, sorts transactions by date, and writes back to disk.

    Args:
        journal_path: Absolute path to the journal file being edited.
    """

    BINDINGS = [
        Binding("ctrl+s", "save", "Save", key_display="Ctrl+S"),
        Binding("ctrl+r", "toggle_cleared", "Toggle cleared", key_display="Ctrl+R"),
        Binding("escape", "blur_editor", "Unfocus"),
        Binding("ctrl+t", "select_transaction_block", "Select transaction",
                show=False, priority=True),
        Binding("ctrl+home", "cursor_to_start", "Start of file",
                show=False, priority=True),
        Binding("ctrl+end", "cursor_to_end", "End of file",
                show=False, priority=True),
        Binding("ctrl+a", "select_all", "Select all",
                show=False, priority=True),
    ]

    DEFAULT_CSS = """
    JournalEditor {
        layout: vertical;
    }
    JournalEditor > TextArea {
        height: 1fr;
    }
    """

    class SaveCompleted(Message):
        """Posted after a successful Ctrl+S save so the balance sidebar can refresh."""

    class CursorAccountChanged(Message):
        """Posted when the account under the text cursor changes (or becomes None)."""

        def __init__(self, account: str | None) -> None:
            super().__init__()
            self.account = account

    def __init__(self, journal_path: Path) -> None:
        """Initialise with the resolved absolute journal file path.

        Args:
            journal_path: Absolute path to the .journal or .ledger file to edit.
        """
        super().__init__()
        self.journal_path = journal_path
        self._current_account: str | None = None

    def compose(self) -> ComposeResult:
        """Render a full-height TextArea for journal editing."""
        yield TextArea(id="journal_textarea", show_line_numbers=True)

    def on_mount(self) -> None:
        """Load the raw journal text into the TextArea on first render."""
        import PyLedger  # noqa: PLC0415

        doc = PyLedger.EditorDocument(str(self.journal_path))
        self.query_one("#journal_textarea", TextArea).load_text("\n".join(doc.lines))

    # ------------------------------------------------------------------
    # Cursor tracking
    # ------------------------------------------------------------------

    def on_text_area_selection_changed(self, event: TextArea.SelectionChanged) -> None:
        """Detect account-name changes as the cursor moves through the text."""
        new_account = _account_at_cursor(event.text_area)
        if new_account != self._current_account:
            self._current_account = new_account
            self.post_message(self.CursorAccountChanged(new_account))

    # ------------------------------------------------------------------
    # Key actions
    # ------------------------------------------------------------------

    def action_blur_editor(self) -> None:
        """Return focus to the parent app on Escape."""
        self.app.set_focus(None)

    def action_toggle_cleared(self) -> None:
        """Cycle the flag on the transaction header line at the cursor.

        Only acts on non-indented (header) lines. Posting lines are ignored.
        Cycle order: no flag → '!' → '*' → no flag.
        """
        textarea = self.query_one("#journal_textarea", TextArea)
        row, _ = textarea.cursor_location
        lines = textarea.text.splitlines()
        if row >= len(lines):
            return
        line = lines[row]
        if not line or line[0].isspace():
            return
        new_line = _cycle_flag_in_header(line)
        if new_line != line:
            textarea.replace(new_line, (row, 0), (row, len(line)))

    def action_save(self) -> None:
        """Validate, sort by date, and write the journal to disk.

        Notifications are shown for parse and check errors but do not block the
        write. The cursor row is restored after content is replaced.
        """
        import PyLedger  # noqa: PLC0415

        textarea = self.query_one("#journal_textarea", TextArea)
        text = textarea.text
        journal, parse_errors = PyLedger.parse_string_lenient(text)

        for err in parse_errors:
            self.app.notify(str(err), severity="warning")

        journal.transactions.sort(key=lambda t: t.date)
        sorted_text = PyLedger.journal_to_text(journal)

        saved_loc = textarea.cursor_location
        textarea.load_text(sorted_text)

        lines = sorted_text.splitlines()
        max_row = max(0, len(lines) - 1)
        textarea.move_cursor((min(saved_loc[0], max_row), saved_loc[1]))

        Path(self.journal_path).write_text(sorted_text, encoding="utf-8")

        for err in PyLedger.checks.run_basic_checks(journal):
            self.app.notify(err.message, severity="warning")

        self.post_message(self.SaveCompleted())
        self.app.notify("Saved", severity="information")

    def action_select_transaction_block(self) -> None:
        """Select the entire transaction block containing the cursor (Ctrl+T)."""
        from textual.document._document import Selection  # noqa: PLC0415

        textarea = self.query_one("#journal_textarea", TextArea)
        row, _ = textarea.cursor_location
        lines = textarea.text.splitlines()
        if not lines:
            return
        start_row, end_row = _find_transaction_block(lines, row)
        end_col = len(lines[end_row]) if end_row < len(lines) else 0
        textarea.selection = Selection((start_row, 0), (end_row, end_col))

    def action_cursor_to_start(self) -> None:
        """Move cursor to the very start of the file (Ctrl+Home)."""
        self.query_one("#journal_textarea", TextArea).move_cursor((0, 0))

    def action_cursor_to_end(self) -> None:
        """Move cursor to the very end of the file (Ctrl+End)."""
        textarea = self.query_one("#journal_textarea", TextArea)
        lines = textarea.text.splitlines()
        last_row = max(0, len(lines) - 1)
        last_col = len(lines[last_row]) if lines else 0
        textarea.move_cursor((last_row, last_col))

    def action_select_all(self) -> None:
        """Select all text in the editor (Ctrl+A)."""
        from textual.document._document import Selection  # noqa: PLC0415

        textarea = self.query_one("#journal_textarea", TextArea)
        lines = textarea.text.splitlines()
        if not lines:
            return
        last_row = len(lines) - 1
        textarea.selection = Selection((0, 0), (last_row, len(lines[last_row])))

