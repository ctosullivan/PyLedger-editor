# Architecture

## Overview

PyLedger follows a linear data-flow pipeline:

```
Journal file(s) (.journal / .ledger)
        │
        ▼
  [ loader.py ]        ← File I/O, include directive expansion, path resolution,
        │                glob matching, and circular include detection
        ▼
  [ parser.py ]        ← Pure text → structured Python objects (no file I/O)
        │
        ▼
  [ models.py ]        ← Core data model: Transaction, Posting, Amount, etc.
        │
        ▼
  [ checks.py ]        ← Validation checks on Journal objects (balance, strict mode, etc.)
        │
        ▼
  [ reports.py ]       ← Consumes model objects, produces report data
        │
        ▼
  [ cli.py ]           ← Validates, formats and prints report data for the terminal
```

---

## Module Responsibilities

### `PyLedger/loader.py`

**Single responsibility**: File I/O, include directive expansion, path
resolution, glob matching, circular include detection, stdin loading, and
multi-file merging.

- `load_journal(path)` — load a single `.journal` or `.ledger` file; returns a
  fully populated `Journal` object
- `load_journal_stdin()` — read journal text from `sys.stdin`; returns a
  `Journal` with `source_file = "(stdin)"`
- `merge_journals(journals)` — concatenate a list of `Journal` objects into
  one; `source_file` from the first; `included_files` summed
- Recursively expands `include` directives before parsing (text-expansion
  strategy), so directive scope propagates naturally through included content
- Resolves include paths: relative (to containing file's directory), absolute,
  and tilde (`~`) expansion; glob patterns via `glob.glob(recursive=True)`
- Detects circular includes by tracking visited paths
- Populates `journal.source_file` and `journal.included_files`
- Raises `ParseError` for unsupported extensions, format prefixes, circular
  includes, or glob patterns that match no files
- Raises `FileNotFoundError` if the root file or a non-glob included file does
  not exist

### `PyLedger/parser.py`

**Single responsibility**: Convert raw `.journal` text (a Python string) into
`Transaction` objects and a `Journal` container.

- `parse_string(text)` — the sole public function; operates on text only,
  performs no file I/O
- Reads journal text line by line via a state machine
- Recognises transaction headers, postings, comments, and directives
- Raises `ParseError` with line number on malformed input
- Does **not** perform any balance validation, file loading, or reporting logic
- `include` directive lines encountered in raw text are silently skipped
  (expansion is always done by `loader.py` before `parse_string` is called)

### `PyLedger/models.py`

**Single responsibility**: Define the canonical Python data structures for
journal entries.

Core types:
- `Amount` — a numeric value paired with a commodity symbol
- `Posting` — an account name plus an optional `Amount`
- `Transaction` — a date, optional cleared/pending flag, description, and list of `Posting`s
- `Journal` — top-level container: a list of `Transaction`s, a list of
  `PriceDirective`s, `declared_accounts`, `declared_commodities`,
  `declared_payees`, `source_file`, and `included_files` count

Models are plain dataclasses. They contain no parsing or reporting logic.

### `PyLedger/checks.py`

**Single responsibility**: Validate `Journal` objects and return structured
errors without raising exceptions.

- `CheckError` — dataclass with `check_name` and `message` fields
- Individual check functions (`check_autobalanced`, `check_accounts`,
  `check_commodities`, `check_payees`, `check_ordereddates`,
  `check_uniqueleafnames`) — each returns `list[CheckError]`
- Convenience runners: `run_basic_checks`, `run_strict_checks`, `run_checks`
- Does **not** perform any file I/O, parsing, or formatting

### `PyLedger/reports.py`

**Single responsibility**: Accept a `Journal` and produce structured report
data (not formatted strings).

Reports:
- `balance(journal, ...)` → mapping of account name → running balance
- `register(journal, ...)` → list of register rows (date, description, amount, balance)
- `accounts(journal)` → sorted list of account names
- `stats(journal)` → `JournalStats` dataclass with summary statistics

Reports do **not** print to stdout — they return data that `cli.py` formats.

### `PyLedger/cli.py`

**Single responsibility**: Parse command-line arguments and coordinate
`loader` → `checks` → `reports` → formatted output.

- Uses `argparse` from the standard library
- Resolves journal file(s) via `_resolve_files()`: `-f`/`--file` flags (one or
  more), then positional shorthand, then `$LEDGER_FILE`, then
  `~/.hledger.journal`
- Loads each file with `loader.load_journal()` (or `load_journal_stdin()` for
  `-f -`), then merges with `loader.merge_journals()`
- Runs default basic checks (`autobalanced`, `parseable`) via `checks.run_basic_checks()`
  on every command before proceeding; exits 1 on failure
- With `-s`/`--strict`: additionally runs `accounts` and `commodities` checks
- `check [NAME...]` command: runs specified checks via `checks.run_checks()`
- Calls the appropriate `reports.*` function
- Formats and prints the result to stdout

---

## Error Handling Strategy

| Layer | Error type | Action |
|---|---|---|
| `loader` | `ParseError` | Raised for extension/format/circular/glob errors; line numbers re-attributed to original source file |
| `loader` | `FileNotFoundError` | Raised if root or non-glob included file is missing |
| `parser` | `ParseError` | Raised with line number and message |
| `checks` | `list[CheckError]` | Returned (never raised); CLI converts to stderr + exit 1 |
| `reports` | `ValueError` | Raised for invalid arguments |
| `cli` | Any | Caught, printed to stderr, exit code 1 |

---

## Design Principles

- Each module imports only from modules below it in the pipeline
  (`cli` → `loader` → `parser`/`models`; `cli` → `checks` → `models`;
  `reports` → `models`)
- No circular imports
- No global mutable state
