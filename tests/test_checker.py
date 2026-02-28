from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import patch

import pytest

from pythaw.checker import check
from pythaw.config import Config

if TYPE_CHECKING:
    from pathlib import Path


def _make_files(base: Path, files: dict[str, str]) -> None:
    """Create files under *base* with the given content."""
    for name, content in files.items():
        p = base / name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content)


class TestCheckDirectViolations:
    """Verify detection of rule violations directly inside handler functions."""

    @pytest.mark.parametrize(
        ("call", "code"),
        [
            ('boto3.client("s3")', "PW001"),
            ('boto3.resource("s3")', "PW002"),
            ("boto3.Session()", "PW003"),
        ],
        ids=["PW001", "PW002", "PW003"],
    )
    def test_detects_violation(self, tmp_path: Path, call: str, code: str) -> None:
        """Each built-in rule detects its corresponding boto3 call in a handler."""
        source = f"def handler(event, context):\n    {call}\n"
        _make_files(tmp_path, {"app.py": source})
        with patch("pythaw.finder._git_ls_files", return_value=None):
            violations = check(tmp_path, Config())
        assert len(violations) == 1
        assert violations[0].code == code

    def test_no_violation_at_module_scope(self, tmp_path: Path) -> None:
        """Calls at module scope (outside handler) are not flagged."""
        source = (
            "import boto3\n"
            "\n"
            'client = boto3.client("s3")\n'
            "\n"
            "def handler(event, context):\n"
            "    return client.get_object(Bucket='b', Key='k')\n"
        )
        _make_files(tmp_path, {"app.py": source})
        with patch("pythaw.finder._git_ls_files", return_value=None):
            violations = check(tmp_path, Config())
        assert violations == []

    def test_no_violation_without_matching_calls(self, tmp_path: Path) -> None:
        """Handler with no boto3 calls produces no violations."""
        source = "def handler(event, context):\n    return {'statusCode': 200}\n"
        _make_files(tmp_path, {"app.py": source})
        with patch("pythaw.finder._git_ls_files", return_value=None):
            violations = check(tmp_path, Config())
        assert violations == []

    def test_multiple_violations_in_one_handler(self, tmp_path: Path) -> None:
        """Multiple violating calls in a single handler are all reported."""
        source = (
            "import boto3\n"
            "\n"
            "def handler(event, context):\n"
            '    client = boto3.client("s3")\n'
            '    resource = boto3.resource("s3")\n'
        )
        _make_files(tmp_path, {"app.py": source})
        with patch("pythaw.finder._git_ls_files", return_value=None):
            violations = check(tmp_path, Config())
        codes = sorted(v.code for v in violations)
        assert codes == ["PW001", "PW002"]

    def test_violation_in_nested_function(self, tmp_path: Path) -> None:
        """Calls inside a nested function within a handler are detected."""
        source = (
            "import boto3\n"
            "\n"
            "def handler(event, context):\n"
            "    def helper():\n"
            '        boto3.client("s3")\n'
            "    helper()\n"
        )
        _make_files(tmp_path, {"app.py": source})
        with patch("pythaw.finder._git_ls_files", return_value=None):
            violations = check(tmp_path, Config())
        assert len(violations) == 1
        assert violations[0].code == "PW001"


class TestCheckPositionInfo:
    """Verify that violations carry correct file, line, and column info."""

    def test_correct_position(self, tmp_path: Path) -> None:
        """Violation points to the exact call location."""
        source = (
            "import boto3\n"
            "\n"
            "def handler(event, context):\n"
            '    client = boto3.client("s3")\n'
        )
        _make_files(tmp_path, {"app.py": source})
        with patch("pythaw.finder._git_ls_files", return_value=None):
            violations = check(tmp_path, Config())
        assert len(violations) == 1
        v = violations[0]
        assert v.file == str((tmp_path / "app.py").resolve())
        assert v.line == 4
        assert v.col == 13


class TestCheckEdgeCases:
    """Verify edge cases for the checker."""

    def test_skips_syntax_error_files(self, tmp_path: Path) -> None:
        """Files with syntax errors are skipped without raising."""
        _make_files(
            tmp_path,
            {
                "good.py": (
                    "import boto3\n"
                    "def handler(event, context):\n"
                    '    boto3.client("s3")\n'
                ),
                "bad.py": "def handler(event, context\n",
            },
        )
        with patch("pythaw.finder._git_ls_files", return_value=None):
            violations = check(tmp_path, Config())
        assert len(violations) == 1
        assert violations[0].file == str((tmp_path / "good.py").resolve())

    def test_single_file_path(self, tmp_path: Path) -> None:
        """Check works when given a single file path."""
        py = tmp_path / "app.py"
        py.write_text(
            'import boto3\ndef handler(event, context):\n    boto3.client("s3")\n'
        )
        violations = check(py, Config())
        assert len(violations) == 1
        assert violations[0].code == "PW001"
