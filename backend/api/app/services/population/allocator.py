"""
Constraint-aware target population allocation for FORGE.

SCALABLE entities are allocated from derived minimum populations.
FIXED entities retain their declared populations.

Minimum and maximum bounds are derived independently:
- Minimum pass: SCALABLE entities are seeded at 1; FIXED counts are retained.
- Maximum pass: SCALABLE entities are AUTO; FIXED counts are retained.

The integer allocation solver distributes the remaining target
minimum-first and respects the derived bounds.

A candidate is FEASIBLE only when its exact total and all supported
necessary population constraints have been independently verified.
This module does not claim row-level relationship generation guarantees.
"""

from dataclasses import dataclass
from math import prod
from typing import Any

from .adapter import (
    build_dependencies_by_entity,
    build_entities_metadata,
)
from .allocation_solver import allocate_integer_populations
from .constraint_analysis import analyze_specification_constraints
from .planner import PopulationPlan, build_population_plan


@dataclass(frozen=True)
class PopulationAllocation:
    target: int
    driver: str
    populations: dict[str, int]
    fixed_total: int
    unaffected_total: int
    scalable_total: int
    allocated_total: int
    affected_entities: tuple[str, ...]
    feasible_target: bool
    reason: str | None = None
    status: str = "UNRESOLVED"
    diagnostics: tuple[str, ...] = ()


def _validate_positive_integer(value: object, field_name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"{field_name} must be an integer.")
    if value <= 0:
        raise ValueError(f"{field_name} must be greater than zero.")
    return value


def _validate_population_inputs(
    specification: dict[str, Any],
) -> tuple[dict[str, int], dict[str, str]]:
    """Validate populations while preserving FIXED and SCALABLE semantics."""

    entities = specification.get("entities")
    if not isinstance(entities, list) or not entities:
        raise ValueError("Specification must contain at least one entity.")

    counts: dict[str, int] = {}
    scaling: dict[str, str] = {}

    for entity in entities:
        if (
            not isinstance(entity, dict)
            or not isinstance(entity.get("name"), str)
            or not entity["name"].strip()
        ):
            raise ValueError("Every entity must have a valid name.")

        name = entity["name"]

        if name in counts:
            raise ValueError(f"Duplicate entity name: {name}")

        population = entity.get("population") or {}
        if not isinstance(population, dict):
            raise ValueError(f"Population definition for '{name}' must be an object.")

        mode = population.get("scaling", "SCALABLE")
        if mode not in {"FIXED", "SCALABLE"}:
            raise ValueError(
                f"Population scaling for '{name}' must be FIXED or SCALABLE."
            )

        count = population.get("count")

        if count is None:
            if mode == "FIXED":
                raise ValueError(
                    f"FIXED entity '{name}' must have an explicit population count."
                )

            # SCALABLE entities may use AUTO. Their previous count is not
            # an allocation minimum or weight.
            counts[name] = 0
        else:
            if isinstance(count, bool) or not isinstance(count, int) or count < 0:
                raise ValueError(
                    f"Population count for '{name}' must be a " "non-negative integer."
                )

            counts[name] = count

        scaling[name] = mode

    return counts, scaling


def _constraint_violations(
    populations: dict[str, int],
    constraints: list[Any],
) -> list[str]:
    """Verify supported necessary population constraints."""

    violations: list[str] = []

    for constraint in constraints:
        kind = constraint.kind
        entity = constraint.entity
        related = tuple(constraint.related_entities)
        value = populations.get(entity, 0)

        if kind == "PARENT_REQUIRED_FOR_POSITIVE_CHILD":
            if value > 0:
                for parent in related:
                    if populations.get(parent, 0) <= 0:
                        violations.append(
                            f"{entity} has {value:,} rows but required parent "
                            f"{parent} has no identity keys."
                        )

        elif kind == "CHILD_AT_LEAST_PARENT":
            if related:
                parent = related[0]
                if value < populations.get(parent, 0):
                    violations.append(
                        f"{entity} must have at least as many rows as {parent}."
                    )

        elif kind == "CHILD_AT_MOST_PARENT":
            if related:
                parent = related[0]
                if value > populations.get(parent, 0):
                    violations.append(
                        f"{entity} cannot exceed the population of {parent}."
                    )

        elif kind == "IDENTITY_CAPACITY":
            capacity = constraint.multiplier * prod(
                populations.get(parent, 0) for parent in related
            )
            if value > capacity:
                violations.append(
                    f"{entity} population {value:,} exceeds its derived "
                    f"identity capacity {capacity:,}."
                )

        else:
            violations.append(f"Unsupported population constraint kind: {kind}.")

    return violations


