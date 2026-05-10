"""File loader for PyLedger.

Handles file I/O, include directive expansion, path resolution, glob
matching, and circular include detection. Calls parse_string() for
text-to-Journal conversion.
"""

from __future__ import annotations

import glob as _glob_module
import os
import re
from pathlib import Path

from PyLedger.models import Journal
from PyLedger.parser import ParseError, parse_string


_SUPPORTED_EXTENSIONS: frozenset[str] = frozenset({".journal", ".ledger"})

# Known hledger format type prefixes (e.g. "timedot:", "csv:").
# These are not supported in PyLedger v1.
_FORMAT_PREFIXES: frozenset[str] = frozenset({
    "journal", "ledger", "timeclock", "timedot", "csv", "ssv", "tsv", "rules",
})

# Matches an hledger `include` directive line.
#
# Purpose: detect whether a non-indented line is an include directive and
#          extract the target path string for further resolution.
#
# Group breakdown:
#   (1) (.+)  — the raw target path string, captured after the mandatory
#               whitespace that follows the "include" keyword. May contain
#               glob characters, tildes, slashes, or spaces. Caller strips
#               leading/trailing whitespace before use.
#
# Edge cases:
#   - A line of just "include" (no whitespace) does not match because \s+
#     requires at least one whitespace character after the keyword.
#   - "include  " (keyword + only spaces) matches with a whitespace-only
#     group (1); the caller raises ParseError after stripping.
#   - Indented lines (starting with spaces/tabs) do not match because ^
#     anchors to the start of the line; indented posting-style lines are
#     never directives.
#   - "included" or "includes" do not match because \s+ requires whitespace
#     immediately after the exact word "include".
_INCLUDE_LINE = re.compile(r"^include\s+(.+)$")


def _validate_extension(
    path: Path,
    *,
    lineno: int | None = None,
    source: Path | None = None,
) -> None:
    """Raise ParseError if path has an unsupported extension."""
    ext = path.suffix.lower()
    if ext not in _SUPPORTED_EXTENSIONS:
        supported = ", ".join(sorted(_SUPPORTED_EXTENSIONS))
        src = f" in {source}" if source is not None else ""
        raise ParseError(
            f"unsupported file format {ext!r} — PyLedger accepts: {supported}{src}",
            lineno,
        )


def _check_format_prefix(raw: str, lineno: int, source: Path) -> None:
    """Raise ParseError if raw begins with a known hledger format type prefix.

    Format prefixes (e.g. "timedot:notes.md") are not supported in PyLedger v1.
    Single-character prefixes are treated as Windows drive letters (e.g. "C:")
    and are not flagged here.
    """
    colon = raw.find(":")
    if colon > 1:
        prefix = raw[:colon].lower()
        if prefix in _FORMAT_PREFIXES:
            raise ParseError(
                f"format prefixes not supported in PyLedger v1 — "
                f"remove the '{prefix}:' prefix from the include path",
                lineno,
            )


def _resolve_include_path(raw: str, containing_dir: Path) -> list[Path]:
    """Resolve a raw include path string to a sorted list of absolute Paths.

    Handles tilde expansion, absolute paths, relative paths (relative to
    containing_dir), and glob patterns. Returns an empty list when a glob
    pattern matches no files. Does NOT filter out the calling file.

    Args:
        raw: The stripped path string from the include directive.
        containing_dir: Absolute directory of the file containing the include.

    Returns:
        Sorted list of resolved absolute Path objects.
    """
    if raw.startswith("~"):
        base = Path(raw).expanduser()
    elif Path(raw).is_absolute():
        base = Path(raw)
    else:
        base = containing_dir / raw

    base_str = str(base)
    if any(c in base_str for c in ("*", "?", "[")):
        matches = _glob_module.glob(base_str, recursive=True)
        return sorted(Path(m).resolve() for m in matches)

    return [base.resolve()]


def _expand_includes(
    file_path: Path,
    visited: set[Path],
    line_map: list[tuple[Path, int]],
) -> str:
    """Recursively read file_path and expand all include directives.

    Appends one (file_path, lineno) entry to line_map for every line that
    appears in the returned text, so callers can map expanded-text line
    numbers back to their originating source file and line.

    The include directive lines themselves are consumed and produce no output
    or line_map entries; they are replaced by the expanded content of the
    referenced file(s).

    Args:
        file_path: Resolved absolute path to the file to expand.
        visited: Set of absolute paths currently in the include chain.
                 Mutated (add before recurse, remove after) for cycle detection.
        line_map: Accumulator for source attribution. Caller passes an empty
                  list for the root file; recursive calls share the same list.

    Returns:
        Fully expanded text with all include directives substituted inline.

    Raises:
        FileNotFoundError: if file_path or a non-glob included file does not exist.
        ParseError: on circular include, unsupported extension, format prefix,
                    or a glob pattern that matches no files.
    """
    text = file_path.read_text(encoding="utf-8")
    lines = text.splitlines()
    output: list[str] = []

    for lineno, line in enumerate(lines, 1):
        m = _INCLUDE_LINE.match(line)
        if not m:
            line_map.append((file_path, lineno))
            output.append(line + "\n")
            continue

        raw_target = m.group(1).strip()
        if not raw_target:
            raise ParseError("include: missing file path", lineno)

        _check_format_prefix(raw_target, lineno, file_path)

        is_glob = any(c in raw_target for c in ("*", "?", "["))
        targets = _resolve_include_path(raw_target, file_path.parent)
        targets = [t for t in targets if t != file_path]

        if not targets:
            if is_glob:
                raise ParseError(
                    f"include: no files matched {raw_target!r}",
                    lineno,
                )
            # Non-glob: resolve for a clear error message
            resolved = _resolve_include_path(raw_target, file_path.parent)[0]
            raise FileNotFoundError(
                f"include: file not found: {resolved} "
                f"(referenced at {file_path}, line {lineno})"
            )

        for target in targets:
            _validate_extension(target, lineno=lineno, source=file_path)
            if target in visited:
                raise ParseError(
                    f"circular include detected: {target} is already being "
                    f"processed (referenced at {file_path}, line {lineno})",
                    lineno,
                )
            visited.add(target)
            output.append(_expand_includes(target, visited, line_map))
            visited.remove(target)

    return "".join(output)


