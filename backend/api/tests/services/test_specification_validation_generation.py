from copy import deepcopy

import pytest

from app.services.specification_validation_service import (
    SpecificationValidationService,
)


def make_specification(fields):
    return {
        "name": "Field Generation Validation Test",
        "version": "1.0",
        "vocabulary_version": "1.0",
        "model": {"name": "Field Generation Validation Test"},
        "generation": {"seed": 42},
        "entities": [
            {
                "name": "TEST_ENTITY",
                "fields": fields,
                "identity": {"fields": ["TEST_ID"]},
                "population": {"count": 10},
            }
        ],
        "relationships": [],
        "foreign_keys": [],
        "constraints": [],
    }


def test_canonical_validation_reports_missing_generation_configuration():
    specification = make_specification(
        [
            {
                "name": "TEST_ID",
                "type": "IDENTIFIER",
                "identity": {"strategy": "SEQUENTIAL_ID"},
            },
            {
                "name": "TEST_NAME",
                "type": "STRING",
            },
        ]
    )

    result = SpecificationValidationService().validate(specification)

    generation_errors = [
        finding
        for finding in result["findings"]
        if finding["category"] == "Generation"
        and finding["severity"] == "error"
    ]

    assert result["can_continue"] is False
    assert len(generation_errors) == 2
    assert {
        (finding["entity"], finding["field"])
        for finding in generation_errors
    } == {
        ("TEST_ENTITY", "TEST_NAME"),
        ("TEST_ENTITY", "TEST_ID"),
    } - {("TEST_ENTITY", "TEST_ID")}


def test_canonical_validation_reports_all_invalid_fields():
    specification = make_specification(
        [
            {
                "name": "TEST_ID",
                "type": "IDENTIFIER",
                "identity": {"strategy": "SEQUENTIAL_ID"},
            },
            {"name": "NAME", "type": "STRING"},
            {"name": "QUANTITY", "type": "INTEGER"},
            {"name": "ACTIVE", "type": "BOOLEAN"},
        ]
    )

    result = SpecificationValidationService().validate(specification)

    generation_errors = [
        finding
        for finding in result["findings"]
        if finding["category"] == "Generation"
        and finding["severity"] == "error"
    ]

    assert result["can_continue"] is False
    assert {
        finding["field"] for finding in generation_errors
    } == {"NAME", "QUANTITY", "ACTIVE"}
    assert result["errors"] >= len(generation_errors)


def test_canonical_validation_accepts_complete_field_generation_configuration():
    specification = make_specification(
        [
            {
                "name": "TEST_ID",
                "type": "IDENTIFIER",
                "identity": {"strategy": "SEQUENTIAL_ID"},
            },
            {
                "name": "NAME",
                "type": "STRING",
                "generation": {
                    "strategy": "RANDOM",
                    "generator": "RANDOM_STRING",
                    "parameters": {
                        "minimum_length": 3,
                        "maximum_length": 20,
                        "character_set": "ALPHANUMERIC",
                    },
                },
            },
            {
                "name": "QUANTITY",
                "type": "INTEGER",
                "generation": {
                    "strategy": "RANDOM",
                    "distribution": "UNIFORM",
                    "parameters": {"minimum": 1, "maximum": 100},
                },
            },
            {
                "name": "ACTIVE",
                "type": "BOOLEAN",
                "generation": {"strategy": "RANDOM"},
            },
        ]
    )

    result = SpecificationValidationService().validate(specification)

    generation_errors = [
        finding
        for finding in result["findings"]
        if finding["category"] == "Generation"
        and finding["severity"] == "error"
    ]

    assert generation_errors == []


def make_fk_specification(source_field):
    specification = make_specification(
        [
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
        ]
    )
    specification["entities"].append(
        {
            "name": "CHILD",
            "fields": [source_field],
            "population": {"count": 10},
        }
    )
    specification["foreign_keys"] = [
        {
            "name": "FK_CHILD_PARENT",
            "source": {"entity": "CHILD", "fields": [source_field["name"]]},
            "target": {"entity": "TEST_ENTITY", "fields": ["PARENT_CODE"]},
        }
    ]
    return specification


def test_canonical_fk_source_string_does_not_require_scalar_generation():
    specification = make_fk_specification(
        {"name": "PARENT_CODE_FK", "type": "STRING"}
    )
    specification["foreign_keys"][0]["target"]["fields"] = ["PARENT_CODE"]

    result = SpecificationValidationService().validate(specification)

    generation_errors = [
        finding
        for finding in result["findings"]
        if finding["category"] == "Generation"
        and finding["entity"] == "CHILD"
        and finding["field"] == "PARENT_CODE_FK"
    ]
    assert generation_errors == []


def test_canonical_fk_source_identifier_still_requires_sequential_id():
    specification = make_fk_specification(
        {"name": "PARENT_ID_FK", "type": "IDENTIFIER"}
    )
    specification["foreign_keys"][0]["target"]["fields"] = ["PARENT_ID"]

    result = SpecificationValidationService().validate(specification)

    assert any(
        finding["category"] == "Generation"
        and finding["entity"] == "CHILD"
        and finding["field"] == "PARENT_ID_FK"
        and "IDENTIFIER requires SEQUENTIAL_ID" in finding["details"]
        for finding in result["findings"]
    )


