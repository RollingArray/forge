from __future__ import annotations

import pytest

from app.services.generation.context import GenerationContext
from app.services.generation.entity_generator import (
    EntityGenerationError,
    EntityGenerator,
)


def _sequential_identity_field() -> dict:
    return {
        "name": "ID",
        "type": "IDENTIFIER",
        "identity": {
            "strategy": "SEQUENTIAL_ID",
        },
    }


def _categorical_identity_field() -> dict:
    return {
        "name": "CODE",
        "type": "STRING",
        "generation": {
            "strategy": "RANDOM",
            "distribution": "CATEGORICAL",
            "parameters": {
                "values": ["A", "B", "C"],
            },
        },
    }


def _uniform_identity_field() -> dict:
    return {
        "name": "ID",
        "type": "INTEGER",
        "generation": {
            "strategy": "RANDOM",
            "distribution": "UNIFORM",
            "parameters": {
                "minimum": 1,
                "maximum": 5,
            },
        },
    }


def _discrete_uniform_identity_field() -> dict:
    return {
        "name": "ID",
        "type": "INTEGER",
        "generation": {
            "strategy": "RANDOM",
            "distribution": "DISCRETE_UNIFORM",
            "parameters": {
                "minimum": 10,
                "maximum": 14,
            },
        },
    }


def _allocate(
    *,
    seed: int,
    target_rows: int,
    fields: list[dict],
    identity_fields: tuple[str, ...],
    foreign_keys: list[dict] | None = None,
    context: GenerationContext | None = None,
) -> list[dict]:
    generator = EntityGenerator(seed=seed)

    return generator._allocate_fk_identity(
        target_rows=target_rows,
        row_start=0,
        row_count=target_rows,
        identity_fields=identity_fields,
        foreign_keys=foreign_keys or [],
        context=context or GenerationContext(),
        fields=fields,
    )


def _allocate_chunk(
    *,
    seed: int,
    target_rows: int,
    row_start: int,
    row_count: int,
    fields: list[dict],
    identity_fields: tuple[str, ...],
    foreign_keys: list[dict] | None = None,
    context: GenerationContext | None = None,
) -> list[dict]:
    generator = EntityGenerator(seed=seed)

    return generator._allocate_fk_identity(
        target_rows=target_rows,
        row_start=row_start,
        row_count=row_count,
        identity_fields=identity_fields,
        foreign_keys=foreign_keys or [],
        context=context or GenerationContext(),
        fields=fields,
    )


def test_sequential_identity_allocates_one_value_per_requested_row() -> None:
    fields = [_sequential_identity_field()]

    rows = _allocate(
        seed=42,
        target_rows=5,
        fields=fields,
        identity_fields=("ID",),
    )

    assert rows == [
        {"ID": 1},
        {"ID": 2},
        {"ID": 3},
        {"ID": 4},
        {"ID": 5},
    ]


def test_categorical_identity_uses_configured_domain() -> None:
    fields = [_categorical_identity_field()]

    rows = _allocate(
        seed=42,
        target_rows=3,
        fields=fields,
        identity_fields=("CODE",),
    )

    assert len(rows) == 3
    assert {row["CODE"] for row in rows}.issubset({"A", "B", "C"})


def test_uniform_identity_uses_configured_domain() -> None:
    fields = [_uniform_identity_field()]

    rows = _allocate(
        seed=42,
        target_rows=5,
        fields=fields,
        identity_fields=("ID",),
    )

    assert len(rows) == 5
    assert all(1 <= row["ID"] <= 5 for row in rows)
    assert len({row["ID"] for row in rows}) == 5


def test_discrete_uniform_identity_uses_configured_domain() -> None:
    fields = [_discrete_uniform_identity_field()]

    rows = _allocate(
        seed=42,
        target_rows=5,
        fields=fields,
        identity_fields=("ID",),
    )

    assert len(rows) == 5
    assert all(10 <= row["ID"] <= 14 for row in rows)
    assert len({row["ID"] for row in rows}) == 5


def test_context_indexed_key_space_preserves_unique_identity_keys_across_chunks() -> None:
    context = GenerationContext()

    context.add_rows(
        entity_name="CUSTOMER",
        rows=[
            {"CUSTOMER_ID": "C1"},
            {"CUSTOMER_ID": "C2"},
        ],
        identity_fields=("CUSTOMER_ID",),
    )

    context.add_rows(
        entity_name="CUSTOMER",
        rows=[
            {"CUSTOMER_ID": "C2"},
            {"CUSTOMER_ID": "C3"},
        ],
        identity_fields=("CUSTOMER_ID",),
    )

    assert context.get_indexed_key_space(
        entity_name="CUSTOMER",
        fields=("CUSTOMER_ID",),
    ) == [
        ("C1",),
        ("C2",),
        ("C3",),
    ]


