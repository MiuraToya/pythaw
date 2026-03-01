from __future__ import annotations

import importlib
import pkgutil

from pythaw.rules._base import Rule

__all__ = ["Rule", "get_all_rules", "get_rule"]


def _collect_rules() -> tuple[Rule, ...]:
    """Discover and instantiate all Rule subclasses in this package.

    Scans all modules under ``pythaw/rules/`` (excluding ``_``-prefixed
    modules like ``_base``), imports each one, and collects every
    ``Rule`` subclass found.  The resulting instances are sorted by
    their ``code`` attribute (e.g. ``"PW001"``, ``"PW002"``, …) so
    that ordering is deterministic.
    """
    rules: list[Rule] = []
    for info in pkgutil.iter_modules(__path__):
        if info.name.startswith("_"):
            continue
        mod = importlib.import_module(f"{__name__}.{info.name}")
        rules.extend(
            obj()
            for obj in vars(mod).values()
            if isinstance(obj, type) and issubclass(obj, Rule) and obj is not Rule
        )
    rules.sort(key=lambda r: r.code)
    return tuple(rules)


_RULES = _collect_rules()


def get_all_rules() -> tuple[Rule, ...]:
    """Return all built-in rules."""
    return _RULES


def get_rule(code: str) -> Rule | None:
    """Return the rule matching *code*, or ``None`` if not found."""
    for rule in _RULES:
        if rule.code == code:
            return rule
    return None
