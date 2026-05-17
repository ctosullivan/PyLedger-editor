# Keyboard Shortcut Reference

## File Operations

| Shortcut | Action |
|----------|--------|
| `Ctrl+S` | Save: merge any active filter view, sort transactions by date, re-align whitespace, then write (validation errors shown as warnings, do not block save) |
| `Ctrl+Shift+P` | Open / close transaction filter popup |

## Search

| Shortcut | Action |
|----------|--------|
| `Ctrl+F` | Open search bar (if closed), or jump to **next** match (if bar already open) |
| `Ctrl+Shift+F` | Jump to **previous** match (bar must be open) |
| `Ctrl+R` | Jump to **previous** match when the search bar is open; otherwise toggles cleared state |
| `Escape` | Close search bar (or unfocus editor) |

Search requires at least 2 characters. Matches are highlighted in the editor: dim background for all matches, bright background for the current match. The counter shows "N of M" (or "No matches").

## View Filter (Ctrl+L)

| Shortcut | Action |
|----------|--------|
| `Ctrl+L` | Cycle view filter: **All transactions** → **Cleared only** → **Unreconciled only** → All |

The view filter changes what the editor shows without hiding any data from disk:

- **All transactions** (default): full journal visible; normal read-write editing.
- **Cleared only**: shows only transactions marked `*`. Editing is allowed; changes are merged back into the full journal when the filter changes or when you save.
- **Unreconciled only**: shows only transactions with no `*` flag. Same edit-and-merge behaviour.

`Ctrl+S` while in a filtered view merges edits back and saves the **complete** journal (all transactions, not just the visible ones), then returns the editor to All mode.

## Cleared / Status Toggle

| Shortcut | Action |
|----------|--------|
| `Ctrl+R` | **Normal mode, single transaction**: 3-state cycle: uncleared → pending (`!`) → cleared (`*`) → uncleared. **Multi-transaction selection**: if all selected are cleared → all become uncleared; otherwise → all become cleared (`*`). **Search bar open**: jumps to previous match instead. |

## Panel Focus Cycling

| Shortcut | Action |
|----------|--------|
| `Tab` | Cycle focus: Text editor → Text editor (only one panel now) |
| `Shift+Tab` | Reverse cycle |

## Transaction Block Selection & Navigation

| Shortcut | Action |
|----------|--------|
| `Ctrl+T` | First press: select the current transaction block. Each subsequent press: extend the selection by one more transaction block. |
| `Shift+PgUp` | Move cursor to the header line of the previous transaction |
| `Shift+PgDown` | Move cursor to the header line of the next transaction |

## Text Editing

| Shortcut | Action |
|----------|--------|
| `Enter` | When cursor is on a transaction header (and **not** at column 0) or posting line, the new line is auto-indented with 4 spaces. At column 0 of a header, Enter inserts a plain newline (useful for adding blank lines between transactions). TAB is reserved for focus cycling. |
| `Ctrl+G` | **Single cursor**: duplicate the current transaction block to end of file with today's date. **Multi-block selection** (from repeated `Ctrl+T`): duplicate all selected transaction blocks to end of file, each with today's date. |
| `Ctrl+D` | Insert today's date at the cursor position |

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
| `Shift+Up` | Increment date by one day |
| `Shift+Down` | Decrement date by one day |
| `Shift+Alt+Up` | Increment date by one month |
| `Shift+Alt+Down` | Decrement date by one month |
| `Alt+P` | Insert previous matching transaction template (Emacs `M-p`) |
| `Alt+N` | Insert next matching transaction template (Emacs `M-n`) |
| `Ctrl+K` | Kill (delete) to end of line |

## Known Terminal-Emulator Conflicts

| Shortcut | Conflict | Notes |
|----------|----------|-------|
| `Ctrl+C` | SIGINT (many terminals) | May need remapping in terminal settings |
| `Ctrl+K` | Some terminal emulators use for clear-line | Documented; handle gracefully |
| `Ctrl+Shift+P` | Windows Terminal command palette | FilterPopup binding — may be intercepted |
| `Ctrl+Shift+F` | Windows Terminal Find bar | May be intercepted; use `Ctrl+R` as fallback for prev-match |

See [knowledge_base/design_decisions.md](../knowledge_base/design_decisions.md)
for the full conflict log and resolutions.
