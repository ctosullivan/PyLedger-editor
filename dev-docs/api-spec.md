# Internal API Specification

> **PROTECTED FILE** — Do not modify without explicit user approval.
> See CLAUDE.md §Unauthorised Change Rule.

This file documents the internal APIs exposed by `ledger_editor` modules.
It does NOT document PyLedger's own API — see
`vendor/pyledger/dev-docs/api-spec.md` for that.

---

## `ledger_editor.utils.file_resolver`

### `resolve_journal_file`

```python
def resolve_journal_file(cli_path: str | None) -> Path | None:
    """Return the resolved journal file path, or None if none is found.

    Resolution order:
      1. cli_path (if exists on disk)
      2. $LEDGER_FILE env var (if exists on disk)
      3. ~/.hledger.journal (if exists)
      4. None

    Args:
        cli_path: Raw path string from CLI, or None.

    Returns:
        Absolute Path, or None.
    """
```

---

## `ledger_editor.utils.date_parser`

### `parse_date`

```python
def parse_date(text: str, today: datetime.date | None = None) -> datetime.date:
    """Parse a smart date string into a datetime.date.

    Raises:
        DateParseError: if the string matches none of the supported patterns.
    """
```

### `parse_date_range`

```python
def parse_date_range(
    from_text: str | None,
    to_text: str | None,
    today: datetime.date | None = None,
) -> tuple[datetime.date | None, datetime.date | None]:
    """Parse an optional date-from / date-to pair.

    Raises:
        DateParseError: if either non-None string fails to parse.
    """
```

### `DateParseError`

```python
class DateParseError(ValueError): ...
```

---

## `ledger_editor.utils.ledger_io`

### `load_journal`

```python
def load_journal(path: Path) -> Journal:
    """Load via PyLedger.load(). Raises FileNotFoundError or ParseError."""
```

### `save_journal`

```python
def save_journal(path: Path, journal: Journal) -> None:
    """Serialise via PyLedger.journal_to_text() and write to path."""
```

---

## `ledger_editor.app`

### `LedgerApp`

```python
class LedgerApp(App[None]):
    """Root Textual application. Constructed with a resolved journal Path."""

    def __init__(self, journal_path: Path) -> None: ...
    def action_toggle_filter(self) -> None: ...
```

### `main`

```python
def main(argv: list[str] | None = None) -> None:
    """CLI entry point. Resolves journal, launches LedgerApp."""
```

---

## `ledger_editor.widgets.BalanceSidebar`

```python
class BalanceSidebar(Widget):
    def __init__(self, journal_path: Path) -> None: ...
    async def refresh_balances(self) -> None: ...
```

## `ledger_editor.widgets.TransactionTable`

```python
class TransactionTable(Widget):
    def __init__(self, journal_path: Path) -> None: ...
    def action_toggle_cleared(self) -> None: ...
    def action_save(self) -> None: ...
    def action_autofill(self) -> None: ...
```

## `ledger_editor.widgets.FilterPopup`

```python
class FilterPopup(Widget):
    def apply_filter(self) -> None: ...
```

---

## `ledger_editor.widgets.search_bar`

### `_build_offset_table`

```python
def _build_offset_table(text: str) -> list[int]:
    """Return a list of byte-start offsets for every line in text.

    Index i holds the character offset of line i within the full text.
    Used for O(log N) offset→(row, col) conversion via bisect.
    """
```

### `_offset_to_location`

```python
def _offset_to_location(
    offset: int, table: list[int]
) -> tuple[int, int]:
    """Convert a flat character offset to a (row, col) location.

    Args:
        offset: character offset within the document.
        table: offset table returned by _build_offset_table().

    Returns:
        (row, col) tuple (0-indexed).
    """
```

### `SearchBar`

```python
class SearchBar(Widget):
    """Incremental search bar docked inside JournalEditor.

    Hidden (display: none) by default; shown by open_bar().
    """

    def open_bar(self, initial_direction: int = 1) -> None:
        """Show the bar, focus the input, and begin searching.

        Args:
            initial_direction: 1 for forward (Ctrl+F), -1 for reverse (Ctrl+Shift+F).
        """

    def dismiss(self) -> None:
        """Clear highlights and hide the bar."""

    def advance(self, direction: int = 1) -> None:
        """Move to the next (direction=1) or previous (direction=-1) match."""

    def advance_to_transaction(self, direction: int = 1) -> None:
        """Jump to the next transaction block that contains a match (Alt+F3)."""
```

---

## `ledger_editor.widgets.reconcile_actions`

### `_find_transaction_header_above`

```python
def _find_transaction_header_above(
    line_infos: list, row: int
) -> int | None:
    """Walk line_infos backwards from row to find the nearest XACT_HEADER.

    Returns:
        Row index of the header, or None if no header found above.
    """
```

### `_build_reconcile_document`

```python
def _build_reconcile_document(
    transactions: list,
) -> tuple[str, dict[int, int]]:
    """Serialise transactions into a reconcile editor document.

    Returns:
        (text, line_to_tx) where line_to_tx maps each transaction's header
        line number → its index in the transactions list.
    """
```

### `ReconcileMixin`

