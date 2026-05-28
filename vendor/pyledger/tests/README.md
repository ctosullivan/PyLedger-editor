# Tests

## Running Tests

Run the full test suite from the project root:

```bash
python -m unittest discover -s tests -t . -v
```

Run a single test module:

```bash
python -m unittest tests.test_parser.test_parser
python -m unittest tests.test_directives.test_directives
python -m unittest tests.test_checks.test_checks
python -m unittest tests.test_cli.test_cli
python -m unittest tests.test_loader.test_loader
python -m unittest tests.test_reports
```

Run a single test case or method:

```bash
python -m unittest tests.test_parser.test_parser.TestParseStringSampleJournal
python -m unittest tests.test_directives.test_directives.TestAliasDirective.test_basic_alias_exact_match
```

## Folder Structure

```
tests/
├── fixtures/                    ← sample journal files
│   └── sample.journal
├── test_parser/                 ← core transaction and amount parsing
│   ├── __init__.py
│   └── test_parser.py
├── test_directives/             ← directive parsing (account, commodity, etc.)
│   ├── __init__.py
│   └── test_directives.py
├── test_checks/                 ← validation checks (autobalanced, strict, etc.)
│   ├── __init__.py
│   └── test_checks.py
├── test_cli/                    ← CLI integration tests
│   ├── __init__.py
│   └── test_cli.py
├── test_loader/                 ← multi-file journal loading
│   ├── __init__.py
│   └── test_loader.py
├── test_reports/                ← earmarked for future report tests
├── test_reports.py              ← report / stats tests (flat file)
└── README.md
```

**Note:** Each test subdirectory requires an `__init__.py` file. Without it, Python
3.13's `unittest discover` silently skips the directory when recursing.

## Conventions

### File naming

| What | Convention | Example |
|---|---|---|
| Test module | `test_<area>.py` | `test_parser.py`, `test_directives.py` |
| Test class | `Test<What>` | `TestParseStringSampleJournal`, `TestAliasDirective` |
| Test method | `test_<behaviour>` | `test_basic_alias_exact_match` |

### What to test

- Every public function in `PyLedger/` must have at least one test.
- Tests should cover the happy path and the most important error paths.
- For parser tests: test both valid input (produces expected model) and
  invalid input (raises `ParseError` with a useful message).

### Fixtures

Sample journal files live in `tests/fixtures/`. Load them with a path relative
to the test file's own directory:

```python
import pathlib

FIXTURES = pathlib.Path(__file__).parent.parent / "fixtures"
SAMPLE_JOURNAL = FIXTURES / "sample.journal"
```

Note the `.parent.parent` — test files inside subdirectories (e.g. `test_parser/`)
are one level down from `tests/`, so the fixtures path goes up two levels.

Add new fixture files when a test requires a specific journal structure not
covered by `sample.journal`. Name fixtures descriptively:
`minimal.journal`, `multi_currency.journal`, `malformed_date.journal`, etc.

### No third-party test dependencies

Tests use Python's built-in `unittest` only. Do not add pytest, hypothesis,
or any other test library without user approval.
