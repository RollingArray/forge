from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Any


def convert_value(
    value: Any,
    field_type: Any,
) -> Any:
    """Convert a serialized artifact value to its FORGE field type."""

    if value is None:
        return None

    normalized_type = str(
        field_type or "STRING"
    ).strip().upper()

    if normalized_type == "DECIMAL":
        if isinstance(value, Decimal):
            return value

        if not isinstance(value, str):
            raise ValueError(
                "DECIMAL artifact values must be decimal strings."
            )

        try:
            decimal_value = Decimal(value)
        except InvalidOperation as exc:
            raise ValueError(
                f"Invalid DECIMAL value {value!r}."
            ) from exc

        if not decimal_value.is_finite():
            raise ValueError(
                f"DECIMAL value must be finite: {value!r}."
            )

        return decimal_value

    if not isinstance(value, str):
        return value

    if normalized_type in {"INTEGER", "IDENTIFIER"}:
        return int(value)

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
