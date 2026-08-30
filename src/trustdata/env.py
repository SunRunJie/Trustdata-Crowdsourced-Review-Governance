"""Minimal project-local environment-file loader."""

from __future__ import annotations

import os
import re
from pathlib import Path


_ENV_KEY = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def load_env_file(path: Path, *, override: bool = False) -> list[str]:
    """Load simple ``KEY=VALUE`` entries from *path* without exposing values.

    Blank lines and full-line comments are ignored. Existing process environment
    variables take precedence unless ``override`` is explicitly requested.
    """
    if not path.is_file():
        return []

    loaded: list[str] = []
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line.removeprefix("export ").lstrip()
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()
        if not _ENV_KEY.fullmatch(key):
            continue
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
            value = value[1:-1]
        if override or key not in os.environ:
            os.environ[key] = value
            loaded.append(key)
    return loaded


def set_env_value(path: Path, key: str, value: str) -> None:
    """Set one dotenv value without returning or logging its previous value."""
    if not _ENV_KEY.fullmatch(key):
        raise ValueError(f"Invalid environment-variable name: {key!r}")
    if "\n" in value or "\r" in value:
        raise ValueError("Environment values must be single-line")

    lines = path.read_text(encoding="utf-8").splitlines() if path.is_file() else []
    replacement = f"{key}={value}"
    pattern = re.compile(rf"^\s*(?:export\s+)?{re.escape(key)}\s*=")
    for index, line in enumerate(lines):
        if pattern.match(line):
            lines[index] = replacement
            break
    else:
        if lines and lines[-1]:
            lines.append("")
        lines.append(replacement)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
