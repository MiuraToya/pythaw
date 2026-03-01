from __future__ import annotations

import subprocess
from fnmatch import fnmatch
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pythaw.config import Config


def find_files(path: Path, config: Config) -> list[Path]:
    """Collect Python files to check under *path*.

    When *path* is a regular file it is returned directly (no filtering).
    When *path* is a directory, ``*.py`` files are discovered recursively,
    respecting ``.gitignore`` and the ``exclude`` patterns in *config*.
    """
    target = path.resolve()

    if target.is_file():
        return [target]

    if not target.is_dir():
        return []

    # Prefer git for file discovery (.gitignore-aware); fall back to
    # plain glob when git is unavailable or the directory is not a repo.
    py_files = _git_ls_files(target)
    if py_files is None:
        py_files = _rglob_py(target)

    if config.exclude:
        py_files = [f for f in py_files if not _is_excluded(f, target, config.exclude)]

    py_files.sort()
    return py_files


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _git_ls_files(directory: Path) -> list[Path] | None:
    """List Python files using *git*, respecting ``.gitignore``.

    Returns ``None`` when *git* is unavailable or *directory* is not inside a
    git repository so the caller can fall back to a plain glob.
    """
    # --cached: tracked files, --others: untracked files.
    # Together they cover all files except .gitignore'd ones
    # (filtered by --exclude-standard).
    # -z: null-delimited output for safe parsing of filenames with spaces.
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
    except (OSError, subprocess.TimeoutExpired):
        # OSError covers git not installed, permission denied, etc.
        # TimeoutExpired: git hung (e.g. prompting for credentials).
        return None

    if result.returncode != 0:
        return None

    paths: list[Path] = []
    for name in result.stdout.split("\0"):
        # -z output ends with a trailing \0, producing an empty string
        # at the end of split(); skip it.
        if name:
            # git ls-files returns paths relative to cwd; convert to absolute.
            resolved = (directory / name).resolve()
            # --cached includes files still in the index after deletion;
            # verify the file actually exists on disk.
            if resolved.is_file():
                paths.append(resolved)
    return paths


def _rglob_py(directory: Path) -> list[Path]:
    """Recursively glob for ``*.py`` files (fallback when git is absent)."""
    return [p.resolve() for p in directory.rglob("*.py") if p.is_file()]


def _is_excluded(
    file: Path,
    directory: Path,
    exclude: tuple[str, ...],
) -> bool:
    """Return ``True`` if *file* matches any *exclude* pattern.

    Each component of the relative path is tested individually so that a
    pattern like ``"tests"`` matches a directory at any depth.  The full
    relative path is also tested to support glob patterns such as
    ``"tests/*.py"``.
    """
    try:
        relative = file.relative_to(directory)
    except ValueError:
        return False

    for pattern in exclude:
        for part in relative.parts:
            if fnmatch(part, pattern):
                return True
        if fnmatch(str(relative), pattern):
            return True
    return False
