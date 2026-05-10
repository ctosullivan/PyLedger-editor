# CLAUDE.md — Project Context and Rules

## Project Identity

This is **PyLedger**: a Python implementation of the [hledger](https://hledger.org)
plain-text accounting tool.

- **Target Python**: 3.10+
- **Dependency policy**: Prefer Python built-in libraries. No third-party packages
  in `PyLedger/` core modules without explicit user approval.
- **Supported file formats**: `.journal`, `.ledger` (see `dev-docs/hledger-compatibility.md`)

---

## Knowledge Base

Project-specific knowledge that Claude cannot infer from code lives in `knowledge/`:

| File | Purpose |
|---|---|
| `knowledge/DECISIONS.md` | Non-obvious judgment calls — what was chosen, why, and what was rejected |
| `knowledge/EDGE_CASES.md` | Human-identified edge cases that are non-obvious or regression-prone |
| `knowledge/ANTIPATTERNS.md` | Approaches tried and abandoned — do not revisit without reading these first |
| `knowledge/DOMAIN_RULES.md` | Tacit hledger format rules and PyLedger invariants Claude can't infer from code |

**When to update:** Add an entry to the relevant file whenever a non-obvious decision is made, an edge case is identified, or an approach is abandoned. Do this **in the same response** as the change.

---

## Context File (`CONTEXT.md`)

`CONTEXT.md` at the project root is Claude's working memory between sessions. It records where we are *right now* — not permanent history (that goes in `knowledge/` or `CHANGELOG.md`).

**Claude must overwrite `CONTEXT.md` completely at the end of every response that makes a substantive change**, replacing all sections with the current state. The file is throwaway by design.

Sections to maintain:
- **Current Task** — one sentence: what we're trying to achieve
- **Where We Are** — the literal next step (not a summary)
- **Decisions In Flight** — session-level calls not yet in `knowledge/DECISIONS.md`
- **Files Currently Relevant** — only files needed for the immediate next step
- **Blockers / Open Questions** — unresolved items needing a human decision
- **What NOT To Revisit** — closed decisions Claude might otherwise re-litigate
- **Recent Git State** — `git log --oneline -5` output

---

## Documentation Sync Rules (CRITICAL)

Whenever any of the following change, the corresponding doc(s) **MUST** be updated
**in the same response** — no exceptions, no deferring to a follow-up:

| What changed | Doc to update |
|---|---|
| Public function/class signatures (added, removed, renamed, retyped) | `dev-docs/api-spec.md` |
| Module responsibilities or data-flow | `dev-docs/architecture.md` |
| Hledger format feature support (added, removed, changed) | `dev-docs/hledger-compatibility.md` |
| CLI commands, journal format, or public Python API (user-facing) | `docs/` (human docs — usage, journal-format, python-api) |
| Any substantive code or doc change | `CHANGELOG.md` (new entry in `[Unreleased]`) |
| Milestone completed or scope confirmed | `ROADMAP.md` (status updated) |

Claude must **NEVER** make code changes that silently break the docs.

If Claude is unsure whether a change requires a doc update, it must **ask before
proceeding**.

See `dev-docs/SYNC.md` for the full sync contract.

---

## Unauthorised Change Rule

The following **must NOT be changed** without explicit user approval:

1. `dev-docs/api-spec.md` — public API contracts
2. `pyproject.toml` — dependencies and project metadata
3. The folder structure described in this file

If a user request would affect any of these, Claude must:
1. State exactly what would change
2. Ask for confirmation before making the change

---

## Testing Rules

- All new public functions must have a corresponding test in `tests/`
- Use Python's built-in `unittest` module only (no pytest, no third-party runners)
- Test fixtures (sample journals, etc.) go in `tests/fixtures/`
- Test file naming: `test_<module>.py` (e.g. `test_parser.py`)
- Test method naming: `test_<behaviour>` (e.g. `test_parse_simple_transaction`)

Run the full test suite:
```
python -m unittest discover -s tests -t . -v
```

---

## Code Style

- **Type hints** on all public functions and methods
- **Docstrings** on all public classes and functions (one-line summary minimum)
- No third-party imports in `PyLedger/` without user approval
- Keep modules focused: see `dev-docs/architecture.md` for each module's
  single responsibility

### Regex Documentation Rule

Every regular expression — whether compiled with `re.compile()` or used inline —
**must** be accompanied by a multiline comment directly above it. The comment must
cover all three of:

1. **Purpose** — what the regex is trying to match and why
2. **Group breakdown** — each capture group explained by index and name
3. **Edge cases** — non-obvious inputs it accepts or rejects, and why

Example of the required style:

```python
# Matches a transaction header line in hledger journal format.
# Purpose: extract date, optional status flag, optional code, description,
#          and optional inline comment from a single non-indented line.
#
# Group breakdown:
#   (1) \d{4}-\d{2}-\d{2}  — ISO date, required, always first token
#   (2) [*!]?               — status flag: * = cleared, ! = pending, absent = uncleared
#   (3) \(([^)]*)\)         — transaction code in parens, e.g. (INV-42); full parens consumed,
#                             only the inner text is captured
#   (4) .*?                 — description: lazy so the trailing comment anchor can match
#   (5) (?:\s*;\s*(.*))?    — inline comment after ';'; the ';' itself is not captured
#
# Edge cases:
#   - Description may be empty (e.g. "2024-01-01 *" with no text after flag)
#   - Code may be absent even when a flag is present
#   - A ';' inside the description (before two spaces) would be mis-parsed as a comment;
#     this is acceptable per v1 scope (hledger itself treats first ';' as comment start)
_TXN_HEADER = re.compile(
    r"^(\d{4}-\d{2}-\d{2})"
    r"\s*([*!])?"
    r"\s*(?:\(([^)]*)\))?"
    r"\s*(.*?)"
    r"(?:\s*;\s*(.*))?$"
)
```

Claude must apply this rule whenever it writes or modifies a regex, including
retroactively if editing a file that already contains undocumented regexes.

---

## Module Size & Refactoring

When a module (`PyLedger/*.py`) or test file (`tests/test_*.py`) approaches or exceeds
**300–500 lines**, or is handling more than one clear responsibility, it is a signal that
a refactor should be considered.

Claude must **never initiate a major refactor unilaterally**. The process is:

1. **Flag the concern** — note the file, its current line count, and the responsibilities
   that appear to have accumulated.
2. **Propose a split** — describe the suggested sub-modules or reorganisation (new file
   names, what moves where).
3. **Wait for explicit approval** — do not move or rewrite any code until the user confirms
   the proposal.

This applies equally to production modules and test files.

> A "major refactor" means moving, splitting, or substantially reorganising code across
> files. Routine tidying within a single function does not require approval.

---

## Hledger Compatibility

- Consult `dev-docs/hledger-compatibility.md` before implementing any parser feature
- Do **not** silently implement out-of-scope features — document them first
- When in doubt about format semantics, link to the official hledger docs

---

## Changelog & Roadmap Rules

- Every substantive code or doc change must have a corresponding `CHANGELOG.md`
  entry added **in the same response**, placed at the top of the `[Unreleased]`
  section
- Each entry must include a **Human** line (what the user directed) and a
  **Claude** line (what Claude implemented)
- A milestone must **only** be marked `[DONE]` in `ROADMAP.md` when the user
  explicitly states it is complete — Claude must never infer completion
  unilaterally
- Do not move individual changelog entries from `[Unreleased]` to a versioned
  section — that is done manually at commit time by the user

### Milestone archiving

When the user explicitly states that a milestone is complete (and its status is
therefore `[DONE]`), Claude must archive its changelog entries **in the same
response**:

1. Create `dev-docs/changelog/MILESTONE-N.md` containing all dev entries for that
   milestone (oldest first), the archive date, and the relevant commit hashes
2. Replace those entries in `CHANGELOG.md` with a single summary line linking
   to the archive file
3. Ensure `dev-docs/changelog/` exists (create it if absent)

See the "Archiving at milestone completion" section in `CHANGELOG.md` for the
exact file format and templates.

### Commit Message Format

When producing a commit message, follow [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>: <short summary>
```

**Types:** `feat`, `fix`, `docs`, `test`, `style`, `refactor`, `chore`

Rules:
- Imperative mood ("add feature" not "added feature")
- Summary under 72 characters
- No period at end of summary
- Blank line + body for complex changes

---

## Folder Structure (do not change without approval)

```
PyLedger/
├── CLAUDE.md
├── CONTEXT.md                       ← Claude's session working memory (overwrite each session)
├── README.md
├── ROADMAP.md
├── CHANGELOG.md
├── LICENSE
├── MANIFEST.in
├── .gitignore
├── pyproject.toml
├── knowledge/                       ← permanent project knowledge base
│   ├── DECISIONS.md                 ← non-obvious judgment calls and why
│   ├── EDGE_CASES.md                ← human-identified edge cases
│   ├── ANTIPATTERNS.md              ← approaches tried and abandoned
│   └── DOMAIN_RULES.md             ← tacit hledger/domain rules
├── dev-docs/                        ← AI-workflow / developer docs
│   ├── api-spec.md
│   ├── architecture.md
│   ├── hledger-compatibility.md
│   ├── SYNC.md
│   └── changelog/                   ← milestone archive files live here
├── docs/                            ← human-facing user documentation
│   ├── getting-started.md
│   ├── usage.md
│   ├── journal-format.md
│   └── python-api.md
├── tests/
│   ├── __init__.py
│   ├── fixtures/
│   │   └── sample.journal
│   ├── test_parser/             ← core transaction and amount parsing tests
│   │   ├── __init__.py
│   │   └── test_parser.py
│   ├── test_directives/         ← directive parsing tests
│   │   ├── __init__.py
│   │   └── test_directives.py
│   ├── test_checks/             ← validation check tests
│   │   ├── __init__.py
│   │   └── test_checks.py
│   ├── test_cli/                ← CLI integration tests
│   │   ├── __init__.py
│   │   └── test_cli.py
│   ├── test_loader/             ← multi-file loading tests
│   │   ├── __init__.py
│   │   └── test_loader.py
│   ├── test_reports/            ← earmarked for future report tests
│   ├── test_reports.py
│   └── README.md
└── PyLedger/
    ├── __init__.py
    ├── __main__.py
    ├── parser.py
    ├── models.py
    ├── reports.py
    └── cli.py
```
