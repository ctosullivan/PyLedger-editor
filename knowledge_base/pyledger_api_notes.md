# PyLedger API Notes

Authoritative reference: `vendor/pyledger/dev-docs/api-spec.md`
Source models: `vendor/pyledger/pyLedger/models.py`

Installed version: **0.5.0** (pip name: `pyledger==0.5`, Python import: `import PyLedger`)
Package directory in repo: `pyLedger/` (note lowercase 'py') — imported as `PyLedger`.

---

## Key Discrepancy vs. Original Prompt Spec (§3.2)

> **IMPORTANT**: The prompt described `Transaction.flag: str | None` with values
> `None`, `"*"`, `"!"`. This field does NOT exist in v0.5.0.
>
> The actual fields are:
> - `Transaction.cleared: bool = False` — `True` when marked with `"*"`
> - `Transaction.pending: bool = False` — `True` when marked with `"!"`
>
> Any editor code that toggles cleared/pending status must use these two booleans,
> not a `flag` field.

Other discrepancies:
- `Journal.price_directives` in the prompt is actually `Journal.prices` (list[PriceDirective])
- `balance()` returns `dict[str, dict[str, Decimal]]` in flat mode (commodity-keyed), not just `Decimal`

---

## Top-Level Public API (`import PyLedger`)

| Name | Type | Description |
|------|------|-------------|
| `PyLedger.load(path)` | `Journal` | Alias for `loader.load_journal()`; handles includes |
| `PyLedger.EditorDocument(path)` | class | In-memory editable journal document |
| `PyLedger.transaction_to_text(txn)` | `str` | Serialise one Transaction to journal text |
| `PyLedger.journal_to_text(journal)` | `str` | Serialise all transactions (no directives in v0.5) |
| `PyLedger.parse_string_lenient(text)` | `tuple[Journal, list[ParseError]]` | Lenient parse; never raises |
| `PyLedger.resolve_elision(txn)` | `list[Posting]` | Infer elided posting amounts |
| `PyLedger.check_transaction_autobalanced(txn)` | `list[CheckError]` | Single-txn balance check |
| `PyLedger.Query` | dataclass | Filter criteria for report functions |
| `PyLedger.BalanceRow` | dataclass | One row in tree-mode balance report |
| `PyLedger.RegisterRow` | dataclass | One row in register report |
| `PyLedger.CheckError` | dataclass | Validation error with check_name + message |
| `PyLedger.SourceSpan` | dataclass | Source line range for a parsed transaction |
| `PyLedger.balance_from_spec(journal, spec, query)` | `list[ReportSectionResult]` | Structured balance |
| `PyLedger.__version__` | `str` | `"0.5.0"` |

---

## Model Dataclasses (from `PyLedger/models.py`)

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
    comment: str = ""              # kept for backward compat; prefer inline_comment
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
    source_line: int | None = None        # repr=False
    inferred: bool = False                 # repr=False
    inline_comment: str | None = None      # repr=False, compare=False
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
```

### `Query`

```python
@dataclass
class Query:
    account: str | None = None
    not_account: str | None = None
    payee: str | None = None
    date_from: datetime.date | None = None
    date_to: datetime.date | None = None
    depth: int | None = None
```

### `BalanceRow` (tree=True mode)

```python
@dataclass
class BalanceRow:
    account: str               # full colon-separated path
    depth: int                 # colon-segment count (0 = top-level)
    amounts: dict[str, Decimal]  # commodity → net balance
    is_subtotal: bool          # True for implicit parent accounts
```

---

## `EditorDocument` (key methods)

```python
class EditorDocument:
    path: str                  # resolved absolute path
    journal: Journal           # parsed journal
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

Breaking change from Milestone 2 → 3: flat mode now returns a commodity-keyed
dict instead of `dict[str, Decimal]`.

---

## File Resolution Order (for `PyLedger.cli`)

1. `-f FILE` argument (may be repeated; all merged)
2. Positional journal-file argument (backward-compat alias for -f)
3. `$LEDGER_FILE` environment variable
4. `~/.hledger.journal` default

The editor implements the same order in `utils/file_resolver.py`.
