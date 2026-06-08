# Internal API Specification

> **PROTECTED FILE** — Do not modify without explicit user approval.
> See CLAUDE.md §Unauthorised Change Rule.

This file documents the internal APIs exposed by `ledgerkit_editor` modules.
It does NOT document ledgerkit's own API — see the
[ledgerkit PyPI package](https://pypi.org/project/ledgerkit/) source and
`knowledge_base/ledgerkit_api_notes.md` for that.

---

## `ledgerkit_editor.utils.file_resolver`

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

## `ledgerkit_editor.utils.date_parser`

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

## `ledgerkit_editor.utils.commodity_format`

### `extract_commodity_styles`

```python
def extract_commodity_styles(journal: Journal) -> dict[str, CommodityStyle]:
    """Return commodity styles inferred from a parsed Journal.

    Delegates to Journal.commodity_styles (ledgerkit v0.1.0+). Priority:
      1. Explicit commodity directives.
      2. First posting amount per commodity (uses Amount.raw).
      3. First price-directive amount per commodity.

    Returns an empty dict when the journal has no amounts with raw strings.
    """
```

### `apply_commodity_styles`

```python
def apply_commodity_styles(
    text: str,
    styles: dict[str, CommodityStyle],
) -> str:
    """Post-process serialised journal text to apply detected commodity formats.

    For each posting line, extracts the amount token, looks up its commodity
    in styles, and replaces the token with CommodityStyle.format(quantity).
    Lines whose commodity is absent from styles, and all non-posting lines,
    are passed through unchanged.

    Intended to run before align_posting_amounts() in the save pipeline so
    reformatted amounts are then correctly column-aligned.

    Returns text unchanged immediately when styles is empty.
    """
```

---

## `ledgerkit_editor.utils.ledger_io`

### `load_journal`

```python
def load_journal(path: Path) -> Journal:
    """Load via ledgerkit.load(). Raises FileNotFoundError or ParseError."""
```

### `save_journal`

```python
def save_journal(path: Path, journal: Journal) -> None:
    """Serialise via ledgerkit.journal_to_text() and write to path."""
```

### `align_posting_amounts`

```python
def align_posting_amounts(text: str, column: int = 52) -> str:
    """Re-space posting amount fields so each amount starts at ``column``.

    Applied to the output of journal_to_text() on every Ctrl+S save.
    Lines without an explicit amount (balance-completing postings, comment
    lines) are passed through unchanged.  Minimum spacing between account
    and amount is always 2 spaces.
    """
```

### `split_preamble`

```python
def split_preamble(text: str) -> tuple[str, str]:
    """Split journal text into (preamble, body).

    The preamble is all content before the first ISO-date transaction header.
    Returns (text, "") when no transactions are found.
    Used internally by split_journal_segments as a fallback.
    """
```

### `split_journal_segments`

```python
def split_journal_segments(
    text: str,
    transactions: list[Transaction],
) -> tuple[list[str], list[str]]:
    """Split journal text into non-transaction blocks and transaction blocks.

    Uses Transaction.source_span (1-based inclusive line numbers) to extract
    each transaction's lines. Returns (non_txn_blocks, txn_blocks) where
    len(non_txn_blocks) == len(txn_blocks) + 1. non_txn_blocks[0] is the
    preamble; non_txn_blocks[i] for i > 0 is the inter-transaction content
    (P directives, comments, blank lines) between txn_blocks[i-1] and
    txn_blocks[i]; non_txn_blocks[-1] is trailing content.

    Falls back to split_preamble semantics when source_span is unavailable.
    Used by action_save to preserve directives across sort-and-reserialise.
    """
```

---

## `ledgerkit_editor.utils.atomic_edit`

### `atomic_edit`

```python
@contextmanager
def atomic_edit(text_area: TextArea) -> Iterator[None]:
    """Collapse all TextArea edits within this block into one undo entry.

    Uses text_area.history._undo_stack (EditHistory, Textual 0.83.0).
    Raises RuntimeError if _undo_stack is absent.
    """
```

---

## `ledgerkit_editor.commands`

### `Command`

```python
@dataclass
class Command:
    execute: Callable[[], None]
    undo: Callable[[], None]
    description: str
```

### `CommandHistory`

```python
@dataclass
class CommandHistory:
    """Application-level undo/redo stack for text + model operations."""
    def execute(self, cmd: Command) -> None: ...
    def undo(self) -> Optional[Command]: ...
    def redo(self) -> Optional[Command]: ...
    @property
    def can_undo(self) -> bool: ...
    @property
    def can_redo(self) -> bool: ...
```

---

## `ledgerkit_editor.themes`

### `VALID_THEMES`

```python
VALID_THEMES: frozenset[str]
```

Frozenset of every accepted `--theme` value: all Textual built-in theme names
(from `textual.theme.BUILTIN_THEMES`) plus each project-bundled theme name.
Computed at import time so new Textual releases and new bundled entries are
included automatically.

---

## `ledgerkit_editor.app`

### `LedgerApp`

```python
class LedgerApp(App[None]):
    """Root Textual application. Constructed with a resolved journal Path."""

    def __init__(
        self,
        journal_path: Path,
        start_line: int | None = None,
        theme_name: str | None = None,
    ) -> None: ...
    def action_toggle_filter(self) -> None: ...
```

`start_line`: 1-indexed line to place the cursor on after the file loads.
`theme_name`: Registered theme name; defaults to `monokai-pro` when `None`.

### `main`

```python
def main(argv: list[str] | None = None) -> None:
    """CLI entry point. Resolves journal, launches LedgerApp."""
```

---

## `ledgerkit_editor.widgets.BalanceSidebar`

```python
class BalanceSidebar(Widget):
    def __init__(self, journal_path: Path) -> None: ...
    async def refresh_balances(self) -> None: ...
```

## `ledgerkit_editor.widgets.JournalEditor`

```python
class JournalEditor(Widget):
    def __init__(self, journal_path: Path, start_line: int | None = None) -> None: ...
    def action_toggle_cleared(self) -> None: ...
    def action_save(self) -> None: ...
    def action_autofill(self) -> None: ...
    def action_undo(self) -> None:
        """Consults CommandHistory first; falls through to LedgerTextArea.action_undo()."""
    def action_redo(self) -> None:
        """Consults CommandHistory first; falls through to LedgerTextArea.action_redo()."""
```

## `ledgerkit_editor.widgets.FilterPopup`

```python
class FilterPopup(Widget):
    def apply_filter(self) -> None: ...
```

---

## `ledgerkit_editor.widgets.search_bar`

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

## `ledgerkit_editor.widgets.reconcile_actions`

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

## `ledgerkit_editor.widgets.reconcile_bar`

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

## `ledgerkit_editor.widgets.reconcile_summary`

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

## `ledgerkit_editor.widgets.register_panel` (updated)

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

## `ledgerkit_editor.widgets.ledger_textarea`

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

## `ledgerkit_editor.highlighting`

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

## `ledgerkit_editor.themes`

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
