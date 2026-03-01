from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Violation:
    """A single rule violation found in a source file.

    Attributes:
        file: Path to the source file (relative).
        line: Line number of the violation.
        col: Column offset of the violation.
        code: Rule code (e.g. ``"PW001"``).
        message: Human-readable description of the violation.
    """

    file: str
    line: int
    col: int
    code: str
    message: str
