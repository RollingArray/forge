from dataclasses import dataclass
from typing import Any

from app.services.generation.executor import GenerationExecutor
from app.services.generation_planner import (
    GenerationEntityPlan,
    GenerationPlan,
)


@dataclass
class FakeAIService:
    values: list[str]

    def generate_semantic_values(
        self,
        *,
        description: str,
        mode: str,
        count: int,
    ) -> list[str]:
        assert description == "Realistic aerospace product name."
        assert mode == "UNIQUE"
        assert count == 3

        return self.values


class FakeSemanticStore:
    def __init__(
        self,
        persisted: dict[tuple[str, str], dict[str, Any]] | None = None,
    ) -> None:
        self.saved: list[dict[str, Any]] = []
        self.persisted = persisted or {}
        self.get_calls: list[dict[str, str]] = []

    def get(
        self,
        *,
        job_id: str,
        entity_name: str,
        field_name: str,
    ) -> dict[str, Any] | None:
        self.get_calls.append(
            {
                "job_id": job_id,
                "entity_name": entity_name,
                "field_name": field_name,
            }
        )

        return self.persisted.get(
            (entity_name, field_name)
        )

    def append_unique(
        self,
        *,
        job_id: str,
        entity_name: str,
        field_name: str,
        values: list[str],
    ) -> None:
        current = self.persisted.get((entity_name, field_name))

        if current is None:
            self.persisted[(entity_name, field_name)] = {
                "entity_name": entity_name,
                "field_name": field_name,
                "mode": "UNIQUE",
                "values": list(values),
            }
            return

        current["values"].extend(values)

    def save(
        self,
        *,
        job_id: str,
        entity_name: str,
        field_name: str,
        mode: str,
        values: list[str],
    ) -> None:
        self.saved.append(
            {
                "job_id": job_id,
                "entity_name": entity_name,
                "field_name": field_name,
                "mode": mode,
                "values": list(values),
            }
        )


def test_executor_persists_ai_generated_semantic_values(
    tmp_path,
    monkeypatch,
) -> None:
    monkeypatch.chdir(tmp_path)

    semantic_values = [
        "Hydraulic Pump",
        "Flight Control Computer",
        "Landing Gear Assembly",
    ]

    ai_service = FakeAIService(
        values=semantic_values,
    )

    semantic_store = FakeSemanticStore()

    executor = GenerationExecutor(
        seed=42,
        ai_service=ai_service,
        semantic_store=semantic_store,
    )

    specification = {
        "entities": [
            {
                "name": "PRODUCT",
                "population": {
                    "count": 3,
                },
                "fields": [
                    {
                        "name": "PRODUCT_NAME",
                        "type": "STRING",
                        "generation": {
                            "generator": "SEMANTIC",
                            "parameters": {
                                "description": (
                                    "Realistic aerospace product name."
                                ),
                                "mode": "UNIQUE",
                            },
                        },
                    },
                ],
            },
        ],
        "foreign_keys": [],
    }

    plan = GenerationPlan(
        entities=(
            GenerationEntityPlan(
                entity_name="PRODUCT",
                target_rows=3,
            ),
        ),
    )

    executor.execute(
        specification=specification,
        plan=plan,
        job_id="FORGE-SEMANTIC-TEST",
    )

    assert semantic_store.persisted[("PRODUCT", "PRODUCT_NAME")] == {
        "entity_name": "PRODUCT",
        "field_name": "PRODUCT_NAME",
        "mode": "UNIQUE",
        "values": semantic_values,
    }


class FakeCheckpointStore:
    def __init__(self, checkpoint=None) -> None:
        self.checkpoint = checkpoint

    def get(self, job_id: str):
        return self.checkpoint


def test_executor_detects_existing_checkpoint() -> None:
    executor = GenerationExecutor(
        seed=42,
        checkpoint_store=FakeCheckpointStore(
            checkpoint={
                "job_id": "FORGE-TEST",
                "entities": {},
            },
        ),
    )

    assert executor.has_existing_checkpoint(
        "FORGE-TEST",
    )


