"""
FORGE Generation Core
Deterministic/statistical data generation.

This module is UI-independent.
"""

from __future__ import annotations

import importlib.util
import random
import string
import sys
import time
from itertools import product
from pathlib import Path
from typing import Any

from .relationship import (
    build_relationship_assignments,
    get_parent_child_entities,
    get_parent_child_fields,
)

RESULT_PATH = Path(__file__).resolve().parent / "result.py"

result_spec = importlib.util.spec_from_file_location(
    "forge_generation_result",
    RESULT_PATH,
)

if result_spec is None or result_spec.loader is None:
    raise RuntimeError(f"Unable to load generation result contract from {RESULT_PATH}")

result_module = importlib.util.module_from_spec(result_spec)

sys.modules["forge_generation_result"] = result_module

result_spec.loader.exec_module(result_module)

GenerationChunkResult = result_module.GenerationChunkResult
GenerationChunkStatus = result_module.GenerationChunkStatus


def build_relationship_assignments_by_field(
    entity_name: str,
    relationships: tuple[Any, ...],
    context: Any,
    row_count: int,
    rng: random.Random,
    start_offset: int = 0,
) -> list[dict[str, Any]]:
    """Build relationship-managed field values for an entity."""

    assignments = [{} for _ in range(row_count)]

    for relationship in relationships:
        parent_child = get_parent_child_entities(
            relationship,
        )

        if parent_child is None:
            continue

        parent_entity, child_entity = parent_child

        if child_entity != entity_name:
            continue

        parent_child_fields = get_parent_child_fields(
            relationship,
        )

        if parent_child_fields is None:
            continue

        parent_fields, _ = parent_child_fields

        parent_keys = context.get_key_values(
            parent_entity,
            parent_fields,
        )

        relationship_assignments = build_relationship_assignments(
            relationship=relationship,
            parent_keys=parent_keys,
            child_count=row_count,
            rng=rng,
            start_offset=start_offset,
        )

        for index, values in enumerate(relationship_assignments):
            assignments[index].update(values)

    return assignments

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
    parameters = generation.get(
        "parameters",
        {},
    )

    if distribution in {
        "UNIFORM",
        "DISCRETE_UNIFORM",
    }:
        minimum = parameters["minimum"]
        maximum = parameters["maximum"]

        return rng.randint(
            minimum,
            maximum,
        )

    if distribution == "CATEGORICAL":
        values = parameters["values"]

        return rng.choice(values)

    raise ValueError(f"Unsupported INTEGER distribution: {distribution!r}")


def generate_decimal(
    generation: dict[str, Any],
    rng: random.Random,
) -> float:
    """Generate a DECIMAL according to its declared distribution."""

    distribution = generation.get("distribution")
    parameters = generation.get(
        "parameters",
        {},
    )

    if distribution == "UNIFORM":
        minimum = parameters["minimum"]
        maximum = parameters["maximum"]

        return rng.uniform(
            minimum,
            maximum,
        )

    if distribution == "NORMAL":
        mean = parameters.get(
            "mean",
            0.0,
        )

        standard_deviation = parameters.get(
            "standard_deviation",
            1.0,
        )

        return rng.normalvariate(
            mean,
            standard_deviation,
        )

    raise ValueError(f"Unsupported DECIMAL distribution: {distribution!r}")


def generate_categorical(
    generation: dict[str, Any],
    rng: random.Random,
) -> Any:
    """Generate a value from a declared categorical vocabulary."""

    parameters = generation.get(
        "parameters",
        {},
    )

    values = parameters["values"]

    return rng.choice(values)


def generate_random_string(
    generation: dict[str, Any],
    rng: random.Random,
) -> str:
    """Generate an opaque random string."""

    parameters = generation.get(
        "parameters",
        {},
    )

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
        raise ValueError(f"Unsupported character set: {character_set!r}")

    length = rng.randint(
        minimum_length,
        maximum_length,
    )

    return "".join(rng.choice(alphabet) for _ in range(length))


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
        raise ValueError("PATTERN contains an unterminated literal section.")

    return "".join(result)


def get_field_constraints(
    entity_name: str,
    field_name: str,
    constraints: tuple[Any, ...],
) -> tuple[Any, ...]:
    """Return constraints applicable to one entity field."""

    return tuple(
        constraint
        for constraint in constraints
        if (
            getattr(constraint, "entity", None) == entity_name
            and getattr(constraint, "field", None) == field_name
        )
    )


def apply_constraint_to_generation(
    generation: dict[str, Any],
    operator: str,
    expected: Any,
) -> dict[str, Any]:
    """Return a generation configuration restricted by one constraint."""

    effective = {
        key: (
            value.copy()
            if isinstance(value, dict)
            else list(value)
            if isinstance(value, list)
            else value
        )
        for key, value in generation.items()
    }

    parameters = dict(
        effective.get(
            "parameters",
            {},
        )
    )

    effective["parameters"] = parameters

    distribution = effective.get("distribution")

    if distribution == "CATEGORICAL":
        values = list(parameters.get("values", []))

        operators = {
            "==": lambda actual: actual == expected,
            "!=": lambda actual: actual != expected,
            ">": lambda actual: actual > expected,
            ">=": lambda actual: actual >= expected,
            "<": lambda actual: actual < expected,
            "<=": lambda actual: actual <= expected,
        }

        predicate = operators.get(operator)

        if predicate is None:
            raise ValueError(
                f"Operator {operator!r} is not supported for "
                "CATEGORICAL generation."
            )

        try:
            values = [
                value
                for value in values
                if predicate(value)
            ]
        except TypeError as exc:
            raise ValueError(
                "Constraint comparison is not compatible with the "
                f"categorical values for operator {operator!r} "
                f"and expected value {expected!r}."
            ) from exc

        if not values:
            raise ValueError(
                "Constraint produces an empty categorical generation "
                f"domain: {operator} {expected!r}."
            )

        parameters["values"] = values
        return effective

    if distribution in {"UNIFORM", "DISCRETE_UNIFORM"}:
        minimum = parameters["minimum"]
        maximum = parameters["maximum"]

        if operator == ">":
            if isinstance(minimum, int) and isinstance(expected, int):
                minimum = max(minimum, expected + 1)
            else:
                import math

                minimum = max(
                    minimum,
                    math.nextafter(
                        float(expected),
                        float("inf"),
                    ),
                )

        elif operator == ">=":
            minimum = max(
                minimum,
                expected,
            )

        elif operator == "<":
            if isinstance(maximum, int) and isinstance(expected, int):
                maximum = min(maximum, expected - 1)
            else:
                import math

                maximum = min(
                    maximum,
                    math.nextafter(
                        float(expected),
                        float("-inf"),
                    ),
                )

        elif operator == "<=":
            maximum = min(
                maximum,
                expected,
            )

        else:
            raise ValueError(
                f"Operator {operator!r} is not supported for "
                f"{distribution} generation."
            )

        if minimum > maximum:
            raise ValueError(
                "Constraint produces an empty numeric generation "
                f"range: {operator} {expected!r}."
            )

        parameters["minimum"] = minimum
        parameters["maximum"] = maximum

        return effective

    raise ValueError(
        f"Constraint-aware generation is not supported for "
        f"distribution {distribution!r}."
    )


