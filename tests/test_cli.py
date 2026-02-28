from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import patch

import pytest

from pythaw.cli import main

if TYPE_CHECKING:
    from pathlib import Path


def _make_files(base: Path, files: dict[str, str]) -> None:
    """Create files under *base* with the given content."""
    for name, content in files.items():
        p = base / name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content)


class TestCheckSubcommand:
    """Verify the 'check' subcommand behaviour."""

    def test_violations_exit_code_1(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Exits with code 1 and prints violations when issues are found."""
        source = 'import boto3\ndef handler(event, context):\n    boto3.client("s3")\n'
        _make_files(tmp_path, {"app.py": source})
        with (
            patch("pythaw.finder._git_ls_files", return_value=None),
            pytest.raises(SystemExit) as exc_info,
        ):
            main(["check", str(tmp_path)])
        assert exc_info.value.code == 1
        out = capsys.readouterr().out
        assert "PW001" in out
        assert "Found 1 violation" in out

    def test_no_violations_exit_code_0(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Exits with code 0 and prints a success message when no issues are found."""
        source = "def handler(event, context):\n    return 200\n"
        _make_files(tmp_path, {"app.py": source})
        with (
            patch("pythaw.finder._git_ls_files", return_value=None),
            pytest.raises(SystemExit) as exc_info,
        ):
            main(["check", str(tmp_path)])
        assert exc_info.value.code == 0
        assert capsys.readouterr().out == "All checks passed!\n"

    def test_config_error_exit_code_2(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Exits with code 2 and prints error when config is invalid."""
        _make_files(
            tmp_path,
            {
                "pyproject.toml": "[tool.pythaw]\nhandler_patterns = 42\n",
                "app.py": "def handler(event, context):\n    pass\n",
            },
        )
        toml = tmp_path / "pyproject.toml"
        with (
            patch("pythaw.config._find_pyproject", return_value=toml),
            pytest.raises(SystemExit) as exc_info,
        ):
            main(["check", str(tmp_path)])
        assert exc_info.value.code == 2
        assert capsys.readouterr().err != ""


class TestExitZeroOption:
    """Verify --exit-zero CLI option."""

    def test_exit_zero_with_violations(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """--exit-zero returns 0 even when violations exist."""
        source = (
            "import boto3\n"
            "def handler(event, context):\n"
            '    boto3.client("s3")\n'
        )
        _make_files(tmp_path, {"app.py": source})
        with (
            patch("pythaw.finder._git_ls_files", return_value=None),
            pytest.raises(SystemExit) as exc_info,
        ):
            main(["check", str(tmp_path), "--exit-zero"])
        assert exc_info.value.code == 0
        out = capsys.readouterr().out
        assert "PW001" in out

    def test_exit_zero_without_violations(
        self, tmp_path: Path
    ) -> None:
        """--exit-zero still returns 0 when no violations."""
        source = "def handler(event, context):\n    return 200\n"
        _make_files(tmp_path, {"app.py": source})
        with (
            patch("pythaw.finder._git_ls_files", return_value=None),
            pytest.raises(SystemExit) as exc_info,
        ):
            main(["check", str(tmp_path), "--exit-zero"])
        assert exc_info.value.code == 0


class TestStatisticsOption:
    """Verify --statistics CLI option."""

    def test_statistics_output(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """--statistics appends per-rule violation counts."""
        source = (
            "import boto3\n"
            "def handler(event, context):\n"
            '    boto3.client("s3")\n'
            '    boto3.resource("s3")\n'
            '    boto3.client("dynamodb")\n'
        )
        _make_files(tmp_path, {"app.py": source})
        with (
            patch("pythaw.finder._git_ls_files", return_value=None),
            pytest.raises(SystemExit) as exc_info,
        ):
            main(["check", str(tmp_path), "--statistics"])
        assert exc_info.value.code == 1
        out = capsys.readouterr().out
        assert "PW001  2" in out
        assert "PW002  1" in out


class TestRulesSubcommand:
    """Verify the 'rules' subcommand behaviour."""

    def test_lists_all_rules(self, capsys: pytest.CaptureFixture[str]) -> None:
        """Prints all built-in rules with code and message."""
        with pytest.raises(SystemExit) as exc_info:
            main(["rules"])
        assert exc_info.value.code == 0
        out = capsys.readouterr().out
        assert "PW001" in out
        assert "PW002" in out
        assert "PW003" in out


class TestRuleSubcommand:
    """Verify the 'rule' subcommand behaviour."""

    def test_shows_rule_detail(self, capsys: pytest.CaptureFixture[str]) -> None:
        """Prints what/why/example for a known rule code."""
        with pytest.raises(SystemExit) as exc_info:
            main(["rule", "PW001"])
        assert exc_info.value.code == 0
        out = capsys.readouterr().out
        assert "What it does" in out
        assert "Why is this bad" in out
        assert "Example" in out

    def test_unknown_code_exit_code_2(self, capsys: pytest.CaptureFixture[str]) -> None:
        """Exits with code 2 when an unknown rule code is given."""
        with pytest.raises(SystemExit) as exc_info:
            main(["rule", "PW999"])
        assert exc_info.value.code == 2
        assert capsys.readouterr().err != ""
