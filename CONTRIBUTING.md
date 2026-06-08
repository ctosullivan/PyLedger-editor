# Contributing to ledgerkit-editor

## Development Setup

```bash
git clone https://github.com/ctosullivan/ledgerkit-editor.git
cd ledgerkit-editor

python -m venv .venv
.venv\Scripts\activate       # Windows
# source .venv/bin/activate  # macOS / Linux

pip install --upgrade pip
pip install -e ".[dev]"
```

Run the test suite:

```bash
pytest --tb=short
```

Launch the editor (requires a journal file):

```bash
python -m ledgerkit_editor path/to/my.journal
# or
ledgerkit-editor path/to/my.journal
```

---

## Updating ledgerkit

`ledgerkit` is a normal PyPI dependency. To update, change the version pin in
`pyproject.toml` and run `pip install -e .`. Review the ledgerkit
[changelog](https://github.com/ctosullivan/ledgerkit/blob/master/CHANGELOG.md)
and `knowledge_base/ledgerkit_api_notes.md` for breaking changes before bumping.

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
