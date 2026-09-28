"""
File: generator.py
Purpose: Deterministic scalar field generation for FORGE.
"""

from __future__ import annotations

import random
from decimal import Decimal
from typing import Any


class GenerationError(ValueError):
    """Raised when a field cannot be generated from its specification."""


class Generator:
    """Generate scalar values from production FORGE field definitions."""

    def __init__(self, seed: int) -> None:
        self._random = random.Random(seed)

    def choose_from(
        self,
        values: list[str],
    ) -> str:
        """Choose one value deterministically from a semantic vocabulary."""

        if not values:
            raise GenerationError(
                "Cannot choose from an empty value list."
            )

        return str(self._random.choice(values))

    def generate_value(
        self,
        field: dict[str, Any],
        row_number: int,
    ) -> Any:
        """Generate one scalar value from a field definition."""

        field_type = field.get("type")

        if field_type == "IDENTIFIER":
            return self._generate_identifier(
                field=field,
                row_number=row_number,
            )

        if field_type == "STRING":
            return self._generate_string(
                field=field,
            )

        if field_type == "CATEGORICAL":
            return self._generate_categorical(
                field=field,
            )

        if field_type == "INTEGER":
            return self._generate_integer(
                field=field,
            )

        if field_type == "DECIMAL":
            return self._generate_decimal(
                field=field,
            )

        if field_type == "BOOLEAN":
            return self._generate_boolean()

        raise GenerationError(
            f"Unsupported field type: {field_type!r}"
        )

    @staticmethod
    def _generate_identifier(
        *,
        field: dict[str, Any],
        row_number: int,
    ) -> int:
        """Generate an identifier according to its identity strategy."""

        identity = field.get("identity") or {}
        strategy = identity.get("strategy")

        if strategy != "SEQUENTIAL_ID":
            raise GenerationError(
                "Unsupported identifier strategy: "
                f"{strategy!r}"
            )

        return row_number

    def _generate_string(
        self,
        *,
        field: dict[str, Any],
    ) -> str:
        """Generate a deterministic string value."""

        return f"{field.get('name', 'FIELD')}_{self._random.randint(1, 1_000_000)}"

    def _generate_categorical(
        self,
        *,
        field: dict[str, Any],
    ) -> str:
        """Generate a deterministic categorical value."""

        generation = field.get("generation") or {}
        parameters = generation.get("parameters") or {}
        values = parameters.get("values")

        if not isinstance(values, list) or not values:
            raise GenerationError(
                "Categorical field requires a non-empty values list: "
                f"{field.get('name')}"
            )

        return str(self._random.choice(values))

    def _generate_integer(
        self,
        *,
        field: dict[str, Any],
    ) -> int:
        """Generate an integer value from its production definition."""

        generation = field.get("generation") or {}
        parameters = generation.get("parameters") or {}

        if generation.get("distribution") == "UNIFORM":
            minimum = parameters.get("minimum")
            maximum = parameters.get("maximum")

            if minimum is None or maximum is None:
                raise GenerationError(
                    f"Uniform integer field requires minimum and maximum: "
                    f"{field.get('name')}"
                )

            if minimum > maximum:
                raise GenerationError(
                    f"Integer field minimum cannot exceed maximum: "
                    f"{field.get('name')}"
                )

            return self._random.randint(
                int(minimum),
                int(maximum),
            )

        return self._random.randint(1, 1_000)

    def _generate_decimal(
        self,
        *,
        field: dict[str, Any],
    ) -> Decimal:
        """Generate a decimal value from its production definition."""

        generation = field.get("generation") or {}
        parameters = generation.get("parameters") or {}

        if generation.get("distribution") == "UNIFORM":
            minimum = parameters.get("minimum")
            maximum = parameters.get("maximum")

            if minimum is None or maximum is None:
                raise GenerationError(
                    f"Uniform decimal field requires minimum and maximum: "
                    f"{field.get('name')}"
                )

            if minimum > maximum:
                raise GenerationError(
                    f"Decimal field minimum cannot exceed maximum: "
                    f"{field.get('name')}"
                )

            minimum_decimal = Decimal(str(minimum))
            maximum_decimal = Decimal(str(maximum))

            return (
                minimum_decimal
                + (
                    maximum_decimal
                    - minimum_decimal
                ) * Decimal(str(self._random.random()))
            )

        return Decimal(
            self._random.randint(1, 100_000)
        ) / Decimal("100")

    def _generate_boolean(self) -> bool:
        """Generate a boolean value."""

        return bool(self._random.getrandbits(1))
