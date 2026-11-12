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


def _multi_component_identity_specification(
    parent_names: tuple[str, ...],
    child_population: int,
) -> dict:
    """Build a child identity from independent FK components."""

    entities = [
        _entity(name, f"{name}_ID")
        for name in dict.fromkeys(parent_names)
    ]

    child_fields = tuple(
        f"PARENT_{index}_ID"
        for index in range(len(parent_names))
    )

    child = {
        "name": "CHILD",
        "fields": [
            {
                "name": field_name,
                "type": "IDENTIFIER",
                "identity": {"strategy": "SEQUENTIAL_ID"},
            }
            for field_name in child_fields
        ],
        "identity": {"fields": list(child_fields)},
        "population": {
            "count": child_population,
            "scaling": "FIXED",
        },
    }

    entities.append(child)

    foreign_keys = [
        _fk(
            f"FK_CHILD_PARENT_{index}",
            "CHILD",
            child_field,
            parent_name,
            f"{parent_name}_ID",
        )
        for index, (child_field, parent_name) in enumerate(
            zip(child_fields, parent_names),
            start=1,
        )
    ]

    return {
        "entities": entities,
        "foreign_keys": foreign_keys,
        "relationships": [],
    }


def test_identity_capacity_preserves_repeated_parent_components() -> None:
    from app.services.population.constraint_analysis import (
        analyze_specification_constraints,
    )

    specification = _multi_component_identity_specification(
        ("PARENT", "PARENT"),
        child_population=50,
    )

    analysis = analyze_specification_constraints(specification)

    assert analysis.structurally_valid
    assert analysis.allocation_supported

    child_capacity = next(
        item
        for item in analysis.identity_capacities
        if item.entity == "CHILD"
    )

    assert child_capacity.parent_entities == ("PARENT", "PARENT")

    identity_constraint = next(
        item
        for item in analysis.population_constraints
        if item.kind == "IDENTITY_CAPACITY"
        and item.entity == "CHILD"
    )

    assert identity_constraint.related_entities == ("PARENT", "PARENT")


def test_two_independent_same_parent_fks_allow_cartesian_identity_capacity() -> None:
    from app.services.population.allocator import _constraint_violations
    from app.services.population.constraint_analysis import (
        analyze_specification_constraints,
    )

    specification = _multi_component_identity_specification(
        ("PARENT", "PARENT"),
        child_population=50,
    )

    analysis = analyze_specification_constraints(specification)

    violations = _constraint_violations(
        {"PARENT": 10, "CHILD": 50},
        analysis.population_constraints,
    )

    assert violations == []


def test_two_independent_parent_fks_allow_product_of_parent_keyspaces() -> None:
    from app.services.population.allocator import _constraint_violations
    from app.services.population.constraint_analysis import (
        analyze_specification_constraints,
    )

    specification = _multi_component_identity_specification(
        ("PARENT_A", "PARENT_B"),
        child_population=50,
    )

    analysis = analyze_specification_constraints(specification)

    violations = _constraint_violations(
        {
            "PARENT_A": 10,
            "PARENT_B": 10,
            "CHILD": 50,
        },
        analysis.population_constraints,
    )

    assert violations == []


def test_standard_population_plan_uses_cartesian_identity_capacity() -> None:
    from app.services.population.adapter import build_plan_from_specification

    specification = _multi_component_identity_specification(
        ("PARENT", "PARENT"),
        child_population=50,
    )

    for entity in specification["entities"]:
        if entity["name"] == "PARENT":
            entity["population"] = {"count": 10, "scaling": "FIXED"}
        elif entity["name"] == "CHILD":
            entity["population"] = {"count": 50, "scaling": "FIXED"}

    plan = build_plan_from_specification(specification)

    assert plan.maximums.get("CHILD") == 100
    assert plan.populations["CHILD"].status.value == "FEASIBLE"


