# Contributing to Ledger Editor

## Development Setup

```bash
python -m venv .venv
.venv\Scripts\activate       # Windows
# source .venv/bin/activate  # macOS / Linux
pip install --upgrade pip
pip install textual==8.2.5 pytest pytest-asyncio

# Install PyLedger from the vendor snapshot (editable so imports resolve correctly).
# The PyPI 'pyledger' package is a stub — always use the vendor version.
pip install -e vendor/pyledger/
```

> **Windows note**: the vendor checkout may place the source package in a directory
> named `pyLedger` (lowercase 'py') due to Windows filesystem case-folding. If you
> get `ModuleNotFoundError: No module named 'PyLedger'` after install, rename it:
>
> ```powershell
> Rename-Item vendor\pyledger\pyLedger PyLedger_tmp
> Rename-Item vendor\pyledger\PyLedger_tmp PyLedger
> pip install -e vendor/pyledger/
> ```

Run the test suite:

```bash
pytest --tb=short
```

Launch the editor (requires a journal file):

```bash
python -m ledger_editor path/to/my.journal
# or
ledger-editor path/to/my.journal   # if installed via pip install -e .
```

---

## Updating PyLedger (Vendor Dependency)

PyLedger is updated frequently. Follow this workflow precisely when a new
version is available.

```bash
# 1. Remove write-lock from vendor tree (Windows)
attrib -R /S /D vendor\pyledger\*

# (macOS / Linux: chmod -R u+w vendor/pyledger)

# 2. Fetch the new tag (replace X.Y.Z with the new version)
git -C vendor/pyledger fetch --depth=1 origin refs/tags/vX.Y.Z
git -C vendor/pyledger checkout FETCH_HEAD

# 3. Update pip dependency and re-pin
pip install pyledger==X.Y.Z
pip freeze > requirements.txt
# Also update pyproject.toml dependencies.pyledger to ==X.Y.Z

# 4. Re-apply write-lock
attrib +R /S /D vendor\pyledger\*

# (macOS / Linux: chmod -R a-w vendor/pyledger)

# 5. Compare CHANGELOG and API spec for breaking changes
#    Open and compare:
#      vendor/pyledger/CHANGELOG.md
#      vendor/pyledger/dev-docs/api-spec.md
#    Update knowledge_base/pyledger_api_notes.md to reflect any API changes.

# 6. Run the full test suite to surface any breaking changes
pytest --tb=short
```

After updating, commit the vendor snapshot and updated requirements:

```bash
git add vendor/pyledger requirements.txt pyproject.toml knowledge_base/pyledger_api_notes.md
git commit -m "chore: update PyLedger to vX.Y.Z"
```

---

## Code Style

- Python 3.11+, type hints on all public functions
- `black` for formatting (line length 88)
- No inline comments explaining WHAT — only WHY when non-obvious
- Regex rules: see CLAUDE.md §Regex Documentation Rule

## Testing

- All new public functions, widgets, and keybinding handlers require a `pytest` test
- Fixtures (sample journals) go in `tests/fixtures/`
- Run with: `pytest --tb=short`
