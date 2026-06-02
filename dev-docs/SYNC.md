# Documentation Sync Contract

This file defines what must be kept in sync when code changes.
It mirrors the approach in `vendor/ledgerkit/dev-docs/SYNC.md`.

---

## Trigger → Doc mapping

| Trigger | Required doc update |
|---------|---------------------|
| Public function/class signature added, removed, renamed, or retyped | `dev-docs/api-spec.md` |
| Module responsibility or data-flow changes | `dev-docs/architecture.md` |
| Keybinding added, removed, or rebound | `docs/shortcuts.md` |
| Widget behaviour visible to users changes | `docs/shortcuts.md` + `dev-docs/architecture.md` |
| Any substantive code or doc change | `CHANGELOG.md` (new entry in `[Unreleased]`) |
| Milestone completed (on user instruction only) | `ROADMAP.md` |
| ledgerkit vendor updated | `knowledge_base/ledgerkit_api_notes.md` |
| Terminal-emulator conflict discovered | `knowledge_base/design_decisions.md` |

## Rules

1. Doc updates happen **in the same response** as the triggering change — never
   deferred to a follow-up.

2. If unsure whether a change triggers a doc update, **ask before proceeding**.

3. Claude must never mark a ROADMAP milestone `[DONE]` without explicit user
   instruction — "I think this is done" is not sufficient.

4. `dev-docs/api-spec.md`, `pyproject.toml`, and the canonical folder structure
   are protected: state exactly what would change and ask for confirmation first.
