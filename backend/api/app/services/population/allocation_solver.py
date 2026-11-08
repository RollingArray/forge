"""Bounded-time, deterministic population allocation with constraint closure.

The fairness policy is a deterministic approximation to weighted max-min
fairness over normalized populations (population / priority). Hard population
constraints and exact-target verification take precedence over fairness.
"""

from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
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
    status: str = "UNRESOLVED"


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


def _compile_population_constraints(constraints: Sequence[object]) -> tuple[tuple, ...]:
    return tuple(
        (
            getattr(item, "kind", None),
            getattr(item, "entity", None),
            tuple(getattr(item, "related_entities", ())),
            getattr(item, "multiplier", 1),
        )
        for item in constraints
    )


def _constraint_violations(
    populations: Mapping[str, int], constraints: Sequence[object]
) -> list[str]:
    """Independently verify every supported population-level constraint."""
    violations: list[str] = []
    for kind, entity, related, multiplier in _compile_population_constraints(constraints):
        if entity not in populations:
            violations.append(f"Constraint references unknown entity {entity!r}.")
            continue
        value = populations[entity]
        if kind == "PARENT_REQUIRED_FOR_POSITIVE_CHILD":
            if value > 0:
                for parent in related:
                    if parent not in populations or populations[parent] <= 0:
                        violations.append(f"{entity} requires a positive {parent} population.")
        elif kind == "CHILD_AT_LEAST_PARENT":
            if related and (related[0] not in populations or value < populations[related[0]]):
                violations.append(f"{entity} must have at least as many rows as {related[0]}.")
        elif kind == "CHILD_AT_MOST_PARENT":
            if related and (related[0] not in populations or value > populations[related[0]]):
                violations.append(f"{entity} cannot exceed the population of {related[0]}.")
        elif kind == "IDENTITY_CAPACITY":
            if isinstance(multiplier, bool) or not isinstance(multiplier, int) or multiplier < 0:
                violations.append(f"{entity} has an invalid identity-capacity multiplier.")
                continue
            if any(parent not in populations for parent in related):
                violations.append(f"{entity} identity capacity references an unknown parent.")
                continue
            capacity = multiplier * prod(populations[parent] for parent in related)
            if value > capacity:
                violations.append(
                    f"{entity} exceeds its derived identity capacity of {capacity:,}."
                )
        else:
            violations.append(f"Unsupported population constraint kind: {kind}.")
    return violations


_INFEASIBLE_REPAIR = object()


