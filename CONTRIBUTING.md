# Contributing to LedgerKit Editor

## Development Setup

```bash
python -m venv .venv
.venv\Scripts\activate       # Windows
# source .venv/bin/activate  # macOS / Linux
pip install --upgrade pip
pip install textual==8.2.5 pytest pytest-asyncio

# Install ledgerkit from the vendor snapshot (editable so imports resolve correctly).
pip install -e vendor/ledgerkit/
```

Run the test suite:

```bash
pytest --tb=short
```

Launch the editor (requires a journal file):

```bash
python -m ledgerkit_editor path/to/my.journal
# or
ledgerkit-editor path/to/my.journal   # if installed via pip install -e .
```

---

## Updating ledgerkit (Vendor Dependency)

ledgerkit is updated frequently. Follow this workflow precisely when a new
version is available.

```bash
# 1. Remove write-lock from vendor tree (Windows)
attrib -R /S /D vendor\ledgerkit\*

# (macOS / Linux: chmod -R u+w vendor/ledgerkit)

# 2. Fetch the new tag (replace X.Y.Z with the new version)
git -C vendor/ledgerkit fetch --depth=1 origin refs/tags/vX.Y.Z
git -C vendor/ledgerkit checkout FETCH_HEAD

# 3. Update pip dependency and re-pin
pip install -e vendor/ledgerkit/
pip freeze > requirements.txt
# Also update pyproject.toml dependencies.ledgerkit to ==X.Y.Z

# 4. Re-apply write-lock
attrib +R /S /D vendor\ledgerkit\*

# (macOS / Linux: chmod -R a-w vendor/ledgerkit)

# 5. Compare CHANGELOG and API spec for breaking changes
#    Open and compare:
#      vendor/ledgerkit/CHANGELOG.md
#      vendor/ledgerkit/dev-docs/api-spec.md
#    Update knowledge_base/ledgerkit_api_notes.md to reflect any API changes.

# 6. Run the full test suite to surface any breaking changes
pytest --tb=short
```

After updating, commit the vendor snapshot and updated requirements:

```bash
git add vendor/ledgerkit requirements.txt pyproject.toml knowledge_base/ledgerkit_api_notes.md
git commit -m "chore: update ledgerkit to vX.Y.Z"
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
