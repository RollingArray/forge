"""
FORGE Generation Core
Deterministic/statistical data generation.

This module is UI-independent.
"""

from __future__ import annotations

import random
import string
import time
from typing import Any

import importlib.util
import sys
from pathlib import Path


RESULT_PATH = Path(__file__).resolve().parent / "result.py"

result_spec = importlib.util.spec_from_file_location(
    "forge_generation_result",
    RESULT_PATH,
)

if result_spec is None or result_spec.loader is None:
    raise RuntimeError(
        f"Unable to load generation result contract from {RESULT_PATH}"
    )

result_module = importlib.util.module_from_spec(result_spec)

sys.modules["forge_generation_result"] = result_module

result_spec.loader.exec_module(result_module)

GenerationChunkResult = result_module.GenerationChunkResult
GenerationChunkStatus = result_module.GenerationChunkStatus


def generate_identifier(
    row_number: int,
) -> int:
    """Generate a deterministic sequential identifier."""

    return row_number + 1


def generate_boolean(
    rng: random.Random,
) -> bool:
    """Generate a random boolean value."""

    return rng.choice([True, False])


def generate_integer(
    generation: dict[str, Any],
    rng: random.Random,
) -> int:
    """Generate an INTEGER according to its declared distribution."""

    distribution = generation.get("distribution")
    parameters = generation.get("parameters", {})

    if distribution in {"UNIFORM", "DISCRETE_UNIFORM"}:
        minimum = parameters["minimum"]
        maximum = parameters["maximum"]

        return rng.randint(
            minimum,
            maximum,
        )

    if distribution == "CATEGORICAL":
        values = parameters["values"]

        return rng.choice(values)

    raise ValueError(
        f"Unsupported INTEGER distribution: {distribution!r}"
    )


def generate_decimal(
    generation: dict[str, Any],
    rng: random.Random,
) -> float:
    """Generate a DECIMAL according to its declared distribution."""

    distribution = generation.get("distribution")
    parameters = generation.get("parameters", {})

    if distribution == "UNIFORM":
        minimum = parameters["minimum"]
        maximum = parameters["maximum"]

        return rng.uniform(
            minimum,
            maximum,
        )

    if distribution == "NORMAL":
        mean = parameters.get("mean", 0.0)
        standard_deviation = parameters.get(
            "standard_deviation",
            1.0,
        )

        return rng.normalvariate(
            mean,
            standard_deviation,
        )

    raise ValueError(
        f"Unsupported DECIMAL distribution: {distribution!r}"
    )


def generate_categorical(
    generation: dict[str, Any],
    rng: random.Random,
) -> Any:
    """Generate a value from a declared categorical vocabulary."""

    parameters = generation.get("parameters", {})
    values = parameters["values"]

    return rng.choice(values)


def generate_random_string(
    generation: dict[str, Any],
    rng: random.Random,
) -> str:
    """Generate an opaque random string."""

    parameters = generation.get("parameters", {})

    minimum_length = parameters["minimum_length"]
    maximum_length = parameters["maximum_length"]
    character_set = parameters["character_set"]

    if character_set == "ALPHA":
        alphabet = string.ascii_letters
    elif character_set == "DIGITS":
        alphabet = string.digits
    elif character_set == "ALPHANUMERIC":
        alphabet = string.ascii_letters + string.digits
    else:
        raise ValueError(
            f"Unsupported character set: {character_set!r}"
        )

    length = rng.randint(
        minimum_length,
        maximum_length,
    )

    return "".join(
        rng.choice(alphabet)
        for _ in range(length)
    )


def generate_pattern(
    generation: dict[str, Any],
    rng: random.Random,
) -> str:
    """
    Generate a value from a FORGE PATTERN.

    Supported tokens outside quoted literals:
        # -> digit
        A -> uppercase letter
        a -> lowercase letter
        X -> alphanumeric character

    Text enclosed in single quotes is treated entirely as literal text.
    """

    pattern = generation.get(
        "parameters",
        {},
    )["pattern"]

    uppercase = string.ascii_uppercase
    lowercase = string.ascii_lowercase
    digits = string.digits
    alphanumeric = uppercase + lowercase + digits

    result: list[str] = []
    literal_mode = False

    for character in pattern:

        if character == "'":
            literal_mode = not literal_mode
            continue

        if literal_mode:
            result.append(character)

        elif character == "#":
            result.append(rng.choice(digits))

        elif character == "A":
            result.append(rng.choice(uppercase))

        elif character == "a":
            result.append(rng.choice(lowercase))

        elif character == "X":
            result.append(rng.choice(alphanumeric))

        else:
            result.append(character)

    if literal_mode:
        raise ValueError(
            "PATTERN contains an unterminated literal section."
        )

    return "".join(result)


