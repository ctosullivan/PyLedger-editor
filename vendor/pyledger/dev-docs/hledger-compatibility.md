# Hledger Compatibility

Reference: https://hledger.org/1.52/hledger.html

This document tracks which hledger format features are in scope for **v1** of
PyLedger, which are explicitly out of scope, and which are undecided.

---

## Supported File Formats

PyLedger accepts the following file extensions. This is a deliberate subset of
what hledger 1.52 supports (full comparison below).

| Extension | Description |
|---|---|
| `.journal` | Primary hledger journal format — fully supported |
| `.ledger` | Ledger-CLI compatible journal syntax — supported to the same degree as `.journal`; both use identical parsing in PyLedger v1 |

### Deviation from hledger 1.52

hledger 1.52 supports seven format families. The table below documents every
format and PyLedger's stance. Reference: https://hledger.org/1.52/hledger.html#data-formats

| hledger 1.52 format | Extensions | PyLedger v1 |
|---|---|---|
| journal | `.journal` `.j` `.hledger` `.ledger` | **Supported** for `.journal` and `.ledger` only; `.j` and `.hledger` aliases are **not** accepted |
| timeclock | `.timeclock` | **Not supported** — out of scope |
| timedot | `.timedot` | **Not supported** — out of scope |
| csv | `.csv` | **Not supported** — out of scope |
| ssv | `.ssv` | **Not supported** — out of scope |
| tsv | `.tsv` | **Not supported** — out of scope |
| rules | `.rules` | **Not supported** — out of scope |

**Note on `.ledger`:** PyLedger does not aim for full Ledger-CLI compatibility.
The `.ledger` extension is accepted because the hledger-compatible subset of
Ledger syntax is identical to `.journal` syntax within v1 scope. Ledger-specific
features (e.g. automated transactions, periodic transactions, value expressions)
remain out of scope and will raise `ParseError` or be silently ignored per the
rules in the "Out of Scope" table below.

---

## Transaction Block Structure

A transaction block is the fundamental unit of a journal file.

```
; Transaction block — annotated

2024-01-15 * (INV-42) Groceries  ; comment   ← block BEGINS here (date required)
│           │  │        │          │
│           │  │        │          └─ inline comment          (optional)
│           │  │        └──────────── description             (optional, free text)
│           │  └───────────────────── transaction code        (optional, parenthesised)
│           └──────────────────────── status: * cleared / ! pending (optional)
└──────────────────────────────────── date YYYY-MM-DD         (REQUIRED - Simple Date Format)

    expenses:food:groceries   £85.40          ← posting lines (2+ space indent)
    assets:bank:checking                      ← elided amount (at most ONE per block)

                                              ← blank line ENDS the block (or EOF)
```

**Delimiter rules:**
- A block **begins** on any non-indented line whose first token is a valid simple
  date: `\d{4}[-/.]\d{1,2}[-/.]\d{1,2}` (full date) or `\d{1,2}[-/.]\d{1,2}`
  (year-omitted); all three separators (`-`, `/`, `.`) and optional leading zeros
  are accepted, consistent with the Simple date spec in the In Scope table
- A block **ends** on the first blank line that follows the header, or at end of file
- The field order on the header line is fixed: `date [flag] [(code)] [description] [; comment]`
- Posting lines are generally identified by 2+ leading spaces (or a tab), however this is not a requirement
- Within a posting line, the account name and amount **must** be separated by
  two or more spaces; a single space is treated as part of the account name
  (e.g. `expenses:fun money`) — a `ParseError` is raised if no double-space
  separator is found and no amount can be parsed
- Exactly **one** posting per block may omit its amount (the *elided* posting); two or
  more elided amounts in the same block is a `ParseError`

---

## In Scope (v1)

### Transactions

| Feature | Example | Notes |
|---|---|---|
| Simple date | `2024-01-15`, `2024/1/15`, `2024.1.15`, `1/15` | Separators: `-` `/` `.`; leading zeros optional; year may be omitted (inferred from current date) |
| Description | `2024-01-15 Groceries` | Free text after the date |
| Cleared flag | `2024-01-15 * Groceries` | `*` = cleared |
| Pending flag | `2024-01-15 ! Groceries` | `!` = pending |
| Transaction code | `2024-01-15 (INV-42) Groceries` | Parenthesised string before description |
| Postings | `  expenses:food  £30.00` | Two-space indent; account and amount **must** be separated by two or more spaces |
| Elided amount | `  assets:checking` | One posting per transaction may omit amount; no separator required when amount is absent |

### Account Names

| Feature | Example | Notes |
|---|---|---|
| Hierarchical names | `expenses:food:restaurants` | Colon-separated segments |
| Mixed case | `Assets:Bank` | Case-sensitive |
| Spaces in names | `expenses:fun money` | Supported |

### Amounts

