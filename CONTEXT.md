# CONTEXT.md — Session Working Memory

## Current Task

v1.0.0 release preparation complete. All phases done.

## Where We Are

All changes applied. Next step for the owner:
1. Rename GitHub repo from `PyLedger-editor` to `ledgerkit-editor` (Settings → Rename)
2. Create GitHub Environments `testpypi` (no gate) and `pypi` (required reviewer)
3. Configure Trusted Publishers on TestPyPI and PyPI (see CONTRIBUTING.md)
4. Push a `v1.0.0` tag to trigger the publish workflow

## Decisions In Flight

- `ledgerkit` pinned to `==1.0.0.dev1` — dev release; bump to stable when ledgerkit
  cuts a non-dev 1.0.0
- `textual` pinned to `==8.2.5` — do not upgrade without checking `LedgerTextArea._build_highlight_map`
  (private Textual 8.2.5 API)

## Files Currently Relevant

- `pyproject.toml` — version 1.0.0, requires-python >=3.9, ledgerkit==1.0.0.dev1
- `.github/workflows/ci.yml` — CI on push/PR to master
- `.github/workflows/publish.yml` — publish on v*.*.* tag push
- `CHANGELOG.md` — restructured to Keep-a-Changelog format
- `knowledge_base/ledgerkit_api_notes.md` — API notes updated for ledgerkit 1.0.0.dev1

## Blockers / Open Questions

None for code. Manual owner actions required before PyPI publish (see "Where We Are").

## What NOT To Revisit

- Vendor directory: deleted. ledgerkit is a normal PyPI dep from here on.
- `requirements-dev.txt`: deleted. Dev deps are in `[project.optional-dependencies] dev`.
- Python floor: confirmed >=3.9 (Textual 8.x requires it). Do not lower.
- Pre-existing test failure: `test_file_resolver.py::TestResolveJournalFile::test_returns_none_when_nothing_found`
  fails because `~/.hledger.journal` exists on this machine. Not a regression.

## Recent Git State

(run `git log --oneline -5` to refresh)
