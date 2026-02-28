from __future__ import annotations

import ast

import pytest

from pythaw.rules import get_all_rules, get_rule
from pythaw.rules.pw001 import Boto3ClientRule
from pythaw.rules.pw002 import Boto3ResourceRule
from pythaw.rules.pw003 import Boto3SessionRule
from pythaw.rules.pw004 import PymysqlConnectRule
from pythaw.rules.pw005 import Psycopg2ConnectRule
from pythaw.rules.pw006 import RedisRule
from pythaw.rules.pw007 import RedisStrictRule
from pythaw.rules.pw008 import HttpxClientRule
from pythaw.rules.pw009 import RequestsSessionRule


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
        """Rule code is PW001."""
        assert self.rule.code == "PW001"

    def test_message(self) -> None:
        """Message describes the violation."""
        assert self.rule.message == "boto3.client() should be called at module scope"

    def test_match_boto3_client(self) -> None:
        """Matches boto3.client() call."""
        node = _extract_call('boto3.client("s3")')
        assert self.rule.check(node) is True

    @pytest.mark.parametrize(
        "source",
        [
            'other.client("s3")',
            "boto3.resource('s3')",
            "client('s3')",
        ],
    )
    def test_no_match(self, source: str) -> None:
        """Does not match unrelated calls."""
        node = _extract_call(source)
        assert self.rule.check(node) is False


class TestBoto3ResourceRule:
    """PW002: Verify check() and metadata for boto3.resource()."""

    def setup_method(self) -> None:
        self.rule = Boto3ResourceRule()

    def test_code(self) -> None:
        """Rule code is PW002."""
        assert self.rule.code == "PW002"

    def test_message(self) -> None:
        """Message describes the violation."""
        assert self.rule.message == "boto3.resource() should be called at module scope"

    def test_match_boto3_resource(self) -> None:
        """Matches boto3.resource() call."""
        node = _extract_call('boto3.resource("s3")')
        assert self.rule.check(node) is True

    @pytest.mark.parametrize(
        "source",
        [
            'other.resource("s3")',
            'boto3.client("s3")',
            "resource('s3')",
        ],
    )
    def test_no_match(self, source: str) -> None:
        """Does not match unrelated calls."""
        node = _extract_call(source)
        assert self.rule.check(node) is False


class TestBoto3SessionRule:
    """PW003: Verify check() and metadata for boto3.Session()."""

    def setup_method(self) -> None:
        self.rule = Boto3SessionRule()

    def test_code(self) -> None:
        """Rule code is PW003."""
        assert self.rule.code == "PW003"

    def test_message(self) -> None:
        """Message describes the violation."""
        assert self.rule.message == "boto3.Session() should be called at module scope"

    def test_match_boto3_session(self) -> None:
        """Matches boto3.Session() call."""
        node = _extract_call("boto3.Session()")
        assert self.rule.check(node) is True

    @pytest.mark.parametrize(
        "source",
        [
            "other.Session()",
            'boto3.client("s3")',
            "Session()",
        ],
    )
    def test_no_match(self, source: str) -> None:
        """Does not match unrelated calls."""
        node = _extract_call(source)
        assert self.rule.check(node) is False


class TestPymysqlConnectRule:
    """PW004: Verify check() and metadata for pymysql.connect()."""

    def setup_method(self) -> None:
        self.rule = PymysqlConnectRule()

    def test_code(self) -> None:
        """Rule code is PW004."""
        assert self.rule.code == "PW004"

    def test_message(self) -> None:
        """Message describes the violation."""
        assert self.rule.message == "pymysql.connect() should be called at module scope"

    def test_match(self) -> None:
        """Matches pymysql.connect() call."""
        node = _extract_call("pymysql.connect(host='localhost')")
        assert self.rule.check(node) is True

    @pytest.mark.parametrize(
        "source",
        ["other.connect()", "pymysql.cursor()", "connect()"],
    )
    def test_no_match(self, source: str) -> None:
        """Does not match unrelated calls."""
        node = _extract_call(source)
        assert self.rule.check(node) is False


class TestPsycopg2ConnectRule:
    """PW005: Verify check() and metadata for psycopg2.connect()."""

    def setup_method(self) -> None:
        self.rule = Psycopg2ConnectRule()

    def test_code(self) -> None:
        """Rule code is PW005."""
        assert self.rule.code == "PW005"

    def test_message(self) -> None:
        """Message describes the violation."""
        expected = "psycopg2.connect() should be called at module scope"
        assert self.rule.message == expected

    def test_match(self) -> None:
        """Matches psycopg2.connect() call."""
        node = _extract_call("psycopg2.connect(dsn='...')")
        assert self.rule.check(node) is True

    @pytest.mark.parametrize(
        "source",
        ["other.connect()", "psycopg2.cursor()", "connect()"],
    )
    def test_no_match(self, source: str) -> None:
        """Does not match unrelated calls."""
        node = _extract_call(source)
        assert self.rule.check(node) is False


