import pytest

from app.services.field_generation_validation import (
    validate_field_generation,
)


@pytest.mark.parametrize(
    "field",
    [
        {
            "type": "IDENTIFIER",
            "identity": {"strategy": "SEQUENTIAL_ID"},
        },
        {
            "type": "STRING",
            "generation": {
                "strategy": "RANDOM",
                "generator": "RANDOM_STRING",
                "parameters": {
                    "minimum_length": 5,
                    "maximum_length": 20,
                    "character_set": "ALPHANUMERIC",
                },
            },
        },
        {
            "type": "STRING",
            "generation": {
                "strategy": "RANDOM",
                "generator": "PATTERN",
                "parameters": {"pattern": "SUP-\\\\d{6}"},
            },
        },
        {
            "type": "STRING",
            "generation": {
                "strategy": "RANDOM",
                "generator": "SEMANTIC",
                "parameters": {
                    "description": "A supplier company name",
                    "mode": "VOCABULARY",
                },
            },
        },
        {
            "type": "INTEGER",
            "generation": {
                "strategy": "RANDOM",
                "distribution": "UNIFORM",
                "parameters": {"minimum": 1, "maximum": 100},
            },
        },
        {
            "type": "INTEGER",
            "generation": {
                "strategy": "RANDOM",
                "distribution": "DISCRETE_UNIFORM",
                "parameters": {"minimum": 0, "maximum": 10},
            },
        },
        {
            "type": "DECIMAL",
            "generation": {
                "strategy": "RANDOM",
                "distribution": "UNIFORM",
                "parameters": {"minimum": "0.0", "maximum": "99.99"},
            },
        },
        {
            "type": "DECIMAL",
            "generation": {
                "strategy": "RANDOM",
                "distribution": "NORMAL",
                "parameters": {"minimum": "-10.5", "maximum": "10.5"},
            },
        },
        {
            "type": "BOOLEAN",
            "generation": {"strategy": "RANDOM"},
        },
        {
            "type": "CATEGORICAL",
            "generation": {
                "strategy": "RANDOM",
                "distribution": "CATEGORICAL",
                "parameters": {"values": ["OPEN", "CLOSED"]},
            },
        },
    ],
)
def test_valid_field_generation_configurations_have_no_errors(field):
    assert validate_field_generation(field) == []


@pytest.mark.parametrize(
    ("field", "expected"),
    [
        (
            {"type": "IDENTIFIER"},
            "IDENTIFIER requires SEQUENTIAL_ID.",
        ),
        (
            {
                "type": "IDENTIFIER",
                "identity": {"strategy": "RANDOM"},
            },
            "IDENTIFIER requires SEQUENTIAL_ID.",
        ),
        (
            {"type": "BOOLEAN"},
            "BOOLEAN requires RANDOM.",
        ),
        (
            {
                "type": "BOOLEAN",
                "generation": {"strategy": "SEQUENTIAL"},
            },
            "BOOLEAN requires RANDOM.",
        ),
        (
            {"type": "STRING"},
            "STRING requires generation.strategy RANDOM.",
        ),
        (
            {
                "type": "STRING",
                "generation": {
                    "strategy": "RANDOM",
                    "generator": "UNKNOWN",
                },
            },
            "STRING requires RANDOM_STRING, PATTERN, or SEMANTIC.",
        ),
        (
            {
                "type": "CATEGORICAL",
                "generation": {
                    "strategy": "RANDOM",
                    "distribution": "UNIFORM",
                    "parameters": {"values": ["A"]},
                },
            },
            "CATEGORICAL requires RANDOM, CATEGORICAL distribution, and a non-empty values list.",
        ),
        (
            {
                "type": "CATEGORICAL",
                "generation": {
                    "strategy": "RANDOM",
                    "distribution": "CATEGORICAL",
                    "parameters": {"values": []},
                },
            },
            "CATEGORICAL requires RANDOM, CATEGORICAL distribution, and a non-empty values list.",
        ),
    ],
)
def test_missing_or_incompatible_field_configuration_is_rejected(
    field,
    expected,
):
    assert expected in validate_field_generation(field)


@pytest.mark.parametrize(
    ("parameters", "expected"),
    [
        (
            {
                "minimum_length": 0,
                "maximum_length": 10,
                "character_set": "ALPHA",
            },
            "RANDOM_STRING requires positive ordered integer minimum_length and maximum_length.",
        ),
        (
            {
                "minimum_length": 10,
                "maximum_length": 5,
                "character_set": "ALPHA",
            },
            "RANDOM_STRING requires positive ordered integer minimum_length and maximum_length.",
        ),
        (
            {
                "minimum_length": True,
                "maximum_length": 10,
                "character_set": "ALPHA",
            },
            "RANDOM_STRING requires positive ordered integer minimum_length and maximum_length.",
        ),
        (
            {
                "minimum_length": 1,
                "maximum_length": 10,
                "character_set": "UNKNOWN",
            },
            "RANDOM_STRING requires a supported character_set.",
        ),
    ],
)
def test_random_string_requires_valid_parameters(parameters, expected):
    field = {
        "type": "STRING",
        "generation": {
            "strategy": "RANDOM",
            "generator": "RANDOM_STRING",
            "parameters": parameters,
        },
    }

    assert expected in validate_field_generation(field)


