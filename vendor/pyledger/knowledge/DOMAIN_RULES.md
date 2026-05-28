# Domain Rules

Tacit knowledge about the hledger journal format and PyLedger's implementation that Claude cannot infer from code alone.

---

## Double-space separator is mandatory between account name and amount

Postings use two or more spaces (or a tab) to separate the account name from the amount. A single space is not sufficient.

```
    expenses:food  £30.00   ← valid (2+ spaces)
    expenses:food £30.00    ← invalid (1 space — rejected by _TWO_SPACE_SEP)
```

**Why it matters:** Account names may legitimately contain spaces (e.g. `assets:joint account`). The double-space is the only unambiguous delimiter.

**Implication:** Never use a single space between account and amount in fixtures or test strings.

---

## At most one elided amount per transaction block

Exactly one posting per transaction may omit its amount. The parser infers the missing amount so the transaction balances to zero. Two or more elided amounts are ambiguous and raise `ParseError`.

**Implication:** Always provide explicit amounts in test fixtures except when specifically testing elision.

---

## `Posting.amount` is `Amount | None` by design

`None` is not an error state — it means the posting has an intentionally elided amount (to be inferred at check/report time). Code accessing `.quantity` or `.commodity` must guard with `assert amt is not None` or an equivalent.

---

## P directive records a price at a point in time — it is not a global rate

`P 2024-01-01 € $1.20` means "on 2024-01-01, one € was worth $1.20". It does NOT mean all €-denominated amounts throughout the journal are worth $1.20. Commodity valuation logic must use the *closest preceding date* for a given commodity pair.

**Scope:** P directives are file-local. Whether they propagate through `include` is TBD for Milestone 2.

---

## Balance rule: all postings in a transaction must sum to zero per commodity

A transaction is balanced when the algebraic sum of all posting amounts (per commodity) is zero. This is enforced by `checks.check_autobalanced`, not by the parser.

**Elided amount rule:** If one posting has no amount, its amount is inferred as the negation of the sum of all other postings. This only works when all other postings share a single commodity.

---

## `strict` mode requires ALL accounts AND commodities to be declared

Under `-s`/`--strict`, every account name appearing in a posting must have a matching `account` directive, and every commodity symbol must have a matching `commodity` directive. The check stops at the first failure and reports it with file path and line number.

**Implication:** Strict-mode fixtures (`tests/fixtures/strict_valid.journal`) must declare every account and commodity used.

---

## Account names use `:` as a hierarchy separator

`assets:bank:checking` has three segments. The `account_depth` stat counts colon-delimited segments. Leaf uniqueness (`uniqueleafnames` check) compares only the last segment.

---

## `decimal-mark` changes the parser mode for subsequent postings only

After `decimal-mark ,`, amounts must use European format (`1.234,56`). The change is not retroactive. Mixing formats within a file after the directive is a parse error.

**Default:** Period decimal (`1234.56`). Explicit `decimal-mark .` resets to default.

---

## Commodity symbols may be prefix or suffix

`£30.00` — prefix symbol (`£`), no space.
`30.00 EUR` — suffix symbol (`EUR`), one space separator.
Both are valid; the commodity value in `Amount.commodity` is just the symbol string without spaces.

---

## Comment indentation rule: column-0 vs. indented

There are two distinct comment forms inside a journal, and **indentation** is the discriminator:

| Form | First char | Indent? | Meaning |
|---|---|---|---|
| Top-level comment | `#` or `;` | No (column 0) | Always ignored; never captured into any data structure |
| Follow-on comment | `;` | Yes (leading whitespace) | Captured as `inline_comment` on the preceding transaction or posting |
| `#` inside a txn | `#` | Yes | Updates `source_span.end_line` only; text NOT captured |

**Key invariant:** A column-0 `;` or `#` is ALWAYS a top-level comment — even if it appears with no blank line between two transactions. It must never be captured as a follow-on comment for the previous transaction's last posting.

**Why it matters:** The parser uses `lstrip()` to strip whitespace before the startswith check, so it must also test `line[0:1].isspace()` before deciding to capture. Without this check a column-0 `;` between two adjacent transactions would incorrectly appear in the preceding posting's `inline_comment`.

**Inline `;` (same-line) is separate:** A `;` on the same line as a transaction header or posting is always captured regardless of indentation. This is handled in `_parse_txn_header` and `_parse_posting`, not in the standalone-comment branch.

---

## `include` directive: glob vs explicit path error handling

- **Explicit path** (no glob characters): raises `FileNotFoundError` if file does not exist.
- **Glob pattern** (`*`, `**`, `?`, `[range]`): silently produces no entries if no files match — this is NOT an error.

This matches the hledger 1.52 `include` spec.
