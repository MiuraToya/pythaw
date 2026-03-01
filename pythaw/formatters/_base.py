from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pythaw.violation import Violation


class Formatter(ABC):
    """Base class for all output formatters.

    Subclasses must implement the ``format`` method.
    """

    @abstractmethod
    def format(self, violations: list[Violation]) -> str:
        """Format violations into an output string.

        Args:
            violations: List of violations to format.

        Returns:
            A formatted string ready for printing.
        """