def test_canonical_fk_source_still_rejects_malformed_generation_structure():
    specification = make_fk_specification(
        {
            "name": "PARENT_CODE_FK",
            "type": "STRING",
            "generation": {"parameters": []},
        }
    )

    result = SpecificationValidationService().validate(specification)

    assert any(
        finding["category"] == "Generation"
        and finding["entity"] == "CHILD"
        and finding["field"] == "PARENT_CODE_FK"
        and "parameters must be an object" in finding["details"]
        for finding in result["findings"]
    )


def test_canonical_validation_reports_unsupported_field_type():
    specification = make_specification(
        [
            {
                "name": "TEST_ID",
                "type": "IDENTIFIER",
                "identity": {"strategy": "SEQUENTIAL_ID"},
            },
            {
                "name": "UNSUPPORTED_TYPE",
                "type": "MAGIC",
            },
        ]
    )

    result = SpecificationValidationService().validate(specification)

    findings = [
        finding
        for finding in result["findings"]
        if finding["entity"] == "TEST_ENTITY"
        and finding["field"] == "UNSUPPORTED_TYPE"
        and finding["title"] == "Unsupported field type"
    ]

    assert result["can_continue"] is False
    assert len(findings) == 1
    assert "MAGIC" in findings[0]["details"]


def make_constraint_specification(constraint):
    specification = make_specification(
        [
            {
                "name": "TEST_ID",
                "type": "IDENTIFIER",
                "identity": {"strategy": "SEQUENTIAL_ID"},
            },
            {
                "name": "TEST_NAME",
                "type": "STRING",
                "generation": {
                    "strategy": "RANDOM",
                    "generator": "RANDOM_STRING",
                    "parameters": {
                        "minimum_length": 3,
                        "maximum_length": 20,
                        "character_set": "ALPHANUMERIC",
                    },
                },
            },
            {
                "name": "TEST_QUANTITY",
                "type": "INTEGER",
                "generation": {
                    "strategy": "RANDOM",
                    "distribution": "UNIFORM",
                    "parameters": {"minimum": 1, "maximum": 100},
                },
            },
        ]
    )
    specification["constraints"] = [constraint]
    return specification


def get_constraint_finding(specification):
    result = SpecificationValidationService().validate(specification)
    findings = [
        finding
        for finding in result["findings"]
        if finding["category"] == "Constraint"
    ]
    assert len(findings) == 1
    return findings[0]


def test_constraint_diagnostic_identifies_unknown_entity():
    finding = get_constraint_finding(
        make_constraint_specification(
            {
                "entity": "UNKNOWN_ENTITY",
                "field": "TEST_NAME",
                "operator": "==",
                "value": "ABC",
            }
        )
    )

    assert finding["severity"] == "error"
    assert "entity" in finding["details"].lower()
    assert "UNKNOWN_ENTITY" in finding["details"]
    assert "does not exist" in finding["details"].lower()


def test_constraint_diagnostic_identifies_unknown_field():
    finding = get_constraint_finding(
        make_constraint_specification(
            {
                "entity": "TEST_ENTITY",
                "field": "UNKNOWN_FIELD",
                "operator": "==",
                "value": "ABC",
            }
        )
    )

    assert finding["severity"] == "error"
    assert "UNKNOWN_FIELD" in finding["details"]
    assert "field" in finding["details"].lower()
    assert "does not exist" in finding["details"].lower()


def test_constraint_diagnostic_identifies_unsupported_operator():
    finding = get_constraint_finding(
        make_constraint_specification(
            {
                "entity": "TEST_ENTITY",
                "field": "TEST_NAME",
                "operator": ">",
                "value": "ABC",
            }
        )
    )

    assert finding["severity"] == "error"
    assert ">" in finding["details"]
    assert "STRING" in finding["details"]
    assert "operator" in finding["details"].lower()
    assert "not supported" in finding["details"].lower()


def test_constraint_diagnostic_identifies_missing_comparison_value():
    finding = get_constraint_finding(
        make_constraint_specification(
            {
                "entity": "TEST_ENTITY",
                "field": "TEST_NAME",
                "operator": "==",
            }
        )
    )

    assert finding["severity"] == "error"
    assert "value" in finding["details"].lower()
    assert "required" in finding["details"].lower()


def test_constraint_diagnostic_preserves_invalid_integer_value_message():
    finding = get_constraint_finding(
        make_constraint_specification(
            {
                "entity": "TEST_ENTITY",
                "field": "TEST_QUANTITY",
                "operator": ">",
                "value": "NOT_AN_INTEGER",
            }
        )
    )

    assert finding["severity"] == "error"
    assert "valid integer" in finding["details"].lower()


def test_constraint_validation_accepts_valid_constraint():
    finding = get_constraint_finding(
        make_constraint_specification(
            {
                "entity": "TEST_ENTITY",
                "field": "TEST_QUANTITY",
                "operator": ">",
                "value": 10,
            }
        )
    )

    assert finding["severity"] == "passed"
    assert finding["title"] == "Constraint is valid"


def test_model_validation_does_not_validate_population_counts():
    specification = make_specification(
        [
            {
                "name": "TEST_ID",
                "type": "IDENTIFIER",
                "identity": {"strategy": "SEQUENTIAL_ID"},
            },
        ]
    )
    specification["entities"][0].pop("population")

    result = SpecificationValidationService().validate(specification)

    population_findings = [
        finding
        for finding in result["findings"]
        if "population" in (
            finding["title"] + " " + finding["details"]
        ).lower()
    ]

    assert population_findings == []


