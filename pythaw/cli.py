from __future__ import annotations

import argparse
import sys
from collections import Counter
from pathlib import Path
from typing import TYPE_CHECKING

from pythaw.checker import check
from pythaw.config import Config, ConfigError
from pythaw.formatters import get_formatter
from pythaw.rendering import (
    print_rule_detail,
    print_rules_list,
    print_statistics,
    print_success,
    print_violations,
)
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
    check_p.add_argument(
        "--exit-zero",
        action="store_true",
        help="Exit with code 0 even when violations are found",
    )
    check_p.add_argument(
        "--statistics",
        action="store_true",
        help="Show per-rule violation counts",
    )
    check_p.add_argument(
        "--format",
        choices=["concise", "json", "github", "sarif"],
        default="concise",
        help="Output format (default: concise)",
    )
    check_p.add_argument(
        "--select",
        default=None,
        help="Comma-separated list of rule codes to enable (e.g. PW001,PW002)",
    )
    check_p.add_argument(
        "--ignore",
        default=None,
        help="Comma-separated list of rule codes to disable (e.g. PW003)",
    )
    check_p.set_defaults(func=_cmd_check)

    rules_p = sub.add_parser("rules", help="List all built-in rules")
    rules_p.set_defaults(func=_cmd_rules)

    rule_p = sub.add_parser("rule", help="Show details for a rule")
    rule_p.add_argument("code", help="Rule code (e.g. PW001)")
    rule_p.set_defaults(func=_cmd_rule)

    return parser


def _parse_code_list(value: str | None) -> frozenset[str]:
    """Parse a comma-separated rule code list into a frozenset."""
    if value is None:
        return frozenset()
    return frozenset(c.strip() for c in value.split(",") if c.strip())


def _cmd_check(args: argparse.Namespace) -> int:
    try:
        config = Config.load()
    except ConfigError as exc:
        print(str(exc), file=sys.stderr)
        return 2

    select = _parse_code_list(args.select)
    ignore = _parse_code_list(args.ignore)
    violations = check(args.path, config, select=select, ignore=ignore)

    if not violations:
        print_success()
        return 0

    if args.format == "concise":
        print_violations(violations)
    else:
        formatter = get_formatter(args.format)
        if formatter is not None:  # pragma: no branch — always exists
            print(formatter.format(violations))

    if args.statistics:
        counts = Counter(v.code for v in violations)
        if args.format == "concise":
            print_statistics(counts)
        else:
            print()
            for code in sorted(counts):
                print(f"{code}  {counts[code]}")

    return 0 if args.exit_zero else 1


def _cmd_rules(_args: argparse.Namespace) -> int:
    print_rules_list(get_all_rules())
    return 0


def _cmd_rule(args: argparse.Namespace) -> int:
    rule = get_rule(args.code)
    if rule is None:
        print(f"Unknown rule: {args.code}", file=sys.stderr)
        return 2

    print_rule_detail(rule)
    return 0
