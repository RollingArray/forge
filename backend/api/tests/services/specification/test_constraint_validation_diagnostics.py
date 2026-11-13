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


