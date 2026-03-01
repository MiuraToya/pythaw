from __future__ import annotations

from typing import TYPE_CHECKING

from pythaw.formatters._base import Formatter

if TYPE_CHECKING:
    from pythaw.violation import Violation


class GithubFormatter(Formatter):
    """Format violations as GitHub Actions error annotations."""

    def format(self, violations: list[Violation]) -> str:
        if not violations:
            return ""

        lines = [
            (f"::error file={v.file},line={v.line},col={v.col}::{v.code} {v.message}")
            for v in violations
        ]
        return "\n".join(lines)
