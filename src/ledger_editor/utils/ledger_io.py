"""Journal file I/O via PyLedger.

Thin wrappers around PyLedger's public API so the rest of the editor can
call load/save without directly coupling to PyLedger import paths.

Key PyLedger types used here:
  - PyLedger.load(path)              → Journal  (alias for loader.load_journal)
  - PyLedger.EditorDocument(path)   → in-memory editable document
  - PyLedger.journal_to_text(j)     → str
  - PyLedger.transaction_to_text(t) → str

Always consult vendor/pyledger/dev-docs/api-spec.md before extending this
module. Never assume the PyLedger API — read the spec first.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from PyLedger.models import Journal

__all__ = ["load_journal", "save_journal"]


def load_journal(path: Path) -> "Journal":
    """Load a journal file and return a parsed Journal object.

    Delegates to PyLedger.load() which handles include directives, glob
    expansion, and circular-include detection.

    Args:
        path: Absolute path to the .journal or .ledger file.

    Returns:
        Parsed Journal containing all transactions, prices, and declared
        accounts/commodities/payees.

    Raises:
        FileNotFoundError: if the path does not exist.
        PyLedger.parser.ParseError: if the file content is malformed.
    """
    import PyLedger  # noqa: PLC0415 — deferred to avoid startup cost
    return PyLedger.load(path)


def save_journal(path: Path, journal: "Journal") -> None:
    """Serialise a Journal to the given path.

    Uses PyLedger.journal_to_text() for serialisation. Note: directives
    (account, commodity, payee, P) are not round-tripped by journal_to_text
    in PyLedger v0.5.0 — only transactions are serialised.

    Args:
        path:    Absolute path to write the journal file.
        journal: Journal object to serialise.
    """
    import PyLedger  # noqa: PLC0415 — deferred to avoid startup cost
    text = PyLedger.journal_to_text(journal)
    path.write_text(text, encoding="utf-8")
