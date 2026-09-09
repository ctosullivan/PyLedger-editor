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
| `Ctrl+R` | toggle_cleared | — | 3-state cycle (uncleared → `!` → `*` → uncleared); multi-block selection bulk-toggles |
| `Ctrl+G` | autofill | — | Single cursor → duplicate current block; multi-block selection → duplicate all selected blocks |
| `Ctrl+D` | insert_today | ✓ | Overrides TextArea `delete_right` |
| `Escape` | blur_editor | — | Unfocus TextArea (or close search bar) |
| `Ctrl+T` | select_transaction_block | ✓ | Block-select current transaction; repeated presses extend to next block |
| `Shift+PageUp` | prev_transaction | ✓ | Jump to previous transaction header. **Search bar open**: jump to previous match instead. |
| `Shift+PageDown` | next_transaction | ✓ | Jump to next transaction header. **Search bar open**: jump to next match instead. |
| `Ctrl+Home` | cursor_to_start | ✓ | Move cursor to top of file |
| `Ctrl+End` | cursor_to_end | ✓ | Move cursor to bottom of file |
| `Ctrl+A` | select_all | ✓ | Select entire file content |
| `Ctrl+F` | open_search | ✓ | Opens bar if closed; advances to next match if bar already open. **priority=True required** — TextArea maps Ctrl+F → `delete_word_right` |
| `Ctrl+L` | cycle_view_filter | — | Cycle view: All → Cleared → Unreconciled → All. Exits an active Ctrl+O criteria filter first if one is active (mutually exclusive — `view_filter.py`) |
| `Ctrl+Z` | undo | ✓ | Consults `CommandHistory` (Layer 2) first, falls through to TextArea's native undo |
| `Ctrl+Y` | redo | ✓ | Mirrors `Ctrl+Z` fallthrough |
| `Shift+Up` | date_shift_up | ✓ | Increment the date sub-field under the cursor (`date_shift.py`, `DateShiftMixin`) — transaction header or `P` price directive. Falls through to TextArea's own Shift+Up selection off a date field |
| `Shift+Down` | date_shift_down | ✓ | Same as Shift+Up, decrementing |
| `Tab` | autocomplete | ✓ | Complete the account/payee token at the cursor, or cycle to the next match if already showing (`autocomplete.py`, `AutocompleteMixin`). Falls through to `app.action_focus_next()` (ordinary Tab's default target) when nothing is completable — **overrides TextArea's default `tab_behavior="focus"` handling**, i.e. this binding *is* what makes Tab do anything at all in this editor now, not TextArea |

### FilterPopup (`filter_popup.py`)

| Key | Action | priority=True | Notes |
|---|---|---|---|
| `Ctrl+O` | close_self | ✓ | Close popup (same key that opened it). Leaves any already-applied filter active — does not clear it |
| `Escape` | close_self | ✓ | Close popup, same caveat as above |

Not a key binding, but relevant here: `Enter` in any of FilterPopup's `Input`
fields (`on_input_submitted`), or the **Apply**/**Clear** `Button`s
(`on_button_pressed`), post `FilterApplied`/`FilterCleared` messages —
handled by `LedgerApp` (`app.py`), not `JournalEditor`, since `FilterPopup`
is a Screen-level sibling of `JournalEditor`, not a child (see
`dev-docs/architecture.md`'s Layout section).

### SearchBar (`search_bar.py`)

| Key | Action | priority=True | Notes |
|---|---|---|---|
| `Ctrl+C` | copy_match | — (deliberately) | Copies the current search match's text — **only** reached when the focused `#search-input` `Input` has no text selection of its own (`Input.action_copy()` raises `SkipAction` in that case, letting the key bubble here). Deliberately **not** `priority=True`: that would let this binding preempt a real selection the user made *inside the search box itself*, which must keep copying normally via `Input`'s own (non-priority) `ctrl+c` binding — see the module's `BINDINGS` comment for the full reasoning. This is the safe pattern for binding Ctrl+C at all; see the correction to §6 below. |

Escape-dismissal is handled by `JournalEditor.action_blur_editor` (checked
after the Tab-autocomplete popup, before the search bar), not a SearchBar
binding of its own. Match navigation is dispatched by JournalEditor
(context-sensitive Ctrl+F for next, Shift+PageUp/PageDown for
previous/next) and forwarded to SearchBar via method calls.

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
| `Ctrl+C` | copy | No, on the TextArea itself — but SearchBar's `#search-input` `Input` binds its own `ctrl+c` (non-priority, see §1 SearchBar) whenever the search bar has focus instead |
| `Ctrl+V` | paste | No — not bound by project |
| `Ctrl+X` | cut | No — not bound by project |
| `Ctrl+Z` | undo | **YES** — overridden by JournalEditor `priority=True` (consults `CommandHistory` first) |
| `Ctrl+Y` | redo | **YES** — overridden by JournalEditor `priority=True` |
| `Ctrl+D` | delete_right (one char forward) | **YES** — overridden by JournalEditor `priority=True` (insert today) |
| `Ctrl+F` | delete_word_right | **YES** — overridden by JournalEditor `priority=True` (open search) |
| `Ctrl+K` | delete_to_line_end | No — not bound by project |
| `Ctrl+U` | delete_to_line_start | No — not bound by project |
| `Ctrl+W` | delete_word_left | No — not bound by project |
| `Backspace` | delete_left | No |
| `Delete` | delete_right | No |
| `Enter` | newline_below (or insert newline) | No (project has special logic in `_on_key` for indented Enter) |
| `Tab` | focus-cycle (`tab_behavior="focus"`, TextArea's default — not indent; the constructor never passes `tab_behavior="indent"`) | **YES** — overridden by JournalEditor `priority=True` (Tab autocomplete). Since `tab_behavior` is left at its default, TextArea itself never actually consumes Tab either way — JournalEditor's binding is the only thing giving Tab any behavior in this editor now |

### No built-in TextArea binding for these (safe to bind)

`Ctrl+B`, `Ctrl+E`, `Ctrl+G`, `Ctrl+H`, `Ctrl+I`, `Ctrl+J`, `Ctrl+L`,
`Ctrl+M`, `Ctrl+N`, `Ctrl+O`, `Ctrl+P`, `Ctrl+Q`, `Ctrl+R`, `Ctrl+S`,
`Ctrl+T`, `F1`–`F12` (all free), `Alt+*`.

> Note: outside a Textual app, terminal emulators may intercept `Ctrl+Q`
> (XON/XOFF), `Ctrl+S` (flow-control pause), `Ctrl+C` (SIGINT), `Ctrl+Z`
> (SIGTSTP) before an application ever sees them. Textual sets raw mode, so
> **all four are actually safe to bind** inside this app — verified in
> practice for `Ctrl+S`, `Ctrl+Z`, and `Ctrl+C` (§6 above); the real
> constraint for `Ctrl+C` specifically isn't the terminal, it's Textual's
> own `App`-level `ctrl+c → help_quit` binding, which is why that one
> needs the "bind non-priority on a focused child, let its own copy action
> refuse first" pattern rather than a flat "don't bind it."

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
| `Ctrl+Shift+P` | Command palette | No longer used by the app |

---

## 4. Free Ctrl+ Keys (as of v1.0.2 / `release/1.1.0`)

These keys have no TextArea binding AND no project binding. Safe to add new
actions without `priority=True`:

`Ctrl+B`, `Ctrl+E`, `Ctrl+H`, `Ctrl+I`, `Ctrl+J`, `Ctrl+M`, `Ctrl+N`, `Ctrl+Q`*

`Ctrl+P` is **not** free — it's Textual's own built-in command-palette
binding (`App.COMMAND_PALETTE_DISPLAY = "Ctrl+P"` in `app.py` is just the
display string for it, not the binding itself). `Ctrl+O` is bound to the
FilterPopup toggle. `Tab` is bound to autocomplete (§1).

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
`priority=True`. The full list as of v1.0.2 / `release/1.1.0`: `ctrl+d`,
`ctrl+f`, `ctrl+t`, `shift+pageup`, `shift+pagedown`, `ctrl+home`,
`ctrl+end`, `ctrl+a`, `ctrl+z`, `ctrl+y`, `shift+up`, `shift+down`, `tab`.

Exception, and worth remembering as the general rule when it applies:
SearchBar's `ctrl+c` (§1) is **deliberately non-priority** — see the
Ctrl+C correction in §6. Priority isn't "always add it defensively"; it's
"add it when the parent must go first," and sometimes (Ctrl+C) the
opposite is what's actually needed.

---

## 6. Terminal Compatibility Notes

| Key | Risk | Mitigation |
|---|---|---|
| `Ctrl+S` | Flow control (XOFF) in some terminals | Textual sets raw mode — safe in practice |
| `Ctrl+C` | Was assumed unsafe (SIGINT) — **corrected**: Textual's raw mode means the terminal never sees it; the real constraint is Textual's own `App`-level `ctrl+c` → `help_quit` binding (non-priority, `system=True`, Textual 8.2.5). It's now bound on SearchBar (non-priority — see §1) so a focused child's own `ctrl+c` handling gets first refusal, matching the pattern Textual's built-in `Input`/`TextArea` copy actions already use. **Safe to bind** following that same pattern; just don't use `priority=True` on it, or you'll pre-empt real in-widget copy actions the same way the old App-level nag used to pre-empt this one |
| `Ctrl+Z` | Was assumed unsafe (SIGTSTP) — **corrected**: same raw-mode reasoning as Ctrl+C. Bound as `undo` on JournalEditor with `priority=True` in practice, and it works — the raw-mode terminal never intercepts it |
| `Ctrl+Q` | XON resume in some multiplexers | Avoid; use `Ctrl+P` / `Ctrl+O` instead |
| `Alt+*` | Inconsistent across terminal emulators | Test in target terminal before shipping |
| `Ctrl+Shift+*` | May not be distinguishable in some terminals | Works in Windows Terminal and most modern emulators; test before shipping |