def test_restore_key_space_builds_indexed_key_space() -> None:
    context = GenerationContext()

    context.restore_key_space(
        entity_name="CUSTOMER",
        identity_fields=("CUSTOMER_ID",),
        key_space={
            ("C1",),
            ("C2",),
            ("C3",),
        },
    )

    indexed_keys = context.get_indexed_key_space(
        entity_name="CUSTOMER",
        fields=("CUSTOMER_ID",),
    )

    assert set(indexed_keys) == {
        ("C1",),
        ("C2",),
        ("C3",),
    }


def test_context_key_space_preserves_unique_identity_keys_across_chunks() -> None:
    context = GenerationContext()

    context.add_rows(
        entity_name="CUSTOMER",
        rows=[
            {"CUSTOMER_ID": "C1"},
            {"CUSTOMER_ID": "C2"},
        ],
        identity_fields=("CUSTOMER_ID",),
    )

    context.add_rows(
        entity_name="CUSTOMER",
        rows=[
            {"CUSTOMER_ID": "C2"},
            {"CUSTOMER_ID": "C3"},
        ],
        identity_fields=("CUSTOMER_ID",),
    )

    assert context.get_key_space(
        entity_name="CUSTOMER",
        fields=("CUSTOMER_ID",),
    ) == {
        ("C1",),
        ("C2",),
        ("C3",),
    }


def test_single_field_fk_identity_uses_parent_key_space() -> None:
    context = GenerationContext()

    context.add_rows(
        entity_name="CUSTOMER",
        rows=[
            {"CUSTOMER_ID": "C1"},
            {"CUSTOMER_ID": "C2"},
            {"CUSTOMER_ID": "C3"},
        ],
        identity_fields=("CUSTOMER_ID",),
    )

    fields = [
        {
            "name": "CUSTOMER_ID",
            "type": "STRING",
            "identity": {},
        }
    ]

    foreign_keys = [
        {
            "child_fields": ["CUSTOMER_ID"],
            "parent_entity": "CUSTOMER",
            "parent_fields": ["CUSTOMER_ID"],
        }
    ]

    rows = _allocate(
        seed=42,
        target_rows=3,
        fields=fields,
        identity_fields=("CUSTOMER_ID",),
        foreign_keys=foreign_keys,
        context=context,
    )

    assert len(rows) == 3
    assert {
        row["CUSTOMER_ID"]
        for row in rows
    }.issubset({"C1", "C2", "C3"})
    assert len({
        row["CUSTOMER_ID"]
        for row in rows
    }) == 3


def test_fk_identity_allocation_is_deterministic_for_same_seed() -> None:
    fields = [
        {
            "name": "CUSTOMER_ID",
            "type": "STRING",
            "identity": {},
        }
    ]

    foreign_keys = [
        {
            "child_fields": ["CUSTOMER_ID"],
            "parent_entity": "CUSTOMER",
            "parent_fields": ["CUSTOMER_ID"],
        }
    ]

    first_context = GenerationContext()
    first_context.add_rows(
        entity_name="CUSTOMER",
        rows=[
            {"CUSTOMER_ID": "C1"},
            {"CUSTOMER_ID": "C2"},
            {"CUSTOMER_ID": "C3"},
            {"CUSTOMER_ID": "C4"},
        ],
        identity_fields=("CUSTOMER_ID",),
    )

    second_context = GenerationContext()
    second_context.add_rows(
        entity_name="CUSTOMER",
        rows=[
            {"CUSTOMER_ID": "C1"},
            {"CUSTOMER_ID": "C2"},
            {"CUSTOMER_ID": "C3"},
            {"CUSTOMER_ID": "C4"},
        ],
        identity_fields=("CUSTOMER_ID",),
    )

    first = _allocate(
        seed=123,
        target_rows=4,
        fields=fields,
        identity_fields=("CUSTOMER_ID",),
        foreign_keys=foreign_keys,
        context=first_context,
    )

    second = _allocate(
        seed=123,
        target_rows=4,
        fields=fields,
        identity_fields=("CUSTOMER_ID",),
        foreign_keys=foreign_keys,
        context=second_context,
    )

    assert first == second


