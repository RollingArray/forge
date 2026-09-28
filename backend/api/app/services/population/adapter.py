"""
File: adapter.py
Purpose: Build production population-planning inputs from a FORGE specification.
"""

from typing import Any

from .model import EntityPopulation, PopulationMode
from .planner import PopulationPlan, build_population_plan


def build_population_inputs(
    specification: dict[str, Any],
) -> dict[str, int | str]:
    """Extract entity populations from a FORGE specification."""

    populations: dict[str, int | str] = {}

    for entity in specification.get("entities", []):
        name = entity["name"]
        population = entity.get("population", {})
        count = population.get("count")

        if count is None:
            populations[name] = "AUTO"
        else:
            populations[name] = count

    return populations


def build_entities_metadata(
    specification: dict[str, Any],
) -> dict[str, dict[str, Any]]:
    """Build entity metadata required by capacity analysis."""

    entities: dict[str, dict[str, Any]] = {}

    for entity in specification.get("entities", []):
        entities[entity["name"]] = {
            "identity": entity.get("identity", {}).get("fields", [])
        }

    return entities


def build_relationships(
    specification: dict[str, Any],
) -> list[dict[str, Any]]:
    """Extract relationship definitions."""

    return list(specification.get("relationships", []))


def build_dependencies_by_entity(
    specification: dict[str, Any],
) -> dict[str, tuple[EntityPopulation, ...]]:
    """Build FK dependency metadata for capacity analysis."""

    dependencies: dict[str, list[Any]] = {}

    for foreign_key in specification.get("foreign_keys", []):
        source = foreign_key["source"]
        target = foreign_key["target"]

        dependency = _ForeignKeyDependency(
            foreign_key_name=foreign_key["name"],
            parent_entity=target["entity"],
            source_fields=tuple(source["fields"]),
            target_fields=tuple(target["fields"]),
        )

        dependencies.setdefault(
            source["entity"],
            [],
        ).append(dependency)

    return {
        entity: tuple(entity_dependencies)
        for entity, entity_dependencies in dependencies.items()
    }


class _ForeignKeyDependency:
    """Internal FK dependency representation used by capacity analysis."""

    def __init__(
        self,
        foreign_key_name: str,
        parent_entity: str,
        source_fields: tuple[str, ...],
        target_fields: tuple[str, ...],
    ) -> None:
        self.foreign_key_name = foreign_key_name
        self.parent_entity = parent_entity
        self.source_fields = source_fields
        self.target_fields = target_fields


def build_plan_from_specification(
    specification: dict[str, Any],
) -> PopulationPlan:
    """Build a population plan directly from a FORGE specification."""

    populations = build_population_inputs(specification)
    relationships = build_relationships(specification)
    entities = build_entities_metadata(specification)
    dependencies = build_dependencies_by_entity(specification)

    return build_population_plan(
        populations=populations,
        relationships=relationships,
        dependencies_by_entity=dependencies,
        entities=entities,
    )