```python
class ReconcileMixin:
    """Mixin providing reconcile-mode methods for JournalEditor."""

    def enter_reconcile_mode(self, account: str) -> None:
        """Load reconcile view for account, make textarea read-only."""

    def exit_reconcile_mode(self, commit: bool) -> None:
        """Exit reconcile mode. If commit=True, apply cleared flags to journal."""

    def action_commit_reconcile(self) -> None:
        """Ctrl+Enter: commit and exit reconcile mode."""

    def action_cancel_reconcile(self) -> None:
        """Escape: cancel and exit reconcile mode."""

    def action_reconcile_mark_all_cleared(self) -> None:
        """Ctrl+A in reconcile mode: mark all transactions cleared."""
```

---

## `ledger_editor.widgets.reconcile_bar`

### `ReconcileStatusBar`

```python
class ReconcileStatusBar(Widget):
    """One-line status bar shown above JournalEditor during reconcile mode.

    Displays: account | checked balance | target input | Δ delta.
    """

    class TargetChanged(Message):
        """Posted when the user edits the reconcile target amount."""
        target: Decimal

    def set_reconcile_data(self, account: str, transactions: list) -> None:
        """Initialise the bar for a new reconcile session."""
```

---

## `ledger_editor.widgets.reconcile_summary`

### `ReconcileSummary`

```python
class ReconcileSummary(Widget):
    """Four-value reconciliation summary shown in RegisterPanel during reconcile mode.

    Displays: cleared balance, unreconciled count/net, pending count/net,
    difference vs target.
    """

    def set_reconcile_data(self, account: str, transactions: list) -> None:
        """Initialise for a new reconcile session."""

    def refresh_totals(self, tx: object, account: str) -> None:
        """Recompute all summary values after a TransactionClearedToggled event."""

    def set_target(self, target: Decimal) -> None:
        """Update the target balance."""
```

---

## `ledger_editor.widgets.register_panel` (updated)

### `_cached_register_rows`

```python
@lru_cache(maxsize=32)
def _cached_register_rows(
    journal_path: str, account: str, mtime: float
) -> list[tuple[str, str, str, str]]:
    """Load and cache register rows from disk.

    Cache key includes mtime so rows are automatically invalidated after
    a Ctrl+S save. The live-update path (refresh_account_from_text) bypasses
    this cache and parses in-memory text directly.
    """
```

---

## `ledger_editor.widgets.ledger_textarea`

### `LedgerTextArea`

```python
class LedgerTextArea(TextArea):
    """TextArea subclass with hledger journal syntax highlighting and search.

    Drop-in replacement for TextArea. Overrides _build_highlight_map()
    (private Textual 8.2.5 API) to inject ledger token spans and search
    highlight spans into self._highlights on every edit.
    """

    def set_search_matches(
        self,
        matches: list[tuple[tuple[int, int], tuple[int, int]]],
        current: int,
    ) -> None:
        """Update search highlight state and repaint the widget.

        Args:
            matches: list of ((start_row, start_col), (end_row, end_col)) pairs.
            current: index of the focused match, or -1 to clear.
        """

    def _rebuild_ledger_theme(self) -> None:
        """Activate the correct TextAreaTheme for the current app theme.

        Uses the static Monokai Pro TextAreaTheme when app.theme == "monokai-pro",
        otherwise builds a generic bridge theme from the app CSS variables.
        """
```

---

## `ledger_editor.highlighting`

### `LineKind`

```python
class LineKind(Enum):
    """Classification of a single journal line."""
    BLANK, COMMENT, DIRECTIVE, XACT_HEADER, POSTING, UNKNOWN
```

### `LineInfo`

```python
@dataclass
class LineInfo:
    """Pre-computed classification and clearing state for one journal line."""
    kind: LineKind
    cleared: bool = False
    pending: bool = False
```

### `LedgerHighlighter`

```python
class LedgerHighlighter:
    """Regex-based hledger syntax highlighter (no Textual imports).

    Single O(N) scan via invalidate(); per-line queries are O(1).
    """

    def invalidate(self, text: str) -> None:
        """Re-scan the full document and cache LineInfo for every line."""

    def get_highlights(
        self, line_index: int, line_text: str
    ) -> list[tuple[int, int | None, str]]:
        """Return (start_col, end_col, token_name) spans for one line.

        end_col is None to mean "to end of line" (used for block overlays).
        Column offsets are Unicode codepoint positions.
        """
```

### `build_textarea_theme`

```python
def build_textarea_theme(app: App) -> TextAreaTheme:
    """Build a TextAreaTheme from the active app theme's CSS variables.

    Reads app.get_css_variables() (keys without '$' prefix) and maps each
    ledger token to the appropriate colour role. Falls back to '#888888'
    for text and 'transparent' for background if a variable is absent.

    Returns:
        A TextAreaTheme named "ledger".
    """
```

---

## `ledger_editor.themes`

### `register_all`

```python
def register_all(app: App, ledger_textarea: LedgerTextArea) -> None:
    """Register all bundled app themes and TextAreaThemes.

    Must be called before setting app.theme to any bundled theme name.
    """
```

### `BUNDLED_THEMES`

```python
BUNDLED_THEMES: list[Theme]
```
All bundled Textual `Theme` objects (currently: `[MONOKAI_PRO_APP_THEME]`).

### `TEXTAREA_THEME_MAP`

```python
TEXTAREA_THEME_MAP: dict[str, str]
```
Maps app theme name → TextAreaTheme name for the static (non-bridge) path.
Currently: `{"monokai-pro": "monokai-pro-ledger"}`.