def test_composite_fk_identity_uses_complete_parent_tuples() -> None:
    context = GenerationContext()

    context.add_rows(
        entity_name="PARENT",
        rows=[
            {"A": "A1", "B": "B1"},
            {"A": "A2", "B": "B2"},
        ],
        identity_fields=("A", "B"),
    )

    fields = [
        {"name": "A", "type": "STRING", "identity": {}},
        {"name": "B", "type": "STRING", "identity": {}},
    ]

    foreign_keys = [
        {
            "child_fields": ["A", "B"],
            "parent_entity": "PARENT",
            "parent_fields": ["A", "B"],
        }
    ]

    rows = _allocate(
        seed=42,
        target_rows=2,
        fields=fields,
        identity_fields=("A", "B"),
        foreign_keys=foreign_keys,
        context=context,
    )

    assert len(rows) == 2
    assert {
        (row["A"], row["B"])
        for row in rows
    } == {
        ("A1", "B1"),
        ("A2", "B2"),
    }


def test_identity_capacity_is_enforced() -> None:
    fields = [_uniform_identity_field()]

    with pytest.raises(
        EntityGenerationError,
        match="only 5 unique identity combinations",
    ):
        _allocate(
            seed=42,
            target_rows=6,
            fields=fields,
            identity_fields=("ID",),
        )


def test_identity_allocation_is_deterministic_for_same_seed() -> None:
    fields = [_uniform_identity_field()]

    first = _allocate(
        seed=123,
        target_rows=5,
        fields=fields,
        identity_fields=("ID",),
    )

    second = _allocate(
        seed=123,
        target_rows=5,
        fields=fields,
        identity_fields=("ID",),
    )

    assert first == second


def test_chunked_cartesian_identity_allocation_matches_full_allocation() -> None:
    fields = [
        _sequential_identity_field(),
        {
            "name": "CODE",
            "type": "STRING",
            "generation": {
                "strategy": "RANDOM",
                "distribution": "CATEGORICAL",
                "parameters": {
                    "values": ["A", "B", "C", "D"],
                },
            },
        },
    ]

    full = _allocate(
        seed=42,
        target_rows=12,
        fields=fields,
        identity_fields=("ID", "CODE"),
    )

    chunks = [
        _allocate_chunk(
            seed=42,
            target_rows=12,
            row_start=0,
            row_count=4,
            fields=fields,
            identity_fields=("ID", "CODE"),
        ),
        _allocate_chunk(
            seed=42,
            target_rows=12,
            row_start=4,
            row_count=4,
            fields=fields,
            identity_fields=("ID", "CODE"),
        ),
        _allocate_chunk(
            seed=42,
            target_rows=12,
            row_start=8,
            row_count=4,
            fields=fields,
            identity_fields=("ID", "CODE"),
        ),
    ]

    chunked = [row for chunk in chunks for row in chunk]

    assert chunked == full
    assert len({
        (row["ID"], row["CODE"])
        for row in chunked
    }) == 12


def test_identity_allocation_is_unique() -> None:
    fields = [
        _sequential_identity_field(),
        {
            "name": "CODE",
            "type": "STRING",
            "generation": {
                "strategy": "RANDOM",
                "distribution": "CATEGORICAL",
                "parameters": {
                    "values": ["A", "B"],
                },
            },
        },
    ]

    rows = _allocate(
        seed=42,
        target_rows=4,
        fields=fields,
        identity_fields=("ID", "CODE"),
    )

    keys = {
        (row["ID"], row["CODE"])
        for row in rows
    }

    assert len(keys) == len(rows)


def test_large_sequential_population_allocates_only_requested_chunk() -> None:
    fields = [_sequential_identity_field()]

    rows = _allocate_chunk(
        seed=42,
        target_rows=10_000_000,
        row_start=5_000_000,
        row_count=50,
        fields=fields,
        identity_fields=("ID",),
    )

    assert len(rows) == 50
    assert rows[0] == {"ID": 5_000_001}
    assert rows[-1] == {"ID": 5_000_050}


