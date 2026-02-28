from __future__ import annotations

import subprocess
import sys
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from pathlib import Path


def _run_pythaw(*args: str, cwd: Path) -> subprocess.CompletedProcess[str]:
    """Run the pythaw CLI as a subprocess."""
    return subprocess.run(  # noqa: S603
        [sys.executable, "-m", "pythaw", *args],
        cwd=cwd,
        capture_output=True,
        text=True,
        check=False,
    )


def _make_files(base: Path, files: dict[str, str]) -> None:
    """Create files under *base* with the given content."""
    for name, content in files.items():
        p = base / name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content)


class TestCheckE2E:
    """End-to-end tests for the 'check' subcommand."""

    def test_detects_violation_and_exits_1(self, tmp_path: Path) -> None:
        """Violations produce concise output and exit code 1."""
        _make_files(
            tmp_path,
            {
                "app.py": (
                    "import boto3\n"
                    "\n"
                    "def handler(event, context):\n"
                    '    client = boto3.client("s3")\n'
                ),
            },
        )
        result = _run_pythaw("check", ".", cwd=tmp_path)
        assert result.returncode == 1
        assert "PW001" in result.stdout
        assert "boto3.client()" in result.stdout
        assert "Found 1 violation in 1 file." in result.stdout

    def test_clean_code_exits_0(self, tmp_path: Path) -> None:
        """No violations produce no output and exit code 0."""
        _make_files(
            tmp_path,
            {
                "app.py": (
                    "import boto3\n"
                    "\n"
                    "client = boto3.client('s3')\n"
                    "\n"
                    "def handler(event, context):\n"
                    "    return client.get_object(Bucket='b', Key='k')\n"
                ),
            },
        )
        result = _run_pythaw("check", ".", cwd=tmp_path)
        assert result.returncode == 0
        assert result.stdout == ""

    def test_multiple_violations_across_files(self, tmp_path: Path) -> None:
        """Multiple violations across files are all reported."""
        _make_files(
            tmp_path,
            {
                "a.py": (
                    "import boto3\n"
                    "def handler(event, context):\n"
                    '    boto3.client("s3")\n'
                ),
                "b.py": (
                    "import boto3\n"
                    "def lambda_handler(event, context):\n"
                    '    boto3.resource("dynamodb")\n'
                ),
            },
        )
        result = _run_pythaw("check", ".", cwd=tmp_path)
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
