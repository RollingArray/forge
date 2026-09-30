from __future__ import annotations

from typing import Any


def convert_value(
    value: Any,
    field_type: Any,
) -> Any:
    """Convert a serialized artifact value to its FORGE field type."""

    if value is None:
        return None

    if not isinstance(value, str):
        return value

    normalized_type = str(
        field_type or "STRING"
    ).strip().upper()

    if normalized_type in {"INTEGER", "IDENTIFIER"}:
        return int(value)

    if normalized_type == "DECIMAL":
        return float(value)

    if normalized_type == "BOOLEAN":
        normalized_value = value.strip().lower()

        if normalized_value == "true":
            return True

        if normalized_value == "false":
            return False

        raise ValueError(
            f"Invalid BOOLEAN value {value!r}."
        )

    return value