def _identity_parent_repair(
    *,
    child_value: int,
    related: tuple[str, ...],
    multiplier: int,
    candidate: dict[str, int],
    scalable: set[str],
    maximums: Mapping[str, int | None],
    budget: int,
) -> dict[str, int] | None | object:
    """Find a low-cost integer parent-keyspace repair within ``budget``.

    Repeated parents remain repeated through their exponent. The common
    enterprise case has one or two distinct parent keyspaces; the general
    bounded water-fill below handles additional dimensions deterministically.
    """
    if multiplier < 0:
        return _INFEASIBLE_REPAIR
    if not related:
        return _INFEASIBLE_REPAIR if child_value > multiplier else dict(candidate)
    multiplicities: dict[str, int] = {}
    for parent in related:
        if parent not in candidate:
            return None
        multiplicities[parent] = multiplicities.get(parent, 0) + 1

    adjustable = [name for name in sorted(multiplicities) if name in scalable]
    if not adjustable:
        capacity = multiplier * prod(candidate[name] ** exponent for name, exponent in multiplicities.items())
        return _INFEASIBLE_REPAIR if child_value > capacity else dict(candidate)

    fixed_factor = multiplier
    for name, exponent in multiplicities.items():
        if name not in adjustable:
            fixed_factor *= candidate[name] ** exponent
    if fixed_factor <= 0:
        return _INFEASIBLE_REPAIR

    def capacity_after(additions: int) -> tuple[int, dict[str, int]]:
        """Approximate the maximum Cartesian product for a fixed cost in O(d)."""
        values = {name: candidate[name] for name in adjustable}
        if additions <= 0:
            capacity = fixed_factor
            for name in adjustable:
                capacity *= values[name] ** multiplicities[name]
            return capacity, values

        # Continuous optimum for product maximization under a sum budget:
        # each uncapped dimension approaches population / exponent = lambda.
        # Bisection is logarithmic in numeric range and independent of rows.
        upper = max(
            Fraction(
                maximums[name]
                if maximums.get(name) is not None
                else candidate[name] + additions,
                multiplicities[name],
            )
            for name in adjustable
        ) + additions + 1
        lower = Fraction(0, 1)
        for _ in range(72):
            level = (lower + upper) / 2
            used = 0
            for name in adjustable:
                wanted = max(candidate[name], int(level * multiplicities[name]))
                maximum = maximums.get(name)
                if maximum is not None:
                    wanted = min(wanted, maximum)
                used += wanted - candidate[name]
            if used <= additions:
                lower = level
            else:
                upper = level

        used = 0
        for name in adjustable:
            wanted = max(candidate[name], int(lower * multiplicities[name]))
            maximum = maximums.get(name)
            if maximum is not None:
                wanted = min(wanted, maximum)
            values[name] = wanted
            used += wanted - candidate[name]

        # At most one rounding unit per distinct dimension is normally left.
        # Spend any remaining budget using exact marginal-product comparisons.
        remaining = additions - used
        while remaining > 0:
            choices: list[tuple[int, int, str]] = []
            for name in adjustable:
                maximum = maximums.get(name)
                if maximum is not None and values[name] >= maximum:
                    continue
                exponent = multiplicities[name]
                choices.append(((values[name] + 1) ** exponent,
                                max(1, values[name]) ** exponent, name))
            if not choices:
                break
            selected = choices[0]
            for choice in choices[1:]:
                left = choice[0] * selected[1]
                right = selected[0] * choice[1]
                if left > right or (left == right and choice[2] < selected[2]):
                    selected = choice
            values[selected[2]] += 1
            remaining -= 1

        capacity = fixed_factor
        for name in adjustable:
            capacity *= values[name] ** multiplicities[name]
        return capacity, values

    current_capacity = multiplier * prod(candidate[name] ** exponent for name, exponent in multiplicities.items())
    if child_value <= current_capacity:
        return dict(candidate)

    # Determine whether the maximum bounded parent keyspace can ever suffice.
    maximum_values = dict(candidate)
    for name in adjustable:
        maximum = maximums.get(name)
        if maximum is None:
            maximum_values[name] = candidate[name] + budget
        else:
            maximum_values[name] = maximum
    maximum_capacity = multiplier * prod(
        maximum_values[name] ** exponent for name, exponent in multiplicities.items()
    )
    if maximum_capacity < child_value:
        return _INFEASIBLE_REPAIR

    low, high = 1, budget
    if high <= 0 or capacity_after(high)[0] < child_value:
        return None
    while low < high:
        middle = (low + high) // 2
        if capacity_after(middle)[0] >= child_value:
            high = middle
        else:
            low = middle + 1
    _, repaired = capacity_after(low)
    result = dict(candidate)
    result.update(repaired)
    return result


def _close_constraints(
    populations: Mapping[str, int],
    *,
    scalable_names: set[str],
    maximums: Mapping[str, int | None],
    constraints: tuple[tuple, ...],
    target: int,
) -> tuple[dict[str, int] | None, str | None]:
    """Apply monotonic constraint closure; never grows fixed populations."""
    result = dict(populations)
    max_passes = max(8, 4 * (len(constraints) + len(result) + 1))
    for _ in range(max_passes):
        changed = False
        for kind, entity, related, multiplier in constraints:
            if entity not in result or any(parent not in result for parent in related):
                return None, "UNRESOLVED: a constraint references an unknown entity."
            required: dict[str, int] = {}
            value = result[entity]
            if kind == "PARENT_REQUIRED_FOR_POSITIVE_CHILD":
                if value > 0:
                    required.update({parent: max(1, result[parent]) for parent in related})
            elif kind == "CHILD_AT_LEAST_PARENT":
                if related:
                    required[entity] = max(value, result[related[0]])
            elif kind == "CHILD_AT_MOST_PARENT":
                if related:
                    parent = related[0]
                    required[parent] = max(result[parent], value)
            elif kind == "IDENTITY_CAPACITY":
                if isinstance(multiplier, bool) or not isinstance(multiplier, int) or multiplier < 0:
                    return None, "UNRESOLVED: invalid identity-capacity multiplier."
                capacity = multiplier * prod(result[parent] for parent in related)
                if value > capacity:
                    repaired = _identity_parent_repair(
                        child_value=value,
                        related=related,
                        multiplier=multiplier,
                        candidate=result,
                        scalable=scalable_names,
                        maximums=maximums,
                        budget=max(0, target - sum(result.values())),
                    )
                    if repaired is _INFEASIBLE_REPAIR:
                        return None, "INFEASIBLE: maximum supported parent keyspaces cannot satisfy identity capacity."
                    if repaired is None:
                        return None, "UNRESOLVED: identity capacity cannot be repaired within the target and supported bounds."
                    if repaired != result:
                        result = repaired
                        changed = True
            else:
                return None, f"UNRESOLVED: unsupported population constraint kind {kind!r}."

            for name, wanted in required.items():
                if wanted <= result[name]:
                    continue
                if name not in scalable_names:
                    return None, f"INFEASIBLE: constraint requires increasing fixed entity {name}."
                maximum = maximums.get(name)
                if maximum is not None and wanted > maximum:
                    return None, f"INFEASIBLE: constraint requires {name}={wanted}, above maximum {maximum}."
                result[name] = wanted
                changed = True

            if sum(result.values()) > target:
                return None, "UNRESOLVED: constraint closure exceeds the remaining target budget."
        if not changed:
            return result, None
    return None, "UNRESOLVED: constraint closure exceeded its bounded propagation passes."


