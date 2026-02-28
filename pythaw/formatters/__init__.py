from __future__ import annotations

from pythaw.formatters._base import Formatter
from pythaw.formatters.concise import ConciseFormatter
from pythaw.formatters.github import GithubFormatter
from pythaw.formatters.json import JsonFormatter
from pythaw.formatters.sarif import SarifFormatter

__all__ = [
    "ConciseFormatter",
    "Formatter",
    "GithubFormatter",
    "JsonFormatter",
    "SarifFormatter",
    "get_formatter",
]

FORMATTERS: dict[str, Formatter] = {
    "concise": ConciseFormatter(),
    "json": JsonFormatter(),
    "github": GithubFormatter(),
    "sarif": SarifFormatter(),
}


def get_formatter(name: str) -> Formatter | None:
    """Return a formatter by name, or None if not found."""
    return FORMATTERS.get(name)