def test_generate_allocates_identity_per_execution_chunk() -> None:
    entity = {
        "name": "TEST_ENTITY",
        "population": {
            "count": 125,
        },
        "fields": [
            _sequential_identity_field(),
        ],
        "identity": {
            "fields": ["ID"],
        },
    }

    context = GenerationContext()
    completed_chunks: list[tuple[int, int, int]] = []

    def on_chunk_completed(
        entity_name: str,
        chunk_number: int,
        total_chunks: int,
        generated_rows: int,
        chunk_rows: list[dict],
    ) -> None:
        completed_chunks.append(
            (
                chunk_number,
                total_chunks,
                len(chunk_rows),
            )
        )

    generator = EntityGenerator(seed=42)

    generated_rows = generator.generate(
        entity=entity,
        foreign_keys=[],
        context=context,
        chunk_size=50,
        on_chunk_completed=on_chunk_completed,
    )

    assert generated_rows == 125

    assert completed_chunks == [
        (1, 3, 50),
        (2, 3, 50),
        (3, 3, 25),
    ]

    rows = context.get_rows(
        entity_name="TEST_ENTITY",
    )

    assert rows == []

    key_space = context.get_key_space(
        entity_name="TEST_ENTITY",
        fields=("ID",),
    )

    assert len(key_space) == 125
    assert key_space == {
        (identity,)
        for identity in range(1, 126)
    }


def test_generate_can_start_from_a_later_chunk() -> None:
    entity = {
        "name": "TEST_ENTITY",
        "population": {
            "count": 125,
        },
        "fields": [
            _sequential_identity_field(),
        ],
        "identity": {
            "fields": ["ID"],
        },
    }

    context = GenerationContext()
    completed_chunks: list[tuple[int, int, int]] = []

    def on_chunk_completed(
        entity_name: str,
        chunk_number: int,
        total_chunks: int,
        generated_rows: int,
        chunk_rows: list[dict],
    ) -> None:
        completed_chunks.append(
            (
                chunk_number,
                total_chunks,
                len(chunk_rows),
            )
        )

    generator = EntityGenerator(seed=42)

    generated_rows = generator.generate(
        entity=entity,
        foreign_keys=[],
        context=context,
        chunk_size=50,
        start_chunk=3,
        on_chunk_completed=on_chunk_completed,
    )

    assert generated_rows == 25

    assert completed_chunks == [
        (3, 3, 25),
    ]

    rows = context.get_rows(
        entity_name="TEST_ENTITY",
    )

    assert rows == []

    key_space = context.get_key_space(
        entity_name="TEST_ENTITY",
        fields=("ID",),
    )

    assert key_space == {
        (identity,)
        for identity in range(101, 126)
    }


def test_restore_key_space_restores_identity_keys_without_rows() -> None:
    context = GenerationContext()

    context.restore_key_space(
        entity_name="CUSTOMER",
        identity_fields=("CUSTOMER_ID",),
        key_space={
            ("C1",),
            ("C2",),
            ("C3",),
        },
    )

    assert context.get_key_space(
        entity_name="CUSTOMER",
        fields=("CUSTOMER_ID",),
    ) == {
        ("C1",),
        ("C2",),
        ("C3",),
    }

    assert context.get_rows(
        entity_name="CUSTOMER",
    ) == []


def test_single_field_fk_uses_indexed_parent_key_space() -> None:
    context = GenerationContext()

    context.add_rows(
        entity_name="CUSTOMER",
        rows=[
            {"CUSTOMER_ID": "C1"},
            {"CUSTOMER_ID": "C2"},
            {"CUSTOMER_ID": "C3"},
        ],
        identity_fields=("CUSTOMER_ID",),
    )

    indexed_keys = context.get_indexed_key_space(
        entity_name="CUSTOMER",
        fields=("CUSTOMER_ID",),
    )

    assert indexed_keys == [
        ("C1",),
        ("C2",),
        ("C3",),
    ]

    assert context.get_key_space(
        entity_name="CUSTOMER",
        fields=("CUSTOMER_ID",),
    ) == {
        ("C1",),
        ("C2",),
        ("C3",),
    }

def _mandatory_parent_context(
    parent_keys: list[tuple],
    parent_fields: tuple[str, ...] = ("PARENT_ID",),
) -> GenerationContext:
    context = GenerationContext()
    context.restore_key_space(
        entity_name="PARENT",
        identity_fields=parent_fields,
        key_space=parent_keys,
    )
    return context


