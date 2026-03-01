from __future__ import annotations

import subprocess
from typing import TYPE_CHECKING
from unittest.mock import patch

import pytest

from pythaw.config import Config
from pythaw.finder import find_files

if TYPE_CHECKING:
    from pathlib import Path


def _git(cwd: Path, *args: str) -> None:
    """Run a git command inside *cwd*."""
    subprocess.run(  # noqa: S603
        ["git", *args],  # noqa: S607
        cwd=cwd,
        capture_output=True,
        check=False,
    )


def _make_files(base: Path, files: dict[str, str]) -> None:
    """Create files under *base* with the given content."""
    for name, content in files.items():
        p = base / name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content)


# ---------------------------------------------------------------------------
# find_files
# ---------------------------------------------------------------------------


class TestFindFilesSingleFile:
    """Verify behaviour when a single file path is passed."""

    def test_returns_single_file(self, tmp_path: Path) -> None:
        """A regular .py file is returned as-is."""
        py = tmp_path / "app.py"
        py.touch()
        result = find_files(py, Config())
        assert result == [py.resolve()]

    def test_single_file_ignores_exclude(self, tmp_path: Path) -> None:
        """Exclude patterns are not applied to explicit file paths."""
        py = tmp_path / "excluded.py"
        py.touch()
        cfg = Config(exclude=("excluded.py",))
        result = find_files(py, cfg)
        assert result == [py.resolve()]


class TestFindFilesNonExistent:
    """Verify behaviour for paths that do not exist."""

    def test_nonexistent_path_returns_empty(self, tmp_path: Path) -> None:
        """A path that does not exist yields an empty list."""
        result = find_files(tmp_path / "no_such_path", Config())
        assert result == []


class TestFindFilesDirectory:
    """Verify recursive Python file discovery in directories."""

    def test_discovers_py_files_recursively(self, tmp_path: Path) -> None:
        """All *.py files under the directory are found."""
        _make_files(
            tmp_path,
            {"a.py": "", "sub/b.py": "", "sub/deep/c.py": "", "readme.txt": ""},
        )
        with patch("pythaw.finder._git_ls_files", return_value=None):
            result = find_files(tmp_path, Config())
        names = sorted(p.name for p in result)
        assert names == ["a.py", "b.py", "c.py"]

    @pytest.mark.parametrize(
        ("files", "exclude"),
        [
            ({"app.py": "", "tests/test_app.py": ""}, ("tests",)),
            ({"app.py": "", "test_app.py": ""}, ("test_*",)),
            ({"src/app.py": "", "src/.venv/lib.py": ""}, (".venv",)),
        ],
        ids=["directory", "glob-pattern", "nested-directory"],
    )
    def test_exclude_patterns(
        self, tmp_path: Path, files: dict[str, str], exclude: tuple[str, ...]
    ) -> None:
        """Exclude patterns filter out matching files by directory, glob, or nesting."""
        _make_files(tmp_path, files)
        cfg = Config(exclude=exclude)
        with patch("pythaw.finder._git_ls_files", return_value=None):
            result = find_files(tmp_path, cfg)
        names = [p.name for p in result]
        assert names == ["app.py"]

    def test_results_are_sorted(self, tmp_path: Path) -> None:
        """Returned paths are in sorted order."""
        _make_files(tmp_path, {"z.py": "", "a.py": "", "m.py": ""})
        with patch("pythaw.finder._git_ls_files", return_value=None):
            result = find_files(tmp_path, Config())
        names = [p.name for p in result]
        assert names == ["a.py", "m.py", "z.py"]


class TestGitIgnoreIntegration:
    """Verify .gitignore is respected when git is available."""

    def test_gitignored_files_are_excluded(self, tmp_path: Path) -> None:
        """Files listed in .gitignore are not returned."""
        _git(tmp_path, "init")
        (tmp_path / ".gitignore").write_text("ignored/\n")
        _make_files(tmp_path, {"app.py": "", "ignored/secret.py": ""})
        _git(tmp_path, "add", ".")
        result = find_files(tmp_path, Config())
        names = [p.name for p in result]
        assert "secret.py" not in names
        assert "app.py" in names

    def test_untracked_files_are_included(self, tmp_path: Path) -> None:
        """Untracked (but not ignored) files are still discovered."""
        _git(tmp_path, "init")
        _make_files(tmp_path, {"tracked.py": "", "untracked.py": ""})
        _git(tmp_path, "add", "tracked.py")
        result = find_files(tmp_path, Config())
        names = sorted(p.name for p in result)
        assert names == ["tracked.py", "untracked.py"]


class TestGitFallback:
    """Verify graceful fallback when git is not available."""

    def test_falls_back_when_git_missing(self, tmp_path: Path) -> None:
        """When git is not installed, rglob fallback is used."""
        _make_files(tmp_path, {"app.py": ""})
        with patch(
            "pythaw.finder.subprocess.run",
            side_effect=FileNotFoundError,
        ):
            result = find_files(tmp_path, Config())
        assert len(result) == 1
        assert result[0].name == "app.py"

    def test_falls_back_when_not_git_repo(self, tmp_path: Path) -> None:
        """When directory is not a git repo, rglob fallback is used."""
        _make_files(tmp_path, {"app.py": ""})
        result = find_files(tmp_path, Config())
        assert len(result) == 1
        assert result[0].name == "app.py"
