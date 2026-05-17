# Keybindings Reference

Complete map of all keybindings active in Ledger Editor: project-defined bindings
per widget and inherited Textual/TextArea bindings. Used by Claude to reason about
binding conflicts and identify free keys.

---

## 1. Project-Defined Bindings

### JournalEditor (`transaction_table.py`)

| Key | Action | priority=True | Notes |
|---|---|---|---|
| `Ctrl+S` | save | — | Sort + save journal to disk; merges filtered view edits first |
| `Ctrl+R` | toggle_cleared | — | Context-sensitive: **search bar open** → prev match; **normal** → 3-state cycle |
| `Ctrl+G` | autofill | — | Single cursor → duplicate current block; multi-block selection → duplicate all selected blocks |
| `Ctrl+D` | insert_today | ✓ | Overrides TextArea `delete_right` |
| `Escape` | blur_editor | — | Unfocus TextArea (or close search bar) |
| `Ctrl+T` | select_transaction_block | ✓ | Block-select current transaction; repeated presses extend to next block |
| `Shift+PageUp` | prev_transaction | ✓ | Jump to previous transaction header |
| `Shift+PageDown` | next_transaction | ✓ | Jump to next transaction header |
| `Ctrl+Home` | cursor_to_start | ✓ | Move cursor to top of file |
| `Ctrl+End` | cursor_to_end | ✓ | Move cursor to bottom of file |
| `Ctrl+A` | select_all | ✓ | Select entire file content |
| `Ctrl+F` | open_search | ✓ | Opens bar if closed; advances to next match if bar already open. **priority=True required** — TextArea maps Ctrl+F → `delete_word_right` |
| `Ctrl+Shift+F` | search_prev | ✓ | Previous match (bar must be open). May be intercepted by Windows Terminal Find |
| `Ctrl+L` | cycle_view_filter | — | Cycle view: All → Cleared → Unreconciled → All |

### FilterPopup (`filter_popup.py`)

| Key | Action | priority=True | Notes |
|---|---|---|---|
| `Ctrl+Shift+P` | close_self | ✓ | Close popup (same key that opened it) |
| `Escape` | close_self | ✓ | Close popup |

### SearchBar (`search_bar.py`)

SearchBar has no BINDINGS of its own. It is dismissed via Escape (handled by
JournalEditor). Navigation is dispatched by JournalEditor (context-sensitive
Ctrl+F for next, Ctrl+Shift+F and Ctrl+R for previous) and forwarded to
SearchBar via method calls.

---

## 2. TextArea Inherited Bindings (Textual 8.2.5)

These are active whenever `LedgerTextArea` has focus. Any project binding that
overlaps **must use `priority=True`** on the parent widget's Binding entry, or
the TextArea will consume the key first.

### Cursor movement

| Key | TextArea action |
|---|---|
| `Up` / `Down` / `Left` / `Right` | cursor_up / cursor_down / cursor_left / cursor_right |
| `Ctrl+Left` / `Ctrl+Right` | cursor_word_left / cursor_word_right |
| `Home` / `End` | cursor_line_start / cursor_line_end |
| `PageUp` / `PageDown` | cursor_page_up / cursor_page_down |
| `Ctrl+Home` / `Ctrl+End` | cursor_document_start / cursor_document_end |

### Selection (hold Shift)

Shift + any cursor movement key extends the selection.

| Key | TextArea action |
|---|---|
| `Shift+Up/Down/Left/Right` | cursor_*_select variants |
| `Shift+Ctrl+Left/Right` | cursor_word_*_select |
| `Shift+Home/End` | cursor_line_*_select |
| `Shift+PageUp/PageDown` | cursor_page_*_select |
| `Shift+Ctrl+Home/End` | cursor_document_*_select |

### Editing

| Key | TextArea action | Collision with project? |
|---|---|---|
| `Ctrl+A` | select_all | **YES** — overridden by JournalEditor `priority=True` |
| `Ctrl+C` | copy | No — not bound by project |
| `Ctrl+V` | paste | No — not bound by project |
| `Ctrl+X` | cut | No — not bound by project |
| `Ctrl+Z` | undo | No — not bound by project |
| `Ctrl+Y` | redo | No — not bound by project |
| `Ctrl+D` | delete_right (one char forward) | **YES** — overridden by JournalEditor `priority=True` (insert today) |
| `Ctrl+F` | delete_word_right | **YES** — overridden by JournalEditor `priority=True` (open search) |
| `Ctrl+K` | delete_to_line_end | No — not bound by project |
| `Ctrl+U` | delete_to_line_start | No — not bound by project |
| `Ctrl+W` | delete_word_left | No — not bound by project |
| `Backspace` | delete_left | No |
| `Delete` | delete_right | No |
| `Enter` | newline_below (or insert newline) | No (project has special logic in `_on_key` for indented Enter) |
| `Tab` | indent | No (captured before TextArea in sidebar / register) |

