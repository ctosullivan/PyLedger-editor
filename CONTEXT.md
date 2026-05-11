# CONTEXT.md — Session Working Memory

## Current Task

v0.5.0 release — **COMPLETE** as of 2026-05-11. All 166 tests pass.

## Where We Are

v0.5.0 shipped. Changes relative to v0.4.0:

**Syntax highlighting:**
- Added `ledger_editor.highlighting` package (`tokens.py`, `highlighter.py`,
  `theme_bridge.py`) with pure-Python `LedgerHighlighter` (single O(N) scan).
- Added `ledger_editor.themes` package with `MONOKAI_PRO_APP_THEME`,
  `MONOKAI_PRO_TEXTAREA_THEME`, TCSS overrides, and `register_all()`.
- Introduced `LedgerTextArea(TextArea)` overriding `_build_highlight_map()`.

**UAT bug fixes:**
- Payee colour: always `PAYEE_UNCLEARED` regardless of cleared/pending state.
- Amount prefix artefact: prefix symbols (`£`, `$`, `€`) merged into amount span.
- Block tinting removed: no block-level background spans emitted anywhere.
- ANSI theme crash: `build_textarea_theme()` catches `ColorParseError`.
- Notes grey: `ledger.note` / `ledger.posting.note` use `_COMMENT` in Monokai Pro.

**New features:**
- Enter auto-indent: `LedgerTextArea._on_key()` with `event.prevent_default()` —
  inserts `\n    ` on XACT_HEADER/POSTING lines; prevents `TextArea._on_key` from
  running via Textual's MRO dispatch loop.
- Shift+PgUp/Down: navigate between transaction headers via `_line_infos`.
- Ctrl+G: duplicate current transaction block to end of file with today's date.
- Bulk Ctrl+R: multi-row selection → all cleared→uncleared; otherwise all→`*`.

**Key bindings (final):**
- `ctrl+r` — toggle/bulk-toggle cleared
- `ctrl+t` — select transaction block
- `ctrl+g` — duplicate transaction to end with today's date
- `shift+pageup/pagedown` — navigate prev/next transaction header

## Decisions In Flight

**Textual version**: `.venv` has Textual 8.2.5. System Python has 0.83.0. Always
run via `.venv`.

**`_build_highlight_map()` override**: Private Textual 8.2.5 API. Revisit on upgrade.

**MRO dispatch**: `event.prevent_default()` is the correct way to block parent
`_on_key` in a Textual TextArea subclass — early `return` is insufficient because
Textual calls `_on_key` from every class in the MRO independently.

**Performance**: `_scan()` is synchronous O(N). Acceptable for typical journals.
`@work(thread=True)` path documented for scale if needed.

## Files Currently Relevant

- `src/ledger_editor/highlighting/` — tokens, highlighter, theme_bridge, __init__
- `src/ledger_editor/themes/` — monokai_pro.py, __init__.py, monokai_pro.tcss
- `src/ledger_editor/widgets/ledger_textarea.py` — `LedgerTextArea(TextArea)`
- `src/ledger_editor/widgets/transaction_table.py` — `JournalEditor`
- `src/ledger_editor/app.py` — `LedgerApp.on_mount`, `CSS_PATH`
- `tests/test_highlighting.py` — 62 pure unit tests
- `tests/test_themes.py` — 7 Textual pilot tests
- `tests/test_transaction_table.py` — 97 tests

## Blockers / Open Questions

None.

## What NOT To Revisit

- `cleared: bool` and `pending: bool` on `Transaction` (NOT `flag: str`)
- Ctrl+R for toggle cleared, Ctrl+T for block select, Ctrl+G for duplicate
- Ctrl+S uses `Path.write_text(journal_to_text(...))` NOT `EditorDocument.save()`
- `-theme-monokai-pro` CSS class is auto-added by Textual (NOT manually toggled)
- `_build_highlight_map()` is the correct override point
- `_app_theme_changed()` is the correct hook for theme switches (not `watch_theme`)
- Block background tinting: REMOVED by user request
- Payee token: always `PAYEE_UNCLEARED`
- Prefix commodity spans: merged into amount span
- `event.prevent_default()` required in `_on_key` — early `return` not sufficient

## Recent Git State

Branch: master — committed as v0.5.0.
Last commit: feat: hledger syntax highlighting, Monokai Pro theme, UAT fixes (v0.5.0)

Test suite: 166 tests.
