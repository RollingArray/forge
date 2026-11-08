from types import SimpleNamespace

from app.services.population.allocation_solver import allocate_integer_populations


def _constraint(kind: str, entity: str, *related: str, multiplier: int = 1):
    return SimpleNamespace(
        kind=kind,
        entity=entity,
        related_entities=tuple(related),
        multiplier=multiplier,
    )


def test_weighted_normalized_populations_are_fair_and_deterministic() -> None:
    arguments = {
        "target": 100_003,
        "minimums": {"A": 1, "B": 1, "C": 1},
        "priorities": {"A": 2, "B": 1, "C": 1},
    }

    first = allocate_integer_populations(**arguments)
    second = allocate_integer_populations(**arguments)

    assert first.status == "FEASIBLE"
    assert first.feasible
    assert first.allocated_total == 100_003
    assert first.populations == second.populations
    normalized = [
        first.populations["A"] / 2,
        first.populations["B"],
        first.populations["C"],
    ]
    assert max(normalized) - min(normalized) <= 1


def test_odd_one_to_one_target_is_unresolved_not_infeasible() -> None:
    constraints = [
        _constraint("CHILD_AT_LEAST_PARENT", "CHILD", "PARENT"),
        _constraint("CHILD_AT_MOST_PARENT", "CHILD", "PARENT"),
    ]

    result = allocate_integer_populations(
        target=3,
        minimums={"CHILD": 1, "PARENT": 1},
        constraints=constraints,
    )

    assert not result.feasible
    assert result.status == "UNRESOLVED"
    assert result.allocated_total == 2
    assert result.populations == {"CHILD": 1, "PARENT": 1}


def test_target_below_derived_minimum_is_proven_infeasible() -> None:
    result = allocate_integer_populations(
        target=1,
        minimums={"A": 1, "B": 1},
    )

    assert not result.feasible
    assert result.status == "INFEASIBLE"


def test_five_million_target_is_allocated_exactly_in_bulk() -> None:
    names = [f"ENTITY_{index:02d}" for index in range(39)]
    constraints = [
        _constraint("PARENT_REQUIRED_FOR_POSITIVE_CHILD", name, "BUSINESS_UNIT")
        for name in names
    ]

    result = allocate_integer_populations(
        target=5_000_000,
        minimums={name: 1 for name in names},
        fixed={"BUSINESS_UNIT": 4},
        constraints=constraints,
    )

    assert result.status == "FEASIBLE"
    assert result.feasible
    assert result.allocated_total == 5_000_000
    assert sum(result.populations.values()) == 5_000_000
    assert all(result.populations[name] >= 1 for name in names)
