from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Violation:
    """A single rule violation found in a source file."""

    file: str
    line: int
    col: int
    code: str
    message: str
