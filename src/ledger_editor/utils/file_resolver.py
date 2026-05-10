"""Journal file resolution following PyLedger's hledger-compatible order.

Resolution priority (matching PyLedger cli.py behaviour):
  1. CLI argument passed to the editor
  2. $LEDGER_FILE environment variable
  3. ~/.hledger.journal default fallback
  4. None — caller must prompt the user

See also: vendor/pyledger/PyLedger/cli.py for the reference implementation.
"""

from __future__ import annotations

import os
from pathlib import Path

__all__ = ["resolve_journal_file"]

_DEFAULT_JOURNAL = Path.home() / ".hledger.journal"


def resolve_journal_file(cli_path: str | None) -> Path | None:
    """Return the resolved journal file path, or None if none is found.

    Applies the hledger-compatible resolution order:
      1. cli_path argument (if provided and the file exists)
      2. $LEDGER_FILE environment variable (if set and the file exists)
      3. ~/.hledger.journal (if it exists)
      4. None

    Args:
        cli_path: Raw path string from the command-line argument, or None.

    Returns:
        Absolute Path to the journal file, or None when no file is found.
    """
    if cli_path is not None:
        candidate = Path(cli_path).expanduser().resolve()
        if candidate.exists():
            return candidate

    env_path = os.environ.get("LEDGER_FILE")
    if env_path:
        candidate = Path(env_path).expanduser().resolve()
        if candidate.exists():
            return candidate

    if _DEFAULT_JOURNAL.exists():
        return _DEFAULT_JOURNAL.resolve()

    return None
