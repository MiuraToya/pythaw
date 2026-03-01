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
    """Project configuration loaded from ``pyproject.toml``.

    Attributes:
        handler_patterns: fnmatch patterns to identify handler functions.
        exclude: fnmatch patterns to exclude files/directories from scanning.
    """

    handler_patterns: tuple[str, ...] = ("handler", "lambda_handler", "*_handler")
    exclude: tuple[str, ...] = ()
    per_file_ignores: tuple[tuple[str, tuple[str, ...]], ...] = ()

    @staticmethod
    def load() -> Config:
        """Load config from ``pyproject.toml``.

        Searches for ``pyproject.toml`` in the current directory and parent
        directories. If not found, returns default config.

        Returns:
            A Config instance populated from ``[tool.pythaw]``, or defaults.

        Raises:
            ConfigError: If the TOML file is invalid or contains bad values.
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

    if "per-file-ignores" in section:
        kwargs["per_file_ignores"] = _validate_per_file_ignores(
            section["per-file-ignores"],
        )

    return Config(**kwargs)


def _validate_str_list(value: object, name: str) -> tuple[str, ...]:
    """Return *value* as a tuple of strings, or raise `ConfigError`."""
    if not isinstance(value, list) or not all(isinstance(v, str) for v in value):
        msg = f"tool.pythaw.{name} must be a list of strings"
        raise ConfigError(msg)
    return tuple(value)


def _validate_per_file_ignores(
    value: object,
) -> tuple[tuple[str, tuple[str, ...]], ...]:
    """Validate and return ``per-file-ignores`` as a tuple of (glob, codes) pairs."""
    if not isinstance(value, dict):
        msg = "tool.pythaw.per-file-ignores must be a table"
        raise ConfigError(msg)
    result: list[tuple[str, tuple[str, ...]]] = []
    for pattern, codes in value.items():
        if not isinstance(pattern, str):
            msg = "tool.pythaw.per-file-ignores keys must be strings"
            raise ConfigError(msg)
        if not isinstance(codes, list) or not all(isinstance(c, str) for c in codes):
            msg = f'tool.pythaw.per-file-ignores["{pattern}"] must be a list of strings'
            raise ConfigError(msg)
        result.append((pattern, tuple(codes)))
    return tuple(result)
