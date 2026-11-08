"""Deterministic defaults for canonical FORGE specifications."""

from copy import deepcopy
from typing import Any


DEFAULT_POPULATION_COUNT = 100
DEFAULT_POPULATION_SCALING = "SCALABLE"


def apply_specification_defaults(
    specification: dict[str, Any],
    assumptions: list[str] | None = None,
) -> tuple[dict[str, Any], list[str]]:
    """Apply established FORGE defaults without overwriting explicit values."""

    candidate = deepcopy(specification)

    existing_assumptions = (
        assumptions
        if assumptions is not None
        else []
    )
    resulting_assumptions = list(existing_assumptions)

    entities = candidate.get("entities")

    if isinstance(entities, list):
        for entity in entities:
            if not isinstance(entity, dict):
                continue

            entity_name = entity.get("name", "unnamed")
            population = entity.get("population")

            if not isinstance(population, dict):
                population = {}
                entity["population"] = population

            if population.get("count") is None:
                population["count"] = DEFAULT_POPULATION_COUNT
                assumption = (
                    f"FORGE default applied: entity {entity_name} "
                    f"population.count = {DEFAULT_POPULATION_COUNT}; "
                    "the user did not specify a count."
                )
                if assumption not in resulting_assumptions:
                    resulting_assumptions.append(assumption)

            if "scaling" not in population:
                population["scaling"] = DEFAULT_POPULATION_SCALING
                assumption = (
                    f"FORGE default applied: entity {entity_name} "
                    f"population.scaling = {DEFAULT_POPULATION_SCALING}; "
                    "the user did not explicitly request FIXED scaling."
                )
                if assumption not in resulting_assumptions:
                    resulting_assumptions.append(assumption)

    return candidate, resulting_assumptions
