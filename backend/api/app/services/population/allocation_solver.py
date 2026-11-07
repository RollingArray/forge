"""Deterministic integer allocation for entity populations."""

from dataclasses import dataclass
from math import prod
from typing import Mapping, Sequence


@dataclass(frozen=True)
class AllocationResult:
    target: int
    populations: dict[str, int]
    allocated_total: int
    minimum_total: int
    maximum_total: int | None
    feasible: bool
    reason: str | None = None


def _validate_count(value: object, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"{name} must be an integer.")
    if value < 0:
        raise ValueError(f"{name} cannot be negative.")
    return value


def _validate_names(names: Mapping[str, object], label: str) -> None:
    for name in names:
        if not isinstance(name, str) or not name.strip():
            raise ValueError(f"{label} contains an invalid entity name.")


def _constraint_violations(
    populations: Mapping[str, int],
    constraints: Sequence[object],
) -> list[str]:
    """Return violations of the supported population-level constraints."""

    violations: list[str] = []

    for constraint in constraints:
        kind = getattr(constraint, "kind", None)
        entity = getattr(constraint, "entity", None)
        related = tuple(getattr(constraint, "related_entities", ()))
        value = populations.get(entity, 0)

        if kind == "PARENT_REQUIRED_FOR_POSITIVE_CHILD":
            if value > 0:
                for parent in related:
                    if populations.get(parent, 0) <= 0:
                        violations.append(
                            f"{entity} requires a positive {parent} population."
                        )

        elif kind == "CHILD_AT_LEAST_PARENT":
            if related and value < populations.get(related[0], 0):
                violations.append(
                    f"{entity} must have at least as many rows as {related[0]}."
                )

        elif kind == "CHILD_AT_MOST_PARENT":
            if related and value > populations.get(related[0], 0):
                violations.append(
                    f"{entity} cannot exceed the population of {related[0]}."
                )

        elif kind == "IDENTITY_CAPACITY":
            capacity = getattr(constraint, "multiplier", 1) * prod(
                populations.get(parent, 0) for parent in related
            )
            if value > capacity:
                violations.append(
                    f"{entity} exceeds its derived identity capacity of {capacity:,}."
                )

        else:
            violations.append(
                f"Unsupported population constraint kind: {kind}."
            )

    return violations


def _build_growth_candidate(
    seed: str,
    allocations: Mapping[str, int],
    maximums: Mapping[str, int | None],
    constraints: Sequence[object],
    fixed_populations: Mapping[str, int],
    max_added: int,
) -> dict[str, int] | None:
    """Build the smallest monotonic coordinated move for one growth seed."""

    candidate = dict(fixed_populations)
    candidate.update(allocations)
    initial_total = sum(candidate.values())

    if seed not in allocations:
        return None

    seed_maximum = maximums.get(seed)
    if seed_maximum is not None and allocations[seed] >= seed_maximum:
        return None

    candidate[seed] += 1

    def increase(name: str, value: int) -> bool:
        if name not in allocations:
            return False

        maximum = maximums.get(name)
        if maximum is not None and value > maximum:
            return False

        candidate[name] = max(candidate[name], value)

        added = sum(candidate.values()) - initial_total
        return added <= max_added

    # Constraint repair is monotonic. Revisit constraints until all
    # population inequalities are satisfied.
    while True:
        changed = False

        for constraint in constraints:
            kind = getattr(constraint, "kind", None)
            entity = getattr(constraint, "entity", None)
            related = tuple(
                getattr(constraint, "related_entities", ())
            )

            if entity not in candidate:
                return None

            value = candidate[entity]

            if kind == "PARENT_REQUIRED_FOR_POSITIVE_CHILD":
                if value > 0:
                    for parent in related:
                        if parent not in candidate:
                            return None
                        if candidate[parent] <= 0:
                            if not increase(parent, 1):
                                return None
                            changed = True

            elif kind == "CHILD_AT_LEAST_PARENT":
                if related:
                    parent = related[0]
                    if parent not in candidate:
                        return None
                    required = candidate[parent]
                    if value < required:
                        if not increase(entity, required):
                            return None
                        changed = True

            elif kind == "CHILD_AT_MOST_PARENT":
                if related:
                    parent = related[0]
                    if parent not in candidate:
                        return None
                    required = candidate[entity]
                    if candidate[parent] < required:
                        if not increase(parent, required):
                            return None
                        changed = True

            elif kind == "IDENTITY_CAPACITY":
                # Validate capacity after all other population repairs.
                # A coordinated move may increase the required parent
                # keyspace later in this same candidate.
                continue

            else:
                return None

        added = sum(candidate.values()) - initial_total

        if added > max_added:
            return None

        if not changed:
            break

    if _constraint_violations(candidate, constraints):
        return None

    return candidate


def _distribute_residual(
    residual: int,
    allocations: dict[str, int],
    maximums: Mapping[str, int | None],
    priorities: Mapping[str, int],
    constraints: Sequence[object],
    fixed_populations: Mapping[str, int],
) -> int:
    """
    Distribute residual records through constraint-aware growth moves.

    Each move may increment multiple scalable entities to preserve
    population constraints. Feasible moves are selected using weighted
    fairness based on the initiating entity's current allocation.
    """

    remaining = residual

    while remaining > 0:
        feasible_moves: list[
            tuple[float, int, str, dict[str, int], int]
        ] = []

        for name in allocations:
            candidate = _build_growth_candidate(
                seed=name,
                allocations=allocations,
                maximums=maximums,
                constraints=constraints,
                fixed_populations=fixed_populations,
                max_added=remaining,
            )

            if candidate is None:
                continue

            added = sum(candidate.values()) - sum(
                fixed_populations.values()
            ) - sum(allocations.values())

            if added <= 0 or added > remaining:
                continue

            priority = priorities[name]
            feasible_moves.append(
                (
                    allocations[name] / priority,
                    -priority,
                    name,
                    candidate,
                    added,
                )
            )

        if not feasible_moves:
            break

        _, _, _, selected, added = min(
            feasible_moves,
            key=lambda item: (item[0], item[1], item[2]),
        )

        for name in allocations:
            allocations[name] = selected[name]

        remaining -= added

    return remaining


