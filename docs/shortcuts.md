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
| `Escape` | Close search bar (or unfocus editor) |

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

The popup has four fields, all optional — leave any blank to not filter on that dimension:

- **Date from / Date to** — smart dates: ISO 8601 (`2024-01-15`), named periods (`today`, `yesterday`, `last month`, `last year`, `ytd`), quarters (`q1`–`q4`, current year), or a relative offset (`-7d`, `+2w`, `-1m`, `+1y`).
- **Account** — matches if *any* posting in the transaction matches. A plain string is a case-insensitive substring match; a string containing any regex metacharacter (`. ^ $ * + ? ( ) [ ] { } | \`) is compiled and matched as a Python regex instead (case-insensitive) — e.g. `^expenses:food` matches only accounts starting with that prefix, `food|rent` matches either. This is the same substring-or-regex convention hledger itself uses.
- **Payee** — same substring-or-regex convention, matched against the transaction description.

**Apply** builds the filter and shows only matching transactions, using the same show/edit/merge-back engine as `Ctrl+L` — edits made while filtered are merged back into the full journal when you clear the filter, switch to `Ctrl+L`, or save. An invalid date string or regex is rejected with a notification and the previous view is left unchanged.

**Clear** restores the full journal.

`Ctrl+O`'s criteria filter and `Ctrl+L`'s cleared/uncleared cycle are **mutually exclusive** — applying one automatically exits the other first. The status bar at the top of the editor shows which (if either) is currently active.

## Cleared / Status Toggle

| Shortcut | Action |
|----------|--------|
| `Ctrl+R` | **Single transaction**: 3-state cycle: uncleared → pending (`!`) → cleared (`*`) → uncleared. **Multi-transaction selection**: if all selected are cleared → all become uncleared; otherwise → all become cleared (`*`). |

## Panel Focus Cycling

| Shortcut | Action |
|----------|--------|
| `Tab` | Cycle focus: Text editor → Text editor (only one panel now) |
| `Shift+Tab` | Reverse cycle |

## Transaction Block Selection & Navigation

| Shortcut | Action |
|----------|--------|
| `Ctrl+T` | First press: select the current transaction block. Each subsequent press: extend the selection by one more transaction block. |
| `Shift+PgUp` | Move cursor to the header line of the previous transaction. **When search bar is open**: jump to previous match instead. |
| `Shift+PgDown` | Move cursor to the header line of the next transaction. **When search bar is open**: jump to next match instead. |

## Text Editing

| Shortcut | Action |
|----------|--------|
| `Enter` | When cursor is on a transaction header (and **not** at column 0) or posting line, the new line is auto-indented with 4 spaces. At column 0 of a header, Enter inserts a plain newline (useful for adding blank lines between transactions). TAB is reserved for focus cycling. |
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
