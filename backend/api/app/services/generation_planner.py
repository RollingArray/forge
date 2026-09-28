"""
File: generation_planner.py
Purpose: Deterministic generation planning for FORGE.
"""

from __future__ import annotations

from dataclasses import dataclass


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
    source = relationship.get("source")
    target = relationship.get("target")

    if not isinstance(source, str) or not source:
        raise GenerationPlanningError(
            "Each relationship must have a source."
        )

    if not isinstance(target, str) or not target:
        raise GenerationPlanningError(
            "Each relationship must have a target."
        )

    if "." not in source or "." not in target:
        raise GenerationPlanningError(
            "Relationship source and target must use "
            "'ENTITY.FIELD' notation."
        )

    source_entity, source_field = source.split(".", 1)
    target_entity, target_field = target.split(".", 1)

    _validate_entity_reference(
        source_entity,
        entity_names,
        "Relationship source",
    )
    _validate_entity_reference(
        target_entity,
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
        source_entity=source_entity,
        source_fields=(source_field,),
        target_entity=target_entity,
        target_fields=(target_field,),
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

    return ConstraintDefinition(
        entity=entity,
        field=field,
        operator=operator,
        value=constraint["value"],
    )


def _build_constraints(
    specification: dict,
    entity_names: set[str],
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

    def build(
        self,
        specification: dict,
    ) -> GenerationPlan:
        """Build the complete generation plan without generating data."""

        entities = _require_entities(specification)
        entity_names = _get_entity_names(entities)

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

        constraints = _build_constraints(
            specification,
            entity_names,
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
