"""
FORGE Generation Core
Specification loading and access.

This module is UI-independent.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class SpecificationError(Exception):
    """Raised when a FORGE specification cannot be loaded."""


def load_specification(path: str | Path) -> dict[str, Any]:
    """
    Load a FORGE specification from a JSON file.

    This function only loads and parses the specification.
    Validation is intentionally handled separately.
    """

    specification_path = Path(path)

    if not specification_path.exists():
        raise SpecificationError(
            f"Specification file not found: {specification_path}"
        )

    if not specification_path.is_file():
        raise SpecificationError(
            f"Specification path is not a file: {specification_path}"
        )

    try:
        with specification_path.open("r", encoding="utf-8") as file:
            specification = json.load(file)
    except json.JSONDecodeError as exc:
        raise SpecificationError(
            f"Invalid JSON specification: {specification_path}"
        ) from exc

    if not isinstance(specification, dict):
        raise SpecificationError(
            "FORGE specification root must be a JSON object."
        )

    return specification
