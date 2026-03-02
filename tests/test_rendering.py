"""Tests for the rich-based rendering module."""

from __future__ import annotations

from collections import Counter
from io import StringIO

from rich.console import Console

from pythaw import rendering
from pythaw.rules import get_all_rules, get_rule
from pythaw.violation import CallSite, Violation


def _capture(func, *args):  # type: ignore[no-untyped-def]
    """Call *func* while capturing console output and return the text."""
    buf = StringIO()
    original = rendering.console
    rendering.console = Console(file=buf, highlight=False, width=200)
    try:
        func(*args)
    finally:
        rendering.console = original
    return buf.getvalue()


class TestPrintViolations:
    """Verify print_violations output."""

    def test_single_violation(self) -> None:
        """Renders a single violation with file location, code, and summary."""
        violations = [
            Violation(file="app.py", line=3, col=4, code="PW001", message="test msg"),
        ]
        out = _capture(rendering.print_violations, violations)
        assert "PW001 test msg" in out
        assert "--> app.py:3:4" in out
        assert "Found 1 violation in 1 file." in out

    def test_multiple_violations_plural(self) -> None:
        """Renders correct plural summary for multiple violations across files."""
        violations = [
            Violation(file="a.py", line=1, col=0, code="PW001", message="msg1"),
            Violation(file="b.py", line=2, col=0, code="PW002", message="msg2"),
        ]
        out = _capture(rendering.print_violations, violations)
        assert "Found 2 violations in 2 files." in out

    def test_call_chain_indentation(self) -> None:
        """Renders via chain with increasing indentation per depth level."""
        violations = [
            Violation(
                file="handler.py",
                line=10,
                col=4,
                code="PW001",
                message="test",
                call_chain=(
                    CallSite(file="a.py", line=5, col=4, name="foo()"),
                    CallSite(file="b.py", line=8, col=4, name="bar()"),
                ),
            ),
        ]
        out = _capture(rendering.print_violations, violations)
        lines = out.splitlines()
        via_lines = [line for line in lines if "\u2192" in line]
        assert len(via_lines) == 2
        # Second via line should have more leading whitespace than first
        assert len(via_lines[1]) - len(via_lines[1].lstrip()) > len(via_lines[0]) - len(
            via_lines[0].lstrip()
        )


class TestPrintSuccess:
    """Verify print_success output."""

    def test_success_message(self) -> None:
        """Prints the success message text."""
        out = _capture(rendering.print_success)
        assert "All checks passed!" in out


class TestPrintStatistics:
    """Verify print_statistics output."""

    def test_statistics_table(self) -> None:
        """Renders per-rule counts in sorted order."""
        counts: Counter[str] = Counter({"PW002": 3, "PW001": 1})
        out = _capture(rendering.print_statistics, counts)
        assert "PW001" in out
        assert "1" in out
        assert "PW002" in out
        assert "3" in out
        # PW001 should appear before PW002 (sorted)
        assert out.index("PW001") < out.index("PW002")


class TestPrintRulesList:
    """Verify print_rules_list output."""

    def test_lists_all_rules(self) -> None:
        """Renders a table containing all built-in rule codes."""
        rules = get_all_rules()
        out = _capture(rendering.print_rules_list, rules)
        for rule in rules:
            assert rule.code in out
            assert rule.message in out


class TestPrintRuleDetail:
    """Verify print_rule_detail output."""

    def test_shows_all_sections(self) -> None:
        """Renders code, what, why, and example sections for a rule."""
        rule = get_rule("PW001")
        assert rule is not None
        out = _capture(rendering.print_rule_detail, rule)
        assert "PW001" in out
        assert "What it does" in out
        assert "Why is this bad" in out
        assert "Example" in out
