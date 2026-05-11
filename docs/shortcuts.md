# Keyboard Shortcut Reference

## File Operations

| Shortcut | Action |
|----------|--------|
| `Ctrl+S` | Save: sort transactions by date, re-align whitespace, then write (validation errors shown as warnings, do not block save) |
| `Ctrl+Shift+F` | Open / close transaction filter popup |

## Cleared / Status Toggle

| Shortcut | Action |
|----------|--------|
| `Ctrl+R` | **Single transaction**: 3-state cycle: uncleared → pending (`!`) → cleared (`*`) → uncleared. **Multi-transaction selection**: if all selected transactions are cleared → all become uncleared; otherwise → all become cleared (`*`). |

## Panel Focus Cycling

| Shortcut | Action |
|----------|--------|
| `Tab` | Cycle focus: Text editor → Balance sidebar → Register panel → Text editor |
| `Shift+Tab` | Reverse cycle |

## Transaction Block Selection & Navigation

| Shortcut | Action |
|----------|--------|
| `Ctrl+T` | Select the entire current transaction block (header line through last posting), regardless of cursor position within the block |
| `Shift+PgUp` | Move cursor to the header line of the previous transaction |
| `Shift+PgDown` | Move cursor to the header line of the next transaction |

## Text Editing

| Shortcut | Action |
|----------|--------|
| `Enter` | When cursor is on a transaction header or posting line, the new line is auto-indented with 4 spaces (TAB is reserved for focus cycling) |
| `Ctrl+G` | Duplicate the current transaction block to the end of the file with today's date |

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
| `Ctrl+Enter` | Finalise / commit current transaction entry |
| `Ctrl+K` | Kill (delete) to end of line |

## Known Terminal-Emulator Conflicts

| Shortcut | Conflict | Notes |
|----------|----------|-------|
| `Ctrl+C` | SIGINT (many terminals) | May need remapping in terminal settings |
| `Ctrl+K` | Some terminal emulators use for clear-line | Documented; handle gracefully |

See [knowledge_base/design_decisions.md](../knowledge_base/design_decisions.md)
for the full conflict log and resolutions.
