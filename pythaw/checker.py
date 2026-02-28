from __future__ import annotations

import ast
import os
from typing import TYPE_CHECKING

from pythaw.finder import find_handlers
from pythaw.rules import get_all_rules
from pythaw.violation import Violation

if TYPE_CHECKING:
    from pathlib import Path

    from pythaw.config import Config
    from pythaw.rules._base import Rule


def check(path: Path, config: Config) -> list[Violation]:
    """Run all rules against handler functions found under *path*."""
    handlers = find_handlers(path, config)
    rules = get_all_rules()
    violations: list[Violation] = []

    parsed: dict[Path, ast.Module | None] = {}
    for handler in handlers:
        tree = _get_tree(handler.file, parsed)
        if tree is None:
            continue
        func_node = _find_function_node(tree, handler.name, handler.lineno)
        if func_node is None:
            continue
        violations.extend(_check_function(handler.file, func_node, rules))

    return violations


def _get_tree(file: Path, cache: dict[Path, ast.Module | None]) -> ast.Module | None:
    """Parse *file* and cache the result."""
    if file not in cache:
        try:
            source = file.read_text(encoding="utf-8")
            cache[file] = ast.parse(source, filename=str(file))
        except (SyntaxError, UnicodeDecodeError, OSError):
            cache[file] = None
    return cache[file]


def _find_function_node(
    tree: ast.Module,
    name: str,
    lineno: int,
) -> ast.FunctionDef | ast.AsyncFunctionDef | None:
    """Find a top-level function node by *name* and *lineno*."""
    for node in ast.iter_child_nodes(tree):
        if (
            isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
            and node.name == name
            and node.lineno == lineno
        ):
            return node
    return None


def _check_function(
    file: Path,
    func_node: ast.FunctionDef | ast.AsyncFunctionDef,
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
