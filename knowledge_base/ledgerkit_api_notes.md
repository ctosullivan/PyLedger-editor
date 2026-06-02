# ledgerkit API Notes

Authoritative reference: `vendor/ledgerkit/dev-docs/api-spec.md`
Source models: `vendor/ledgerkit/ledgerkit/models.py`

Installed version: **0.1.0** (Python import: `import ledgerkit`)
Package directory in repo: `ledgerkit/`.

### Migration from PyLedger v0.5.1

- Package renamed from `PyLedger` to `ledgerkit` (all lowercase)
- Module import: `import ledgerkit` (was `import PyLedger`)
- New: `Amount.raw: Optional[str]` — stores the raw source string; used by
  `Journal.commodity_styles` to infer display formats
- New: `Journal.commodity_styles` property — returns `Dict[str, CommodityStyle]`
  inferred from the first-seen raw amount per commodity (see below)
- New: `CommodityStyle` class — captures prefix/suffix, spacing, decimal mark,
  group separator, and precision; use `.format(quantity)` to render amounts
- `run_basic_checks` still exists in `ledgerkit.checks`

---

## Key Notes

> **Transaction fields**: `Transaction.cleared: bool` and `Transaction.pending: bool`
> (no `flag` field). Always check models.py before writing code.

Other notes:
- `Journal.price_directives` in old docs is actually `Journal.prices` (list[PriceDirective])
- `balance()` returns `dict[str, dict[str, Decimal]]` in flat mode (commodity-keyed)
- `Journal._commodity_directive_raws`: internal dict mapping commodity → raw directive
  string; used by `commodity_styles` property (directive-declared styles take priority)

---

## Top-Level Public API (`import ledgerkit`)

| Name | Type | Description |
|------|------|-------------|
| `ledgerkit.load(path)` | `Journal` | Alias for `loader.load_journal()`; handles includes |
| `ledgerkit.EditorDocument(path)` | class | In-memory editable journal document |
| `ledgerkit.transaction_to_text(txn)` | `str` | Serialise one Transaction to journal text |
| `ledgerkit.journal_to_text(journal)` | `str` | Serialise all transactions (no directives) |
| `ledgerkit.parse_string_lenient(text)` | `tuple[Journal, list[ParseError]]` | Lenient parse; never raises |
| `ledgerkit.resolve_elision(txn)` | `list[Posting]` | Infer elided posting amounts |
| `ledgerkit.check_transaction_autobalanced(txn)` | `list[CheckError]` | Single-txn balance check |
| `ledgerkit.CommodityStyle` | dataclass | Display style for one commodity |
| `ledgerkit.Query` | dataclass | Filter criteria for report functions |
| `ledgerkit.BalanceRow` | dataclass | One row in tree-mode balance report |
| `ledgerkit.RegisterRow` | dataclass | One row in register report |
| `ledgerkit.CheckError` | dataclass | Validation error with check_name + message |
| `ledgerkit.SourceSpan` | dataclass | Source line range for a parsed transaction |
| `ledgerkit.balance_from_spec(journal, spec, query)` | `list[ReportSectionResult]` | Structured balance |
| `ledgerkit.__version__` | `str` | `"0.1.0"` |

---

## `CommodityStyle` (new in ledgerkit v0.1.0)

```python
@dataclass
class CommodityStyle:
    commodity: str
    prefix: bool = True          # True → £30.00, False → 30.00 EUR
    space: bool = False          # space between symbol and number
    decimal_mark: str = "."      # "." or "," depending on locale
    group_separator: str = ""    # "," or "." or "" (no grouping)
    precision: int = 2           # decimal places

    def format(self, quantity: Decimal) -> str: ...
    # Note: prefix negative → SYMBOL-NUMBER (e.g. £-5.00), not -SYMBOLNUMBER

    @classmethod
    def infer(cls, commodity: str, raw_amount_str: str) -> "CommodityStyle": ...
    # Infers style from a raw amount string as it appeared in the journal source

    @classmethod
    def parse_style_override(cls, style_string: str) -> "CommodityStyle": ...
    # Parses a -c/--commodity-style override string in hledger format
```

## `Journal.commodity_styles` (new in ledgerkit v0.1.0)

```python
@property
def commodity_styles(self) -> dict[str, CommodityStyle]:
    """Infer display styles from journal data.

    Priority (highest wins):
      1. Explicit commodity directives (_commodity_directive_raws)
      2. First posting amount seen per commodity (Amount.raw field)
      3. First price-directive amount seen per commodity
    """
```

Use `journal.commodity_styles` after loading to get the detected format per commodity.
Requires `Amount.raw` to be set (it is, when loaded via `EditorDocument` or `load()`).

---

## Model Dataclasses (from `ledgerkit/models.py`)

### `Amount`

```python
@dataclass
class Amount:
    quantity: Decimal
    commodity: str
    raw: Optional[str] = field(default=None, repr=False, compare=False)
    # raw stores the original source string, e.g. "£1,234.56" or "500.00 EUR"
```

### `Transaction`

```python
@dataclass
class Transaction:
    date: datetime.date
    description: str
    postings: list[Posting] = field(default_factory=list)
    cleared: bool = False          # True when marked with "*"
    pending: bool = False          # True when marked with "!"
    code: str = ""
    comment: str = ""
    source_line: int | None = ...
    source_span: SourceSpan | None = ...  # repr=False, compare=False
    raw_text: str | None = ...            # repr=False, compare=False
    inline_comment: str | None = ...      # repr=False, compare=False
```

### `Posting`

```python
@dataclass
class Posting:
    account: str
    amount: Amount | None = None
    balance_assertion: BalanceAssertion | None = None
    source_line: int | None = None
    inferred: bool = False
    inline_comment: str | None = None
```

### `Journal`

```python
@dataclass
class Journal:
    transactions: list[Transaction] = ...
    prices: list[PriceDirective] = ...      # NOTE: 'prices', not 'price_directives'
    declared_accounts: list[str] = ...
    declared_commodities: list[str] = ...
    declared_payees: list[str] = ...
    declared_tags: list[str] = ...
    source_file: str | None = None
    included_files: int = 0
    _commodity_directive_raws: dict = ...   # internal; feeds commodity_styles
```

---

## `EditorDocument` (key attributes and methods)

```python
class EditorDocument:
    path: str                  # resolved absolute path
    journal: Journal           # parsed journal (commodity_styles available here)
    lines: list[str]           # current file content, no newlines
    dirty: bool                # True when unsaved changes exist

    def __init__(self, path: str) -> None: ...
    def add_transaction(self, txn: Transaction) -> None: ...
    def update_transaction(self, original: Transaction, updated: Transaction) -> None: ...
    def delete_transaction(self, txn: Transaction) -> None: ...
    def save(self) -> None: ...
    def reload(self) -> None: ...
    def validate_transaction(self, txn: Transaction) -> list[CheckError]: ...
```

V1 limitation: include directives in the edited file are silently ignored.

---

## `reports.balance()` Return Type

```python
# Flat mode (default, tree=False):
journal.balance() -> dict[str, dict[str, Decimal]]
#   outer key: account name
#   inner key: commodity symbol
#   value: net balance as Decimal

# Tree mode:
journal.balance(tree=True) -> list[BalanceRow]
```

---

## File Resolution Order (for `ledgerkit.cli`)

1. `-f FILE` argument (may be repeated; all merged)
2. Positional journal-file argument (backward-compat alias for -f)
3. `$LEDGER_FILE` environment variable
4. `~/.hledger.journal` default

The editor implements the same order in `utils/file_resolver.py`.
