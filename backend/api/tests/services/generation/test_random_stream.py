import random

import pytest

from app.services.generation.random_stream import (
    create_random_stream,
    derive_random_seed,
)


BASE_ARGUMENTS = {
    "base_seed": 42,
    "algorithm_version": "forge-generation-test-v1",
    "entity_name": "CUSTOMER",
    "scope": "CUSTOMER_NAME",
    "row_number": 1,
    "purpose": "SCALAR",
}


def test_derived_seed_is_stable():
    first = derive_random_seed(**BASE_ARGUMENTS)
    second = derive_random_seed(**BASE_ARGUMENTS)

    assert first == second


@pytest.mark.parametrize(
    ("name", "value"),
    [
        ("base_seed", 43),
        ("algorithm_version", "forge-generation-test-v2"),
        ("entity_name", "SUPPLIER"),
        ("scope", "SUPPLIER_NAME"),
        ("row_number", 2),
        ("purpose", "VOCABULARY"),
    ],
)
def test_each_identity_dimension_produces_an_independent_seed(name, value):
    changed = {**BASE_ARGUMENTS, name: value}

    assert derive_random_seed(**changed) != derive_random_seed(
        **BASE_ARGUMENTS
    )


def test_stream_is_a_standard_random_instance():
    stream = create_random_stream(**BASE_ARGUMENTS)

    assert isinstance(stream, random.Random)


def test_independent_streams_reproduce_the_same_sequence():
    first = create_random_stream(**BASE_ARGUMENTS)
    second = create_random_stream(**BASE_ARGUMENTS)

    assert [first.random() for _ in range(10)] == [
        second.random() for _ in range(10)
    ]


def test_consuming_one_stream_does_not_change_another_stream():
    untouched = create_random_stream(**BASE_ARGUMENTS)
    consumed = create_random_stream(**BASE_ARGUMENTS)

    expected = [untouched.random() for _ in range(5)]

    for _ in range(100):
        consumed.random()

    replay = create_random_stream(**BASE_ARGUMENTS)

    assert [replay.random() for _ in range(5)] == expected


@pytest.mark.parametrize(
    ("name", "value"),
    [
        ("base_seed", True),
        ("base_seed", 42.0),
        ("row_number", True),
        ("row_number", 0),
        ("row_number", -1),
        ("algorithm_version", ""),
        ("entity_name", " "),
        ("scope", ""),
        ("purpose", " "),
    ],
)
def test_invalid_identity_values_are_rejected(name, value):
    arguments = {**BASE_ARGUMENTS, name: value}

    with pytest.raises(ValueError):
        derive_random_seed(**arguments)
