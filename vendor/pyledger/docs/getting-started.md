# Getting Started with PyLedger

PyLedger is a Python tool for plain-text double-entry accounting, compatible
with the [hledger](https://hledger.org) journal format.

---

## Requirements

- Python 3.10 or later

Check your version:

```bash
python --version
```

---

## Installation

Clone the repository and install in editable mode:

```bash
git clone https://github.com/ctosullivan/PyLedger.git
cd PyLedger
pip install -e .
```

Verify the installation:

```bash
PyLedger --version
```

---

## Your First Journal File

Create a file called `myledger.journal`:

```
2024-01-01 Opening balance
    assets:bank:checking    £1000.00
    equity:opening-balances

2024-01-10 Supermarket
    expenses:food           £45.00
    assets:bank:checking
```

Each transaction starts with a date and description. Indented lines are
postings (account + amount). One posting per transaction may omit its amount —
PyLedger infers it from the others.

---

## Run Your First Command

```bash
PyLedger print myledger.journal
```

This prints all transactions in a readable format. See [usage.md](usage.md)
for all available commands.

---

## What's Next

- [usage.md](usage.md) — all CLI commands with examples
- [journal-format.md](journal-format.md) — full journal syntax reference
- [python-api.md](python-api.md) — use PyLedger as a Python library
