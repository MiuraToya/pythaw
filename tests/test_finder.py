from __future__ import annotations

import subprocess
from typing import TYPE_CHECKING
from unittest.mock import patch

from pythaw.config import Config
from pythaw.finder import collect_files, find_handlers

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
# collect_files
# ---------------------------------------------------------------------------


class TestCollectFilesSingleFile:
    """Verify behaviour when a single file path is passed."""

    def test_returns_single_file(self, tmp_path: Path) -> None:
        """A regular .py file is returned as-is."""
        py = tmp_path / "app.py"
        py.touch()
        result = collect_files(py, Config())
        assert result == [py.resolve()]

    def test_single_file_ignores_exclude(self, tmp_path: Path) -> None:
        """Exclude patterns are not applied to explicit file paths."""
        py = tmp_path / "excluded.py"
        py.touch()
        cfg = Config(exclude=("excluded.py",))
        result = collect_files(py, cfg)
        assert result == [py.resolve()]


class TestCollectFilesNonExistent:
    """Verify behaviour for paths that do not exist."""

    def test_nonexistent_path_returns_empty(self, tmp_path: Path) -> None:
        """A path that does not exist yields an empty list."""
        result = collect_files(tmp_path / "no_such_path", Config())
        assert result == []


class TestCollectFilesDirectory:
    """Verify recursive Python file discovery in directories."""

    def test_discovers_py_files_recursively(self, tmp_path: Path) -> None:
        """All *.py files under the directory are found."""
        _make_files(
            tmp_path,
            {"a.py": "", "sub/b.py": "", "sub/deep/c.py": "", "readme.txt": ""},
        )
        with patch("pythaw.finder._git_ls_files", return_value=None):
            result = collect_files(tmp_path, Config())
        names = sorted(p.name for p in result)
        assert names == ["a.py", "b.py", "c.py"]

    def test_excludes_matching_directory(self, tmp_path: Path) -> None:
        """Files under an excluded directory are filtered out."""
        _make_files(tmp_path, {"app.py": "", "tests/test_app.py": ""})
        cfg = Config(exclude=("tests",))
        with patch("pythaw.finder._git_ls_files", return_value=None):
            result = collect_files(tmp_path, cfg)
        names = [p.name for p in result]
        assert names == ["app.py"]

    def test_excludes_glob_pattern(self, tmp_path: Path) -> None:
        """Glob-style exclude patterns work correctly."""
        _make_files(tmp_path, {"app.py": "", "test_app.py": ""})
        cfg = Config(exclude=("test_*",))
        with patch("pythaw.finder._git_ls_files", return_value=None):
            result = collect_files(tmp_path, cfg)
        names = [p.name for p in result]
        assert names == ["app.py"]

    def test_excludes_nested_directory(self, tmp_path: Path) -> None:
        """Exclude pattern matches a directory name at any depth."""
        _make_files(tmp_path, {"src/app.py": "", "src/.venv/lib.py": ""})
        cfg = Config(exclude=(".venv",))
        with patch("pythaw.finder._git_ls_files", return_value=None):
            result = collect_files(tmp_path, cfg)
        names = [p.name for p in result]
        assert names == ["app.py"]

    def test_results_are_sorted(self, tmp_path: Path) -> None:
        """Returned paths are in sorted order."""
        _make_files(tmp_path, {"z.py": "", "a.py": "", "m.py": ""})
        with patch("pythaw.finder._git_ls_files", return_value=None):
            result = collect_files(tmp_path, Config())
        names = [p.name for p in result]
        assert names == ["a.py", "m.py", "z.py"]

    def test_empty_directory(self, tmp_path: Path) -> None:
        """An empty directory yields an empty list."""
        with patch("pythaw.finder._git_ls_files", return_value=None):
            result = collect_files(tmp_path, Config())
        assert result == []


class TestGitIgnoreIntegration:
    """Verify .gitignore is respected when git is available."""

    def test_gitignored_files_are_excluded(self, tmp_path: Path) -> None:
        """Files listed in .gitignore are not returned."""
        _git(tmp_path, "init")
        (tmp_path / ".gitignore").write_text("ignored/\n")
        _make_files(tmp_path, {"app.py": "", "ignored/secret.py": ""})
        _git(tmp_path, "add", ".")
        result = collect_files(tmp_path, Config())
        names = [p.name for p in result]
        assert "secret.py" not in names
        assert "app.py" in names

    def test_untracked_files_are_included(self, tmp_path: Path) -> None:
        """Untracked (but not ignored) files are still discovered."""
        _git(tmp_path, "init")
        _make_files(tmp_path, {"tracked.py": "", "untracked.py": ""})
        _git(tmp_path, "add", "tracked.py")
        result = collect_files(tmp_path, Config())
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
            result = collect_files(tmp_path, Config())
        assert len(result) == 1
        assert result[0].name == "app.py"

    def test_falls_back_when_not_git_repo(self, tmp_path: Path) -> None:
        """When directory is not a git repo, rglob fallback is used."""
        _make_files(tmp_path, {"app.py": ""})
        result = collect_files(tmp_path, Config())
        assert len(result) == 1
        assert result[0].name == "app.py"


# ---------------------------------------------------------------------------
# find_handlers
# ---------------------------------------------------------------------------


