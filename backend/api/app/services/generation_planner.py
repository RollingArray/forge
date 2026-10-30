"""
File: generation_planner.py
Purpose: Deterministic generation planning for FORGE.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from decimal import Decimal

from app.services.relationship_endpoint import parse_relationship_endpoint


class GenerationPlanningError(ValueError):
    """Raised when a FORGE generation plan cannot be built."""


@dataclass(frozen=True)
class ForeignKeyDependency:
    """Dependency created by a foreign-key relationship."""

    foreign_key_name: str
    parent_entity: str
    source_fields: tuple[str, ...]
    target_fields: tuple[str, ...]


@dataclass(frozen=True)
class RelationshipDependency:
    """Relationship semantics between two entities."""

    source_entity: str
    source_fields: tuple[str, ...]
    target_entity: str
    target_fields: tuple[str, ...]
    relationship_type: str
    source_participation: str
    target_participation: str


@dataclass(frozen=True)
class RelationshipGroup:
    """Canonical grouped relationship semantics."""

    parent_entity: str
    child_entity: str
    parent_fields: tuple[str, ...]
    child_fields: tuple[str, ...]
    relationship_type: str
    parent_participation: str
    child_participation: str


@dataclass(frozen=True)
class ConstraintDefinition:
    """Constraint that must be satisfied during generation."""

    entity: str
    field: str
    operator: str
    value: object


@dataclass(frozen=True)
class GenerationEntityPlan:
    """Generation requirements and FK dependencies for one entity."""

    entity_name: str
    target_rows: int
    dependencies: tuple[ForeignKeyDependency, ...] = ()

    @property
    def is_root(self) -> bool:
        return not self.dependencies


@dataclass(frozen=True)
class GenerationPlan:
    """Generation requirements and model semantics for a specification."""

    entities: tuple[GenerationEntityPlan, ...]
    relationships: tuple[RelationshipDependency, ...] = ()
    relationship_groups: tuple[RelationshipGroup, ...] = ()
    constraints: tuple[ConstraintDefinition, ...] = ()

    @property
    def total_target_rows(self) -> int:
        return sum(entity.target_rows for entity in self.entities)

    @property
    def generation_order(self) -> tuple[str, ...]:
        """Return entities in dependency-safe generation order."""

        plans = {entity.entity_name: entity for entity in self.entities}
        remaining = set(plans)
        resolved: set[str] = set()
        order: list[str] = []

        while remaining:
            ready = [
                entity_name
                for entity_name in remaining
                if all(
                    dependency.parent_entity in resolved
                    for dependency in plans[entity_name].dependencies
                )
            ]

            if not ready:
                unresolved = sorted(remaining)
                raise GenerationPlanningError(
                    "Unable to resolve FORGE generation dependencies. "
                    f"Possible dependency cycle involving: {unresolved}"
                )

            for entity_plan in plans.values():
                if entity_plan.entity_name not in ready:
                    continue

                order.append(entity_plan.entity_name)
                resolved.add(entity_plan.entity_name)
                remaining.remove(entity_plan.entity_name)

        return tuple(order)


def _validate_generation_configuration(
    specification: dict,
    entities: list,
) -> None:
    """Reject unsupported or malformed field-generation configurations."""

    foreign_key_fields: set[tuple[str, str]] = set()
    foreign_keys = specification.get("foreign_keys", [])

    if foreign_keys is None:
        foreign_keys = []

    if isinstance(foreign_keys, list):
        for foreign_key in foreign_keys:
            if not isinstance(foreign_key, dict):
                continue
            source = foreign_key.get("source")
            if not isinstance(source, dict):
                continue
            entity_name = source.get("entity")
            fields = source.get("fields")
            if isinstance(entity_name, str) and isinstance(fields, list):
                foreign_key_fields.update(
                    (entity_name, field_name)
                    for field_name in fields
                    if isinstance(field_name, str)
                )

    def fail(entity_name: str, field_name: str, reason: str) -> None:
        raise GenerationPlanningError(
            f"Invalid generation configuration for "
            f"{entity_name}.{field_name}: {reason}"
        )

    def finite_number(value: object) -> Decimal | None:
        if isinstance(value, bool) or value is None:
            return None
        try:
            result = Decimal(str(value))
        except (ArithmeticError, TypeError, ValueError):
            return None
        return result if result.is_finite() else None

    for entity in entities:
        if not isinstance(entity, dict):
            continue
        entity_name = entity.get("name", "<unknown>")
        fields = entity.get("fields", [])
        if not isinstance(fields, list):
            fail(entity_name, "<fields>", "fields must be a list.")

        field_names: list[str] = []
        for field in fields:
            if not isinstance(field, dict):
                fail(entity_name, "<unknown>", "each field must be an object.")
            name = field.get("name")
            if not isinstance(name, str) or not name.strip():
                fail(entity_name, "<unknown>", "field name must be non-empty.")
            field_names.append(name)

        if len(field_names) != len(set(field_names)):
            fail(entity_name, "<fields>", "field names must be unique.")

        entity_identity = entity.get("identity")
        if entity_identity is not None:
            if not isinstance(entity_identity, dict):
                fail(entity_name, "<identity>", "identity must be an object.")

            if "fields" in entity_identity:
                identity_fields = entity_identity["fields"]
                if (
                    not isinstance(identity_fields, list)
                    or not identity_fields
                ):
                    fail(
                        entity_name, "<identity>",
                        "identity.fields must be a non-empty list.",
                    )

                if any(
                    not isinstance(name, str) or not name.strip()
                    for name in identity_fields
                ):
                    fail(
                        entity_name, "<identity>",
                        "identity.fields must contain non-empty field names.",
                    )

                if len(identity_fields) != len(set(identity_fields)):
                    fail(
                        entity_name, "<identity>",
                        "identity.fields must contain unique field names.",
                    )

                unknown_fields = [
                    name for name in identity_fields
                    if name not in field_names
                ]
                if unknown_fields:
                    fail(
                        entity_name, "<identity>",
                        "identity.fields references unknown field(s): "
                        + ", ".join(unknown_fields),
                    )

        for field in fields:
            if not isinstance(field, dict):
                fail(entity_name, "<unknown>", "each field must be an object.")

            field_name = field.get("name")
            if not isinstance(field_name, str) or not field_name.strip():
                fail(entity_name, "<unknown>", "field name must be non-empty.")

            field_type = field.get("type")
            if field_type not in {
                "IDENTIFIER", "STRING", "INTEGER",
                "DECIMAL", "BOOLEAN", "CATEGORICAL",
            }:
                fail(entity_name, field_name, f"unsupported field type {field_type!r}.")

            identity = field.get("identity")
            generation = field.get("generation")

            if identity is not None and not isinstance(identity, dict):
                fail(entity_name, field_name, "identity must be an object.")
            if generation is not None and not isinstance(generation, dict):
                fail(entity_name, field_name, "generation must be an object.")

            identity = identity or {}
            generation = generation or {}

            parameters = generation.get("parameters")
            if parameters is not None and not isinstance(parameters, dict):
                fail(entity_name, field_name, "parameters must be an object.")
            parameters = parameters or {}

            # FK assignment supplies values before scalar generation, but
            # structural validation above still applies to these fields.
            if (entity_name, field_name) in foreign_key_fields:
                if field_type == "IDENTIFIER" and (
                    identity.get("strategy") != "SEQUENTIAL_ID"
                ):
                    fail(
                        entity_name, field_name,
                        "IDENTIFIER requires SEQUENTIAL_ID.",
                    )
                continue

            generator = generation.get("generator")
            distribution = generation.get("distribution")

            if field_type == "IDENTIFIER":
                if identity.get("strategy") != "SEQUENTIAL_ID":
                    fail(
                        entity_name, field_name,
                        "IDENTIFIER requires SEQUENTIAL_ID.",
                    )
                continue

            if field_type == "BOOLEAN":
                if generation.get("strategy") != "RANDOM":
                    fail(entity_name, field_name, "BOOLEAN requires RANDOM.")
                continue

            if field_type == "STRING":
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
                        fail(
                            entity_name, field_name,
                            "RANDOM_STRING requires positive ordered integer "
                            "minimum_length and maximum_length.",
                        )
                    if charset not in {"ALPHA", "DIGITS", "ALPHANUMERIC"}:
                        fail(
                            entity_name, field_name,
                            "RANDOM_STRING requires a supported character_set.",
                        )
                elif generator == "PATTERN":
                    pattern = parameters.get("pattern")
                    if not isinstance(pattern, str) or not pattern.strip():
                        fail(
                            entity_name, field_name,
                            "PATTERN requires a non-empty pattern.",
                        )
                elif generator == "SEMANTIC":
                    description = parameters.get("description")
                    mode = parameters.get("mode")
                    if not isinstance(description, str) or not description.strip():
                        fail(
                            entity_name, field_name,
                            "SEMANTIC requires a non-empty description.",
                        )
                    if mode not in {"UNIQUE", "VOCABULARY"}:
                        fail(
                            entity_name, field_name,
                            "SEMANTIC mode must be UNIQUE or VOCABULARY.",
                        )
                else:
                    fail(
                        entity_name, field_name,
                        "STRING requires RANDOM_STRING, PATTERN, or SEMANTIC.",
                    )
                continue

            if field_type == "CATEGORICAL":
                values = parameters.get("values")
                if (
                    generation.get("strategy") != "RANDOM"
                    or distribution != "CATEGORICAL"
                    or not isinstance(values, list)
                    or not values
                ):
                    fail(
                        entity_name, field_name,
                        "CATEGORICAL requires RANDOM, CATEGORICAL distribution, "
                        "and a non-empty values list.",
                    )
                continue

            if field_type in {"INTEGER", "DECIMAL"}:
                allowed = (
                    {"UNIFORM", "DISCRETE_UNIFORM"}
                    if field_type == "INTEGER"
                    else {"UNIFORM"}
                )
                if (
                    generation.get("strategy") != "RANDOM"
                    or distribution not in allowed
                ):
                    fail(
                        entity_name, field_name,
                        f"{field_type} supports only RANDOM with distributions "
                        f"{', '.join(sorted(allowed))}.",
                    )

                minimum = finite_number(parameters.get("minimum"))
                maximum = finite_number(parameters.get("maximum"))
                if minimum is None or maximum is None:
                    fail(
                        entity_name, field_name,
                        "minimum and maximum must be finite numeric values.",
                    )
                if minimum > maximum:
                    fail(
                        entity_name, field_name,
                        "minimum cannot exceed maximum.",
                    )
                if field_type == "INTEGER" and (
                    minimum != minimum.to_integral_value()
                    or maximum != maximum.to_integral_value()
                ):
                    fail(
                        entity_name, field_name,
                        "INTEGER bounds must be whole numbers.",
                    )
                continue

            fail(entity_name, field_name, f"unsupported field type {field_type!r}.")


def _get_entity_names(entities: list) -> set[str]:
    return {
        entity.get("name")
        for entity in entities
        if isinstance(entity, dict)
        and isinstance(entity.get("name"), str)
    }


def _require_entities(specification: dict) -> list:
    entities = specification.get("entities")

    if not isinstance(entities, list):
        raise GenerationPlanningError(
            "FORGE specification must contain an entities list."
        )

    return entities


def _validate_entity_reference(
    entity_name: object,
    entity_names: set[str],
    context: str,
) -> None:
    if entity_name not in entity_names:
        raise GenerationPlanningError(
            f"{context}: entity '{entity_name}' does not exist."
        )


def _validate_field_lists(
    name: str,
    source_fields: object,
    target_fields: object,
) -> None:
    if not isinstance(source_fields, list) or not source_fields:
        raise GenerationPlanningError(
            f"{name}: source.fields must be a non-empty list."
        )

    if not isinstance(target_fields, list) or not target_fields:
        raise GenerationPlanningError(
            f"{name}: target.fields must be a non-empty list."
        )

    if len(source_fields) != len(target_fields):
        raise GenerationPlanningError(
            f"{name}: source and target field counts must match."
        )


def _parse_foreign_key(
    foreign_key: dict,
    entity_names: set[str],
) -> ForeignKeyDependency:
    name = foreign_key.get("name")
    source = foreign_key.get("source")
    target = foreign_key.get("target")

    if not isinstance(name, str) or not name:
        raise GenerationPlanningError(
            "Each FORGE foreign key must have a non-empty name."
        )

    if not isinstance(source, dict) or not isinstance(target, dict):
        raise GenerationPlanningError(
            f"{name}: source and target must be objects."
        )

    source_entity = source.get("entity")
    target_entity = target.get("entity")
    source_fields = source.get("fields")
    target_fields = target.get("fields")

    _validate_entity_reference(
        source_entity,
        entity_names,
        f"{name}: source",
    )
    _validate_entity_reference(
        target_entity,
        entity_names,
        f"{name}: target",
    )
    _validate_field_lists(
        name,
        source_fields,
        target_fields,
    )

    return ForeignKeyDependency(
        foreign_key_name=name,
        parent_entity=target_entity,
        source_fields=tuple(source_fields),
        target_fields=tuple(target_fields),
    )


def _build_foreign_key_dependencies(
    specification: dict,
    entity_names: set[str],
) -> dict[str, tuple[ForeignKeyDependency, ...]]:
    foreign_keys = specification.get("foreign_keys", [])

    if foreign_keys is None:
        foreign_keys = []

    if not isinstance(foreign_keys, list):
        raise GenerationPlanningError(
            "FORGE specification foreign_keys must be a list."
        )

    dependencies: dict[str, list[ForeignKeyDependency]] = {
        entity_name: [] for entity_name in entity_names
    }

    for foreign_key in foreign_keys:
        if not isinstance(foreign_key, dict):
            raise GenerationPlanningError(
                "Each FORGE foreign key must be an object."
            )

        dependency = _parse_foreign_key(
            foreign_key,
            entity_names,
        )

        source_entity = foreign_key["source"]["entity"]
        dependencies[source_entity].append(dependency)

    return {
        entity_name: tuple(entity_dependencies)
        for entity_name, entity_dependencies in dependencies.items()
    }


def _parse_relationship(
    relationship: dict,
    entity_names: set[str],
) -> RelationshipDependency:
    """Parse legacy or composite relationship endpoints."""

    try:
        source = parse_relationship_endpoint(
            relationship.get("source"),
            "source",
        )
        target = parse_relationship_endpoint(
            relationship.get("target"),
            "target",
        )
    except ValueError as exc:
        raise GenerationPlanningError(str(exc)) from exc

    _validate_entity_reference(
        source.entity,
        entity_names,
        "Relationship source",
    )
    _validate_entity_reference(
        target.entity,
        entity_names,
        "Relationship target",
    )

    relationship_type = relationship.get("type")

    if not isinstance(relationship_type, str) or not relationship_type:
        raise GenerationPlanningError(
            "Each relationship must have a type."
        )

    source_participation = relationship.get(
        "source_participation",
        "MANDATORY",
    )
    target_participation = relationship.get(
        "target_participation",
        "MANDATORY",
    )

    return RelationshipDependency(
        source_entity=source.entity,
        source_fields=source.fields,
        target_entity=target.entity,
        target_fields=target.fields,
        relationship_type=relationship_type,
        source_participation=source_participation,
        target_participation=target_participation,
    )


def _build_relationship_dependencies(
    specification: dict,
    entity_names: set[str],
) -> tuple[RelationshipDependency, ...]:
    relationships = specification.get("relationships", [])

    if relationships is None:
        relationships = []

    if not isinstance(relationships, list):
        raise GenerationPlanningError(
            "FORGE specification relationships must be a list."
        )

    result: list[RelationshipDependency] = []

    for relationship in relationships:
        if not isinstance(relationship, dict):
            raise GenerationPlanningError(
                "Each FORGE relationship must be an object."
            )

        result.append(
            _parse_relationship(
                relationship,
                entity_names,
            )
        )

    return tuple(result)


def _build_relationship_groups(
    relationships: tuple[RelationshipDependency, ...],
) -> tuple[RelationshipGroup, ...]:
    groups: dict[
        tuple[str, str, str, str, str],
        list[RelationshipDependency],
    ] = {}

    for relationship in relationships:
        key = (
            relationship.source_entity,
            relationship.target_entity,
            relationship.relationship_type,
            relationship.source_participation,
            relationship.target_participation,
        )
        groups.setdefault(key, []).append(relationship)

    result: list[RelationshipGroup] = []

    for grouped_relationships in groups.values():
        first = grouped_relationships[0]

        parent_fields = tuple(
            field
            for relationship in grouped_relationships
            for field in relationship.source_fields
        )
        child_fields = tuple(
            field
            for relationship in grouped_relationships
            for field in relationship.target_fields
        )

        if len(parent_fields) != len(set(parent_fields)):
            raise GenerationPlanningError(
                "Relationship group contains duplicate parent fields: "
                f"{first.source_entity} -> {first.target_entity}."
            )

        if len(child_fields) != len(set(child_fields)):
            raise GenerationPlanningError(
                "Relationship group contains duplicate child fields: "
                f"{first.source_entity} -> {first.target_entity}."
            )

        result.append(
            RelationshipGroup(
                parent_entity=first.source_entity,
                child_entity=first.target_entity,
                parent_fields=parent_fields,
                child_fields=child_fields,
                relationship_type=first.relationship_type,
                parent_participation=first.source_participation,
                child_participation=first.target_participation,
            )
        )

    return tuple(result)


def _parse_constraint(
    constraint: dict,
    entity_names: set[str],
    field_types_by_entity: dict[str, dict[str, str]],
) -> ConstraintDefinition:
    entity = constraint.get("entity")
    field = constraint.get("field")
    operator = constraint.get("operator")

    if not isinstance(entity, str) or not entity:
        raise GenerationPlanningError(
            "Each constraint must have a non-empty entity."
        )

    _validate_entity_reference(
        entity,
        entity_names,
        "Constraint",
    )

    if not isinstance(field, str) or not field:
        raise GenerationPlanningError(
            f"{entity}: constraint field must be non-empty."
        )

    if not isinstance(operator, str) or not operator:
        raise GenerationPlanningError(
            f"{entity}.{field}: constraint operator must be non-empty."
        )

    if "value" not in constraint:
        raise GenerationPlanningError(
            f"{entity}.{field}: constraint must contain a value."
        )

    field_type = field_types_by_entity.get(entity, {}).get(field)
    supported_operators = {
        "INTEGER": {">", ">=", "<", "<="},
        "DECIMAL": {">", ">=", "<", "<="},
        "STRING": {"==", "!="},
        "CATEGORICAL": {"==", "!="},
    }
    if field_type is None:
        raise GenerationPlanningError(
            f"{entity}.{field}: constraint field was not found."
        )
    if operator not in supported_operators.get(field_type, set()):
        raise GenerationPlanningError(
            f"{entity}.{field}: operator {operator!r} is not supported "
            f"for {field_type} fields."
        )

    value = constraint["value"]
    if field_type in {"INTEGER", "DECIMAL"}:
        try:
            if isinstance(value, bool):
                raise ValueError("Boolean values are not numeric.")
            number = float(value)
            if not math.isfinite(number):
                raise ValueError("Value must be finite.")
            if field_type == "INTEGER" and not number.is_integer():
                raise ValueError("Value must be an integer.")
        except (TypeError, ValueError, OverflowError) as exc:
            raise GenerationPlanningError(
                f"{entity}.{field}: comparison value must be a valid "
                f"{field_type.lower()}."
            ) from exc

    return ConstraintDefinition(
        entity=entity,
        field=field,
        operator=operator,
        value=value,
    )


def _build_constraints(
    specification: dict,
    entity_names: set[str],
    field_types_by_entity: dict[str, dict[str, str]],
) -> tuple[ConstraintDefinition, ...]:
    constraints = specification.get("constraints", [])

    if constraints is None:
        constraints = []

    if not isinstance(constraints, list):
        raise GenerationPlanningError(
            "FORGE specification constraints must be a list."
        )

    result: list[ConstraintDefinition] = []

    for constraint in constraints:
        if not isinstance(constraint, dict):
            raise GenerationPlanningError(
                "Each FORGE constraint must be an object."
            )

        result.append(
            _parse_constraint(
                constraint,
                entity_names,
                field_types_by_entity,
            )
        )

    return tuple(result)


def _get_population_count(
    entity_name: str,
    entity: dict,
) -> int:
    population = entity.get("population")

    if not isinstance(population, dict):
        raise GenerationPlanningError(
            f"{entity_name}: population must be an object."
        )

    target_rows = population.get("count")

    if (
        not isinstance(target_rows, int)
        or isinstance(target_rows, bool)
        or target_rows < 0
    ):
        raise GenerationPlanningError(
            f"{entity_name}: population.count must be "
            "a non-negative integer."
        )

    return target_rows


def _build_entity_plans(
    entities: list,
    dependencies: dict[str, tuple[ForeignKeyDependency, ...]],
) -> tuple[GenerationEntityPlan, ...]:
    plans: list[GenerationEntityPlan] = []

    for entity in entities:
        if not isinstance(entity, dict):
            raise GenerationPlanningError(
                "Each FORGE entity must be an object."
            )

        entity_name = entity.get("name")

        if not isinstance(entity_name, str) or not entity_name:
            raise GenerationPlanningError(
                "Each FORGE entity must have a non-empty name."
            )

        plans.append(
            GenerationEntityPlan(
                entity_name=entity_name,
                target_rows=_get_population_count(
                    entity_name,
                    entity,
                ),
                dependencies=dependencies.get(
                    entity_name,
                    (),
                ),
            )
        )

    return tuple(plans)


class GenerationPlanner:
    """Build a deterministic, semantics-preserving generation plan."""

    def validate_generation_configuration(
        self,
        specification: dict,
    ) -> None:
        """Validate field-generation settings without requiring populations."""

        entities = _require_entities(specification)
        _validate_generation_configuration(specification, entities)

    def build(
        self,
        specification: dict,
    ) -> GenerationPlan:
        """Build the complete generation plan without generating data."""

        entities = _require_entities(specification)
        entity_names = _get_entity_names(entities)

        _validate_generation_configuration(specification, entities)

        dependencies = _build_foreign_key_dependencies(
            specification,
            entity_names,
        )

        relationships = _build_relationship_dependencies(
            specification,
            entity_names,
        )

        relationship_groups = _build_relationship_groups(
            relationships,
        )

        field_types_by_entity = {
            entity["name"]: {
                field["name"]: str(field.get("type", "")).strip().upper()
                for field in entity.get("fields", [])
                if isinstance(field, dict)
                and isinstance(field.get("name"), str)
            }
            for entity in entities
            if isinstance(entity, dict)
            and isinstance(entity.get("name"), str)
        }

        constraints = _build_constraints(
            specification,
            entity_names,
            field_types_by_entity,
        )

        entity_plans = _build_entity_plans(
            entities,
            dependencies,
        )

        plan = GenerationPlan(
            entities=entity_plans,
            relationships=relationships,
            relationship_groups=relationship_groups,
            constraints=constraints,
        )

        # Resolve dependencies during planning so cycles fail
        # before generation begins.
        plan.generation_order

        return plan
