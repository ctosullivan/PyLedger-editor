# Next Release — Phased Implementation Plan

**Created:** 2026-09-05
**Author:** Claude (Opus 5), from a request in `planning/prompts/2026-09-05-next-release-phase-plan-request.md`
**Status:** All 5 open decisions accepted (recommended options), 2026-09-05 — see "Open decisions" at the end. No code has been changed as part of producing this plan; implementation starts once a release branch is created (see "Branching").
**Current shipped version:** 1.0.1 (see `CHANGELOG.md`)

This plan was written after reading the actual installed Textual 8.2.5 and
ledgerkit 1.0.0.dev1 source (per `CLAUDE.md`'s "never assume the API" rule),
not just this repo's own notes — root causes below are traced to specific
lines in those packages, not guessed.

---

## Documentation drift found during investigation

Not part of the requested scope, but discovered while tracing the bugs below
and worth the user's attention before or alongside this work, since later
phases (5 and 6) will otherwise be auditing docs that are already known-stale:

- `dev-docs/architecture.md` and the "Folder Structure" section of `CLAUDE.md`
  both still describe `balance_sidebar.py`, `register_panel.py`, and the
  `reconcile_*` widgets. `ROADMAP.md` records these as **removed in v0.8.0**.
  Neither doc mentions `view_filter_bar.py`, which exists and is live.
- `ROADMAP.md`'s "What Is Shipped" section is pinned at v0.8.2 and its
  Milestone C still lists `Shift+Up/Down` date editing as undone — but
  `CHANGELOG.md`'s v1.0.0 entry says it shipped. Milestones A and B in
  `ROADMAP.md` already describe two of the features requested below
  (Filter transactions, Tab autocomplete) — this plan treats those sections
  as the pre-existing design intent and builds on them rather than starting
  from scratch.

These are flagged, not fixed, here — fixing them is exactly the kind of task
Phase 6 below builds a repeatable process for. Phase 6's first run should
use this list as its pilot case.

---

## Phase overview

| Phase | Scope | Suggested version | Depends on |
|---|---|---|---|
| 1 | 4 bug fixes (date shift, search-bar copy, scroll padding) | `1.0.2` (patch) | — |
| 2 | Housekeeping gate: `transaction_table.py` size flag (decision only) | — (no code without approval) | Phase 1 |
| 3 | Feature: Transaction Filter (Ctrl+O) — smart dates + regex | `1.1.0` (minor) | Phase 2 decision |
| 4 | Feature: Tab autocompletion | `1.2.0` (minor) | Phase 2 decision, informed by Phase 3 |
| 5 | Tooling: repeatable "polish & simplify" skill + process | no version bump | — (can run anytime) |
| 6 | Tooling: repeatable "documentation" skill + AI-README | no version bump | — (can run anytime) |

Phases 1–4 change `pyproject.toml`'s version and are user-facing releases;
Phases 5–6 add developer tooling (`.claude/skills/…`, new docs) and don't by
themselves require a version bump. Per `CLAUDE.md`'s Unauthorised Change
Rule, **any actual edit to `pyproject.toml`, `dev-docs/api-spec.md`, or the
canonical folder structure will be called out explicitly and held for your
confirmation before it happens** — nothing here is pre-approved by writing
it into a plan.

---

## Branching

Before any implementation work starts, create a dedicated release branch off
`master` (currently clean, at `b768a6f`) rather than committing this work
directly to `master`:

- Branch name: `release/1.1.0` — the `1.0.2` / `1.1.0` / `1.2.0` version
  sequence is confirmed (open decision 5, accepted).
  Phase 1's bug fixes are small enough to land as commits on this same
  branch rather than a separate branch each, unless you'd prefer `1.0.2`
  to ship independently and sooner than the feature work — in that case,
  branch `fix/1.0.2-bug-batch` from `master` first, merge/tag it, then cut
  `release/1.1.0` from the updated `master`.
  All commits and eventual PR(s) will follow the existing commit-message
  and PR conventions already in place in this repo.
- Phase 2's module split, and Phases 3/4's feature work, all happen as
  commits on that branch — each phase can be its own PR into the release
  branch, or the whole branch can be reviewed as one PR into `master`,
  whichever you prefer once work starts.
- Phases 5 and 6 (skills + docs tooling) don't touch the package version
  and aren't tied to a release cut — they can land on `master` directly (or
  their own short-lived branches) independent of this release branch's
  timeline.
