# Design Decisions

Non-obvious judgment calls, conflicts, and rationale.
Add an entry whenever a non-obvious decision is made or a conflict is discovered.

---

## Shift+C Cleared Toggle Cycle (2026-05-10)

**Decision**: 3-state cycle — uncleared → pending → cleared → uncleared

**Mapping to PyLedger fields**:
```
uncleared: cleared=False, pending=False
pending:   cleared=False, pending=True
cleared:   cleared=True,  pending=False
```

**Rationale**: User requested 3-state to match full hledger semantics. The
`"!"` (pending) state is useful for recording transactions that have been
initiated but not yet confirmed (e.g. cheques in transit).

**Note**: PyLedger v0.5.0 does NOT have a `Transaction.flag` field — the prompt
spec was incorrect. The actual fields are `Transaction.cleared: bool` and
`Transaction.pending: bool`. All toggle logic must use these two booleans.

---

## Ctrl+D Autofill Scope (2026-05-10)

**Decision**: Duplicate once — copy selected transaction into a new entry at
the bottom of the ledger, date adjusted to today.

**Rationale**: User confirmed "duplicate once" semantics (option a). Fill-all
(Excel-style) was rejected as it is destructive and not aligned with typical
ledger editing workflow where each transaction is discrete.

---

## Ctrl+S Tidy Behaviour (2026-05-10)

**Decision**: Sort transactions by date + re-align amounts/whitespace,
then warn-and-save (validation errors shown as warnings, do not block write).

**Rationale**: User chose the most comprehensive tidy (both sort and align) with
non-blocking validation. This matches hledger's philosophy of being permissive
during editing. Editors should never silently discard data.

**Implementation notes**:
- Sort is stable on equal dates (preserve original order within a date).
- Re-align: use PyLedger.journal_to_text() output as the canonical tidy form,
  then re-parse to confirm round-trip fidelity.
- Validation: run `PyLedger` basic checks; surface errors in a notification bar.

---

## Transaction.flag vs cleared/pending (2026-05-10)

**Decision**: Use `Transaction.cleared` and `Transaction.pending` booleans.

**Context**: The scaffold prompt (§3.2) described `Transaction.flag: str | None`
with values `None / "*" / "!"`. After vendor checkout this was confirmed to be
incorrect for v0.5.0. The actual model uses separate `bool` fields.

**Consequence**: Any code, test, or documentation that references `Transaction.flag`
is wrong and must be corrected. This is recorded in `knowledge_base/pyledger_api_notes.md`.

---

## File Resolution Order (2026-05-10)

**Decision**: CLI argument → `$LEDGER_FILE` → `~/.hledger.journal` → None (prompt on launch)

**Rationale**: Matches PyLedger's own `cli.py` resolution order (hledger-compatible).
Using the same order means users familiar with hledger have no surprises.

---

## Terminal-Emulator Keybinding Conflicts

Conflicts are documented here as discovered during implementation.

| Shortcut | Conflict | Status |
|----------|----------|--------|
| `Ctrl+C` | SIGINT (interrupt) in many terminals | Textual intercepts this before the terminal; should work in most cases. Verify on Windows Terminal and macOS Terminal. |
| `Ctrl+K` | Clear to end of line in some terminals (e.g. bash readline) | Textual intercepts; should work inside the TUI. Test with iTerm2 and Windows Terminal. |
| `Shift+Alt+Up/Down` | Month increment/decrement — may conflict with window management on some desktop environments | Document workaround if reported by users. |

---

## Test Runner Choice (2026-05-10)

**Decision**: pytest with pytest-asyncio (`asyncio_mode = "auto"`)

**Rationale**: Textual's async widget tests require an async test runner.
pytest-asyncio integrates cleanly. PyLedger itself uses unittest, but the
editor's Textual widget tests would be significantly more verbose with unittest
and no native async support.
