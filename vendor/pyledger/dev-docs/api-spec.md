# API Specification

Status key: `[IMPLEMENTED]` · `[STUB — Milestone 2]` · `[PLANNED]`

---

## Top-level (`PyLedger/__init__.py`)

### `load` `[IMPLEMENTED]`

```python
def load(path: str | os.PathLike) -> Journal:
    """Load a .journal or .ledger file and return a Journal object.

    Alias for loader.load_journal(). Supports include directives.
    Intended for programmatic use:
        import PyLedger
        journal = PyLedger.load("myfile.journal")

    Raises:
        FileNotFoundError: if the path or a non-glob included file does not exist.
        ParseError: if an extension is unsupported, a format prefix is used,
                    a circular include is detected, a glob matches nothing,
                    or the file contents are malformed.
    """
```

Also invocable as a module:

```
python -m PyLedger <command> <journal-file>
```

---

## `PyLedger/models.py`

### `Amount` `[IMPLEMENTED]`

```python
@dataclass
class Amount:
    quantity: Decimal
    commodity: str  # e.g. "£", "$", "EUR", "AAPL"
```

Represents a single monetary or commodity amount.

---

### `BalanceAssertion` `[IMPLEMENTED]`

```python
@dataclass
class BalanceAssertion:
    amount: Amount
    inclusive: bool = False       # True for =* and ==*
    sole_commodity: bool = False  # True for == and ==*
```

An inline balance assertion attached to a posting.  Corresponds to the
hledger assertion markers `=`, `==`, `=*`, `==*`.  See
`dev-docs/hledger-compatibility.md` for syntax and semantics.

---

### `Posting` `[IMPLEMENTED]`

```python
@dataclass
class Posting:
    account: str                                    # e.g. "expenses:food"
    amount: Amount | None = None                    # None means "infer from other postings"
    balance_assertion: BalanceAssertion | None = None  # optional inline assertion
    source_line: int | None = None                  # 1-based line number; None for programmatic objects
    inferred: bool = False                          # True for postings synthesised by resolve_elision()
```

One line within a transaction, mapping an account to an amount.

The wire format requires **two or more spaces** between the account name and the
amount. A single space is treated as part of the account name, allowing names such
as `expenses:fun money`. When no double-space separator is present, the posting has
no amount (`amount=None` — elided).

`inferred` is set to `True` on postings synthesised by `resolve_elision()` and is
`False` for all postings parsed directly from journal text. `repr=False` keeps the
dataclass repr clean.

---

### `Transaction` `[IMPLEMENTED]`

```python
@dataclass
class Transaction:
    date: datetime.date
    description: str
    postings: list[Posting]
    cleared: bool = False          # True if marked with "*"
    pending: bool = False          # True if marked with "!"
    code: str = ""                 # Optional transaction code in parentheses
    comment: str = ""              # Inline or trailing comment text
    source_line: int | None = None # 1-based line number of the header in source file
```

Represents a complete journal transaction entry.

**Wire → model mapping** (see `dev-docs/hledger-compatibility.md` for block delimiters):

```
"2024-01-15 * (INV-42) Groceries ; comment"
  │            │  │       │        │
  │            │  │       │        └── comment     = "comment"
  │            │  │       └─────────── description = "Groceries"
  │            │  └─────────────────── code        = "INV-42"
  │            └────────────────────── cleared     = True  (pending = False)
  └─────────────────────────────────── date        = date(2024, 1, 15)
```

`postings` preserves journal order. A `Posting` with `amount=None` is an *elided*
posting whose value is inferred from the other postings at reporting time.

---

### `PriceDirective` `[IMPLEMENTED]`

```python
@dataclass
class PriceDirective:
    date: datetime.date
    commodity: str   # The commodity being priced, e.g. "AAPL", "EUR"
    price: Amount    # The price expressed as an Amount (quantity + currency symbol)
```

Represents one `P` directive from the journal. Stored in `Journal.prices`.

