# CLAUDE.md — Project Context and Rules

## Project Identity

This is **Ledger Editor**: a terminal-based, keyboard-driven plain-text ledger
editor built with [Textual](https://textual.textualize.io/) and
[PyLedger](https://github.com/ctosullivan/PyLedger).

- **Target Python**: 3.11+
- **UI framework**: Textual (pinned to 8.2.5)
- **Ledger backend**: PyLedger v0.5.0 (vendor-pinned, read-only)
- **Supported file formats**: `.journal`, `.ledger` (hledger-compatible)

See `dev-docs/architecture.md` for the module layout and data-flow diagram.

---

## PyLedger Vendor Rule (CRITICAL)

**Always consult `vendor/pyledger/` before writing any code that calls PyLedger.**

1. Read `vendor/pyledger/dev-docs/api-spec.md` for the definitive function
   signatures and return types.
2. Read `vendor/pyledger/pyLedger/models.py` for the exact dataclass field names.
3. **Never assume the API** — the prompt description may lag behind the actual
   source. The vendor checkout is authoritative.

Key discrepancy vs original spec: `Transaction` uses **`cleared: bool`** and
**`pending: bool`** (not a `flag: str | None` field). Always check models.py.

### Vendor Update Workflow

See `CONTRIBUTING.md` for the full workflow. Short form:

```bash
# 1. Remove write-lock
attrib -R /S /D vendor\pyledger\*

# 2. Fetch new version
git -C vendor/pyledger fetch --depth=1 origin refs/tags/vX.Y.Z
git -C vendor/pyledger checkout FETCH_HEAD

# 3. Update pip dep and re-pin
pip install pyledger==X.Y.Z
pip freeze > requirements.txt

# 4. Re-apply write-lock
attrib +R /S /D vendor\pyledger\*

# 5. Compare CHANGELOG.md and dev-docs/api-spec.md; update knowledge_base/
# 6. Run pytest
```

---

## Documentation Sync Rules (CRITICAL)

Whenever any of the following change, the corresponding doc(s) **MUST** be
updated **in the same response** — never deferred:

| What changed | Doc to update |
|---|---|
| Public function/class signatures (added, removed, renamed, retyped) | `dev-docs/api-spec.md` |
| Module responsibilities or data-flow | `dev-docs/architecture.md` |
| Widget behaviour or keybinding semantics | `docs/shortcuts.md` |
| Any substantive code or doc change | `CHANGELOG.md` (new entry in `[Unreleased]`) |
| Milestone completed or scope confirmed | `ROADMAP.md` (status updated) |

See `dev-docs/SYNC.md` for the full sync contract.

---

## Unauthorised Change Rule

The following **must NOT be changed** without explicit user approval:

1. `dev-docs/api-spec.md` — internal API contracts
2. `pyproject.toml` — dependencies and project metadata
3. The folder structure described in this file

If a request would affect any of these, Claude must:
1. State exactly what would change
2. Ask for confirmation before making the change

---

## Regex Documentation Rule

Every regular expression — whether compiled with `re.compile()` or used inline —
**must** be accompanied by a multiline comment directly above it covering:

1. **Purpose** — what the regex matches and why
2. **Group breakdown** — each capture group by index and name
3. **Edge cases** — non-obvious inputs it accepts or rejects

See `vendor/pyledger/CLAUDE.md` for the exact required style with a worked
example. Replicate that style verbatim.

---

## Changelog & Roadmap Rules

- Every substantive code or doc change gets a `CHANGELOG.md` entry added
  **in the same response**, placed at the top of the `[Unreleased]` section.
- Each entry must include a **Human:** line (what the user directed) and a
  **Claude:** line (what was implemented).
- A milestone is only marked `[DONE]` in `ROADMAP.md` on **explicit user
  instruction** — Claude never infers completion.

### Commit Message Format

Follow [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>: <short summary>
```

Types: `feat`, `fix`, `docs`, `test`, `style`, `refactor`, `chore`

- Imperative mood ("add feature" not "added feature")
- Summary under 72 characters, no period

---

## Testing Rules

- All new public functions, widgets, and keybinding handlers must have
  corresponding `pytest` tests in `tests/`.
- Test runner: **pytest** with **pytest-asyncio** (`asyncio_mode = "auto"`).
- Fixtures (sample journals, etc.) go in `tests/fixtures/`.
- Test file naming: `test_<module>.py`

Run the full test suite:

```bash
pytest --tb=short
```

---

## Coding Conventions

- **Async-first**: use Textual workers for all I/O; never block the event loop.
- **Reactive attributes**: use Textual's `reactive()` for widget state that
  drives re-renders; document in `knowledge_base/textual_patterns.md`.
- **Type hints** on all public functions and methods.
- **Docstrings** on all public classes and functions (one-line summary minimum).
- No comments explaining WHAT the code does — only WHY when non-obvious.
- No multi-paragraph docstrings.

---

## Module Size Rule

When a module or test file approaches 300–500 lines, or handles more than one
clear responsibility:

1. Flag the concern with the current line count.
2. Propose a split (new file names, what moves where).
3. Wait for explicit approval before moving any code.

---

## Context File

`CONTEXT.md` is Claude's working memory between sessions. Overwrite it
completely at the end of every response that makes a substantive change.

Sections to maintain:
- **Current Task**
- **Where We Are**
- **Decisions In Flight**
- **Files Currently Relevant**
- **Blockers / Open Questions**
- **What NOT To Revisit**
- **Recent Git State**

---

## Folder Structure (do not change without approval)

```
ledger-editor/
├── src/ledger_editor/
│   ├── app.py                   — LedgerApp (Textual App subclass)
│   ├── widgets/
│   │   ├── balance_sidebar.py   — BalanceSidebar widget
│   │   ├── transaction_table.py — JournalEditor widget (main editing surface)
│   │   ├── ledger_textarea.py   — LedgerTextArea subclass (syntax + search highlights)
│   │   ├── search_bar.py        — SearchBar widget (Ctrl+F incremental search)
│   │   ├── reconcile_actions.py — ReconcileMixin + pure reconcile helpers
│   │   ├── reconcile_bar.py     — ReconcileStatusBar (shown during reconcile mode)
│   │   ├── reconcile_summary.py — ReconcileSummary (RegisterPanel reconcile view)
│   │   ├── register_panel.py    — RegisterPanel with ContentSwitcher
│   │   └── filter_popup.py      — FilterPopup overlay (Ctrl+Shift+P)
│   ├── keybindings/
│   │   ├── office.py            — MS Office / Excel convention stubs
│   │   └── emacs_ledger.py      — Emacs Ledger-mode convention stubs
│   ├── commands/__init__.py     — command palette stubs
│   └── utils/
│       ├── date_parser.py       — smart date parsing
│       ├── ledger_io.py         — load/save via PyLedger
│       └── file_resolver.py     — journal file resolution
├── tests/
├── vendor/pyledger/             — READ-ONLY sparse checkout of PyLedger v0.5.0
├── knowledge_base/              — project-specific knowledge
├── docs/                        — user-facing documentation
├── dev-docs/                    — developer/AI documentation
├── CLAUDE.md                    — this file
├── CONTEXT.md                   — session working memory
├── CONTRIBUTING.md              — vendor update + dev guide
├── CHANGELOG.md
├── ROADMAP.md
└── pyproject.toml
```
