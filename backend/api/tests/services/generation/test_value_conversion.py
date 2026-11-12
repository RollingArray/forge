from decimal import Decimal

import pytest

from app.services.generation.value_conversion import convert_value


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("12.3400", Decimal("12.3400")),
        ("0.123456789123456789", Decimal("0.123456789123456789")),
        (
            "-999999999999999999.123456789",
            Decimal("-999999999999999999.123456789"),
        ),
        ("10", Decimal("10")),
    ],
)
def test_decimal_conversion_preserves_exact_value(value, expected):
    result = convert_value(value, "DECIMAL")

    assert isinstance(result, Decimal)
    assert result == expected


def test_decimal_conversion_preserves_trailing_zero_exponent():
    result = convert_value("12.3400", "DECIMAL")

    assert result.as_tuple().exponent == -4
    assert str(result) == "12.3400"


def test_decimal_conversion_returns_existing_decimal_unchanged():
    value = Decimal("0.123456789123456789")

    assert convert_value(value, "DECIMAL") is value


@pytest.mark.parametrize("value", [12.34, 12, True])
def test_decimal_conversion_rejects_json_numeric_values(value):
    with pytest.raises(ValueError, match="decimal strings"):
        convert_value(value, "DECIMAL")


@pytest.mark.parametrize(
    "value",
    ["not-a-number", "NaN", "Infinity", "-Infinity"],
)
def test_decimal_conversion_rejects_invalid_or_non_finite_values(value):
    with pytest.raises(ValueError):
        convert_value(value, "DECIMAL")


def test_integer_conversion_remains_unchanged():
    assert convert_value("123", "INTEGER") == 123
    assert convert_value(123, "INTEGER") == 123


def test_identifier_conversion_remains_unchanged():
    assert convert_value("123", "IDENTIFIER") == 123


def test_boolean_conversion_remains_unchanged():
    assert convert_value("true", "BOOLEAN") is True
    assert convert_value("false", "BOOLEAN") is False


def test_string_conversion_remains_unchanged():
    assert convert_value("00123", "STRING") == "00123"