def test_mandatory_parent_participation_covers_every_parent_across_chunks() -> None:
    parent_keys = [(f"P{i}",) for i in range(1, 6)]
    context = _mandatory_parent_context(parent_keys)

    entity = {
        "name": "CHILD",
        "population": {"count": 5},
        "fields": [{"name": "PARENT_ID", "type": "STRING"}],
    }
    foreign_keys = [{
        "child_fields": ["PARENT_ID"],
        "parent_entity": "PARENT",
        "parent_fields": ["PARENT_ID"],
    }]
    mandatory_relationships = [{
        "child_fields": ("PARENT_ID",),
        "parent_entity": "PARENT",
        "parent_fields": ("PARENT_ID",),
    }]

    generated: list[dict] = []

    EntityGenerator(seed=42).generate(
        entity=entity,
        foreign_keys=foreign_keys,
        context=context,
        mandatory_relationships=mandatory_relationships,
        chunk_size=2,
        on_chunk_completed=lambda _entity, _chunk, _total, _count, rows:
            generated.extend(rows),
    )

    assert [row["PARENT_ID"] for row in generated] == [
        "P1", "P2", "P3", "P4", "P5"
    ]


def test_mandatory_parent_participation_uses_global_row_position_on_resume() -> None:
    parent_keys = [(f"P{i}",) for i in range(1, 4)]
    context = _mandatory_parent_context(parent_keys)

    entity = {
        "name": "CHILD",
        "population": {"count": 5},
        "fields": [{"name": "PARENT_ID", "type": "STRING"}],
    }
    foreign_keys = [{
        "child_fields": ["PARENT_ID"],
        "parent_entity": "PARENT",
        "parent_fields": ["PARENT_ID"],
    }]
    mandatory_relationships = [{
        "child_fields": ("PARENT_ID",),
        "parent_entity": "PARENT",
        "parent_fields": ("PARENT_ID",),
    }]

    generated: list[dict] = []

    EntityGenerator(seed=42).generate(
        entity=entity,
        foreign_keys=foreign_keys,
        context=context,
        mandatory_relationships=mandatory_relationships,
        chunk_size=2,
        start_chunk=2,
        on_chunk_completed=lambda _entity, _chunk, _total, _count, rows:
            generated.extend(rows),
    )

    # Global child row 3 must receive parent key 3, even when execution
    # resumes at chunk 2.
    assert generated[0]["PARENT_ID"] == "P3"


def test_mandatory_composite_parent_participation_preserves_complete_tuples() -> None:
    parent_keys = [
        ("T1", "P1"),
        ("T2", "P2"),
        ("T3", "P3"),
    ]
    context = _mandatory_parent_context(
        parent_keys,
        ("TENANT_ID", "PARENT_ID"),
    )

    entity = {
        "name": "CHILD",
        "population": {"count": 3},
        "fields": [
            {"name": "FK_TENANT_ID", "type": "STRING"},
            {"name": "FK_PARENT_ID", "type": "STRING"},
        ],
    }
    foreign_keys = [{
        "child_fields": ["FK_TENANT_ID", "FK_PARENT_ID"],
        "parent_entity": "PARENT",
        "parent_fields": ["TENANT_ID", "PARENT_ID"],
    }]
    mandatory_relationships = [{
        "child_fields": ("FK_TENANT_ID", "FK_PARENT_ID"),
        "parent_entity": "PARENT",
        "parent_fields": ("TENANT_ID", "PARENT_ID"),
    }]

    generated: list[dict] = []

    EntityGenerator(seed=42).generate(
        entity=entity,
        foreign_keys=foreign_keys,
        context=context,
        mandatory_relationships=mandatory_relationships,
        chunk_size=2,
        on_chunk_completed=lambda _entity, _chunk, _total, _count, rows:
            generated.extend(rows),
    )

    actual_tuples = [
        (row["FK_TENANT_ID"], row["FK_PARENT_ID"])
        for row in generated
    ]
    assert actual_tuples == parent_keys


def test_mandatory_parent_participation_rejects_insufficient_child_population() -> None:
    context = _mandatory_parent_context([
        ("P1",),
        ("P2",),
        ("P3",),
    ])

    entity = {
        "name": "CHILD",
        "population": {"count": 2},
        "fields": [{"name": "PARENT_ID", "type": "STRING"}],
    }
    foreign_keys = [{
        "child_fields": ["PARENT_ID"],
        "parent_entity": "PARENT",
        "parent_fields": ["PARENT_ID"],
    }]
    mandatory_relationships = [{
        "child_fields": ("PARENT_ID",),
        "parent_entity": "PARENT",
        "parent_fields": ("PARENT_ID",),
    }]

    with pytest.raises(
        EntityGenerationError,
        match="requires at least 3 child rows",
    ):
        EntityGenerator(seed=42).generate(
            entity=entity,
            foreign_keys=foreign_keys,
            context=context,
            mandatory_relationships=mandatory_relationships,
        )
