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
) -> dict[str, Any]:
    """Select a compatible existing parent key for a foreign-key dependency.

    Existing source-field values are treated as authoritative constraints.
    This is important when a relationship has already assigned part of
    a composite foreign key.

    When the foreign key covers the complete child identity, parent keys
    are filtered using the declared child identity field order. This
    prevents field-order differences between the FK mapping and the
    child identity definition from causing duplicate identities.
    """

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
    # must consume a distinct compatible parent identity. The child
    # identity is built using the identity declaration's field order,
    # not the FK source-field order.
    #
    # This matters for composite identities such as VBEP:
    #
    #   FK source fields:       (VBELN, POSNR)
    #   child identity fields:  (POSNR, VBELN)
    #
    # The corresponding identity for parent key (1, 91) is therefore
    # (91, 1), not (1, 91).
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


def _resolve_composite_foreign_key_assignments(
    row: dict[str, Any],
    dependencies: tuple[Any, ...],
    identity_fields: tuple[str, ...],
    context: Any | None,
    rng: random.Random,
) -> dict[str, Any]:
    """Resolve multi-field foreign keys as complete parent-key units.

    This handles composite foreign keys whose source fields do not
    necessarily cover the complete child identity.

    Relationship assignments may have populated the individual source
    fields independently. Those values are intentionally replaced by
    one complete parent key so the composite foreign key remains
    referentially valid.

    The existing complete composite-identity FK path is left untouched.
    """

    if context is None:
        return {}

    assignments: dict[str, Any] = {}

    for dependency in dependencies:
        source_fields = tuple(
            dependency.source_fields
        )

        # Only handle genuinely composite foreign keys.
        if len(source_fields) < 2:
            continue

        # Preserve the existing complete composite-identity path.
        if (
            set(source_fields) == set(identity_fields)
            and len(source_fields) == len(identity_fields)
        ):
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

        selected_key = rng.choice(parent_keys)

        assignments.update(
            dict(
                zip(
                    source_fields,
                    selected_key,
                )
            )
        )

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

    This path is intentionally limited to the previously unsupported
    topology where multiple independent foreign keys collectively cover
    the complete child identity.

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
            set(dependency.source_fields)
            == identity_field_set
            and len(dependency.source_fields)
            == len(identity_fields)
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

    # Build compatible candidate values for each independent FK.
    candidate_values: list[
        tuple[Any, list[tuple[Any, ...]]]
    ] = []

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

        compatible_keys: list[tuple[Any, ...]] = []

        for parent_key in parent_keys:
            compatible = True

            for source_field, target_value in zip(
                dependency.source_fields,
                parent_key,
            ):
                # For this special composite-identity topology,
                # the independent FK allocator owns the identity
                # fields. Relationship assignments may already have
                # populated those fields, but they must not constrain
                # the Cartesian identity space.
                if (
                    source_field in row
                    and source_field not in identity_field_set
                ):
                    if row[source_field] != target_value:
                        compatible = False
                        break

            if compatible:
                compatible_keys.append(parent_key)

        if not compatible_keys:
            raise ValueError(
                f"No compatible parent key found for foreign-key "
                f"{dependency!r} given existing values "
                f"{row!r}."
            )

        candidate_values.append(
            (
                dependency,
                compatible_keys,
            )
        )

    # Build the Cartesian product of the independent FK choices.
    combinations: list[dict[str, Any]] = []

    for selected_keys in product(
        *[
            keys
            for _, keys in candidate_values
        ]
    ):
        assignment = row.copy()

        for (
            dependency,
            parent_key,
        ) in zip(
            (
                dependency
                for dependency, _ in candidate_values
            ),
            selected_keys,
        ):
            for source_field, value in zip(
                dependency.source_fields,
                parent_key,
            ):
                assignment[source_field] = value

        identity = build_identity(
            assignment,
            identity_fields,
        )

        if identity not in existing_identities:
            combinations.append(
                {
                    field: assignment[field]
                    for field in identity_fields
                }
            )

    if not combinations:
        identity_capacity = 1

        for _, keys in candidate_values:
            identity_capacity *= len(keys)

        raise ValueError(
            f"Unable to generate a unique identity for "
            f"{identity_fields}. The available composite FK "
            f"identity space is exhausted "
            f"(capacity={identity_capacity}, "
            f"existing={len(existing_identities)})."
        )

    return rng.choice(combinations)


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
    """Find identity fields with finite non-protected candidates."""

    if protected_fields is None:
        protected_fields = set()

    candidates: list[tuple[str, list[Any]]] = []

    for field in fields:

        field_name = field.get("name")

        if field_name not in identity_fields:
            continue

        if field_name in protected_fields:
            continue

        values = get_categorical_values(field)

        if values:
            candidates.append(
                (
                    field_name,
                    values,
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

        assignments = build_relationship_assignments_by_field(
            entity_name=entity_name,
            relationships=relationships,
            context=context,
            row_count=row_count,
            rng=rng,
            start_offset=start_row,
        )

        for assignment in assignments:
            protected_fields.update(assignment.keys())

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
    rng: random.Random,
    semantic_values_by_field: dict[str, list[str]],
    identity_fields: tuple[str, ...],
    existing_identities: set[tuple[Any, ...]],
    protected_fields: set[str],
    constraints: tuple[Any, ...],
) -> dict[str, Any]:
    """Generate one row before identity uniqueness resolution."""

    row = relationship_assignment.copy()

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
        context=context,
        dependencies=dependencies,
        rng=rng,
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
