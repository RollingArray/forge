import pytest

from app.services.generation_planner import (
    GenerationPlanner,
    GenerationPlanningError,
)


def _specification(field_type, constraint_value):
    field = {
        "name": "PRICE",
        "type": field_type,
        "generation": {
            "strategy": "RANDOM",
            "distribution": (
                "UNIFORM" if field_type == "DECIMAL" else "DISCRETE_UNIFORM"
            ),
            "parameters": (
                {"minimum": "0", "maximum": "1"}
                if field_type == "DECIMAL"
                else {"minimum": 0, "maximum": 10}
            ),
        },
    }

    return {
        "entities": [
            {
                "name": "PRODUCT",
                "population": {"count": 1},
                "fields": [field],
            }
        ],
        "constraints": [
            {
                "entity": "PRODUCT",
                "field": "PRICE",
                "operator": ">",
                "value": constraint_value,
            }
        ],
    }


@pytest.mark.parametrize(
    "value",
    [
        "0.100000000000000001",
        "999999999999999999999999999999.123456789",
        "0.000000000000000000000000000001",
        "-12345678901234567890.123400",
        "1e10000",
    ],
)
def test_planner_accepts_exact_decimal_constraint_strings(value):
    plan = GenerationPlanner().build(
        _specification("DECIMAL", value)
    )

    assert len(plan.constraints) == 1
    assert plan.constraints[0].value == value
    assert isinstance(plan.constraints[0].value, str)


@pytest.mark.parametrize("value", [0.1, 1, True, None])
def test_planner_rejects_non_string_decimal_constraint_values(value):
    with pytest.raises(
        GenerationPlanningError,
        match="comparison value must be a valid decimal",
    ):
        GenerationPlanner().build(
            _specification("DECIMAL", value)
        )


@pytest.mark.parametrize(
    "value",
    ["NaN", "Infinity", "-Infinity", "not-a-decimal"],
)
def test_planner_rejects_invalid_or_non_finite_decimal_strings(value):
    with pytest.raises(
        GenerationPlanningError,
        match="comparison value must be a valid decimal",
    ):
        GenerationPlanner().build(
            _specification("DECIMAL", value)
        )


def test_planner_preserves_existing_integer_constraint_behavior():
    plan = GenerationPlanner().build(
        _specification("INTEGER", 10)
    )

    assert plan.constraints[0].value == 10


def test_planner_rejects_fractional_integer_constraint():
    with pytest.raises(
        GenerationPlanningError,
        match="comparison value must be a valid integer",
    ):
        GenerationPlanner().build(
            _specification("INTEGER", 10.5)
        )
