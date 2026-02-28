from __future__ import annotations

from pythaw.formatters import ConciseFormatter, get_formatter
from pythaw.violation import Violation


class TestConciseFormatter:
    """Verify concise format: 'file:line:col: code message' + summary line."""

    def setup_method(self) -> None:
        self.formatter = ConciseFormatter()

    def test_single_violation(self) -> None:
        """Formats one violation with a '1 violation in 1 file' summary."""
        violations = [
            Violation(
                file="handler.py",
                line=15,
                col=4,
                code="PW001",
                message="boto3.client() should be called at module scope",
            ),
        ]
        result = self.formatter.format(violations)

        expected = (
            "handler.py:15:4: PW001 boto3.client() should be called at module scope\n"
            "\n"
            "Found 1 violation in 1 file."
        )
        assert result == expected

    def test_multiple_violations_multiple_files(self) -> None:
        """Formats violations across multiple files with correct summary counts."""
        violations = [
            Violation(
                file="handler.py",
                line=15,
                col=4,
                code="PW001",
                message="boto3.client() should be called at module scope",
            ),
            Violation(
                file="handler.py",
                line=23,
                col=8,
                code="PW002",
                message="boto3.resource() should be called at module scope",
            ),
            Violation(
                file="other.py",
                line=10,
                col=4,
                code="PW001",
                message="boto3.client() should be called at module scope",
            ),
        ]
        result = self.formatter.format(violations)

        expected = (
            "handler.py:15:4: PW001 boto3.client() should be called at module scope\n"
            "handler.py:23:8: PW002 boto3.resource() should be called at module scope\n"
            "other.py:10:4: PW001 boto3.client() should be called at module scope\n"
            "\n"
            "Found 3 violations in 2 files."
        )
        assert result == expected

    def test_no_violations(self) -> None:
        """Empty violation list returns empty string."""
        result = self.formatter.format([])
        assert result == ""


class TestFormatterRegistry:
    """Verify get_formatter() registry lookup."""

    def test_get_concise_formatter(self) -> None:
        """'concise' key returns a ConciseFormatter instance."""
        formatter = get_formatter("concise")
        assert isinstance(formatter, ConciseFormatter)

    def test_get_unknown_formatter(self) -> None:
        """Unknown key returns None."""
        formatter = get_formatter("unknown")
        assert formatter is None