### No built-in TextArea binding for these (safe to bind)

`Ctrl+B`, `Ctrl+E`, `Ctrl+G`, `Ctrl+H`, `Ctrl+I`, `Ctrl+J`, `Ctrl+L`,
`Ctrl+M`, `Ctrl+N`, `Ctrl+O`, `Ctrl+P`, `Ctrl+Q`, `Ctrl+R`, `Ctrl+S`,
`Ctrl+T`, `F1`–`F12` (all free), `Alt+*`.

> Note: Terminal emulators often intercept `Ctrl+Q` (XON/XOFF), `Ctrl+S`
> (flow-control pause), `Ctrl+C` (SIGINT), `Ctrl+Z` (SIGTSTP). Use these
> only when the app is known to run in a raw-mode terminal (Textual sets raw
> mode, so Ctrl+S and Ctrl+Z are safe; Ctrl+C is not safe).

---

## 3. Collision Map

All confirmed conflicts and their resolutions:

| Key | TextArea binding | Project binding | Widget | Resolution |
|---|---|---|---|---|
| `Ctrl+D` | delete_right | insert_today | JournalEditor | `priority=True` on JournalEditor Binding |
| `Ctrl+F` | delete_word_right | open_search (context-sensitive) | JournalEditor | `priority=True` on JournalEditor Binding |
| `Ctrl+A` | select_all (TextArea) | select_all | JournalEditor | `priority=True` on JournalEditor Binding |

Windows Terminal intercepts (at winui level, never reach the Textual app):

| Key | Windows Terminal default | Project impact |
|---|---|---|
| `Ctrl+Shift+P` | Command palette | FilterPopup may not open in Windows Terminal |
| `Ctrl+Shift+F` | Find bar | search_prev may not work; use Ctrl+R as fallback for prev-match |

---

## 4. Free Ctrl+ Keys (as of v0.8.0)

These keys have no TextArea binding AND no project binding. Safe to add new
actions without `priority=True`:

`Ctrl+B`, `Ctrl+E`, `Ctrl+H`, `Ctrl+I`, `Ctrl+J`, `Ctrl+M`,
`Ctrl+N`, `Ctrl+O`, `Ctrl+P`, `Ctrl+Q`*

Function keys (all free):
`F1`–`F12`

Keys with a TextArea binding but unused by the project (safe to override with
`priority=True`):
`Ctrl+K` (delete_to_line_end), `Ctrl+U` (delete_to_line_start),
`Ctrl+W` (delete_word_left)

> *`Ctrl+Q` may be intercepted by some terminal multiplexers.

---

## 5. `priority=True` Pattern

When a parent widget (e.g. JournalEditor) and a focused child widget (e.g.
LedgerTextArea / TextArea) both claim the same key, Textual delivers the key to
the **focused child** first. The parent never sees it unless the child either
does not handle the key or the parent's binding has `priority=True`.

```python
# WRONG — TextArea's ctrl+f (delete_word_right) fires; JournalEditor never sees it
Binding("ctrl+f", "open_search", "Search")

# CORRECT — JournalEditor intercepts the key before TextArea
Binding("ctrl+f", "open_search", "Search", priority=True)
```

All JournalEditor bindings that shadow TextArea built-ins must carry
`priority=True`. The full list as of v0.8.0: `ctrl+d`, `ctrl+f`,
`ctrl+shift+f`, `ctrl+t`, `shift+pageup`, `shift+pagedown`,
`ctrl+home`, `ctrl+end`, `ctrl+a`.

---

## 6. Terminal Compatibility Notes

| Key | Risk | Mitigation |
|---|---|---|
| `Ctrl+S` | Flow control (XOFF) in some terminals | Textual sets raw mode — safe in practice |
| `Ctrl+C` | SIGINT in most terminals | **Do not bind** |
| `Ctrl+Z` | SIGTSTP in most terminals | **Do not bind** |
| `Ctrl+Q` | XON resume in some multiplexers | Avoid; use `Ctrl+P` / `Ctrl+O` instead |
| `Alt+*` | Inconsistent across terminal emulators | Test in target terminal before shipping |
| `Ctrl+Shift+*` | May not be distinguishable in some terminals | Works in Windows Terminal and most modern emulators; test before shipping |
