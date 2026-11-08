"""Shared deterministic validation for FORGE field generation settings."""

from decimal import Decimal, InvalidOperation
from typing import Any


def _finite_number(value: Any) -> Decimal | None:
    """Return a finite decimal value, excluding booleans and invalid inputs."""
    if isinstance(value, bool) or value is None:
        return None

    try:
        number = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return None

    return number if number.is_finite() else None


def validate_field_generation(
    field: dict[str, Any],
    *,
    require_generation: bool = True,
) -> list[str]:
    """Return generation-configuration errors for one canonical field."""

    if not isinstance(field, dict):
        return ["Field definition must be an object."]

    field_type = field.get("type")
    identity = field.get("identity")
    generation = field.get("generation")

    if identity is not None and not isinstance(identity, dict):
        return ["identity must be an object."]

    if generation is not None and not isinstance(generation, dict):
        return ["generation must be an object."]

    identity = identity or {}
    generation = generation or {}

    parameters = generation.get("parameters")
    if parameters is not None and not isinstance(parameters, dict):
        return ["parameters must be an object."]
    parameters = parameters or {}

    errors: list[str] = []

    # FK source fields receive their values through FK assignment. Their
    # configuration structure must still be valid, but scalar generation
    # settings are not required (except IDENTIFIER identity strategy).
    if not require_generation and field_type != "IDENTIFIER":
        return errors

    if field_type == "IDENTIFIER":
        if identity.get("strategy") != "SEQUENTIAL_ID":
            errors.append("IDENTIFIER requires SEQUENTIAL_ID.")
        return errors

    if field_type == "BOOLEAN":
        if generation.get("strategy") != "RANDOM":
            errors.append("BOOLEAN requires RANDOM.")
        return errors

    generator = generation.get("generator")
    distribution = generation.get("distribution")

    if field_type == "STRING":
        if generation.get("strategy") != "RANDOM":
            errors.append("STRING requires generation.strategy RANDOM.")

        if generator == "RANDOM_STRING":
            minimum = parameters.get("minimum_length")
            maximum = parameters.get("maximum_length")
            charset = parameters.get("character_set")

            if (
                isinstance(minimum, bool)
                or not isinstance(minimum, int)
                or isinstance(maximum, bool)
                or not isinstance(maximum, int)
                or minimum < 1
                or maximum < minimum
            ):
                errors.append(
                    "RANDOM_STRING requires positive ordered integer "
                    "minimum_length and maximum_length."
                )

            if charset not in {"ALPHA", "DIGITS", "ALPHANUMERIC"}:
                errors.append(
                    "RANDOM_STRING requires a supported character_set."
                )

        elif generator == "PATTERN":
            pattern = parameters.get("pattern")
            if not isinstance(pattern, str) or not pattern.strip():
                errors.append("PATTERN requires a non-empty pattern.")

        elif generator == "SEMANTIC":
            description = parameters.get("description")
            mode = parameters.get("mode")

            if not isinstance(description, str) or not description.strip():
                errors.append("SEMANTIC requires a non-empty description.")

            if mode not in {"UNIQUE", "VOCABULARY"}:
                errors.append("SEMANTIC mode must be UNIQUE or VOCABULARY.")

        else:
            errors.append(
                "STRING requires RANDOM_STRING, PATTERN, or SEMANTIC."
            )

        return errors

    if field_type == "CATEGORICAL":
        values = parameters.get("values")
        if (
            generation.get("strategy") != "RANDOM"
            or distribution != "CATEGORICAL"
            or not isinstance(values, list)
            or not values
        ):
            errors.append(
                "CATEGORICAL requires RANDOM, CATEGORICAL distribution, "
                "and a non-empty values list."
            )
        return errors

    if field_type in {"INTEGER", "DECIMAL"}:
        allowed = (
            {"UNIFORM", "DISCRETE_UNIFORM"}
            if field_type == "INTEGER"
            else {"UNIFORM", "NORMAL"}
        )

        if generation.get("strategy") != "RANDOM" or distribution not in allowed:
            errors.append(
                f"{field_type} supports only RANDOM with distributions "
                f"{', '.join(sorted(allowed))}."
            )

        minimum = _finite_number(parameters.get("minimum"))
        maximum = _finite_number(parameters.get("maximum"))

        if minimum is None or maximum is None:
            errors.append(
                "minimum and maximum must be finite numeric values."
            )
        else:
            if minimum > maximum:
                errors.append("minimum cannot exceed maximum.")

            if field_type == "INTEGER" and (
                minimum != minimum.to_integral_value()
                or maximum != maximum.to_integral_value()
            ):
                errors.append("INTEGER bounds must be whole numbers.")

        return errors

    errors.append(f"unsupported field type {field_type!r}.")
    return errors
