# CONTEXT.md — Session Working Memory

## Current Task

v0.6.0 — UAT round 2 fixes + insert-date refinements. **COMPLETE** as of 2026-05-12.
All 178 tests pass.

## Where We Are

v0.6.0 committed. Changes since v0.5.0:

**Bug fixes:**
- Amount last-digit white: Textual `_highlights` uses UTF-8 byte offsets (tree-sitter).
  Added `_build_cp_to_byte()` in `ledger_textarea.py`; `_build_highlight_map` now
  converts codepoint spans to byte spans before writing to `_highlights`.
- 1-char suffix commodity white: `_AMOUNT_RE` changed `{2,6}` → `{1,6}`.
- Enter at col 0 indented date: added `col > 0` guard for XACT_HEADER in `_on_key`.
- Ctrl+T not extending: `action_select_transaction_block` now extends when current
  selection ends at a block boundary, adding the next block with each press.
- Ctrl+R order-sensitive: normalized `min/max(sel.start[0], sel.end[0])` in
  `action_toggle_cleared` so reversed selections work correctly.
- Ctrl+Shift+F not closing popup: added `priority=True` BINDINGS for ctrl+shift+f
  and escape to `FilterPopup`, plus `action_close_self`.
- Enter auto-indent scroll: replaced `self.move_cursor(self.cursor_location)` (reactive
  no-op) with `self.scroll_cursor_visible()` (unconditional) so cursor stays visible
  when pressing Enter at the bottom of the buffer.

**New features:**
- Live sidebar/register refresh: `JournalEditor.on_text_area_changed` debounces
  0.8 s then posts `LiveChanged(text, account)`; `BalanceSidebar.refresh_from_text()`
  and `RegisterPanel.refresh_account_from_text()` parse in-memory text via
  `parse_string_lenient`.
- `Ctrl+D` → `action_insert_today`: inserts today's ISO date + trailing space at
  cursor. `priority=True` overrides TextArea's delete-char handler. (Initial
  bindings tried: `Ctrl+;` didn't register; `Ctrl+M` conflicted with Enter.)

## Decisions In Flight

**Textual version**: `.venv` has Textual 8.2.5. System Python has 0.83.0. Always
run via `.venv`.

**`_build_highlight_map()` override**: Private Textual 8.2.5 API. Revisit on upgrade.

**Byte vs codepoint offsets**: Confirmed — Textual's `_highlights` uses UTF-8 byte
column offsets (from tree-sitter `node.start_point`/`end_point`). `_build_cp_to_byte`
is the conversion layer. ASCII-only lines: byte == codepoint (no overhead).

**MRO dispatch**: `event.prevent_default()` required in `_on_key` (early `return`
not sufficient — Textual calls `_on_key` from every MRO class independently).

**scroll_cursor_visible()**: Public TextArea method — unconditional scroll to cursor.
Needed after `event.prevent_default()` + `self.insert()` because Textual's normal
scroll-to-cursor step is skipped when default action is prevented.

**Live refresh debounce**: 0.8 s after last keystroke. Uses `parse_string_lenient`
so partial edits show best-effort tree rather than crashing.

**ANSI themes**: No colour styling in ANSI-Dark/Light — expected behaviour, since
there are no CSS variable equivalents for the ANSI colour names. The fallback
(#888888) applies for all tokens.

## Files Currently Relevant

- `src/ledger_editor/highlighting/highlighter.py` — `_AMOUNT_RE` {1,6} fix
- `src/ledger_editor/widgets/ledger_textarea.py` — `_build_cp_to_byte`, updated
  `_build_highlight_map`, col-0 guard + `scroll_cursor_visible` in `_on_key`
- `src/ledger_editor/widgets/transaction_table.py` — Ctrl+T extend, Ctrl+R
  normalization, Ctrl+D insert-today, `LiveChanged` message, debounced
  `on_text_area_changed`
- `src/ledger_editor/widgets/filter_popup.py` — close bindings
- `src/ledger_editor/widgets/balance_sidebar.py` — `refresh_from_text`
- `src/ledger_editor/widgets/register_panel.py` — `refresh_account_from_text`
- `src/ledger_editor/app.py` — `on_journal_editor_live_changed`
- `docs/shortcuts.md` — Ctrl+T extend, Ctrl+D insert-date updated
- `tests/test_highlighting.py` — TestCommodity1Char, TestCpToByteMapping added
- `tests/test_transaction_table.py` — TestBulkToggleReversedSelection, TestEnterAtCol0,
  TestSelectExtend, TestInsertToday added

## Blockers / Open Questions

- ANSI themes have no colour styling — by design (no CSS variable equivalents).
  Could be addressed in a future milestone if needed.

## What NOT To Revisit

- `cleared: bool` and `pending: bool` on `Transaction` (NOT `flag: str`)
- Ctrl+R for toggle cleared, Ctrl+T for block select (extends on repeat), Ctrl+G for
  duplicate, Ctrl+D for insert today
- `_build_highlight_map()` is the correct override point
- `_app_theme_changed()` is the correct hook for theme switches
- Block background tinting: REMOVED by user request
- Payee token: always `PAYEE_UNCLEARED`
- Prefix commodity spans: merged into amount span
- `event.prevent_default()` required in `_on_key` — early `return` not sufficient
- Byte offset conversion is required for all `_highlights` spans
- `scroll_cursor_visible()` required after `event.prevent_default()` + `insert()` —
  `move_cursor(same_pos)` is a reactive no-op

## Recent Git State

Branch: master — v0.6.0 committed.
Last commit: feat: UAT round 2 fixes, Ctrl+D insert-date, scroll fix (v0.6.0)

Test suite: 178 tests.