- No branch has been created yet — this is scoped for the point where you
  say to start implementation, consistent with holding off on any actual
  repo changes until this plan is approved.

---

## Phase 1 — Bug fixes (target `1.0.2`)

All four root causes below were confirmed by reading the installed package
source (Textual 8.2.5, this repo), not inferred from symptoms alone.

### 1.1 — Shift+Up/Down doesn't work on `P` price-directive dates

**Root cause:** `JournalEditor._shift_date_by()`
(`src/ledgerkit_editor/widgets/transaction_table.py:830`) only proceeds when
`line_infos[row].kind == LineKind.XACT_HEADER`. A `P` directive line
(`P 2026-09-01 EUR 1.08 USD`) is classified as generic `LineKind.DIRECTIVE`
by `_DIRECTIVE_RE` in `highlighting/highlighter.py:64`, which treats `P`
identically to `D`, `Y`, `account`, `commodity`, etc. — there is currently no
way to distinguish "a directive whose argument happens to start with a date"
from any other directive. Even if there were, `_shift_date_by` assumes the
date starts at column 0 (`_TXN_HEADER_RE` / `_shift_date_str` in
`transaction_table.py:38,153`), which is true for a transaction header but
not for `P DATE …` (the date starts after `"P "`).

**Fix approach:**
1. Add a dedicated, documented regex for price directives (per the Regex
   Documentation Rule) — something like
   `_PRICE_DIRECTIVE_RE = re.compile(r"^P\s+(\d{4}[-/]\d{1,2}[-/]\d{1,2})\b")`
   (digit counts widened to `{1,2}` here in the same pass as fix 1.2, since
   the two bugs share the same date grammar).
2. Extend `_shift_date_by`'s branch condition: when the line is a
   `LineKind.DIRECTIVE` and matches `_PRICE_DIRECTIVE_RE`, compute the
   sub-field and date span from the regex match's group span (not from
   column 0), then delegate to the same `_shift_date_str` used for
   transaction headers.
3. Factor the "identify date span → compute sub-field from cursor col →
   shift → replace" sequence into one small helper shared by both branches,
   so the XACT_HEADER and P-directive paths don't duplicate the
   `_date_subfield_at_col` / `replace()` call sites.

**Files touched:** `widgets/transaction_table.py`, `highlighting/highlighter.py`.
**Tests:** extend `tests/test_date_shift.py` with `P` directive fixtures —
cursor in year/month/day sub-fields, verifying only the date substring
changes and the commodity/rate portion of the line is untouched.
**Docs to sync (same response as the fix, per `dev-docs/SYNC.md`):**
`docs/shortcuts.md` (date-shift row should mention it also applies to `P`
directives), `CHANGELOG.md` `[Unreleased]` entry with Human/Claude lines.

### 1.2 — Dates without a leading zero (e.g. `2026-9-1`) aren't recognized

**Root cause:** Three separate regexes all hard-require 2-digit month/day:
`_XACT_HEADER_RE` (`highlighting/highlighter.py:43`), `_TXN_HEADER_RE`
(`transaction_table.py:38`), and `_DATE_PARSE_RE`
(`transaction_table.py:150`). A line typed as `2026-9-1 Payee` fails all
three: it isn't classified as `XACT_HEADER` at all (falls through to
`UNKNOWN`), gets no date highlighting, and `_shift_date_by` immediately
falls through to plain text selection instead of shifting — matching the
reported symptom exactly.

This is a genuinely deeper fix than the one-line regex change it looks
like: the column arithmetic in `_date_subfield_at_col`
(`transaction_table.py:125`) hard-codes a fixed 10-character `YYYY-MM-DD`
layout (cols 0–3 year, 4 separator→month, 5–6 month, 7 separator→day, 8–9
day). A variable-width date like `2026-9-1` (9 chars) or `2026-09-1` (10
chars, differently laid out) breaks that arithmetic if handled naively.

**Fix approach — "normalize on first shift" (recommended over a fully
variable-width rewrite):**
1. Widen all three regexes' month/day groups from `\d{2}` to `\d{1,2}`,
   including the new `_PRICE_DIRECTIVE_RE` from 1.1 (both bugs share the
   grammar, so land them together). This alone fixes recognition/
   highlighting — every other call site that uses `_TXN_HEADER_RE.group(1)`
   as an opaque token (`_cycle_flag_in_header`, `action_autofill`, bulk
   cleared-toggle) is unaffected since they never split the date string.
