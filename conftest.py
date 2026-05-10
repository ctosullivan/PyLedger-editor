"""Pytest root conftest — ensures vendor/pyledger is on sys.path.

The PyLedger package lives at vendor/pyledger/pyLedger/. On Windows (case-
insensitive filesystem) this is importable as 'import PyLedger'. This conftest
adds vendor/pyledger/ to sys.path before any tests run.
"""

import sys
from pathlib import Path

_VENDOR_PATH = str(Path(__file__).parent / "vendor" / "pyledger")
if _VENDOR_PATH not in sys.path:
    sys.path.insert(0, _VENDOR_PATH)
