from copy import deepcopy

import pytest

from app.services.population.allocator import allocate_population_target


def _entity(
    name: str,
    identity: str,
    foreign_key_fields: tuple[str, ...] = (),
) -> dict:
    field_names = (identity, *foreign_key_fields)

    return {
        "name": name,
        "fields": [
            {
                "name": field_name,
                "type": "IDENTIFIER",
                "identity": {"strategy": "SEQUENTIAL_ID"},
            }
            for field_name in field_names
        ],
        "identity": {"fields": [identity]},
        "population": {"count": 1, "scaling": "SCALABLE"},
    }


def _fk(name: str, child: str, child_field: str, parent: str, parent_field: str):
    return {
        "name": name,
        "source": {"entity": child, "fields": [child_field]},
        "target": {"entity": parent, "fields": [parent_field]},
    }


def _relationship(
    source: str,
    source_field: str,
    target: str,
    target_field: str,
    relationship_type: str,
    source_participation: str = "MANDATORY",
    target_participation: str = "MANDATORY",
) -> dict:
    return {
        "source": {"entity": source, "fields": [source_field]},
        "target": {"entity": target, "fields": [target_field]},
        "type": relationship_type,
        "source_participation": source_participation,
        "target_participation": target_participation,
    }


@pytest.fixture
def five_entity_specification() -> dict:
    return {
        "entities": [
            _entity("DEPARTMENT", "department_UID"),
            _entity("EMPLOYEE", "employee_UID", ("department_UID", "project_UID")),
            _entity("EMPLOYEE_PROFILE", "profile_UID", ("employee_UID",)),
            _entity("ASSET", "asset_UID", ("employee_UID",)),
            _entity("PROJECT", "project_UID"),
        ],
        "foreign_keys": [
            _fk(
                "FK_EMPLOYEE_DEPARTMENT",
                "EMPLOYEE",
                "department_UID",
                "DEPARTMENT",
                "department_UID",
            ),
            _fk(
                "FK_EMPLOYEE_PROFILE_EMPLOYEE",
                "EMPLOYEE_PROFILE",
                "employee_UID",
                "EMPLOYEE",
                "employee_UID",
            ),
            _fk(
                "FK_ASSET_EMPLOYEE",
                "ASSET",
                "employee_UID",
                "EMPLOYEE",
                "employee_UID",
            ),
            _fk(
                "FK_EMPLOYEE_PROJECT",
                "EMPLOYEE",
                "project_UID",
                "PROJECT",
                "project_UID",
            ),
        ],
        "relationships": [
            _relationship(
                "DEPARTMENT",
                "department_UID",
                "EMPLOYEE",
                "department_UID",
                "ONE_TO_MANY",
            ),
            _relationship(
                "EMPLOYEE",
                "employee_UID",
                "EMPLOYEE_PROFILE",
                "employee_UID",
                "ONE_TO_ONE",
            ),
            _relationship(
                "ASSET",
                "employee_UID",
                "EMPLOYEE",
                "employee_UID",
                "MANY_TO_ONE",
                target_participation="OPTIONAL",
            ),
            _relationship(
                "PROJECT",
                "project_UID",
                "EMPLOYEE",
                "project_UID",
                "ONE_TO_MANY",
            ),
        ],
    }


@pytest.mark.parametrize(
    ("driver", "expected"),
    [
        (
            "DEPARTMENT",
            {
                "ASSET": 12_500,
                "DEPARTMENT": 25_000,
                "EMPLOYEE": 25_000,
                "EMPLOYEE_PROFILE": 25_000,
                "PROJECT": 12_500,
            },
        ),
        (
            "EMPLOYEE",
            {
                "ASSET": 14_286,
                "DEPARTMENT": 14_286,
                "EMPLOYEE": 28_571,
                "EMPLOYEE_PROFILE": 28_571,
                "PROJECT": 14_286,
            },
        ),
        (
            "EMPLOYEE_PROFILE",
            {
                "ASSET": 14_286,
                "DEPARTMENT": 14_286,
                "EMPLOYEE": 28_571,
                "EMPLOYEE_PROFILE": 28_571,
                "PROJECT": 14_286,
            },
        ),
        (
            "ASSET",
            {
                "ASSET": 33_333,
                "DEPARTMENT": 16_667,
                "EMPLOYEE": 16_667,
                "EMPLOYEE_PROFILE": 16_667,
                "PROJECT": 16_666,
            },
        ),
        (
            "PROJECT",
            {
                "ASSET": 12_500,
                "DEPARTMENT": 12_500,
                "EMPLOYEE": 25_000,
                "EMPLOYEE_PROFILE": 25_000,
                "PROJECT": 25_000,
            },
        ),
    ],
)
def test_five_entity_model_allocates_exact_target_for_each_driver(
    five_entity_specification: dict,
    driver: str,
    expected: dict[str, int],
) -> None:
    result = allocate_population_target(
        specification=deepcopy(five_entity_specification),
        target=100_000,
        driver=driver,
    )

    assert result.status == "FEASIBLE"
    assert result.feasible_target
    assert result.allocated_total == 100_000
    assert result.populations == expected

    # The mandatory one-to-one relationship must remain equal.
    assert result.populations["EMPLOYEE_PROFILE"] == result.populations["EMPLOYEE"]

    # Mandatory parent participation requires both parents to cover employees.
    assert result.populations["EMPLOYEE"] >= result.populations["DEPARTMENT"]
    assert result.populations["EMPLOYEE"] >= result.populations["PROJECT"]


def test_five_entity_allocation_is_deterministic(
    five_entity_specification: dict,
) -> None:
    first = allocate_population_target(
        specification=deepcopy(five_entity_specification),
        target=100_000,
        driver="EMPLOYEE",
    )
    second = allocate_population_target(
        specification=deepcopy(five_entity_specification),
        target=100_000,
        driver="EMPLOYEE",
    )

    assert first.status == second.status == "FEASIBLE"
    assert first.populations == second.populations
    assert first.allocated_total == second.allocated_total == 100_000


def test_exact_minimum_target_is_feasible(
    five_entity_specification: dict,
) -> None:
    result = allocate_population_target(
        specification=five_entity_specification,
        target=5,
        driver="EMPLOYEE",
    )

    assert result.status == "FEASIBLE"
    assert result.feasible_target
    assert result.allocated_total == 5
    assert result.populations == {
        "ASSET": 1,
        "DEPARTMENT": 1,
        "EMPLOYEE": 1,
        "EMPLOYEE_PROFILE": 1,
        "PROJECT": 1,
    }


def test_target_can_be_met_by_independent_entity_growth(
    five_entity_specification: dict,
) -> None:
    result = allocate_population_target(
        specification=five_entity_specification,
        target=6,
        driver="EMPLOYEE",
    )

    assert result.status == "FEASIBLE"
    assert result.feasible_target
    assert result.allocated_total == 6
    assert sum(result.populations.values()) == 6
    assert result.populations["EMPLOYEE"] == 1
    assert result.populations["EMPLOYEE_PROFILE"] == 1
    assert result.populations["ASSET"] == 2
