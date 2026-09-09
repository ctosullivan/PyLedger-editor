---
name: polish-codebase
description: Periodic, opt-in, non-functional-change pass over ledgerkit-editor — dead code, duplication, efficiency, and CLAUDE.md convention compliance, with a hard behavior-unchanged gate. Use when the user asks to polish, tidy, clean up, or simplify the codebase generally (not a specific bug or feature), or explicitly invokes this skill by name. Do NOT use for a normal feature/bugfix diff review — that's /code-review.
user-invocable: true
---

# polish-codebase

A deliberate, explicit-ask pass over the whole `ledgerkit-editor` codebase
for structure, readability, and efficiency — never behavior. This exists
because Claude's default behavior is to *not* refactor beyond what a task
requires; this skill is the sanctioned channel for that work when the user
actually wants it, run periodically rather than folded into unrelated
feature commits. See `planning/next-release-phase-plan.md` Phase 5 for the
plan this skill was built from.

**Suggested cadence:** once per minor release (after a feature phase lands),
not on a fixed calendar schedule — this codebase doesn't accumulate enough
cruft week-to-week to justify a timer. Tying it to release boundaries keeps
each run meaningful.

## Process

### 1. Baseline gate

Run the full suite before touching anything:

```
pytest --tb=short
```

If it isn't green at the start, **stop and report** — this skill polishes
working code, it does not fix pre-existing failures as a side effect (that's
a separate, ordinary bugfix task).

### 2. Delegate the mechanical review

Don't reinvent dead-code/duplication/efficiency detection — this environment
already has two skills for exactly that:

- `/code-review` at medium-to-high effort, for the reuse/simplification/
  efficiency findings.
- `/simplify` to apply the fixes it finds.

Run these across the working tree (or a deliberately scoped subset — see
"Scoping a run" below) rather than hand-rolling an equivalent pass. This
skill's job is the project-specific layer on top of what those two already
know how to do, not a replacement for them.

### 3. Project-specific checklist

This is the part `/code-review` and `/simplify` can't know, because it's
specific to this repo's own `CLAUDE.md`:

- **Regex Documentation Rule** — every `re.compile(...)` (inline or not)
  still has its Purpose / Group breakdown / Edge cases comment directly
  above it, and that comment is still accurate to what the regex actually
  does (not just present).
- **Module Size Rule** — no module has quietly grown past 300–500 lines
  since the last run without being flagged. Check with:
  ```
  find src -name "*.py" | xargs wc -l | sort -n
  ```
  A module over the guidance gets a **flagged proposal** (current line
  count + a concrete split, file-for-file) — never an unapproved split.
  Wait for explicit approval before moving code, exactly as the rule says.
- **No what-comments** — comments explain *why*, never *what* the code
  already says on its face. Flag (and remove, if trivially safe) any that
  just restate the following line in English.
- **Docstring length** — one-line minimum, no multi-paragraph docstrings
  (per `CLAUDE.md`'s Coding Conventions).
- **Duplication against `knowledge_base/`** — if this pass finds a pattern
  already documented in `knowledge_base/textual_patterns.md` or
  `knowledge_base/design_decisions.md` being reinvented slightly
  differently elsewhere, that's worth surfacing even if `/simplify` doesn't
  catch it as classic duplication.

### 4. The non-negotiable: behavior must not change

- Every fix in scope for this skill is structural: renaming, dead-code
  removal, deduplication, a cleaner equivalent expression — never a change
  in what the program does for any input.
- If `/code-review` or `/simplify` surfaces something that *would* change
  behavior (a real bug, a missing edge case), **do not fix it here** — note
  it and hand it back to the user as a separate, ordinary finding. Mixing a
  behavior fix into a polish pass defeats the point of having a
  behavior-unchanged pass at all.
- Re-run the full suite after every change:
  ```
  pytest --tb=short
  ```
  A red suite at the end means something in this pass changed behavior —
  find it and back it out, don't patch the test to match.

### 5. Doc sync and reporting

- Anything substantive found *and fixed* gets a `CHANGELOG.md [Unreleased]`
  entry, per `CLAUDE.md`'s Changelog Rules — **Human:** line can simply be
  "periodic polish pass", **Claude:** line describes what moved/was removed
  and why.
- If a fix touches a module's responsibilities enough to matter,
  `dev-docs/architecture.md` needs the same update, same response, per the
  Documentation Sync Rule.
- Produce a short before/after summary for the user at the end (files
  touched, one line each on what changed and why) — this skill *proposes*,
  it doesn't commit silently. Committing is a separate, explicit step the
  user asks for, same as any other change in this repo.

## Scoping a run

Default to the whole `src/ledgerkit_editor/` tree. If the user names a
specific module, directory, or "just the stuff we touched in the last
release," scope `/code-review` and `/simplify` to that instead — a targeted
polish pass is still a valid use of this skill, not a compromise on it.

## What this skill is not

- Not a bug hunt — that's `/code-review` on a specific diff, or a plain bug
  report from the user.
- Not a feature-addition pass — new functionality, however small, belongs
  in an ordinary feature task with its own plan, not folded into a polish
  run.
- Not a documentation audit — that's `/document-package`'s job (see
  `.claude/skills/document-package/SKILL.md`), even though the two overlap
  at the edges (a structural rename here can leave a doc stale there).