def generate_field_value(
    field: dict[str, Any],
    row_number: int,
    rng: random.Random,
) -> Any:
    """
    Generate one value for one field.

    This function dispatches to the appropriate primitive generator.
    """

    field_type = field.get("type")

    if field_type == "IDENTIFIER":
        return generate_identifier(row_number)

    if field_type == "BOOLEAN":
        return generate_boolean(rng)

    generation = field.get("generation")

    if not isinstance(generation, dict):
        raise ValueError(
            f"Field {field.get('name')!r} has no generation configuration."
        )

    if field_type == "INTEGER":
        return generate_integer(
            generation,
            rng,
        )

    if field_type == "DECIMAL":
        return generate_decimal(
            generation,
            rng,
        )

    if field_type == "CATEGORICAL":
        return generate_categorical(
            generation,
            rng,
        )

    if field_type == "STRING":

        generator = generation.get("generator")

        if generator == "RANDOM_STRING":
            return generate_random_string(
                generation,
                rng,
            )

        if generator == "PATTERN":
            return generate_pattern(
                generation,
                rng,
            )

        if generator == "SEMANTIC":
            raise NotImplementedError(
                "SEMANTIC generation is handled by the semantic generation service."
            )

        if generation.get("distribution") == "CATEGORICAL":
            return generate_categorical(
                generation,
                rng,
            )

    raise ValueError(
        f"Unsupported field generation: "
        f"{field.get('name')!r} ({field_type!r})"
    )


def generate_entity_chunk(
    entity: dict[str, Any],
    start_row: int,
    row_count: int,
    seed: int,
) -> list[dict[str, Any]]:
    """
    Generate one bounded chunk of rows for one entity.

    The function is deterministic for the same entity definition,
    row range, and seed.

    Relationship, dependency, constraint-aware, and semantic
    generation are handled by higher-level generation services.
    """

    entity_name = entity.get("name")

    if not isinstance(entity_name, str) or not entity_name:
        raise ValueError(
            "Entity must have a non-empty name."
        )

    if (
        not isinstance(start_row, int)
        or isinstance(start_row, bool)
        or start_row < 0
    ):
        raise ValueError(
            "start_row must be a non-negative integer."
        )

    if (
        not isinstance(row_count, int)
        or isinstance(row_count, bool)
        or row_count < 0
    ):
        raise ValueError(
            "row_count must be a non-negative integer."
        )

    fields = entity.get("fields")

    if not isinstance(fields, list):
        raise ValueError(
            f"{entity_name}: fields must be a list."
        )

    rng = random.Random(
        seed
    )

    rows: list[dict[str, Any]] = []

    for offset in range(row_count):

        row_number = start_row + offset

        row = {}

        for field in fields:

            field_name = field.get("name")

            if not isinstance(field_name, str) or not field_name:
                raise ValueError(
                    f"{entity_name}: field must have a non-empty name."
                )

            row[field_name] = generate_field_value(
                field=field,
                row_number=row_number,
                rng=rng,
            )

        rows.append(row)

    return rows


def generate_entity_chunk_result(
    entity: dict[str, Any],
    chunk_number: int,
    start_row: int,
    row_count: int,
    seed: int,
) -> GenerationChunkResult:
    """
    Generate one entity chunk and return its execution result.

    The underlying row generation remains deterministic and unchanged.
    This wrapper adds execution metadata required by the generation job layer.
    """

    entity_name = entity.get("name")

    if not isinstance(entity_name, str) or not entity_name:
        raise ValueError(
            "Entity must have a non-empty name."
        )

    start_time = time.perf_counter()

    try:
        rows = generate_entity_chunk(
            entity=entity,
            start_row=start_row,
            row_count=row_count,
            seed=seed,
        )

    except Exception as exc:
        elapsed_seconds = time.perf_counter() - start_time

        return GenerationChunkResult(
            entity_name=entity_name,
            chunk_number=chunk_number,
            row_count=0,
            status=GenerationChunkStatus.FAILED,
            elapsed_seconds=elapsed_seconds,
            error=str(exc),
        )

    elapsed_seconds = time.perf_counter() - start_time

    return GenerationChunkResult(
        entity_name=entity_name,
        chunk_number=chunk_number,
        row_count=len(rows),
        status=GenerationChunkStatus.COMPLETED,
        elapsed_seconds=elapsed_seconds,
    )
