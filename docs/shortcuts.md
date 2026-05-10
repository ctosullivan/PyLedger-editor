# Keyboard Shortcut Reference

## MS Office / Excel Conventions

| Shortcut | Action |
|----------|--------|
| `Ctrl+A` | Select all transactions in current view |
| `Ctrl+C` | Copy selected transaction(s) to clipboard |
| `Ctrl+V` | Paste transaction(s) from clipboard |
| `Ctrl+X` | Cut selected transaction(s) |
| `Ctrl+D` | Autofill: duplicate selected transaction to bottom of ledger; date adjusted to today |
| `Ctrl+S` | Save: sort transactions by date, re-align whitespace, then write (validation errors shown as warnings, do not block save) |
| `Ctrl+F` | Forward search |
| `Ctrl+R` | Reverse search |
| `Ctrl+Shift+F` | Open / close transaction filter popup |

## Cleared / Status Toggle

| Shortcut | Action |
|----------|--------|
| `Shift+C` | 3-state cycle: uncleared → pending (`!`) → cleared (`*`) → uncleared |

## Cursor / Text Navigation (TextArea built-in)

The editor surface is a full TextArea. All standard cursor movement is available
natively — arrow keys, `Home`/`End`, `Ctrl+←/→` (word jump), `PgUp`/`PgDn`,
`Shift+` any of the above to select. These are NOT custom bindings; they are
provided by the Textual TextArea widget and cannot conflict with app bindings.

## Emacs Ledger-Mode Conventions (Milestone 3 — pending)

| Shortcut | Action |
|----------|--------|
| `Tab` | Autocomplete account name / payee from known entries |
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
| `Ctrl+C` | SIGINT (many terminals) | May need remapping in terminal settings; see knowledge_base/design_decisions.md |
| `Ctrl+K` | Some terminal emulators use for clear-line | Documented; handle gracefully |

See [knowledge_base/design_decisions.md](../knowledge_base/design_decisions.md)
for the full conflict log and resolutions.
