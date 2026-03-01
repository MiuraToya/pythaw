from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib


class ConfigError(Exception):
    """Raised when configuration is invalid."""


@dataclass(frozen=True)
class Config:
    """Project configuration loaded from pyproject.toml."""

    handler_patterns: tuple[str, ...] = ("handler", "lambda_handler", "*_handler")
    exclude: tuple[str, ...] = ()

    @staticmethod
    def load() -> Config:
        """Load config from pyproject.toml.

        Search for pyproject.toml in the current directory and parent
        directories.  If not found, return default config.
        """
        toml_path = _find_pyproject()
        if toml_path is None:
            return Config()

        try:
            raw = toml_path.read_bytes()
            data = tomllib.loads(raw.decode())
        except (OSError, tomllib.TOMLDecodeError) as exc:
            msg = f"Failed to read {toml_path}: {exc}"
            raise ConfigError(msg) from exc

        section: dict[str, Any] = data.get("tool", {}).get("pythaw", {})
        if not section:
            return Config()

        return _build_config(section)


def _find_pyproject() -> Path | None:
    """Walk up from cwd looking for pyproject.toml."""
    current = Path.cwd().resolve()
    for directory in (current, *current.parents):
        candidate = directory / "pyproject.toml"
        if candidate.is_file():
            return candidate
    return None


def _build_config(section: dict[str, Any]) -> Config:
    """Construct a Config from the ``[tool.pythaw]`` mapping."""
    kwargs: dict[str, Any] = {}

    if "handler_patterns" in section:
        kwargs["handler_patterns"] = _validate_str_list(
            section["handler_patterns"],
            "handler_patterns",
        )

    if "exclude" in section:
        kwargs["exclude"] = _validate_str_list(section["exclude"], "exclude")

    return Config(**kwargs)


def _validate_str_list(value: object, name: str) -> tuple[str, ...]:
    """Return *value* as a tuple of strings, or raise `ConfigError`."""
    if not isinstance(value, list) or not all(isinstance(v, str) for v in value):
        msg = f"tool.pythaw.{name} must be a list of strings"
        raise ConfigError(msg)
    return tuple(value)
