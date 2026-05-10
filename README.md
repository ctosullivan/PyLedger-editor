# Ledger Editor

A terminal-based, keyboard-driven plain-text ledger editor built with
[Textual](https://textual.textualize.io/) and
[PyLedger](https://github.com/ctosullivan/PyLedger).

## Features (planned)

- Persistent account-balance sidebar (tree view)
- In-place transaction editing with live validation
- Smart date parsing and autocomplete
- MS Office / Excel keyboard conventions
- Emacs Ledger-mode keyboard conventions
- Transaction filter popup (`Ctrl+Shift+F`)

## Quick Start

```bash
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # macOS / Linux
pip install -r requirements.txt
python -m ledger_editor path/to/my.journal
```

Or install as a package:

```bash
pip install -e .
ledger-editor path/to/my.journal
```

## Journal File Resolution

The editor resolves the journal file in this order:

1. Path passed as a command-line argument
2. `$LEDGER_FILE` environment variable
3. `~/.hledger.journal` default
4. Interactive prompt on launch (if none of the above exist)

## Keyboard Shortcuts

See [docs/shortcuts.md](docs/shortcuts.md) for the full reference.

## Development

See [CONTRIBUTING.md](CONTRIBUTING.md) for setup instructions and the
PyLedger vendor update workflow.

## Requirements

- Python 3.11+
- textual 8.2.5
- pyledger 0.5