def test_malformed_constraint_entry_returns_error_instead_of_crashing():
    specification = make_constraint_specification(None)

    result = SpecificationValidationService().validate(specification)

    assert result["can_continue"] is False
    assert any(
        finding["category"] == "Constraint"
        and finding["severity"] == "error"
        and "must be an object" in finding["details"]
        for finding in result["findings"]
    )


def test_malformed_relationship_entry_returns_error_instead_of_crashing():
    specification = make_specification(
        [
            {
                "name": "TEST_ID",
                "type": "IDENTIFIER",
                "identity": {"strategy": "SEQUENTIAL_ID"},
            },
        ]
    )
    specification["relationships"] = [None]

    result = SpecificationValidationService().validate(specification)

    assert result["can_continue"] is False
    assert any(
        finding["category"] == "Relationship"
        and finding["severity"] == "error"
        and "must be an object" in finding["details"]
        for finding in result["findings"]
    )


def test_malformed_entity_and_field_entries_return_findings():
    specification = make_specification(
        [
            {
                "name": "TEST_ID",
                "type": "IDENTIFIER",
                "identity": {"strategy": "SEQUENTIAL_ID"},
            },
        ]
    )
    specification["entities"].append(None)
    specification["entities"][0]["fields"].append(None)

    result = SpecificationValidationService().validate(specification)

    assert result["can_continue"] is False
    assert any(
        finding["title"] == "Invalid entity definition"
        for finding in result["findings"]
    )
    assert any(
        finding["title"] == "Invalid field definition"
        for finding in result["findings"]
    )


def test_invalid_top_level_collection_returns_validation_finding():
    specification = make_specification(
        [
            {
                "name": "TEST_ID",
                "type": "IDENTIFIER",
                "identity": {"strategy": "SEQUENTIAL_ID"},
            },
        ]
    )
    specification["constraints"] = {"not": "a list"}

    result = SpecificationValidationService().validate(specification)

    assert result["can_continue"] is False
    assert any(
        finding["title"] == "Invalid constraint collection"
        for finding in result["findings"]
    )

def test_model_validation_blocks_unsupported_local_identity():
    specification = make_specification(
        [
            {
                "name": "TEST_ID",
                "type": "STRING",
                "generation": {
                    "strategy": "RANDOM",
                    "generator": "RANDOM_STRING",
                    "parameters": {
                        "minimum_length": 3,
                        "maximum_length": 12,
                        "character_set": "ALPHANUMERIC",
                    },
                },
            }
        ]
    )

    result = SpecificationValidationService().validate(specification)

    assert result["can_continue"] is False
    assert result["unsupported"] >= 1
    assert any(
        finding["severity"] == "unsupported"
        and finding["title"] == "Unsupported Local Identity"
        and finding["entity"] == "TEST_ENTITY"
        and finding["field"] == "TEST_ID"
        for finding in result["findings"]
    )


def test_model_validation_blocks_direct_many_to_many_relationship():
    specification = make_specification(
        [
            {
                "name": "TEST_ID",
                "type": "IDENTIFIER",
                "identity": {"strategy": "SEQUENTIAL_ID"},
            }
        ]
    )
    specification["entities"].append({
        "name": "CHILD",
        "fields": [
            {
                "name": "CHILD_ID",
                "type": "IDENTIFIER",
                "identity": {"strategy": "SEQUENTIAL_ID"},
            }
        ],
        "identity": {"fields": ["CHILD_ID"]},
        "population": {"count": 10},
    })
    specification["relationships"] = [
        {
            "source": "TEST_ENTITY.TEST_ID",
            "target": "CHILD.CHILD_ID",
            "type": "MANY_TO_MANY",
            "source_participation": "MANDATORY",
            "target_participation": "MANDATORY",
        }
    ]

    result = SpecificationValidationService().validate(specification)

    assert result["can_continue"] is False
    assert result["unsupported"] >= 1
    assert any(
        finding["severity"] == "unsupported"
        and finding["title"] == "Unsupported Many To Many"
        for finding in result["findings"]
    )


def test_model_validation_blocks_unmapped_relationship():
    specification = make_specification(
        [
            {
                "name": "TEST_ID",
                "type": "IDENTIFIER",
                "identity": {"strategy": "SEQUENTIAL_ID"},
            }
        ]
    )
    specification["entities"].append({
        "name": "CHILD",
        "fields": [
            {
                "name": "CHILD_ID",
                "type": "IDENTIFIER",
                "identity": {"strategy": "SEQUENTIAL_ID"},
            }
        ],
        "identity": {"fields": ["CHILD_ID"]},
        "population": {"count": 10},
    })
    specification["relationships"] = [
        {
            "source": "TEST_ENTITY.TEST_ID",
            "target": "CHILD.CHILD_ID",
            "type": "ONE_TO_MANY",
            "source_participation": "MANDATORY",
            "target_participation": "MANDATORY",
        }
    ]

    result = SpecificationValidationService().validate(specification)

    assert result["can_continue"] is False
    assert any(
        finding["severity"] == "error"
        and finding["category"] == "Relationship"
        and finding["title"] == "Relationship Fk Not Found"
        for finding in result["findings"]
    )
    assert result["unsupported"] == 0


