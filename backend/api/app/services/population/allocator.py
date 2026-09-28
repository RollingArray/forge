
"""
File: allocator.py
Purpose: Build target-driven population candidates for FORGE.

The allocator is intentionally separate from the Experiment 023 population
planner. It creates a candidate distribution. Experiment 023 remains the
authority for structural feasibility.
"""

from collections import deque
from dataclasses import dataclass
from typing import Any


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


def _validate_positive_integer(value: object, field_name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"{field_name} must be an integer.")

    if value <= 0:
        raise ValueError(f"{field_name} must be greater than zero.")

    return value


def _distribute_exact(
    total: int,
    entities: list[tuple[str, int]],
) -> dict[str, int]:
    """Distribute total proportionally while preserving an exact total."""
    if total <= 0 or not entities:
        return {entity: 0 for entity, _ in entities}

    weight_total = sum(max(weight, 0) for _, weight in entities)

    if weight_total == 0:
        weights = {entity: 1 for entity, _ in entities}
        weight_total = len(entities)
    else:
        weights = {
            entity: max(weight, 0)
            for entity, weight in entities
        }

    allocations: dict[str, int] = {}
    remainders: list[tuple[float, str]] = []
    assigned = 0

    for entity, _ in entities:
        exact = total * weights[entity] / weight_total
        base = int(exact)

        allocations[entity] = base
        assigned += base
        remainders.append((exact - base, entity))

    remaining = total - assigned

    for _, entity in sorted(
        remainders,
        key=lambda item: (-item[0], item[1]),
    )[:remaining]:
        allocations[entity] += 1

    return allocations


def _build_children_by_entity(
    relationships: list[dict[str, Any]],
) -> dict[str, set[str]]:
    children: dict[str, set[str]] = {}

    for relationship in relationships:
        source = relationship["source"].split(".", 1)[0]
        target = relationship["target"].split(".", 1)[0]

        children.setdefault(source, set()).add(target)

    return children


def _find_affected_entities(
    driver: str,
    relationships: list[dict[str, Any]],
) -> set[str]:
    """Return the driver and all entities downstream from it."""
    children = _build_children_by_entity(relationships)

    affected: set[str] = set()
    queue: deque[str] = deque([driver])

    while queue:
        entity = queue.popleft()

        if entity in affected:
            continue

        affected.add(entity)

        for child in sorted(children.get(entity, set())):
            if child not in affected:
                queue.append(child)

    return affected


def allocate_population_target(
    specification: dict[str, Any],
    target: int,
    driver: str,
) -> PopulationAllocation:
    """
    Allocate a dataset target using an explicit population driver.

    The driver and entities structurally downstream from it form the
    driver's scaling domain.

    FIXED entities remain unchanged.

    Unrelated entities retain their current populations.

    Within the driver's scalable domain, current populations are used as
    baseline weights so the existing structural shape is preserved while
    the domain grows to satisfy the requested dataset target.

    The candidate is subsequently evaluated by the existing 023 planner.
    """
    target = _validate_positive_integer(target, "target")

    if not isinstance(driver, str) or not driver.strip():
        raise ValueError("driver must be a non-empty entity name.")

    driver = driver.strip()

    entities = specification.get("entities", [])
    relationships = specification.get("relationships", [])

    entity_names = {
        entity["name"]
        for entity in entities
    }

    if driver not in entity_names:
        raise ValueError(
            f"Population driver '{driver}' does not exist in the specification."
        )

    affected_entities = _find_affected_entities(
        driver=driver,
        relationships=relationships,
    )

    population_by_entity: dict[str, int] = {}
    scaling_by_entity: dict[str, str] = {}

    for entity in entities:
        name = entity["name"]
        population = entity.get("population") or {}

        count = population.get("count")
        if count is None:
            count = 0

        if isinstance(count, bool) or not isinstance(count, int):
            raise ValueError(
                f"Population count for '{name}' must be an integer."
            )

        if count < 0:
            raise ValueError(
                f"Population count for '{name}' cannot be negative."
            )

        population_by_entity[name] = count
        scaling_by_entity[name] = population.get(
            "scaling",
            "SCALABLE",
        )

    if scaling_by_entity[driver] == "FIXED":
        return PopulationAllocation(
            target=target,
            driver=driver,
            populations=population_by_entity,
            fixed_total=sum(
                count
                for name, count in population_by_entity.items()
                if scaling_by_entity[name] == "FIXED"
            ),
            unaffected_total=0,
            scalable_total=0,
            allocated_total=sum(population_by_entity.values()),
            affected_entities=tuple(sorted(affected_entities)),
            feasible_target=False,
            reason=(
                f"Population driver '{driver}' is FIXED. "
                "A FIXED entity cannot be used as the population driver."
            ),
        )

    fixed_total = sum(
        count
        for name, count in population_by_entity.items()
        if scaling_by_entity[name] == "FIXED"
    )

    unaffected_entities = {
        name
        for name in entity_names
        if name not in affected_entities
    }

    unaffected_total = sum(
        population_by_entity[name]
        for name in unaffected_entities
    )

    fixed_in_affected = {
        name
        for name in affected_entities
        if scaling_by_entity[name] == "FIXED"
    }

    fixed_affected_total = sum(
        population_by_entity[name]
        for name in fixed_in_affected
    )

    baseline_total = (
        unaffected_total
        + fixed_affected_total
    )

    remaining_target = target - baseline_total

    populations = dict(population_by_entity)

    if remaining_target < 0:
        return PopulationAllocation(
            target=target,
            driver=driver,
            populations=populations,
            fixed_total=fixed_total,
            unaffected_total=unaffected_total,
            scalable_total=0,
            allocated_total=sum(populations.values()),
            affected_entities=tuple(sorted(affected_entities)),
            feasible_target=False,
            reason=(
                f"Target {target:,} is smaller than the "
                f"{baseline_total:,} records that cannot be reduced "
                "by the selected population driver."
            ),
        )

    scalable_affected = [
        (name, population_by_entity[name])
        for name in sorted(affected_entities)
        if scaling_by_entity[name] == "SCALABLE"
    ]

    if not scalable_affected:
        feasible = baseline_total == target

        return PopulationAllocation(
            target=target,
            driver=driver,
            populations=populations,
            fixed_total=fixed_total,
            unaffected_total=unaffected_total,
            scalable_total=0,
            allocated_total=sum(populations.values()),
            affected_entities=tuple(sorted(affected_entities)),
            feasible_target=feasible,
            reason=(
                None
                if feasible
                else (
                    f"Target {target:,} cannot be reached because the "
                    "selected driver has no scalable population domain."
                )
            ),
        )

    allocations = _distribute_exact(
        remaining_target,
        scalable_affected,
    )

    populations.update(allocations)

    allocated_total = sum(populations.values())

    return PopulationAllocation(
        target=target,
        driver=driver,
        populations=populations,
        fixed_total=fixed_total,
        unaffected_total=unaffected_total,
        scalable_total=remaining_target,
        allocated_total=allocated_total,
        affected_entities=tuple(sorted(affected_entities)),
        feasible_target=allocated_total == target,
        reason=None,
    )