2. In `_shift_date_by`, before computing `subfield =
   _date_subfield_at_col(col)`: if the matched date string isn't already
   canonical 10-char zero-padded form, normalize it first — write the
   zero-padded date back via `textarea.replace()`, remap the cursor column
   proportionally (cursor stays in the same logical sub-field it was in
   before padding), *then* run the existing fixed-width shift logic
   unchanged. `_shift_date_str` already formats output with `:02d`, so no
   change is needed there once its input regex accepts 1–2 digits.
3. Add two small, pure, testable helpers: `_normalize_date_str(s) -> str`
   and `_remap_col_after_normalize(old, new, col) -> int`.

This means the very first Shift+Up/Down on an unpadded date both expands it
to `2026-09-01` *and* shifts it — exactly as requested — without touching
the fixed-width assumptions everywhere else in the file.

**Files touched:** `widgets/transaction_table.py`, `highlighting/highlighter.py`.
**Tests:** `tests/test_date_shift.py` (all digit-count combinations: `9-1`,
`09-1`, `9-01`; `/` separator variant; cursor in each sub-field pre-
expansion) and `tests/test_highlighting.py` (unpadded dates must now be
classified `XACT_HEADER`, not `UNKNOWN`).
**Docs to sync:** `CHANGELOG.md`; recommend also adding a short note to
`knowledge_base/design_decisions.md` documenting the "expand-on-shift"
choice, since it's a case where the editor mutates more text than the user
directly typed — worth recording the rationale for future readers, matching
that file's existing style.

### 1.3 — Ctrl+C is swallowed as "quit" while the search bar has focus

