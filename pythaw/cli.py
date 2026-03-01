from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import TYPE_CHECKING

from pythaw.checker import check
from pythaw.config import Config, ConfigError
from pythaw.formatters import get_formatter
from pythaw.rules import get_all_rules, get_rule

if TYPE_CHECKING:
    from collections.abc import Sequence


def main(argv: Sequence[str] | None = None) -> None:
    """CLI entry point.

    Args:
        argv: Command-line arguments. Defaults to ``sys.argv[1:]``.

    Raises:
        SystemExit: Always raised with the appropriate exit code
            (0 = no issues, 1 = violations found, 2 = tool error).
    """
    parser = _build_parser()
    args = parser.parse_args(argv)

    if not hasattr(args, "func"):
        parser.print_help()
        raise SystemExit(2)

    raise SystemExit(args.func(args))


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="pythaw",
        description="Detect heavy initialization inside AWS Lambda Python handlers.",
    )
    sub = parser.add_subparsers()

    check_p = sub.add_parser("check", help="Check files for violations")
    check_p.add_argument("path", type=Path, help="File or directory to check")
    check_p.set_defaults(func=_cmd_check)

    rules_p = sub.add_parser("rules", help="List all built-in rules")
    rules_p.set_defaults(func=_cmd_rules)

    rule_p = sub.add_parser("rule", help="Show details for a rule")
    rule_p.add_argument("code", help="Rule code (e.g. PW001)")
    rule_p.set_defaults(func=_cmd_rule)

    return parser


def _cmd_check(args: argparse.Namespace) -> int:
    try:
        config = Config.load()
    except ConfigError as exc:
        print(str(exc), file=sys.stderr)
        return 2

    violations = check(args.path, config)

    if not violations:
        print("All checks passed!")
        return 0

    formatter = get_formatter("concise")
    if formatter is not None:  # pragma: no branch — always exists
        print(formatter.format(violations))
    return 1


def _cmd_rules(_args: argparse.Namespace) -> int:
    for rule in get_all_rules():
        print(f"{rule.code}  {rule.message}")
    return 0


def _cmd_rule(args: argparse.Namespace) -> int:
    rule = get_rule(args.code)
    if rule is None:
        print(f"Unknown rule: {args.code}", file=sys.stderr)
        return 2

    print(f"{rule.code}: {rule.message}")
    print()
    print("What it does:")
    print(f"  {rule.what}")
    print()
    print("Why is this bad?:")
    print(f"  {rule.why}")
    print()
    print("Example:")
    for line in rule.example.splitlines():
        print(f"  {line}")
    return 0
