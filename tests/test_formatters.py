from __future__ import annotations

import json

from pythaw.formatters import ConciseFormatter, get_formatter
from pythaw.formatters.github import GithubFormatter
from pythaw.formatters.json import JsonFormatter
from pythaw.formatters.sarif import SarifFormatter
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


SAMPLE_VIOLATIONS = [
    Violation(
        file="handler.py",
        line=15,
        col=4,
        code="PW001",
        message="boto3.client() should be called at module scope",
    ),
    Violation(
        file="other.py",
        line=10,
        col=4,
        code="PW002",
        message=("boto3.resource() should be called at module scope"),
    ),
]


class TestJsonFormatter:
    """Verify JSON output format."""

    def setup_method(self) -> None:
        self.formatter = JsonFormatter()

    def test_valid_json(self) -> None:
        """Output is valid JSON."""
        result = self.formatter.format(SAMPLE_VIOLATIONS)
        data = json.loads(result)
        assert isinstance(data, list)
        assert len(data) == 2

    def test_fields(self) -> None:
        """Each entry contains file, line, col, code, message."""
        result = self.formatter.format(SAMPLE_VIOLATIONS)
        data = json.loads(result)
        entry = data[0]
        assert entry["file"] == "handler.py"
        assert entry["line"] == 15
        assert entry["col"] == 4
        assert entry["code"] == "PW001"

    def test_empty(self) -> None:
        """Empty list returns empty JSON array."""
        result = self.formatter.format([])
        assert json.loads(result) == []


class TestGithubFormatter:
    """Verify GitHub Actions annotation format."""

    def setup_method(self) -> None:
        self.formatter = GithubFormatter()

    def test_annotation_format(self) -> None:
        """Output uses ::error annotation syntax."""
        result = self.formatter.format(SAMPLE_VIOLATIONS)
        lines = result.strip().splitlines()
        assert len(lines) == 2
        assert lines[0].startswith("::error ")
        assert "file=handler.py" in lines[0]
        assert "line=15" in lines[0]
        assert "col=4" in lines[0]
        assert "PW001" in lines[0]

    def test_empty(self) -> None:
        """Empty list returns empty string."""
        assert self.formatter.format([]) == ""


class TestSarifFormatter:
    """Verify SARIF output format."""

    def setup_method(self) -> None:
        self.formatter = SarifFormatter()

    def test_valid_sarif_structure(self) -> None:
        """Output is valid SARIF JSON with required fields."""
        result = self.formatter.format(SAMPLE_VIOLATIONS)
        data = json.loads(result)
        assert data["$schema"] is not None
        assert data["version"] == "2.1.0"
        runs = data["runs"]
        assert len(runs) == 1
        assert runs[0]["tool"]["driver"]["name"] == "pythaw"

    def test_results_count(self) -> None:
        """SARIF results match violation count."""
        result = self.formatter.format(SAMPLE_VIOLATIONS)
        data = json.loads(result)
        results = data["runs"][0]["results"]
        assert len(results) == 2

    def test_result_fields(self) -> None:
        """Each SARIF result has ruleId and location."""
        result = self.formatter.format(SAMPLE_VIOLATIONS)
        data = json.loads(result)
        r = data["runs"][0]["results"][0]
        assert r["ruleId"] == "PW001"
        loc = r["locations"][0]["physicalLocation"]
        assert loc["artifactLocation"]["uri"] == "handler.py"
        assert loc["region"]["startLine"] == 15
        assert loc["region"]["startColumn"] == 4

    def test_empty(self) -> None:
        """Empty list returns SARIF with empty results."""
        result = self.formatter.format([])
        data = json.loads(result)
        assert data["runs"][0]["results"] == []


class TestFormatterRegistry:
    """Verify get_formatter() registry lookup."""

    def test_get_concise_formatter(self) -> None:
        """'concise' key returns a ConciseFormatter instance."""
        formatter = get_formatter("concise")
        assert isinstance(formatter, ConciseFormatter)

    def test_get_json_formatter(self) -> None:
        """'json' key returns a JsonFormatter instance."""
        formatter = get_formatter("json")
        assert isinstance(formatter, JsonFormatter)

    def test_get_github_formatter(self) -> None:
        """'github' key returns a GithubFormatter instance."""
        formatter = get_formatter("github")
        assert isinstance(formatter, GithubFormatter)

    def test_get_sarif_formatter(self) -> None:
        """'sarif' key returns a SarifFormatter instance."""
        formatter = get_formatter("sarif")
        assert isinstance(formatter, SarifFormatter)

    def test_get_unknown_formatter(self) -> None:
        """Unknown key returns None."""
        formatter = get_formatter("unknown")
        assert formatter is None
