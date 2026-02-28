from __future__ import annotations

from pythaw.rules._base import Rule
from pythaw.rules.pw001 import Boto3ClientRule
from pythaw.rules.pw002 import Boto3ResourceRule
from pythaw.rules.pw003 import Boto3SessionRule

__all__ = ["Rule", "get_all_rules", "get_rule"]

_RULES: tuple[Rule, ...] = (
    Boto3ClientRule(),
    Boto3ResourceRule(),
    Boto3SessionRule(),
)


def get_all_rules() -> tuple[Rule, ...]:
    return _RULES


def get_rule(code: str) -> Rule | None:
    for rule in _RULES:
        if rule.code == code:
            return rule
    return None
