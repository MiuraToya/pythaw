from __future__ import annotations

import re
from pathlib import Path
from unittest.mock import patch

import pytest

from pythaw.checker import check
from pythaw.config import Config
from pythaw.rules import get_all_rules, get_rule

FIXTURES_DIR = Path(__file__).parent / "fixtures" / "rules"

_FIXTURES = sorted(FIXTURES_DIR.glob("PW*.py"))


def _parse_expected_errors(fixture: Path) -> set[tuple[int, str]]:
    """Extract ``(line_number, code)`` pairs from ``# error: PWXXX`` comments."""
    errors: set[tuple[int, str]] = set()
    for i, line in enumerate(fixture.read_text().splitlines(), start=1):
        m = re.search(r"#\s*error:\s*(PW\d+)", line)
        if m:
            errors.add((i, m.group(1)))
    return errors


# ---------------------------------------------------------------------------
# Fixture-based rule violation tests
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("fixture", _FIXTURES, ids=lambda p: p.stem)
class TestRuleViolation:
    """Verify rule detection using fixture files.

    Each fixture in ``tests/fixtures/rules/`` contains handler code
    annotated with ``# error: PWXXX`` comments marking expected
    violations, plus OK code that should not trigger any violations.
    """

    def test_expected_violations_detected(self, fixture: Path) -> None:
        """All lines marked with '# error:' produce the expected violation."""
        expected = _parse_expected_errors(fixture)
        with patch("pythaw.finder._git_ls_files", return_value=None):
            violations = check(fixture, Config())
        actual = {(v.line, v.code) for v in violations}
        assert actual == expected

    def test_no_false_positives(self, fixture: Path) -> None:
        """Lines without '# error:' do not produce violations."""
        expected_lines = {line for line, _ in _parse_expected_errors(fixture)}
        with patch("pythaw.finder._git_ls_files", return_value=None):
            violations = check(fixture, Config())
        unexpected = [v for v in violations if v.line not in expected_lines]
        assert unexpected == []


# ---------------------------------------------------------------------------
# Registry tests
# ---------------------------------------------------------------------------


class TestRegistry:
    """Verify get_all_rules() and get_rule() registry functions."""

    def test_all_rules_sorted_by_code(self) -> None:
        """Rules are returned sorted by code."""
        rules = get_all_rules()
        codes = [r.code for r in rules]
        assert codes == sorted(codes)

    def test_get_rule_by_code(self) -> None:
        """Each rule can be looked up by its code."""
        for rule in get_all_rules():
            assert get_rule(rule.code) is rule

    def test_unknown_returns_none(self) -> None:
        """Unknown code returns None."""
        assert get_rule("PW999") is None
