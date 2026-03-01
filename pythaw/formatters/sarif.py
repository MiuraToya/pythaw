from __future__ import annotations

import json as _json
from typing import TYPE_CHECKING, Any

from pythaw.formatters._base import Formatter

if TYPE_CHECKING:
    from pythaw.violation import Violation

_SARIF_SCHEMA = (
    "https://raw.githubusercontent.com/oasis-tcs/sarif-spec"
    "/main/sarif-2.1/schema/sarif-schema-2.1.0.json"
)


class SarifFormatter(Formatter):
    """Format violations as SARIF 2.1.0 JSON."""

    def format(self, violations: list[Violation]) -> str:
        results: list[dict[str, Any]] = [
            {
                "ruleId": v.code,
                "level": "error",
                "message": {"text": v.message},
                "locations": [
                    {
                        "physicalLocation": {
                            "artifactLocation": {
                                "uri": v.file,
                            },
                            "region": {
                                "startLine": v.line,
                                "startColumn": v.col,
                            },
                        },
                    },
                ],
            }
            for v in violations
        ]

        sarif: dict[str, Any] = {
            "$schema": _SARIF_SCHEMA,
            "version": "2.1.0",
            "runs": [
                {
                    "tool": {
                        "driver": {
                            "name": "pythaw",
                        },
                    },
                    "results": results,
                },
            ],
        }
        return _json.dumps(sarif, indent=2)
