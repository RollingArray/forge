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
