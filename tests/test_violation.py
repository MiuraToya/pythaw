from __future__ import annotations

import pytest

from pythaw.violation import Violation


class TestViolation:
    """Verify Violation dataclass behavior."""

    def test_fields(self) -> None:
        v = Violation(
            file="handler.py",
            line=15,
            col=4,
            code="PW001",
            message="boto3.client() should be called at module scope",
        )
        assert v.file == "handler.py"
        assert v.line == 15
        assert v.col == 4
        assert v.code == "PW001"
        assert v.message == "boto3.client() should be called at module scope"

    def test_frozen(self) -> None:
        v = Violation(file="handler.py", line=15, col=4, code="PW001", message="msg")
        with pytest.raises(AttributeError):
            v.line = 99  # type: ignore[misc]

    def test_equality(self) -> None:
        v1 = Violation(file="a.py", line=1, col=0, code="PW001", message="msg")
        v2 = Violation(file="a.py", line=1, col=0, code="PW001", message="msg")
        assert v1 == v2

    def test_inequality(self) -> None:
        v1 = Violation(file="a.py", line=1, col=0, code="PW001", message="msg")
        v2 = Violation(file="a.py", line=2, col=0, code="PW001", message="msg")
        assert v1 != v2
