from __future__ import annotations

import ast
import os
import re
from fnmatch import fnmatch
from typing import TYPE_CHECKING, TypeAlias

from pythaw.finder import find_files
from pythaw.rules import get_all_rules
from pythaw.violation import Violation

if TYPE_CHECKING:
    from pathlib import Path

    from pythaw.config import Config
    from pythaw.rules._base import Rule

FunctionNode: TypeAlias = ast.FunctionDef | ast.AsyncFunctionDef


def check(
    path: Path,
    config: Config,
    *,
    select: frozenset[str] = frozenset(),
    ignore: frozenset[str] = frozenset(),
) -> list[Violation]:
    """Run all rules against handler functions found under *path*.

    Args:
        path: File or directory to check.
        config: Project configuration (handler patterns, excludes, etc.).
        select: If non-empty, only run rules whose codes are in this set.
        ignore: Rule codes to skip.

    Returns:
        A list of violations found across all handler functions.
    """
    files = find_files(path, config)
    rules = _filter_rules(get_all_rules(), select=select, ignore=ignore)
    violations: list[Violation] = []

    base = path if path.is_dir() else path.parent
    for file in files:
        source = _read_source(file)
        if source is None:
            continue
        if _has_nocheck(source):
            continue
        tree = _parse_source(source, file)
        if tree is None:
            continue
        file_rules = _apply_per_file_ignores(rules, file, base, config.per_file_ignores)
        suppressed = _parse_nopw_comments(source)
        for func_node in _extract_handlers(tree, config.handler_patterns):
            violations.extend(
                _check_function(file, func_node, file_rules, suppressed)
            )

    return violations


def _apply_per_file_ignores(
    rules: tuple[Rule, ...],
    file: Path,
    base: Path,
    per_file_ignores: tuple[tuple[str, tuple[str, ...]], ...],
) -> tuple[Rule, ...]:
    """Remove rules that match per-file-ignores patterns for *file*."""
    if not per_file_ignores:
        return rules
    ignored_codes: set[str] = set()
    try:
        rel = str(file.resolve().relative_to(base.resolve()))
    except ValueError:
        rel = os.path.relpath(file)
    for pattern, codes in per_file_ignores:
        if fnmatch(rel, pattern):
            ignored_codes.update(codes)
    if not ignored_codes:
        return rules
    return tuple(r for r in rules if r.code not in ignored_codes)


def _filter_rules(
    rules: tuple[Rule, ...],
    *,
    select: frozenset[str],
    ignore: frozenset[str],
) -> tuple[Rule, ...]:
    """Filter rules by *select* and *ignore* code sets."""
    filtered = rules
    if select:
        filtered = tuple(r for r in filtered if r.code in select)
    if ignore:
        filtered = tuple(r for r in filtered if r.code not in ignore)
    return filtered


_NOPW_RE = re.compile(r"#\s*nopw:\s*(PW\d+(?:\s*,\s*PW\d+)*)")
_NOCHECK_RE = re.compile(r"^\s*#\s*pythaw:\s*nocheck\b")


def _read_source(file: Path) -> str | None:
    """Read *file* and return its contents, or ``None`` on failure."""
    try:
        return file.read_text(encoding="utf-8")
    except (UnicodeDecodeError, OSError):
        return None


def _parse_source(source: str, file: Path) -> ast.Module | None:
    """Parse *source* and return the AST, or ``None`` on failure."""
    try:
        return ast.parse(source, filename=str(file))
    except SyntaxError:
        return None


def _has_nocheck(source: str) -> bool:
    """Return ``True`` if *source* contains a ``# pythaw: nocheck`` directive."""
    for line in source.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            if _NOCHECK_RE.match(stripped):
                return True
            continue
        break
    return False


def _parse_nopw_comments(source: str) -> dict[int, frozenset[str]]:
    """Extract per-line ``# nopw: PWXXX`` suppression directives.

    Returns a mapping of line number to the set of suppressed rule codes.
    """
    suppressed: dict[int, frozenset[str]] = {}
    for lineno, line in enumerate(source.splitlines(), start=1):
        m = _NOPW_RE.search(line)
        if m:
            codes = frozenset(c.strip() for c in m.group(1).split(","))
            suppressed[lineno] = codes
    return suppressed


def _extract_handlers(
    tree: ast.Module,
    patterns: tuple[str, ...],
) -> list[FunctionNode]:
    """Return top-level function nodes whose name matches *patterns*."""
    # Only inspect top-level nodes (iter_child_nodes does not recurse)
    # so that nested functions and class methods are excluded.
    return [
        node
        for node in ast.iter_child_nodes(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and any(fnmatch(node.name, p) for p in patterns)
    ]


def _check_function(
    file: Path,
    func_node: FunctionNode,
    rules: tuple[Rule, ...],
    suppressed: dict[int, frozenset[str]],
) -> list[Violation]:
    """Walk *func_node* and return violations for any matching Call nodes."""
    return [
        Violation(
            file=os.path.relpath(file),
            line=node.lineno,
            col=node.col_offset,
            code=rule.code,
            message=rule.message,
        )
        for node in ast.walk(func_node)
        if isinstance(node, ast.Call)
        for rule in rules
        if rule.check(node)
        and rule.code not in suppressed.get(node.lineno, frozenset())
    ]
