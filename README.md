# Ledger Editor

> **Early beta — use with caution.** This software is under active development and
> **may corrupt your journal files**. Always keep a backup before editing. Do not
> use on irreplaceable data without a recovery plan.

A terminal-based, keyboard-driven plain-text [hledger](https://hledger.org/) journal
editor built with [Textual](https://textual.textualize.io/) and
[PyLedger](https://github.com/ctosullivan/PyLedger).

## Features

- Full-screen text editor with hledger syntax highlighting (dates, payees, accounts,
  amounts, commodities, comments, directives)
- Monokai Pro default theme; runtime theme switching supported
- Incremental search with match highlighting (`Ctrl+F`, `Shift+PgUp/Down`)
- View filter — show all / cleared-only / unreconciled-only transactions (`Ctrl+L`)
- Transaction block selection and duplication (`Ctrl+T`, `Ctrl+G`)
- Cleared status toggle — single transaction (3-state cycle) and bulk selection (`Ctrl+R`)
- Insert today's date at cursor (`Ctrl+D`)
- Save with date-sort and whitespace re-alignment (`Ctrl+S`)
- Transaction filter popup (`Ctrl+O`) — **UI stub only; criteria filtering not yet implemented**
- Command palette (`Ctrl+P`)

## Installation

### From GitHub (recommended while in beta)

```bash
git clone https://github.com/ctosullivan/PyLedger-editor.git
cd PyLedger-editor

python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # macOS / Linux

# PyLedger must be installed from the vendor checkout —
# the 'pyledger' package on PyPI is a stub and will not work.
pip install --upgrade pip
pip install -e vendor/pyledger/

# Install Ledger Editor and its remaining dependencies
pip install textual==8.2.5 pytest pytest-asyncio
pip install -e .

# Launch
ledger-editor path/to/my.journal
```

### Requirements

- Python 3.00+
- textual 8.2.5 (installed automatically via `pip install -e .`)
- pyledger 0.5.0 (installed manually from `vendor/pyledger/` — see above)

## Journal File Resolution

The editor resolves the journal file in this order:

1. Path passed as a command-line argument
2. `$LEDGER_FILE` environment variable
3. `~/.hledger.journal` default
4. Interactive prompt on launch (if none of the above resolve)

## Keyboard Shortcuts

See [docs/shortcuts.md](docs/shortcuts.md) for the full reference.

## Development

See [CONTRIBUTING.md](CONTRIBUTING.md) for setup instructions and the
PyLedger vendor update workflow.

## Roadmap

See [ROADMAP.md](ROADMAP.md) for planned features and current development status.
