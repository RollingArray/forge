from types import SimpleNamespace

from app.services.population.allocation_solver import (
    _build_growth_candidate,
    allocate_integer_populations,
)


def _constraint(kind: str, entity: str, related: str):
    return SimpleNamespace(
        kind=kind,
        entity=entity,
        related_entities=(related,),
        multiplier=1,
    )


def test_allocation_supports_coordinated_one_to_one_increments() -> None:
    constraints = [
        _constraint(
            "CHILD_AT_LEAST_PARENT",
            "EMPLOYEE_PROFILE",
            "EMPLOYEE",
        ),
        _constraint(
            "CHILD_AT_MOST_PARENT",
            "EMPLOYEE_PROFILE",
            "EMPLOYEE",
        ),
    ]

    result = allocate_integer_populations(
        target=4,
        minimums={
            "EMPLOYEE": 1,
            "EMPLOYEE_PROFILE": 1,
        },
        constraints=constraints,
    )

    assert result.feasible
    assert result.allocated_total == 4
    assert result.populations == {
        "EMPLOYEE": 2,
        "EMPLOYEE_PROFILE": 2,
    }


def test_coordinated_and_independent_entities_can_grow_together() -> None:
    constraints = [
        _constraint(
            "CHILD_AT_LEAST_PARENT",
            "EMPLOYEE_PROFILE",
            "EMPLOYEE",
        ),
        _constraint(
            "CHILD_AT_MOST_PARENT",
            "EMPLOYEE_PROFILE",
            "EMPLOYEE",
        ),
        _constraint(
            "PARENT_REQUIRED_FOR_POSITIVE_CHILD",
            "ASSET",
            "EMPLOYEE",
        ),
    ]

    result = allocate_integer_populations(
        target=6,
        minimums={
            "EMPLOYEE": 1,
            "EMPLOYEE_PROFILE": 1,
            "ASSET": 1,
        },
        constraints=constraints,
    )

    assert result.feasible
    assert result.allocated_total == 6
    assert result.populations == {
        "EMPLOYEE": 2,
        "EMPLOYEE_PROFILE": 2,
        "ASSET": 2,
    }


def test_one_to_many_does_not_force_equal_populations() -> None:
    constraints = [
        _constraint(
            "CHILD_AT_LEAST_PARENT",
            "CHILD",
            "PARENT",
        ),
    ]

    result = allocate_integer_populations(
        target=5,
        minimums={"PARENT": 1, "CHILD": 1},
        constraints=constraints,
    )

    assert result.feasible
    assert result.allocated_total == 5
    assert result.populations == {"PARENT": 2, "CHILD": 3}
    assert result.populations["CHILD"] > result.populations["PARENT"]


def test_fixed_parent_is_never_changed_during_coordinated_growth() -> None:
    constraints = [
        _constraint(
            "CHILD_AT_LEAST_PARENT",
            "CHILD",
            "PARENT",
        ),
    ]

    result = allocate_integer_populations(
        target=3,
        minimums={"CHILD": 1},
        fixed={"PARENT": 1},
        constraints=constraints,
    )

    assert result.feasible
    assert result.allocated_total == 3
    assert result.populations == {"PARENT": 1, "CHILD": 2}


def test_maximum_population_is_respected() -> None:
    result = allocate_integer_populations(
        target=3,
        minimums={"ENTITY": 1},
        maximums={"ENTITY": 2},
    )

    assert not result.feasible
    assert result.allocated_total == 2
    assert result.populations == {"ENTITY": 2}


def test_identity_capacity_is_never_exceeded() -> None:
    constraints = [
        _constraint(
            "IDENTITY_CAPACITY",
            "CHILD",
            "PARENT",
        ),
    ]

    result = allocate_integer_populations(
        target=3,
        minimums={"CHILD": 1},
        fixed={"PARENT": 1},
        constraints=constraints,
    )

    assert not result.feasible
    assert result.allocated_total == 2
    assert result.populations == {"PARENT": 1, "CHILD": 1}


def test_coordinated_growth_works_with_unrelated_fixed_population() -> None:
    constraints = [
        _constraint(
            "CHILD_AT_LEAST_PARENT",
            "EMPLOYEE_PROFILE",
            "EMPLOYEE",
        ),
        _constraint(
            "CHILD_AT_MOST_PARENT",
            "EMPLOYEE_PROFILE",
            "EMPLOYEE",
        ),
    ]

    result = allocate_integer_populations(
        target=14,
        minimums={
            "EMPLOYEE": 1,
            "EMPLOYEE_PROFILE": 1,
        },
        fixed={"ARCHIVE": 10},
        constraints=constraints,
    )

    assert result.feasible
    assert result.allocated_total == 14
    assert result.populations == {
        "ARCHIVE": 10,
        "EMPLOYEE": 2,
        "EMPLOYEE_PROFILE": 2,
    }