Example journal line: `P 2024-03-01 AAPL $179.00`

Commodity valuation using these records (converting amounts between commodities
in reports) is in scope for v1 and will be implemented in Milestone 2.

---

### `Journal` `[IMPLEMENTED]`

```python
@dataclass
class Journal:
    transactions: list[Transaction]
    prices: list[PriceDirective] = field(default_factory=list)
    declared_accounts: list[str] = field(default_factory=list)
    declared_commodities: list[str] = field(default_factory=list)
    declared_payees: list[str] = field(default_factory=list)
    declared_tags: list[str] = field(default_factory=list)
    source_file: str | None = None
    included_files: int = 0   # count of distinct files pulled in via include
```

Top-level container for all parsed journal data.

`declared_accounts`, `declared_commodities`, `declared_payees`, and `declared_tags` are populated
by `account`, `commodity`, `payee`, and `tag` directives respectively. The first three are used
by the strict-mode checks in `checks.py`; `declared_tags` is reserved for the deferred `check tags`.

`included_files` is set by `loader.load_journal()`. When `parse_string()` is
called directly (no file I/O), it remains `0`.

**Report methods** (delegate to `PyLedger.reports` via lazy import):

```python
def balance(self, accounts: list[str] | None = None,
            query: Query | None = None,
            tree: bool = False) -> dict[str, dict[str, Decimal]] | list[BalanceRow]: ...
def register(self, accounts: list[str] | None = None,
             query: Query | None = None) -> list[RegisterRow]: ...
def accounts(self) -> list[str]: ...
def stats(self, query: Query | None = None) -> JournalStats: ...
```

The `accounts` parameter on `balance()` and `register()` is deprecated — use `query=`
for new code. When both are supplied, `query` takes precedence.

---

### `Query` `[IMPLEMENTED — Milestone 2]`

```python
@dataclass
class Query:
    account:     str | None = None        # substring or regex; matches posting account names
    not_account: str | None = None        # exclusion filter on account names
    payee:       str | None = None        # substring or regex; matches transaction description
    date_from:   datetime.date | None = None  # inclusive lower bound
    date_to:     datetime.date | None = None  # inclusive upper bound
    depth:       int | None = None        # max account tree depth (colon-segment count)
```

All fields are optional and default to `None`. `Query()` with all `None` fields is
semantically equivalent to `query=None` (no filter). `account`, `not_account`, and
`payee` patterns are matched as plain case-insensitive substrings unless the string
contains a regex metacharacter, in which case `re.search` is used.

Re-exported from `PyLedger.__init__` as `PyLedger.Query`.

---

### `BalanceRow` `[NEW — Milestone 3]`

```python
@dataclass
class BalanceRow:
    account: str               # full account path, e.g. "assets:bank"
    depth: int                 # number of ':' separators (0 = top-level)
    amounts: dict[str, Decimal]  # commodity → net balance (own + descendants)
    is_subtotal: bool          # True for implicit parent accounts with no direct postings
```

One row in a tree-mode balance report, as returned by `balance(tree=True)`.
`amounts` aggregates all descendant postings in addition to the account's own postings.
`is_subtotal` is `True` when the account name appears as a prefix in another account's
path but has no postings directly attributed to it.

Re-exported from `PyLedger.__init__` as `PyLedger.BalanceRow`.

---

### `RegisterRow` `[IMPLEMENTED — Milestone 2]`

```python
@dataclass
class RegisterRow:
    date:            datetime.date
    description:     str
    account:         str
    amount:          Amount
    running_balance: Decimal
```

One row in a register report. `running_balance` is the cumulative sum of
`amount.quantity` across all rows in output order.

Re-exported from `PyLedger.__init__` as `PyLedger.RegisterRow`.

---

### `ReportSection` `[IMPLEMENTED — Milestone 2]`

