from __future__ import annotations

import json as _json
from typing import TYPE_CHECKING

from pythaw.formatters._base import Formatter

if TYPE_CHECKING:
    from pythaw.violation import Violation


class JsonFormatter(Formatter):
    """Format violations as a JSON array."""

    def format(self, violations: list[Violation]) -> str:
        data = [
            {
                "file": v.file,
                "line": v.line,
                "col": v.col,
                "code": v.code,
                "message": v.message,
            }
            for v in violations
        ]
        return _json.dumps(data, indent=2)
