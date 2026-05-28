# Antipatterns

Approaches that were tried and abandoned — do not revisit without addressing the underlying problem.

---

## Strict indentation gate for posting detection

**Tried:** Original `parse_string` used `line.startswith("  ") or line.startswith("\t")` to distinguish posting lines from directives/headers.

**Problem:** hledger 1.52 documents posting indentation as conventional, not mandatory. The strict gate would reject valid journals and contradicted the compatibility spec.

**Lesson:** Posting detection must be position-based (inside an open transaction block), not indentation-based.

**Do not revisit unless:** hledger changes the spec to require indentation (currently documented as conventional).

**See also:** `knowledge/DECISIONS.md` — "Posting indentation is conventional"

---

## `parse_file()` in `parser.py`

**Tried:** An early version of `parser.py` contained both `parse_string()` and `parse_file()`, mixing pure text parsing with file I/O in the same module.

**Problem:** Made the parser impure and harder to test. File resolution logic (relative paths, tilde expansion, format checks) accumulated in the wrong module.

**Lesson:** `parser.py` must remain a pure text-to-model function. All I/O belongs in `loader.py`.

**Do not revisit unless:** There's a compelling reason to collapse loader and parser (there isn't — they serve distinct responsibilities).

---

## `self.assertIsNotNone()` as a Pylance type guard

**Tried:** Using `self.assertIsNotNone(posting.amount)` before accessing `.quantity`/`.commodity` on `Posting.amount` (typed `Amount | None`).

**Problem:** Pylance does not treat `self.assertIsNotNone()` as a type-narrowing operation. `reportOptionalMemberAccess` warnings persist even after the assertion.

**Lesson:** Use bare `assert x is not None` immediately after extracting the field to a local variable. Pylance recognises this as a type guard.

**Do not revisit unless:** A future Pylance version adds support for `assertIsNotNone` narrowing (track microsoft/pylance-release).

---

## Accumulating aliases across included files

**Tried:** (Design consideration during alias implementation) — applying aliases globally across all files loaded via `include`.

**Problem:** Would silently rewrite account names in unrelated included files, producing surprising and hard-to-debug behaviour.

**Lesson:** Aliases are file-scoped at parse time. Each file's alias list is independent.

**Do not revisit unless:** A user explicitly requests cross-file alias propagation and we document it as a deliberate deviation from hledger.