```python
@dataclass(frozen=True)
class ReportSection:
    name:     str                     # display name, e.g. "Fixed Expenses"
    accounts: tuple[str, ...]         # account patterns to include (OR logic)
    exclude:  tuple[str, ...] = ()    # account patterns to exclude
    label:    str | None = None       # override for subtotal line; defaults to f"Total {name}"
    depth:    int | None = None       # depth cap for this section; overrides outer Query depth
    invert:   bool = False            # negate all amounts (use for income sections)
```

Frozen dataclass — instances are immutable and safe to share across report calls.
`accounts` uses OR logic: a posting is included if it matches any pattern.
`exclude` patterns are applied as a final subtraction.

Re-exported from `PyLedger.__init__` as `PyLedger.ReportSection`.

---

### `ReportSpec` `[IMPLEMENTED — Milestone 2]`

```python
@dataclass(frozen=True)
class ReportSpec:
    name:           str
    sections:       tuple[ReportSection, ...]
    show_subtotals: bool = True
    show_total:     bool = True
    total_label:    str = "Net"
```

A structured report definition composed of named sections. Frozen dataclass.

> **Note:** Journal-comment-based spec parsing (`; report` / `; end report` syntax)
> is `[DEFERRED — Milestone 3]`. In Milestone 2, specs are constructed
> programmatically only.

Re-exported from `PyLedger.__init__` as `PyLedger.ReportSpec`.

---

### `ReportSectionResult` `[IMPLEMENTED — Milestone 2]`

```python
@dataclass
class ReportSectionResult:
    section:  ReportSection
    rows:     dict[str, Decimal]   # account name → net balance (after invert)
    subtotal: Decimal              # sum of all values in rows (after invert)
```

Mutable result object returned per section by `balance_from_spec()`.

Re-exported from `PyLedger.__init__` as `PyLedger.ReportSectionResult`.

---

## `PyLedger/parser.py`

### `ParseError` `[IMPLEMENTED]`

```python
class ParseError(ValueError):
    def __init__(self, message: str, line_number: int | None = None) -> None: ...
```

Raised on malformed journal input. `line_number` is 1-based when available.

---

### `parse_string` `[IMPLEMENTED]`

```python
def parse_string(text: str, default_year: int | None = None) -> Journal:
    """Parse a journal from a string and return a Journal object.

    Accepted date formats: YYYY-MM-DD, YYYY/MM/DD, YYYY.MM.DD, and year-omitted
    forms such as M/DD or MM-DD. Leading zeros on month and day are optional.
    When the year is omitted, default_year is used (defaults to the current
    calendar year when None).

    Raises:
        ParseError: if the input is not valid hledger journal syntax.
    """
```

---

### `parse_string_lenient` `[NEW — Milestone 3]`

```python
def parse_string_lenient(
    text: str,
    default_year: int | None = None,
) -> tuple[Journal, list[ParseError]]:
    """Parse leniently, returning (journal_with_valid_txns, list_of_errors).

    Never raises. Intended for editor on_text_changed callbacks. Malformed
    transactions are skipped; valid transactions are included in the returned
    Journal. Directive-level errors (bad P directive, etc.) are also collected
    rather than raised.

    default_year: used for year-omitted dates; defaults to the current calendar
    year when None.
    """
```

Re-exported from `PyLedger.__init__` as `PyLedger.parse_string_lenient`.

---

### `resolve_elision` `[NEW — Milestone 3]`

```python
def resolve_elision(txn: Transaction) -> list[Posting]:
    """Resolve any single elided posting in txn into N concrete inferred postings.

    hledger rule: exactly one posting per transaction may have no amount. Its
    value is the negation of the sum of all other postings, computed
    independently per commodity. For N commodities in the other postings, N
    synthetic Posting objects are produced (sorted by commodity name) and
    spliced in at the elided posting's position.

    Returns list(txn.postings) unchanged when:
      - There are 0 elided postings (already fully specified)
      - There are 2+ elided postings (invalid — not resolved here)
      - All explicit postings have zero total (nothing to infer)

    Synthesised postings have inferred=True. Original postings retain
    inferred=False regardless of whether they came from parsed text or were
    constructed programmatically.
    """
```

