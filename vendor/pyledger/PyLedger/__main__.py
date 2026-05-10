"""Enables `python -m PyLedger` invocation.

Usage:
    python -m PyLedger <command> <journal-file>

This is equivalent to running the `PyLedger` CLI entry point directly.
"""

import sys
from PyLedger.cli import main

sys.exit(main())