def _planner_inputs(
    specification: dict[str, Any],
    counts: dict[str, int],
    scaling: dict[str, str],
    scalable_mode: str,
) -> dict[str, Any]:
    """
    Build inputs for one independent population-planning pass.

    scalable_mode:
        BASELINE_ONE: use 1 for every SCALABLE entity.
        AUTO: use AUTO for every SCALABLE entity.

    FIXED populations always retain their declared counts.
    """

    if scalable_mode not in {"BASELINE_ONE", "AUTO"}:
        raise ValueError(f"Unsupported scalable planner mode: {scalable_mode}")

    populations: dict[str, int | str] = {}

    for name in counts:
        if scaling[name] == "FIXED":
            populations[name] = counts[name]
        elif scalable_mode == "BASELINE_ONE":
            populations[name] = 1
        else:
            populations[name] = "AUTO"

    return {
        "populations": populations,
        "relationships": list(specification.get("relationships", [])),
        "entities": build_entities_metadata(specification),
        "dependencies": build_dependencies_by_entity(specification),
    }


def _build_planner_pass(
    specification: dict[str, Any],
    counts: dict[str, int],
    scaling: dict[str, str],
    scalable_mode: str,
) -> PopulationPlan:
    """Build one population-planning pass using the requested baseline."""

    inputs = _planner_inputs(
        specification=specification,
        counts=counts,
        scaling=scaling,
        scalable_mode=scalable_mode,
    )

    return build_population_plan(
        populations=inputs["populations"],
        relationships=inputs["relationships"],
        dependencies_by_entity=inputs["dependencies"],
        entities=inputs["entities"],
    )