Re-exported from `PyLedger.__init__` as `PyLedger.resolve_elision`.

---

---

## `PyLedger/loader.py`

### `load_journal` `[IMPLEMENTED]`

```python
def load_journal(path: str | os.PathLike) -> Journal:
    """Load a .journal or .ledger file and return a Journal object.

    Handles include directives recursively. Included files are expanded at
    the point of the directive before parsing, preserving directive scope
    (e.g. an alias active before an include applies to included content).

    Path resolution in include directives:
      - ~/...       tilde expanded to the home directory
      - /abs/path   used as-is (absolute)
      - relative    resolved relative to the containing file's directory
      - Globs (* ** ? [range]) expanded via glob.glob; the containing file
        is always excluded from results.

    Populates journal.source_file (absolute path string) and
    journal.included_files (count of distinct included files).

    Raises:
        FileNotFoundError: if the root path or a non-glob included file
            does not exist.
        ParseError: if an extension is unsupported, a format prefix is
            used (e.g. timedot:), a circular include is detected, a glob
            matches no files, or the file contents are malformed.
    """
```

> **Note:** `parse_file()` was removed in this milestone. Use `load_journal()`
> (or the `PyLedger.load` alias) for all file loading.

---

### `load_journal_stdin` `[IMPLEMENTED]`

```python
def load_journal_stdin() -> Journal:
    """Read a journal from stdin and return a Journal object.

    Parses the full stdin contents as hledger journal text.
    Sets source_file to "(stdin)". included_files is always 0.

    Raises:
        ParseError: if the stdin content is malformed.
    """
```

---

### `merge_journals` `[IMPLEMENTED]`

```python
def merge_journals(journals: list[Journal]) -> Journal:
    """Merge a list of Journal objects into a single Journal.

    Transactions, prices, declared_accounts, declared_commodities,
    declared_payees, and declared_tags are all concatenated in input order.
    source_file is taken from the first journal.
    included_files is the sum across all input journals.

    Raises:
        ValueError: if journals is empty.
    """
```

---

## `PyLedger/checks.py`

### `CheckError` `[UPDATED — Milestone 3]`

```python
@dataclass
class CheckError:
    check_name: str          # e.g. "autobalanced", "accounts"
    message: str             # human-readable single-line description
    line_number: int | None = None  # 1-based source line of the offending entry; None when unavailable
```

`line_number` is populated for all transaction-level errors (autobalanced, assertions,
payees, ordereddates, accounts, commodities) and is `None` for errors without a
single clear source line (e.g. `uniqueleafnames`). The default is `None` for backward
compatibility with code that constructs `CheckError` directly.

Also re-exported from `PyLedger.__init__` as `PyLedger.CheckError`.

---

### Check constants `[IMPLEMENTED]`

```python
BASIC_CHECK_NAMES:  tuple[str, ...] = ("parseable", "autobalanced", "assertions")
STRICT_CHECK_NAMES: tuple[str, ...] = ("accounts", "commodities")
OTHER_CHECK_NAMES:  tuple[str, ...] = ("payees", "ordereddates", "uniqueleafnames")
```

---

### Individual check functions `[IMPLEMENTED]`

All return `list[CheckError]` — empty list means no errors.

| Function | Tier | Description |
|---|---|---|
| `check_parseable(journal)` | basic | Always `[]` — already parsed |
| `check_autobalanced(journal)` | basic | Each transaction nets to zero per commodity; one elided posting allowed |
| `check_assertions(journal)` | basic | All inline balance assertions pass; checked in date order |
| `check_accounts(journal)` | strict | All posting accounts appear in `declared_accounts` |
| `check_commodities(journal)` | strict | All commodity symbols in amounts appear in `declared_commodities`; zero-amount postings (commodity `""`) are exempt |
| `check_payees(journal)` | other | All transaction descriptions appear in `declared_payees` |
| `check_ordereddates(journal)` | other | Transactions in non-decreasing date order |
| `check_uniqueleafnames(journal)` | other | No two accounts share the same final colon-segment |

