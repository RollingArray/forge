"""Deterministic integer allocation for entity populations."""

from dataclasses import dataclass
from typing import Mapping


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


def _distribute_residual(
    residual: int,
    allocations: dict[str, int],
    maximums: Mapping[str, int | None],
    priorities: Mapping[str, int],
) -> None:
    """Raise final populations toward a common level, respecting caps."""

    del priorities  # Equal final populations are the default policy.

    remaining = residual

    while remaining > 0:
        active = [
            name
            for name, count in allocations.items()
            if maximums.get(name) is None
            or count < maximums[name]
        ]

        if not active:
            break

        lowest = min(allocations[name] for name in active)
        lowest_group = sorted(
            name for name in active
            if allocations[name] == lowest
        )

        next_level = min(
            (
                allocations[name]
                for name in active
                if allocations[name] > lowest
            ),
            default=None,
        )

        next_cap = min(
            (
                maximums[name]
                for name in lowest_group
                if maximums.get(name) is not None
            ),
            default=None,
        )

        boundaries = [
            value for value in (next_level, next_cap)
            if value is not None
        ]

        if boundaries:
            distance = min(boundaries) - lowest
        else:
            distance = max(1, remaining // len(lowest_group))

        if distance <= 0:
            break

        cost = distance * len(lowest_group)

        if cost <= remaining:
            for name in lowest_group:
                allocations[name] += distance
            remaining -= cost
            continue

        full_rounds, extra = divmod(
            remaining, len(lowest_group)
        )

        for name in lowest_group:
            allocations[name] += full_rounds

        for name in lowest_group[:extra]:
            allocations[name] += 1

        remaining = 0


def allocate_integer_populations(
    *,
    target: int,
    minimums: Mapping[str, int],
    maximums: Mapping[str, int | None] | None = None,
    fixed: Mapping[str, int] | None = None,
    priorities: Mapping[str, int] | None = None,
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

    _distribute_residual(
        residual=residual,
        allocations=scalable_allocations,
        maximums=normalized_maximums,
        priorities=normalized_priorities,
    )

    allocations.update(scalable_allocations)

    allocated_total = sum(allocations.values())

    feasible = allocated_total == target

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
                f"Only {allocated_total:,} of {target:,} requested "
                "records could be allocated within the supplied capacities."
            )
        ),
    )
