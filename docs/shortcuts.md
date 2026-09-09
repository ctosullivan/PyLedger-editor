# Keyboard Shortcut Reference

## File Operations

| Shortcut | Action |
|----------|--------|
| `Ctrl+S` | Save: merge any active filter view, sort transactions by date, re-align posting amounts to column 52 (emacs ledger-mode style), then write (validation errors shown as warnings, do not block save) |
| `Ctrl+O` | Open / close the transaction filter popup — see [Transaction Filter (Ctrl+O)](#transaction-filter-ctrlo) below |

## Search

| Shortcut | Action |
|----------|--------|
| `Ctrl+F` | Open search bar (if closed), or jump to **next** match (if bar already open) |
| `Shift+PgDown` | Jump to **next** match (when search bar is open); otherwise jump to next transaction header |
| `Shift+PgUp` | Jump to **previous** match (when search bar is open); otherwise jump to previous transaction header |
| `Ctrl+C` | While the search input has focus: copies the currently highlighted match's text to the clipboard. If you've selected text inside the search box itself instead, that selection is copied as normal. |
| `Escape` | Dismiss the Tab-autocomplete suggestion bar if showing; else close the search bar; else unfocus the editor — checked in that order. |

Search requires at least 2 characters. Matches are highlighted in the editor: dim background for all matches, bright background for the current match. The counter shows "N of M" (or "No matches"). Jumping to a match keeps at least 4 lines of context visible above and below the cursor, matching transaction navigation (`Shift+PgUp`/`Shift+PgDown`).

## View Filter (Ctrl+L)

| Shortcut | Action |
|----------|--------|
| `Ctrl+L` | Cycle view filter: **All transactions** → **Cleared only** → **Unreconciled only** → All |

The view filter changes what the editor shows without hiding any data from disk:

- **All transactions** (default): full journal visible; normal read-write editing.
- **Cleared only**: shows only transactions marked `*`. Editing is allowed; changes are merged back into the full journal when the filter changes or when you save.
- **Unreconciled only**: shows only transactions with no `*` flag. Same edit-and-merge behaviour.

`Ctrl+S` while in a filtered view merges edits back and saves the **complete** journal (all transactions, not just the visible ones), then returns the editor to All mode.

## Transaction Filter (Ctrl+O)

| Shortcut | Action |
|----------|--------|
| `Ctrl+O` | Open / close the filter popup. Closing it (a second `Ctrl+O`, or `Escape`) leaves any already-applied filter active — it only dismisses the popup, not the filter. |
| `Enter` (in any field) | Apply the filter — same as clicking **Apply** |
| `Tab` (in the Account or Payee field) | Complete the field's value against known account/payee names — press again to cycle to the next match. See [Tab Autocomplete](#tab-autocomplete) below; this is the same convention, just applied to a whole field's value instead of a partial token within a line. `Tab` in the Date fields is unaffected (ordinary focus-cycling). |

The popup has four fields, all optional — leave any blank to not filter on that dimension:

- **Date from / Date to** — smart dates:
  - ISO 8601 (`2024-01-15`)
  - Year-month shorthand — a whole calendar month: `2026-02` (or `2026-2`, unpadded)
  - Named periods: `today`, `yesterday`, `this week`, `last week`, `this month`, `last month`, `this year`, `last year`, `ytd`
  - Quarters: `q1`–`q4` (current year)
  - A month name, with or without a year: `september`, `sep 2026`, `September 2026` — a bare month name defaults to the current year
  - A relative offset: `-7d`, `+2w`, `-1m`, `+1y`

  A named period, month name, or `2026-02`-style shorthand typed into **just one** of the two fields (the other left blank) is bounded to that whole period automatically — e.g. Date From = `last month` alone filters to last month only (1st through its last day), not "from the 1st of last month onward" including everything since. `ytd` is bounded by today, not December 31st; weeks start Monday. Filling in both fields explicitly always wins over the auto-fill. A plain ISO date or a relative offset (`-7d`) used alone stays open-ended, since those are single points in time rather than spans with a natural other end.
- **Account** — matches if *any* posting in the transaction matches. A plain string is a case-insensitive substring match; a string containing any regex metacharacter (`. ^ $ * + ? ( ) [ ] { } | \`) is compiled and matched as a Python regex instead (case-insensitive) — e.g. `^expenses:food` matches only accounts starting with that prefix, `food|rent` matches either. This is the same substring-or-regex convention hledger itself uses. `Tab` completes/cycles known account names (see above).
- **Payee** — same substring-or-regex convention, matched against the transaction description. `Tab` completes/cycles known payee names.

**Apply** builds the filter and shows only matching transactions, using the same show/edit/merge-back engine as `Ctrl+L` — edits made while filtered are merged back into the full journal when you clear the filter, switch to `Ctrl+L`, or save. An invalid date string or regex is rejected with a notification and the previous view is left unchanged. Applying with **every field blank** is treated as "no filter" (same as Clear) rather than a "match everything" filter — it's a true no-op and won't reformat the document or mark it modified.

**Clear** restores the full journal and empties the popup's own input fields.

`Ctrl+O`'s criteria filter and `Ctrl+L`'s cleared/uncleared cycle **combine** — active together, they narrow the view to transactions matching *both* (e.g. "Cleared only" + an account filter shows only cleared transactions in that account), not just whichever was applied most recently. Either can be adjusted or cleared independently of the other: clearing the `Ctrl+O` filter leaves any active `Ctrl+L` mode in place, and cycling `Ctrl+L` back to All leaves an active `Ctrl+O` filter in place. The status bar at the top of the editor describes whichever combination is currently active, together with a **visible/total transaction count** whenever any filter is active (e.g. "View: Cleared only + Filtered (Ctrl+O) (2/17)") — no count is shown for "All transactions", since it's redundant there.

## Cleared / Status Toggle

| Shortcut | Action |
|----------|--------|
| `Ctrl+R` | **Single transaction**: 3-state cycle: uncleared → pending (`!`) → cleared (`*`) → uncleared. **Multi-transaction selection**: if all selected are cleared → all become uncleared; otherwise → all become cleared (`*`). |

## Tab Autocomplete

| Shortcut | Action |
|----------|--------|
| `Tab` | Complete the account or payee name at the cursor. Press again to cycle to the next match. Anywhere else, falls through to ordinary focus-cycling (there's currently only one focusable panel, so this is rarely noticeable). |
| `Escape` | Dismiss the suggestion bar, if showing (checked before search-bar dismissal / unfocus — see the Search section). |
| `Shift+Tab` | Reverse focus-cycle (unaffected by autocomplete). |

Works in three places:

- **Posting line, while typing the account name** (before the amount) — suggests from every account declared with an `account` directive plus every account actually used on a posting anywhere in the journal.
- **Transaction header, at or past the payee/description field** (after the date and any `*`/`!`/`(CODE)`) — suggests from every declared `payee` directive plus every transaction description in the journal.
- **The Ctrl+O filter popup's Account and Payee fields** — same account/payee lists as above, applied to the whole field's value rather than a token within a line (no suggestion bar there; the field's text just updates in place on each `Tab`). See [Transaction Filter (Ctrl+O)](#transaction-filter-ctrlo).

Suggestions come from a snapshot index rebuilt on file load and after each `Ctrl+S` save — not on every keystroke, so text you've typed but not yet saved won't complete against itself until you save. The first match is inserted immediately; in the main editor, a suggestion bar at the bottom shows the full candidate list and highlights the current one (the filter popup's fields don't have room for that, so there it's just the field's value cycling with no visible list). This intentionally cycles like shell tab-completion (press `Tab` repeatedly to step through matches) rather than a `Up`/`Down`-navigable dropdown — `Up`/`Down` stay ordinary cursor-movement keys everywhere in the editor, including while the search bar has focus.

## Transaction Block Selection & Navigation

| Shortcut | Action |
|----------|--------|
| `Ctrl+T` | First press: select the current transaction block. Each subsequent press: extend the selection by one more transaction block. |
| `Shift+PgUp` | Move cursor to the header line of the previous transaction. **When search bar is open**: jump to previous match instead. |
| `Shift+PgDown` | Move cursor to the header line of the next transaction. **When search bar is open**: jump to next match instead. |

## Text Editing

| Shortcut | Action |
|----------|--------|
| `Enter` | When cursor is on a transaction header (and **not** at column 0) or posting line, the new line is auto-indented with 4 spaces. At column 0 of a header, Enter inserts a plain newline (useful for adding blank lines between transactions). `Tab` is reserved for autocomplete — see [Tab Autocomplete](#tab-autocomplete) above. |
| `Ctrl+G` | **Single cursor**: duplicate the current transaction block to end of file with today's date. **Multi-block selection** (from repeated `Ctrl+T`): duplicate all selected transaction blocks to end of file, each with today's date. Fully undoable with `Ctrl+Z`. |
| `Ctrl+D` | Insert today's date at the cursor position |
| `Ctrl+Z` | Undo. Reverses custom commands (CommandHistory) first; if none, falls through to native TextArea undo for regular text edits. |
| `Ctrl+Y` | Redo. Mirrors `Ctrl+Z` fallthrough logic. |

## Text Navigation (custom bindings)

| Shortcut | Action |
|----------|--------|
| `Ctrl+Home` | Move cursor to start of file |
| `Ctrl+End` | Move cursor to end of file |
| `Ctrl+A` | Select all text in the editor |

## Cursor / Text Navigation (TextArea built-in)

The editor surface is a full TextArea. All standard cursor movement is available
natively — arrow keys, `Home`/`End`, `Ctrl+←/→` (word jump), `PgUp`/`PgDn`,
`Shift+` any of the above to select. `Ctrl+Shift+←/→` selects word-by-word
(does not snap to end of line — this is expected behaviour).

## Command Palette

| Shortcut | Action |
|----------|--------|
| `Ctrl+P` | Open command palette |

## Emacs Ledger-Mode Conventions (Milestone 3 — pending)

| Shortcut | Action |
|----------|--------|
| `Shift+Up` | Increment the date component under the cursor (year, month, or day) — on either a transaction header or a `P` price-directive date. An unpadded date (e.g. `2026-9-1`) is expanded to zero-padded form (`2026-09-01`) as part of the same shift. Falls back to text selection when cursor is not on a date field. |
| `Shift+Down` | Decrement the date component under the cursor (year, month, or day) — on either a transaction header or a `P` price-directive date, with the same unpadded-date expansion as `Shift+Up`. Falls back to text selection when cursor is not on a date field. |
| `Shift+Alt+Up` | Increment date by one month *(reserved — not yet implemented)* |
| `Shift+Alt+Down` | Decrement date by one month *(reserved — not yet implemented)* |
| `Alt+P` | Insert previous matching transaction template (Emacs `M-p`) |
| `Alt+N` | Insert next matching transaction template (Emacs `M-n`) |
| `Ctrl+K` | Kill (delete) to end of line |

## Known Terminal-Emulator Conflicts

| Shortcut | Conflict | Notes |
|----------|----------|-------|
| `Ctrl+C` | SIGINT (many terminals) | May need remapping in terminal settings |
| `Ctrl+K` | Some terminal emulators use for clear-line | Documented; handle gracefully |
| `Ctrl+Shift+P` | Windows Terminal command palette | No longer used by the app |

See [knowledge_base/design_decisions.md](../knowledge_base/design_decisions.md)
for the full conflict log and resolutions.