---

### `run_basic_checks` `[IMPLEMENTED]`

```python
def run_basic_checks(
    journal: Journal,
    *,
    skip: frozenset[str] | None = None,
) -> list[CheckError]:
    """Run parseable + autobalanced + assertions checks. Always run by the CLI.

    skip: names to suppress (e.g. frozenset({"assertions"}) for -I flag).
    """
```

---

### `run_strict_checks` `[IMPLEMENTED]`

```python
def run_strict_checks(
    journal: Journal,
    *,
    skip: frozenset[str] | None = None,
) -> list[CheckError]:
    """Run basic checks plus accounts + commodities checks."""
```

---

### `run_checks` `[IMPLEMENTED]`

```python
def run_checks(
    journal: Journal,
    names: list[str] | None = None,
    *,
    strict: bool = False,
    skip: frozenset[str] | None = None,
) -> list[CheckError]:
    """Run basic checks always; strict checks if strict=True;
    named 'other' checks if listed in names.

    skip: names to suppress entirely (e.g. frozenset({"assertions"}) for -I).

    Valid names: "parseable", "autobalanced", "assertions", "accounts",
    "commodities", "payees", "ordereddates", "uniqueleafnames".

    Raises:
        ValueError: if an unknown check name is provided.
    """
```

### `check_transaction_autobalanced` `[NEW — Editor Readiness]`

```python
def check_transaction_autobalanced(txn: Transaction) -> list[CheckError]:
    """Run the autobalanced check on a single Transaction.

    Returns [] if balanced or if the transaction has exactly one elided posting.
    Returns a list containing one CheckError per unbalanced commodity otherwise.
    Does not raise.
    """
```

Re-exported from `PyLedger.__init__` as `PyLedger.check_transaction_autobalanced`.

---

## `PyLedger/writer.py` `[NEW — Editor Readiness]`

### `transaction_to_text`

```python
def transaction_to_text(txn: Transaction) -> str:
    """Serialise a Transaction to a journal-format string.

    The returned string ends with a single newline. When parsed by
    parse_string(), the result round-trips to an equivalent Transaction
    (same date, flag, description, postings, amounts, comments;
    source_span and raw_text are not checked).

    Formatting rules:
    - Date as YYYY-MM-DD.
    - Status flag (* or !) included if set.
    - Code in parentheses if set.
    - Transaction.inline_comment appended after '  ;' if not None.
    - Each posting indented with four spaces.
    - Amounts right-aligned at a consistent column (decimal points line up).
    - Elided posting (no amount) serialised as indented account name only.
    - Posting.inline_comment appended after '  ;' if not None.
    """
```

Re-exported from `PyLedger.__init__` as `PyLedger.transaction_to_text`.

### `journal_to_text`

```python
def journal_to_text(journal: Journal) -> str:
    """Serialise all transactions in journal.transactions to text.

    Transactions are separated by blank lines; the output ends with a single
    newline. Directives (account, commodity, payee, P) are not serialised in v1.
    """
```

Re-exported from `PyLedger.__init__` as `PyLedger.journal_to_text`.

---

## `PyLedger/editor_model.py` `[NEW — Editor Readiness]`

### `EditorDocument`

```python
class EditorDocument:
    """An in-memory editable representation of a journal file.

    Attributes:
        path:    Resolved absolute path to the journal file.
        journal: Parsed Journal with all transactions (source_span populated).
        lines:   Current file content as a list of strings, one per line,
                 without newline characters.
        dirty:   True when lines differ from the last saved/loaded content.
    """

    def __init__(self, path: str) -> None:
        """Load the journal at path; populate journal and lines."""

    def add_transaction(self, txn: Transaction) -> None:
        """Insert txn into self.lines in chronological order."""

    def update_transaction(self, original: Transaction, updated: Transaction) -> None:
        """Replace the source lines of original with the serialised form of updated."""

    def delete_transaction(self, txn: Transaction) -> None:
        """Remove the source lines of txn and any immediately following blank line."""

    def save(self) -> None:
        """Write self.lines to self.path; set dirty=False."""

    def reload(self) -> None:
        """Re-read self.path from disk and re-parse."""

    def validate_transaction(self, txn: Transaction) -> list[CheckError]:
        """Run the autobalanced check on txn alone. Does not raise."""
```