| Feature | Example | Notes |
|---|---|---|
| Prefixed symbol | `£30.00`, `$10` | Symbol before quantity |
| Suffixed symbol | `30.00 EUR` | Symbol after quantity (space optional) |
| Negative amounts | `-£5.00` | Leading minus |
| Decimal separator | `1,234.56` | Comma thousands separator, period decimal |
| No decimal | `£100` | Integer quantities |

### Comments

| Feature | Example | Notes |
|---|---|---|
| Whole-line `;` | `; this is a comment` | Any line whose first non-space character is `;` |
| Whole-line `#` | `# another comment` | Any line whose first non-space character is `#` |
| Inline `;` on transaction | `2024-01-15 Desc  ; comment` | `;` after description; captured in `Transaction.comment` |
| Inline `;` on posting | `  expenses:food  £30  ; note` | `;` after amount; stripped during parsing |
| Follow-on comment line | `    ; continued note` | Indented line starting with `;` inside a transaction block; silently skipped |
| Block comment | `comment` / `end comment` | All lines between the two directives are skipped; unclosed block runs to EOF |

### Directives

| Feature | Syntax | Notes |
|---|---|---|
| P directive | `P DATE COMMODITY PRICE` | **[IMPLEMENTED]** Market price declaration; stored in `Journal.prices` as `PriceDirective` objects. DATE uses simple date format; COMMODITY1SYMBOL is the commodity being priced; COMMODITY2AMOUNT is the price as an amount (prefix or suffix symbol). Inline comments (`  ;`) stripped. Scope: prices propagate through `include` naturally (text-expansion strategy). Commodity valuation using stored prices is in scope for Milestone 2. Reference: https://hledger.org/1.52/hledger.html#p-directive |
| alias directive | `alias OLD=NEW` / `alias /REGEX/=REPLACEMENT` / `end aliases` | **[IMPLEMENTED]** Account name rewriting applied at parse time. Basic aliases match `OLD` as an exact account name or as a colon-delimited prefix (e.g. `alias checking = assets:bank` rewrites `checking` and `checking:savings`). Regex aliases substitute any matching substring (case-insensitive per hledger spec; backreferences `\1` supported). Multiple aliases accumulate; `end aliases` clears all active rules. Aliases also rewrite account names in `account` directives. Inline comments using `  ;` or `  #` (two-space rule) are stripped from alias bodies. **Application order:** most-recently-defined alias applied first (LIFO), matching hledger behaviour. **Scoping deviation:** because `include` is handled as a separate `parse_string()` call in `loader.py`, alias rules defined in one file do NOT propagate into included files — a deviation from hledger 1.52 (where aliases propagate into includes). Command-line `--alias` option deferred to a future milestone. Reference: https://hledger.org/1.52/hledger.html#alias-directive |
| include directive | `include other.journal` | **[IMPLEMENTED]** Embeds entries and directives from another `.journal` or `.ledger` file inline at the point of the directive; directives active before the include apply to the included file (text-expansion strategy). Path resolution: relative to containing file's directory, absolute, and `~` tilde expansion; glob patterns (`*`, `**`, `?`, `[range]`) expanded via `glob.glob(recursive=True)`; the containing file is always excluded from glob results. A glob that matches no files raises `ParseError`. Circular includes raise `ParseError`. Format prefixes (e.g. `timedot:`) raise `ParseError` — not supported in PyLedger v1. Only `.journal` and `.ledger` targets accepted (other extensions raise `ParseError`). **Dot-file glob behaviour**: uses Python `glob.glob()` defaults, which may differ from hledger 1.52 (hledger excludes dot files from `*`/`**`; Python's glob may include them). Reference: https://hledger.org/1.52/hledger.html#include-directive |
| account directive | `account assets:bank:checking` | **[IMPLEMENTED]** Declares an account name. Stored in `Journal.declared_accounts`. Inline comments (2-space + `;`) and Ledger-style indented subdirectives are stripped. Used by `check accounts` / `-s`. Account types (`type:` tag), display ordering, and tag propagation are deferred. Reference: https://hledger.org/1.52/hledger.html#account-directive |
| commodity directive | `commodity $1,000.00` / `commodity EUR` | **[IMPLEMENTED]** Declares a commodity symbol. Symbol extracted from sample amount (prefix `$`, suffix `EUR`) or bare token. Quoted symbols (`"AAPL 2023"`) supported. Indented `format` subdirectives consumed and ignored. Stored in `Journal.declared_commodities`. Used by `check commodities` / `-s`. Commodity display style and decimal-mark inference are deferred. Reference: https://hledger.org/1.52/hledger.html#commodity-directive |
| payee directive | `payee Whole Foods` | **[IMPLEMENTED]** Declares a payee name. Inline comments stripped with 2-space rule. Quoted names (`payee ""`) supported. Stored in `Journal.declared_payees`. Used by `check payees`. Reference: https://hledger.org/1.52/hledger.html#payee-directive |
| tag directive | `tag TAGNAME` | **[IMPLEMENTED]** Declares a tag name. Stored in `Journal.declared_tags`. Inline comments stripped with the 2-space rule. Indented subdirectives consumed and ignored. Used by `check tags` — deferred until inline tag-comment parsing is implemented. Reference: https://hledger.org/1.52/hledger.html#tag-directive |
| decimal-mark directive | `decimal-mark .` / `decimal-mark ,` | **[IMPLEMENTED]** Declares the decimal mark for amount parsing from this point forward in the file. Default is `.` (period). Setting `,` enables EU-style amounts where `.` = thousands separator and `,` = decimal mark (e.g. `1.234,56` → `1234.56`). Raises `ParseError` for any character other than `.` or `,`. Reference: https://hledger.org/1.52/hledger.html#decimal-mark-directive |

