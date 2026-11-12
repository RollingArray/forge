"""Exact helpers for DECIMAL precision and scale."""

from decimal import Decimal


def decimal_to_scaled_integer(value: Decimal, scale: int) -> int | None:
    """Convert a Decimal to an integer at the requested scale.

    Returns None if the value cannot be represented exactly at that scale.
    """
    if not value.is_finite() or isinstance(scale, bool) or scale < 0:
        return None

    sign, digits, exponent = value.as_tuple()
    coefficient = int("".join(str(digit) for digit in digits) or "0")
    shift = exponent + scale

    if shift >= 0:
        scaled = coefficient * (10 ** shift)
    else:
        divisor = 10 ** (-shift)
        if coefficient % divisor:
            return None
        scaled = coefficient // divisor

    return -scaled if sign else scaled


def scaled_integer_to_decimal(value: int, scale: int) -> Decimal:
    """Convert a scaled integer to an exact Decimal with the given scale."""
    sign = 1 if value < 0 else 0
    digits = tuple(int(character) for character in str(abs(value)))
    return Decimal((sign, digits, -scale))