def test_executor_detects_missing_checkpoint() -> None:
    executor = GenerationExecutor(
        seed=42,
        checkpoint_store=FakeCheckpointStore(),
    )

    assert not executor.has_existing_checkpoint(
        "FORGE-TEST",
    )


class _FakeCheckpointStore:
    def __init__(self, checkpoint=None):
        self._checkpoint = checkpoint

    def get(self, job_id):
        return self._checkpoint


def test_get_start_chunk_returns_one_without_checkpoint() -> None:
    from app.services.generation.executor import GenerationExecutor

    executor = GenerationExecutor(
        seed=42,
        checkpoint_store=_FakeCheckpointStore(),
    )

    assert executor._get_start_chunk(
        job_id="FORGE-TEST",
        entity_name="CUSTOMER",
    ) == 1


def test_get_start_chunk_returns_first_uncommitted_chunk() -> None:
    from app.services.generation.executor import GenerationExecutor

    checkpoint = {
        "entities": {
            "CUSTOMER": {
                "committed_chunks": [1, 2, 3, 4, 5, 6],
            },
        },
    }

    executor = GenerationExecutor(
        seed=42,
        checkpoint_store=_FakeCheckpointStore(checkpoint),
    )

    assert executor._get_start_chunk(
        job_id="FORGE-TEST",
        entity_name="CUSTOMER",
    ) == 7


def test_get_start_chunk_handles_non_contiguous_committed_chunks() -> None:
    from app.services.generation.executor import GenerationExecutor

    checkpoint = {
        "entities": {
            "CUSTOMER": {
                "committed_chunks": [1, 2, 4, 5],
            },
        },
    }

    executor = GenerationExecutor(
        seed=42,
        checkpoint_store=_FakeCheckpointStore(checkpoint),
    )

    assert executor._get_start_chunk(
        job_id="FORGE-TEST",
        entity_name="CUSTOMER",
    ) == 3


class FakeArtifactReader:
    def __init__(self, key_space):
        self.key_space = key_space
        self.calls = []

    def get_entity_key_space(
        self,
        *,
        job_id,
        entity_name,
        identity_fields,
    ):
        self.calls.append(
            {
                "job_id": job_id,
                "entity_name": entity_name,
                "identity_fields": identity_fields,
            }
        )
        return set(self.key_space)


