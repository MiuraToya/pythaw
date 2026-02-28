from __future__ import annotations

import os
from pathlib import Path

import pytest

from pythaw.config import Config, ConfigError


def _chdir(path: Path) -> Path:
    """Change to *path* and return the previous working directory."""
    original = Path.cwd()
    os.chdir(path)
    return original


class TestConfigLoad:
    """Verify Config.load() reads pyproject.toml via automatic discovery."""

    def test_load_with_tool_pythaw_section(self, tmp_path: Path) -> None:
        """Both handler_patterns and exclude are read correctly."""
        (tmp_path / "pyproject.toml").write_text(
            '[tool.pythaw]\nhandler_patterns = ["my_handler"]\nexclude = ["vendor/"]\n'
        )
        original = _chdir(tmp_path)
        try:
            cfg = Config.load()
            assert cfg.handler_patterns == ("my_handler",)
            assert cfg.exclude == ("vendor/",)
        finally:
            os.chdir(original)

    def test_load_without_tool_pythaw_section(self, tmp_path: Path) -> None:
        """Missing [tool.pythaw] section falls back to defaults."""
        (tmp_path / "pyproject.toml").write_text("[project]\nname = 'foo'\n")
        original = _chdir(tmp_path)
        try:
            cfg = Config.load()
            assert cfg.handler_patterns == ("handler", "lambda_handler", "*_handler")
            assert cfg.exclude == ()
        finally:
            os.chdir(original)

    def test_load_handler_patterns_only(self, tmp_path: Path) -> None:
        """Only handler_patterns specified; exclude keeps its default."""
        (tmp_path / "pyproject.toml").write_text(
            '[tool.pythaw]\nhandler_patterns = ["entry"]\n'
        )
        original = _chdir(tmp_path)
        try:
            cfg = Config.load()
            assert cfg.handler_patterns == ("entry",)
            assert cfg.exclude == ()
        finally:
            os.chdir(original)

    def test_load_exclude_only(self, tmp_path: Path) -> None:
        """Only exclude specified; handler_patterns keeps its default."""
        (tmp_path / "pyproject.toml").write_text(
            '[tool.pythaw]\nexclude = ["tests/"]\n'
        )
        original = _chdir(tmp_path)
        try:
            cfg = Config.load()
            assert cfg.handler_patterns == ("handler", "lambda_handler", "*_handler")
            assert cfg.exclude == ("tests/",)
        finally:
            os.chdir(original)

    def test_discovers_pyproject_in_parent(self, tmp_path: Path) -> None:
        """Walks up parent directories to find pyproject.toml."""
        (tmp_path / "pyproject.toml").write_text(
            '[tool.pythaw]\nexclude = ["from_parent/"]\n'
        )
        child = tmp_path / "sub" / "dir"
        child.mkdir(parents=True)
        original = _chdir(child)
        try:
            cfg = Config.load()
            assert cfg.exclude == ("from_parent/",)
        finally:
            os.chdir(original)

    def test_no_pyproject_returns_default(self, tmp_path: Path) -> None:
        """No pyproject.toml anywhere in the hierarchy falls back to defaults."""
        empty = tmp_path / "empty"
        empty.mkdir()
        original = _chdir(empty)
        try:
            cfg = Config.load()
            assert cfg.handler_patterns == ("handler", "lambda_handler", "*_handler")
            assert cfg.exclude == ()
        finally:
            os.chdir(original)


class TestConfigValidation:
    """Verify that invalid [tool.pythaw] values raise ConfigError."""

    @pytest.mark.parametrize(
        "toml_content",
        [
            "[tool.pythaw]\nhandler_patterns = 42\n",
            '[tool.pythaw]\nhandler_patterns = ["ok", 1]\n',
        ],
    )
    def test_handler_patterns_invalid(self, tmp_path: Path, toml_content: str) -> None:
        """Non-string or non-list handler_patterns raises ConfigError."""
        (tmp_path / "pyproject.toml").write_text(toml_content)
        original = _chdir(tmp_path)
        try:
            with pytest.raises(ConfigError, match="handler_patterns must be a list"):
                Config.load()
        finally:
            os.chdir(original)

    @pytest.mark.parametrize(
        "toml_content",
        [
            "[tool.pythaw]\nexclude = true\n",
            '[tool.pythaw]\nexclude = ["ok", 1]\n',
        ],
    )
    def test_exclude_invalid(self, tmp_path: Path, toml_content: str) -> None:
        """Non-string or non-list exclude raises ConfigError."""
        (tmp_path / "pyproject.toml").write_text(toml_content)
        original = _chdir(tmp_path)
        try:
            with pytest.raises(ConfigError, match="exclude must be a list"):
                Config.load()
        finally:
            os.chdir(original)

    def test_invalid_toml_raises_config_error(self, tmp_path: Path) -> None:
        """Malformed TOML syntax raises ConfigError."""
        (tmp_path / "pyproject.toml").write_text("[tool.pythaw\n")
        original = _chdir(tmp_path)
        try:
            with pytest.raises(ConfigError, match="Failed to read"):
                Config.load()
        finally:
            os.chdir(original)
