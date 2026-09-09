---
name: document-package
description: Periodic documentation audit for ledgerkit-editor — finds and fixes drift between docs (README, docs/, dev-docs/, knowledge_base/, ROADMAP, CHANGELOG) and actual code, and maintains AI-README.md, the agent-efficient project primer. Use when the user asks to audit/update/fix the docs generally, or explicitly invokes this skill by name. Do NOT use for a single doc-sync obligation on one PR — CLAUDE.md's same-response Documentation Sync Rule already covers that; this is the periodic backstop for what individual PRs miss.
user-invocable: true
---

# document-package

A periodic audit-and-repair pass over every doc in `ledgerkit-editor`,
plus upkeep of `AI-README.md` (a portable, agent-efficient project primer
distinct from the human-facing docs). Backstops — does not replace —
`CLAUDE.md`'s same-response Documentation Sync Rule and `dev-docs/SYNC.md`:
individual changes will still occasionally miss a doc update, and this is
the periodic pass that catches what slipped through. See
`planning/next-release-phase-plan.md` Phase 6 for the plan this skill was
built from, and that plan's "Documentation drift found during
investigation" section for the pilot run's findings (already fixed as of
that plan's Phase 2/6 commits — treat repeat occurrences of the same class
of drift as a signal this skill needs to run more often, not as a one-off).

**Suggested cadence:** after each release, using that release's own
`CHANGELOG.md [Unreleased]`→dated-section entries as the input list of
"things that might have drifted a doc" — every module renamed, every
keybinding added, every widget removed is a doc-drift candidate.

## Process

### 1. Audit pass

Compare every doc against the actual code, not against what the doc
*used* to say:

| Doc | Check against |
|---|---|
| `dev-docs/architecture.md` "Module Responsibilities" | `find src/ledgerkit_editor -name "*.py"` — every file present, no removed ones lingering |
| `dev-docs/architecture.md` "Layout" / "Data Flow" / "ledgerkit Integration Points" | Whatever the app actually composes today (`app.py`'s `compose()`, `JournalEditor.compose()`) — these sections have drifted badly before (see the plan's pilot findings: they described the pre-v0.8.0 `BalanceSidebar`/`RegisterPanel` architecture for months after removal) |
| `docs/shortcuts.md` | Every `Binding(...)` across `app.py` and every widget's `BINDINGS` — a mismatched key, a missing row, or a row describing removed behavior are all findings |
| `ROADMAP.md` "What Is Shipped" | The actual latest `CHANGELOG.md` version section — this drifts every time a release ships and the roadmap isn't touched |
| `ROADMAP.md` milestone checklists | Whether the described behavior actually exists and is tested — check off items that are true, but **never** mark a milestone itself `[DONE]` without the user's explicit instruction (`CLAUDE.md` Documentation Sync Rule, rule 3) |
| `README.md` | Feature bullets against what's actually shipped; installation steps against current `pyproject.toml` |
| `CLAUDE.md` "Folder Structure" | The real `src/` tree — **this file is protected** (`CLAUDE.md` Unauthorised Change Rule): state exactly what's stale and ask for confirmation before editing it; never edit it directly during an audit run |
| `knowledge_base/*.md` | Still-accurate rationale — a design decision doc describing a behavior that's since changed needs either an update or a note that it's superseded |
| `dev-docs/api-spec.md` | **Protected file** — same as `CLAUDE.md`'s folder structure: flag drift, don't fix it without approval |

### 2. Human-facing docs

Fix drift found above directly (except the two protected files, which get
flagged and held for confirmation per the table). Priorities when time is
limited:

1. `docs/shortcuts.md` — the doc most likely to have drifted, since every
   feature phase touches keybindings.
2. `dev-docs/architecture.md` — regenerate the module-tree listing from the
   real `src/` layout rather than hand-editing prose where feasible, to
   make future drift structurally harder (a tree that's copy-pasted from
   `find` output can't silently omit a file the way hand-maintained prose
   can).
3. `README.md`, `ROADMAP.md`, `knowledge_base/*.md`.

### 3. AI-README.md

Maintain `AI-README.md` at the repo root — a dense, marketing-free primer
meant to be pasted cold into a fresh AI session's first message. Distinct
from `CLAUDE.md` (which is process rules for *this* assistant working in
*this* repo) and from `README.md` (human-facing, sells the project) — this
one explains the project to an agent as fast and load-bearingly as
possible. On each run:

- Confirm the module tree, key data flows, and "load-bearing" facts (the
  two-layer undo stack, the pinned-and-private-API dependency on Textual
  8.2.5, the "never assume the ledgerkit API" rule) are still accurate.
- Update it in the same pass as any Module Responsibilities fix above —
  they're describing the same reality from two different angles (one for
  a human maintainer, one for a pasted-in agent), so they drift together.
- Keep it short enough to actually paste. If it's grown past what a human
  would realistically paste into a prompt, that's itself a finding — trim
  before adding.

### 4. Report and doc-sync the audit itself

- List every finding (fixed, and flagged-but-not-fixed for the two
  protected files) in a short summary for the user.
- The audit run itself is a substantive change — give it a
  `CHANGELOG.md [Unreleased]` entry with Human/Claude lines, same as any
  other doc change, per `CLAUDE.md`'s Changelog Rules.
- For the two protected files (`CLAUDE.md`, `dev-docs/api-spec.md`): state
  exactly what would change and wait for explicit approval, per the
  Unauthorised Change Rule — do not proceed on inference.

## What this skill is not

- Not a substitute for `dev-docs/SYNC.md`'s same-response rule — that rule
  still applies to every ordinary change; this skill is the periodic net
  underneath it, not a replacement.
- Not a codebase quality pass — that's `.claude/skills/polish-codebase/
  SKILL.md`, even though a structural rename there is exactly the kind of
  thing this skill needs to catch afterward.
- Not license to rewrite doc *content* wholesale on a whim — fix drift
  (inaccurate, stale, or missing information), don't restyle or shorten
  prose that's still correct just because it could be phrased differently.
