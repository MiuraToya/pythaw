from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import ast


class Rule(ABC):
    """Base class for all pythaw rules.

    Subclasses must implement all abstract properties (``code``, ``message``,
    ``what``, ``why``, ``example``) and the ``check`` method.
    """

    @property
    @abstractmethod
    def code(self) -> str: ...

    @property
    @abstractmethod
    def message(self) -> str: ...

    @property
    @abstractmethod
    def what(self) -> str: ...

    @property
    @abstractmethod
    def why(self) -> str: ...

    @property
    @abstractmethod
    def example(self) -> str: ...

    @abstractmethod
    def check(self, node: ast.Call) -> bool:
        """Return True if the given Call node violates this rule.

        Args:
            node: An ``ast.Call`` node to inspect.

        Returns:
            True if the node matches this rule's violation pattern.
        """