def _build_growth_candidate(
    seed: str,
    allocations: Mapping[str, int],
    maximums: Mapping[str, int | None],
    constraints: Sequence[object],
    fixed_populations: Mapping[str, int],
    max_added: int,
) -> dict[str, int] | None:
    """Compatibility helper: build one constraint-closed seed increment."""
    if seed not in allocations or max_added <= 0:
        return None
    base = dict(fixed_populations)
    base.update(allocations)
    maximum = maximums.get(seed)
    if maximum is not None and base[seed] >= maximum:
        return None
    proposed = dict(base)
    proposed[seed] += 1
    closed, reason = _close_constraints(
        proposed,
        scalable_names=set(allocations),
        maximums=maximums,
        constraints=_compile_population_constraints(constraints),
        target=sum(base.values()) + max_added,
    )
    if closed is None or reason is not None:
        return None
    if sum(closed.values()) - sum(base.values()) > max_added:
        return None
    return closed


def _waterline_candidate(
    base: Mapping[str, int],
    level: int,
    *,
    priorities: Mapping[str, int],
    maximums: Mapping[str, int | None],
    scalable_names: set[str],
    constraints: tuple[tuple, ...],
    target: int,
) -> dict[str, int] | None:
    proposed = dict(base)
    for name in sorted(scalable_names):
        wanted = level * priorities[name]
        maximum = maximums.get(name)
        if maximum is not None:
            wanted = min(wanted, maximum)
        proposed[name] = max(proposed[name], wanted)
    closed, reason = _close_constraints(
        proposed,
        scalable_names=scalable_names,
        maximums=maximums,
        constraints=constraints,
        target=target,
    )
    if closed is None or reason is not None or sum(closed.values()) > target:
        return None
    return closed