def test_model_validation_blocks_foreign_key_dependency_cycle():
    specification = make_specification(
        [
            {
                "name": "A_ID",
                "type": "IDENTIFIER",
                "identity": {"strategy": "SEQUENTIAL_ID"},
            },
            {
                "name": "B_REF",
                "type": "IDENTIFIER",
                "identity": {"strategy": "SEQUENTIAL_ID"},
            },
        ]
    )
    specification["entities"] = [
        {
            "name": "A",
            "fields": [
                {
                    "name": "A_ID",
                    "type": "IDENTIFIER",
                    "identity": {"strategy": "SEQUENTIAL_ID"},
                },
                {
                    "name": "B_REF",
                    "type": "IDENTIFIER",
                    "identity": {"strategy": "SEQUENTIAL_ID"},
                },
            ],
            "identity": {"fields": ["A_ID"]},
            "population": {"count": 10},
        },
        {
            "name": "B",
            "fields": [
                {
                    "name": "B_ID",
                    "type": "IDENTIFIER",
                    "identity": {"strategy": "SEQUENTIAL_ID"},
                },
                {
                    "name": "A_REF",
                    "type": "IDENTIFIER",
                    "identity": {"strategy": "SEQUENTIAL_ID"},
                },
            ],
            "identity": {"fields": ["B_ID"]},
            "population": {"count": 10},
        },
    ]
    specification["foreign_keys"] = [
        {
            "name": "FK_A_B",
            "source": {"entity": "A", "fields": ["B_REF"]},
            "target": {"entity": "B", "fields": ["B_ID"]},
        },
        {
            "name": "FK_B_A",
            "source": {"entity": "B", "fields": ["A_REF"]},
            "target": {"entity": "A", "fields": ["A_ID"]},
        },
    ]

    result = SpecificationValidationService().validate(specification)

    assert result["can_continue"] is False
    assert any(
        finding["severity"] == "error"
        and finding["title"].lower() == "foreign-key dependency cycle detected"
        for finding in result["findings"]
    )


def test_model_validation_preserves_partial_composite_identity_fk_diagnostic():
    specification = make_specification([
        {
            "name": "CHILD_PARENT_REF",
            "type": "IDENTIFIER",
            "identity": {"strategy": "SEQUENTIAL_ID"},
        },
        {
            "name": "CHILD_ID",
            "type": "IDENTIFIER",
            "identity": {"strategy": "SEQUENTIAL_ID"},
        },
        {
            "name": "CHILD_OTHER_REF",
            "type": "IDENTIFIER",
            "identity": {"strategy": "SEQUENTIAL_ID"},
        },
    ])

    specification["entities"][0]["name"] = "CHILD"
    specification["entities"][0]["identity"] = {
        "fields": ["CHILD_PARENT_REF", "CHILD_ID"]
    }

    specification["entities"].append({
        "name": "PARENT",
        "fields": [
            {
                "name": "PARENT_ID_A",
                "type": "IDENTIFIER",
                "identity": {"strategy": "SEQUENTIAL_ID"},
            },
            {
                "name": "PARENT_ID_B",
                "type": "IDENTIFIER",
                "identity": {"strategy": "SEQUENTIAL_ID"},
            },
        ],
        "identity": {"fields": ["PARENT_ID_A", "PARENT_ID_B"]},
        "population": {"count": 10},
    })

    specification["foreign_keys"] = [{
        "name": "FK_CHILD_PARENT",
        "source": {
            "entity": "CHILD",
            "fields": ["CHILD_PARENT_REF", "CHILD_OTHER_REF"],
        },
        "target": {
            "entity": "PARENT",
            "fields": ["PARENT_ID_A", "PARENT_ID_B"],
        },
    }]

    result = SpecificationValidationService().validate(specification)

    assert any(
        finding["title"] == "Partial Composite Identity Fk"
        and finding["severity"] == "error"
        for finding in result["findings"]
    )


def test_model_validation_preserves_overlapping_identity_components_diagnostic():
    specification = make_specification([
        {
            "name": "PARENT_REF",
            "type": "IDENTIFIER",
            "identity": {"strategy": "SEQUENTIAL_ID"},
        },
    ])

    specification["entities"][0]["name"] = "CHILD"
    specification["entities"][0]["identity"] = {
        "fields": ["PARENT_REF"]
    }

    for parent_name, parent_id in (
        ("PARENT_A", "PARENT_A_ID"),
        ("PARENT_B", "PARENT_B_ID"),
    ):
        specification["entities"].append({
            "name": parent_name,
            "fields": [{
                "name": parent_id,
                "type": "IDENTIFIER",
                "identity": {"strategy": "SEQUENTIAL_ID"},
            }],
            "identity": {"fields": [parent_id]},
            "population": {"count": 10},
        })

    specification["foreign_keys"] = [
        {
            "name": "FK_CHILD_PARENT_A",
            "source": {
                "entity": "CHILD",
                "fields": ["PARENT_REF"],
            },
            "target": {
                "entity": "PARENT_A",
                "fields": ["PARENT_A_ID"],
            },
        },
        {
            "name": "FK_CHILD_PARENT_B",
            "source": {
                "entity": "CHILD",
                "fields": ["PARENT_REF"],
            },
            "target": {
                "entity": "PARENT_B",
                "fields": ["PARENT_B_ID"],
            },
        },
    ]

    result = SpecificationValidationService().validate(specification)

    titles = [finding["title"] for finding in result["findings"]]

    assert "Overlapping Identity Components" in titles
    assert "Overlapping source field assignments" in titles


