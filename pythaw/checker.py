from __future__ import annotations

import ast
import os
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
    select: tuple[str, ...] | None = None,
    ignore: tuple[str, ...] | None = None,
) -> list[Violation]:
    """Run all rules against handler functions found under *path*.

    Args:
        path: File or directory to check.
        config: Project configuration (handler patterns, excludes, etc.).
        select: If provided, only run rules whose code is in this tuple.
        ignore: If provided, skip rules whose code is in this tuple.

    Returns:
        A list of violations found across all handler functions.
    """
    files = find_files(path, config)
    rules = _filter_rules(get_all_rules(), select, ignore)
    violations: list[Violation] = []

    for file in files:
        tree = _parse_file(file)
        if tree is None:
            continue
        for func_node in _extract_handlers(tree, config.handler_patterns):
            violations.extend(_check_function(file, func_node, rules))

    return violations


def _filter_rules(
    rules: tuple[Rule, ...],
    select: tuple[str, ...] | None,
    ignore: tuple[str, ...] | None,
) -> tuple[Rule, ...]:
    """Filter rules by select/ignore lists."""
    filtered = rules
    if select is not None:
        filtered = tuple(r for r in filtered if r.code in select)
    if ignore is not None:
        filtered = tuple(r for r in filtered if r.code not in ignore)
    return filtered


def _parse_file(file: Path) -> ast.Module | None:
    """Parse *file* and return the AST, or ``None`` on failure."""
    try:
        source = file.read_text(encoding="utf-8")
        return ast.parse(source, filename=str(file))
    except (SyntaxError, UnicodeDecodeError, OSError):
        return None


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
    ]