V1 limitation: include directives in the edited file are silently ignored; the file
is parsed as-is via `parse_string()`. Use `loader.load_journal()` when full include
support is required (source_span values will reference merged-text line numbers in
that case).

Re-exported from `PyLedger.__init__` as `PyLedger.EditorDocument`.

---

## `PyLedger/models.py` — `SourceSpan` `[NEW — Editor Readiness]`

```python
@dataclass
class SourceSpan:
    """Source location of a parsed transaction block."""
    file: str        # absolute path, "(string)", or "(stdin)"
    start_line: int  # 1-indexed, inclusive — transaction header line
    end_line: int    # 1-indexed, inclusive — last posting/comment line
```

Attached to `Transaction.source_span` by the parser. Also available as
`Transaction.raw_text` (verbatim source lines) and `Transaction.inline_comment`
(`str | None`). `Posting.inline_comment` (`str | None`) captures the text after `;`
on a posting line.

Re-exported from `PyLedger.__init__` as `PyLedger.SourceSpan`.

---

## `PyLedger/reports.py`

All report functions accept a `Journal` as their first argument and are also
accessible as methods on `Journal` directly (e.g. `journal.balance()`).

### `balance` `[UPDATED — Milestone 3]`

```python
def balance(
    journal: Journal,
    query: Query | None = None,
    tree: bool = False,
) -> dict[str, dict[str, Decimal]] | list[BalanceRow]:
    """Return account balances, optionally in tree form.

    Flat mode (tree=False, default):
        Returns dict[account, dict[commodity, net_balance]].
        Only accounts with at least one matching posting are included.

    Tree mode (tree=True):
        Returns list[BalanceRow] sorted alphabetically by account path.
        Implicit parent accounts (no direct postings) are included with
        is_subtotal=True. Amounts aggregate own + all descendant postings.

    Elided posting amounts are resolved via resolve_elision() before
    aggregation. depth in the query truncates (rolls up) account names —
    matching hledger --depth behaviour.
    """
```

**Breaking change from Milestone 2**: the return type changed from
`dict[str, Decimal]` (single commodity assumed) to
`dict[str, dict[str, Decimal]]` (commodity-keyed). Update callers as:
```python
# Before (Milestone 2):
bal = journal.balance()["assets:bank"]  # Decimal
# After (Milestone 3):
bal = journal.balance()["assets:bank"]["£"]  # Decimal
```

`balance_from_spec` retains its `dict[str, Decimal]` return type (multi-commodity
support for spec-based reports is deferred).

---

### `register` `[IMPLEMENTED — Milestone 2]`

```python
def register(
    journal: Journal,
    query: Query | None = None,
) -> list[RegisterRow]:
    """Return a chronological list of register rows."""
```

`RegisterRow` is defined in `PyLedger/models.py` and re-exported from `PyLedger.__init__`.
See `RegisterRow` under `PyLedger/models.py` above.

---

### `accounts` `[IMPLEMENTED — Milestone 2]`

```python
def accounts(journal: Journal, query: Query | None = None) -> list[str]:
    """Return a sorted list of all unique account names in the journal."""
```

---

### `stats` `[IMPLEMENTED]`