def test_model_validation_capability_analysis_ignores_population_settings():
    specification = make_specification(
        [
            {
                "name": "TEST_ID",
                "type": "IDENTIFIER",
                "identity": {"strategy": "SEQUENTIAL_ID"},
            }
        ]
    )
    specification["entities"][0]["population"] = {
        "count": -100,
        "scaling": "INVALID_MODE",
    }

    result = SpecificationValidationService().validate(specification)

    assert not any(
        "population" in finding["title"].lower()
        or "scaling" in finding["title"].lower()
        for finding in result["findings"]
    )

def test_model_validation_reports_structural_and_capability_findings_together():
    specification = make_specification(
        [
            {
                "name": "TEST_ID",
                "type": "STRING",
                "generation": {
                    "strategy": "RANDOM",
                    "generator": "RANDOM_STRING",
                    "parameters": {
                        "minimum_length": 3,
                        "maximum_length": 12,
                        "character_set": "ALPHANUMERIC",
                    },
                },
            }
        ]
    )

    customer = specification["entities"][0]
    customer["name"] = "CUSTOMER"
    customer["fields"][0]["name"] = "CODE"
    customer["identity"]["fields"] = ["CODE"]

    specification["entities"].append({
        "name": "ORDER",
        "fields": [],
        "identity": {"fields": []},
        "population": {"count": 10, "scaling": "SCALABLE"},
    })

    result = SpecificationValidationService().validate(specification)

    assert result["can_continue"] is False

    assert any(
        finding["severity"] == "error"
        and finding["title"] == "Identity definition is missing"
        and finding["entity"] == "ORDER"
        for finding in result["findings"]
    )

    assert any(
        finding["severity"] == "unsupported"
        and finding["title"] == "Unsupported Local Identity"
        and finding["entity"] == "CUSTOMER"
        and finding["field"] == "CODE"
        for finding in result["findings"]
    )

    assert not any(
        finding.get("entity") == "CUSTOMER"
        and finding["title"] == "Identity Coverage Incomplete"
        for finding in result["findings"]
    )

    # The analyzer must not duplicate the structural missing-identity finding.
    assert sum(
        finding["title"] == "Identity definition is missing"
        and finding["entity"] == "ORDER"
        for finding in result["findings"]
    ) == 1



@pytest.mark.parametrize("section,value", [
    ("model", None),
    ("model", []),
    ("generation", None),
    ("generation", []),
])
def test_malformed_model_and_generation_sections_return_findings(section, value):
    specification = make_specification([
        {
            "name": "TEST_ID",
            "type": "IDENTIFIER",
            "identity": {"strategy": "SEQUENTIAL_ID"},
        }
    ])
    specification[section] = value

    result = SpecificationValidationService().validate(specification)

    assert result["can_continue"] is False
    assert result["findings"]
    assert result["errors"] > 0


def test_identity_fields_with_unhashable_members_return_findings():
    specification = make_specification([
        {
            "name": "TEST_ID",
            "type": "IDENTIFIER",
            "identity": {"strategy": "SEQUENTIAL_ID"},
        }
    ])
    specification["entities"][0]["identity"] = {"fields": ["TEST_ID", []]}

    result = SpecificationValidationService().validate(specification)

    assert result["can_continue"] is False
    assert any(
        finding["title"] == "Invalid identity field"
        for finding in result["findings"]
    )


def test_null_field_collection_returns_findings_without_crashing():
    specification = make_specification([
        {
            "name": "TEST_ID",
            "type": "IDENTIFIER",
            "identity": {"strategy": "SEQUENTIAL_ID"},
        }
    ])
    specification["entities"][0]["fields"] = None

    result = SpecificationValidationService().validate(specification)

    assert result["can_continue"] is False
    assert any(
        finding["title"] == "Invalid field collection"
        for finding in result["findings"]
    )


def test_relationship_success_requires_a_resolved_foreign_key_mapping():
    specification = make_specification([
        {
            "name": "TEST_ID",
            "type": "IDENTIFIER",
            "identity": {"strategy": "SEQUENTIAL_ID"},
        }
    ])
    specification["entities"].append({
        "name": "CHILD",
        "fields": [
            {
                "name": "CHILD_ID",
                "type": "IDENTIFIER",
                "identity": {"strategy": "SEQUENTIAL_ID"},
            },
            {
                "name": "PARENT_REF",
                "type": "IDENTIFIER",
                "identity": {"strategy": "SEQUENTIAL_ID"},
            },
        ],
        "identity": {"fields": ["CHILD_ID"]},
        "population": {"count": 10},
    })
    specification["foreign_keys"] = [{
        "name": "FK_CHILD_PARENT",
        "source": {"entity": "CHILD", "fields": ["PARENT_REF"]},
        "target": {"entity": "TEST_ENTITY", "fields": ["TEST_ID"]},
    }]
    specification["relationships"] = [{
        "source": "CHILD.PARENT_REF",
        "target": "TEST_ENTITY.TEST_ID",
        "type": "MANY_TO_ONE",
        "source_participation": "MANDATORY",
        "target_participation": "OPTIONAL",
    }]

    result = SpecificationValidationService().validate(specification)

    mapped = [
        finding for finding in result["findings"]
        if finding["title"] == "Relationship mapping is valid"
    ]
    assert len(mapped) == 1
    assert "FK_CHILD_PARENT" in mapped[0]["details"]
    assert "FORWARD" in mapped[0]["details"]

    entity_successes = [
        finding for finding in result["findings"]
        if finding["title"] == "Entity structure is valid"
    ]
    assert {
        finding["entity"] for finding in entity_successes
    } == {"TEST_ENTITY", "CHILD"}

    foreign_key_successes = [
        finding for finding in result["findings"]
        if finding["title"] == "Foreign key declaration is valid"
    ]
    assert len(foreign_key_successes) == 1
    assert "FK_CHILD_PARENT" in foreign_key_successes[0]["details"]