### Validation / Checks

PyLedger runs validation checks after parsing. Checks are grouped into tiers.

| Check | Tier | Description |
|---|---|---|
| `parseable` | basic (always) | Journal parsed without `ParseError` — trivially satisfied after load |
| `autobalanced` | basic (always) | Each transaction nets to zero per commodity; one elided posting per transaction is allowed and is inferred to balance |
| `assertions` | basic (always) | All balance assertions in posting lines pass; disable with `-I`/`--ignore-assertions` |
| `accounts` | strict (`-s`) | All posting accounts appear in `declared_accounts` |
| `commodities` | strict (`-s`) | All commodity symbols in amounts appear in `declared_commodities`; zero-amount postings (commodity `""`) are exempt |
| `payees` | other (named) | All transaction descriptions appear in `declared_payees` |
| `ordereddates` | other (named) | Transactions appear in non-decreasing date order |
| `uniqueleafnames` | other (named) | No two accounts share the same final colon-segment |

**Deferred checks** (out of scope for v1): `balanced` (exact-balance assertions on totals), `recentassertions`, `tags`.

### Balance assertions

Balance assertions appear inline after a posting amount and verify the running balance at that point in the journal. They are checked in date order (then parse order within the same date), which means transactions can be freely reordered without breaking assertions.

Supported syntax:

| Syntax | Description |
|---|---|
| `amount = EXPECTED` | Single-commodity, subaccount-exclusive |
| `amount == EXPECTED` | Sole-commodity, subaccount-exclusive (no other commodity may have a non-zero balance) |
| `amount =* EXPECTED` | Single-commodity, subaccount-inclusive (sum includes all sub-accounts) |
| `amount ==* EXPECTED` | Sole-commodity, subaccount-inclusive |

The assertion amount must be the same commodity as the posting amount (or the commodity being checked). Costs are ignored (not yet implemented). Posting status (unmarked/pending/cleared) does not affect assertions.

**Balance assignments** (`= EXPECTED` with no explicit posting amount) are parsed — the posting amount is stored as `None` — but the implied amount is **not** inferred from the assertion; this is a known limitation deferred to a future milestone.

---

## Out of Scope (v1)

These features will **not** be implemented in v1. Attempting to parse them
will either be silently ignored or raise a `ParseError` — documented per
feature below.

| Feature | hledger syntax | v1 behaviour |
|---|---|---|
| Auto postings | `= expenses:food` rules | `ParseError` |
| Periodic transactions | `~ monthly` | `ParseError` |
| Timeclock entries | `i`, `o`, `b`, `h` records | `ParseError` |
| Decimal comma | `1.234,56` (EU style) | **Supported** via `decimal-mark ,` directive — amounts parsed using comma as decimal mark |
| Secondary dates | `2024-01-15=2024-01-20` | Secondary date ignored |
| Tags | `; tag:value` | Inline tag annotations silently ignored; `tag` directive (declaring allowed tag names) is **[IMPLEMENTED]** — stored in `Journal.declared_tags` |
| Lot prices | `10 AAPL @ $150.00` | `ParseError` |
| Balance assertions | `assets:checking = £500` | **[IMPLEMENTED]** — see `assertions` check above |
| Virtual postings | `(expenses:food)` or `[expenses:food]` | `ParseError` |
| Multi-currency auto-conversion | | Not supported |

---

## Undecided / Future

- Multiple commodities in one transaction
- Account type inference from name prefixes (`assets`, `liabilities`, etc.)
- Smart dates (hledger relative date expressions such as `today`, `yesterday`,
  `last month`, `next year`) — not currently planned for v1
- Comment "other syntax" — hledger accepts additional comment introducers in
  certain contexts (e.g. `*` in org-mode files); not currently planned for v1

---

## Compatibility Notes

- PyLedger does **not** aim for 100% hledger compatibility in v1.
- The goal is to correctly parse the most common single-currency personal
  finance journal files.
- When a file is not parseable, `ParseError` should include the line number
  and a clear message explaining what was unexpected.
