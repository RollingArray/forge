from copy import deepcopy

import pytest

from app.services.specification_defaults import (
    apply_specification_defaults,
)


@pytest.mark.parametrize(
    "population",
    [
        None,
        {},
        {"count": None},
    ],
)
def test_missing_population_count_defaults_to_100(population):
    specification = {
        "entities": [
            {
                "name": "SUPPLIER",
                "population": population,
            }
        ]
    }

    result, assumptions = apply_specification_defaults(specification)

    assert result["entities"][0]["population"]["count"] == 100
    assert result["entities"][0]["population"]["scaling"] == "SCALABLE"
    assert len(assumptions) == 2
    assert "assumptions" not in result
    assert specification["entities"][0]["population"] == population


@pytest.mark.parametrize("count", [0, 1, 100, 5000])
def test_explicit_population_count_is_preserved(count):
    specification = {
        "entities": [
            {
                "name": "SUPPLIER",
                "population": {
                    "count": count,
                    "scaling": "FIXED",
                },
            }
        ]
    }

    result, assumptions = apply_specification_defaults(specification)

    assert result["entities"][0]["population"] == {
        "count": count,
        "scaling": "FIXED",
    }
    assert assumptions == []


def test_existing_assumptions_are_preserved_without_duplicates():
    existing = "Existing authoring assumption."
    default_assumption = (
        "FORGE default applied: entity SUPPLIER population.count = 100; "
        "the user did not specify a count."
    )
    specification = {
        "entities": [
            {
                "name": "SUPPLIER",
                "population": {"count": None},
            }
        ]
    }

    result, assumptions = apply_specification_defaults(
        specification,
        [existing, default_assumption],
    )

    assert assumptions.count(existing) == 1
    assert assumptions.count(default_assumption) == 1
    assert result["entities"][0]["population"]["count"] == 100


def test_defaulting_does_not_mutate_input_specification():
    specification = {
        "entities": [
            {"name": "SUPPLIER"},
        ]
    }
    original = deepcopy(specification)

    apply_specification_defaults(specification)

    assert specification == original


def test_non_dictionary_entities_are_ignored():
    specification = {
        "entities": [
            None,
            "invalid",
            {"name": "SUPPLIER"},
        ]
    }

    result, assumptions = apply_specification_defaults(specification)

    assert result["entities"][0] is None
    assert result["entities"][1] == "invalid"
    assert result["entities"][2]["population"]["count"] == 100
    assert len(assumptions) == 2