def allocate_integer_populations(
    *,
    target: int,
    minimums: Mapping[str, int],
    maximums: Mapping[str, int | None] | None = None,
    fixed: Mapping[str, int] | None = None,
    priorities: Mapping[str, int] | None = None,
    constraints: Sequence[object] = (),
) -> AllocationResult:
    """
    Allocate an exact dataset target across fixed and scalable entities.

    Scalable entities start at their minimum populations. Residual records
    are distributed equally by default, or proportionally to positive
    integer priorities when supplied.

    Existing population counts are deliberately not accepted as weights.
    """

    target = _validate_count(target, "target")
    maximums = maximums or {}
    fixed = fixed or {}
    priorities = priorities or {}
    constraints = tuple(constraints)

    _validate_names(minimums, "minimums")
    _validate_names(maximums, "maximums")
    _validate_names(fixed, "fixed")
    _validate_names(priorities, "priorities")

    overlap = set(minimums) & set(fixed)
    if overlap:
        raise ValueError(
            "Entities cannot be both scalable and fixed: "
            + ", ".join(sorted(overlap))
        )

    unknown_maximums = set(maximums) - set(minimums)
    if unknown_maximums:
        raise ValueError(
            "Maximums supplied for unknown scalable entities: "
            + ", ".join(sorted(unknown_maximums))
        )

    unknown_priorities = set(priorities) - set(minimums)
    if unknown_priorities:
        raise ValueError(
            "Priorities supplied for unknown scalable entities: "
            + ", ".join(sorted(unknown_priorities))
        )

    for name, value in minimums.items():
        _validate_count(value, f"minimum for '{name}'")

    for name, value in fixed.items():
        _validate_count(value, f"fixed population for '{name}'")

    normalized_maximums: dict[str, int | None] = {}

    for name in minimums:
        maximum = maximums.get(name)
        if maximum is not None:
            maximum = _validate_count(maximum, f"maximum for '{name}'")
            if maximum < minimums[name]:
                raise ValueError(
                    f"Maximum for '{name}' is below its minimum."
                )
        normalized_maximums[name] = maximum

    normalized_priorities: dict[str, int] = {}

    for name in minimums:
        priority = priorities.get(name, 1)
        if (
            isinstance(priority, bool)
            or not isinstance(priority, int)
            or priority <= 0
        ):
            raise ValueError(
                f"Priority for '{name}' must be a positive integer."
            )
        normalized_priorities[name] = priority

    minimum_total = sum(fixed.values()) + sum(minimums.values())

    finite_maximum_total = sum(fixed.values())
    has_unbounded_entity = False

    for name, maximum in normalized_maximums.items():
        if maximum is None:
            has_unbounded_entity = True
        else:
            finite_maximum_total += maximum

    maximum_total = (
        None if has_unbounded_entity else finite_maximum_total
    )

    allocations = dict(fixed)
    allocations.update(minimums)

    if target < minimum_total:
        return AllocationResult(
            target=target,
            populations=allocations,
            allocated_total=sum(allocations.values()),
            minimum_total=minimum_total,
            maximum_total=maximum_total,
            feasible=False,
            reason=(
                f"Target {target:,} is below the minimum required "
                f"population of {minimum_total:,}."
            ),
        )

    if maximum_total is not None and target > maximum_total:
        for name, maximum in normalized_maximums.items():
            allocations[name] = maximum

        return AllocationResult(
            target=target,
            populations=allocations,
            allocated_total=sum(allocations.values()),
            minimum_total=minimum_total,
            maximum_total=maximum_total,
            feasible=False,
            reason=(
                f"Target {target:,} exceeds the maximum supported "
                f"population of {maximum_total:,}."
            ),
        )

    residual = target - minimum_total

    scalable_allocations = {
        name: allocations[name]
        for name in minimums
    }

    initial_violations = _constraint_violations(
        allocations,
        constraints,
    )

    if initial_violations:
        return AllocationResult(
            target=target,
            populations=allocations,
            allocated_total=sum(allocations.values()),
            minimum_total=minimum_total,
            maximum_total=maximum_total,
            feasible=False,
            reason=(
                "The minimum population allocation already violates "
                "supported population constraints: "
                + " ".join(initial_violations)
            ),
        )

    remaining = _distribute_residual(
        residual=residual,
        allocations=scalable_allocations,
        maximums=normalized_maximums,
        priorities=normalized_priorities,
        constraints=constraints,
        fixed_populations=fixed,
    )

    allocations.update(scalable_allocations)

    allocated_total = sum(allocations.values())

    feasible = remaining == 0 and allocated_total == target

    return AllocationResult(
        target=target,
        populations=allocations,
        allocated_total=allocated_total,
        minimum_total=minimum_total,
        maximum_total=maximum_total,
        feasible=feasible,
        reason=(
            None
            if feasible
            else (
                f"Only {allocated_total:,} of {target:,} requested records "
                "could be allocated without violating supported population "
                "constraints or derived capacities."
            )
        ),
    )
