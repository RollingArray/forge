"""Analyze entity populations and relationship requirements."""

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class PopulationRequirement:
    """A minimum population requirement derived from a relationship."""

    entity: str
    minimum: int
    relationship: str
    reason: str


def _split_endpoint(endpoint: str) -> tuple[str, str]:
    """Split an entity.field endpoint."""

    entity, field = endpoint.split(".", 1)
    return entity, field


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
        return population.get("requested", population.get("count"))

    if isinstance(population, int):
        return population

    return None


def _analyze_one_to_one(
    source_entity: str,
    target_entity: str,
    source_participation: str,
    target_participation: str,
    source_population: int | None,
    target_population: int | None,
    relationship_name: str,
) -> list[PopulationRequirement]:
    """Derive population requirements for a ONE_TO_ONE relationship."""

    requirements: list[PopulationRequirement] = []

    if source_participation == "MANDATORY" and source_population is not None:
        requirements.append(
            PopulationRequirement(
                entity=target_entity,
                minimum=source_population,
                relationship=relationship_name,
                reason=(
                    f"ONE_TO_ONE relationship requires at least "
                    f"{source_population} {target_entity} records "
                    f"to support the mandatory participation of "
                    f"{source_entity}."
                ),
            )
        )

    if target_participation == "MANDATORY" and target_population is not None:
        requirements.append(
            PopulationRequirement(
                entity=source_entity,
                minimum=target_population,
                relationship=relationship_name,
                reason=(
                    f"ONE_TO_ONE relationship requires at least "
                    f"{target_population} {source_entity} records "
                    f"to support the mandatory participation of "
                    f"{target_entity}."
                ),
            )
        )

    return requirements


def _analyze_one_to_many(
    source_entity: str,
    target_entity: str,
    source_participation: str,
    target_participation: str,
    source_population: int | None,
    target_population: int | None,
    relationship_name: str,
) -> list[PopulationRequirement]:
    """Derive population requirements for a ONE_TO_MANY relationship."""

    requirements: list[PopulationRequirement] = []

    # Mandatory target participation means every target needs a source.
    # Therefore at least one source is required when targets exist.
    if (
        target_participation == "MANDATORY"
        and target_population is not None
        and target_population > 0
    ):
        requirements.append(
            PopulationRequirement(
                entity=source_entity,
                minimum=1,
                relationship=relationship_name,
                reason=(
                    f"ONE_TO_MANY relationship requires at least "
                    f"one {source_entity} record because "
                    f"{target_entity} participation is mandatory."
                ),
            )
        )

    # Mandatory source participation means every source needs at least
    # one target. Therefore target population must be >= source population.
    if source_participation == "MANDATORY" and source_population is not None:
        requirements.append(
            PopulationRequirement(
                entity=target_entity,
                minimum=source_population,
                relationship=relationship_name,
                reason=(
                    f"ONE_TO_MANY relationship requires at least "
                    f"{source_population} {target_entity} records "
                    f"because every {source_entity} must participate."
                ),
            )
        )

    return requirements


def _analyze_many_to_one(
    source_entity: str,
    target_entity: str,
    source_participation: str,
    target_participation: str,
    source_population: int | None,
    target_population: int | None,
    relationship_name: str,
) -> list[PopulationRequirement]:
    """Derive population requirements for a MANY_TO_ONE relationship."""

    requirements: list[PopulationRequirement] = []

    # Mandatory source participation means every source needs a target.
    # At least one target is therefore required when source records exist.
    if (
        source_participation == "MANDATORY"
        and source_population is not None
        and source_population > 0
    ):
        requirements.append(
            PopulationRequirement(
                entity=target_entity,
                minimum=1,
                relationship=relationship_name,
                reason=(
                    f"MANY_TO_ONE relationship requires at least "
                    f"one {target_entity} record because "
                    f"{source_entity} participation is mandatory."
                ),
            )
        )

    # Mandatory target participation means every target needs a source.
    # Therefore source population must be >= target population.
    if target_participation == "MANDATORY" and target_population is not None:
        requirements.append(
            PopulationRequirement(
                entity=source_entity,
                minimum=target_population,
                relationship=relationship_name,
                reason=(
                    f"MANY_TO_ONE relationship requires at least "
                    f"{target_population} {source_entity} records "
                    f"because every {target_entity} must participate."
                ),
            )
        )

    return requirements


def analyze_relationship(
    relationship: dict[str, Any],
    populations: dict[str, Any],
) -> list[PopulationRequirement]:
    """Analyze one relationship for minimum population requirements.

    This function only derives requirements. It does not modify populations.

    The current rules intentionally cover only population implications
    that can be established directly from relationship cardinality and
    participation. Identity-capacity constraints are handled separately.
    """

    source_entity, _ = _split_endpoint(relationship["source"])
    target_entity, _ = _split_endpoint(relationship["target"])

    relationship_type = relationship["type"]
    source_participation = relationship.get(
        "source_participation",
        "OPTIONAL",
    )
    target_participation = relationship.get(
        "target_participation",
        "OPTIONAL",
    )

    source_population = _get_population(
        populations,
        source_entity,
    )
    target_population = _get_population(
        populations,
        target_entity,
    )

    relationship_name = f"{relationship['source']} -> {relationship['target']}"

    if relationship_type == "ONE_TO_ONE":
        return _analyze_one_to_one(
            source_entity=source_entity,
            target_entity=target_entity,
            source_participation=source_participation,
            target_participation=target_participation,
            source_population=source_population,
            target_population=target_population,
            relationship_name=relationship_name,
        )

    if relationship_type == "ONE_TO_MANY":
        return _analyze_one_to_many(
            source_entity=source_entity,
            target_entity=target_entity,
            source_participation=source_participation,
            target_participation=target_participation,
            source_population=source_population,
            target_population=target_population,
            relationship_name=relationship_name,
        )

    if relationship_type == "MANY_TO_ONE":
        return _analyze_many_to_one(
            source_entity=source_entity,
            target_entity=target_entity,
            source_participation=source_participation,
            target_participation=target_participation,
            source_population=source_population,
            target_population=target_population,
            relationship_name=relationship_name,
        )

    if relationship_type == "MANY_TO_MANY":
        # Cardinality alone does not establish a minimum population on
        # either side. Additional relationship constraints are required.
        return []

    raise ValueError(f"Unsupported relationship type: {relationship_type!r}")


def analyze_populations(
    relationships: list[dict[str, Any]],
    populations: dict[str, Any],
) -> list[PopulationRequirement]:
    """Analyze all relationships and return derived requirements."""

    requirements: list[PopulationRequirement] = []

    for relationship in relationships:
        requirements.extend(
            analyze_relationship(
                relationship=relationship,
                populations=populations,
            )
        )

    return requirements


def minimum_requirements_by_entity(
    requirements: list[PopulationRequirement],
) -> dict[str, int]:
    """Collapse requirements to the strongest minimum per entity."""

    minimums: dict[str, int] = {}

    for requirement in requirements:
        current = minimums.get(requirement.entity, 0)
        minimums[requirement.entity] = max(
            current,
            requirement.minimum,
        )

    return minimums
