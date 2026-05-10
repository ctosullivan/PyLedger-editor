# PyLedger Python API

PyLedger can be used as a Python library. The public API is designed to be
simple: load a journal file, then call report methods on the returned object.

---

## Loading a Journal

```python
import PyLedger

journal = PyLedger.load("myfile.journal")
```

`PyLedger.load()` accepts `.journal` or `.ledger` files and returns a
`Journal` object. It fully supports the `include` directive — included files
are resolved and expanded recursively before parsing.

Raises `FileNotFoundError` if the file does not exist, or `ParseError` if
the file is malformed, uses an unsupported extension, contains a circular
include, or has a glob pattern that matches no files.

You can also call the lower-level text parser directly (no file I/O, no
include directive support):

```python
from PyLedger.parser import parse_string

journal = parse_string("2024-01-01 Test\n    assets:bank  £100\n    equity\n")
```

---

## The `Journal` Object

A `Journal` holds all parsed data from the file.

```python
journal.transactions   # list[Transaction]
journal.prices         # list[PriceDirective]  — from P directives
journal.source_file    # str | None  — absolute path of the root file
journal.included_files # int  — count of distinct files pulled in via include
```

### Report methods

All report methods are available directly on the `Journal` object:

```python
account_list = journal.accounts()   # list[str] — sorted unique account names
balances     = journal.balance()    # dict[str, Decimal] — net balance per account
rows         = journal.register()   # list[RegisterRow] — chronological postings
summary      = journal.stats()      # JournalStats — counts, date range, etc.
```

All methods accept an optional `query=` parameter for filtering — see the
[Filtering with Query](#filtering-with-query) section below.

---

## Data Models

### `Transaction`

```python
txn.date          # datetime.date
txn.description   # str
txn.postings      # list[Posting]
txn.cleared       # bool  — True if marked with *
txn.pending       # bool  — True if marked with !
txn.code          # str   — transaction code in parentheses, e.g. "INV-42"
txn.comment       # str   — inline comment text
```

### `Posting`

```python
posting.account   # str          — e.g. "expenses:food"
posting.amount    # Amount|None  — None means elided (inferred at report time)
```

### `Amount`

```python
amount.quantity   # Decimal  — numeric value
amount.commodity  # str      — e.g. "£", "EUR", "AAPL"
```

### `PriceDirective`

```python
price.date        # datetime.date
price.commodity   # str     — the commodity being priced, e.g. "AAPL"
price.price       # Amount  — the price expressed as an Amount
```

---

## Filtering with Query

All four report functions accept an optional `query=` parameter that controls
which transactions and postings are included.

```python
import PyLedger
from PyLedger import Query
import datetime

journal = PyLedger.load("myfile.journal")

# Show only expense account balances
balances = journal.balance(query=Query(account="expenses"))

# Show balances for the current year only
balances = journal.balance(query=Query(
    date_from=datetime.date(2024, 1, 1),
    date_to=datetime.date(2024, 12, 31),
))

# Combine filters: food expenses in Q1
rows = journal.register(query=Query(
    account="expenses:food",
    date_from=datetime.date(2024, 1, 1),
    date_to=datetime.date(2024, 3, 31),
))

# Top-level account balances only (depth rollup)
top_level = journal.balance(query=Query(depth=1))
# → {"assets": Decimal("9641"), "expenses": Decimal("1359"), ...}
```

`Query` fields at a glance:

| Field | Type | Effect |
|---|---|---|
| `account` | `str \| None` | Include only postings whose account matches (substring or regex) |
| `not_account` | `str \| None` | Exclude postings whose account matches |
| `payee` | `str \| None` | Include only transactions whose description matches |
| `date_from` | `date \| None` | Include only transactions on or after this date |
| `date_to` | `date \| None` | Include only transactions on or before this date |
| `depth` | `int \| None` | For `balance()`: roll up to this depth. For `accounts()`/`register()`: exclude deeper accounts |

Patterns in `account`, `not_account`, and `payee` are matched as plain
case-insensitive substrings unless they contain a regex metacharacter (e.g. `^`,
`$`, `.`, `*`), in which case `re.search` is used.

---

## Custom Report Layouts with ReportSpec

`ReportSpec` and `ReportSection` let you define structured, named reports with
multiple account groups, sign control, and depth overrides.

```python
import PyLedger
from PyLedger import Query, ReportSpec, ReportSection, balance_from_spec
import datetime

journal = PyLedger.load("myfile.journal")

# Build an income statement spec
spec = ReportSpec(
    name="Income Statement",
    sections=(
        ReportSection(
            "Income",
            accounts=("income",),
            invert=True,   # income carries negative balances; invert shows as positive
        ),
        ReportSection(
            "Expenses",
            accounts=("expenses",),
            exclude=("expenses:transfers",),  # skip inter-account transfers
        ),
    ),
)

# Run the report (optionally filtered to a date range)
results = balance_from_spec(
    journal,
    spec,
    query=Query(
        date_from=datetime.date(2024, 1, 1),
        date_to=datetime.date(2024, 12, 31),
    ),
)

for section_result in results:
    print(f"\n{section_result.section.name}")
    for account, balance in sorted(section_result.rows.items()):
        print(f"  {account:<40}  {balance:>12}")
    print(f"  {'Total ' + section_result.section.name:<40}  {section_result.subtotal:>12}")
```

`balance_from_spec` returns one `ReportSectionResult` per section:

```python
@dataclass
class ReportSectionResult:
    section:  ReportSection          # the spec section that produced this result
    rows:     dict[str, Decimal]     # account → net balance (after invert)
    subtotal: Decimal                # sum of all rows (after invert)
```

> **Note:** Defining report specs inside journal files via comment directives
> (`; report` / `; end report`) is planned for Milestone 3. In the current
> release, specs are constructed programmatically only.

---

## Error Handling

```python
from PyLedger.parser import ParseError

try:
    journal = PyLedger.load("myfile.journal")
except FileNotFoundError:
    print("File not found")
except ParseError as e:
    print(f"Parse error on line {e.line_number}: {e}")
```

---

## Example: Iterate Transactions

```python
import PyLedger

journal = PyLedger.load("myfile.journal")

for txn in journal.transactions:
    status = "*" if txn.cleared else ("!" if txn.pending else " ")
    print(f"{txn.date} {status} {txn.description}")
    for posting in txn.postings:
        if posting.amount:
            print(f"    {posting.account}  {posting.amount.commodity}{posting.amount.quantity}")
        else:
            print(f"    {posting.account}")
    print()
```