class TestRedisRule:
    """PW006: Verify check() and metadata for redis.Redis()."""

    def setup_method(self) -> None:
        self.rule = RedisRule()

    def test_code(self) -> None:
        """Rule code is PW006."""
        assert self.rule.code == "PW006"

    def test_message(self) -> None:
        """Message describes the violation."""
        assert self.rule.message == "redis.Redis() should be called at module scope"

    def test_match(self) -> None:
        """Matches redis.Redis() call."""
        node = _extract_call("redis.Redis(host='localhost')")
        assert self.rule.check(node) is True

    @pytest.mark.parametrize(
        "source",
        ["other.Redis()", "redis.StrictRedis()", "Redis()"],
    )
    def test_no_match(self, source: str) -> None:
        """Does not match unrelated calls."""
        node = _extract_call(source)
        assert self.rule.check(node) is False


class TestRedisStrictRule:
    """PW007: Verify check() and metadata for redis.StrictRedis()."""

    def setup_method(self) -> None:
        self.rule = RedisStrictRule()

    def test_code(self) -> None:
        """Rule code is PW007."""
        assert self.rule.code == "PW007"

    def test_message(self) -> None:
        """Message describes the violation."""
        expected = "redis.StrictRedis() should be called at module scope"
        assert self.rule.message == expected

    def test_match(self) -> None:
        """Matches redis.StrictRedis() call."""
        node = _extract_call("redis.StrictRedis(host='localhost')")
        assert self.rule.check(node) is True

    @pytest.mark.parametrize(
        "source",
        ["other.StrictRedis()", "redis.Redis()", "StrictRedis()"],
    )
    def test_no_match(self, source: str) -> None:
        """Does not match unrelated calls."""
        node = _extract_call(source)
        assert self.rule.check(node) is False


class TestHttpxClientRule:
    """PW008: Verify check() and metadata for httpx.Client()."""

    def setup_method(self) -> None:
        self.rule = HttpxClientRule()

    def test_code(self) -> None:
        """Rule code is PW008."""
        assert self.rule.code == "PW008"

    def test_message(self) -> None:
        """Message describes the violation."""
        assert self.rule.message == "httpx.Client() should be called at module scope"

    def test_match(self) -> None:
        """Matches httpx.Client() call."""
        node = _extract_call("httpx.Client()")
        assert self.rule.check(node) is True

    @pytest.mark.parametrize(
        "source",
        ["other.Client()", "httpx.AsyncClient()", "Client()"],
    )
    def test_no_match(self, source: str) -> None:
        """Does not match unrelated calls."""
        node = _extract_call(source)
        assert self.rule.check(node) is False


class TestRequestsSessionRule:
    """PW009: Verify check() and metadata for requests.Session()."""

    def setup_method(self) -> None:
        self.rule = RequestsSessionRule()

    def test_code(self) -> None:
        """Rule code is PW009."""
        assert self.rule.code == "PW009"

    def test_message(self) -> None:
        """Message describes the violation."""
        expected = "requests.Session() should be called at module scope"
        assert self.rule.message == expected

    def test_match(self) -> None:
        """Matches requests.Session() call."""
        node = _extract_call("requests.Session()")
        assert self.rule.check(node) is True

    @pytest.mark.parametrize(
        "source",
        ["other.Session()", "requests.get('url')", "Session()"],
    )
    def test_no_match(self, source: str) -> None:
        """Does not match unrelated calls."""
        node = _extract_call(source)
        assert self.rule.check(node) is False


class TestRegistry:
    """Verify get_all_rules() and get_rule() registry functions."""

    def test_get_all_rules(self) -> None:
        """Returns all nine built-in rules in order."""
        expected = (
            Boto3ClientRule,
            Boto3ResourceRule,
            Boto3SessionRule,
            PymysqlConnectRule,
            Psycopg2ConnectRule,
            RedisRule,
            RedisStrictRule,
            HttpxClientRule,
            RequestsSessionRule,
        )
        rules = get_all_rules()
        assert tuple(type(r) for r in rules) == expected

    @pytest.mark.parametrize(
        ("code", "expected_type"),
        [
            ("PW001", Boto3ClientRule),
            ("PW002", Boto3ResourceRule),
            ("PW003", Boto3SessionRule),
            ("PW004", PymysqlConnectRule),
            ("PW005", Psycopg2ConnectRule),
            ("PW006", RedisRule),
            ("PW007", RedisStrictRule),
            ("PW008", HttpxClientRule),
            ("PW009", RequestsSessionRule),
        ],
    )
    def test_get_rule_by_code(self, code: str, expected_type: type) -> None:
        """Looks up each rule by its code."""
        rule = get_rule(code)
        assert isinstance(rule, expected_type)

    def test_get_rule_unknown_returns_none(self) -> None:
        """Unknown code returns None."""
        assert get_rule("PW999") is None