```python
@dataclass
class JournalStats:
    """Summary statistics for a journal. No runtime fields — CLI measures those."""
    source_file: str | None
    included_files: int              # count of distinct files pulled in via include
    transaction_count: int
    date_range: tuple[datetime.date, datetime.date] | None   # (first, last)
    last_txn_date: datetime.date | None
    last_txn_days_ago: int | None    # (today - last_txn_date).days
    txns_span_days: int | None       # (last - first).days + 1
    txns_per_day: float              # transaction_count / txns_span_days, else 0.0
    txns_last_30_days: int
    txns_per_day_last_30: float
    txns_last_7_days: int
    txns_per_day_last_7: float
    payee_count: int                 # unique descriptions
    account_count: int
    account_depth: int               # max colon-segment depth across all accounts
    commodity_count: int
    commodities: list[str]           # sorted commodity symbols
    price_count: int                 # len(journal.prices)

def stats(journal: Journal, query: Query | None = None) -> JournalStats:
    """Return summary statistics for the journal."""
```

When `query` is non-`None`, transaction-level filters (date range, payee) are applied
before computing statistics. Account-level filters are not yet applied to `stats` fields
(deferred to a follow-on task).

Also accessible as `PyLedger.JournalStats` (re-exported from `__init__.py`).

---

### `balance_from_spec` `[IMPLEMENTED — Milestone 2]`

```python
def balance_from_spec(
    journal: Journal,
    spec: ReportSpec,
    query: Query | None = None,
) -> list[ReportSectionResult]:
    """Compute a structured balance report driven by a ReportSpec."""
```

Returns one `ReportSectionResult` per section in `spec.sections` order. The outer
`query` acts as a uniform time/payee filter across all sections. Within each section,
`section.accounts` patterns are OR-combined and `section.exclude` patterns are
subtracted. `section.depth` overrides `query.depth` for that section only.
`section.invert` negates all amounts after aggregation.

Re-exported from `PyLedger.__init__` as `PyLedger.balance_from_spec`.

---

## `PyLedger/cli.py`

### `main` `[IMPLEMENTED]`

```python
def main(argv: list[str] | None = None) -> int:
    """Entry point for the PyLedger CLI.

    Args:
        argv: Argument list (defaults to sys.argv[1:] when None).

    Returns:
        Exit code (0 = success, 1 = error).
    """
```

CLI interface (via `pyproject.toml` `[project.scripts]` and `PyLedger/__main__.py`):

```
PyLedger [-f FILE]... [-s] [-v] [-1] [-o FILE] <command> [args...]
python -m PyLedger [-f FILE]... [-s] [-v] [-1] [-o FILE] <command> [args...]

Flags:
  -f, --file         Read data from FILE, or stdin if -. May be specified
                     more than once; all files are merged in order. If not
                     given, falls back to the positional argument, then
                     $LEDGER_FILE, then ~/.hledger.journal.
  -s, --strict       Enable strict mode: also check that all posting accounts
                     and commodity symbols are declared via account/commodity
                     directives. Equivalent to running check accounts commodities
                     in addition to the default basic checks.
  -I, --ignore-assertions
                     Disable balance assertion checking (the assertions basic
                     check). Useful for troubleshooting or loading Ledger files.
  -v, --verbose      More detailed output (stats: show commodity names)
  -1                 Single tab-separated line (stats only)
  -o, --output-file  Write output to FILE instead of stdout

Commands:
  balance             Print account balances
  register            Print a register of transactions
  accounts            List all accounts
  print               Print transactions in journal format
  stats               Print journal statistics
  check [CHECK...]    Run validation checks; default runs basic checks only.
                      Named checks: parseable autobalanced accounts commodities
                                    payees ordereddates uniqueleafnames
```

**Default validation**: all commands run `autobalanced` and `parseable` checks
automatically before executing. Any failure prints an error to stderr and exits 1.

**`check` command**: accepts zero or more check names as positional arguments.
With no names, runs only the basic checks. With `-s`, also runs `accounts` and
`commodities`. Named `other` checks (`payees`, `ordereddates`, `uniqueleafnames`)
are run only if explicitly listed. Silent on success (exit 0); errors to stderr
(exit 1).

The positional `journal-file` argument (when not using `check`) is a
backward-compatible shorthand for `-f FILE`. Specifying both `-f` and a
positional argument is an error.
