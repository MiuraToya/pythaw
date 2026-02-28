from __future__ import annotations

import ast

import pytest

from pythaw.rules import get_all_rules, get_rule
from pythaw.rules.pw001 import Boto3ClientRule
from pythaw.rules.pw002 import Boto3ResourceRule
from pythaw.rules.pw003 import Boto3SessionRule


def _extract_call(source: str) -> ast.Call:
    """Parse a source string and return the first Call node found."""
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            return node
    msg = f"No Call node found in: {source}"
    raise AssertionError(msg)


class TestBoto3ClientRule:
    """PW001: Verify check() and metadata for boto3.client()."""

    def setup_method(self) -> None:
        self.rule = Boto3ClientRule()

    def test_code(self) -> None:
        assert self.rule.code == "PW001"

    def test_message(self) -> None:
        assert self.rule.message == "boto3.client() should be called at module scope"

    def test_match_boto3_client(self) -> None:
        node = _extract_call('boto3.client("s3")')
        assert self.rule.check(node) is True

    @pytest.mark.parametrize("source", [
        'other.client("s3")',
        "boto3.resource('s3')",
        "client('s3')",
    ])
    def test_no_match(self, source: str) -> None:
        node = _extract_call(source)
        assert self.rule.check(node) is False


class TestBoto3ResourceRule:
    """PW002: Verify check() and metadata for boto3.resource()."""

    def setup_method(self) -> None:
        self.rule = Boto3ResourceRule()

    def test_code(self) -> None:
        assert self.rule.code == "PW002"

    def test_message(self) -> None:
        assert self.rule.message == "boto3.resource() should be called at module scope"

    def test_match_boto3_resource(self) -> None:
        node = _extract_call('boto3.resource("s3")')
        assert self.rule.check(node) is True

    @pytest.mark.parametrize("source", [
        'other.resource("s3")',
        'boto3.client("s3")',
        "resource('s3')",
    ])
    def test_no_match(self, source: str) -> None:
        node = _extract_call(source)
        assert self.rule.check(node) is False


class TestBoto3SessionRule:
    """PW003: Verify check() and metadata for boto3.Session()."""

    def setup_method(self) -> None:
        self.rule = Boto3SessionRule()

    def test_code(self) -> None:
        assert self.rule.code == "PW003"

    def test_message(self) -> None:
        assert self.rule.message == "boto3.Session() should be called at module scope"

    def test_match_boto3_session(self) -> None:
        node = _extract_call("boto3.Session()")
        assert self.rule.check(node) is True

    @pytest.mark.parametrize("source", [
        "other.Session()",
        'boto3.client("s3")',
        "Session()",
    ])
    def test_no_match(self, source: str) -> None:
        node = _extract_call(source)
        assert self.rule.check(node) is False


class TestRegistry:
    """Verify get_all_rules() and get_rule() registry functions."""

    def test_get_all_rules(self) -> None:
        rules = get_all_rules()
        assert rules == (get_rule("PW001"), get_rule("PW002"), get_rule("PW003"))

    @pytest.mark.parametrize(
        ("code", "expected_type"),
        [
            ("PW001", Boto3ClientRule),
            ("PW002", Boto3ResourceRule),
            ("PW003", Boto3SessionRule),
        ],
    )
    def test_get_rule_by_code(self, code: str, expected_type: type) -> None:
        rule = get_rule(code)
        assert isinstance(rule, expected_type)

    def test_get_rule_unknown_returns_none(self) -> None:
        assert get_rule("PW999") is None
