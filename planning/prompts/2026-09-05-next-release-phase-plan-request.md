# Original request — next-release phase plan

Captured verbatim from the user's request on 2026-09-05, preserved alongside
the generated plan (`planning/next-release-phase-plan.md`) for traceability.

---

Create a phased implementation plan for the next release - save generated phase plan to planning folder including a copy of this prompt in a planning subfolder.

Following bug fixes should be implemented:
- dates in P declarations are not being treated as dates - date incrementation with shift key should work on these as well.
- There is a bug with the date incrementation using the shift key - dates where there is no leading zero such as 2026-9-1 are not being recognized as valid dates - these should be expanded to 2026-09-01 and shift incrementation should work on these dates.
- when focus is taken away from the editor using CTRL+F and a search result is found and highlighted, CTRL+C is then intercepted by the CLI as the quit command - text should be allowed to be copied using CTRL+C whil focus is on the search panel.
- When moving to the previous search result in the file or when using SHIFT+PGUP, not enough padding is provided - the cursor moves to the very top of the editor panel - more padding should be allowed similar to when SHIFT+PGDOWN is entered.

- The next feature - Filter transactions should be planned - this should support smart dates and Python regex

- The feature Tab autocompletion based on information in the ledger file - such as suggesting account names, transaction classification etc

- A repeatable process and accompanying Claude skill should be planned to polish and simplify codebase and look for enhancements and efficiencies without impacting functionality

- A repeatable process and accompanying Claude skill should be planned to document the package in a best practice manner, creating both human-focused docs and also brief AI-focused docs such as an AI-README describing what the project does in an agent-efficient manner the AI-README should be suitable for being pasted as a prompt and describe what the project is, how it works and how to use it etc.
