from __future__ import annotations

import ast
import os
import re
from fnmatch import fnmatch
from typing import TYPE_CHECKING, TypeAlias

from pythaw.finder import find_files
from pythaw.resolver import Resolver
from pythaw.rules import get_all_rules
from pythaw.violation import CallSite, Violation

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
    resolver = Resolver(base)
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
                _check_function(
                    file,
                    func_node,
                    file_rules,
                    suppressed,
                    resolver,
                )
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


def _check_function(  # noqa: PLR0913
    file: Path,
    func_node: FunctionNode,
    rules: tuple[Rule, ...],
    suppressed: dict[int, frozenset[str]],
    resolver: Resolver,
    *,
    chain: tuple[CallSite, ...] = (),
    visited: set[tuple[str, str]] | None = None,
) -> list[Violation]:
    """Walk *func_node* and return violations, following local calls."""
    if visited is None:
        visited = set()

    violations: list[Violation] = []
    for node in ast.walk(func_node):
        if not isinstance(node, ast.Call):
            continue

        # Check rule violations
        suppressed_codes = suppressed.get(node.lineno, frozenset())
        violations.extend(
            Violation(
                file=os.path.relpath(file),
                line=node.lineno,
                col=node.col_offset,
                code=rule.code,
                message=rule.message,
                call_chain=chain,
            )
            for rule in rules
            if rule.check(node) and rule.code not in suppressed_codes
        )

        # Follow resolved local calls
        _follow_call(
            file,
            node,
            rules,
            resolver,
            chain,
            visited,
            violations,
        )

    return violations


def _follow_call(  # noqa: PLR0913
    file: Path,
    node: ast.Call,
    rules: tuple[Rule, ...],
    resolver: Resolver,
    chain: tuple[CallSite, ...],
    visited: set[tuple[str, str]],
    violations: list[Violation],
) -> None:
    """Resolve *node* and recursively check the target definition."""
    target = resolver.resolve_call(file, node)
    if target is None:
        return
    target_file, target_defn = target

    walkable: FunctionNode | None
    if isinstance(target_defn, ast.ClassDef):
        walkable = resolver.get_init(target_defn)
    else:
        walkable = target_defn
    if walkable is None:
        return

    key = (str(target_file.resolve()), target_defn.name)
    if key in visited:
        return
    visited.add(key)

    site = CallSite(
        file=os.path.relpath(file),
        line=node.lineno,
        col=node.col_offset,
        name=resolver.call_display_name(node),
    )
    target_source = resolver.read_source(target_file)
    target_suppressed = _parse_nopw_comments(target_source) if target_source else {}
    violations.extend(
        _check_function(
            target_file,
            walkable,
            rules,
            target_suppressed,
            resolver,
            chain=(*chain, site),
            visited=visited,
        )
    )
