"""
FORGE Generation Core
Generation planning.

This module converts a validated FORGE specification into
a UI-independent, dependency-aware generation plan.

No data is generated here.
"""

from __future__ import annotations

from dataclasses import dataclass

from .job import EntityGenerationProgress, GenerationJob
from .specification import SpecificationError


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
class ConstraintDefinition:
    """Constraint that must be satisfied during generation."""

    entity: str
    field: str
    operator: str
    value: object


@dataclass(frozen=True)
class EntityGenerationPlan:
    """Generation requirements and FK dependencies for one entity."""

    entity_name: str
    target_rows: int
    dependencies: tuple[ForeignKeyDependency, ...] = ()

    @property
    def is_root(self) -> bool:
        """Return True when the entity has no generation dependencies."""

        return not self.dependencies


@dataclass(frozen=True)
class GenerationPlan:
    """Generation requirements and model semantics for a specification."""

    entities: tuple[EntityGenerationPlan, ...]
    relationships: tuple[RelationshipDependency, ...] = ()
    constraints: tuple[ConstraintDefinition, ...] = ()

    @property
    def total_target_rows(self) -> int:
        """Return the total number of rows requested."""

        return sum(entity.target_rows for entity in self.entities)

    @property
    def generation_order(self) -> tuple[str, ...]:
        """
        Return entities in dependency-safe generation order.

        Parent entities always appear before entities that depend
        on them through a foreign key.
        """

        plans = {entity.entity_name: entity for entity in self.entities}

        remaining = set(plans)
        resolved: set[str] = set()
        order: list[str] = []

        while remaining:
            ready = self._find_ready_entities(
                remaining,
                resolved,
                plans,
            )

            if not ready:
                unresolved = sorted(remaining)
                raise SpecificationError(
                    "Unable to resolve FORGE generation dependencies. "
                    f"Possible dependency cycle involving: {unresolved}"
                )

            self._append_ready_entities(
                ready,
                plans,
                resolved,
                remaining,
                order,
            )

        return tuple(order)

    @staticmethod
    def _find_ready_entities(
        remaining: set[str],
        resolved: set[str],
        plans: dict[str, EntityGenerationPlan],
    ) -> list[str]:
        """Return entities whose FK parents have already been resolved."""

        return [
            entity_name
            for entity_name in remaining
            if all(
                dependency.parent_entity in resolved
                for dependency in plans[entity_name].dependencies
            )
        ]

    @staticmethod
    def _append_ready_entities(
        ready: list[str],
        plans: dict[str, EntityGenerationPlan],
        resolved: set[str],
        remaining: set[str],
        order: list[str],
    ) -> None:
        """Append ready entities while preserving specification order."""

        for entity_plan in plans.values():
            if entity_plan.entity_name not in ready:
                continue

            order.append(entity_plan.entity_name)
            resolved.add(entity_plan.entity_name)
            remaining.remove(entity_plan.entity_name)


def _get_entity_names(
    entities: list,
) -> set[str]:
    """Return entity names declared in the specification."""

    return {
        entity.get("name")
        for entity in entities
        if isinstance(entity, dict) and isinstance(entity.get("name"), str)
    }


def _require_entities(
    specification: dict,
) -> list:
    """Return the specification entities or raise a planning error."""

    entities = specification.get("entities")

    if not isinstance(entities, list):
        raise SpecificationError("FORGE specification must contain an entities list.")

    return entities


def _validate_entity_reference(
    entity_name: str,
    entity_names: set[str],
    context: str,
) -> None:
    """Validate that an entity reference exists."""

    if entity_name not in entity_names:
        raise SpecificationError(f"{context}: entity '{entity_name}' does not exist.")


def _validate_field_lists(
    name: str,
    source_fields: object,
    target_fields: object,
) -> None:
    """Validate paired FK field lists."""

    if not isinstance(source_fields, list) or not source_fields:
        raise SpecificationError(f"{name}: source.fields must be a non-empty list.")

    if not isinstance(target_fields, list) or not target_fields:
        raise SpecificationError(f"{name}: target.fields must be a non-empty list.")

    if len(source_fields) != len(target_fields):
        raise SpecificationError(f"{name}: source and target field counts must match.")


