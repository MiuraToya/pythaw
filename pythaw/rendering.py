"""Rich-based CLI rendering for pythaw output."""

from __future__ import annotations

from typing import TYPE_CHECKING

from rich.console import Console
from rich.table import Table
from rich.text import Text

if TYPE_CHECKING:
    from collections import Counter

    from pythaw.rules._base import Rule
    from pythaw.violation import Violation

console = Console(highlight=False)

STYLE_COLD = "bold deep_sky_blue1"
STYLE_SUCCESS = "bold dark_orange"
STYLE_LOCATION = "bold"


def print_violations(violations: list[Violation]) -> None:
    """Print violations with colour-coded output."""
    for v in violations:
        line = Text()
        line.append(f"{v.file}:{v.line}:{v.col}: ", style=STYLE_LOCATION)
        line.append(f"{v.code} ", style=STYLE_COLD)
        line.append(v.message)
        console.print(line)

        for depth, site in enumerate(v.call_chain):
            indent = "  " * (depth + 1)
            via = Text()
            via.append(f"{indent}\u2192 ", style=STYLE_COLD)
            via.append(f"{site.file}:{site.line}:{site.col} ", style=STYLE_LOCATION)
            via.append(site.name, style=STYLE_COLD)
            console.print(via)

    file_count = len({v.file for v in violations})
    violation_count = len(violations)
    f_plural = "s" if file_count != 1 else ""
    v_plural = "s" if violation_count != 1 else ""
    summary = (
        f"Found {violation_count} violation{v_plural} in {file_count} file{f_plural}."
    )
    console.print()
    console.print(summary, style=STYLE_COLD)


def print_success() -> None:
    """Print success message."""
    console.print("All checks passed!", style=STYLE_SUCCESS)


def print_statistics(counts: Counter[str]) -> None:
    """Print per-rule violation counts as a table."""
    table = Table(box=None, pad_edge=False)
    table.add_column("Rule", style=STYLE_COLD)
    table.add_column("Count", justify="right")
    for code in sorted(counts):
        table.add_row(code, str(counts[code]))
    console.print()
    console.print(table)


def print_rules_list(rules: tuple[Rule, ...]) -> None:
    """Print a table of all built-in rules."""
    table = Table(box=None, pad_edge=False)
    table.add_column("Code", style=STYLE_COLD)
    table.add_column("Message")
    for rule in rules:
        table.add_row(rule.code, rule.message)
    console.print(table)


def print_rule_detail(rule: Rule) -> None:
    """Print detailed information for a single rule."""
    title = Text()
    title.append(rule.code, style=STYLE_COLD)
    title.append(f": {rule.message}")
    console.print(title)
    console.print()
    console.print("What it does:")
    console.print(f"  {rule.what}")
    console.print()
    console.print("Why is this bad?:")
    console.print(f"  {rule.why}")
    console.print()
    console.print("Example:")
    for line in rule.example.splitlines():
        console.print(f"  {line}")
