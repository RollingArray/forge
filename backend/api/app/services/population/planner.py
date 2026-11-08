"""
File: planner.py
Purpose: Resolve explicit and AUTO entity populations.

The planning semantics in this module preserve Experiment 023.
"""

from dataclasses import dataclass
from math import prod
from typing import Any

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
from .relationship import (
    PopulationRequirement,
    analyze_populations,
    minimum_requirements_by_entity,
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

    raise ValueError(
        f"Invalid population definition for '{entity}': {value!r}"
    )


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
                "Adjust the related entity populations or "
                "relationship constraints."
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
                "Population was resolved from the minimum "
                "feasible requirement."
            ),
            recommendation=(
                f"Resolved population: {minimum_feasible:,}."
            ),
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
                "Population was resolved from the available "
                "key-capacity bound."
            ),
            recommendation=(
                f"Resolved population: {maximum_feasible:,}."
            ),
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


def _analyze_specification_capacities(
    specification: dict[str, Any],
    populations: dict[str, EntityPopulation],
    *,
    derive_limits: bool = True,
) -> tuple[list[CapacityRequirement], list[CapacityLimit]]:
    """Derive population bounds from the canonical identity analysis."""

    from .constraint_analysis import analyze_specification_constraints

    analysis = analyze_specification_constraints(specification)

    # Capacity is evaluated per identity. An unrelated unresolved
    # relationship must not suppress bounds for otherwise supported
    # identity components. Unsupported identities are skipped individually
    # below, rather than receiving an assumed capacity.
    requirements: list[CapacityRequirement] = []
    limits: list[CapacityLimit] = []

    # A positive child population requires at least one key in every
    # referenced parent keyspace. It does not require one parent key per
    # child row unless the complete identity semantics establish that.
    for dependency in analysis.foreign_key_dependencies:
        child_population = populations.get(dependency.child_entity)
        if (
            child_population is None
            or child_population.requested is None
            or child_population.requested <= 0
        ):
            continue

        requirements.append(
            CapacityRequirement(
                entity=dependency.parent_entity,
                minimum=1,
                relationship=dependency.name,
                reason=(
                    f"A positive {dependency.child_entity} population "
                    f"requires at least one {dependency.parent_entity} "
                    "identity key."
                ),
            )
        )

    # EntityGenerator constructs identity combinations as a Cartesian
    # product of independent FK and finite local identity components.
    # The allocator's baseline pass uses temporary population values only
    # to derive minimum requirements. Those values must not become finite
    # identity limits. The AUTO pass derives limits from fixed populations.
    if not derive_limits:
        return requirements, limits

    for capacity in analysis.identity_capacities:
        if not capacity.supported or capacity.unbounded:
            continue

        parent_populations: list[int] = []
        capacity_is_known = True

        for parent_entity in capacity.parent_entities:
            parent_population = populations.get(parent_entity)
            if (
                parent_population is None
                or parent_population.requested is None
            ):
                capacity_is_known = False
                break
            parent_populations.append(parent_population.requested)

        if not capacity_is_known:
            continue

        maximum = capacity.finite_multiplier * prod(parent_populations)

        limits.append(
            CapacityLimit(
                entity=capacity.entity,
                maximum=maximum,
                relationship="identity_components",
                reason=(
                    f"The {capacity.entity} identity supports at most "
                    f"{maximum:,} distinct combinations from its "
                    "independent identity components."
                ),
            )
        )

    return requirements, limits


def build_population_plan(
    populations: dict[str, Any],
    relationships: list[dict[str, Any]],
    dependencies_by_entity: dict[str, tuple[Any, ...]] | None = None,
    entities: dict[str, Any] | None = None,
    specification: dict[str, Any] | None = None,
    derive_capacity_limits: bool = True,
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

    relationship_minimums = minimum_requirements_by_entity(
        relationship_requirements,
    )

    capacity_requirements: list[CapacityRequirement] = []
    capacity_limits: list[CapacityLimit] = []
    capacity_minimums: dict[str, int] = {}
    maximums: dict[str, int] = {}

    if specification is not None:
        (
            capacity_requirements,
            capacity_limits,
        ) = _analyze_specification_capacities(
            specification=specification,
            populations=normalized,
            derive_limits=derive_capacity_limits,
        )
    elif dependencies_by_entity and entities:
        # Backward-compatible path for callers that provide only the
        # legacy population, entity, and FK metadata.
        (
            capacity_requirements,
            capacity_limits,
        ) = analyze_fk_capacities(
            dependencies_by_entity=dependencies_by_entity,
            entities=entities,
            populations=normalized,
        )

    capacity_minimums = minimum_capacity_by_entity(
        capacity_requirements,
    )

    maximums = maximum_capacity_by_entity(
        capacity_limits,
    )

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