def test_relationship_invalid_participation_is_not_duplicated():
    specification = make_specification([
        {
            "name": "TEST_ID",
            "type": "IDENTIFIER",
            "identity": {"strategy": "SEQUENTIAL_ID"},
        }
    ])
    specification["relationships"] = [{
        "source": "TEST_ENTITY.TEST_ID",
        "target": "TEST_ENTITY.TEST_ID",
        "type": "ONE_TO_ONE",
        "source_participation": [],
        "target_participation": "OPTIONAL",
    }]

    result = SpecificationValidationService().validate(specification)

    findings = [
        finding for finding in result["findings"]
        if finding["title"] == "Invalid source participation"
    ]
    assert len(findings) == 1


def test_decimal_constraint_accepts_large_finite_decimal_without_float_overflow():
    specification = make_constraint_specification({
        "entity": "TEST_ENTITY",
        "field": "TEST_AMOUNT",
        "operator": ">",
        "value": "1e10000",
    })
    specification["entities"][0]["fields"].append({
        "name": "TEST_AMOUNT",
        "type": "DECIMAL",
        "generation": {
            "strategy": "RANDOM",
            "distribution": "UNIFORM",
            "parameters": {"minimum": "0", "maximum": "1e10001"},
        },
    })

    finding = get_constraint_finding(specification)
    assert finding["severity"] == "passed"


@pytest.mark.parametrize("section", [
    "dependencies",
    "statistical_behavior",
    "scenarios",
])
def test_additional_specification_sections_validate_object_structure(section):
    specification = make_specification([
        {
            "name": "TEST_ID",
            "type": "IDENTIFIER",
            "identity": {"strategy": "SEQUENTIAL_ID"},
        }
    ])
    specification[section] = [None]

    result = SpecificationValidationService().validate(specification)

    assert result["can_continue"] is False
    assert any(
        finding["severity"] == "error"
        and section in finding["details"]
        for finding in result["findings"]
    )


def test_duplicate_relationship_declaration_is_reported_once():
    specification = make_specification([
        {
            "name": "TEST_ID",
            "type": "IDENTIFIER",
            "identity": {"strategy": "SEQUENTIAL_ID"},
        }
    ])
    relationship = {
        "source": "TEST_ENTITY.TEST_ID",
        "target": "TEST_ENTITY.TEST_ID",
        "type": "ONE_TO_ONE",
        "source_participation": "MANDATORY",
        "target_participation": "OPTIONAL",
    }
    specification["relationships"] = [relationship, dict(relationship)]

    result = SpecificationValidationService().validate(specification)

    duplicates = [
        finding for finding in result["findings"]
        if finding["title"] == "Duplicate relationship definition"
    ]
    assert len(duplicates) == 1



def test_invalid_foreign_key_cannot_produce_passed_relationship_mapping():
    specification = make_specification([
        {
            "name": "TEST_ID",
            "type": "IDENTIFIER",
            "identity": {"strategy": "SEQUENTIAL_ID"},
        }
    ])
    specification["entities"].append({
        "name": "CHILD",
        "fields": [
            {
                "name": "CHILD_ID",
                "type": "IDENTIFIER",
                "identity": {"strategy": "SEQUENTIAL_ID"},
            },
            {
                "name": "PARENT_REF",
                "type": "STRING",
                "generation": {
                    "strategy": "RANDOM",
                    "generator": "RANDOM_STRING",
                    "parameters": {
                        "minimum_length": 2,
                        "maximum_length": 8,
                        "character_set": "ALPHANUMERIC",
                    },
                },
            },
        ],
        "identity": {"fields": ["CHILD_ID"]},
        "population": {"count": 10},
    })
    specification["foreign_keys"] = [{
        "name": "FK_CHILD_PARENT",
        "source": {"entity": "CHILD", "fields": ["PARENT_REF"]},
        "target": {"entity": "TEST_ENTITY", "fields": ["TEST_ID"]},
    }]
    specification["relationships"] = [{
        "source": "CHILD.PARENT_REF",
        "target": "TEST_ENTITY.TEST_ID",
        "type": "MANY_TO_ONE",
        "source_participation": "MANDATORY",
        "target_participation": "OPTIONAL",
    }]

    result = SpecificationValidationService().validate(specification)

    assert any(
        finding["title"] == "Incompatible foreign key field types"
        for finding in result["findings"]
    )
    assert not any(
        finding["title"] == "Relationship mapping is valid"
        for finding in result["findings"]
    )
    assert not any(
        finding["title"] == "Foreign key declaration is valid"
        for finding in result["findings"]
    )


