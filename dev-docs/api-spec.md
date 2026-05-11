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

## `ledger_editor.widgets.ledger_textarea`

### `LedgerTextArea`

```python
class LedgerTextArea(TextArea):
    """TextArea subclass with hledger journal syntax highlighting.

    Drop-in replacement for TextArea. Overrides _build_highlight_map()
    (private Textual 8.2.5 API) to inject ledger token spans and block
    background overlays into self._highlights on every edit.
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