**Root cause (traced in installed Textual 8.2.5 source):**
`Input.action_copy()` (`textual/widgets/_input.py`) raises `SkipAction()`
when `Input.selected_text` is empty. The search box holds the *query* text
the user typed — the actual match is only highlighted inside the
`LedgerTextArea` document (`SearchBar._compute_matches` /
`set_search_matches`), never selected inside the `Input` itself. So with
nothing selected in the `Input`, `action_copy` skips, and Textual's
non-priority key-binding walk continues up the focus chain to `App`'s
built-in `Binding("ctrl+c", "help_quit", ..., system=True)`
(`textual/app.py`) — which in this Textual version doesn't actually quit
(that's `ctrl+q`), it just pops a "Press ctrl+q to quit" notification. That
notification, plus the failed copy, is what reads as "Ctrl+C intercepted as
quit."

**Fix approach:**
1. Add a `ctrl+c` binding on `SearchBar` (`priority=True`, so it's
   captured before any bubbling) that: if the focused `Input` has a real
   text selection, do nothing and let `Input.action_copy` handle it
   normally; otherwise, if there's a current match (`self._current != -1`),
   copy that match's text — read the span out of the `LedgerTextArea`
   document via `self._matches[self._current]` — to the clipboard with
   `self.app.copy_to_clipboard(...)`.
2. This also incidentally suppresses the unwanted "press ctrl+q" nag while
   the search bar is open, since the key never reaches `App` at all.

**Files touched:** `widgets/search_bar.py`.
**New test file:** `tests/test_search_bar.py` doesn't currently exist —
`SearchBar` has zero direct test coverage today. Per the Testing Rules this
needs to be created (`test_<module>.py` convention), covering: copy with an
active match and no Input selection; copy with an actual Input text
selection (must not be overridden); copy with zero matches (no-op, no
crash).
**Docs to sync:** `docs/shortcuts.md` search section (note Ctrl+C copies
the current match); `CHANGELOG.md`.

### 1.4 — Shift+PgUp / previous search match scrolls with no top padding

**Root cause (traced in installed Textual 8.2.5 source):**
`LedgerTextArea.scroll_cursor_visible()`
(`widgets/ledger_textarea.py:110`) overrides the base `TextArea` method to
add `spacing=Spacing(right=self.gutter_width, bottom=4)` — a **bottom-only**
4-line margin. Every cursor-moving action (`action_prev_transaction`,
`action_next_transaction`, `SearchBar._advance`/`_advance_transaction`)
already benefits from this override automatically, because Textual's
`TextArea._watch_selection()` calls `self.scroll_cursor_visible()` on every
`move_cursor()` (this dispatches polymorphically to the subclass override
even though the call originates in the base class). But since `Spacing` has
no `top=` value here, moving **up** scrolls until the cursor sits flush
against row 0 of the viewport with zero reserved context — exactly the
asymmetry reported.

**Fix approach:**
1. Add a symmetric top margin: `Spacing(right=self.gutter_width, top=4,
   bottom=4)`.
2. Default to the same value (4) for both edges as the simplest reading of
   "similar padding" — flag as easy to tune if 4 feels wrong once tried
   interactively, but don't over-engineer a separate top/bottom constant
   without a reason to.

**Files touched:** `widgets/ledger_textarea.py`.
**Tests:** no existing test currently exercises `scroll_cursor_visible`
directly (checked `tests/test_transaction_table.py` — no hits). Add a test
asserting the `Spacing` passed to `scroll_to_region` includes a non-zero
`top` equal to `bottom`, plus a behavioral test moving the cursor up
through several transaction headers and checking the viewport's top
scroll offset reserves the same margin the existing downward case gets.
**Docs to sync:** `CHANGELOG.md`; consider a one-line addition to
`knowledge_base/textual_patterns.md` documenting the symmetric-margin
scroll pattern, since that file exists specifically to record this kind of
non-obvious Textual behavior for future reactive-attribute/rendering work.

### Phase 1 wrap-up

- Run `pytest --tb=short` (full suite) before and after.
- One `CHANGELOG.md [Unreleased]` entry per bug (Human/Claude lines each),
  or one combined "Fixed" entry listing all four — your call on granularity.
- Version bump to `1.0.2` in `pyproject.toml` is a protected change under
  the Unauthorised Change Rule — will be called out and held for explicit
  confirmation at that point, not bundled silently into the bug-fix commits.

---

## Phase 2 — Housekeeping gate: module size (decision only, no code yet)

Per the Module Size Rule, this is a **flag + proposal**, not an action.

`src/ledgerkit_editor/widgets/transaction_table.py` is currently **849
lines** — already ~1.7× over the 500-line ceiling — and both Phase 3
(Filter) and Phase 4 (Autocomplete) below add non-trivial new logic to
exactly this file (Filter reuses/generalizes its existing view-filter
engine; Autocomplete adds new key-handling and a new popup). Landing both
features on top of an already-oversized file makes the eventual split
strictly harder and the module harder to review in the meantime.

**Proposed split** (for your approval before any code moves):

| New file | Moves from `transaction_table.py` |
|---|---|
| `widgets/date_shift.py` | `_shift_date_str`, `_date_subfield_at_col`, `_DATE_PARSE_RE`, `_PRICE_DIRECTIVE_RE` (from Phase 1), `action_date_shift_up/down`, `_shift_date_by` |
| `widgets/view_filter.py` | `_apply_view_filter`, `_merge_filtered_edits`, `action_cycle_view_filter`, the `_filter_journal` / `_filter_visible_indices` / `_filter_non_txn_blocks` state — generalized in Phase 3 to accept an arbitrary predicate instead of the hardcoded cleared/uncleared check |
| `widgets/transaction_blocks.py` | `_find_transaction_block`, block selection/duplication/bulk-toggle (`Ctrl+T`, `Ctrl+G`, bulk `Ctrl+R`) |
| `transaction_table.py` (remains) | `JournalEditor` class skeleton, `compose()`, `BINDINGS`, message classes, save/load orchestration, thin delegation to the above modules |

This is scoped to land at the **start** of Phase 3's work, not as a
separate release — it's pure internal reorganization with no behavior
change, verified by the existing test suite passing unchanged (tests may
need their imports updated to the new module paths, per `tests/test_
transaction_table.py`, `tests/test_date_shift.py`, `tests/test_view_
filter.py`).

**Decision (accepted):** approved as proposed. This split happens at the
start of Phase 3's work, exactly as described above.

---

## Phase 3 — Feature: Transaction Filter, smart dates + regex (target `1.1.0`)

This isn't a greenfield feature — `ROADMAP.md` Milestone A and
`widgets/filter_popup.py`'s own docstring already describe the intended
shape (assemble a `ledgerkit.Query`, apply it, `Ctrl+O` toggles the popup).
The UI (`FilterPopup`) already exists as a stub; `apply_filter()` is the
unimplemented piece, plus wiring it into `JournalEditor`.

### Key finding: the hard parts already exist, in two different places

1. **Regex support is free**, if we match `ledgerkit`'s own convention
   rather than inventing a new one. Read `ledgerkit/reports.py`
   (`_matches_pattern`, `_REGEX_META`, `_posting_matches`): `Query.account`
   and `Query.payee` already follow hledger's rule — a pattern containing
   any regex metacharacter is compiled and matched with `re.search`
   (case-insensitive); anything else is a plain substring match. This is
   exactly "Python regex" support, and it's the same behavior `ledgerkit`
   uses for `balance()`/`register()`, so filter results stay consistent
   with anything else built on `ledgerkit.Query` later.
   - **Caveat:** `_matches_pattern` and `_posting_matches` are private
     (`_`-prefixed, not exported from `ledgerkit.__init__`). Per this
     project's own ledgerkit API Rule, importing private members of a
     pinned dependency is fragile.
     **Decision (accepted):** duplicate the ~10-line matching logic
     locally in `ledgerkit_editor/utils/query_match.py`, with a full regex
     documentation comment per `CLAUDE.md`'s Regex Documentation Rule
     (mirroring `_matches_pattern`'s semantics deliberately, noted in a
     comment so the two don't silently drift). No dependency on an
     upstream `ledgerkit` change for this release — filing a public
     `matches_query(transaction, query) -> bool` export as a follow-up
     suggestion for `ledgerkit` itself remains a good idea, just not a
     blocker here.
2. **The show/merge/restore engine already exists** — it's the `Ctrl+L`
   view-filter machinery (`_apply_view_filter`, `_merge_filtered_edits`,
   `_filter_journal`, `_filter_visible_indices`, `_filter_non_txn_blocks`
   in `transaction_table.py:543-642`). It already handles: parsing the full
   journal, hiding non-matching transactions from the `TextArea` while
   preserving directives/comments/blank-line structure via
   `_filter_non_txn_blocks`, merging user edits made in the filtered view
   back into the full model, and restoring the complete journal on exit —
   including edge cases like transactions added/removed while filtered.
   Today it's hardcoded to a 3-state cleared/uncleared cycle. **Generalize
   it to accept an arbitrary `Callable[[Transaction], bool]` predicate**
   instead, so `Ctrl+L` becomes "predicate = cleared-state check" and the
   new `Ctrl+O` criteria filter becomes "predicate = built from
   `FilterPopup`'s fields", sharing one engine instead of building a
   second, parallel one. This is the concrete payoff of the Phase 2 split
   (`widgets/view_filter.py`).

### Smart dates — mostly built, one gap

`utils/date_parser.py` already implements `today`/`yesterday`/`ytd`/
`last month`/`last year`/`q1`-`q4`/ISO-8601, with a documented `TODO:
implement relative offset parsing ("-7d", "+1m", "+1w")` at line 90 — the
filter feature is precisely the consumer that needs this, so implement it
now rather than leaving the stub. Suggested grammar (document per the
Regex Documentation Rule when implemented): `^([+-])(\d+)([dwmy])$`,
applied via `timedelta` for `d`/`w` and month/year-aware arithmetic
(reusing the same month-end-clamping approach as `_shift_date_str` in
Phase 1.1/1.2, for consistency) for `m`/`y`.

### Design/wiring plan

1. `FilterPopup.apply_filter()`: read `date_from`/`date_to` via
   `date_parser.parse_date_range()`, `account`/`payee` as raw strings
   (regex-or-substring, per above), build a `ledgerkit.Query`, and post a
   message (e.g. `FilterPopup.FilterApplied(query)`) to `JournalEditor`
   rather than calling into it directly — keeps the popup decoupled, matching
   the existing message-passing pattern used elsewhere (`SaveCompleted`,
   `FileModifiedChanged`).
2. `JournalEditor` handles `FilterApplied` by entering the generalized
   filter-engine (from Phase 2's `view_filter.py`) with a predicate built
   from the query (date range checked against `Transaction.date`; account
   checked against every `Posting.account` in the transaction; payee
   checked against `Transaction.description`).
3. Invalid regex in the account/payee fields (`re.error`) must be caught
   and surfaced as a notification, not crash the popup — `FilterPopup`
   currently has no error path for this at all.
4. Clearing the filter (`Ctrl+O` again, or an explicit "Clear" affordance
   in the popup) restores the full journal via the same restore path
   `Ctrl+L` mode 0 already uses.
5. Interaction with `Ctrl+L`: they share the same underlying engine but
   are two independent triggers. **Decision (accepted 2026-09-05,
   reversed 2026-09-09 per UAT feedback):** implemented as **replace**
   (one active filter at a time) — opening the criteria filter exits any
   active `Ctrl+L` cleared-filter first, and vice versa. UAT on
   `release/1.1.0` found this mentally awkward in practice; the desired
   behaviour going forward is **combine (AND)** instead — e.g. `Ctrl+L`
   "Cleared only" narrowed further by a `Ctrl+O` account/date/payee filter,
   rather than the second one discarding the first. **Not yet
   implemented** — this note records the direction for a follow-up
   change, not a completed one. When it's picked up:
   - `ViewFilterMixin` needs a second independent predicate slot (or a
     single combined predicate assembled from both the fixed
     cleared/uncleared check and any `_active_predicate`), since
     `_apply_view_filter`'s mode!=0 branch currently treats
     `_active_predicate is not None` as fully overriding the
     cleared/uncleared check rather than composing with it.
   - `ViewFilterBar`'s label needs to describe a combined state (e.g.
     "View: Cleared only + Filtered (Ctrl+O)"), not just whichever one is
     "active".
   - Decide what happens to an existing `Ctrl+O` filter when `Ctrl+L` is
     pressed again to cycle back to All — does it fall back to "just the
     Ctrl+O filter" or clear entirely? (Symmetric question for clearing
     the Ctrl+O side while a Ctrl+L mode is active.)
   - Update `tests/test_filter_popup.py::TestFilterMutualExclusivity`
     (currently asserts replace semantics) to assert combine semantics
     instead, and add coverage for the partial-clear questions above.

**Files touched:** `widgets/filter_popup.py`, `widgets/view_filter.py`
(post-split), `utils/date_parser.py`, new `utils/query_match.py`.
**Tests:** `tests/test_date_parser.py` (relative offsets), new
`tests/test_filter_popup.py`, `tests/test_view_filter.py` extended for the
generalized-predicate engine, fixtures with regex-metacharacter account/
payee names in `tests/fixtures/`.
**Docs to sync:** `docs/shortcuts.md` (Ctrl+O row currently says filtering
isn't implemented), `dev-docs/architecture.md` (new data flow: FilterPopup
→ Query → predicate → view-filter engine), `ROADMAP.md` Milestone A → only
mark `[DONE]` on your explicit instruction, `CHANGELOG.md`.

---

## Phase 4 — Feature: Tab autocompletion (target `1.2.0`)

Corresponds to `ROADMAP.md` Milestone B ("Tab autocomplete from declared
accounts + all posting accounts", "transaction template" insertion).

### Decision (accepted): what Tab means going forward

`docs/shortcuts.md` currently documents `Tab` as "cycle focus: Text editor →
Text editor (**only one panel now**)" — i.e., since the `BalanceSidebar`/
`RegisterPanel` removal in v0.8.0, Tab-for-focus-cycling is effectively a
no-op when the editor has focus (it only does something when the search
bar's `Input` is also present in the focus chain). This meaningfully lowered
the risk of reclaiming `Tab` for autocomplete, and reclaiming it is now
confirmed:

- `Tab` triggers/advances autocomplete suggestions when a suggestion
  popup is open or a completable token is under the cursor; otherwise it
  falls through to Textual's default `Tab` behavior unchanged (whatever
  that resolves to today, including inside the search bar's `Input`).

### Decision (accepted): scope for `1.2.0`

Two distinct, separately-scoped capabilities are readable from "suggesting
account names, transaction classification etc." — confirmed scope: 4a is
in for `1.2.0`, 4b is deferred.

- **(a) Name completion — in scope for `1.2.0`.** Tab on a partial token
  completes it against a known-names index: declared `account` directives
  + every distinct posting account seen in the journal (for posting
  lines), and every distinct `Transaction.description` (for the payee
  position on a header line). This is the `1.2.0` baseline.
- **(b) Historical classification — deferred to Phase 4b.** After a payee
  is typed/selected, suggest the account(s) most frequently (or most
  recently) used in past transactions with that same payee, i.e. "last
  time I bought from this payee, it was posted to `expenses:groceries`" —
  the same idea behind `ROADMAP.md` Milestone B's `Alt+P`/`Alt+N` "insert
  previous/next matching transaction template". Sequenced after 4a lands
  and is stable, since it needs its own ranking/recency logic and UI
  (accept a suggested *account*, or accept a whole suggested *posting
  line/template*) — kept out of `1.2.0` to avoid scope creep on a feature
  that's already non-trivial.

### Implementation plan (Phase 4a — name completion)

1. **Index build**: scan the full journal (via
   `ledgerkit.parse_string_lenient`, already used elsewhere in this file)
   into an accounts set (declared + used) and a payees set (all
   `description` values). Rebuild on file load and after `Ctrl+S`, **not**
   on every keystroke — `ROADMAP.md` Milestone D already calls out 10k+
   transaction performance as a concern, so this must be a cached,
   explicitly-invalidated index, not a per-char rescan.
2. **Trigger detection**: on `Tab`, use `line_infos` (already computed by
   `LedgerHighlighter`) to determine line kind and cursor position:
   `POSTING` line → complete against the accounts index, scoped to the
   token left of the cursor up to the line's leading whitespace/last `:` ;
   `XACT_HEADER` line, cursor past the date/flag/code → complete against
   the payees index.
3. **New widget**: `widgets/autocomplete_popup.py` — an overlay list
   (same `layer: overlay` pattern as `FilterPopup`), keyboard-navigable
   (`Up`/`Down` to move selection, `Tab`/`Enter` to accept, `Escape` to
   dismiss), positioned near the cursor.
4. Accepting a suggestion replaces the partial token via `textarea.replace()`
   (single undoable edit, consistent with every other mutation in this
   file).

**New files:** `widgets/autocomplete_popup.py`, `utils/journal_index.py`
(the account/payee index builder — pure, testable independent of Textual).
**Files touched:** `widgets/transaction_table.py` (Tab key handling —
another point in favor of the Phase 2 split landing first).
**Tests:** `tests/test_journal_index.py` (pure index-building logic), new
`tests/test_autocomplete_popup.py`, fixtures with repeated/overlapping
account and payee names in `tests/fixtures/`.
**Docs to sync:** `docs/shortcuts.md` (Tab semantics rewritten),
`dev-docs/architecture.md` (new widget + index data flow), `ROADMAP.md`
Milestone B progress (mark `[DONE]` only on explicit instruction),
`CHANGELOG.md`.

---

## Phase 5 — Repeatable process + skill: polish & simplify (no version bump)

Goal: a periodic, opt-in, non-functional-change pass — distinct from the
"only refactor when asked" default behavior this assistant otherwise
follows; this skill *is* the sanctioned, explicit ask for that work,
invoked deliberately rather than folded into unrelated feature commits.

**Process (what the skill actually does each run):**
1. Baseline gate: run `pytest --tb=short` — full pass required before
   touching anything. If the suite isn't green at the start, stop and
   report rather than "fixing" pre-existing failures as a side effect.
2. Delegate the mechanical review to the two general-purpose skills already
   available in this environment rather than reinventing them:
   `/code-review` (quality-focused pass — reuse/simplification/efficiency)
   and `/simplify` (applies the fixes it finds). These already know how to
   find dead code, duplication, and inefficiency; this project skill's job
   is to add the project-specific layer on top, not replace them.
3. Project-specific checklist layered on top (this is the part generic
   skills can't know): every regex still has its Purpose/Group
   breakdown/Edge cases comment (Regex Documentation Rule); no module has
   quietly grown past the 300–500 line guidance without being flagged
   (Module Size Rule); no comment explains *what* code does rather than
   *why*; docstrings are one-line-minimum, not multi-paragraph; a
   `CHANGELOG.md [Unreleased]` entry exists for anything substantive found
   and fixed, with Human/Claude lines (Human line: "periodic polish pass").
4. Explicit non-negotiable: **behavior must not change**. Re-run the full
   suite after changes; if the diff includes anything beyond structure/
   naming/dead-code/duplication removal, it's out of scope for this skill
   and should be raised as a separate, ordinary change instead.
5. Output a short before/after report for review — this skill proposes,
   it doesn't auto-commit silently; consistent with how `/code-review` and
   `/simplify` already work in this environment.

**Deliverable:** `.claude/skills/polish-codebase/SKILL.md` (this directory
doesn't exist in the repo yet). Suggest also adding one paragraph to
`CONTRIBUTING.md` pointing at it, so it's discoverable alongside the
existing dev-setup/dependency-update instructions there.

**Suggested cadence:** run once per minor release (i.e., after Phase 3,
after Phase 4, etc.) rather than on a fixed calendar schedule — codebases
this size don't accumulate enough cruft week-to-week to justify a
`/loop`-style timer; tying it to release boundaries keeps it meaningful.

---

## Phase 6 — Repeatable process + skill: documentation (no version bump)

**Process:**
1. Audit pass: compare every doc under `docs/`, `dev-docs/`,
   `knowledge_base/`, `README.md`, `ROADMAP.md`, `CHANGELOG.md`, and
   `CLAUDE.md`'s own Folder Structure section against the actual `src/`
   tree, `BINDINGS` declarations, and shipped `CHANGELOG.md` history —
   catching exactly the kind of drift found in this session (see
   "Documentation drift found during investigation" above; use that list
   as the pilot run's starting checklist).
2. Maintain **human-facing docs**: `README.md` (install/usage/screenshots),
   `docs/shortcuts.md` (keybinding reference — this is the doc most likely
   to drift, since every feature phase above touches it), `dev-docs/
   architecture.md` (module responsibilities/data-flow — regenerate the
   module-tree listing from the real `src/` layout rather than hand-editing
   prose, where feasible, to make drift structurally harder).
3. Produce and maintain an **`AI-README.md`** at the repo root: a dense,
   marketing-free, agent-efficient primer — what the project is, its
   architecture in load-bearing terms (module responsibilities, the
   two-layer undo stack, the private-Textual-API dependency and why it's
   pinned, the "never assume the ledgerkit API" rule and where to check),
   how to run tests/dev loop, and pointers into the canonical docs for
   depth. Written to be pasted cold into a fresh AI session's first
   message and immediately useful — this is close in spirit to this
   project's own `CLAUDE.md`, but framed as a *portable prompt* rather than
   a set of process rules, and short enough to actually paste.
4. This backstops — doesn't replace — the existing same-response sync
   rule in `dev-docs/SYNC.md`; individual PRs will still keep occasionally
   missing a doc update, and this periodic audit catches what slips
   through.

**Deliverable:** `.claude/skills/document-package/SKILL.md`
(`.claude/skills/` doesn't exist yet — both this and Phase 5's skill would
be its first two entries), plus the new `AI-README.md`.

**Suggested cadence:** same as Phase 5 — after each release, using the
release's own `CHANGELOG.md [Unreleased]` entries as the input list of
"things that might have drifted a doc."

---

## Open decisions — resolved 2026-09-05

All five accepted the recommended option, no changes requested:

1. **Phase 2 split** — **accepted.** The proposed `transaction_table.py`
   breakup (into `date_shift.py`, `view_filter.py`,
   `transaction_blocks.py`) happens at the start of Phase 3, as described.
2. **Phase 3** — **accepted.** Duplicate `ledgerkit`'s private matching
   logic locally (`utils/query_match.py`) rather than waiting on an
   upstream `ledgerkit` export.
3. **Phase 3** — **accepted, then reversed 2026-09-09 per UAT feedback.**
   Implemented as: `Ctrl+O` criteria filter replaces any active `Ctrl+L`
   filter rather than combining (AND) with it. UAT found this awkward;
   desired direction going forward is **combine (AND)** instead — see the
   "Interaction with `Ctrl+L`" note in Phase 3 above for what that
   requires. Not yet implemented as of this note.
4. **Phase 4** — **accepted.** Reclaiming `Tab` for autocomplete is
   confirmed. Scope is 4a (name completion) for `1.2.0`; 4b
   (historical-account/template suggestion) is deferred.
5. **Versioning** — **accepted.** `1.0.2` / `1.1.0` / `1.2.0` sequence
   confirmed; `release/1.1.0` is the branch name in the Branching section
   above.

Nothing above blocked starting Phase 1 (bug fixes) even before this
resolution — it had no open design questions. With all five now settled,
the plan is unblocked end-to-end pending only the branch-creation step
described in "Branching."
