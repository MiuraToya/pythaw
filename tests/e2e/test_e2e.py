from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

import pytest

FIXTURES_DIR = Path(__file__).parent / "fixtures"


def _run_pythaw(*args: str, cwd: Path) -> subprocess.CompletedProcess[str]:
    """Run the pythaw CLI as a subprocess."""
    return subprocess.run(  # noqa: S603
        [sys.executable, "-m", "pythaw", *args],
        cwd=cwd,
        capture_output=True,
        text=True,
        check=False,
    )


def _use_fixture(name: str, tmp_path: Path) -> Path:
    """Copy a fixture directory into *tmp_path* and return the copy path."""
    dst = tmp_path / name
    shutil.copytree(FIXTURES_DIR / name, dst)
    return dst


class TestCheckE2E:
    """End-to-end tests for the 'check' subcommand."""

    def test_detects_violation_and_exits_1(self, tmp_path: Path) -> None:
        """Violations produce concise output with relative paths and exit code 1."""
        cwd = _use_fixture("violation", tmp_path)
        result = _run_pythaw("check", ".", cwd=cwd)
        assert result.returncode == 1
        assert "PW001" in result.stdout
        assert "boto3.client()" in result.stdout
        assert "Found 1 violation in 1 file." in result.stdout
        assert result.stdout.startswith("app.py:")

    def test_clean_code_exits_0(self, tmp_path: Path) -> None:
        """No violations produce no output and exit code 0."""
        cwd = _use_fixture("clean", tmp_path)
        result = _run_pythaw("check", ".", cwd=cwd)
        assert result.returncode == 0
        assert result.stdout == ""

    def test_multiple_violations_across_files(self, tmp_path: Path) -> None:
        """Multiple violations across files are all reported."""
        cwd = _use_fixture("multi_violation", tmp_path)
        result = _run_pythaw("check", ".", cwd=cwd)
        assert result.returncode == 1
        assert "PW001" in result.stdout
        assert "PW002" in result.stdout
        assert "Found 2 violations in 2 files." in result.stdout


class TestRulesE2E:
    """End-to-end tests for the 'rules' subcommand."""

    def test_lists_rules(self, tmp_path: Path) -> None:
        """Lists all built-in rules."""
        result = _run_pythaw("rules", cwd=tmp_path)
        assert result.returncode == 0
        assert "PW001" in result.stdout
        assert "PW002" in result.stdout
        assert "PW003" in result.stdout


class TestRuleE2E:
    """End-to-end tests for the 'rule' subcommand."""

    @pytest.mark.parametrize("code", ["PW001", "PW002", "PW003"])
    def test_shows_rule_detail(self, tmp_path: Path, code: str) -> None:
        """Shows what/why/example for each rule."""
        result = _run_pythaw("rule", code, cwd=tmp_path)
        assert result.returncode == 0
        assert "What it does" in result.stdout
        assert "Example" in result.stdout

    def test_unknown_code_exits_2(self, tmp_path: Path) -> None:
        """Unknown rule code produces error and exit code 2."""
        result = _run_pythaw("rule", "PW999", cwd=tmp_path)
        assert result.returncode == 2
        assert "Unknown rule" in result.stderr


class TestNoSubcommandE2E:
    """End-to-end tests for missing subcommand."""

    def test_no_args_exits_2(self, tmp_path: Path) -> None:
        """Running without subcommand exits with code 2."""
        result = _run_pythaw(cwd=tmp_path)
        assert result.returncode == 2


class TestConfigE2E:
    """End-to-end tests for pyproject.toml configuration."""

    def test_custom_handler_patterns(self, tmp_path: Path) -> None:
        """Custom handler_patterns detects non-default function names."""
        cwd = _use_fixture("custom_patterns", tmp_path)
        result = _run_pythaw("check", ".", cwd=cwd)
        assert result.returncode == 1
        assert "PW001" in result.stdout

    def test_custom_patterns_ignore_default(self, tmp_path: Path) -> None:
        """Custom handler_patterns replaces defaults entirely."""
        cwd = _use_fixture("custom_patterns_no_default", tmp_path)
        result = _run_pythaw("check", ".", cwd=cwd)
        assert result.returncode == 0

    def test_exclude_filters_directory(self, tmp_path: Path) -> None:
        """Excluded directories are skipped during check."""
        cwd = _use_fixture("exclude_dir", tmp_path)
        result = _run_pythaw("check", ".", cwd=cwd)
        assert result.returncode == 0

    def test_invalid_toml_exits_2(self, tmp_path: Path) -> None:
        """Malformed pyproject.toml produces error and exit code 2."""
        cwd = _use_fixture("invalid_toml", tmp_path)
        result = _run_pythaw("check", ".", cwd=cwd)
        assert result.returncode == 2
        assert "Failed to read" in result.stderr

    def test_invalid_config_value_exits_2(self, tmp_path: Path) -> None:
        """Non-list handler_patterns produces error and exit code 2."""
        cwd = _use_fixture("invalid_config_value", tmp_path)
        result = _run_pythaw("check", ".", cwd=cwd)
        assert result.returncode == 2
        assert "must be a list" in result.stderr


class TestHandlerPatternsE2E:
    """End-to-end tests for various handler patterns."""

    def test_non_existent_path_exits_0(self, tmp_path: Path) -> None:
        """Non-existent path produces no violations."""
        result = _run_pythaw("check", "no_such_dir", cwd=tmp_path)
        assert result.returncode == 0

    def test_multiple_handlers_in_one_file(self, tmp_path: Path) -> None:
        """Multiple handlers in a single file each produce violations."""
        cwd = _use_fixture("multi_handler", tmp_path)
        result = _run_pythaw("check", ".", cwd=cwd)
        assert result.returncode == 1
        assert "PW001" in result.stdout
        assert "PW003" in result.stdout
        assert "2 violations" in result.stdout

    def test_async_handler(self, tmp_path: Path) -> None:
        """Async handler functions are also checked."""
        cwd = _use_fixture("async_handler", tmp_path)
        result = _run_pythaw("check", ".", cwd=cwd)
        assert result.returncode == 1
        assert "PW001" in result.stdout

    def test_non_handler_function_not_checked(self, tmp_path: Path) -> None:
        """Functions not matching handler patterns are ignored."""
        cwd = _use_fixture("non_handler", tmp_path)
        result = _run_pythaw("check", ".", cwd=cwd)
        assert result.returncode == 0

    def test_nested_call_in_handler(self, tmp_path: Path) -> None:
        """Nested boto3 calls inside handler are detected."""
        cwd = _use_fixture("nested_call", tmp_path)
        result = _run_pythaw("check", ".", cwd=cwd)
        assert result.returncode == 1
        assert "PW001" in result.stdout
