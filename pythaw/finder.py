from __future__ import annotations

import ast
import subprocess
from dataclasses import dataclass
from fnmatch import fnmatch
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pythaw.config import Config


@dataclass(frozen=True)
class HandlerFunction:
    """A handler entry point discovered in a source file."""

    file: Path
    name: str
    lineno: int
    col_offset: int


def find_handlers(path: Path, config: Config) -> list[HandlerFunction]:
    """Find handler entry points in Python files under *path*.

    Collects ``*.py`` files, parses each one, and returns top-level
    function definitions whose name matches any of the configured
    ``handler_patterns``.
    """
    files = collect_files(path, config)
    handlers: list[HandlerFunction] = []
    for file in files:
        handlers.extend(_extract_handlers(file, config.handler_patterns))
    return handlers


def collect_files(path: Path, config: Config) -> list[Path]:
    """Collect Python files to check under *path*.

    When *path* is a regular file it is returned directly (no filtering).
    When *path* is a directory, ``*.py`` files are discovered recursively,
    respecting ``.gitignore`` and the ``exclude`` patterns in *config*.
    """
    target = Path(path).resolve()

    if target.is_file():
        return [target]

    if not target.is_dir():
        return []

    py_files = _git_ls_files(target)
    if py_files is None:
        py_files = _rglob_py(target)

    if config.exclude:
        py_files = [
            f for f in py_files if not _is_excluded(f, target, config.exclude)
        ]

    py_files.sort()
    return py_files


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _extract_handlers(
    file: Path,
    patterns: tuple[str, ...],
) -> list[HandlerFunction]:
    """Parse *file* and return top-level functions matching *patterns*."""
    try:
        source = file.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=str(file))
    except (SyntaxError, UnicodeDecodeError, OSError):
        return []

    return [
        HandlerFunction(
            file=file,
            name=node.name,
            lineno=node.lineno,
            col_offset=node.col_offset,
        )
        for node in ast.iter_child_nodes(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and any(fnmatch(node.name, p) for p in patterns)
    ]


def _git_ls_files(directory: Path) -> list[Path] | None:
    """List Python files using *git*, respecting ``.gitignore``.

    Returns ``None`` when *git* is unavailable or *directory* is not inside a
    git repository so the caller can fall back to a plain glob.
    """
    cmd = [
        "git",
        "ls-files",
        "--cached",
        "--others",
        "--exclude-standard",
        "-z",
        "*.py",
    ]
    try:
        result = subprocess.run(  # noqa: S603
            cmd,
            cwd=directory,
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return None

    if result.returncode != 0:
        return None

    paths: list[Path] = []
    for name in result.stdout.split("\0"):
        if name:
            resolved = (directory / name).resolve()
            if resolved.is_file():
                paths.append(resolved)
    return paths


def _rglob_py(directory: Path) -> list[Path]:
    """Recursively glob for ``*.py`` files (fallback when git is absent)."""
    return [p.resolve() for p in directory.rglob("*.py") if p.is_file()]


def _is_excluded(
    file: Path,
    base: Path,
    exclude: tuple[str, ...],
) -> bool:
    """Return ``True`` if *file* matches any *exclude* pattern.

    Each component of the relative path is tested individually so that a
    pattern like ``"tests"`` matches a directory at any depth.  The full
    relative path is also tested to support glob patterns such as
    ``"tests/*.py"``.
    """
    try:
        relative = file.relative_to(base)
    except ValueError:
        return False

    rel_str = str(relative)
    for pattern in exclude:
        for part in relative.parts:
            if fnmatch(part, pattern):
                return True
        if fnmatch(rel_str, pattern):
            return True
    return False
