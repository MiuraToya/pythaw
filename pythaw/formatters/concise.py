from __future__ import annotations

from typing import TYPE_CHECKING

from pythaw.formatters._base import Formatter

if TYPE_CHECKING:
    from pythaw.violation import Violation


class ConciseFormatter(Formatter):
    """Format violations as one-line-per-violation with a summary.

    Output format::

        file:line:col: CODE message

        Found N violation(s) in M file(s).
    """

    def format(self, violations: list[Violation]) -> str:
        if not violations:
            return ""

        lines = [f"{v.file}:{v.line}:{v.col}: {v.code} {v.message}" for v in violations]

        file_count = len({v.file for v in violations})
        violation_count = len(violations)
        f_plural = "s" if file_count != 1 else ""
        v_plural = "s" if violation_count != 1 else ""
        summary = (
            f"Found {violation_count} violation{v_plural}"
            f" in {file_count} file{f_plural}."
        )

        lines.append("")
        lines.append(summary)

        return "\n".join(lines)
