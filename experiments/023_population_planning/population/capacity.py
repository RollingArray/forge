"""Analyze identity and foreign-key capacity constraints."""

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class CapacityRequirement:
    """A minimum population requirement derived from key capacity."""

    entity: str
    minimum: int
    relationship: str
    reason: str


@dataclass(frozen=True)
class CapacityLimit:
    """A maximum population supported by available relationship keys."""

    entity: str
    maximum: int
    relationship: str
    reason: str


def _get_identity_fields(
    entities: dict[str, Any],
    entity: str,
) -> tuple[str, ...]:
    """Return identity fields for an entity."""

    metadata = entities.get(entity)

    if metadata is None:
        return ()

    if isinstance(metadata, dict):
        identity = metadata.get("identity")

        if identity:
            return tuple(identity)

    if hasattr(metadata, "identity"):
        identity = metadata.identity

        if identity:
            return tuple(identity)

    return ()


def _get_population(
    populations: dict[str, Any],
    entity: str,
) -> int | None:
    """Return the requested population for an entity."""

    population = populations.get(entity)

    if population is None:
        return None

    if hasattr(population, "requested"):
        return population.requested

    if isinstance(population, dict):
        return population.get(
            "requested",
            population.get("count"),
        )

    if isinstance(population, int):
        return population

    return None


def _is_complete_identity_fk(
    source_fields: tuple[str, ...],
    target_fields: tuple[str, ...],
    child_identity: tuple[str, ...],
    parent_identity: tuple[str, ...],
) -> bool:
    """Return whether an FK covers both complete entity identities."""

    if not source_fields or not target_fields:
        return False

    if not child_identity or not parent_identity:
        return False

    # Identity field order is not semantically significant.
    # The FK must cover the complete identity field set on both sides.
    return set(source_fields) == set(child_identity) and set(target_fields) == set(
        parent_identity
    )


def analyze_fk_capacity(
    child_entity: str,
    dependency: Any,
    entities: dict[str, Any],
    populations: dict[str, Any],
) -> tuple[
    list[CapacityRequirement],
    list[CapacityLimit],
]:
    """Analyze key-capacity implications for one foreign key.

    When the complete child identity is also the FK source and the complete
    parent identity is the FK target:

        child identity == child FK source fields
        parent identity == parent FK target fields

    every child record requires a distinct compatible parent identity key.

    Therefore:

        known child population
            -> minimum parent population

        known parent population
            -> maximum child population

    This function only derives requirements and limits. It does not modify
    populations.
    """

    parent_entity = dependency.parent_entity

    source_fields = tuple(dependency.source_fields)
    target_fields = tuple(dependency.target_fields)

    child_identity = _get_identity_fields(
        entities,
        child_entity,
    )

    parent_identity = _get_identity_fields(
        entities,
        parent_entity,
    )

    child_population = _get_population(
        populations,
        child_entity,
    )

    parent_population = _get_population(
        populations,
        parent_entity,
    )

    requirements: list[CapacityRequirement] = []
    limits: list[CapacityLimit] = []

    if not _is_complete_identity_fk(
        source_fields=source_fields,
        target_fields=target_fields,
        child_identity=child_identity,
        parent_identity=parent_identity,
    ):
        return requirements, limits

    relationship_name = (
        f"{child_entity}.({', '.join(source_fields)})"
        f" -> "
        f"{parent_entity}.({', '.join(target_fields)})"
    )

    # Known child population requires enough distinct parent keys.
    if child_population is not None:
        requirements.append(
            CapacityRequirement(
                entity=parent_entity,
                minimum=child_population,
                relationship=relationship_name,
                reason=(
                    f"Every {child_entity} record requires a distinct "
                    f"compatible {parent_entity} identity key because the "
                    f"foreign key covers the complete child identity."
                ),
            )
        )

    # Known parent population limits how many distinct child identities
    # can reference those parent keys under this one-to-one key mapping.
    if parent_population is not None:
        limits.append(
            CapacityLimit(
                entity=child_entity,
                maximum=parent_population,
                relationship=relationship_name,
                reason=(
                    f"The available {parent_entity} identity keys can "
                    f"support at most {parent_population} {child_entity} "
                    f"records because each child requires a distinct "
                    f"compatible parent key."
                ),
            )
        )

    return requirements, limits


def analyze_fk_capacities(
    dependencies_by_entity: dict[str, tuple[Any, ...]],
    entities: dict[str, Any],
    populations: dict[str, Any],
) -> tuple[
    list[CapacityRequirement],
    list[CapacityLimit],
]:
    """Analyze key-capacity requirements and limits across all FKs."""

    requirements: list[CapacityRequirement] = []
    limits: list[CapacityLimit] = []

    for child_entity, dependencies in dependencies_by_entity.items():
        for dependency in dependencies:
            dependency_requirements, dependency_limits = analyze_fk_capacity(
                child_entity=child_entity,
                dependency=dependency,
                entities=entities,
                populations=populations,
            )

            requirements.extend(dependency_requirements)
            limits.extend(dependency_limits)

    return requirements, limits


def minimum_capacity_by_entity(
    requirements: list[CapacityRequirement],
) -> dict[str, int]:
    """Collapse capacity requirements to the strongest minimum per entity."""

    minimums: dict[str, int] = {}

    for requirement in requirements:
        current = minimums.get(
            requirement.entity,
            0,
        )

        minimums[requirement.entity] = max(
            current,
            requirement.minimum,
        )

    return minimums


def maximum_capacity_by_entity(
    limits: list[CapacityLimit],
) -> dict[str, int]:
    """Collapse capacity limits to the strongest maximum per entity."""

    maximums: dict[str, int] = {}

    for limit in limits:
        current = maximums.get(limit.entity)

        if current is None:
            maximums[limit.entity] = limit.maximum
        else:
            maximums[limit.entity] = min(
                current,
                limit.maximum,
            )

    return maximums