@pytest.mark.parametrize(
    ("generator", "parameters", "expected"),
    [
        (
            "PATTERN",
            {"pattern": "   "},
            "PATTERN requires a non-empty pattern.",
        ),
        (
            "SEMANTIC",
            {"description": "", "mode": "UNIQUE"},
            "SEMANTIC requires a non-empty description.",
        ),
        (
            "SEMANTIC",
            {"description": "Supplier name", "mode": "INVALID"},
            "SEMANTIC mode must be UNIQUE or VOCABULARY.",
        ),
    ],
)
def test_string_generators_require_their_mandatory_parameters(
    generator,
    parameters,
    expected,
):
    field = {
        "type": "STRING",
        "generation": {
            "strategy": "RANDOM",
            "generator": generator,
            "parameters": parameters,
        },
    }

    assert expected in validate_field_generation(field)


@pytest.mark.parametrize(
    ("field_type", "distribution", "parameters", "expected"),
    [
        (
            "INTEGER",
            "UNIFORM",
            {"minimum": 1},
            "minimum and maximum must be finite numeric values.",
        ),
        (
            "INTEGER",
            "UNIFORM",
            {"minimum": 1, "maximum": float("inf")},
            "minimum and maximum must be finite numeric values.",
        ),
        (
            "INTEGER",
            "UNIFORM",
            {"minimum": True, "maximum": 10},
            "minimum and maximum must be finite numeric values.",
        ),
        (
            "INTEGER",
            "UNIFORM",
            {"minimum": 1.5, "maximum": 10},
            "INTEGER bounds must be whole numbers.",
        ),
        (
            "INTEGER",
            "UNIFORM",
            {"minimum": 10, "maximum": 1},
            "minimum cannot exceed maximum.",
        ),
        (
            "DECIMAL",
            "UNIFORM",
            {"minimum": "10", "maximum": "1"},
            "minimum cannot exceed maximum.",
        ),
        (
            "DECIMAL",
            "DISCRETE_UNIFORM",
            {"minimum": "0", "maximum": "10"},
            "DECIMAL supports only RANDOM with distributions NORMAL, UNIFORM.",
        ),
    ],
)
def test_numeric_fields_reject_invalid_bounds_and_distributions(
    field_type,
    distribution,
    parameters,
    expected,
):
    field = {
        "type": field_type,
        "generation": {
            "strategy": "RANDOM",
            "distribution": distribution,
            "parameters": parameters,
        },
    }

    assert expected in validate_field_generation(field)


@pytest.mark.parametrize(
    ("field", "expected"),
    [
        (None, "Field definition must be an object."),
        ({"type": "STRING", "identity": []}, "identity must be an object."),
        ({"type": "STRING", "generation": []}, "generation must be an object."),
        (
            {
                "type": "STRING",
                "generation": {
                    "strategy": "RANDOM",
                    "generator": "PATTERN",
                    "parameters": [],
                },
            },
            "parameters must be an object.",
        ),
        ({"type": "DATE"}, "unsupported field type 'DATE'."),
    ],
)
def test_malformed_or_unsupported_field_definitions_are_rejected(
    field,
    expected,
):
    assert expected in validate_field_generation(field)


def test_integer_bounds_accept_numeric_strings():
    field = {
        "type": "INTEGER",
        "generation": {
            "strategy": "RANDOM",
            "distribution": "UNIFORM",
            "parameters": {"minimum": "1", "maximum": "100"},
        },
    }

    assert validate_field_generation(field) == []


@pytest.mark.parametrize(
    ("minimum", "maximum"),
    [
        (0.0, "10.0"),
        ("0.0", 10.0),
        (0, 10),
    ],
)
def test_decimal_bounds_reject_json_numeric_values(minimum, maximum):
    field = {
        "type": "DECIMAL",
        "generation": {
            "strategy": "RANDOM",
            "distribution": "UNIFORM",
            "parameters": {
                "minimum": minimum,
                "maximum": maximum,
            },
        },
    }

    assert (
        "DECIMAL minimum and maximum must be decimal strings."
        in validate_field_generation(field)
    )


def test_decimal_bounds_accept_exact_decimal_strings():
    field = {
        "type": "DECIMAL",
        "generation": {
            "strategy": "RANDOM",
            "distribution": "UNIFORM",
            "parameters": {
                "minimum": "0.123456789123456789",
                "maximum": "9.876543219876543219",
            },
        },
    }

    assert validate_field_generation(field) == []


def test_decimal_bounds_preserve_trailing_zero_representation():
    field = {
        "type": "DECIMAL",
        "generation": {
            "strategy": "RANDOM",
            "distribution": "UNIFORM",
            "parameters": {
                "minimum": "12.3400",
                "maximum": "20.0000",
            },
        },
    }

    assert validate_field_generation(field) == []
    assert field["generation"]["parameters"]["minimum"] == "12.3400"
    assert field["generation"]["parameters"]["maximum"] == "20.0000"