@pytest.mark.parametrize(
    "relationship_type,expected_title",
    [
        ("ONE_TO_MANY", "Relationship Direction Mismatch"),
        ("MANY_TO_ONE", "Ambiguous Relationship Mapping"),
    ],
)
def test_relationship_mapping_failures_are_relationship_errors(
    relationship_type,
    expected_title,
):
    specification = make_specification([
        {
            "name": "TEST_ID",
            "type": "IDENTIFIER",
            "identity": {"strategy": "SEQUENTIAL_ID"},
        }
    ])
    specification["entities"].append({
        "name": "CHILD",
        "fields": [
            {"name": "CHILD_ID", "type": "IDENTIFIER", "identity": {"strategy": "SEQUENTIAL_ID"}},
            {"name": "PARENT_REF", "type": "IDENTIFIER", "identity": {"strategy": "SEQUENTIAL_ID"}},
        ],
        "identity": {"fields": ["CHILD_ID"]},
        "population": {"count": 10},
    })
    foreign_key = {
        "source": {"entity": "CHILD", "fields": ["PARENT_REF"]},
        "target": {"entity": "TEST_ENTITY", "fields": ["TEST_ID"]},
    }
    specification["foreign_keys"] = [
        {"name": "FK_CHILD_PARENT_A", **foreign_key}
    ]
    if expected_title == "Ambiguous Relationship Mapping":
        specification["foreign_keys"].append(
            {"name": "FK_CHILD_PARENT_B", **foreign_key}
        )
    specification["relationships"] = [{
        "source": "CHILD.PARENT_REF",
        "target": "TEST_ENTITY.TEST_ID",
        "type": relationship_type,
        "source_participation": "MANDATORY",
        "target_participation": "OPTIONAL",
    }]

    result = SpecificationValidationService().validate(specification)

    assert any(
        finding["severity"] == "error"
        and finding["category"] == "Relationship"
        and finding["title"] == expected_title
        for finding in result["findings"]
    )


def _make_composite_relationship_specification():
    specification = make_specification([
        {
            "name": "COMPANY_ID",
            "type": "IDENTIFIER",
            "identity": {"strategy": "SEQUENTIAL_ID"},
        },
        {
            "name": "SUPPLIER_ID",
            "type": "IDENTIFIER",
            "identity": {"strategy": "SEQUENTIAL_ID"},
        },
    ])

    supplier = specification["entities"][0]
    supplier["name"] = "SUPPLIER"
    supplier["identity"] = {
        "fields": ["COMPANY_ID", "SUPPLIER_ID"]
    }

    specification["entities"].append({
        "name": "CHILD",
        "fields": [
            {
                "name": "CHILD_ID",
                "type": "IDENTIFIER",
                "identity": {"strategy": "SEQUENTIAL_ID"},
            },
            {
                "name": "COMPANY_REF",
                "type": "IDENTIFIER",
                "identity": {"strategy": "SEQUENTIAL_ID"},
            },
            {
                "name": "SUPPLIER_REF",
                "type": "IDENTIFIER",
                "identity": {"strategy": "SEQUENTIAL_ID"},
            },
        ],
        "identity": {"fields": ["CHILD_ID"]},
        "population": {"count": 10},
    })

    specification["foreign_keys"] = [{
        "name": "FK_CHILD_SUPPLIER_COMPOSITE",
        "source": {
            "entity": "CHILD",
            "fields": ["COMPANY_REF", "SUPPLIER_REF"],
        },
        "target": {
            "entity": "SUPPLIER",
            "fields": ["COMPANY_ID", "SUPPLIER_ID"],
        },
    }]

    specification["relationships"] = [{
        "source": {
            "entity": "CHILD",
            "fields": ["COMPANY_REF", "SUPPLIER_REF"],
        },
        "target": {
            "entity": "SUPPLIER",
            "fields": ["COMPANY_ID", "SUPPLIER_ID"],
        },
        "type": "MANY_TO_ONE",
        "source_participation": "MANDATORY",
        "target_participation": "OPTIONAL",
    }]

    return specification


def test_model_validation_accepts_complete_ordered_composite_relationship_mapping():
    specification = _make_composite_relationship_specification()

    result = SpecificationValidationService().validate(specification)

    mappings = [
        finding for finding in result["findings"]
        if finding["title"] == "Relationship mapping is valid"
    ]

    assert result["can_continue"] is True
    assert len(mappings) == 1
    assert "FK_CHILD_SUPPLIER_COMPOSITE" in mappings[0]["details"]
    assert "FORWARD" in mappings[0]["details"]
    assert "Endpoint fields match in the declared order" in mappings[0]["details"]


def test_model_validation_blocks_reversed_composite_relationship_field_order():
    specification = _make_composite_relationship_specification()
    specification["relationships"][0]["source"]["fields"] = [
        "SUPPLIER_REF",
        "COMPANY_REF",
    ]
    specification["relationships"][0]["target"]["fields"] = [
        "SUPPLIER_ID",
        "COMPANY_ID",
    ]

    result = SpecificationValidationService().validate(specification)

    assert result["can_continue"] is False
    assert not any(
        finding["title"] == "Relationship mapping is valid"
        for finding in result["findings"]
    )
    assert any(
        finding["category"] == "Relationship"
        and finding["severity"] == "error"
        for finding in result["findings"]
    )


