from decimal import Decimal

import pytest

from app.services.decimal_precision import (
    decimal_to_scaled_integer,
    scaled_integer_to_decimal,
)
from app.services.field_generation_validation import validate_field_generation
from app.services.generation.generator import GenerationError, Generator


def decimal_field(
    minimum="0.00",
    maximum="999.99",
    distribution="UNIFORM",
    precision=5,
    scale=2,
):
    parameters = {
        "minimum": minimum,
        "maximum": maximum,
    }

    if precision is not None:
        parameters["precision"] = precision

    if scale is not None:
        parameters["scale"] = scale

    return {
        "name": "AMOUNT",
        "type": "DECIMAL",
        "generation": {
            "strategy": "RANDOM",
            "distribution": distribution,
            "parameters": parameters,
        },
    }


@pytest.mark.parametrize(
    ("value", "scale", "expected"),
    [
        ("12.34", 2, 1234),
        ("12.3400", 2, 1234),
        ("12", 2, 1200),
        ("-0.25", 2, -25),
        ("1.234", 2, None),
    ],
)
def test_decimal_to_scaled_integer(value, scale, expected):
    assert decimal_to_scaled_integer(Decimal(value), scale) == expected


@pytest.mark.parametrize(
    ("value", "scale"),
    [
        (1234, 2),
        (-25, 2),
        (0, 0),
    ],
)
def test_scaled_integer_to_decimal(value, scale):
    result = scaled_integer_to_decimal(value, scale)
    assert decimal_to_scaled_integer(result, scale) == value


def test_valid_decimal_precision_and_scale_are_accepted():
    assert validate_field_generation(decimal_field()) == []


def test_legacy_decimal_without_precision_and_scale_remains_valid():
    assert validate_field_generation(
        decimal_field(precision=None, scale=None)
    ) == []


@pytest.mark.parametrize(
    ("precision", "scale"),
    [
        (None, 2),
        (5, None),
        (0, 0),
        (-1, 0),
        (5, -1),
        (2, 3),
        (True, 1),
        (5, True),
        (5.0, 2),
    ],
)
def test_invalid_precision_and_scale_are_rejected(precision, scale):
    errors = validate_field_generation(
        decimal_field(precision=precision, scale=scale)
    )
    assert errors


@pytest.mark.parametrize(
    ("minimum", "maximum"),
    [
        ("0.001", "1.00"),
        ("-1000.00", "999.99"),
        ("0.00", "1000.00"),
    ],
)
def test_bounds_incompatible_with_precision_and_scale_are_rejected(
    minimum,
    maximum,
):
    errors = validate_field_generation(
        decimal_field(minimum=minimum, maximum=maximum)
    )
    assert errors


@pytest.mark.parametrize("distribution", ["UNIFORM", "NORMAL"])
def test_generated_values_respect_declared_precision_and_scale(distribution):
    field = decimal_field(distribution=distribution)
    generator = Generator(seed=42)

    values = [
        generator.generate_value(field=field, row_number=index)
        for index in range(500)
    ]

    assert all(isinstance(value, Decimal) for value in values)
    assert all(
        Decimal("0.00") <= value <= Decimal("999.99")
        for value in values
    )
    assert all(value.as_tuple().exponent == -2 for value in values)
    assert all(
        abs(decimal_to_scaled_integer(value, 2)) < 10**5
        for value in values
    )


def test_generator_preserves_legacy_decimal_behavior_without_precision():
    field = decimal_field(
        minimum="0.0",
        maximum="10.0",
        precision=None,
        scale=None,
    )

    value = Generator(seed=42).generate_value(field=field, row_number=1)

    assert isinstance(value, Decimal)
    assert Decimal("0.0") <= value <= Decimal("10.0")


def test_generator_rejects_bounds_that_exceed_declared_precision():
    field = decimal_field(maximum="1000.00")

    with pytest.raises(GenerationError, match="exceed precision"):
        Generator(seed=42).generate_value(field=field, row_number=1)
