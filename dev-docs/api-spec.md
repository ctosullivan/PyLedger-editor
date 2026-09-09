# Internal API Specification

> **PROTECTED FILE** — Do not modify without explicit user approval.
> See CLAUDE.md §Unauthorised Change Rule.
> Last corrected 2026-09-09 against the actual `src/ledgerkit_editor/` tree
> (approved fix — see `CHANGELOG.md [Unreleased]`). The widgets this file
> previously documented under `BalanceSidebar`, `reconcile_actions`,
> `reconcile_bar`, `reconcile_summary`, and `register_panel` were removed
> in v0.8.0 and no longer exist; those sections have been dropped.

This file documents the internal APIs exposed by `ledgerkit_editor` modules.
It does NOT document ledgerkit's own API — see the
[ledgerkit PyPI package](https://pypi.org/project/ledgerkit/) source and
`knowledge_base/ledgerkit_api_notes.md` for that.

---

## `ledgerkit_editor.utils.file_resolver`

### `resolve_journal_file`

```python
def resolve_journal_file(cli_path: str | None) -> Path | None:
    """Return the resolved journal file path, or None if none is found.

    Resolution order:
      1. cli_path (if exists on disk)
      2. $LEDGER_FILE env var (if exists on disk)
      3. ~/.hledger.journal (if exists)
      4. None

    Args:
        cli_path: Raw path string from CLI, or None.

    Returns:
        Absolute Path, or None.
    """
```

---

## `ledgerkit_editor.utils.date_parser`

### `parse_date`

```python
def parse_date(text: str, today: datetime.date | None = None) -> datetime.date:
    """Parse a smart date string into a datetime.date.

    Raises:
        DateParseError: if the string matches none of the supported patterns.
    """
```

### `parse_date_range`

```python
def parse_date_range(
    from_text: str | None,
    to_text: str | None,
    today: datetime.date | None = None,
) -> tuple[datetime.date | None, datetime.date | None]:
    """Parse an optional date-from / date-to pair.

    A bounded calendar-period phrase ("last month", "today", "yesterday",
    "last year", "q1".."q4", "ytd" — see _period_bounds()) used ALONE in
    one field auto-fills the other from that same period's other end, so
    e.g. from_text="last month" with to_text=None resolves to the whole of
    last month, not an open-ended floor. Filling both fields explicitly is
    never overridden. A plain ISO date or relative offset ("-7d") used
    alone stays open-ended — single points in time, not spans.

    Raises:
        DateParseError: if either non-None string fails to parse.
    """
```

### `DateParseError`

```python
class DateParseError(ValueError): ...
```

---

## `ledgerkit_editor.utils.commodity_format`

### `extract_commodity_styles`

```python
def extract_commodity_styles(journal: Journal) -> dict[str, CommodityStyle]:
    """Return commodity styles inferred from a parsed Journal.

    Delegates to Journal.commodity_styles (ledgerkit v0.1.0+). Priority:
      1. Explicit commodity directives.
      2. First posting amount per commodity (uses Amount.raw).
      3. First price-directive amount per commodity.

    Returns an empty dict when the journal has no amounts with raw strings.
    """
```

### `apply_commodity_styles`

```python
def apply_commodity_styles(
    text: str,
    styles: dict[str, CommodityStyle],
) -> str:
    """Post-process serialised journal text to apply detected commodity formats.

    For each posting line, extracts the amount token, looks up its commodity
    in styles, and replaces the token with CommodityStyle.format(quantity).
    Lines whose commodity is absent from styles, and all non-posting lines,
    are passed through unchanged.

    Intended to run before align_posting_amounts() in the save pipeline so
    reformatted amounts are then correctly column-aligned.

    Returns text unchanged immediately when styles is empty.
    """
```

---

## `ledgerkit_editor.utils.query_match`

Local reimplementation of ledgerkit's substring-or-regex `Query` matching
convention — `ledgerkit.reports._matches_pattern`/`_posting_matches` are
private and not exported. See the module docstring for the "duplicate vs.
wait for an upstream export" decision.

### `matches_pattern`

```python
def matches_pattern(pattern: str, value: str) -> bool:
    """True if pattern matches value using hledger substring/regex rules.

    A pattern containing any regex metacharacter is compiled and matched via
    re.search (case-insensitive); otherwise a case-insensitive substring match.

    Raises:
        re.error: if pattern looks like regex but doesn't compile.
    """
```

### `build_transaction_predicate`

```python
def build_transaction_predicate(query: object) -> Callable[[object], bool]:
    """Build a whole-transaction visibility predicate from a ledgerkit.Query.

    Visible if: date within [date_from, date_to] (either may be None),
    description matches payee, and (when account/not_account/depth is set)
    at least one posting matches all of them.

    Raises:
        re.error: immediately, if account/not_account/payee looks like
            regex but fails to compile — validated once up front.
    """
```

---

## `ledgerkit_editor.utils.journal_index`

Account/payee name index for Tab autocomplete — a snapshot, not
recomputed per keystroke. See the module docstring.

### `JournalIndex`

```python
@dataclass
class JournalIndex:
    accounts: list[str] = field(default_factory=list)
    payees: list[str] = field(default_factory=list)

    def matching_accounts(self, prefix: str, limit: int = 8) -> list[str]:
        """Accounts starting with prefix (case-insensitive), shortest first."""

    def matching_payees(self, prefix: str, limit: int = 8) -> list[str]:
        """Payees starting with prefix (case-insensitive), shortest first."""
```

### `build_journal_index`

```python
def build_journal_index(text: str) -> JournalIndex:
    """Parse text and build a JournalIndex from declared_accounts/
    declared_payees plus every account/description actually used.

    Returns an empty JournalIndex if parsing fails entirely.
    """
```

---

## `ledgerkit_editor.utils.ledger_io`

### `load_journal`

```python
def load_journal(path: Path) -> Journal:
    """Load via ledgerkit.load(). Raises FileNotFoundError or ParseError."""
```

### `save_journal`

```python
def save_journal(path: Path, journal: Journal) -> None:
    """Serialise via ledgerkit.journal_to_text() and write to path."""
```

Note: `JournalEditor`'s own load (`on_mount`) and save (`action_save`) do
**not** currently call these — they read/write raw text directly and use
`parse_string_lenient`/`transaction_to_text` (see "ledgerkit Integration
Points" in `dev-docs/architecture.md`). `load_journal`/`save_journal` are a
stable, separately-tested public utility, not part of the live app's own
data flow.

### `align_posting_amounts`

```python
def align_posting_amounts(text: str, column: int = 52) -> str:
    """Re-space posting amount fields so each amount starts at ``column``.

    Applied to the output of journal_to_text() on every Ctrl+S save.
    Lines without an explicit amount (balance-completing postings, comment
    lines) are passed through unchanged.  Minimum spacing between account
    and amount is always 2 spaces.
    """
```

### `split_preamble`

```python
def split_preamble(text: str) -> tuple[str, str]:
    """Split journal text into (preamble, body).

    The preamble is all content before the first ISO-date transaction header.
    Returns (text, "") when no transactions are found.
    Used internally by split_journal_segments as a fallback.
    """
```

### `split_journal_segments`

```python
def split_journal_segments(
    text: str,
    transactions: list[Transaction],
) -> tuple[list[str], list[str]]:
    """Split journal text into non-transaction blocks and transaction blocks.

    Uses Transaction.source_span (1-based inclusive line numbers) to extract
    each transaction's lines. Returns (non_txn_blocks, txn_blocks) where
    len(non_txn_blocks) == len(txn_blocks) + 1. non_txn_blocks[0] is the
    preamble; non_txn_blocks[i] for i > 0 is the inter-transaction content
    (P directives, comments, blank lines) between txn_blocks[i-1] and
    txn_blocks[i]; non_txn_blocks[-1] is trailing content.

    Falls back to split_preamble semantics when source_span is unavailable.
    Used by action_save to preserve directives across sort-and-reserialise.
    """
```

---

## `ledgerkit_editor.utils.atomic_edit`

### `atomic_edit`

```python
@contextmanager
def atomic_edit(text_area: TextArea) -> Iterator[None]:
    """Collapse all TextArea edits within this block into one undo entry.

    Uses text_area.history._undo_stack (EditHistory, Textual 0.83.0).
    Raises RuntimeError if _undo_stack is absent.
    """
```

---

## `ledgerkit_editor.commands`

### `Command`

```python
@dataclass
class Command:
    execute: Callable[[], None]
    undo: Callable[[], None]
    description: str
```

### `CommandHistory`

```python
@dataclass
class CommandHistory:
    """Application-level undo/redo stack for text + model operations."""
    def execute(self, cmd: Command) -> None: ...
    def undo(self) -> Optional[Command]: ...
    def redo(self) -> Optional[Command]: ...
    @property
    def can_undo(self) -> bool: ...
    @property
    def can_redo(self) -> bool: ...
```

---

## `ledgerkit_editor.themes`

### `VALID_THEMES`

```python
VALID_THEMES: frozenset[str]
```

Frozenset of every accepted `--theme` value: all Textual built-in theme names
(from `textual.theme.BUILTIN_THEMES`) plus each project-bundled theme name.
Computed at import time so new Textual releases and new bundled entries are
included automatically.

---

## `ledgerkit_editor.app`

### `LedgerApp`

```python
class LedgerApp(App[None]):
    """Root Textual application. Constructed with a resolved journal Path."""

    def __init__(
        self,
        journal_path: Path,
        start_line: int | None = None,
        theme_name: str | None = None,
    ) -> None: ...
    def action_toggle_filter(self) -> None:
        """Ctrl+O: mount or remove the FilterPopup overlay."""

    def on_filter_popup_filter_applied(self, event: "FilterPopup.FilterApplied") -> None:
        """Relays event.predicate to JournalEditor.apply_criteria_filter().

        Lives here, not on JournalEditor, because FilterPopup is a
        Screen-level sibling of JournalEditor (both mounted directly by
        LedgerApp), not a child — its messages bubble to this App, not to
        JournalEditor.
        """

    def on_filter_popup_filter_cleared(self, event: "FilterPopup.FilterCleared") -> None:
        """Relays to JournalEditor.clear_criteria_filter(). Same rationale as above."""
```

`start_line`: 1-indexed line to place the cursor on after the file loads.
`theme_name`: Registered theme name; defaults to `monokai-pro` when `None`.

### `main`

```python
def main(argv: list[str] | None = None) -> None:
    """CLI entry point. Resolves journal, launches LedgerApp."""
```

---

## `ledgerkit_editor.widgets.JournalEditor` (`transaction_table.py`)

`JournalEditor(DateShiftMixin, ViewFilterMixin, TransactionBlocksMixin,
AutocompleteMixin, Widget)` — deliberately thin itself; most of its
effective API comes from the four mixins documented in their own sections
below (Module Size Rule split — see `dev-docs/architecture.md`).

```python
class JournalEditor(...):
    def __init__(self, journal_path: Path, start_line: int | None = None) -> None: ...

    class SaveCompleted(Message):
        """Posted after a successful Ctrl+S save."""

    class FileModifiedChanged(Message):
        """Posted when the modified state changes. Carries `modified: bool`."""

    def action_save(self) -> None:
        """Ctrl+S: merge any active filter, sort by date, re-align, write to disk.

        Also calls rebuild_journal_index() (AutocompleteMixin) on success.
        """
    def action_undo(self) -> None:
        """Consults CommandHistory first; falls through to LedgerTextArea.action_undo()."""
    def action_redo(self) -> None:
        """Consults CommandHistory first; falls through to LedgerTextArea.action_redo()."""
    def action_blur_editor(self) -> None:
        """Escape: dismiss autocomplete popup, else search bar, else unfocus — in that order."""
    def action_open_search(self) -> None:
        """Ctrl+F: open the search bar, or advance to the next match if already open."""
    def action_select_all(self) -> None: ...
    def action_prev_transaction(self) -> None:
        """Shift+PageUp: previous transaction header, or previous search match if the bar is open."""
    def action_next_transaction(self) -> None:
        """Shift+PageDown: mirrors action_prev_transaction."""
    def action_cursor_to_start(self) -> None: ...
    def action_cursor_to_end(self) -> None: ...
    def action_insert_today(self) -> None: ...
```

### `DateShiftMixin` (`widgets/date_shift.py`)

```python
class DateShiftMixin:
    def action_date_shift_up(self) -> None:
        """Shift+Up: increment the date sub-field under the cursor."""
    def action_date_shift_down(self) -> None:
        """Shift+Down: decrement. Both: header or P-directive date; expands
        an unpadded date (e.g. "2026-9-1") to zero-padded form on first use.
        Falls through to text selection when the cursor isn't on a date field.
        """
```

Also exports pure helpers: `_shift_date_str`, `_date_subfield_at_col`,
`_normalize_date_str`, and the regexes `_TXN_HEADER_RE`,
`_PRICE_DIRECTIVE_RE`, `_DATE_PARSE_RE` — see the module for full
docstrings/regex-doc-comments.

### `TransactionBlocksMixin` (`widgets/transaction_blocks.py`)

```python
class TransactionBlocksMixin:
    def action_toggle_cleared(self) -> None:
        """Ctrl+R: 3-state cycle on one header, or bulk-toggle over a multi-block selection."""
    def action_select_transaction_block(self) -> None:
        """Ctrl+T: select the block at the cursor; each repeated press extends to the next block."""
    def action_autofill(self) -> None:
        """Ctrl+G: duplicate the current (or all selected) transaction block(s) to end of file, today's date."""
```

Also exports `_find_transaction_block(lines, row) -> tuple[int, int]` and
`_cycle_flag_in_header(line) -> str` (pure functions).

### `ViewFilterMixin` (`widgets/view_filter.py`)

```python
class ViewFilterMixin:
    def action_cycle_view_filter(self) -> None:
        """Ctrl+L: All -> Cleared -> Unreconciled -> All. Combines (AND)
        with any active Ctrl+O criteria filter rather than replacing it."""

    def apply_criteria_filter(self, predicate: Callable[[object], bool]) -> None:
        """Set (or replace) the Ctrl+O criteria predicate. Combines (AND)
        with any active Ctrl+L cleared/uncleared mode rather than
        replacing it."""

    def clear_criteria_filter(self) -> None:
        """Remove just the Ctrl+O criteria predicate. Any active Ctrl+L
        mode is left untouched. No-op if no criteria filter is active."""

    @property
    def _filter_is_active(self) -> bool:
        """True if either dimension (Ctrl+L mode != 0, or a Ctrl+O
        predicate) is currently filtering the view."""
```

Ctrl+L and Ctrl+O share one parse→hide→merge-edits-back→restore engine.
They are two INDEPENDENT dimensions that combine with AND when both are
active (e.g. "Cleared only" narrowed further by a Ctrl+O account filter) —
reversed from Phase 3's original mutually-exclusive "replace" semantics
per UAT feedback; see `planning/next-release-phase-plan.md`'s Phase 3
"Interaction with Ctrl+L" note for the history. `ViewFilterBar.set_combined()`
composes the status-bar label from both dimensions.

### `AutocompleteMixin` (`widgets/autocomplete.py`)

```python
class AutocompleteMixin:
    def rebuild_journal_index(self) -> None:
        """Recompute self._journal_index from the current TextArea text."""

    def action_autocomplete(self) -> None:
        """Tab: insert/cycle a completion (bash-style — see module docstring
        for why not an Up/Down dropdown), or fall through to normal
        focus-cycling when there's nothing completable at the cursor."""

    def dismiss_autocomplete(self) -> None:
        """Hide the suggestion bar and forget the current anchor, if any."""
```

Also exports the pure `_completion_context(line, col, kind) ->
tuple[str, str, int] | None` — decides whether/what to complete at a
cursor position; see its docstring for the exact (index_kind, partial,
start_col) contract.

### `ViewFilterBar` (`widgets/view_filter_bar.py`)

```python
class ViewFilterBar(Widget):
    """1-row status bar describing the active Ctrl+L mode and/or Ctrl+O
    criteria filter — the two combine, so this may describe both at once."""
    def set_mode(self, mode: int) -> None:
        """Update the label for a fixed Ctrl+L mode (0=All, 1=Cleared, 2=Unreconciled)."""
    def set_label(self, text: str) -> None:
        """Set an arbitrary label directly."""
    def set_combined(self, mode: int, criteria_active: bool) -> None:
        """Compose one label from both the Ctrl+L mode and whether Ctrl+O
        is also active — what ViewFilterMixin actually calls after any
        change to either dimension."""
```

### `AutocompletePopup` (`widgets/autocomplete_popup.py`)

```python
class AutocompletePopup(Widget):
    """Bottom-docked, non-focusable Tab-autocomplete suggestion bar (can_focus = False)."""
    def show(self, candidates: list[str]) -> None:
        """Reveal with candidates, selecting the first. No-op if candidates is empty."""
    def hide(self) -> None:
        """Hide the bar and clear its candidates."""
    def cycle_next(self) -> str | None:
        """Advance to the next candidate (wrapping), return it, or None if none."""
    @property
    def is_showing(self) -> bool: ...
    @property
    def selected_candidate(self) -> str | None: ...
    @property
    def candidates(self) -> list[str]: ...
```

## `ledgerkit_editor.widgets.FilterPopup`

```python
class FilterPopup(Widget):
    """Ctrl+O overlay — date-range, account, and payee filter fields."""

    class FilterApplied(Message):
        """Carries a pre-validated predicate (Callable[[Transaction], bool]),
        built via query_match.build_transaction_predicate() — not a raw Query.
        A DateParseError or re.error is caught and notified inside apply_filter()
        itself, before this is ever posted."""

    class FilterCleared(Message):
        """Posted by the Clear button."""

    def apply_filter(self) -> None:
        """Read field values, build+validate a predicate, post FilterApplied.
        Empty fields become None (no filter on that dimension)."""
```

---

## `ledgerkit_editor.widgets.search_bar`

### `_build_offset_table`

```python
def _build_offset_table(text: str) -> list[int]:
    """Return a list of byte-start offsets for every line in text.

    Index i holds the character offset of line i within the full text.
    Used for O(log N) offset→(row, col) conversion via bisect.
    """
```

### `_offset_to_location`

```python
def _offset_to_location(
    offset: int, table: list[int]
) -> tuple[int, int]:
    """Convert a flat character offset to a (row, col) location.

    Args:
        offset: character offset within the document.
        table: offset table returned by _build_offset_table().

    Returns:
        (row, col) tuple (0-indexed).
    """
```

### `SearchBar`

```python
class SearchBar(Widget):
    """Incremental search bar docked inside JournalEditor.

    Hidden (display: none) by default; shown by open_bar().
    """

    def open_bar(self, initial_direction: int = 1) -> None:
        """Show the bar, focus the input, and begin searching.

        Args:
            initial_direction: 1 for forward (Ctrl+F), -1 for reverse (Ctrl+Shift+F).
        """

    def dismiss(self) -> None:
        """Clear highlights and hide the bar."""

    def advance(self, direction: int = 1) -> None:
        """Move to the next (direction=1) or previous (direction=-1) match."""

    def advance_to_transaction(self, direction: int = 1) -> None:
        """Jump to the next transaction block that contains a match (Alt+F3)."""

    def action_copy_match(self) -> None:
        """Ctrl+C: copy the current match's text to the clipboard.

        Only reached when the focused #search-input Input has no selection
        of its own (Input.action_copy() raises SkipAction in that case).
        Deliberately non-priority — see the module's BINDINGS comment.
        No-op if there's no active match.
        """
```

---

## `ledgerkit_editor.widgets.ledger_textarea`

### `LedgerTextArea`

```python
class LedgerTextArea(TextArea):
    """TextArea subclass with hledger journal syntax highlighting and search.

    Drop-in replacement for TextArea. Overrides _build_highlight_map()
    (private Textual 8.2.5 API) to inject ledger token spans and search
    highlight spans into self._highlights on every edit.
    """

    def set_search_matches(
        self,
        matches: list[tuple[tuple[int, int], tuple[int, int]]],
        current: int,
    ) -> None:
        """Update search highlight state and repaint the widget.

        Args:
            matches: list of ((start_row, start_col), (end_row, end_col)) pairs.
            current: index of the focused match, or -1 to clear.
        """

    def _rebuild_ledger_theme(self) -> None:
        """Activate the correct TextAreaTheme for the current app theme.

        Uses the static Monokai Pro TextAreaTheme when app.theme == "monokai-pro",
        otherwise builds a generic bridge theme from the app CSS variables.
        """
```

---

## `ledgerkit_editor.highlighting`

### `LineKind`

```python
class LineKind(Enum):
    """Classification of a single journal line."""
    BLANK, COMMENT, DIRECTIVE, XACT_HEADER, POSTING, UNKNOWN
```

### `LineInfo`

```python
@dataclass
class LineInfo:
    """Pre-computed classification and clearing state for one journal line."""
    kind: LineKind
    cleared: bool = False
    pending: bool = False
```

### `LedgerHighlighter`

```python
class LedgerHighlighter:
    """Regex-based hledger syntax highlighter (no Textual imports).

    Single O(N) scan via invalidate(); per-line queries are O(1).
    """

    def invalidate(self, text: str) -> None:
        """Re-scan the full document and cache LineInfo for every line."""

    def get_highlights(
        self, line_index: int, line_text: str
    ) -> list[tuple[int, int | None, str]]:
        """Return (start_col, end_col, token_name) spans for one line.

        end_col is None to mean "to end of line" (used for block overlays).
        Column offsets are Unicode codepoint positions.
        """
```

### `build_textarea_theme`

```python
def build_textarea_theme(app: App) -> TextAreaTheme:
    """Build a TextAreaTheme from the active app theme's CSS variables.

    Reads app.get_css_variables() (keys without '$' prefix) and maps each
    ledger token to the appropriate colour role. Falls back to '#888888'
    for text and 'transparent' for background if a variable is absent.

    Returns:
        A TextAreaTheme named "ledger".
    """
```

---

## `ledgerkit_editor.themes`

### `register_all`

```python
def register_all(app: App, ledger_textarea: LedgerTextArea) -> None:
    """Register all bundled app themes and TextAreaThemes.

    Must be called before setting app.theme to any bundled theme name.
    """
```

### `BUNDLED_THEMES`

```python
BUNDLED_THEMES: list[Theme]
```
All bundled Textual `Theme` objects (currently: `[MONOKAI_PRO_APP_THEME]`).

### `TEXTAREA_THEME_MAP`

```python
TEXTAREA_THEME_MAP: dict[str, str]
```
Maps app theme name → TextAreaTheme name for the static (non-bridge) path.
Currently: `{"monokai-pro": "monokai-pro-ledger"}`.