def test_restore_entity_key_space_from_artifacts() -> None:
    from app.services.generation.context import GenerationContext

    artifact_reader = FakeArtifactReader(
        {
            ("C1",),
            ("C2",),
            ("C3",),
        }
    )

    executor = GenerationExecutor(
        seed=42,
        artifact_reader=artifact_reader,
    )

    context = GenerationContext()

    executor._restore_entity_key_space(
        job_id="FORGE-TEST",
        entity_name="CUSTOMER",
        identity_fields=("CUSTOMER_ID",),
        field_types={
            "CUSTOMER_ID": "STRING",
        },
        context=context,
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

    assert artifact_reader.calls == [
        {
            "job_id": "FORGE-TEST",
            "entity_name": "CUSTOMER",
            "identity_fields": ("CUSTOMER_ID",),
        },
    ]


def test_entity_is_fully_committed_when_all_chunks_are_present() -> None:
    executor = GenerationExecutor(
        seed=42,
        checkpoint_store=FakeCheckpointStore(
            checkpoint={
                "entities": {
                    "CUSTOMER": {
                        "total_chunks": 3,
                        "committed_chunks": [1, 2, 3],
                    },
                },
            },
        ),
    )

    assert executor._is_entity_fully_committed(
        job_id="FORGE-TEST",
        entity_name="CUSTOMER",
        total_chunks=3,
    )


def test_entity_is_not_fully_committed_when_a_chunk_is_missing() -> None:
    executor = GenerationExecutor(
        seed=42,
        checkpoint_store=FakeCheckpointStore(
            checkpoint={
                "entities": {
                    "CUSTOMER": {
                        "total_chunks": 3,
                        "committed_chunks": [1, 2],
                    },
                },
            },
        ),
    )

    assert not executor._is_entity_fully_committed(
        job_id="FORGE-TEST",
        entity_name="CUSTOMER",
        total_chunks=3,
    )


def test_entity_is_not_fully_committed_for_non_contiguous_chunks() -> None:
    executor = GenerationExecutor(
        seed=42,
        checkpoint_store=FakeCheckpointStore(
            checkpoint={
                "entities": {
                    "CUSTOMER": {
                        "total_chunks": 3,
                        "committed_chunks": [1, 3],
                    },
                },
            },
        ),
    )

    assert not executor._is_entity_fully_committed(
        job_id="FORGE-TEST",
        entity_name="CUSTOMER",
        total_chunks=3,
    )


def test_restore_entity_key_space_converts_artifact_identity_types() -> None:
    from app.services.generation.context import GenerationContext

    artifact_reader = FakeArtifactReader(
        {
            ("101",),
            ("102",),
            ("103",),
        }
    )

    executor = GenerationExecutor(
        seed=42,
        artifact_reader=artifact_reader,
    )

    context = GenerationContext()

    executor._restore_entity_key_space(
        job_id="FORGE-TEST",
        entity_name="CUSTOMER",
        identity_fields=("CUSTOMER_ID",),
        field_types={
            "CUSTOMER_ID": "INTEGER",
        },
        context=context,
    )

    assert context.get_key_space(
        entity_name="CUSTOMER",
        fields=("CUSTOMER_ID",),
    ) == {
        (101,),
        (102,),
        (103,),
    }


def test_executor_skips_fully_committed_entity_and_restores_keys(
    tmp_path,
    monkeypatch,
) -> None:
    monkeypatch.chdir(tmp_path)

    artifact_reader = FakeArtifactReader(
        {
            ("C1",),
            ("C2",),
            ("C3",),
        }
    )

    checkpoint_store = FakeCheckpointStore(
        checkpoint={
            "entities": {
                "CUSTOMER": {
                    "target_rows": 3,
                    "chunk_size": 50,
                    "total_chunks": 1,
                    "committed_chunks": [1],
                    "committed_rows": 3,
                },
            },
        },
    )

    executor = GenerationExecutor(
        seed=42,
        checkpoint_store=checkpoint_store,
        artifact_reader=artifact_reader,
    )

    specification = {
        "entities": [
            {
                "name": "CUSTOMER",
                "population": {
                    "count": 3,
                },
                "identity": {
                    "fields": ["CUSTOMER_ID"],
                },
                "fields": [
                    {
                        "name": "CUSTOMER_ID",
                        "type": "STRING",
                        "identity": {},
                    },
                ],
            },
        ],
        "foreign_keys": [],
    }

    plan = GenerationPlan(
        entities=(
            GenerationEntityPlan(
                entity_name="CUSTOMER",
                target_rows=3,
            ),
        ),
    )

    result = executor.execute(
        specification=specification,
        plan=plan,
        job_id="FORGE-TEST",
    )

    assert result.entities[0].entity_name == "CUSTOMER"
    assert result.entities[0].target_rows == 3
    assert result.entities[0].generated_rows == 3

    assert result.context.get_key_space(
        entity_name="CUSTOMER",
        fields=("CUSTOMER_ID",),
    ) == {
        ("C1",),
        ("C2",),
        ("C3",),
    }

    assert result.context.get_rows(
        entity_name="CUSTOMER",
    ) == []

    assert artifact_reader.calls == [
        {
            "job_id": "FORGE-TEST",
            "entity_name": "CUSTOMER",
            "identity_fields": ("CUSTOMER_ID",),
        },
    ]


def test_get_committed_rows_returns_zero_without_checkpoint() -> None:
    executor = GenerationExecutor(
        seed=42,
        checkpoint_store=FakeCheckpointStore(),
    )

    assert executor._get_committed_rows(
        job_id="FORGE-TEST",
        entity_name="CUSTOMER",
    ) == 0


def test_get_durable_generated_rows_includes_previous_committed_rows() -> None:
    executor = GenerationExecutor(
        seed=42,
        checkpoint_store=FakeCheckpointStore(
            checkpoint={
                "entities": {
                    "CUSTOMER": {
                        "committed_rows": 300,
                    },
                },
            },
        ),
    )

    assert executor._get_durable_generated_rows(
        job_id="FORGE-TEST",
        entity_name="CUSTOMER",
        generated_rows=700,
    ) == 1000


def test_executor_resumes_partial_entity_from_checkpoint() -> None:
    from app.services.generation.context import GenerationContext

    semantic_values = [
        f"Product {index:03d}"
        for index in range(1, 126)
    ]

    semantic_store = FakeSemanticStore(
        persisted={
            ("PRODUCT", "PRODUCT_NAME"): {
                "entity_name": "PRODUCT",
                "field_name": "PRODUCT_NAME",
                "mode": "UNIQUE",
                "values": semantic_values,
            },
        },
    )

    checkpoint_store = FakeCheckpointStore(
        checkpoint={
            "entities": {
                "PRODUCT": {
                    "target_rows": 125,
                    "chunk_size": 50,
                    "total_chunks": 3,
                    "committed_chunks": [1, 2],
                    "committed_rows": 100,
                },
            },
        },
    )

    artifact_reader = FakeArtifactReader(
        {
            (index,)
            for index in range(1, 101)
        }
    )

    from app.services.generation.artifact_writer import (
        GenerationArtifactWriter,
    )

    artifact_writer = GenerationArtifactWriter()
    artifact_writer.initialize_job("FORGE-RESUME-TEST")

    artifact_writer.write_chunk(
        "FORGE-RESUME-TEST",
        "PRODUCT",
        1,
        [
            {
                "PRODUCT_ID": f"P{index:03d}",
                "PRODUCT_NAME": semantic_values[index - 1],
            }
            for index in range(1, 51)
        ],
    )

    artifact_writer.write_chunk(
        "FORGE-RESUME-TEST",
        "PRODUCT",
        2,
        [
            {
                "PRODUCT_ID": f"P{index:03d}",
                "PRODUCT_NAME": semantic_values[index - 1],
            }
            for index in range(51, 101)
        ],
    )

    executor = GenerationExecutor(
        seed=42,
        ai_service=None,
        semantic_store=semantic_store,
        checkpoint_store=checkpoint_store,
        artifact_reader=artifact_reader,
    )

    specification = {
        "entities": [
            {
                "name": "PRODUCT",
                "population": {
                    "count": 125,
                },
                "identity": {
                    "fields": ["PRODUCT_ID"],
                },
                "fields": [
                    {
                        "name": "PRODUCT_ID",
                        "type": "IDENTIFIER",
                        "identity": {
                            "strategy": "SEQUENTIAL_ID",
                        },
                    },
                    {
                        "name": "PRODUCT_NAME",
                        "type": "STRING",
                        "generation": {
                            "generator": "SEMANTIC",
                            "parameters": {
                                "description": (
                                    "Realistic aerospace product name."
                                ),
                                "mode": "UNIQUE",
                            },
                        },
                    },
                ],
            },
        ],
        "foreign_keys": [],
    }

    plan = GenerationPlan(
        entities=(
            GenerationEntityPlan(
                entity_name="PRODUCT",
                target_rows=125,
            ),
        ),
    )

    result = executor.execute(
        specification=specification,
        plan=plan,
        job_id="FORGE-RESUME-TEST",
    )

    assert result.entities[0].generated_rows == 125

    assert result.context.get_key_space(
        entity_name="PRODUCT",
        fields=("PRODUCT_ID",),
    ) == {
        (index,)
        for index in range(1, 126)
    }

    assert semantic_store.get_calls == [
        {
            "job_id": "FORGE-RESUME-TEST",
            "entity_name": "PRODUCT",
            "field_name": "PRODUCT_NAME",
        },
    ]

    assert semantic_store.saved == []

    assert result.context.get_semantic_values(
        entity_name="PRODUCT",
        field_name="PRODUCT_NAME",
        chunk_number=3,
    ) == semantic_values[100:125]


def test_resume_with_real_artifacts_restores_typed_identity_keys(tmp_path):
    from app.services.generation.artifact_reader import GenerationArtifactReader
    from app.services.generation.artifact_writer import GenerationArtifactWriter
    from app.services.generation_checkpoint_store import GenerationCheckpointStore
    from app.services.generation_semantic_store import GenerationSemanticStore

    job_id = "FORGE-REAL-RESUME-TEST"

    artifact_writer = GenerationArtifactWriter()
    artifact_writer._data_directory = tmp_path

    artifact_reader = GenerationArtifactReader()
    artifact_reader._data_directory = tmp_path

    checkpoint_store = GenerationCheckpointStore()
    checkpoint_store._root = tmp_path / "generation"

    semantic_store = GenerationSemanticStore()
    semantic_store._root = tmp_path / "generation"

    artifact_writer.initialize_job(job_id)

    semantic_values = [
        f"Product {index:03d}"
        for index in range(1, 126)
    ]

    semantic_store.save(
        job_id=job_id,
        entity_name="PRODUCT",
        field_name="PRODUCT_NAME",
        mode="UNIQUE",
        values=semantic_values,
    )

    artifact_writer.write_chunk(
        job_id,
        "PRODUCT",
        1,
        [
            {
                "PRODUCT_ID": index,
                "PRODUCT_NAME": semantic_values[index - 1],
            }
            for index in range(1, 51)
        ],
    )

    artifact_writer.write_chunk(
        job_id,
        "PRODUCT",
        2,
        [
            {
                "PRODUCT_ID": index,
                "PRODUCT_NAME": semantic_values[index - 1],
            }
            for index in range(51, 101)
        ],
    )

    checkpoint_store.save(
        job_id=job_id,
        seed=42,
        entities={
            "PRODUCT": {
                "target_rows": 125,
                "chunk_size": 50,
                "total_chunks": 3,
                "committed_chunks": [1, 2],
                "committed_rows": 100,
            }
        },
    )

    specification = {
        "entities": [
            {
                "name": "PRODUCT",
                "population": {
                    "count": 125,
                },
                "identity": {
                    "fields": ["PRODUCT_ID"],
                },
                "fields": [
                    {
                        "name": "PRODUCT_ID",
                        "type": "IDENTIFIER",
                        "identity": {
                            "strategy": "SEQUENTIAL_ID",
                        },
                    },
                    {
                        "name": "PRODUCT_NAME",
                        "type": "STRING",
                        "generation": {
                            "generator": "SEMANTIC",
                            "parameters": {
                                "description": (
                                    "Realistic aerospace product name."
                                ),
                                "mode": "UNIQUE",
                            },
                        },
                    },
                ],
            },
        ],
        "foreign_keys": [],
    }

    plan = GenerationPlan(
        entities=(
            GenerationEntityPlan(
                entity_name="PRODUCT",
                target_rows=125,
            ),
        ),
    )

    executor = GenerationExecutor(
        seed=42,
        ai_service=None,
        semantic_store=semantic_store,
        checkpoint_store=checkpoint_store,
        artifact_reader=artifact_reader,
        artifact_writer=artifact_writer,
    )

    result = executor.execute(
        specification=specification,
        plan=plan,
        job_id=job_id,
    )

    assert result.entities[0].generated_rows == 125

    identity_keys = result.context.get_key_space(
        entity_name="PRODUCT",
        fields=("PRODUCT_ID",),
    )

    assert identity_keys == {
        (index,)
        for index in range(1, 126)
    }

    assert all(
        isinstance(key[0], int)
        for key in identity_keys
    )

    rows = list(
        artifact_reader.iter_entity_chunks(
            job_id=job_id,
            entity_name="PRODUCT",
        )
    )

    assert len(rows) == 125

    assert {
        int(row["PRODUCT_ID"])
        for row in rows
    } == set(range(1, 126))

    assert all(
        row["PRODUCT_NAME"]
        == semantic_values[int(row["PRODUCT_ID"]) - 1]
        for row in rows
    )
