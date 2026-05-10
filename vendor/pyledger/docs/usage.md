# PyLedger Usage Guide

PyLedger can be used as a command-line tool or as a Python library.

---

## CLI Usage

### Syntax

```bash
PyLedger [-f FILE]... [-s] <command> [args...]
```

You can also invoke it as a Python module (equivalent):

```bash
python -m PyLedger [-f FILE]... [-s] <command> [args...]
```

#### Specifying the journal file

Use `-f`/`--file` to specify the journal file (can be given more than once to
merge multiple files):

```bash
# Single file
PyLedger -f myledger.journal stats

# Multiple files — transactions from both are merged in order
PyLedger -f checking.journal -f savings.journal stats

# Read from stdin
cat myledger.journal | PyLedger -f - stats
```

The positional argument is a shorthand for a single `-f` (kept for
backward compatibility):

```bash
PyLedger stats myledger.journal
```

If no file is specified, PyLedger checks the `$LEDGER_FILE` environment
variable, then falls back to `~/.hledger.journal`.

---

### `-s` / `--strict` — Strict mode

By default PyLedger checks that every transaction balances (the `autobalanced`
check). Strict mode adds two extra checks:

- **`accounts`** — every posting account must be declared with an `account`
  directive somewhere in the journal
- **`commodities`** — every commodity symbol must be declared with a `commodity`
  directive

```bash
PyLedger -s -f myledger.journal stats
```

If any check fails, PyLedger prints an error to stderr and exits with code 1.

---

### `check` — Run validation checks

The `check` command lets you run individual or grouped validation checks on
demand.

```bash
# Run basic checks only (same as the default gate on all commands)
PyLedger check -f myledger.journal

# Run strict checks (basic + accounts + commodities)
PyLedger -s check -f myledger.journal

# Run specific named checks
PyLedger check ordereddates -f myledger.journal
PyLedger check payees ordereddates -f myledger.journal
```

Available check names:

| Name | Description |
|---|---|
| `parseable` | Journal loaded without errors (trivially satisfied) |
| `autobalanced` | Every transaction nets to zero (one elided posting allowed) |
| `accounts` | All posting accounts declared via `account` directives |
| `commodities` | All commodity symbols declared via `commodity` directives |
| `payees` | All transaction descriptions declared via `payee` directives |
| `ordereddates` | Transactions appear in non-decreasing date order |
| `uniqueleafnames` | No two accounts share the same final colon-segment |

On success: no output, exit code 0. On failure: errors printed to stderr, exit code 1.

---

### `print` — Display transactions

Prints all transactions from the journal in a human-readable format.

```bash
PyLedger print myledger.journal
```

Example output:

```
2024-01-01 Opening balance
    assets:bank:checking                        £1000.00
    equity:opening-balances

2024-01-10 * Supermarket
    expenses:food                               £45.00
    assets:bank:checking
```

---

### `balance` — Account balances

Prints the net balance for every account.

```bash
PyLedger balance myledger.journal
```

---

### `register` — Transaction register

Prints a chronological list of all postings with running balances.

```bash
PyLedger register myledger.journal
```

---

### `accounts` — List accounts

Prints all account names found in the journal, sorted alphabetically.

```bash
PyLedger accounts myledger.journal
```

---

### `stats` — Journal statistics

Prints a summary: file name, transaction count, account count, date range,
and commodities used.

```bash
PyLedger stats myledger.journal
```

---

## Python Library Usage

```python
import PyLedger

# Load a journal file
journal = PyLedger.load("myledger.journal")

# Access transactions directly
for txn in journal.transactions:
    print(txn.date, txn.description)

# Run reports (returns data, not formatted strings)
account_list = journal.accounts()   # list[str]
balances     = journal.balance()    # dict[str, Decimal]
rows         = journal.register()   # list[RegisterRow]
summary      = journal.stats()      # JournalStats
```

See [python-api.md](python-api.md) for full library documentation.

---

## Getting Help

```bash
PyLedger --help
```
