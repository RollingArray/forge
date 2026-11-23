from __future__ import annotations

import pytest

from app.services.generation.context import (
    GenerationContext,
    GenerationContextIntegrityError,
)
from app.services.generation.row_generator import (
    RowGenerationError,
    RowGenerator,
)


def test_context_registers_sparse_unique_semantic_values_by_global_row():
    context = GenerationContext()

    context.add_unique_semantic_values(
        entity_name="PRODUCT",
        field_name="PRODUCT_NAME",
        values_by_row={
            0: "Hydraulic Pump",
            50: "Flight Control Computer",
            150: "Landing Gear Assembly",
        },
    )

    assert context.get_unique_semantic_values(
        entity_name="PRODUCT",
        field_name="PRODUCT_NAME",
    ) == {
        0: "Hydraulic Pump",
        50: "Flight Control Computer",
        150: "Landing Gear Assembly",
    }


def test_context_unique_semantic_registration_is_idempotent():
    context = GenerationContext()
    values = {50: "Flight Control Computer"}

    context.add_unique_semantic_values(
        entity_name="PRODUCT",
        field_name="PRODUCT_NAME",
        values_by_row=values,
    )
    context.add_unique_semantic_values(
        entity_name="PRODUCT",
        field_name="PRODUCT_NAME",
        values_by_row=values,
    )

    assert context.get_unique_semantic_value(
        entity_name="PRODUCT",
        field_name="PRODUCT_NAME",
        row_index=50,
    ) == "Flight Control Computer"


def test_context_rejects_conflicting_unique_semantic_assignment():
    context = GenerationContext()
    context.add_unique_semantic_values(
        entity_name="PRODUCT",
        field_name="PRODUCT_NAME",
        values_by_row={50: "Original"},
    )

    with pytest.raises(
        GenerationContextIntegrityError,
        match="Conflicting UNIQUE semantic value",
    ):
        context.add_unique_semantic_values(
            entity_name="PRODUCT",
            field_name="PRODUCT_NAME",
            values_by_row={50: "Replacement"},
        )


def test_context_rejects_duplicate_unique_semantic_values():
    context = GenerationContext()

    with pytest.raises(
        GenerationContextIntegrityError,
        match="Duplicate UNIQUE semantic values",
    ):
        context.add_unique_semantic_values(
            entity_name="PRODUCT",
            field_name="PRODUCT_NAME",
            values_by_row={
                50: "Hydraulic Pump",
                150: " hydraulic pump ",
            },
        )


@pytest.mark.parametrize("row_index", [-1, True, 1.5, "1"])
def test_context_rejects_invalid_unique_semantic_row_index(row_index):
    context = GenerationContext()

    with pytest.raises(GenerationContextIntegrityError):
        context.add_unique_semantic_values(
            entity_name="PRODUCT",
            field_name="PRODUCT_NAME",
            values_by_row={row_index: "Hydraulic Pump"},
        )


def test_context_returns_defensive_copy_of_unique_semantic_mapping():
    context = GenerationContext()
    context.add_unique_semantic_values(
        entity_name="PRODUCT",
        field_name="PRODUCT_NAME",
        values_by_row={50: "Flight Control Computer"},
    )

    returned = context.get_unique_semantic_values(
        entity_name="PRODUCT",
        field_name="PRODUCT_NAME",
    )
    assert returned is not None
    returned[50] = "Changed externally"

    assert context.get_unique_semantic_value(
        entity_name="PRODUCT",
        field_name="PRODUCT_NAME",
        row_index=50,
    ) == "Flight Control Computer"


def test_row_generator_uses_exact_global_row_position_for_unique_semantics():
    context = GenerationContext()
    context.add_unique_semantic_values(
        entity_name="PRODUCT",
        field_name="PRODUCT_NAME",
        values_by_row={
            50: "Flight Control Computer",
            150: "Landing Gear Assembly",
        },
    )

    generator = RowGenerator(seed=42)
    field = {
        "name": "PRODUCT_NAME",
        "type": "STRING",
        "generation": {
            "generator": "SEMANTIC",
            "parameters": {"mode": "UNIQUE"},
        },
    }

    row = generator.generate_row(
        entity_name="PRODUCT",
        fields=[field],
        foreign_keys=[],
        context=context,
        row_number=151,
        chunk_number=4,
    )

    assert row["PRODUCT_NAME"] == "Landing Gear Assembly"


def test_row_generator_does_not_compact_sparse_unique_semantic_positions():
    context = GenerationContext()
    context.add_unique_semantic_values(
        entity_name="PRODUCT",
        field_name="PRODUCT_NAME",
        values_by_row={150: "Landing Gear Assembly"},
    )

    generator = RowGenerator(seed=42)
    field = {
        "name": "PRODUCT_NAME",
        "type": "STRING",
        "generation": {
            "generator": "SEMANTIC",
            "parameters": {"mode": "UNIQUE"},
        },
    }

    with pytest.raises(RowGenerationError, match="global row index 50"):
        generator.generate_row(
            entity_name="PRODUCT",
            fields=[field],
            foreign_keys=[],
            context=context,
            row_number=51,
            chunk_number=2,
        )

def test_row_generator_returns_fields_in_specification_order():
    generator = RowGenerator(seed=42)

    row = generator.generate_row(
        entity_name="SUPPLIER_PART",
        fields=[
            {"name": "SUPPLIER_ID", "type": "IDENTIFIER"},
            {"name": "PART_ID", "type": "IDENTIFIER"},
            {"name": "SUPPLIER_PART_ID", "type": "IDENTIFIER"},
        ],
        foreign_keys=[],
        context=GenerationContext(),
        row_number=1,
        initial_values={
            "PART_ID": 5829,
            "SUPPLIER_ID": 51068,
            "SUPPLIER_PART_ID": 1,
        },
    )

    assert list(row) == [
        "SUPPLIER_ID",
        "PART_ID",
        "SUPPLIER_PART_ID",
    ]

    assert row == {
        "SUPPLIER_ID": 51068,
        "PART_ID": 5829,
        "SUPPLIER_PART_ID": 1,
    }


def test_row_generator_rejects_unexpected_initial_values():
    generator = RowGenerator(seed=42)

    with pytest.raises(
        RowGenerationError,
        match="unexpected fields",
    ):
        generator.generate_row(
            entity_name="SUPPLIER_PART",
            fields=[
                {"name": "SUPPLIER_ID", "type": "IDENTIFIER"},
            ],
            foreign_keys=[],
            context=GenerationContext(),
            row_number=1,
            initial_values={
                "SUPPLIER_ID": 51068,
                "UNKNOWN_FIELD": "unexpected",
            },
        )


def test_row_generator_rejects_duplicate_specification_fields():
    generator = RowGenerator(seed=42)

    with pytest.raises(
        RowGenerationError,
        match="Duplicate field names",
    ):
        generator.generate_row(
            entity_name="SUPPLIER_PART",
            fields=[
                {"name": "SUPPLIER_ID", "type": "IDENTIFIER"},
                {"name": "SUPPLIER_ID", "type": "IDENTIFIER"},
            ],
            foreign_keys=[],
            context=GenerationContext(),
            row_number=1,
        )