def allocate_integer_populations(
    *,
    target: int,
    minimums: Mapping[str, int],
    maximums: Mapping[str, int | None] | None = None,
    fixed: Mapping[str, int] | None = None,
    priorities: Mapping[str, int] | None = None,
    constraints: Sequence[object] = (),
) -> AllocationResult:
    """Allocate an exact target with bounded closure and weighted fairness."""
    target = _validate_count(target, "target")
    maximums = maximums or {}
    fixed = fixed or {}
    priorities = priorities or {}
    constraints = tuple(constraints)
    compiled = _compile_population_constraints(constraints)

    _validate_names(minimums, "minimums")
    _validate_names(maximums, "maximums")
    _validate_names(fixed, "fixed")
    _validate_names(priorities, "priorities")

    overlap = set(minimums) & set(fixed)
    if overlap:
        raise ValueError("Entities cannot be both scalable and fixed: " + ", ".join(sorted(overlap)))
    unknown_maximums = set(maximums) - set(minimums)
    if unknown_maximums:
        raise ValueError("Maximums supplied for unknown scalable entities: " + ", ".join(sorted(unknown_maximums)))
    unknown_priorities = set(priorities) - set(minimums)
    if unknown_priorities:
        raise ValueError("Priorities supplied for unknown scalable entities: " + ", ".join(sorted(unknown_priorities)))

    normalized_maximums: dict[str, int | None] = {}
    normalized_priorities: dict[str, int] = {}
    for name, minimum in minimums.items():
        _validate_count(minimum, f"minimum for '{name}'")
        maximum = maximums.get(name)
        if maximum is not None:
            maximum = _validate_count(maximum, f"maximum for '{name}'")
            if maximum < minimum:
                raise ValueError(f"Maximum for '{name}' is below its minimum.")
        normalized_maximums[name] = maximum
        priority = priorities.get(name, 1)
        if isinstance(priority, bool) or not isinstance(priority, int) or priority <= 0:
            raise ValueError(f"Priority for '{name}' must be a positive integer.")
        normalized_priorities[name] = priority
    for name, value in fixed.items():
        _validate_count(value, f"fixed population for '{name}'")

    minimum_total = sum(fixed.values()) + sum(minimums.values())
    finite_maximum_total = sum(fixed.values())
    unbounded = False
    for name, maximum in normalized_maximums.items():
        if maximum is None:
            unbounded = True
        else:
            finite_maximum_total += maximum
    maximum_total = None if unbounded else finite_maximum_total

    initial = dict(fixed)
    initial.update(minimums)
    if target < minimum_total:
        return AllocationResult(target, initial, minimum_total, minimum_total, maximum_total, False,
                                f"Target {target:,} is below the minimum required population of {minimum_total:,}.", "INFEASIBLE")
    if maximum_total is not None and target > maximum_total:
        capped = dict(fixed)
        capped.update({name: maximum for name, maximum in normalized_maximums.items()})
        return AllocationResult(target, capped, sum(capped.values()), minimum_total, maximum_total, False,
                                f"Target {target:,} exceeds the maximum supported population of {maximum_total:,}.", "INFEASIBLE")

    scalable_names = set(minimums)
    closed, closure_reason = _close_constraints(
        initial,
        scalable_names=scalable_names,
        maximums=normalized_maximums,
        constraints=compiled,
        target=target,
    )
    if closed is None:
        status = "INFEASIBLE" if closure_reason and closure_reason.startswith("INFEASIBLE:") else "UNRESOLVED"
        return AllocationResult(target, initial, sum(initial.values()), minimum_total, maximum_total, False,
                                closure_reason, status)
    if sum(closed.values()) > target:
        return AllocationResult(target, closed, sum(closed.values()), minimum_total, maximum_total, False,
                                "Minimum constraint closure exceeds the requested target.", "INFEASIBLE")

    # Integer normalized waterline. Binary search is logarithmic in target;
    # each candidate performs bounded constraint propagation.
    low, high = 0, target + 1
    best = closed
    while low + 1 < high:
        middle = (low + high) // 2
        candidate = _waterline_candidate(
            closed, middle, priorities=normalized_priorities,
            maximums=normalized_maximums, scalable_names=scalable_names,
            constraints=compiled, target=target,
        )
        if candidate is not None and sum(candidate.values()) <= target:
            low = middle
            best = candidate
        else:
            high = middle

    current = dict(best)
    remaining = target - sum(current.values())
    # The waterline leaves a bounded rounding tail in ordinary use. A hard
    # operation cap prevents pathological priority inputs from creating a
    # row-by-row runtime proportional to the requested dataset size.
    max_tail_steps = min(
        4_096,
        max(256, 8 * len(scalable_names) + 4 * len(compiled)),
    )
    steps = 0
    while remaining > 0 and steps < max_tail_steps:
        steps += 1
        moves: list[tuple[Fraction, int, str, dict[str, int], int]] = []
        for name in sorted(scalable_names):
            maximum = normalized_maximums.get(name)
            if maximum is not None and current[name] >= maximum:
                continue
            proposed = dict(current)
            proposed[name] += 1
            candidate, reason = _close_constraints(
                proposed,
                scalable_names=scalable_names,
                maximums=normalized_maximums,
                constraints=compiled,
                target=target,
            )
            if candidate is None or reason is not None:
                continue
            cost = sum(candidate.values()) - sum(current.values())
            if 0 < cost <= remaining:
                moves.append((Fraction(current[name], normalized_priorities[name]),
                              -normalized_priorities[name], name, candidate, cost))
        if not moves:
            break
        _, _, _, selected, cost = min(moves, key=lambda item: (item[0], item[1], item[2]))
        current = selected
        remaining -= cost

    allocated_total = sum(current.values())
    violations = _constraint_violations(current, constraints)
    fixed_changed = any(current.get(name) != value for name, value in fixed.items())
    bounds_violated = any(
        current.get(name, 0) < minimums[name]
        or (normalized_maximums[name] is not None and current.get(name, 0) > normalized_maximums[name])
        for name in minimums
    )
    exact = allocated_total == target
    if exact and not violations and not fixed_changed and not bounds_violated:
        return AllocationResult(target, current, allocated_total, minimum_total, maximum_total, True, None, "FEASIBLE")

    reason = (
        f"The bounded allocator established {allocated_total:,} of {target:,} requested rows. "
        "It could not establish an exact valid allocation within its bounded fairness tail."
    )
    if violations:
        reason += " " + " ".join(violations)
    if steps >= max_tail_steps and remaining > 0:
        reason += " The bounded residual-step budget was exhausted."
    return AllocationResult(target, current, allocated_total, minimum_total, maximum_total, False, reason, "UNRESOLVED")
