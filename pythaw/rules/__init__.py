from __future__ import annotations

from pythaw.rules._base import Rule
from pythaw.rules.pw001 import Boto3ClientRule
from pythaw.rules.pw002 import Boto3ResourceRule
from pythaw.rules.pw003 import Boto3SessionRule
from pythaw.rules.pw004 import PymysqlConnectRule
from pythaw.rules.pw005 import Psycopg2ConnectRule
from pythaw.rules.pw006 import RedisRule
from pythaw.rules.pw007 import RedisStrictRule
from pythaw.rules.pw008 import HttpxClientRule
from pythaw.rules.pw009 import RequestsSessionRule

__all__ = ["Rule", "get_all_rules", "get_rule"]

_RULES: tuple[Rule, ...] = (
    Boto3ClientRule(),
    Boto3ResourceRule(),
    Boto3SessionRule(),
    PymysqlConnectRule(),
    Psycopg2ConnectRule(),
    RedisRule(),
    RedisStrictRule(),
    HttpxClientRule(),
    RequestsSessionRule(),
)


def get_all_rules() -> tuple[Rule, ...]:
    return _RULES


def get_rule(code: str) -> Rule | None:
    for rule in _RULES:
        if rule.code == code:
            return rule
    return None
