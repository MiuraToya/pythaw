from __future__ import annotations

from pythaw.formatters._base import Formatter
from pythaw.formatters.concise import ConciseFormatter

__all__ = ["ConciseFormatter", "Formatter", "get_formatter"]

FORMATTERS: dict[str, Formatter] = {
    "concise": ConciseFormatter(),
}


def get_formatter(name: str) -> Formatter | None:
    """Return a formatter by name, or None if not found."""
    return FORMATTERS.get(name)
