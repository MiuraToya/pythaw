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


# --- PW001: boto3.client() ---


class TestBoto3ClientRule:
    def setup_method(self) -> None:
        self.rule = Boto3ClientRule()

    def test_code(self) -> None:
        assert self.rule.code == "PW001"

    def test_message(self) -> None:
        assert self.rule.message == "boto3.client() should be called at module scope"

    def test_match_boto3_client(self) -> None:
        node = _extract_call('boto3.client("s3")')
        assert self.rule.check(node) is True

    def test_no_match_other_module(self) -> None:
        node = _extract_call('other.client("s3")')
        assert self.rule.check(node) is False

    def test_no_match_other_attr(self) -> None:
        node = _extract_call("boto3.resource('s3')")
        assert self.rule.check(node) is False

    def test_no_match_plain_function(self) -> None:
        node = _extract_call("client('s3')")
        assert self.rule.check(node) is False


# --- PW002: boto3.resource() ---


class TestBoto3ResourceRule:
    def setup_method(self) -> None:
        self.rule = Boto3ResourceRule()

    def test_code(self) -> None:
        assert self.rule.code == "PW002"

    def test_message(self) -> None:
        assert self.rule.message == "boto3.resource() should be called at module scope"

    def test_match_boto3_resource(self) -> None:
        node = _extract_call('boto3.resource("s3")')
        assert self.rule.check(node) is True

    def test_no_match_other_module(self) -> None:
        node = _extract_call('other.resource("s3")')
        assert self.rule.check(node) is False

    def test_no_match_other_attr(self) -> None:
        node = _extract_call('boto3.client("s3")')
        assert self.rule.check(node) is False

    def test_no_match_plain_function(self) -> None:
        node = _extract_call("resource('s3')")
        assert self.rule.check(node) is False


# --- PW003: boto3.Session() ---


class TestBoto3SessionRule:
    def setup_method(self) -> None:
        self.rule = Boto3SessionRule()

    def test_code(self) -> None:
        assert self.rule.code == "PW003"

    def test_message(self) -> None:
        assert self.rule.message == "boto3.Session() should be called at module scope"

    def test_match_boto3_session(self) -> None:
        node = _extract_call("boto3.Session()")
        assert self.rule.check(node) is True

    def test_no_match_other_module(self) -> None:
        node = _extract_call("other.Session()")
        assert self.rule.check(node) is False

    def test_no_match_other_attr(self) -> None:
        node = _extract_call('boto3.client("s3")')
        assert self.rule.check(node) is False

    def test_no_match_plain_function(self) -> None:
        node = _extract_call("Session()")
        assert self.rule.check(node) is False


# --- Registry ---


class TestRegistry:
    def test_get_all_rules_returns_three(self) -> None:
        rules = get_all_rules()
        assert len(rules) == 3

    def test_get_all_rules_types(self) -> None:
        rules = get_all_rules()
        assert isinstance(rules[0], Boto3ClientRule)
        assert isinstance(rules[1], Boto3ResourceRule)
        assert isinstance(rules[2], Boto3SessionRule)

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
