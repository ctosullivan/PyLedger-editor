# AI-README — ledgerkit-editor

A portable primer for an AI agent working in this repo. Paste this whole
file as the first message of a fresh session and it should be immediately
useful — it's the load-bearing facts, not marketing copy. For process
*rules* this assistant follows in this repo, see `CLAUDE.md` instead; this
file is "what the project is and how it works," that one is "how to behave
while changing it." Both drift together — keeping this file accurate is
part of `.claude/skills/document-package/SKILL.md`'s job.

## What this is

A keyboard-driven terminal (TUI) editor for **hledger-format plain-text
accounting journals** (`.journal`/`.ledger` files) — think "vim/emacs for
double-entry bookkeeping in a text file." Built on
[Textual](https://textual.textualize.io/) (pinned `8.2.5`) for the UI and
[ledgerkit](https://github.com/ctosullivan/ledgerkit) (pinned
`1.0.0.dev1`, same author) for parsing/serializing hledger syntax and
running reports. Python 3.9+. Early beta — journal files can be corrupted
by bugs; the app itself says so on launch.

Entry point: `ledgerkit-editor path/to/file.journal` (console script) or
`python -m ledgerkit_editor path/to/file.journal`. No arg → resolves via
`$LEDGER_FILE` → `~/.hledger.journal` → interactive prompt.

## How it works — the shape of the code

`src/ledgerkit_editor/`:

- **`app.py`** — `LedgerApp` (Textual `App` root). Composes `Header`, a
  file-path status bar, `JournalEditor` (the entire editing surface — no
  side panels), `Footer`. Owns the `FilterPopup` overlay (Ctrl+O) as a
  Screen-level sibling of `JournalEditor`, and handles its messages
  (`FilterApplied`/`FilterCleared`) — not `JournalEditor` itself, since
  messages only bubble to ancestors and `FilterPopup` isn't a descendant.
- **`widgets/transaction_table.py`** — `JournalEditor`, the main widget.
  A raw-text `TextArea` (`LedgerTextArea`, `#journal_textarea`) **is** the
  live document — there's no separate in-memory model kept in sync; edits
  are just text edits. Deliberately thin: `BINDINGS`, message classes,
  init/mount, `Ctrl+S` save, cursor tracking. Everything else is a mixin:
  - `date_shift.py` `DateShiftMixin` — Shift+Up/Down date-field shifting
    (transaction headers and `P` price directives; expands an unpadded
    date like `2026-9-1` to `2026-09-01` on first shift).
  - `transaction_blocks.py` `TransactionBlocksMixin` — Ctrl+T
    (select/extend transaction block), Ctrl+G (duplicate to end), Ctrl+R
    (cleared-flag toggle, single or bulk).
  - `view_filter.py` `ViewFilterMixin` — Ctrl+L (fixed cleared/uncleared
    cycle) and Ctrl+O (arbitrary predicate, from the Transaction Filter
    popup) share one parse→hide→merge-edits-back→restore engine; the two
    are mutually exclusive.
  - `autocomplete.py` `AutocompleteMixin` — Tab account/payee completion,
    bash-style cycling (not an Up/Down dropdown — see its docstring for
    why: Up/Down are ordinary cursor keys used everywhere, including
    inside the search bar's `Input`, which is a `JournalEditor`
    descendant, so binding them globally risks colliding there).
- **`highlighting/highlighter.py`** — `LedgerHighlighter`: pure-Python,
  regex-based, no Textual imports, single O(N) scan per edit
  (`invalidate()`), O(1) per-line queries after. Injected into
  `LedgerTextArea` (`widgets/ledger_textarea.py`) by overriding
  `TextArea._build_highlight_map()` — **a private Textual 8.2.5 API**; if
  Textual is ever upgraded, that override needs re-checking against the
  new source first.
- **`utils/`** — `date_parser.py` (smart dates: ISO 8601, named periods,
  quarters, relative offsets like `-7d`/`+1m`), `query_match.py` (local
  reimplementation of `ledgerkit`'s substring-or-regex `Query` matching —
  duplicated because the real one is private/unexported, see that
  module's docstring), `journal_index.py` (account/payee name index for
  Tab autocomplete, rebuilt on load/save not per keystroke),
  `ledger_io.py` (`align_posting_amounts`, `split_journal_segments` —
  preserves directives/comments across the sort-and-reserialize that
  `Ctrl+S` does, since `ledgerkit.journal_to_text()` doesn't on its own),
  `commodity_format.py`, `atomic_edit.py`, `file_resolver.py`.
- **`widgets/search_bar.py`**, **`widgets/filter_popup.py`**,
  **`widgets/autocomplete_popup.py`** — three different overlay/bar
  patterns worth knowing apart: `SearchBar` and `AutocompletePopup` are
  docked-and-hidden (composed once, `display` toggled, never take focus —
  the cursor stays in the TextArea); `FilterPopup` is a floating overlay
  that's dynamically mounted/removed and does take focus, closer to a
  modal.
- **`keybindings/office.py`** / **`emacs_ledger.py`** — unused mixin
  *stubs* for alternate keybinding schemes (MS Office/Excel, Emacs
  ledger-mode); not wired into `JournalEditor` yet.

Two-layer undo: Layer 2 (`JournalEditor._command_history`, a
`CommandHistory`) is consulted first on `Ctrl+Z`/`Ctrl+Y`; falls through
to Layer 1 (`LedgerTextArea`'s native Textual `EditHistory`) when Layer 2
has nothing. `atomic_edit()` collapses a bulk operation's multiple
`replace()` calls into one Layer-1 undo entry.

`Ctrl+S` doesn't call `ledgerkit.load()`/`journal_to_text()` on a file
path — it re-parses the in-memory text (`parse_string_lenient`), sorts by
date, re-serializes each transaction (`transaction_to_text()`), weaves
`split_journal_segments()`'s preserved non-transaction blocks back in,
applies commodity formatting and column-52 amount alignment, then writes
directly via `Path.write_text()`.

## Rules that matter more than they look like they should

- **Never assume the `ledgerkit` API.** It's a private, fast-moving
  sibling package by the same author, pinned to a dev release. Before
  writing any code that calls it, check
  `knowledge_base/ledgerkit_api_notes.md` first, then the installed
  source directly if in doubt (`python -c "import inspect, ledgerkit;
  print(inspect.getfile(ledgerkit))"`). Key gotcha already hit once:
  `Transaction` has no `flag` field — it's two separate booleans,
  `cleared` and `pending`.
- **`CLAUDE.md`'s Folder Structure section, `dev-docs/api-spec.md`, and
  `pyproject.toml` are protected** — state exactly what would change and
  get explicit approval before touching any of them. (As of this file's
  last audit, both `CLAUDE.md`'s Folder Structure and `dev-docs/
  api-spec.md` are themselves known-stale — they still reference
  `balance_sidebar.py`/`register_panel.py`/`reconcile_*` widgets removed
  in v0.8.0 — flagged, not fixed, pending that approval.)
- **Every regex needs a Purpose/Group-breakdown/Edge-cases comment**
  directly above it (`CLAUDE.md`'s Regex Documentation Rule) — look at
  any regex in `highlighting/highlighter.py` or `widgets/date_shift.py`
  for the canonical style.
- **Module Size Rule**: flag a module past ~300–500 lines with a proposed
  split; don't move code without approval. This already happened once —
  `transaction_table.py` was 944 lines before the Phase 2 mixin split
  described above.
- **Doc sync is same-response, not deferred** — a signature change syncs
  `dev-docs/api-spec.md` (with approval, since it's protected); a
  keybinding change syncs `docs/shortcuts.md`; any substantive change
  gets a `CHANGELOG.md [Unreleased]` entry with **Human:**/**Claude:**
  lines. `ROADMAP.md` milestones are marked `[DONE]` only on the user's
  explicit instruction, never inferred.
- **Test runner**: `pytest --tb=short` (asyncio auto-mode). Widget/action
  tests use Textual's real pilot harness (`app.run_test()`,
  `pilot.press(...)`) dispatching actual key events through the real
  binding-resolution system — prefer that over calling `action_*` methods
  directly when the thing under test *is* key-binding/focus behavior
  (e.g. the Ctrl+C-in-search-bar fix depended on Textual's real
  priority/non-priority binding walk, which a direct method call would
  have skipped entirely).

## Where to go for depth

- `CLAUDE.md` — the full process-rules contract (this file is the "what,"
  that one is the "how to behave").
- `dev-docs/architecture.md` — module tree, layout, data flow,
  ledgerkit integration points, design decisions, kept in sync by
  `.claude/skills/document-package/SKILL.md`.
- `docs/shortcuts.md` — full keybinding reference, user-facing.
- `knowledge_base/keybindings.md` — the *why* behind every binding,
  `priority=True` collision resolutions, terminal-compatibility notes
  (including two corrected assumptions about Ctrl+C/Ctrl+Z safety).
- `knowledge_base/design_decisions.md`, `knowledge_base/
  textual_patterns.md` — non-obvious judgment calls and reusable Textual
  gotchas discovered along the way.
- `planning/next-release-phase-plan.md` — the most recent multi-phase
  plan (bug fixes → module split → Transaction Filter → Tab autocomplete
  → these two skills), useful as a worked example of this repo's own
  planning style.
- `CONTRIBUTING.md` — dev environment setup, ledgerkit update procedure.
- `.claude/skills/polish-codebase/SKILL.md`,
  `.claude/skills/document-package/SKILL.md` — the two repeatable-process
  skills this repo defines for itself.