def test_standard_population_plan_requires_parent_key_for_positive_child() -> None:
    from app.services.population.adapter import build_plan_from_specification

    specification = _multi_component_identity_specification(
        ("PARENT", "PARENT"),
        child_population=5,
    )

    for entity in specification["entities"]:
        if entity["name"] == "PARENT":
            entity["population"] = {"count": 0, "scaling": "FIXED"}
        elif entity["name"] == "CHILD":
            entity["population"] = {"count": 5, "scaling": "FIXED"}

    plan = build_plan_from_specification(specification)

    assert plan.minimums["PARENT"] == 1
    assert plan.populations["PARENT"].status.value == "INFEASIBLE"


def test_standard_population_plan_leaves_auto_parent_capacity_unresolved() -> None:
    from app.services.population.adapter import build_plan_from_specification

    specification = _multi_component_identity_specification(
        ("PARENT", "PARENT"),
        child_population=5,
    )

    for entity in specification["entities"]:
        if entity["name"] == "PARENT":
            entity["population"] = {"count": None, "scaling": "SCALABLE"}
        elif entity["name"] == "CHILD":
            entity["population"] = {"count": 5, "scaling": "FIXED"}

    plan = build_plan_from_specification(specification)

    assert "CHILD" not in plan.maximums
    assert plan.minimums["PARENT"] == 1
    assert plan.populations["PARENT"].status.value == "AUTO"
    assert plan.populations["PARENT"].resolved == 1


def test_standard_population_plan_multiplies_finite_local_identity_capacity() -> None:
    from app.services.population.adapter import build_plan_from_specification

    specification = _multi_component_identity_specification(
        ("PARENT",),
        child_population=25,
    )

    parent = specification["entities"][0]
    parent["population"] = {"count": 10, "scaling": "FIXED"}

    child = specification["entities"][1]
    child["fields"].append({
        "name": "LOCAL_CODE",
        "type": "STRING",
        "generation": {
            "strategy": "RANDOM",
            "distribution": "CATEGORICAL",
            "parameters": {"values": ["A", "B", "C"]},
        },
    })
    child["identity"]["fields"].append("LOCAL_CODE")
    child["population"] = {"count": 25, "scaling": "FIXED"}

    plan = build_plan_from_specification(specification)

    assert plan.maximums["CHILD"] == 30
    assert plan.populations["CHILD"].status.value == "FEASIBLE"


def test_candidate_allocator_rejects_target_above_finite_local_identity_capacity() -> None:
    specification = _multi_component_identity_specification(
        ("PARENT",),
        child_population=25,
    )

    parent = specification["entities"][0]
    parent["population"] = {"count": 10, "scaling": "FIXED"}

    child = specification["entities"][1]
    child["fields"].append({
        "name": "LOCAL_CODE",
        "type": "STRING",
        "generation": {
            "strategy": "RANDOM",
            "distribution": "CATEGORICAL",
            "parameters": {"values": ["A", "B", "C"]},
        },
    })
    child["identity"]["fields"].append("LOCAL_CODE")
    child["population"] = {"count": 1, "scaling": "SCALABLE"}

    result = allocate_population_target(
        specification=specification,
        target=41,
        driver="CHILD",
    )

    assert result.status == "INFEASIBLE"
    assert not result.feasible_target
    assert "Derived maximum total: 40." in result.diagnostics


def test_standard_population_plan_does_not_cap_sequential_local_identity() -> None:
    from app.services.population.adapter import build_plan_from_specification

    specification = _multi_component_identity_specification(
        ("PARENT",),
        child_population=25,
    )

    parent = specification["entities"][0]
    parent["population"] = {"count": 10, "scaling": "FIXED"}

    child = specification["entities"][1]
    child["fields"].append({
        "name": "LOCAL_ID",
        "type": "IDENTIFIER",
        "identity": {"strategy": "SEQUENTIAL_ID"},
    })
    child["identity"]["fields"].append("LOCAL_ID")
    child["population"] = {"count": 25, "scaling": "FIXED"}

    plan = build_plan_from_specification(specification)

    assert "CHILD" not in plan.maximums
    assert plan.populations["CHILD"].status.value == "FEASIBLE"


