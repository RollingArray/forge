"""Resolve explicit and AUTO entity populations."""

from dataclasses import dataclass
from typing import Any

from .analyzer import (
    PopulationRequirement,
    analyze_populations,
    minimum_requirements_by_entity,
)
from .capacity import (
    CapacityLimit,
    CapacityRequirement,
    analyze_fk_capacities,
    maximum_capacity_by_entity,
    minimum_capacity_by_entity,
)
from .feasibility import (
    PopulationFeasibility,
    evaluate_populations,
)
from .model import (
    EntityPopulation,
    PopulationMode,
    PopulationStatus,
)


@dataclass(frozen=True)
class PopulationPlan:
    """Complete population planning result."""

    populations: dict[str, EntityPopulation]
    relationship_requirements: list[PopulationRequirement]
    capacity_requirements: list[CapacityRequirement]
    capacity_limits: list[CapacityLimit]
    minimums: dict[str, int]
    maximums: dict[str, int]
    feasibility: dict[str, PopulationFeasibility]


def _normalize_population(
    entity: str,
    value: Any,
) -> EntityPopulation:
    """Convert a population input into EntityPopulation."""

    if isinstance(value, EntityPopulation):
        return value

    if isinstance(value, int):
        return EntityPopulation.explicit(
            entity=entity,
            count=value,
        )

    if isinstance(value, str):
        if value.upper() == "AUTO":
            return EntityPopulation.auto(entity)

    if isinstance(value, dict):
        count = value.get("count")

        if isinstance(count, str) and count.upper() == "AUTO":
            return EntityPopulation.auto(entity)

        if isinstance(count, int):
            return EntityPopulation.explicit(
                entity=entity,
                count=count,
            )

    raise ValueError(f"Invalid population definition for '{entity}': {value!r}")


def _merge_minimums(
    relationship_minimums: dict[str, int],
    capacity_minimums: dict[str, int],
) -> dict[str, int]:
    """Return the strongest minimum requirement per entity."""

    minimums: dict[str, int] = {}

    for entity, minimum in relationship_minimums.items():
        minimums[entity] = max(
            minimums.get(entity, 0),
            minimum,
        )

    for entity, minimum in capacity_minimums.items():
        minimums[entity] = max(
            minimums.get(entity, 0),
            minimum,
        )

    return minimums


def _resolve_auto_population(
    population: EntityPopulation,
    minimum_feasible: int | None,
    maximum_feasible: int | None,
) -> EntityPopulation:
    """Resolve an AUTO population from available feasible bounds."""

    entity = population.entity

    if (
        minimum_feasible is not None
        and maximum_feasible is not None
        and minimum_feasible > maximum_feasible
    ):
        return EntityPopulation(
            entity=entity,
            mode=PopulationMode.AUTO,
            requested=None,
            minimum_feasible=minimum_feasible,
            resolved=None,
            status=PopulationStatus.INFEASIBLE,
            reason=(
                f"Derived minimum population "
                f"{minimum_feasible:,} exceeds the maximum "
                f"feasible population {maximum_feasible:,}."
            ),
            recommendation=(
                "Adjust the related entity populations or " "relationship constraints."
            ),
        )

    if minimum_feasible is not None:
        return EntityPopulation(
            entity=entity,
            mode=PopulationMode.AUTO,
            requested=None,
            minimum_feasible=minimum_feasible,
            resolved=minimum_feasible,
            status=PopulationStatus.AUTO,
            reason=(
                "Population was resolved from the minimum " "feasible requirement."
            ),
            recommendation=(f"Resolved population: {minimum_feasible:,}."),
        )

    if maximum_feasible is not None:
        return EntityPopulation(
            entity=entity,
            mode=PopulationMode.AUTO,
            requested=None,
            minimum_feasible=None,
            resolved=maximum_feasible,
            status=PopulationStatus.AUTO,
            reason=(
                "Population was resolved from the available " "key-capacity bound."
            ),
            recommendation=(f"Resolved population: {maximum_feasible:,}."),
        )

    return EntityPopulation(
        entity=entity,
        mode=PopulationMode.AUTO,
        requested=None,
        minimum_feasible=None,
        resolved=None,
        status=PopulationStatus.UNRESOLVED,
        reason=(
            "No relationship or key-capacity population "
            "constraint could be established."
        ),
        recommendation=(
            "Provide an explicit population or additional "
            "constraints that allow FORGE to derive one."
        ),
    )


def _resolve_populations(
    populations: dict[str, EntityPopulation],
    minimums: dict[str, int],
    maximums: dict[str, int],
    feasibility: dict[str, PopulationFeasibility],
) -> dict[str, EntityPopulation]:
    """Resolve explicit and AUTO population states."""

    resolved: dict[str, EntityPopulation] = {}

    for entity, population in populations.items():
        minimum_feasible = minimums.get(entity)
        maximum_feasible = maximums.get(entity)

        if population.mode == PopulationMode.AUTO:
            resolved[entity] = _resolve_auto_population(
                population=population,
                minimum_feasible=minimum_feasible,
                maximum_feasible=maximum_feasible,
            )
            continue

        result = feasibility[entity]

        resolved[entity] = EntityPopulation(
            entity=entity,
            mode=population.mode,
            requested=population.requested,
            minimum_feasible=minimum_feasible,
            resolved=(
                population.requested
                if result.status == PopulationStatus.FEASIBLE
                else None
            ),
            status=result.status,
            reason=result.reason,
            recommendation=result.recommendation,
        )

    return resolved


def build_population_plan(
    populations: dict[str, Any],
    relationships: list[dict[str, Any]],
    dependencies_by_entity: dict[str, tuple[Any, ...]] | None = None,
    entities: dict[str, Any] | None = None,
) -> PopulationPlan:
    """Build a population plan from population and model semantics."""

    normalized: dict[str, EntityPopulation] = {
        entity: _normalize_population(
            entity=entity,
            value=value,
        )
        for entity, value in populations.items()
    }

    relationship_requirements = analyze_populations(
        relationships=relationships,
        populations=normalized,
    )

    relationship_minimums = minimum_requirements_by_entity(relationship_requirements)

    capacity_requirements: list[CapacityRequirement] = []
    capacity_limits: list[CapacityLimit] = []
    capacity_minimums: dict[str, int] = {}
    maximums: dict[str, int] = {}

    if dependencies_by_entity and entities:
        (
            capacity_requirements,
            capacity_limits,
        ) = analyze_fk_capacities(
            dependencies_by_entity=dependencies_by_entity,
            entities=entities,
            populations=normalized,
        )

        capacity_minimums = minimum_capacity_by_entity(capacity_requirements)

        maximums = maximum_capacity_by_entity(capacity_limits)

    minimums = _merge_minimums(
        relationship_minimums=relationship_minimums,
        capacity_minimums=capacity_minimums,
    )

    feasibility = evaluate_populations(
        populations=normalized,
        minimums=minimums,
        maximums=maximums,
    )

    resolved = _resolve_populations(
        populations=normalized,
        minimums=minimums,
        maximums=maximums,
        feasibility=feasibility,
    )

    return PopulationPlan(
        populations=resolved,
        relationship_requirements=relationship_requirements,
        capacity_requirements=capacity_requirements,
        capacity_limits=capacity_limits,
        minimums=minimums,
        maximums=maximums,
        feasibility=feasibility,
    )


def has_infeasible_plan(
    plan: PopulationPlan,
) -> bool:
    """Return True when the plan contains an infeasible population."""

    return any(
        population.status == PopulationStatus.INFEASIBLE
        for population in plan.populations.values()
    )