def allocate_population_target(
    specification: dict[str, Any],
    target: int,
    driver: str,
) -> PopulationAllocation:
    """Allocate a whole-model target across all SCALABLE entities."""

    target = _validate_positive_integer(target, "target")

    if not isinstance(driver, str) or not driver.strip():
        raise ValueError("driver must be a non-empty entity name.")

    driver = driver.strip()

    counts, scaling = _validate_population_inputs(specification)
    names = set(counts)

    if driver not in names:
        raise ValueError(
            f"Population driver '{driver}' does not exist in the specification."
        )

    affected = tuple(sorted(names))

    fixed = sorted(name for name in names if scaling[name] == "FIXED")
    scalable = sorted(name for name in names if scaling[name] == "SCALABLE")

    fixed_populations = {name: counts[name] for name in fixed}
    fixed_total = sum(fixed_populations.values())

    def result(
        populations: dict[str, int],
        status: str,
        reason: str | None,
        diagnostics: tuple[str, ...] = (),
    ) -> PopulationAllocation:
        complete = {name: populations.get(name, counts[name]) for name in sorted(names)}
        allocated = sum(complete.values())

        return PopulationAllocation(
            target=target,
            driver=driver,
            populations=complete,
            fixed_total=fixed_total,
            unaffected_total=0,
            scalable_total=sum(complete[name] for name in scalable),
            allocated_total=allocated,
            affected_entities=affected,
            feasible_target=(status == "FEASIBLE" and allocated == target),
            reason=reason,
            status=status,
            diagnostics=diagnostics,
        )

    if scaling[driver] == "FIXED":
        return result(
            counts,
            "INFEASIBLE",
            f"Population driver '{driver}' is FIXED. Select a SCALABLE entity.",
        )

    if not scalable:
        return result(
            counts,
            "INFEASIBLE",
            "The specification contains no SCALABLE entities.",
        )

    if target < fixed_total:
        return result(
            counts,
            "INFEASIBLE",
            f"Target {target:,} is below the fixed population total "
            f"of {fixed_total:,}.",
        )

    analysis = analyze_specification_constraints(specification)

    if not analysis.structurally_valid:
        messages = tuple(
            item.get("message", str(item)) if isinstance(item, dict) else str(item)
            for item in analysis.diagnostics
        )
        return result(
            counts,
            "UNRESOLVED",
            "The specification has structural errors; allocation cannot be verified.",
            messages,
        )

    if not analysis.allocation_supported:
        messages = tuple(
            item.reason
            for item in analysis.relationships
            if item.status != "MAPPED" and item.reason
        )
        return result(
            counts,
            "UNRESOLVED",
            "The specification contains relationship or identity semantics "
            "that the allocator cannot currently establish.",
            messages,
        )

    # ---------------------------------------------------------------
    # PASS 1: derive minimums.
    #
    # Every SCALABLE entity is seeded at 1. This allows population-
    # dependent relationship rules to become visible to the planner.
    #
    # FIXED entities retain their actual declared populations.
    #
    # IMPORTANT: maximums from this pass must NOT be used. A scalable
    # parent seeded at 1 could otherwise create a false child maximum
    # of 1.
    # ---------------------------------------------------------------

    try:
        minimum_plan = _build_planner_pass(
            specification=specification,
            counts=counts,
            scaling=scaling,
            scalable_mode="BASELINE_ONE",
        )
    except (KeyError, TypeError, ValueError) as exc:
        return result(
            counts,
            "UNRESOLVED",
            "The population planner could not derive minimum allocation bounds.",
            (f"Minimum derivation: {exc}",),
        )

    minimums: dict[str, int] = {
        name: max(1, minimum_plan.minimums.get(name, 0)) for name in scalable
    }

    # ---------------------------------------------------------------
    # PASS 2: derive maximums.
    #
    # SCALABLE entities are AUTO. Only FIXED parent populations can
    # establish finite capacity limits for SCALABLE child entities.
    #
    # IMPORTANT: minimums from this pass must NOT be used. Population-
    # dependent relationship minimums may disappear when populations
    # are AUTO.
    # ---------------------------------------------------------------

    try:
        maximum_plan = _build_planner_pass(
            specification=specification,
            counts=counts,
            scaling=scaling,
            scalable_mode="AUTO",
        )
    except (KeyError, TypeError, ValueError) as exc:
        return result(
            counts,
            "UNRESOLVED",
            "The population planner could not derive maximum allocation bounds.",
            (f"Maximum derivation: {exc}",),
        )

    maximums: dict[str, int | None] = {
        name: maximum_plan.maximums[name]
        for name in scalable
        if name in maximum_plan.maximums
    }

    # ---------------------------------------------------------------
    # Validate the combined bounds.
    # ---------------------------------------------------------------

    contradictory_bounds = [
        (
            name,
            minimums[name],
            maximums[name],
        )
        for name in scalable
        if (maximums.get(name) is not None and minimums[name] > maximums[name])
    ]

    if contradictory_bounds:
        diagnostics = tuple(
            f"{name} has derived minimum {minimum:,} greater than "
            f"maximum {maximum:,}."
            for name, minimum, maximum in contradictory_bounds
        )

        candidate = dict(fixed_populations)
        candidate.update(minimums)

        return result(
            candidate,
            "INFEASIBLE",
            "One or more SCALABLE entities have contradictory derived "
            "population bounds.",
            diagnostics,
        )

    # FIXED entities cannot be changed to satisfy derived bounds.
    #
    # Minimums come from the baseline-one pass.
    # Maximums come from the AUTO pass.
    fixed_bound_violations: list[str] = []

    for name in fixed:
        count = counts[name]

        minimum = minimum_plan.minimums.get(name)
        maximum = maximum_plan.maximums.get(name)

        if minimum is not None and count < minimum:
            fixed_bound_violations.append(
                f"FIXED entity {name} has {count:,} rows, below its "
                f"derived minimum of {minimum:,}."
            )

        if maximum is not None and count > maximum:
            fixed_bound_violations.append(
                f"FIXED entity {name} has {count:,} rows, above its "
                f"derived maximum of {maximum:,}."
            )

    if fixed_bound_violations:
        candidate = dict(fixed_populations)
        candidate.update(minimums)

        return result(
            candidate,
            "INFEASIBLE",
            "One or more FIXED populations violate derived population bounds.",
            tuple(fixed_bound_violations),
        )

    # ---------------------------------------------------------------
    # Allocate the target using the existing integer solver.
    # ---------------------------------------------------------------

    try:
        allocation = allocate_integer_populations(
            target=target,
            minimums=minimums,
            maximums=maximums,
            fixed=fixed_populations,
        )
    except (TypeError, ValueError) as exc:
        return result(
            counts,
            "UNRESOLVED",
            "The integer allocation solver could not process the derived bounds.",
            (str(exc),),
        )

    candidate = allocation.populations

    if not allocation.feasible:
        return result(
            candidate,
            "INFEASIBLE",
            allocation.reason,
            (
                f"Derived minimum total: {allocation.minimum_total:,}.",
                (
                    "Derived maximum total: unbounded."
                    if allocation.maximum_total is None
                    else (f"Derived maximum total: " f"{allocation.maximum_total:,}.")
                ),
            ),
        )

    if allocation.allocated_total != target:
        return result(
            candidate,
            "UNRESOLVED",
            "The allocation solver did not produce the requested exact total.",
            (
                f"Requested total: {target:,}.",
                f"Allocated total: {allocation.allocated_total:,}.",
            ),
        )

    # ---------------------------------------------------------------
    # Independent verification.
    #
    # Derived bounds are necessary conditions. They are not a
    # substitute for checking the candidate against the supported
    # population constraints.
    # ---------------------------------------------------------------

    violations = _constraint_violations(
        candidate,
        analysis.population_constraints,
    )

    if violations:
        return result(
            candidate,
            "UNRESOLVED",
            "The candidate meets the derived bounds but failed the "
            "independent population-constraint verification.",
            tuple(violations),
        )

    return result(candidate, "FEASIBLE", None)