def test_individual_maximum_is_respected_with_an_unbounded_entity() -> None:
    result = allocate_integer_populations(
        target=3,
        minimums={
            "CAPPED": 1,
            "UNBOUNDED": 1,
        },
        maximums={"CAPPED": 1},
    )

    assert result.feasible
    assert result.allocated_total == 3
    assert result.populations == {
        "CAPPED": 1,
        "UNBOUNDED": 2,
    }


def test_identity_capacity_is_checked_after_constraint_repairs() -> None:
    constraints = [
        _constraint(
            "IDENTITY_CAPACITY",
            "CHILD",
            "PARENT",
        ),
        _constraint(
            "CHILD_AT_MOST_PARENT",
            "CHILD",
            "PARENT",
        ),
    ]

    result = allocate_integer_populations(
        target=4,
        minimums={
            "CHILD": 1,
            "PARENT": 1,
        },
        constraints=constraints,
    )

    assert result.feasible
    assert result.allocated_total == 4
    assert result.populations == {
        "CHILD": 2,
        "PARENT": 2,
    }



def test_identity_capacity_is_checked_after_coordinated_parent_repair() -> None:
    constraints = [
        _constraint(
            "IDENTITY_CAPACITY",
            "CHILD",
            "PARENT",
        ),
        _constraint(
            "CHILD_AT_MOST_PARENT",
            "CHILD",
            "PARENT",
        ),
    ]

    candidate = _build_growth_candidate(
        seed="CHILD",
        allocations={
            "CHILD": 1,
            "PARENT": 1,
        },
        maximums={
            "CHILD": None,
            "PARENT": None,
        },
        constraints=constraints,
        fixed_populations={},
        max_added=2,
    )

    assert candidate == {
        "CHILD": 2,
        "PARENT": 2,
    }


def test_coordinated_move_is_rejected_when_remaining_target_is_too_small() -> None:
    constraints = [
        _constraint(
            "CHILD_AT_LEAST_PARENT",
            "PROFILE",
            "EMPLOYEE",
        ),
        _constraint(
            "CHILD_AT_MOST_PARENT",
            "PROFILE",
            "EMPLOYEE",
        ),
    ]

    result = allocate_integer_populations(
        target=3,
        minimums={"EMPLOYEE": 1, "PROFILE": 1},
        constraints=constraints,
    )

    assert not result.feasible
    assert result.allocated_total == 2
    assert result.populations == {"EMPLOYEE": 1, "PROFILE": 1}


def test_coordinated_move_fits_exact_remaining_target() -> None:
    constraints = [
        _constraint(
            "CHILD_AT_LEAST_PARENT",
            "PROFILE",
            "EMPLOYEE",
        ),
        _constraint(
            "CHILD_AT_MOST_PARENT",
            "PROFILE",
            "EMPLOYEE",
        ),
    ]

    result = allocate_integer_populations(
        target=4,
        minimums={"EMPLOYEE": 1, "PROFILE": 1},
        constraints=constraints,
    )

    assert result.feasible
    assert result.allocated_total == 4
    assert result.populations == {"EMPLOYEE": 2, "PROFILE": 2}


def test_allocation_is_deterministic_for_repeated_runs() -> None:
    constraints = [
        _constraint(
            "CHILD_AT_LEAST_PARENT",
            "PROFILE",
            "EMPLOYEE",
        ),
        _constraint(
            "CHILD_AT_MOST_PARENT",
            "PROFILE",
            "EMPLOYEE",
        ),
    ]

    arguments = {
        "target": 100,
        "minimums": {
            "EMPLOYEE": 1,
            "PROFILE": 1,
            "ASSET": 1,
            "PROJECT": 1,
        },
        "priorities": {
            "EMPLOYEE": 2,
            "PROFILE": 2,
            "ASSET": 1,
            "PROJECT": 1,
        },
        "constraints": constraints,
    }

    first = allocate_integer_populations(**arguments)
    second = allocate_integer_populations(**arguments)

    assert first.feasible
    assert second.feasible
    assert first.populations == second.populations
    assert first.allocated_total == second.allocated_total == 100
