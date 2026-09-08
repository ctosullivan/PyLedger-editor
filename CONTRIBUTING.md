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

- Python 3.9+ (matches `pyproject.toml`'s `requires-python`), type hints on all public functions
- `black` for formatting (line length 88)
- No inline comments explaining WHAT — only WHY when non-obvious
- Regex rules: see CLAUDE.md §Regex Documentation Rule

## Testing

- All new public functions, widgets, and keybinding handlers require a `pytest` test
- Fixtures (sample journals) go in `tests/fixtures/`
- Run with: `pytest --tb=short`

---

## Repeatable Maintenance Skills

Two Claude Code skills live in `.claude/skills/` for periodic, opt-in
maintenance passes — neither runs automatically; invoke by name when
wanted, typically after a release:

- **`polish-codebase`** — a non-functional-change pass (dead code,
  duplication, efficiency, CLAUDE.md convention compliance) with a hard
  behavior-unchanged gate. See `.claude/skills/polish-codebase/SKILL.md`.
- **`document-package`** — a documentation audit that finds and fixes
  drift between the docs and the actual code, and maintains
  `AI-README.md` (a portable, agent-efficient project primer, distinct
  from this file and from `CLAUDE.md`). See
  `.claude/skills/document-package/SKILL.md`.

Both were built from `planning/next-release-phase-plan.md`'s Phase 5/6.