def test_model_validation_blocks_partial_composite_relationship_mapping():
    specification = _make_composite_relationship_specification()
    specification["relationships"][0]["source"]["fields"] = ["COMPANY_REF"]
    specification["relationships"][0]["target"]["fields"] = ["COMPANY_ID"]

    result = SpecificationValidationService().validate(specification)

    assert result["can_continue"] is False
    assert not any(
        finding["title"] == "Relationship mapping is valid"
        for finding in result["findings"]
    )
    assert any(
        finding["category"] == "Relationship"
        and finding["severity"] == "error"
        and finding["title"] == "Partial Composite Relationship Mapping"
        for finding in result["findings"]
    )


@pytest.mark.parametrize(
    "role,fields",
    [
        ("source", ["COMPANY_REF", "COMPANY_REF"]),
        ("target", ["COMPANY_ID", "COMPANY_ID"]),
    ],
)
def test_model_validation_rejects_duplicate_fields_in_composite_relationship_endpoint(
    role,
    fields,
):
    specification = _make_composite_relationship_specification()
    specification["relationships"][0][role]["fields"] = fields

    result = SpecificationValidationService().validate(specification)

    assert result["can_continue"] is False
    assert any(
        finding["category"] == "Relationship"
        and finding["severity"] == "error"
        and finding["title"] == f"Invalid {role} endpoint"
        and "duplicate fields" in finding["details"].lower()
        for finding in result["findings"]
    )


@pytest.mark.parametrize(
    "role,endpoint",
    [
        ("source", None),
        ("target", {"entity": "SUPPLIER", "fields": ["SUPPLIER_ID", []]}),
    ],
)
def test_model_validation_rejects_malformed_relationship_endpoint_without_crashing(
    role,
    endpoint,
):
    specification = _make_composite_relationship_specification()
    specification["relationships"][0][role] = endpoint

    result = SpecificationValidationService().validate(specification)

    assert result["can_continue"] is False
    assert any(
        finding["category"] == "Relationship"
        and finding["severity"] == "error"
        and f"Invalid {role} endpoint" == finding["title"]
        for finding in result["findings"]
    )



# MV-01: Optional-section validation must not mutate the input specification.

@pytest.mark.parametrize(
    "section_name",
    ["dependencies", "statistical_behavior", "scenarios"],
)
def test_validation_does_not_mutate_malformed_optional_sections(section_name):
    specification = make_specification([
        {
            "name": "TEST_ID",
            "type": "IDENTIFIER",
            "identity": {"strategy": "SEQUENTIAL_ID"},
        },
    ])
    specification[section_name] = {"invalid": "value"}
    original = deepcopy(specification)

    result = SpecificationValidationService().validate(specification)

    assert specification == original
    assert any(
        finding["title"] == f"Invalid {section_name} collection"
        for finding in result["findings"]
    )


@pytest.mark.parametrize(
    "section_name",
    ["dependencies", "statistical_behavior", "scenarios"],
)
def test_validation_does_not_mutate_optional_section_entries(section_name):
    specification = make_specification([
        {
            "name": "TEST_ID",
            "type": "IDENTIFIER",
            "identity": {"strategy": "SEQUENTIAL_ID"},
        },
    ])
    specification[section_name] = [{"valid": "entry"}, "invalid entry"]
    original = deepcopy(specification)

    result = SpecificationValidationService().validate(specification)

    assert specification == original
    assert any(
        finding["title"].startswith("Invalid ")
        and finding["category"] == "Specification"
        for finding in result["findings"]
    )


# MV-02: Structural FK validation must resolve normalized entity names.

def test_fk_validation_normalizes_entity_names_without_mutating_specification():
    specification = make_fk_specification(
        {"name": "PARENT_CODE_FK", "type": "STRING"}
    )
    specification["entities"][0]["name"] = " TEST_ENTITY "
    specification["entities"][1]["name"] = " CHILD "
    specification["entities"][0]["identity"] = {"fields": ["PARENT_CODE"]}
    specification["foreign_keys"][0]["source"]["entity"] = " CHILD "
    specification["foreign_keys"][0]["target"]["entity"] = " TEST_ENTITY "

    original = deepcopy(specification)
    result = SpecificationValidationService().validate(specification)

    assert specification == original

    fk_errors = {
        "Unknown source entity",
        "Unknown target entity",
        "Source field is missing",
        "Target field is missing",
        "Target identity is missing",
        "Target fields do not match target identity",
    }
    assert not any(
        finding["title"] in fk_errors
        for finding in result["findings"]
    )


def test_capability_validation_normalizes_fk_entity_endpoints():
    specification = make_fk_specification(
        {"name": "PARENT_CODE_FK", "type": "STRING"}
    )
    specification["entities"][0]["name"] = " TEST_ENTITY "
    specification["entities"][1]["name"] = " CHILD "
    specification["entities"][0]["identity"] = {"fields": ["PARENT_CODE"]}
    specification["foreign_keys"][0]["source"]["entity"] = " CHILD "
    specification["foreign_keys"][0]["target"]["entity"] = " TEST_ENTITY "

    original = deepcopy(specification)
    result = SpecificationValidationService().validate(specification)

    assert specification == original
    assert not any(
        finding["title"] == "Capability validation could not complete"
        for finding in result["findings"]
    )