def load_journal_stdin() -> Journal:
    """Read a journal from stdin and return a Journal object.

    Parses the full stdin contents as hledger journal text.
    Sets source_file to "(stdin)". included_files is always 0
    because stdin content cannot reference include directives
    with resolvable relative paths.

    Returns:
        A :class:`~PyLedger.models.Journal` with ``source_file``
        set to ``"(stdin)"``.

    Raises:
        ParseError: if the stdin content is malformed.
    """
    import sys

    journal = parse_string(sys.stdin.read())
    journal.source_file = "(stdin)"
    return journal


def merge_journals(journals: list[Journal]) -> Journal:
    """Merge a list of Journal objects into a single Journal.

    Transactions and prices are concatenated in input order.
    ``source_file`` is taken from the first journal in the list.
    ``included_files`` is the sum of all input journals'
    ``included_files`` values.

    Args:
        journals: Non-empty list of Journal objects to merge.

    Returns:
        A new :class:`~PyLedger.models.Journal` containing the
        combined data, or the original object when the list has
        exactly one entry.

    Raises:
        ValueError: if ``journals`` is empty.
    """
    if not journals:
        raise ValueError("merge_journals: at least one journal required")
    if len(journals) == 1:
        return journals[0]
    return Journal(
        transactions=[t for j in journals for t in j.transactions],
        prices=[p for j in journals for p in j.prices],
        declared_accounts=[a for j in journals for a in j.declared_accounts],
        declared_commodities=[c for j in journals for c in j.declared_commodities],
        declared_payees=[p for j in journals for p in j.declared_payees],
        declared_tags=[t for j in journals for t in j.declared_tags],
        source_file=journals[0].source_file,
        included_files=sum(j.included_files for j in journals),
    )


def load_journal(path: str | os.PathLike) -> Journal:
    """Load a .journal or .ledger file and return a Journal object.

    Supports the hledger ``include`` directive. Included files are expanded
    recursively at the point of the directive before parsing, so directive
    scope (e.g. an ``alias`` active before an ``include``) propagates
    naturally through included content.

    Path resolution in include directives:
      - ``~/...``        tilde expanded to the home directory
      - ``/abs/path``    used as-is (absolute)
      - ``relative``     resolved relative to the containing file's directory
      - Glob patterns (``*``, ``**``, ``?``, ``[range]``) are expanded via
        :func:`glob.glob`; the containing file is always excluded from results.

    Only ``.journal`` and ``.ledger`` files may be loaded or included.
    Format prefixes (e.g. ``timedot:``) raise :class:`ParseError`.
    Circular includes raise :class:`ParseError`.

    Args:
        path: Absolute or relative path to the root journal file.

    Returns:
        A :class:`~PyLedger.models.Journal` with ``source_file`` and
        ``included_files`` populated.

    Raises:
        FileNotFoundError: if the root path or a non-glob included file does
            not exist.
        ParseError: if an extension is unsupported, a format prefix is used,
            a circular include is detected, a glob matches nothing, or the
            file contents are malformed.
    """
    abs_path = Path(os.fspath(path)).resolve()
    _validate_extension(abs_path)

    line_map: list[tuple[Path, int]] = []
    visited: set[Path] = {abs_path}
    expanded = _expand_includes(abs_path, visited, line_map)

    included_count = len({src for src, _ in line_map if src != abs_path})

    try:
        journal = parse_string(expanded, source_file=str(abs_path))
    except ParseError as exc:
        if exc.line_number is not None and 1 <= exc.line_number <= len(line_map):
            orig_file, orig_lineno = line_map[exc.line_number - 1]
            # Strip any existing " (line N)" suffix from the original message
            # before re-raising with the correctly attributed location.
            orig_msg = exc.args[0]
            if " (line " in orig_msg:
                orig_msg = orig_msg[: orig_msg.rfind(" (line ")]
            raise ParseError(
                f"{orig_file}: {orig_msg}",
                orig_lineno,
            ) from exc
        raise

    journal.source_file = str(abs_path)
    journal.included_files = included_count
    return journal