def _parse_foreign_key(
    foreign_key: dict,
    entity_names: set[str],
) -> ForeignKeyDependency:
    """Parse one foreign-key definition."""

    name = foreign_key.get("name")
    source = foreign_key.get("source")
    target = foreign_key.get("target")

    if not isinstance(name, str) or not name:
        raise SpecificationError("Each FORGE foreign key must have a non-empty name.")

    if not isinstance(source, dict) or not isinstance(target, dict):
        raise SpecificationError(f"{name}: source and target must be objects.")

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
    """Build entity-level generation dependencies from top-level FKs."""

    foreign_keys = specification.get("foreign_keys", [])

    if foreign_keys is None:
        foreign_keys = []

    if not isinstance(foreign_keys, list):
        raise SpecificationError("FORGE specification foreign_keys must be a list.")

    dependencies: dict[str, list[ForeignKeyDependency]] = {
        entity_name: [] for entity_name in entity_names
    }

    for foreign_key in foreign_keys:
        if not isinstance(foreign_key, dict):
            raise SpecificationError("Each FORGE foreign key must be an object.")

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
    """Parse one relationship definition."""

    source = relationship.get("source")
    target = relationship.get("target")

    if not isinstance(source, str) or not source:
        raise SpecificationError("Each relationship must have a source.")

    if not isinstance(target, str) or not target:
        raise SpecificationError("Each relationship must have a target.")

    if "." not in source or "." not in target:
        raise SpecificationError(
            "Relationship source and target must use " "'ENTITY.FIELD' notation."
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
        raise SpecificationError("Each relationship must have a type.")

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
    """Build canonical relationship definitions."""

    relationships = specification.get("relationships", [])

    if relationships is None:
        relationships = []

    if not isinstance(relationships, list):
        raise SpecificationError("FORGE specification relationships must be a list.")

    result: list[RelationshipDependency] = []

    for relationship in relationships:
        if not isinstance(relationship, dict):
            raise SpecificationError("Each FORGE relationship must be an object.")

        result.append(
            _parse_relationship(
                relationship,
                entity_names,
            )
        )

    return tuple(result)


def _parse_constraint(
    constraint: dict,
    entity_names: set[str],
) -> ConstraintDefinition:
    """Parse one constraint definition."""

    entity = constraint.get("entity")
    field = constraint.get("field")
    operator = constraint.get("operator")

    if not isinstance(entity, str) or not entity:
        raise SpecificationError("Each constraint must have a non-empty entity.")

    _validate_entity_reference(
        entity,
        entity_names,
        "Constraint",
    )

    if not isinstance(field, str) or not field:
        raise SpecificationError(f"{entity}: constraint field must be non-empty.")

    if not isinstance(operator, str) or not operator:
        raise SpecificationError(
            f"{entity}.{field}: constraint operator must be non-empty."
        )

    if "value" not in constraint:
        raise SpecificationError(f"{entity}.{field}: constraint must contain a value.")

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
    """Build canonical constraint definitions."""

    constraints = specification.get("constraints", [])

    if constraints is None:
        constraints = []

    if not isinstance(constraints, list):
        raise SpecificationError("FORGE specification constraints must be a list.")

    result: list[ConstraintDefinition] = []

    for constraint in constraints:
        if not isinstance(constraint, dict):
            raise SpecificationError("Each FORGE constraint must be an object.")

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
    """Return and validate the population count for one entity."""

    population = entity.get("population")

    if not isinstance(population, dict):
        raise SpecificationError(f"{entity_name}: population must be an object.")

    target_rows = population.get("count")

    if (
        not isinstance(target_rows, int)
        or isinstance(target_rows, bool)
        or target_rows < 0
    ):
        raise SpecificationError(
            f"{entity_name}: population.count must be " "a non-negative integer."
        )

    return target_rows


def _build_entity_plan(
    entity: dict,
    dependencies: dict[str, tuple[ForeignKeyDependency, ...]],
) -> EntityGenerationPlan:
    """Build the generation plan for one entity."""

    entity_name = entity.get("name")

    if not isinstance(entity_name, str) or not entity_name:
        raise SpecificationError("Each FORGE entity must have a non-empty name.")

    target_rows = _get_population_count(
        entity_name,
        entity,
    )

    return EntityGenerationPlan(
        entity_name=entity_name,
        target_rows=target_rows,
        dependencies=dependencies.get(
            entity_name,
            (),
        ),
    )


def _build_entity_plans(
    entities: list,
    dependencies: dict[str, tuple[ForeignKeyDependency, ...]],
) -> tuple[EntityGenerationPlan, ...]:
    """Build generation plans for all entities."""

    plans: list[EntityGenerationPlan] = []

    for entity in entities:
        if not isinstance(entity, dict):
            raise SpecificationError("Each FORGE entity must be an object.")

        plans.append(
            _build_entity_plan(
                entity,
                dependencies,
            )
        )

    return tuple(plans)


def build_generation_plan(
    specification: dict,
) -> GenerationPlan:
    """
    Build a dependency-aware generation plan.

    This function only orchestrates planning.
    No data is generated here.
    """

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
        constraints=constraints,
    )

    # Resolve dependencies during planning so cycles fail before
    # generation begins.
    plan.generation_order

    return plan


def initialize_job_progress(
    job: GenerationJob,
    plan: GenerationPlan,
) -> GenerationJob:
    """
    Initialize entity-level progress from a generation plan.

    The supplied job is updated in place and returned for convenience.
    """

    job.entities = {
        entity_plan.entity_name: EntityGenerationProgress(
            entity_name=entity_plan.entity_name,
            target_rows=entity_plan.target_rows,
        )
        for entity_plan in plan.entities
    }

    return job
