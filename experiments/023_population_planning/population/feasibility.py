"""Evaluate population requests against feasible bounds."""

from dataclasses import dataclass

from .model import (
    EntityPopulation,
    PopulationMode,
    PopulationStatus,
)


@dataclass(frozen=True)
class PopulationFeasibility:
    """Feasibility result for one entity population."""

    entity: str
    requested: int | None
    minimum_feasible: int | None
    maximum_feasible: int | None
    status: PopulationStatus
    reason: str | None = None
    recommendation: str | None = None


def evaluate_population(
    population: EntityPopulation,
    minimum_feasible: int | None = None,
    maximum_feasible: int | None = None,
) -> PopulationFeasibility:
    """Evaluate one population against optional minimum and maximum bounds."""

    entity = population.entity

    if population.mode == PopulationMode.AUTO:
        if (
            minimum_feasible is not None
            and maximum_feasible is not None
            and minimum_feasible > maximum_feasible
        ):
            return PopulationFeasibility(
                entity=entity,
                requested=None,
                minimum_feasible=minimum_feasible,
                maximum_feasible=maximum_feasible,
                status=PopulationStatus.INFEASIBLE,
                reason=(
                    f"Derived minimum population "
                    f"{minimum_feasible:,} exceeds the maximum "
                    f"feasible population "
                    f"{maximum_feasible:,}."
                ),
                recommendation=(
                    "Adjust the related entity populations or "
                    "relationship constraints."
                ),
            )

        return PopulationFeasibility(
            entity=entity,
            requested=None,
            minimum_feasible=minimum_feasible,
            maximum_feasible=maximum_feasible,
            status=PopulationStatus.AUTO,
            reason=(
                "Population was requested as AUTO and will be "
                "resolved by the population planner."
            ),
        )

    requested = population.requested

    if requested is None:
        return PopulationFeasibility(
            entity=entity,
            requested=None,
            minimum_feasible=minimum_feasible,
            maximum_feasible=maximum_feasible,
            status=PopulationStatus.UNRESOLVED,
            reason=(
                "No population value was provided for this entity."
            ),
        )

    if (
        minimum_feasible is not None
        and requested < minimum_feasible
    ):
        return PopulationFeasibility(
            entity=entity,
            requested=requested,
            minimum_feasible=minimum_feasible,
            maximum_feasible=maximum_feasible,
            status=PopulationStatus.INFEASIBLE,
            reason=(
                f"Requested population {requested:,} is below "
                f"the minimum feasible population of "
                f"{minimum_feasible:,}."
            ),
            recommendation=(
                f"Increase {entity} population to at least "
                f"{minimum_feasible:,}."
            ),
        )

    if (
        maximum_feasible is not None
        and requested > maximum_feasible
    ):
        return PopulationFeasibility(
            entity=entity,
            requested=requested,
            minimum_feasible=minimum_feasible,
            maximum_feasible=maximum_feasible,
            status=PopulationStatus.INFEASIBLE,
            reason=(
                f"Requested population {requested:,} exceeds "
                f"the maximum feasible population of "
                f"{maximum_feasible:,}."
            ),
            recommendation=(
                f"Reduce {entity} population to at most "
                f"{maximum_feasible:,}, or increase the "
                "supporting parent population."
            ),
        )

    return PopulationFeasibility(
        entity=entity,
        requested=requested,
        minimum_feasible=minimum_feasible,
        maximum_feasible=maximum_feasible,
        status=PopulationStatus.FEASIBLE,
        reason=(
            "Requested population is within the derived "
            "feasible bounds."
        ),
    )


def evaluate_populations(
    populations: dict[str, EntityPopulation],
    minimums: dict[str, int] | None = None,
    maximums: dict[str, int] | None = None,
) -> dict[str, PopulationFeasibility]:
    """Evaluate all entity populations against their feasible bounds."""

    minimums = minimums or {}
    maximums = maximums or {}

    return {
        entity: evaluate_population(
            population=population,
            minimum_feasible=minimums.get(entity),
            maximum_feasible=maximums.get(entity),
        )
        for entity, population in populations.items()
    }


def has_infeasible_populations(
    feasibility: dict[str, PopulationFeasibility],
) -> bool:
    """Return True when at least one population is infeasible."""

    return any(
        result.status == PopulationStatus.INFEASIBLE
        for result in feasibility.values()
    )
