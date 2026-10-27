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
        """Generate a string according to its declared generator."""

        generation = field.get("generation") or {}
        parameters = generation.get("parameters") or {}
        generator = generation.get("generator")
        field_name = field.get("name", "FIELD")

        if generator == "RANDOM_STRING":
            minimum = parameters.get("minimum_length")
            maximum = parameters.get("maximum_length")
            character_set = parameters.get("character_set")


            if (
                isinstance(minimum, bool)
                or not isinstance(minimum, int)
                or isinstance(maximum, bool)
                or not isinstance(maximum, int)
                or minimum < 1
                or maximum < minimum
            ):
                raise GenerationError(
                    f"Invalid string length range for {field_name}."
                )

            alphabets = {
                "ALPHA": "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz",
                "DIGITS": "0123456789",
                "ALPHANUMERIC": (
                    "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
                    "abcdefghijklmnopqrstuvwxyz"
                    "0123456789"
                ),
            }
            alphabet = alphabets.get(character_set)

            if alphabet is None:
                raise GenerationError(
                    f"Unsupported character set for {field_name}: "
                    f"{character_set!r}"
                )

            length = self._random.randint(minimum, maximum)
            return "".join(
                self._random.choice(alphabet)
                for _ in range(length)
            )

        if generator == "PATTERN":
            pattern = parameters.get("pattern")

            if isinstance(pattern, str):
                pattern = pattern.strip()

            if not isinstance(pattern, str) or not pattern:
                raise GenerationError(
                    f"Pattern string field requires a non-empty pattern: "
                    f"{field_name}"
                )

            alphabets = {
                "#": "0123456789",
                "A": "ABCDEFGHIJKLMNOPQRSTUVWXYZ",
                "a": "abcdefghijklmnopqrstuvwxyz",
                "X": (
                    "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
                    "abcdefghijklmnopqrstuvwxyz"
                    "0123456789"
                ),
            }

            return "".join(
                self._random.choice(alphabets[character])
                if character in alphabets
                else character
                for character in pattern
            )

        if generator == "SEMANTIC":
            raise GenerationError(
                f"Semantic generation for {field_name} must be handled "
                "by RowGenerator."
            )

        raise GenerationError(
            f"Unsupported string generator for {field_name}: "
            f"{generator!r}"
        )

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

    @staticmethod
    def _numeric_bounds(
        *,
        field: dict[str, Any],
        parameters: dict[str, Any],
        field_type: str,
    ) -> tuple[Decimal, Decimal]:
        """Parse and validate finite, ordered numeric bounds."""

        field_name = field.get("name", "FIELD")
        minimum = parameters.get("minimum")
        maximum = parameters.get("maximum")

        if (
            isinstance(minimum, bool)
            or isinstance(maximum, bool)
            or minimum is None
            or maximum is None
        ):
            raise GenerationError(
                f"{field_type} field requires numeric minimum and maximum: "
                f"{field_name}"
            )

        try:
            minimum_decimal = Decimal(str(minimum))
            maximum_decimal = Decimal(str(maximum))
        except (ArithmeticError, ValueError, TypeError):
            raise GenerationError(
                f"{field_type} field requires valid numeric bounds: "
                f"{field_name}"
            ) from None

        if not minimum_decimal.is_finite() or not maximum_decimal.is_finite():
            raise GenerationError(
                f"{field_type} field bounds must be finite: {field_name}"
            )

        if minimum_decimal > maximum_decimal:
            raise GenerationError(
                f"{field_type} field minimum cannot exceed maximum: "
                f"{field_name}"
            )

        return minimum_decimal, maximum_decimal

    def _generate_integer(
        self,
        *,
        field: dict[str, Any],
    ) -> int:
        """Generate an integer according to its declared distribution."""

        generation = field.get("generation") or {}
        parameters = generation.get("parameters") or {}
        distribution = generation.get("distribution")
        field_name = field.get("name", "FIELD")

        if distribution not in {"UNIFORM", "DISCRETE_UNIFORM"}:
            raise GenerationError(
                f"Unsupported integer distribution for {field_name}: "
                f"{distribution!r}"
            )

        minimum, maximum = self._numeric_bounds(
            field=field,
            parameters=parameters,
            field_type="Integer",
        )

        if (
            minimum != minimum.to_integral_value()
            or maximum != maximum.to_integral_value()
        ):
            raise GenerationError(
                f"Integer field bounds must be whole numbers: {field_name}"
            )

        return self._random.randint(int(minimum), int(maximum))

    def _generate_decimal(
        self,
        *,
        field: dict[str, Any],
    ) -> Decimal:
        """Generate a decimal according to its declared distribution."""

        generation = field.get("generation") or {}
        parameters = generation.get("parameters") or {}
        distribution = generation.get("distribution")
        field_name = field.get("name", "FIELD")

        if distribution != "UNIFORM":
            raise GenerationError(
                f"Unsupported decimal distribution for {field_name}: "
                f"{distribution!r}"
            )

        minimum, maximum = self._numeric_bounds(
            field=field,
            parameters=parameters,
            field_type="Decimal",
        )

        if minimum == maximum:
            return minimum

        return minimum + (maximum - minimum) * Decimal(
            str(self._random.random())
        )

    def _generate_boolean(self) -> bool:
        """Generate a boolean value."""

        return bool(self._random.getrandbits(1))
