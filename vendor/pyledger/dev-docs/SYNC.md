# Documentation Sync Contract

## What Must Stay in Sync

| Code location | Doc to keep in sync |
|---|---|
| Public function/class signatures in `PyLedger/parser.py`, `PyLedger/models.py`, `PyLedger/reports.py`, `PyLedger/cli.py` | `dev-docs/api-spec.md` |
| Module responsibilities, data flow, import rules | `dev-docs/architecture.md` |
| Supported/unsupported hledger journal features | `dev-docs/hledger-compatibility.md` |
| Folder structure, rules, policies | `CLAUDE.md` |
| CLI commands, journal format, public Python API | `docs/` (human docs — getting-started, usage, journal-format, python-api) |

## Who Is Responsible

**Claude** is responsible for keeping docs in sync with code changes.

The rule is simple: if you change code, update the docs **in the same
response**. Do not defer doc updates to a follow-up message or commit.

## How to Verify Sync Is Current

1. Check `dev-docs/api-spec.md` — every public function in `PyLedger/` must
   have an entry. Every entry must match the current signature (name,
   parameters, return type, docstring summary).

2. Check `dev-docs/architecture.md` — the module responsibility table must
   accurately describe what each module currently does.

3. Check `dev-docs/hledger-compatibility.md` — any format feature the parser
   handles must appear in the "In Scope" table. Any feature that raises or
   silently ignores must be documented in "Out of Scope".

4. Check `docs/` human guides — CLI command docs, journal format examples,
   and the Python API guide must reflect any user-facing changes.

A quick audit checklist:

```
[ ] Every public function in PyLedger/ has a dev-docs/api-spec.md entry
[ ] No api-spec.md entry is stale (wrong signature or removed function)
[ ] architecture.md data-flow diagram matches actual import structure
[ ] hledger-compatibility.md "In Scope" matches parser capabilities
[ ] hledger-compatibility.md "Out of Scope" matches parser behaviour
[ ] docs/ human guides reflect current CLI commands and API
```

## When Sync May Be Broken

- A function was renamed without updating `dev-docs/api-spec.md`
- A new report was added to `reports.py` but not documented
- A parser feature was extended to handle a new format element without
  updating `dev-docs/hledger-compatibility.md`
- A module was split or merged without updating `dev-docs/architecture.md`
- A CLI command was added or changed without updating `docs/usage.md`

If you discover a sync gap, fix it immediately before making further changes.
