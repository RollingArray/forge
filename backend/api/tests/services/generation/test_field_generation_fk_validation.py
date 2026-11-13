import pytest

from app.services.generation_planner import (
    GenerationPlanner,
    GenerationPlanningError,
)


def make_planner_fk_spec(source_field):
    return {
        "entities": [
            {
                "name": "PARENT",
                "fields": [
                    {
                        "name": "PARENT_ID",
                        "type": "IDENTIFIER",
                        "identity": {"strategy": "SEQUENTIAL_ID"},
                    },
                    {
                        "name": "PARENT_CODE",
                        "type": "STRING",
                        "generation": {
                            "strategy": "RANDOM",
                            "generator": "RANDOM_STRING",
                            "parameters": {
                                "minimum_length": 2,
                                "maximum_length": 12,
                                "character_set": "ALPHANUMERIC",
                            },
                        },
                    },
                ],
            },
            {
                "name": "CHILD",
                "fields": [source_field],
            },
        ],
        "foreign_keys": [
            {
                "name": "FK_CHILD_PARENT",
                "source": {
                    "entity": "CHILD",
                    "fields": [source_field["name"]],
                },
                "target": {
                    "entity": "PARENT",
                    "fields": [
                        "PARENT_ID"
                        if source_field["type"] == "IDENTIFIER"
                        else "PARENT_CODE"
                    ],
                },
            }
        ],
    }


def test_planner_fk_source_string_does_not_require_scalar_generation():
    specification = make_planner_fk_spec(
        {"name": "PARENT_CODE_FK", "type": "STRING"}
    )

    GenerationPlanner().validate_generation_configuration(specification)


def test_planner_fk_source_identifier_still_requires_sequential_id():
    specification = make_planner_fk_spec(
        {"name": "PARENT_ID_FK", "type": "IDENTIFIER"}
    )

    with pytest.raises(
        GenerationPlanningError,
        match="IDENTIFIER requires SEQUENTIAL_ID",
    ):
        GenerationPlanner().validate_generation_configuration(specification)


def test_planner_fk_source_still_rejects_malformed_generation_structure():
    specification = make_planner_fk_spec(
        {
            "name": "PARENT_CODE_FK",
            "type": "STRING",
            "generation": {"parameters": []},
        }
    )

    with pytest.raises(
        GenerationPlanningError,
        match="parameters must be an object",
    ):
        GenerationPlanner().validate_generation_configuration(specification)


def test_non_fk_string_still_requires_scalar_generation():
    specification = make_planner_fk_spec(
        {"name": "PARENT_CODE_FK", "type": "STRING"}
    )
    specification["foreign_keys"] = []

    with pytest.raises(
        GenerationPlanningError,
        match="STRING requires generation.strategy RANDOM",
    ):
        GenerationPlanner().validate_generation_configuration(specification)
