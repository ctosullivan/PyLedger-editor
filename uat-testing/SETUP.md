# UAT Setup — venv + latest dev branch

How to get a clean virtual environment onto the current dev branch
(`release/1.1.0` as of this writing) for a UAT pass. Referenced by the
checklists in this folder — see [`1.1.0-filter-autocomplete-checklist.md`](1.1.0-filter-autocomplete-checklist.md)
and [`1.0.2-bug-fixes-checklist.md`](1.0.2-bug-fixes-checklist.md).

## If you already have this repo cloned, with a working `.venv`

```powershell
git fetch origin
git checkout release/1.1.0
git pull

.venv\Scripts\activate
pip install -e ".[dev]"
pytest --tb=short
```

Skip straight to "Launch the editor" below once that's green.

## Fresh clone, or your `.venv` is broken

**Symptom check first** — if activating an *existing* `.venv` and running
anything gives `Fatal error in launcher: Unable to create process using
"...\.venv\Scripts\python.exe"`, the venv was almost certainly created
before this folder was renamed (this repo used to be `PyLedger-editor`).
Windows venv launcher `.exe`s embed an **absolute path** to `python.exe`
at creation time; a folder rename breaks it silently until you try to use
it. That venv can't be repaired — delete and recreate it (steps below
already do this).

```powershell
# 1. Clone (skip if you already have the repo)
git clone https://github.com/ctosullivan/ledgerkit-editor.git
cd ledgerkit-editor

# 2. Get the branch you want to test
git checkout release/1.1.0

# 3. Remove any existing (possibly broken) venv, from an UNACTIVATED shell
deactivate 2>$null
Remove-Item -Recurse -Force .venv -ErrorAction SilentlyContinue

# 4. Create and activate a fresh venv
python -m venv .venv
.venv\Scripts\activate

# 5. Install — use the module form (python -m pip), not bare `pip`,
#    to sidestep the same launcher-path issue during install itself
python -m pip install --upgrade pip
pip install -e ".[dev]"

# 6. Confirm it's healthy
pytest --tb=short
```

Expect `431 passed` (or higher, if more has landed since this file was
last updated — check the actual count in the pytest summary line, don't
hardcode it).

### If step 3 or 4 fails with "Unable to copy ... venvlauncher.exe"

This repo lives inside a Dropbox-synced folder
(`Dropbox\Dev\Python\ledgerkit-editor`). Dropbox actively locks files
mid-sync on Windows, and a venv is thousands of small files — a classic
trigger for exactly this error. Pause Dropbox sync (tray icon → pause)
and retry steps 3–4. Once it works, consider excluding `.venv` from
Dropbox sync entirely (right-click the folder → Local sync / Selective
Sync → ignore) — it's disposable and fully regenerable from
`pyproject.toml`, so syncing it just adds lock contention for no benefit.

## Launch the editor

```powershell
python -m ledgerkit_editor path\to\your.journal
# or, if the console script is on PATH:
ledgerkit-editor path\to\your.journal
```

For the UAT checklists in this folder specifically, don't point it
directly at `uat-testing\uat-sample.journal` — copy it to a scratch
location first, since `Ctrl+S` during testing writes to disk and you
don't want to dirty the copy other testers will use:

```powershell
Copy-Item uat-testing\uat-sample.journal $env:TEMP\uat-sample.journal
python -m ledgerkit_editor $env:TEMP\uat-sample.journal
```

## Switching between branches for comparison

If you want to A/B against `master` (the last actual release) or another
branch, you don't need a second venv — just re-checkout and reinstall:

```powershell
git checkout master
pip install -e ".[dev]"   # picks up any dependency changes between branches
python -m ledgerkit_editor path\to\your.journal
```

Then `git checkout release/1.1.0` (or whichever branch) and `pip install
-e ".[dev]"` again to switch back.
