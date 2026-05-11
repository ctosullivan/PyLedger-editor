"""Token name constants for hledger journal syntax highlighting.

Names follow the tree-sitter dot-hierarchy convention so they are
forward-compatible if an hledger tree-sitter grammar is added later.
"""

# Transaction header tokens
DATE = "ledger.date"
FLAG_CLEARED = "ledger.flag.cleared"
FLAG_PENDING = "ledger.flag.pending"
CODE = "ledger.code"
PAYEE_UNCLEARED = "ledger.payee.uncleared"
PAYEE_CLEARED = "ledger.payee.cleared"
PAYEE_PENDING = "ledger.payee.pending"
NOTE = "ledger.note"

# Posting tokens
ACCOUNT = "ledger.account"
AMOUNT_POSITIVE = "ledger.amount.positive"
AMOUNT_NEGATIVE = "ledger.amount.negative"
AMOUNT_ZERO = "ledger.amount.zero"
COMMODITY = "ledger.commodity"
POSTING_NOTE = "ledger.posting.note"

# Line-level tokens
COMMENT = "ledger.comment"
DIRECTIVE = "ledger.directive"
DIRECTIVE_ARG = "ledger.directive.arg"

# Block-level overlay tokens (applied as background colour to entire lines)
BLOCK_CLEARED = "ledger.block.cleared"
BLOCK_PENDING = "ledger.block.pending"
BLOCK_UNCLEARED = "ledger.block.uncleared"