def apply_field_constraints(
    entity_name: str,
    field: dict[str, Any],
    constraints: tuple[Any, ...],
) -> dict[str, Any]:
    """Return the effective generation configuration for one entity field."""

    generation = field.get("generation")

    if not isinstance(generation, dict):
        return generation

    field_name = field.get("name")

    effective = dict(generation)

    for constraint in get_field_constraints(
        entity_name=entity_name,
        field_name=field_name,
        constraints=constraints,
    ):
        effective = apply_constraint_to_generation(
            generation=effective,
            operator=constraint.operator,
            expected=constraint.value,
        )

    return effective


def generate_field_value(
    entity_name: str,
    field: dict[str, Any],
    row_number: int,
    rng: random.Random,
    semantic_values: list[str] | None = None,
    constraints: tuple[Any, ...] = (),
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
            f"Field {field.get('name')!r} " "has no generation configuration."
        )

    generation = apply_field_constraints(
        entity_name=entity_name,
        field=field,
        constraints=constraints,
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

            if not semantic_values:
                raise ValueError(
                    f"SEMANTIC values were not provided for field "
                    f"{field.get('name')!r}."
                )

            return rng.choice(semantic_values)

        if generation.get("distribution") == "CATEGORICAL":
            return generate_categorical(
                generation,
                rng,
            )

    raise ValueError(
        f"Unsupported field generation: " f"{field.get('name')!r} ({field_type!r})"
    )


def resolve_foreign_key_value(
    dependency: Any,
    context: Any,
    rng: random.Random,
    existing_values: dict[str, Any] | None = None,
    used_child_identities: set[tuple[Any, ...]] | None = None,
    child_identity_fields: tuple[str, ...] = (),
    foreign_key_key_spaces: dict[
        tuple[str, tuple[str, ...]],
        list[tuple[Any, ...]],
    ] | None = None,
) -> dict[str, Any]:
    """Select a compatible existing parent key for a foreign-key dependency.

    Existing source-field values are treated as authoritative constraints.
    When all FK source fields are already assigned, validate that exact
    parent key directly instead of scanning the complete parent key space.

    When the foreign key covers the complete child identity, parent keys
    are filtered using the declared child identity field order.
    """

    key = (
        dependency.parent_entity,
        tuple(dependency.target_fields),
    )

    if foreign_key_key_spaces is not None:
        parent_keys = foreign_key_key_spaces.get(key, [])
    else:
        parent_keys = context.get_key_values(
            dependency.parent_entity,
            dependency.target_fields,
        )

    if not parent_keys:
        raise ValueError(
            "No generated parent keys available for "
            f"{dependency.parent_entity}."
        )

    if existing_values is None:
        existing_values = {}

    # Fast path: all FK source fields have already been assigned.
    #
    # This is the common path for relationship-managed foreign keys such
    # as SALES_ITEM.ORDER_ID. There is no reason to scan every parent key
    # when the exact requested key is already known.
    all_source_fields_present = all(
        source_field in existing_values
        for source_field in dependency.source_fields
    )

    if all_source_fields_present:
        requested_key = tuple(
            existing_values[source_field]
            for source_field in dependency.source_fields
        )

        parent_key_set = set(parent_keys)

        if requested_key not in parent_key_set:
            raise ValueError(
                f"Foreign-key value {requested_key!r} for "
                f"{dependency.parent_entity} is not present in "
                "the generated parent key space."
            )

        is_complete_identity_fk = (
            bool(child_identity_fields)
            and set(dependency.source_fields)
            == set(child_identity_fields)
            and len(dependency.source_fields)
            == len(child_identity_fields)
        )

        if (
            used_child_identities is not None
            and is_complete_identity_fk
        ):
            values_by_field = dict(
                zip(
                    dependency.source_fields,
                    requested_key,
                )
            )

            child_identity = tuple(
                values_by_field[field]
                for field in child_identity_fields
            )

            if child_identity in used_child_identities:
                raise ValueError(
                    f"Foreign-key identity {child_identity!r} "
                    "has already been consumed."
                )

        return dict(
            zip(
                dependency.source_fields,
                requested_key,
            )
        )

    # General path: some FK source fields are not assigned yet.
    compatible_keys: list[tuple[Any, ...]] = []

    for parent_key in parent_keys:
        compatible = True

        for source_field, target_value in zip(
            dependency.source_fields,
            parent_key,
        ):
            if source_field in existing_values:
                if existing_values[source_field] != target_value:
                    compatible = False
                    break

        if compatible:
            compatible_keys.append(parent_key)

    if not compatible_keys:
        raise ValueError(
            f"No compatible parent key found for foreign-key "
            f"{dependency!r} given existing values "
            f"{existing_values!r}."
        )

    # When the FK covers the complete child identity, each child row
    # must consume a distinct compatible parent identity.
    is_complete_identity_fk = (
        bool(child_identity_fields)
        and set(dependency.source_fields)
        == set(child_identity_fields)
        and len(dependency.source_fields)
        == len(child_identity_fields)
    )

    if (
        used_child_identities is not None
        and is_complete_identity_fk
    ):
        unused_compatible_keys: list[tuple[Any, ...]] = []

        for parent_key in compatible_keys:
            values_by_field = dict(
                zip(
                    dependency.source_fields,
                    parent_key,
                )
            )

            child_identity = tuple(
                values_by_field[field]
                for field in child_identity_fields
            )

            if child_identity not in used_child_identities:
                unused_compatible_keys.append(parent_key)

        compatible_keys = unused_compatible_keys

    if not compatible_keys:
        raise ValueError(
            f"No unused compatible parent key found for foreign-key "
            f"{dependency!r}."
        )

    selected_key = rng.choice(compatible_keys)

    return dict(
        zip(
            dependency.source_fields,
            selected_key,
        )
    )

def _resolve_relationship_group_assignments(
    row: dict[str, Any],
    entity_name: str,
    relationship_groups: tuple[Any, ...],
    context: Any | None,
    rng: random.Random,
    relationship_key_spaces: dict[
        tuple[str, tuple[str, ...]],
        list[tuple[Any, ...]],
    ] | None = None,
) -> dict[str, Any]:
    """
    Resolve grouped relationships as complete parent-key units.

    A relationship group represents one logical parent-child key
    mapping. All fields in the group are selected from the same
    parent identity so composite parent keys remain coupled.
    """

    if context is None:
        return {}

    assignments: dict[str, Any] = {}

    for group in relationship_groups:
        if group.child_entity != entity_name:
            continue

        parent_fields = tuple(group.parent_fields)
        child_fields = tuple(group.child_fields)

        if not parent_fields or not child_fields:
            continue

        if len(parent_fields) != len(child_fields):
            raise ValueError(
                "Relationship group field counts do not match for "
                f"{group.parent_entity} -> {group.child_entity}."
            )

        key = (
            group.parent_entity,
            parent_fields,
        )

        if relationship_key_spaces is not None:
            parent_keys = relationship_key_spaces.get(key, [])
        else:
            parent_keys = context.get_key_values(
                group.parent_entity,
                parent_fields,
            )

        if not parent_keys:
            raise ValueError(
                "No generated parent keys available for "
                f"relationship {group.parent_entity} -> "
                f"{group.child_entity}."
            )

        selected_key = rng.choice(parent_keys)

        for child_field, value in zip(
            child_fields,
            selected_key,
        ):
            # A RelationshipGroup represents the complete logical
            # parent-child relationship. It is authoritative over
            # legacy field-level relationship assignments.
            assignments[child_field] = value

    return assignments


def _prepare_relationship_key_spaces(
    entity_name: str,
    relationship_groups: tuple[Any, ...],
    context: Any | None,
) -> dict[
    tuple[str, tuple[str, ...]],
    list[tuple[Any, ...]],
]:
    """Prepare parent key spaces once for a generation chunk."""

    if context is None:
        return {}

    key_spaces: dict[
        tuple[str, tuple[str, ...]],
        list[tuple[Any, ...]],
    ] = {}

    for group in relationship_groups:
        if group.child_entity != entity_name:
            continue

        parent_fields = tuple(group.parent_fields)

        if not parent_fields:
            continue

        key = (
            group.parent_entity,
            parent_fields,
        )

        if key in key_spaces:
            continue

        parent_keys = context.get_key_values(
            group.parent_entity,
            parent_fields,
        )

        if not parent_keys:
            raise ValueError(
                "No generated parent keys available for "
                f"relationship {group.parent_entity} -> "
                f"{group.child_entity}."
            )

        key_spaces[key] = parent_keys

    return key_spaces



def _prepare_identity_key_spaces(
    identity_fields: tuple[str, ...],
    dependencies: tuple[Any, ...],
    context: Any | None,
) -> dict[
    tuple[str, tuple[str, ...]],
    list[tuple[Any, ...]],
]:
    """Prepare parent key spaces used by identity allocation."""

    if context is None:
        return {}

    key_spaces: dict[
        tuple[str, tuple[str, ...]],
        list[tuple[Any, ...]],
    ] = {}

    identity_field_set = set(identity_fields)

    for dependency in dependencies:
        source_fields = tuple(
            dependency.source_fields
        )

        # Only parent-backed identity dimensions belong here.
        if not source_fields:
            continue

        if not all(
            field in identity_field_set
            for field in source_fields
        ):
            continue

        key = (
            dependency.parent_entity,
            tuple(dependency.target_fields),
        )

        if key in key_spaces:
            continue

        parent_keys = context.get_key_values(
            dependency.parent_entity,
            dependency.target_fields,
        )

        if not parent_keys:
            raise ValueError(
                "No generated parent keys available for "
                f"{dependency.parent_entity}."
            )

        key_spaces[key] = parent_keys

    return key_spaces


def _prepare_foreign_key_key_spaces(
    dependencies: tuple[Any, ...],
    context: Any | None,
) -> dict[
    tuple[str, tuple[str, ...]],
    list[tuple[Any, ...]],
]:
    """Prepare all FK parent key spaces once per generation chunk."""

    if context is None:
        return {}

    key_spaces = {}

    for dependency in dependencies:
        key = (
            dependency.parent_entity,
            tuple(dependency.target_fields),
        )

        if key in key_spaces:
            continue

        parent_keys = context.get_key_values(
            dependency.parent_entity,
            dependency.target_fields,
        )

        if not parent_keys:
            raise ValueError(
                "No generated parent keys available for "
                f"{dependency.parent_entity}."
            )

        key_spaces[key] = parent_keys

    return key_spaces

def _prepare_composite_fk_key_spaces(
    dependencies: tuple[Any, ...],
    context: Any | None,
) -> dict[
    tuple[str, tuple[str, ...]],
    list[tuple[Any, ...]],
]:
    """Prepare composite FK parent key spaces once per generation chunk."""

    if context is None:
        return {}

    key_spaces: dict[
        tuple[str, tuple[str, ...]],
        list[tuple[Any, ...]],
    ] = {}

    for dependency in dependencies:
        source_fields = tuple(
            dependency.source_fields
        )

        # This cache is only needed for genuinely composite FKs.
        if len(source_fields) < 2:
            continue

        key = (
            dependency.parent_entity,
            tuple(dependency.target_fields),
        )

        if key in key_spaces:
            continue

        parent_keys = context.get_key_values(
            dependency.parent_entity,
            dependency.target_fields,
        )

        if not parent_keys:
            raise ValueError(
                "No generated parent keys available for "
                f"{dependency.parent_entity}."
            )

        key_spaces[key] = parent_keys

    return key_spaces



def _resolve_relationship_identity_space_assignment(
    row: dict[str, Any],
    fields: tuple[dict[str, Any], ...],
    identity_fields: tuple[str, ...],
    dependencies: tuple[Any, ...],
    context: Any | None,
    existing_identities: set[tuple[Any, ...]],
    rng: random.Random,
    identity_key_spaces: dict[
        tuple[str, tuple[str, ...]],
        list[tuple[Any, ...]],
    ] | None = None,
) -> dict[str, Any]:
    """Allocate a feasible composite identity.

    Parent-backed identity dimensions are treated as finite identity
    dimensions. A relationship-selected parent key may already be
    exhausted for the child identity space, so another valid parent key
    may be selected when necessary.
    """

    if context is None:
        return {}

    assignments: dict[str, Any] = {}

    field_by_name = {
        field["name"]: field
        for field in fields
    }

    dimensions: list[
        tuple[tuple[str, ...], list[Any]]
    ] = []

    # --------------------------------------------------------------
    # Parent-backed identity dimensions
    # --------------------------------------------------------------

    for dependency in dependencies:
        source_fields = tuple(
            dependency.source_fields
        )

        if not source_fields:
            continue

        if not all(
            field in identity_fields
            for field in source_fields
        ):
            continue

        key = (
            dependency.parent_entity,
            tuple(dependency.target_fields),
        )

        if identity_key_spaces is not None:
            parent_keys = identity_key_spaces.get(
                key,
                [],
            )
        else:
            parent_keys = context.get_key_values(
                dependency.parent_entity,
                dependency.target_fields,
            )

        if not parent_keys:
            raise ValueError(
                "No generated parent keys available for "
                f"{dependency.parent_entity}."
            )

        # Parent identity is a dimension of the complete child
        # identity. Keep it selectable so a parent whose local identity
        # combinations are exhausted can be replaced by another valid
        # parent.
        if len(source_fields) == 1:
            dimensions.append(
                (
                    source_fields,
                    [
                        parent_key[0]
                        for parent_key in parent_keys
                    ],
                )
            )
        else:
            dimensions.append(
                (
                    source_fields,
                    parent_keys,
                )
            )

    # --------------------------------------------------------------
    # Local finite identity dimensions
    # --------------------------------------------------------------

    for field_name in identity_fields:
        if any(
            field_name in dimension_fields
            for dimension_fields, _ in dimensions
        ):
            continue

        field = field_by_name.get(field_name)

        if field is None:
            continue

        generation = field.get(
            "generation",
            {},
        )

        distribution = generation.get(
            "distribution"
        )

        parameters = generation.get(
            "parameters",
            {},
        )

        values: list[Any] = []

        if distribution == "CATEGORICAL":
            values = list(
                parameters.get(
                    "values",
                    [],
                )
            )

        elif distribution in {
            "DISCRETE_UNIFORM",
            "UNIFORM",
        }:
            minimum = parameters.get(
                "minimum"
            )
            maximum = parameters.get(
                "maximum"
            )

            if (
                minimum is not None
                and maximum is not None
                and minimum <= maximum
            ):
                values = list(
                    range(
                        int(minimum),
                        int(maximum) + 1,
                    )
                )

        if values:
            dimensions.append(
                (
                    (field_name,),
                    values,
                )
            )

    if not dimensions:
        return assignments

    # --------------------------------------------------------------
    # Random search over the feasible identity space
    # --------------------------------------------------------------

    for _ in range(128):
        candidate_assignments = {}

        for dimension_fields, values in dimensions:
            selected = rng.choice(values)

            if len(dimension_fields) == 1:
                candidate_assignments[
                    dimension_fields[0]
                ] = selected
            else:
                for field, value in zip(
                    dimension_fields,
                    selected,
                ):
                    candidate_assignments[field] = value

        candidate_identity = tuple(
            candidate_assignments.get(
                field,
                row.get(field),
            )
            for field in identity_fields
        )

        if (
            all(
                field in candidate_assignments
                or field in row
                for field in identity_fields
            )
            and candidate_identity
            not in existing_identities
        ):
            return candidate_assignments

    # --------------------------------------------------------------
    # Deterministic mixed-radix fallback
    # --------------------------------------------------------------

    counters = [0] * len(dimensions)

    total_capacity = 1

    for _, values in dimensions:
        total_capacity *= len(values)

    if total_capacity <= 0:
        raise ValueError(
            "Unable to generate a unique identity for "
            f"{identity_fields}. The available identity "
            "candidate space is exhausted."
        )

    for _ in range(total_capacity):
        candidate_assignments = {}

        for index, (
            dimension_fields,
            values,
        ) in enumerate(dimensions):

            selected = values[
                counters[index]
            ]

            if len(dimension_fields) == 1:
                candidate_assignments[
                    dimension_fields[0]
                ] = selected
            else:
                for field, value in zip(
                    dimension_fields,
                    selected,
                ):
                    candidate_assignments[field] = value

        candidate_identity = tuple(
            candidate_assignments.get(
                field,
                row.get(field),
            )
            for field in identity_fields
        )

        if (
            all(
                field in candidate_assignments
                or field in row
                for field in identity_fields
            )
            and candidate_identity
            not in existing_identities
        ):
            return candidate_assignments

        for index in reversed(
            range(len(counters))
        ):
            counters[index] += 1

            if counters[index] < len(
                dimensions[index][1]
            ):
                break

            counters[index] = 0
        else:
            break

    raise ValueError(
        "Unable to generate a unique identity for "
        f"{identity_fields}. The available identity "
        "candidate space is exhausted."
    )



def _resolve_composite_foreign_key_assignments(
    row: dict[str, Any],
    dependencies: tuple[Any, ...],
    identity_fields: tuple[str, ...],
    context: Any | None,
    rng: random.Random,
    composite_fk_key_spaces: dict[
        tuple[str, tuple[str, ...]],
        list[tuple[Any, ...]],
    ],
) -> dict[str, Any]:
    """Resolve genuinely composite foreign keys as coupled parent keys."""

    if context is None:
        return {}

    assignments: dict[str, Any] = {}

    for dependency in dependencies:
        source_fields = tuple(
            dependency.source_fields
        )
        target_fields = tuple(
            dependency.target_fields
        )

        if len(source_fields) < 2:
            continue

        if len(source_fields) != len(target_fields):
            raise ValueError(
                "Composite foreign-key field count mismatch for "
                f"{dependency.parent_entity}: "
                f"{source_fields} -> {target_fields}."
            )

        key = (
            dependency.parent_entity,
            target_fields,
        )

        parent_keys = composite_fk_key_spaces.get(
            key,
            [],
        )

        if not parent_keys:
            parent_keys = context.get_key_values(
                dependency.parent_entity,
                target_fields,
            )

        if not parent_keys:
            raise ValueError(
                "No generated parent keys available for "
                f"{dependency.parent_entity}."
            )

        if all(
            field in row
            for field in source_fields
        ):
            requested_key = tuple(
                row[field]
                for field in source_fields
            )

            if requested_key not in set(parent_keys):
                raise ValueError(
                    "Composite foreign-key conflict for "
                    f"{dependency.parent_entity}: "
                    f"{source_fields}={requested_key!r} "
                    "does not exist in the parent key space."
                )

            for source_field, value in zip(
                source_fields,
                requested_key,
            ):
                assignments[source_field] = value

            continue

        existing_values = {
            field: row[field]
            for field in source_fields
            if field in row
        }

        compatible_keys = [
            parent_key
            for parent_key in parent_keys
            if all(
                parent_value == existing_values[field]
                for field, parent_value in zip(
                    source_fields,
                    parent_key,
                )
                if field in existing_values
            )
        ]

        if not compatible_keys:
            raise ValueError(
                "Unable to resolve composite foreign key for "
                f"{dependency.parent_entity}. "
                f"Existing values: {existing_values!r}."
            )

        selected_key = rng.choice(
            compatible_keys
        )

        for source_field, value in zip(
            source_fields,
            selected_key,
        ):
            assignments[source_field] = value

    return assignments


def _resolve_composite_identity_fk_assignments(
    row: dict[str, Any],
    dependencies: tuple[Any, ...],
    identity_fields: tuple[str, ...],
    context: Any | None,
    existing_identities: set[tuple[Any, ...]],
    rng: random.Random,
) -> dict[str, Any]:
    """Allocate a unique identity formed by multiple independent FKs.

    This handles the topology where multiple independent foreign keys
    collectively form the complete child identity.

    The implementation deliberately avoids materializing the Cartesian
    product of parent keys. A random combination is selected directly
    and checked against existing identities. A lazy Cartesian scan is
    used only as an exhaustion fallback.

    Existing relationship-managed values in ``row`` remain authoritative.
    All other FK behavior continues through the existing resolver.
    """

    if (
        context is None
        or len(identity_fields) < 2
        or len(dependencies) < 2
    ):
        return {}

    identity_field_set = set(identity_fields)

    candidate_dependencies: list[Any] = []

    for dependency in dependencies:
        source_fields = tuple(dependency.source_fields)

        if not source_fields:
            return {}

        source_field_set = set(source_fields)

        # This helper only handles FK fields that are part of the
        # child identity.
        if not source_field_set.issubset(identity_field_set):
            return {}

        # A dependency must not repeat a source field internally.
        if len(source_field_set) != len(source_fields):
            return {}

        candidate_dependencies.append(dependency)

    # The existing complete-identity FK path must remain untouched.
    for dependency in candidate_dependencies:
        if (
            set(dependency.source_fields) == identity_field_set
            and len(dependency.source_fields) == len(identity_fields)
        ):
            return {}

    # Independent FKs must not overlap. Their union must cover the
    # complete child identity.
    covered_fields: set[str] = set()

    for dependency in candidate_dependencies:
        source_fields = set(dependency.source_fields)

        if covered_fields.intersection(source_fields):
            return {}

        covered_fields.update(source_fields)

    if covered_fields != identity_field_set:
        return {}

    # Fetch the parent key spaces once. The previous implementation
    # scanned these keys and rebuilt the entire Cartesian product for
    # every child row.
    parent_key_spaces: list[tuple[Any, list[tuple[Any, ...]]]] = []

    for dependency in candidate_dependencies:
        parent_keys = context.get_key_values(
            dependency.parent_entity,
            dependency.target_fields,
        )

        if not parent_keys:
            raise ValueError(
                "No generated parent keys available for "
                f"{dependency.parent_entity}."
            )

        parent_key_spaces.append((dependency, parent_keys))

    # Calculate the available composite identity capacity without
    # constructing the Cartesian product.
    identity_capacity = 1

    for _, parent_keys in parent_key_spaces:
        identity_capacity *= len(parent_keys)

    if len(existing_identities) >= identity_capacity:
        raise ValueError(
            f"Unable to generate a unique identity for "
            f"{identity_fields}. The available composite FK "
            f"identity space is exhausted "
            f"(capacity={identity_capacity}, "
            f"existing={len(existing_identities)})."
        )

    # Most workloads, including PRODUCT_PLANT, occupy only a small
    # fraction of the available Cartesian space. Randomly select one
    # parent key from each independent FK and retry on collision.
    #
    # This changes the hot path from:
    #
    #     O(product(parent_key_counts))
    #
    # per row to approximately:
    #
    #     O(number_of_independent_FKs)
    #
    # per row.
    max_random_attempts = min(
        128,
        max(8, identity_capacity - len(existing_identities)),
    )

    for _ in range(max_random_attempts):
        assignment: dict[str, Any] = {}

        for dependency, parent_keys in parent_key_spaces:
            selected_key = rng.choice(parent_keys)

            for source_field, value in zip(
                dependency.source_fields,
                selected_key,
            ):
                assignment[source_field] = value

        identity = build_identity(
            assignment,
            identity_fields,
        )

        if identity not in existing_identities:
            return assignment

    # Random selection becomes less efficient as the identity space
    # approaches saturation. Fall back to a lazy mixed-radix traversal
    # without ever materializing the Cartesian product.
    key_counts = [len(keys) for _, keys in parent_key_spaces]

    for flat_index in range(identity_capacity):
        remaining = flat_index
        assignment = {}

        # Decode one Cartesian-product position using mixed radix.
        selected_indexes = [0] * len(key_counts)

        for position in range(len(key_counts) - 1, -1, -1):
            count = key_counts[position]
            selected_indexes[position] = remaining % count
            remaining //= count

        for (
            (dependency, parent_keys),
            selected_index,
        ) in zip(
            parent_key_spaces,
            selected_indexes,
        ):
            selected_key = parent_keys[selected_index]

            for source_field, value in zip(
                dependency.source_fields,
                selected_key,
            ):
                assignment[source_field] = value

        identity = build_identity(
            assignment,
            identity_fields,
        )

        if identity not in existing_identities:
            return assignment

    raise ValueError(
        f"Unable to generate a unique identity for "
        f"{identity_fields}. The available composite FK "
        f"identity space is exhausted "
        f"(capacity={identity_capacity}, "
        f"existing={len(existing_identities)})."
    )


def find_field_dependency(
    field_name: str,
    dependencies: tuple[Any, ...],
) -> Any | None:
    """Return the FK dependency containing the requested source field."""

    for dependency in dependencies:

        if field_name in dependency.source_fields:
            return dependency

    return None


def get_identity_fields(
    entity: dict[str, Any],
) -> tuple[str, ...]:
    """Return the declared identity fields for an entity."""

    identity = entity.get(
        "identity",
        {},
    )

    if not isinstance(identity, dict):
        return ()

    fields = identity.get(
        "fields",
        [],
    )

    if not isinstance(fields, list):
        return ()

    return tuple(fields)


def build_identity(
    row: dict[str, Any],
    identity_fields: tuple[str, ...],
) -> tuple[Any, ...]:
    """Build an identity tuple from a generated row."""

    return tuple(row.get(field) for field in identity_fields)


def identity_exists(
    row: dict[str, Any],
    identity_fields: tuple[str, ...],
    existing_identities: set[tuple[Any, ...]],
) -> bool:
    """Return whether a generated identity already exists."""

    identity = build_identity(
        row,
        identity_fields,
    )

    return identity in existing_identities


def validate_identity(
    row: dict[str, Any],
    identity_fields: tuple[str, ...],
    existing_identities: set[tuple[Any, ...]],
) -> tuple[Any, ...]:
    """Validate and return a newly generated identity."""

    if not identity_fields:
        return ()

    identity = build_identity(
        row,
        identity_fields,
    )

    if any(value is None for value in identity):
        raise ValueError(f"Identity contains a missing value: {identity!r}")

    if identity in existing_identities:
        raise ValueError(f"Duplicate identity generated: {identity!r}")

    return identity


def get_categorical_values(
    field: dict[str, Any],
) -> list[Any]:
    """Return the declared categorical candidates for a field."""

    generation = field.get("generation")

    if not isinstance(generation, dict):
        return []

    if generation.get("distribution") != "CATEGORICAL":
        return []

    parameters = generation.get(
        "parameters",
        {},
    )

    values = parameters.get(
        "values",
        [],
    )

    if not isinstance(values, list):
        return []

    return values


def find_identity_candidate(
    row: dict[str, Any],
    fields: list[dict[str, Any]],
    identity_fields: tuple[str, ...],
    existing_identities: set[tuple[Any, ...]],
    rng: random.Random,
    protected_fields: set[str] | None = None,
) -> tuple[dict[str, Any], tuple[Any, ...]]:
    """
    Resolve an identity collision using available candidates.

    Relationship-managed and foreign-key-managed fields are
    authoritative and are never modified by identity resolution.
    """

    identity = build_identity(
        row,
        identity_fields,
    )

    if identity not in existing_identities:
        return row, identity

    if protected_fields is None:
        protected_fields = set()

    # Fast path for composite identities made entirely from finite,
    # non-protected domains. Treat the identity as a Cartesian product
    # rather than changing one field at a time.
    #
    # Example:
    #   ORDER_ID × PARTNER_ROLE
    #   25,000 × 4 = 100,000 feasible identities
    #
    # This avoids random-collision exhaustion when the individual fields
    # are valid but the composite identity is approaching saturation.
    composite_candidates: list[tuple[str, list[Any]]] = []

    for field in fields:
        field_name = field.get("name")

        if field_name not in identity_fields:
            continue

        if field_name in protected_fields:
            continue

        generation = field.get("generation")

        if not isinstance(generation, dict):
            continue

        distribution = generation.get("distribution")

        if distribution == "CATEGORICAL":
            values = get_categorical_values(field)

            if values:
                composite_candidates.append(
                    (
                        field_name,
                        values,
                    )
                )

            continue

        if distribution in {
            "DISCRETE_UNIFORM",
            "UNIFORM",
        }:
            parameters = generation.get(
                "parameters",
                {},
            )

            minimum = parameters.get("minimum")
            maximum = parameters.get("maximum")

            if (
                isinstance(minimum, int)
                and not isinstance(minimum, bool)
                and isinstance(maximum, int)
                and not isinstance(maximum, bool)
                and minimum <= maximum
            ):
                composite_candidates.append(
                    (
                        field_name,
                        list(range(minimum, maximum + 1)),
                    )
                )

    if len(composite_candidates) >= 2:
        # Try randomized combinations first. This keeps generation fast
        # when the composite identity space is comfortably sparse.
        candidate_count = 1

        for _, values in composite_candidates:
            candidate_count *= len(values)

        random_attempts = min(
            128,
            max(16, candidate_count),
        )

        for _ in range(random_attempts):
            candidate_row = row.copy()

            for field_name, values in composite_candidates:
                candidate_row[field_name] = rng.choice(values)

            candidate_identity = build_identity(
                candidate_row,
                identity_fields,
            )

            if candidate_identity not in existing_identities:
                return (
                    candidate_row,
                    candidate_identity,
                )

        # Deterministic fallback. Walk the Cartesian product without
        # materializing the complete product in memory.
        indices = [0] * len(composite_candidates)

        while True:
            candidate_row = row.copy()

            for index, (field_name, values) in zip(
                indices,
                composite_candidates,
            ):
                candidate_row[field_name] = values[index]

            candidate_identity = build_identity(
                candidate_row,
                identity_fields,
            )

            if candidate_identity not in existing_identities:
                return (
                    candidate_row,
                    candidate_identity,
                )

            position = len(indices) - 1

            while position >= 0:
                indices[position] += 1

                if indices[position] < len(
                    composite_candidates[position][1]
                ):
                    break

                indices[position] = 0
                position -= 1

            if position < 0:
                break

    # Fast path for finite numeric identity domains. Avoid materializing
    # and scanning a potentially large candidate range on every collision.
    for field in fields:
        field_name = field.get("name")

        if field_name not in identity_fields:
            continue

        if field_name in protected_fields:
            continue

        generation = field.get("generation")

        if not isinstance(generation, dict):
            continue

        if generation.get("distribution") not in {
            "DISCRETE_UNIFORM",
            "UNIFORM",
        }:
            continue

        parameters = generation.get(
            "parameters",
            {},
        )

        minimum = parameters.get("minimum")
        maximum = parameters.get("maximum")

        if not (
            isinstance(minimum, int)
            and not isinstance(minimum, bool)
            and isinstance(maximum, int)
            and not isinstance(maximum, bool)
            and minimum <= maximum
        ):
            continue

        candidate_count = maximum - minimum + 1

        # Try random values directly. This is normally enough when the
        # finite identity domain is not close to saturation.
        random_attempts = min(
            64,
            max(8, candidate_count),
        )

        for _ in range(random_attempts):
            candidate_row = row.copy()
            candidate_row[field_name] = rng.randint(
                minimum,
                maximum,
            )

            candidate_identity = build_identity(
                candidate_row,
                identity_fields,
            )

            if candidate_identity not in existing_identities:
                return (
                    candidate_row,
                    candidate_identity,
                )

    candidates = _build_identity_candidates(
        row=row,
        fields=fields,
        identity_fields=identity_fields,
        protected_fields=protected_fields,
    )

    rng.shuffle(candidates)

    for field_name, values in candidates:

        for value in values:

            candidate_row = row.copy()
            candidate_row[field_name] = value

            candidate_identity = build_identity(
                candidate_row,
                identity_fields,
            )

            if candidate_identity not in existing_identities:
                return (
                    candidate_row,
                    candidate_identity,
                )

    raise ValueError(
        f"Unable to generate a unique identity for "
        f"{identity_fields}: {identity!r}. "
        "The available identity candidate space is exhausted."
    )

def _build_identity_candidates(
    row: dict[str, Any],
    fields: list[dict[str, Any]],
    identity_fields: tuple[str, ...],
    protected_fields: set[str] | None = None,
) -> list[tuple[str, list[Any]]]:
    """Find finite non-protected candidates for identity resolution."""

    if protected_fields is None:
        protected_fields = set()

    candidates: list[tuple[str, list[Any]]] = []

    for field in fields:

        field_name = field.get("name")

        if field_name not in identity_fields:
            continue

        if field_name in protected_fields:
            continue

        generation = field.get("generation")

        if not isinstance(generation, dict):
            continue

        distribution = generation.get("distribution")

        if distribution == "CATEGORICAL":
            values = get_categorical_values(field)

            if values:
                candidates.append(
                    (
                        field_name,
                        values,
                    )
                )

            continue

        if distribution in {"DISCRETE_UNIFORM", "UNIFORM"}:
            parameters = generation.get(
                "parameters",
                {},
            )

            minimum = parameters.get("minimum")
            maximum = parameters.get("maximum")

            if (
                isinstance(minimum, int)
                and not isinstance(minimum, bool)
                and isinstance(maximum, int)
                and not isinstance(maximum, bool)
                and minimum <= maximum
            ):
                candidates.append(
                    (
                        field_name,
                        list(range(minimum, maximum + 1)),
                    )
                )

    return candidates

def _validate_chunk_inputs(
    entity: dict[str, Any],
    start_row: int,
    row_count: int,
) -> tuple[str, list[dict[str, Any]]]:
    """Validate chunk inputs and return the entity name and fields."""

    entity_name = entity.get("name")

    if not isinstance(entity_name, str) or not entity_name:
        raise ValueError("Entity must have a non-empty name.")

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

    return entity_name, fields


def _prepare_generation_state(
    entity_name: str,
    row_count: int,
    start_row: int,
    relationships: tuple[Any, ...],
    relationship_groups: tuple[Any, ...],
    context: Any | None,
    dependencies: tuple[Any, ...],
    rng: random.Random,
) -> tuple[
    list[dict[str, Any]],
    set[str],
]:
    """Prepare relationship assignments and authoritative fields."""

    assignments = [{} for _ in range(row_count)]
    protected_fields: set[str] = set()

    if relationships:
        if context is None:
            raise ValueError(
                "Generation context is required "
                "for relationship generation."
            )

        # RelationshipGroups are the authoritative representation for
        # logical composite relationships. Skip legacy field-level
        # relationship assignments that are fully covered by a group.
        #
        # Example:
        #   DELIVERY_ITEM.(DELIVERY_ID, ITEM_NO)
        #       -> DELIVERY_EVENT.(DELIVERY_ID, ITEM_NO)
        #
        # must be resolved once as a coupled parent identity rather
        # than as two independent relationship lookups.
        grouped_relationship_fields: set[
            tuple[str, str, str]
        ] = set()

        for group in relationship_groups:
            if group.child_entity != entity_name:
                continue

            parent_fields = tuple(group.parent_fields)
            child_fields = tuple(group.child_fields)

            if len(parent_fields) != len(child_fields):
                continue

            for parent_field, child_field in zip(
                parent_fields,
                child_fields,
            ):
                grouped_relationship_fields.add(
                    (
                        group.parent_entity,
                        parent_field,
                        child_field,
                    )
                )

        filtered_relationships = []

        for relationship in relationships:
            source_fields = tuple(
                relationship.source_fields
            )
            target_fields = tuple(
                relationship.target_fields
            )

            is_group_covered = (
                len(source_fields) == 1
                and len(target_fields) == 1
                and (
                    relationship.source_entity,
                    source_fields[0],
                    target_fields[0],
                )
                in grouped_relationship_fields
            )

            if not is_group_covered:
                filtered_relationships.append(
                    relationship
                )

        assignments = build_relationship_assignments_by_field(
            entity_name=entity_name,
            relationships=tuple(filtered_relationships),
            context=context,
            row_count=row_count,
            rng=rng,
            start_offset=start_row,
        )

        for assignment in assignments:
            protected_fields.update(assignment.keys())

    # Grouped relationship child fields are authoritative once
    # resolved. This is especially important for composite parent
    # identities, where the child fields must remain coupled.
    for group in relationship_groups:
        if group.child_entity != entity_name:
            continue

        protected_fields.update(
            group.child_fields
        )

    # Foreign-key source fields are authoritative once resolved.
    for dependency in dependencies:
        protected_fields.update(
            dependency.source_fields
        )

    return assignments, protected_fields


def _resolve_fk_assignments(
    entity_name: str,
    field_name: str,
    row: dict[str, Any],
    dependency: Any,
    context: Any | None,
    rng: random.Random,
    identity_fields: tuple[str, ...],
    existing_identities: set[tuple[Any, ...]],
    foreign_key_key_spaces: dict[
        tuple[str, tuple[str, ...]],
        list[tuple[Any, ...]],
    ],
) -> None:
    """Resolve and apply one foreign-key dependency to a row."""

    if context is None:
        raise ValueError(
            "Generation context is required "
            f"for foreign-key field "
            f"{entity_name}.{field_name}."
        )

    fk_values = resolve_foreign_key_value(
        dependency=dependency,
        context=context,
        rng=rng,
        existing_values=row,
        used_child_identities=existing_identities,
        child_identity_fields=identity_fields,
        foreign_key_key_spaces=foreign_key_key_spaces,
    )

    for source_field, value in fk_values.items():
        if source_field in row:
            # Relationship-managed values are authoritative.
            if row[source_field] != value:
                raise ValueError(
                    f"Foreign-key conflict for "
                    f"{entity_name}.{source_field}: "
                    f"relationship value {row[source_field]!r} "
                    f"does not match FK value {value!r}."
                )
            continue

        row[source_field] = value


def _generate_row(
    entity_name: str,
    entity: dict[str, Any],
    fields: list[dict[str, Any]],
    row_number: int,
    relationship_assignment: dict[str, Any],
    dependencies: tuple[Any, ...],
    context: Any | None,
    relationship_groups: tuple[Any, ...],
    relationship_key_spaces: dict[
        tuple[str, tuple[str, ...]],
        list[tuple[Any, ...]],
    ],
    composite_fk_key_spaces: dict[
        tuple[str, tuple[str, ...]],
        list[tuple[Any, ...]],
    ],
    identity_key_spaces: dict[
        tuple[str, tuple[str, ...]],
        list[tuple[Any, ...]],
    ],
    foreign_key_key_spaces: dict[
        tuple[str, tuple[str, ...]],
        list[tuple[Any, ...]],
    ],
    rng: random.Random,
    semantic_values_by_field: dict[str, list[str]],
    identity_fields: tuple[str, ...],
    existing_identities: set[tuple[Any, ...]],
    protected_fields: set[str],
    constraints: tuple[Any, ...],
) -> dict[str, Any]:
    """Generate one row before identity uniqueness resolution."""

    row = relationship_assignment.copy()

    # Resolve grouped relationships as complete parent-key units.
    # This preserves composite parent identity semantics before
    # individual FK and field generation takes place.
    relationship_group_assignment = (
        _resolve_relationship_group_assignments(
            row=row,
            entity_name=entity_name,
            relationship_groups=relationship_groups,
            context=context,
            rng=rng,
            relationship_key_spaces=relationship_key_spaces,
        )
    )

    row.update(relationship_group_assignment)

    # Resolve multi-field foreign keys as complete parent-key units
    # before normal field generation. This prevents independently
    # assigned relationship fields from creating invalid composite
    # foreign-key combinations.
    composite_fk_assignment = (
        _resolve_composite_foreign_key_assignments(
            row=row,
            dependencies=dependencies,
            identity_fields=identity_fields,
            context=context,
            rng=rng,
            composite_fk_key_spaces=composite_fk_key_spaces,
        )
    )

    row.update(composite_fk_assignment)

    composite_identity_assignment = (
        _resolve_composite_identity_fk_assignments(
            row=row,
            dependencies=dependencies,
            identity_fields=identity_fields,
            context=context,
            existing_identities=existing_identities,
            rng=rng,
        )
    )

    row.update(composite_identity_assignment)

    relationship_identity_assignment = (
        _resolve_relationship_identity_space_assignment(
            row=row,
            fields=fields,
            identity_fields=identity_fields,
            dependencies=dependencies,
            context=context,
            existing_identities=existing_identities,
            rng=rng,
            identity_key_spaces=identity_key_spaces,
        )
    )

    row.update(relationship_identity_assignment)

    for field in fields:
        field_name = field.get("name")

        if not isinstance(field_name, str) or not field_name:
            raise ValueError(
                f"{entity_name}: field must "
                "have a non-empty name."
            )

        # Relationship-managed fields are authoritative.
        if field_name in row:
            continue

        dependency = find_field_dependency(
            field_name,
            dependencies,
        )

        if dependency is not None:
            _resolve_fk_assignments(
                entity_name=entity_name,
                field_name=field_name,
                row=row,
                dependency=dependency,
                context=context,
                rng=rng,
                identity_fields=identity_fields,
                existing_identities=existing_identities,
                foreign_key_key_spaces=foreign_key_key_spaces,
            )
            continue

        row[field_name] = generate_field_value(
            entity_name=entity_name,
            field=field,
            row_number=row_number,
            rng=rng,
            semantic_values=semantic_values_by_field.get(
                field_name
            ),
            constraints=constraints,
        )

    row, _ = find_identity_candidate(
        row=row,
        fields=fields,
        identity_fields=identity_fields,
        existing_identities=existing_identities,
        rng=rng,
        protected_fields=protected_fields,
    )

    return row


def generate_entity_chunk(
    entity: dict[str, Any],
    start_row: int,
    row_count: int,
    seed: int,
    semantic_values_by_field: dict[str, list[str]] | None = None,
    dependencies: tuple[Any, ...] = (),
    context: Any | None = None,
    relationships: tuple[Any, ...] = (),
    relationship_groups: tuple[Any, ...] = (),
    existing_identities: set[tuple[Any, ...]] | None = None,
    constraints: tuple[Any, ...] = (),
) -> list[dict[str, Any]]:
    """
    Generate one bounded chunk of rows for one entity.

    The function is deterministic for the same entity definition,
    row range, and seed.

    Relationship and dependency-managed fields take precedence
    over primitive generation.

    Identity uniqueness is checked during generation. Identity fields
    managed by relationships are authoritative and are not modified
    by identity candidate resolution.
    """

    entity_name, fields = _validate_chunk_inputs(
        entity=entity,
        start_row=start_row,
        row_count=row_count,
    )

    identity_fields = get_identity_fields(entity)

    if existing_identities is None:
        existing_identities = set()

    if semantic_values_by_field is None:
        semantic_values_by_field = {}

    rng = random.Random(seed + start_row)

    (
        relationship_assignments,
        protected_fields,
    ) = _prepare_generation_state(
        entity_name=entity_name,
        row_count=row_count,
        start_row=start_row,
        relationships=relationships,
        relationship_groups=relationship_groups,
        context=context,
        dependencies=dependencies,
        rng=rng,
    )

    relationship_key_spaces = _prepare_relationship_key_spaces(
        entity_name=entity_name,
        relationship_groups=relationship_groups,
        context=context,
    )

    composite_fk_key_spaces = _prepare_composite_fk_key_spaces(
        dependencies=dependencies,
        context=context,
    )

    identity_key_spaces = _prepare_identity_key_spaces(
        identity_fields=identity_fields,
        dependencies=dependencies,
        context=context,
    )

    foreign_key_key_spaces = _prepare_foreign_key_key_spaces(
        dependencies=dependencies,
        context=context,
    )

    rows: list[dict[str, Any]] = []

    for offset in range(row_count):
        row_number = start_row + offset

        row = _generate_row(
            entity_name=entity_name,
            entity=entity,
            fields=fields,
            row_number=row_number,
            relationship_assignment=relationship_assignments[offset],
            dependencies=dependencies,
            context=context,
            relationship_groups=relationship_groups,
            relationship_key_spaces=relationship_key_spaces,
            composite_fk_key_spaces=composite_fk_key_spaces,
            identity_key_spaces=identity_key_spaces,
            foreign_key_key_spaces=foreign_key_key_spaces,
            rng=rng,
            semantic_values_by_field=semantic_values_by_field,
            identity_fields=identity_fields,
            existing_identities=existing_identities,
            protected_fields=protected_fields,
            constraints=constraints,
        )

        identity = build_identity(
            row,
            identity_fields,
        )

        existing_identities.add(identity)
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
        raise ValueError("Entity must have a non-empty name.")

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