class TestFindHandlers:
    """Verify handler discovery with fnmatch pattern matching."""

    def test_finds_handler(self, tmp_path: Path) -> None:
        """Matches a top-level function named 'handler'."""
        _make_files(tmp_path, {"app.py": "def handler(event, context):\n    pass\n"})
        with patch("pythaw.finder._git_ls_files", return_value=None):
            result = find_handlers(tmp_path, Config())
        assert len(result) == 1
        assert result[0].name == "handler"
        assert result[0].file == (tmp_path / "app.py").resolve()

    def test_finds_lambda_handler(self, tmp_path: Path) -> None:
        """Matches a top-level function named 'lambda_handler'."""
        _make_files(
            tmp_path,
            {"app.py": "def lambda_handler(event, context):\n    pass\n"},
        )
        with patch("pythaw.finder._git_ls_files", return_value=None):
            result = find_handlers(tmp_path, Config())
        assert len(result) == 1
        assert result[0].name == "lambda_handler"

    def test_finds_wildcard_handler(self, tmp_path: Path) -> None:
        """Matches a top-level function matching *_handler pattern."""
        _make_files(
            tmp_path,
            {"app.py": "def my_handler(event, context):\n    pass\n"},
        )
        with patch("pythaw.finder._git_ls_files", return_value=None):
            result = find_handlers(tmp_path, Config())
        assert len(result) == 1
        assert result[0].name == "my_handler"

    def test_ignores_non_matching_functions(self, tmp_path: Path) -> None:
        """Functions not matching any handler pattern are ignored."""
        _make_files(
            tmp_path,
            {"app.py": "def process_data(data):\n    pass\n"},
        )
        with patch("pythaw.finder._git_ls_files", return_value=None):
            result = find_handlers(tmp_path, Config())
        assert result == []

    def test_custom_handler_patterns(self, tmp_path: Path) -> None:
        """Uses handler_patterns from config instead of defaults."""
        _make_files(
            tmp_path,
            {"app.py": "def my_entry(event, context):\n    pass\n"},
        )
        cfg = Config(handler_patterns=("my_entry",))
        with patch("pythaw.finder._git_ls_files", return_value=None):
            result = find_handlers(tmp_path, cfg)
        assert len(result) == 1
        assert result[0].name == "my_entry"

    def test_only_matches_top_level_functions(self, tmp_path: Path) -> None:
        """Nested functions and class methods are not detected as handlers."""
        source = (
            "class MyClass:\n"
            "    def handler(self):\n"
            "        pass\n"
            "\n"
            "def outer():\n"
            "    def handler():\n"
            "        pass\n"
        )
        _make_files(tmp_path, {"app.py": source})
        with patch("pythaw.finder._git_ls_files", return_value=None):
            result = find_handlers(tmp_path, Config())
        assert result == []

    def test_multiple_handlers_in_one_file(self, tmp_path: Path) -> None:
        """Multiple matching functions in a single file are all returned."""
        source = (
            "def handler(event, context):\n"
            "    pass\n"
            "\n"
            "def lambda_handler(event, context):\n"
            "    pass\n"
        )
        _make_files(tmp_path, {"app.py": source})
        with patch("pythaw.finder._git_ls_files", return_value=None):
            result = find_handlers(tmp_path, Config())
        names = [h.name for h in result]
        assert "handler" in names
        assert "lambda_handler" in names

    def test_handlers_across_multiple_files(self, tmp_path: Path) -> None:
        """Handlers in different files are all discovered."""
        _make_files(
            tmp_path,
            {
                "a.py": "def handler(event, context):\n    pass\n",
                "b.py": "def lambda_handler(event, context):\n    pass\n",
            },
        )
        with patch("pythaw.finder._git_ls_files", return_value=None):
            result = find_handlers(tmp_path, Config())
        names = sorted(h.name for h in result)
        assert names == ["handler", "lambda_handler"]

    def test_returns_correct_lineno_and_col_offset(self, tmp_path: Path) -> None:
        """HandlerFunction contains correct line number and column offset."""
        source = "\n\ndef handler(event, context):\n    pass\n"
        _make_files(tmp_path, {"app.py": source})
        with patch("pythaw.finder._git_ls_files", return_value=None):
            result = find_handlers(tmp_path, Config())
        assert len(result) == 1
        assert result[0].lineno == 3
        assert result[0].col_offset == 0

    def test_single_file_path(self, tmp_path: Path) -> None:
        """A single file path is checked directly for handlers."""
        py = tmp_path / "app.py"
        py.write_text("def handler(event, context):\n    pass\n")
        result = find_handlers(py, Config())
        assert len(result) == 1
        assert result[0].name == "handler"


class TestFindHandlersEdgeCases:
    """Verify handler discovery edge cases."""

    def test_skips_syntax_error_files(self, tmp_path: Path) -> None:
        """Files with syntax errors are skipped without raising."""
        _make_files(
            tmp_path,
            {
                "good.py": "def handler(event, context):\n    pass\n",
                "bad.py": "def handler(event, context\n",
            },
        )
        with patch("pythaw.finder._git_ls_files", return_value=None):
            result = find_handlers(tmp_path, Config())
        assert len(result) == 1
        assert result[0].file == (tmp_path / "good.py").resolve()

    def test_empty_file_no_handlers(self, tmp_path: Path) -> None:
        """An empty Python file yields no handlers."""
        _make_files(tmp_path, {"empty.py": ""})
        with patch("pythaw.finder._git_ls_files", return_value=None):
            result = find_handlers(tmp_path, Config())
        assert result == []

    def test_async_handler(self, tmp_path: Path) -> None:
        """Async handler functions are also detected."""
        source = "async def handler(event, context):\n    pass\n"
        _make_files(tmp_path, {"app.py": source})
        with patch("pythaw.finder._git_ls_files", return_value=None):
            result = find_handlers(tmp_path, Config())
        assert len(result) == 1
        assert result[0].name == "handler"
