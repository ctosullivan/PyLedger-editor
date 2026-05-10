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
