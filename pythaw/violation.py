from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CallSite:
    """A single step in the call chain from handler to violation.

    Attributes:
        file: Path to the source file (relative) where the call was made.
        line: Line number of the call.
        col: Column offset of the call.
        name: Display name of the called function (e.g. ``"helper()"``).
    """

    file: str
    line: int
    col: int
    name: str


@dataclass(frozen=True)
class Violation:
    """A single rule violation found in a source file.

    Attributes:
        file: Path to the source file (relative).
        line: Line number of the violation.
        col: Column offset of the violation.
        code: Rule code (e.g. ``"PW001"``).
        message: Human-readable description of the violation.
        call_chain: Sequence of call sites from handler to violation.
            Empty for direct violations.
    """

    file: str
    line: int
    col: int
    code: str
    message: str
    call_chain: tuple[CallSite, ...] = ()
