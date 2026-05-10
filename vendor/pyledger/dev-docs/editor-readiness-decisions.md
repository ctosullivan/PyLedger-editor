# Editor-Readiness Design Decisions

Decisions made during the implementation of editor-readiness features
(SourceSpan, writer.py, editor_model.py). Non-obvious judgment calls that
could not be inferred from the code alone.

---

## 1. `compare=False` on all new span/comment fields

**Decision**: `source_span`, `raw_text`, and `inline_comment` on `Transaction`, and
`inline_comment` on `Posting`, all use `field(default=None, repr=False, compare=False)`.

**Why**: These are metadata fields added for editor tooling. Existing tests construct
`Transaction` and `Posting` objects programmatically and may compare them against
parsed objects using `==`. Using `compare=False` ensures none of these new fields
participate in equality checks, so no existing test can silently break. The fields are
intentionally excluded from identity — two transactions representing the same journal
entry should be equal regardless of where they were loaded from.

---

## 2. `Transaction.inline_comment` added alongside `comment`

**Decision**: Both `Transaction.comment: str = ""` and
`Transaction.inline_comment: str | None = None` are present. The parser sets both;
`checks.py`'s `_fmt_txn_header` continues to use `comment`; `writer.py` uses
`inline_comment`.

**Why**: `comment` pre-exists with `str` type and `""` default. It is used by
`_fmt_txn_header` in `checks.py` for source-context error messages. Renaming or
retyping it would silently break any external code that accesses `txn.comment`
directly. The new `inline_comment: str | None` field gives editor tools a clean
None-sentinel API (distinguishing "no comment" from an empty comment), while the
existing `comment` field remains unchanged for backward compatibility.

**Rejected alternative**: Rename `comment` → `inline_comment` and update all call
sites. Rejected because `dev-docs/api-spec.md` treats `comment` as a public field
and changes to it require explicit user approval.

---

## 3. `EditorDocument` uses `parse_string` directly, not `load_journal`

**Decision**: `EditorDocument.__init__` reads the file with `Path.read_text()` and
calls `parse_string(text, source_file=abs_path)` directly. It does NOT call
`loader.load_journal()`.

**Why**: `load_journal` merges all `include` directives into a single expanded text
before calling `parse_string`. The line numbers in `source_span` would then reference
lines in the merged text, not the original file. Since `EditorDocument.update_transaction`
and `delete_transaction` operate on `self.lines` (the actual file content) using
`source_span`, merged-text line numbers would be wrong for any file that contains
`include` directives.

**V1 limitation**: Include directives in the edited file are silently ignored by
`parse_string`; they appear as unrecognised lines and are skipped. A full
include-aware editor would need either a multi-file document model or a way to pass
`line_map` metadata from `_expand_includes` into the parser — both are out of scope
for v1.

---

## 4. `loader.py` passes `source_file` to `parse_string`

**Decision**: `load_journal` now calls `parse_string(expanded, source_file=str(abs_path))`.

**Why**: For single-file journals (no includes), every `source_span.file` is correctly
set to the absolute path. This is the common case and gives correct, useful information
to callers that inspect spans.

**V1 limitation**: For journals with `include` directives, the merged text is parsed
as one unit. All transactions — including those from included files — report
`source_span.file = abs_path` (the root file). Their line numbers reference lines in
the merged text rather than the original included files. The existing `line_map`
infrastructure in `loader.py` has the per-line attribution, but threading it into
`_parse_string_impl` would require a larger architectural change.

---

## 5. `journal_to_text` omits directives

**Decision**: `journal_to_text` serialises only `Transaction` objects. Directives
(`account`, `commodity`, `payee`, `P`) are not included in the output.

**Why**: Directives are stored as plain string lists in `Journal` (e.g.
`journal.declared_accounts`), not as structured objects with position information.
Re-serialising them faithfully — preserving original formatting, comment text,
subdirectives, and order relative to transactions — would require the same kind of
source-position tracking we just added for transactions, which is a larger
undertaking. The primary use case for `journal_to_text` is round-trip smoke testing
and content reconstruction where directives can be managed separately.

---

## 6. Span-refresh uses arithmetic delta, not full re-parse

**Decision**: `update_transaction` and `delete_transaction` in `EditorDocument`
compute a line-count delta and shift all subsequent `source_span` values
arithmetically.

**Why**: Re-parsing the whole file after each mutation would be simpler but violates
the spec requirement ("must not re-parse the whole file"). Full re-parse also loses
the identity of in-memory `Transaction` references (which the editor frontend holds
onto), making update/delete harder to implement correctly. Arithmetic delta is O(n)
in the number of transactions and correct as long as spans are consistent before the
mutation — which they are by invariant.

**Edge case note**: If two mutations are applied in rapid succession and the first
mutation corrupts `self.lines` (e.g. a bug in serialisation), the second mutation's
span calculations will be wrong. The intended usage pattern is one mutation → save or
reload → next mutation, which keeps the invariant intact.

---

## 7. Standalone `;` comment lines in transaction blocks

**Decision**: Standalone `;` comment lines within a transaction block (between
postings) are attached to the most recently seen `Posting.inline_comment` (with `\n`
separator), or to `Transaction.inline_comment` if no posting has been seen yet.
`#`-led comment lines inside a block update `end_line` (included in `raw_text`) but
their text is not attached.

**Why**: hledger's format spec treats `;` as the standard in-block comment delimiter.
Attaching to the preceding posting mirrors how most readers mentally associate a
comment with the line above it. Attaching to the transaction when before the first
posting is the only sensible alternative (there is no preceding posting). `#` is
supported for line comments outside blocks but is not the standard in-block delimiter
per hledger's own documentation, so its text is not attached.
