import pytest

from app.services.specification_import_service import (
    SpecificationImportService,
)


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("12.3400", "12.3400"),
        ("0.123456789123456789", "0.123456789123456789"),
        ("-999999999999999999.123456789", "-999999999999999999.123456789"),
        ("  1.2500  ", "1.2500"),
        ("10", "10"),
    ],
)
def test_optional_decimal_text_preserves_exact_representation(
    value,
    expected,
):
    assert (
        SpecificationImportService._optional_decimal_text(value)
        == expected
    )


@pytest.mark.parametrize(
    "value",
    ["NaN", "Infinity", "-Infinity", "not-a-number"],
)
def test_optional_decimal_text_rejects_invalid_or_non_finite_values(value):
    with pytest.raises(ValueError):
        SpecificationImportService._optional_decimal_text(value)


def test_optional_decimal_text_returns_none_for_blank_input():
    assert SpecificationImportService._optional_decimal_text("") is None
    assert SpecificationImportService._optional_decimal_text("   ") is None