def test_legacy_population_planner_path_remains_available() -> None:
    from app.services.population.adapter import (
        build_dependencies_by_entity,
        build_entities_metadata,
    )
    from app.services.population.planner import build_population_plan

    specification = _multi_component_identity_specification(
        ("PARENT",),
        child_population=5,
    )
    populations = {
        entity["name"]: entity["population"]
        for entity in specification["entities"]
    }

    plan = build_population_plan(
        populations=populations,
        relationships=[],
        dependencies_by_entity=build_dependencies_by_entity(specification),
        entities=build_entities_metadata(specification),
    )

    # Legacy metadata-only callers retain the old per-FK behavior.
    assert isinstance(plan.maximums, dict)
    assert isinstance(plan.capacity_requirements, list)
    assert isinstance(plan.capacity_limits, list)


def test_candidate_allocator_uses_cartesian_capacity_for_repeated_parent_fks() -> None:
    specification = _multi_component_identity_specification(
        ("PARENT", "PARENT"),
        child_population=50,
    )

    parent = next(
        entity for entity in specification["entities"]
        if entity["name"] == "PARENT"
    )
    parent["population"] = {"count": 1, "scaling": "SCALABLE"}

    result = allocate_population_target(
        specification=specification,
        target=60,
        driver="PARENT",
    )

    assert result.status == "FEASIBLE"
    assert result.feasible_target
    assert result.populations == {"CHILD": 50, "PARENT": 10}
    assert result.allocated_total == 60


def test_unrelated_unsupported_identity_does_not_suppress_supported_capacity() -> None:
    from app.services.population.adapter import build_plan_from_specification

    specification = _multi_component_identity_specification(
        ("PARENT", "PARENT"),
        child_population=50,
    )

    for entity in specification["entities"]:
        if entity["name"] == "PARENT":
            entity["population"] = {"count": 10, "scaling": "FIXED"}
        elif entity["name"] == "CHILD":
            entity["population"] = {"count": 50, "scaling": "FIXED"}

    unrelated = _entity("OTHER", "OTHER_ID")
    unrelated["fields"].append(
        {"name": "OTHER_CODE", "type": "STRING"}
    )
    unrelated["identity"] = {"fields": ["OTHER_ID", "OTHER_CODE"]}
    specification["entities"].append(unrelated)

    plan = build_plan_from_specification(specification)

    assert plan.maximums.get("CHILD") == 100

def test_unsupported_identity_returns_structural_diagnostics() -> None:
    specification = {
        "entities": [_entity("CUSTOMER", "CUSTOMER_ID")],
        "foreign_keys": [],
        "relationships": [],
    }

    customer = specification["entities"][0]
    customer["fields"].append(
        {"name": "CODE", "type": "STRING"}
    )
    customer["identity"] = {
        "fields": ["CUSTOMER_ID", "CODE"]
    }

    result = allocate_population_target(
        specification=specification,
        target=10,
        driver="CUSTOMER",
    )

    assert result.status == "UNRESOLVED"
    assert result.diagnostics
    assert any(
        "CODE" in diagnostic and "identity" in diagnostic.lower()
        for diagnostic in result.diagnostics
    )


def test_unsupported_many_to_many_returns_relationship_diagnostics() -> None:
    specification = {
        "entities": [
            _entity("CUSTOMER", "CUSTOMER_ID"),
            _entity("ORDER", "ORDER_ID"),
        ],
        "foreign_keys": [],
        "relationships": [
            _relationship(
                "CUSTOMER",
                "CUSTOMER_ID",
                "ORDER",
                "ORDER_ID",
                "MANY_TO_MANY",
            )
        ],
    }

    result = allocate_population_target(
        specification=specification,
        target=10,
        driver="CUSTOMER",
    )

    assert result.status == "UNRESOLVED"
    assert result.diagnostics
    assert any(
        "association" in diagnostic.lower()
        or "junction" in diagnostic.lower()
        or "many-to-many" in diagnostic.lower()
        for diagnostic in result.diagnostics
    )

