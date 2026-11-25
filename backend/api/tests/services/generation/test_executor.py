from dataclasses import dataclass
from typing import Any
from unittest.mock import Mock

from datetime import datetime, timezone

from app.models.generation_persistence import (
    GenerationArtifactEvidence,
    GenerationCheckpointManifest,
    GenerationChunkEvidence,
    GenerationEntityCheckpoint,
    GenerationFinalization,
    GenerationFinalizationStatus,
)


def make_v2_manifest(
    *,
    entity_name: str = "CUSTOMER",
    target_rows: int = 0,
    chunk_size: int = 50,
    committed_chunks: tuple[int, ...] = (),
    finalized: bool = False,
) -> GenerationCheckpointManifest:
    """Build valid v2 checkpoint evidence for executor unit tests."""
    now = datetime.now(timezone.utc)

    chunks = []
    for number in sorted(committed_chunks):
        row_start = (number - 1) * chunk_size
        row_count = min(chunk_size, target_rows - row_start)
        if row_count <= 0:
            raise ValueError(
                f"Chunk {number} exceeds target_rows={target_rows}"
            )

        chunks.append(
            GenerationChunkEvidence(
                chunk_number=number,
                row_start=row_start,
                row_count=row_count,
                artifact=GenerationArtifactEvidence(
                    path=(
                        f"generated/{entity_name}/chunks/"
                        f"chunk_{number:06d}.csv"
                    ),
                    size_bytes=1,
                    sha256="a" * 64,
                ),
                committed_at=now,
            )
        )

    finalization = GenerationFinalization(
        status=(
            GenerationFinalizationStatus.COMMITTED
            if finalized
            else GenerationFinalizationStatus.PENDING
        ),
        output=(
            GenerationArtifactEvidence(
                path=f"generated/{entity_name}/{entity_name}.csv",
                size_bytes=1,
                sha256="b" * 64,
            )
            if finalized
            else None
        ),
    )

    return GenerationCheckpointManifest(
        data_model_id="FORGE-TEST-MODEL",
        job_id="FORGE-TEST",
        specification_hash="c" * 64,
        seed=42,
        chunk_size=chunk_size,
        algorithm_version="forge-generation-v2",
        attempt_id="test-attempt",
        entities={
            entity_name: GenerationEntityCheckpoint(
                target_rows=target_rows,
                chunks=chunks,
                finalization=finalization,
            )
        },
        created_at=now,
        updated_at=now,
    )


class V2FakeCheckpointStore:
    """Small read-only checkpoint-store fake using the v2 manifest contract."""

    def __init__(self, manifest=None) -> None:
        self.manifest = manifest

    def get(self, *, data_model_id: str, job_id: str):
        return self.manifest

    def get_committed_rows(
        self,
        *,
        data_model_id: str,
        job_id: str,
        entity_name: str,
    ) -> int:
        entity = (
            self.manifest.entities.get(entity_name)
            if self.manifest is not None
            else None
        )
        return entity.committed_rows if entity is not None else 0

    def get_entity_state(
        self,
        *,
        data_model_id: str,
        job_id: str,
        entity_name: str,
    ):
        if self.manifest is None:
            return None
        return self.manifest.entities.get(entity_name)

    def is_chunk_committed(
        self,
        *,
        data_model_id: str,
        job_id: str,
        entity_name: str,
        chunk_number: int,
    ) -> bool:
        entity = self.get_entity_state(
            data_model_id=data_model_id,
            job_id=job_id,
            entity_name=entity_name,
        )
        return entity is not None and any(
            chunk.chunk_number == chunk_number
            for chunk in entity.chunks
        )



import pytest

from app.services.generation.executor import GenerationExecutor
from app.services.generation_planner import (
    GenerationEntityPlan,
    GenerationPlan,
    GenerationPlanner,
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
        exclude_values: list[str] | None = None,
        on_call_completed=None,
        on_progress=None,
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
        data_model_id: str,
        job_id: str,
        entity_name: str,
        field_name: str,
    ) -> dict[str, Any] | None:
        self.get_calls.append(
            {
                "data_model_id": data_model_id,
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
        data_model_id: str,
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
        data_model_id: str,
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
    from app.constants.generation import GENERATION_ALGORITHM_VERSION
    from app.services.generation.artifact_reader import GenerationArtifactReader
    from app.services.generation.artifact_writer import GenerationArtifactWriter
    from app.services.generation.executor import GenerationExecutor
    from app.services.generation_semantic_store import GenerationSemanticStore
    from app.services.generation_checkpoint_store import GenerationCheckpointStore

    semantic_values = [
        "Hydraulic Pump",
        "Flight Control Computer",
        "Landing Gear Assembly",
    ]

    ai_service = FakeAIService(values=semantic_values)

    semantic_store = GenerationSemanticStore()
    semantic_store._root = tmp_path / "semantic"

    data_model_id = "FORGE-SEMANTIC-MODEL"
    job_id = "FORGE-SEMANTIC-TEST"
    attempt_id = "semantic-persistence-attempt"
    artifact_directory = tmp_path / "artifacts"

    specification = {
        "entities": [
            {
                "name": "PRODUCT",
                "population": {"count": 3},
                "fields": [
                    {
                        "name": "PRODUCT_NAME",
                        "type": "STRING",
                        "generation": {
                            "generator": "SEMANTIC",
                            "parameters": {
                                "description": "Realistic aerospace product name.",
                                "mode": "UNIQUE",
                            },
                        },
                    },
                ],
            },
        ],
        "foreign_keys": [],
    }

    checkpoint_store = GenerationCheckpointStore()
    checkpoint_store._root = artifact_directory / "data_model"
    checkpoint_store.initialize(
        data_model_id=data_model_id,
        job_id=job_id,
        specification=specification,
        seed=42,
        chunk_size=50,
        algorithm_version=GENERATION_ALGORITHM_VERSION,
        attempt_id=attempt_id,
        entity_targets={"PRODUCT": 3},
    )

    artifact_writer = GenerationArtifactWriter(checkpoint_store=checkpoint_store)
    artifact_writer._data_directory = artifact_directory

    artifact_reader = GenerationArtifactReader(checkpoint_store=checkpoint_store)
    artifact_reader._data_directory = artifact_directory

    executor = GenerationExecutor(
        seed=42,
        ai_service=ai_service,
        semantic_store=semantic_store,
        checkpoint_store=checkpoint_store,
        artifact_writer=artifact_writer,
        artifact_reader=artifact_reader,
    )

    plan = GenerationPlan(
        entities=(
            GenerationEntityPlan(
                entity_name="PRODUCT",
                target_rows=3,
            ),
        ),
    )

    executor.execute(
        data_model_id=data_model_id,
        specification=specification,
        plan=plan,
        job_id=job_id,
    )

    expected_by_row = {
        index: value
        for index, value in enumerate(semantic_values)
    }

    assert semantic_store.get_unique_values(
        data_model_id=data_model_id,
        job_id=job_id,
        entity_name="PRODUCT",
        field_name="PRODUCT_NAME",
    ) == expected_by_row

    persisted = semantic_store.get(
        data_model_id=data_model_id,
        job_id=job_id,
        entity_name="PRODUCT",
        field_name="PRODUCT_NAME",
    )

    assert persisted is not None
    assert persisted["mode"] == "UNIQUE"
    assert persisted["values_by_row"] == {
        str(index): value
        for index, value in expected_by_row.items()
    }

    manifest = checkpoint_store.get(data_model_id, job_id)
    assert manifest is not None
    assert manifest.attempt_id == attempt_id
    assert manifest.entities["PRODUCT"].committed_rows == 3



class FakeCheckpointStore:
    def __init__(self, checkpoint=None) -> None:
        self.checkpoint = checkpoint

    def get(self, *, data_model_id: str, job_id: str):
        return self.checkpoint


def test_executor_uses_250_row_checkpoint_chunks(
    tmp_path,
    monkeypatch,
) -> None:
    from app.constants.generation import GENERATION_ALGORITHM_VERSION
    from app.services.generation.artifact_reader import GenerationArtifactReader
    from app.services.generation.artifact_writer import GenerationArtifactWriter
    from app.services.generation.executor import GenerationExecutor
    from app.services.generation_checkpoint_store import GenerationCheckpointStore

    data_model_id = "FORGE-CHUNK-SIZE-MODEL"
    job_id = "FORGE-CHUNK-SIZE-TEST"
    attempt_id = "chunk-size-attempt"
    chunk_size = 250
    artifact_directory = tmp_path / "artifacts"

    specification = {
        "entities": [
            {
                "name": "PRODUCT",
                "population": {"count": 251},
                "identity": {"fields": ["PRODUCT_ID"]},
                "fields": [
                    {
                        "name": "PRODUCT_ID",
                        "type": "IDENTIFIER",
                        "identity": {"strategy": "SEQUENTIAL_ID"},
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
                target_rows=251,
            ),
        ),
    )

    checkpoint_store = GenerationCheckpointStore()
    checkpoint_store._root = artifact_directory / "data_model"
    checkpoint_store.initialize(
        data_model_id=data_model_id,
        job_id=job_id,
        specification=specification,
        seed=42,
        chunk_size=chunk_size,
        algorithm_version=GENERATION_ALGORITHM_VERSION,
        attempt_id=attempt_id,
        entity_targets={"PRODUCT": 251},
    )

    artifact_writer = GenerationArtifactWriter(checkpoint_store=checkpoint_store)
    artifact_writer._data_directory = artifact_directory

    artifact_reader = GenerationArtifactReader(checkpoint_store=checkpoint_store)
    artifact_reader._data_directory = artifact_directory

    executor = GenerationExecutor(
        seed=42,
        checkpoint_store=checkpoint_store,
        artifact_writer=artifact_writer,
        artifact_reader=artifact_reader,
    )

    completed_chunks = []

    def record_chunk(
        entity_name,
        chunk_number,
        total_chunks,
        generated_rows,
        chunk_rows,
        *_,
    ) -> None:
        completed_chunks.append(
            (entity_name, chunk_number, total_chunks, len(chunk_rows))
        )

    result = executor.execute(
        data_model_id=data_model_id,
        specification=specification,
        plan=plan,
        job_id=job_id,
        on_chunk_completed=record_chunk,
    )

    assert result.entities[0].generated_rows == 251
    assert completed_chunks == [
        ("PRODUCT", 1, 2, 250),
        ("PRODUCT", 2, 2, 1),
    ]

    manifest = checkpoint_store.get(data_model_id, job_id)
    assert manifest is not None
    assert manifest.chunk_size == 250
    assert manifest.attempt_id == attempt_id

    entity_state = manifest.entities["PRODUCT"]
    assert entity_state.committed_rows == 251
    assert sorted(chunk.chunk_number for chunk in entity_state.chunks) == [1, 2]



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
        "FORGE-TEST-MODEL",
        "FORGE-TEST",
    )


def test_executor_detects_missing_checkpoint() -> None:
    executor = GenerationExecutor(
        seed=42,
        checkpoint_store=FakeCheckpointStore(),
    )

    assert not executor.has_existing_checkpoint(
        "FORGE-TEST-MODEL",
        "FORGE-TEST",
    )


class _FakeCheckpointStore(V2FakeCheckpointStore):
    """Alias retained for the focused executor helper tests."""


def test_get_start_chunk_returns_one_without_checkpoint() -> None:
    executor = GenerationExecutor(
        seed=42,
        checkpoint_store=_FakeCheckpointStore(),
    )

    assert executor._get_start_chunk(
        data_model_id="FORGE-TEST-MODEL",
        job_id="FORGE-TEST",
        entity_name="CUSTOMER",
    ) == 1


def test_get_start_chunk_returns_first_uncommitted_chunk() -> None:
    manifest = make_v2_manifest(
        target_rows=350,
        chunk_size=50,
        committed_chunks=(1, 2, 3, 4, 5, 6),
    )
    executor = GenerationExecutor(
        seed=42,
        checkpoint_store=_FakeCheckpointStore(manifest),
    )

    assert executor._get_start_chunk(
        data_model_id="FORGE-TEST-MODEL",
        job_id="FORGE-TEST",
        entity_name="CUSTOMER",
    ) == 7


def test_get_start_chunk_handles_non_contiguous_committed_chunks() -> None:
    manifest = make_v2_manifest(
        target_rows=250,
        chunk_size=50,
        committed_chunks=(1, 2, 4, 5),
    )
    executor = GenerationExecutor(
        seed=42,
        checkpoint_store=_FakeCheckpointStore(manifest),
    )

    assert executor._get_start_chunk(
        data_model_id="FORGE-TEST-MODEL",
        job_id="FORGE-TEST",
        entity_name="CUSTOMER",
    ) == 3


class FakeArtifactReader:
    def __init__(self, key_space):
        if isinstance(key_space, dict):
            self.key_space_by_row = dict(key_space)
        else:
            ordered = sorted(key_space, key=repr)
            self.key_space_by_row = {
                row_index: key
                for row_index, key in enumerate(ordered)
            }
        self.calls = []

    def get_identity_keys_by_row(
        self,
        *,
        data_model_id,
        job_id,
        entity_name,
        identity_fields,
    ):
        self.calls.append(
            {
                "data_model_id": data_model_id,
                "job_id": job_id,
                "entity_name": entity_name,
                "identity_fields": identity_fields,
            }
        )
        return dict(self.key_space_by_row)


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
        data_model_id="FORGE-TEST-MODEL",
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
            "data_model_id": "FORGE-TEST-MODEL",
            "job_id": "FORGE-TEST",
            "entity_name": "CUSTOMER",
            "identity_fields": ("CUSTOMER_ID",),
        },
    ]


def test_entity_is_fully_committed_when_all_chunks_and_output_are_committed() -> None:
    manifest = make_v2_manifest(
        target_rows=3,
        chunk_size=1,
        committed_chunks=(1, 2, 3),
        finalized=True,
    )
    executor = GenerationExecutor(
        seed=42,
        checkpoint_store=V2FakeCheckpointStore(manifest),
    )

    assert executor._is_entity_fully_committed(
        data_model_id="FORGE-TEST-MODEL",
        job_id="FORGE-TEST",
        entity_name="CUSTOMER",
        total_chunks=3,
    )


def test_entity_is_not_fully_committed_when_a_chunk_is_missing() -> None:
    manifest = make_v2_manifest(
        target_rows=3,
        chunk_size=1,
        committed_chunks=(1, 2),
        finalized=False,
    )
    executor = GenerationExecutor(
        seed=42,
        checkpoint_store=V2FakeCheckpointStore(manifest),
    )

    assert not executor._is_entity_fully_committed(
        data_model_id="FORGE-TEST-MODEL",
        job_id="FORGE-TEST",
        entity_name="CUSTOMER",
        total_chunks=3,
    )


def test_entity_is_not_fully_committed_for_non_contiguous_chunks() -> None:
    manifest = make_v2_manifest(
        target_rows=3,
        chunk_size=1,
        committed_chunks=(1, 3),
        finalized=False,
    )
    executor = GenerationExecutor(
        seed=42,
        checkpoint_store=V2FakeCheckpointStore(manifest),
    )

    assert not executor._is_entity_fully_committed(
        data_model_id="FORGE-TEST-MODEL",
        job_id="FORGE-TEST",
        entity_name="CUSTOMER",
        total_chunks=3,
    )


def test_entity_is_not_fully_committed_until_finalization_is_committed() -> None:
    manifest = make_v2_manifest(
        target_rows=3,
        chunk_size=1,
        committed_chunks=(1, 2, 3),
        finalized=False,
    )
    executor = GenerationExecutor(
        seed=42,
        checkpoint_store=V2FakeCheckpointStore(manifest),
    )

    assert not executor._is_entity_fully_committed(
        data_model_id="FORGE-TEST-MODEL",
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
        data_model_id="FORGE-TEST-MODEL",
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

    checkpoint_store = V2FakeCheckpointStore(
        make_v2_manifest(
            entity_name="CUSTOMER",
            target_rows=3,
            chunk_size=50,
            committed_chunks=(1,),
            finalized=True,
        )
    )

    artifact_writer = Mock()

    executor = GenerationExecutor(
        seed=42,
        checkpoint_store=checkpoint_store,
        artifact_reader=artifact_reader,
        artifact_writer=artifact_writer,
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
        data_model_id="FORGE-TEST-MODEL",
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
            "data_model_id": "FORGE-TEST-MODEL",
            "job_id": "FORGE-TEST",
            "entity_name": "CUSTOMER",
            "identity_fields": ("CUSTOMER_ID",),
        },
    ]


def test_get_committed_rows_returns_zero_without_checkpoint() -> None:
    executor = GenerationExecutor(
        seed=42,
        checkpoint_store=V2FakeCheckpointStore(),
    )

    assert executor._get_committed_rows(
        data_model_id="FORGE-TEST-MODEL",
        job_id="FORGE-TEST",
        entity_name="CUSTOMER",
    ) == 0


def test_get_durable_generated_rows_returns_checkpoint_total() -> None:
    manifest = make_v2_manifest(
        target_rows=300,
        chunk_size=50,
        committed_chunks=(1, 2, 3, 4, 5, 6),
    )
    executor = GenerationExecutor(
        seed=42,
        checkpoint_store=V2FakeCheckpointStore(manifest),
    )

    assert executor._get_durable_generated_rows(
        data_model_id="FORGE-TEST-MODEL",
        job_id="FORGE-TEST",
        entity_name="CUSTOMER",
    ) == 300


def test_executor_resumes_partial_entity_from_checkpoint(tmp_path) -> None:
    from app.constants.generation import GENERATION_ALGORITHM_VERSION
    from app.services.generation.artifact_reader import GenerationArtifactReader
    from app.services.generation.artifact_writer import GenerationArtifactWriter
    from app.services.generation.executor import GenerationExecutor
    from app.services.generation_checkpoint_store import GenerationCheckpointStore
    from app.services.generation_semantic_store import GenerationSemanticStore

    data_model_id = "FORGE-RESUME-MODEL"
    job_id = "FORGE-RESUME-TEST"
    attempt_id = "resume-attempt-001"
    chunk_size = 50

    semantic_values = [
        f"Product {index:03d}"
        for index in range(1, 126)
    ]

    specification = {
        "entities": [
            {
                "name": "PRODUCT",
                "population": {"count": 125},
                "identity": {"fields": ["PRODUCT_ID"]},
                "fields": [
                    {
                        "name": "PRODUCT_ID",
                        "type": "IDENTIFIER",
                        "identity": {"strategy": "SEQUENTIAL_ID"},
                    },
                    {
                        "name": "PRODUCT_NAME",
                        "type": "STRING",
                        "generation": {
                            "generator": "SEMANTIC",
                            "parameters": {
                                "description": "Realistic aerospace product name.",
                                "mode": "UNIQUE",
                            },
                        },
                    },
                ],
            },
        ],
        "foreign_keys": [],
    }

    checkpoint_store = GenerationCheckpointStore()
    checkpoint_store._root = tmp_path / "data_model"

    checkpoint_store.initialize(
        data_model_id=data_model_id,
        job_id=job_id,
        specification=specification,
        seed=42,
        chunk_size=chunk_size,
        algorithm_version=GENERATION_ALGORITHM_VERSION,
        attempt_id=attempt_id,
        entity_targets={"PRODUCT": 125},
    )

    artifact_writer = GenerationArtifactWriter(
        checkpoint_store=checkpoint_store,
    )
    artifact_writer._data_directory = tmp_path

    artifact_reader = GenerationArtifactReader(
        checkpoint_store=checkpoint_store,
    )
    artifact_reader._data_directory = tmp_path

    semantic_store = GenerationSemanticStore()
    semantic_store._root = tmp_path / "generation"

    artifact_writer.initialize_job(data_model_id, job_id)

    # Simulate two durably committed chunks before interruption.
    artifact_writer.write_chunk(
        data_model_id,
        job_id,
        "PRODUCT",
        1,
        [
            {
                "PRODUCT_ID": str(index),
                "PRODUCT_NAME": semantic_values[index - 1],
            }
            for index in range(1, 51)
        ],
        attempt_id=attempt_id,
        row_start=0,
    )

    artifact_writer.write_chunk(
        data_model_id,
        job_id,
        "PRODUCT",
        2,
        [
            {
                "PRODUCT_ID": str(index),
                "PRODUCT_NAME": semantic_values[index - 1],
            }
            for index in range(51, 101)
        ],
        attempt_id=attempt_id,
        row_start=50,
    )

    semantic_store.commit_unique_values(
        data_model_id=data_model_id,
        job_id=job_id,
        entity_name="PRODUCT",
        field_name="PRODUCT_NAME",
        values_by_row={
            index: value
            for index, value in enumerate(semantic_values)
        },
    )

    executor = GenerationExecutor(
        seed=42,
        ai_service=None,
        semantic_store=semantic_store,
        checkpoint_store=checkpoint_store,
        artifact_reader=artifact_reader,
        artifact_writer=artifact_writer,
    )

    plan = GenerationPlan(
        entities=(
            GenerationEntityPlan(
                entity_name="PRODUCT",
                target_rows=125,
            ),
        ),
    )

    result = executor.execute(
        data_model_id=data_model_id,
        specification=specification,
        plan=plan,
        job_id=job_id,
    )

    assert result.entities[0].generated_rows == 125

    recovered_manifest = checkpoint_store.get(data_model_id, job_id)
    assert recovered_manifest is not None

    entity_state = recovered_manifest.entities["PRODUCT"]
    assert entity_state.committed_rows == 125
    assert sorted(chunk.chunk_number for chunk in entity_state.chunks) == [1, 2, 3]



@pytest.mark.parametrize(
    "failure_case",
    [
        None,
        "duplicate",
        "blank",
        "missing_field",
        "missing_chunk",
        "corrupt_store",
    ],
)
def test_resume_with_missing_semantic_store_reconstructs_values_from_artifacts(
    tmp_path,
    failure_case,
):
    from copy import deepcopy

    from app.constants.generation import GENERATION_ALGORITHM_VERSION
    from app.services.generation.artifact_reader import GenerationArtifactReader
    from app.services.generation.artifact_writer import GenerationArtifactWriter
    from app.services.generation.executor import GenerationExecutor
    from app.services.generation_checkpoint_store import GenerationCheckpointStore
    from app.services.generation_persistence_errors import ArtifactIntegrityError
    from app.services.generation_semantic_store import (
        GenerationSemanticStore,
        SemanticStoreIntegrityError,
    )

    data_model_id = "FORGE-REAL-RESUME-MODEL"
    job_id = "FORGE-REAL-RESUME-TEST"
    attempt_id = "semantic-recovery-attempt-001"
    chunk_size = 50

    semantic_values = [
        f"Product {index:03d}"
        for index in range(1, 126)
    ]

    specification = {
        "entities": [
            {
                "name": "PRODUCT",
                "population": {"count": 125},
                "identity": {"fields": ["PRODUCT_ID"]},
                "fields": [
                    {
                        "name": "PRODUCT_ID",
                        "type": "IDENTIFIER",
                        "identity": {"strategy": "SEQUENTIAL_ID"},
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

    checkpoint_store = GenerationCheckpointStore()
    checkpoint_store._root = tmp_path / "data_model"

    checkpoint_store.initialize(
        data_model_id=data_model_id,
        job_id=job_id,
        specification=specification,
        seed=42,
        chunk_size=chunk_size,
        algorithm_version=GENERATION_ALGORITHM_VERSION,
        attempt_id=attempt_id,
        entity_targets={"PRODUCT": 125},
    )

    artifact_writer = GenerationArtifactWriter(
        checkpoint_store=checkpoint_store,
    )
    artifact_writer._data_directory = tmp_path

    artifact_reader = GenerationArtifactReader(
        checkpoint_store=checkpoint_store,
    )
    artifact_reader._data_directory = tmp_path

    semantic_store = GenerationSemanticStore()
    semantic_store._root = tmp_path / "generation"

    artifact_writer.initialize_job(data_model_id, job_id)

    # Publish and commit two chunks before simulating interruption.
    artifact_writer.write_chunk(
        data_model_id,
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
        attempt_id=attempt_id,
        row_start=0,
    )

    artifact_writer.write_chunk(
        data_model_id,
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
        attempt_id=attempt_id,
        row_start=50,
    )

    # No semantic-store file exists. Recovery must reconstruct the first
    # 100 UNIQUE assignments from the committed artifact chunks.
    semantic_path = semantic_store._semantic_path(
        data_model_id,
        job_id,
    )
    assert not semantic_path.exists()

    checkpoint_before_recovery = deepcopy(
        checkpoint_store.get(data_model_id, job_id)
    )
    assert checkpoint_before_recovery is not None

    chunks_directory = (
        tmp_path
        / "data_model"
        / data_model_id
        / "generation"
        / job_id
        / "generated"
        / "PRODUCT"
        / "chunks"
    )

    chunk_one = chunks_directory / "chunk_000001.csv"
    chunk_two = chunks_directory / "chunk_000002.csv"

    if failure_case == "duplicate":
        content = chunk_one.read_text(encoding="utf-8")
        assert "Product 002" in content
        chunk_one.write_text(
            content.replace("Product 002", "Product 001", 1),
            encoding="utf-8",
        )

    elif failure_case == "blank":
        content = chunk_one.read_text(encoding="utf-8")
        assert "Product 002" in content
        chunk_one.write_text(
            content.replace("Product 002", "", 1),
            encoding="utf-8",
        )

    elif failure_case == "missing_field":
        content = chunk_one.read_text(encoding="utf-8")
        assert "PRODUCT_ID,PRODUCT_NAME" in content
        chunk_one.write_text(
            content.replace(
                "PRODUCT_ID,PRODUCT_NAME",
                "PRODUCT_ID",
                1,
            ),
            encoding="utf-8",
        )

    elif failure_case == "missing_chunk":
        chunk_two.unlink()

    elif failure_case == "corrupt_store":
        semantic_path.parent.mkdir(parents=True, exist_ok=True)
        semantic_path.write_text(
            "{ invalid json",
            encoding="utf-8",
        )

    class RecordingAIService:
        def __init__(self) -> None:
            self.calls = []

        def generate_semantic_values(
            self,
            *,
            description,
            mode,
            count,
            exclude_values=None,
            on_call_completed=None,
            on_progress=None,
        ):
            self.calls.append(
                {
                    "description": description,
                    "mode": mode,
                    "count": count,
                    "exclude_values": list(exclude_values or []),
                }
            )
            return semantic_values[100:125]

    ai_service = RecordingAIService()

    executor = GenerationExecutor(
        seed=42,
        ai_service=ai_service,
        semantic_store=semantic_store,
        checkpoint_store=checkpoint_store,
        artifact_reader=artifact_reader,
        artifact_writer=artifact_writer,
    )

    plan = GenerationPlan(
        entities=(
            GenerationEntityPlan(
                entity_name="PRODUCT",
                target_rows=125,
            ),
        ),
    )

    if failure_case is not None:
        expected_error = (
            SemanticStoreIntegrityError
            if failure_case == "corrupt_store"
            else ArtifactIntegrityError
        )

        original_semantic_content = (
            semantic_path.read_text(encoding="utf-8")
            if failure_case == "corrupt_store"
            else None
        )

        with pytest.raises(expected_error):
            executor.execute(
                data_model_id=data_model_id,
                specification=specification,
                plan=plan,
                job_id=job_id,
            )

        # Integrity failures must not trigger AI generation or checkpoint
        # mutation.
        assert ai_service.calls == []

        assert checkpoint_store.get(
            data_model_id,
            job_id,
        ) == checkpoint_before_recovery

        if failure_case == "corrupt_store":
            assert semantic_path.read_text(
                encoding="utf-8"
            ) == original_semantic_content

        return

    result = executor.execute(
        data_model_id=data_model_id,
        specification=specification,
        plan=plan,
        job_id=job_id,
    )

    # Only the missing 25 semantic values should require AI generation.
    assert len(ai_service.calls) == 1
    assert ai_service.calls[0]["mode"] == "UNIQUE"
    assert ai_service.calls[0]["count"] == 25
    assert ai_service.calls[0]["exclude_values"] == semantic_values[:100]

    recovered_values = semantic_store.get_unique_values(
        data_model_id=data_model_id,
        job_id=job_id,
        entity_name="PRODUCT",
        field_name="PRODUCT_NAME",
    )

    assert recovered_values == {
        index: value
        for index, value in enumerate(semantic_values)
    }

    saved_manifest = checkpoint_store.get(data_model_id, job_id)
    assert saved_manifest is not None

    entity_state = saved_manifest.entities["PRODUCT"]

    assert entity_state.committed_rows == 125
    assert sorted(
        chunk.chunk_number for chunk in entity_state.chunks
    ) == [1, 2, 3]

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
            data_model_id=data_model_id,
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


@pytest.mark.parametrize("relationship_type", ["ONE_TO_MANY", "ONE_TO_ONE"])
def test_executor_enforces_mandatory_parent_participation(
    tmp_path,
    monkeypatch,
    relationship_type: str,
) -> None:
    from app.constants.generation import GENERATION_ALGORITHM_VERSION
    from app.services.generation.artifact_reader import GenerationArtifactReader
    from app.services.generation.artifact_writer import GenerationArtifactWriter
    from app.services.generation.executor import GenerationExecutor
    from app.services.generation_checkpoint_store import GenerationCheckpointStore
    from app.services.generation_planner import GenerationPlanner

    specification = {
        "entities": [
            {
                "name": "PARENT",
                "population": {"count": 3},
                "identity": {"fields": ["PARENT_ID"]},
                "fields": [
                    {
                        "name": "PARENT_ID",
                        "type": "IDENTIFIER",
                        "identity": {"strategy": "SEQUENTIAL_ID"},
                    },
                ],
            },
            {
                "name": "CHILD",
                "population": {"count": 3},
                "fields": [
                    {"name": "PARENT_ID", "type": "STRING"},
                ],
            },
        ],
        "foreign_keys": [
            {
                "name": "FK_CHILD_PARENT",
                "source": {"entity": "CHILD", "fields": ["PARENT_ID"]},
                "target": {"entity": "PARENT", "fields": ["PARENT_ID"]},
            },
        ],
        "relationships": [
            {
                "source": {"entity": "PARENT", "fields": ["PARENT_ID"]},
                "target": {"entity": "CHILD", "fields": ["PARENT_ID"]},
                "type": relationship_type,
                "source_participation": "MANDATORY",
                "target_participation": "OPTIONAL",
            },
        ],
    }

    plan = GenerationPlanner().build(specification)

    mandatory_groups = [
        group
        for group in plan.relationship_groups
        if (
            group.resolution_status == "MAPPED"
            and group.relationship_type.upper() == relationship_type
            and group.parent_participation.upper() == "MANDATORY"
        )
    ]

    assert len(mandatory_groups) == 1
    assert mandatory_groups[0].parent_entity == "PARENT"
    assert mandatory_groups[0].child_entity == "CHILD"

    data_model_id = "MANDATORY-PARTICIPATION-TEST"
    job_id = "MANDATORY-PARTICIPATION-TEST-JOB"
    attempt_id = "mandatory-participation-attempt"
    chunk_size = 50
    artifact_directory = tmp_path / "artifacts"

    checkpoint_store = GenerationCheckpointStore()
    checkpoint_store._root = artifact_directory / "data_model"
    checkpoint_store.initialize(
        data_model_id=data_model_id,
        job_id=job_id,
        specification=specification,
        seed=42,
        chunk_size=chunk_size,
        algorithm_version=GENERATION_ALGORITHM_VERSION,
        attempt_id=attempt_id,
        entity_targets={"PARENT": 3, "CHILD": 3},
    )

    artifact_writer = GenerationArtifactWriter(
        checkpoint_store=checkpoint_store,
    )
    artifact_writer._data_directory = artifact_directory

    artifact_reader = GenerationArtifactReader(
        checkpoint_store=checkpoint_store,
    )
    artifact_reader._data_directory = artifact_directory

    completed_chunks: list[tuple[str, list[dict]]] = []

    def capture_chunk(*args) -> None:
        completed_chunks.append((args[0], args[4]))

    executor = GenerationExecutor(
        seed=42,
        checkpoint_store=checkpoint_store,
        artifact_writer=artifact_writer,
        artifact_reader=artifact_reader,
    )

    result = executor.execute(
        specification=specification,
        plan=plan,
        data_model_id=data_model_id,
        job_id=job_id,
        on_chunk_completed=capture_chunk,
    )

    parent_rows = [
        row
        for entity_name, rows in completed_chunks
        if entity_name == "PARENT"
        for row in rows
    ]

    child_rows = [
        row
        for entity_name, rows in completed_chunks
        if entity_name == "CHILD"
        for row in rows
    ]

    parent_ids = {str(row["PARENT_ID"]) for row in parent_rows}
    child_parent_ids = {str(row["PARENT_ID"]) for row in child_rows}

    assert len(parent_rows) == 3
    assert len(child_rows) == 3
    assert child_parent_ids == parent_ids
    assert len(child_parent_ids) == 3
    assert result.generated_rows == 6

    manifest = checkpoint_store.get(data_model_id, job_id)
    assert manifest is not None
    assert manifest.attempt_id == attempt_id
    assert manifest.entities["PARENT"].committed_rows == 3
    assert manifest.entities["CHILD"].committed_rows == 3



def test_executor_excludes_previous_chunk_values_for_unique_semantics(
    tmp_path,
    monkeypatch,
) -> None:
    from app.constants.generation import GENERATION_ALGORITHM_VERSION
    from app.services.generation.artifact_reader import GenerationArtifactReader
    from app.services.generation.artifact_writer import GenerationArtifactWriter
    from app.services.generation.executor import GenerationExecutor
    from app.services.generation_semantic_store import GenerationSemanticStore
    from app.services.generation_checkpoint_store import GenerationCheckpointStore

    data_model_id = "FORGE-UNIQUE-REGRESSION"
    job_id = "FORGE-UNIQUE-CHUNK-TEST"
    attempt_id = "unique-semantic-attempt"
    event_broker = Mock()
    chunk_size = 50
    artifact_directory = tmp_path / "artifacts"

    first_batch = [
        f"Aerospace Product {index:03d}"
        for index in range(1, 51)
    ]
    second_batch = ["Aerospace Product 051"]

    class RecordingAIService:
        def __init__(self) -> None:
            self.calls: list[dict[str, Any]] = []

        def generate_semantic_values(
            self,
            *,
            description: str,
            mode: str,
            count: int,
            exclude_values: list[str] | None = None,
            on_call_completed=None,
            on_progress=None,
        ) -> list[str]:
            call_number = len(self.calls)

            self.calls.append(
                {
                    "description": description,
                    "mode": mode,
                    "count": count,
                    "exclude_values": list(exclude_values or []),
                }
            )

            # Simulate the provider's attempt-level progress callbacks.
            # The first chunk needs 30 + 20 values; the second needs 1.
            if on_progress is not None:
                attempts = (
                    [
                        (1, 30, 0, 30, 30),
                        (2, 20, 30, 20, 50),
                    ]
                    if call_number == 0
                    else [(1, 1, 0, 1, 1)]
                )
                max_attempts = 7 if call_number == 0 else 6

                for attempt, requested, before, returned, total in attempts:
                    refill = attempt > 1

                    on_progress({
                        "status": "STARTED",
                        "attempt_number": attempt,
                        "max_attempts": max_attempts,
                        "requested_count": requested,
                        "total_count": count,
                        "total_unique_count": before,
                        "refill": refill,
                    })

                    if on_call_completed is not None:
                        on_call_completed(
                            requested,
                            returned,
                            0.25,
                            refill,
                        )

                    on_progress({
                        "status": "COMPLETED",
                        "attempt_number": attempt,
                        "max_attempts": max_attempts,
                        "requested_count": requested,
                        "returned_count": returned,
                        "new_unique_count": returned,
                        "duplicate_count": 0,
                        "total_count": count,
                        "total_unique_count": total,
                        "elapsed_seconds": 0.25,
                        "refill": refill,
                    })

            if call_number == 0:
                assert count == 50
                return first_batch

            if call_number == 1:
                assert count == 1
                return second_batch

            raise AssertionError(
                f"Unexpected semantic generation call: {call_number + 1}"
            )

    ai_service = RecordingAIService()

    semantic_store = GenerationSemanticStore()
    semantic_store._root = tmp_path / "semantic"

    checkpoint_store = GenerationCheckpointStore()
    checkpoint_store._root = artifact_directory / "data_model"

    checkpoint_store.initialize(
        data_model_id=data_model_id,
        job_id=job_id,
        specification={
            "entities": [
                {
                    "name": "PRODUCT",
                    "population": {"count": 51},
                    "fields": [
                        {
                            "name": "PRODUCT_NAME",
                            "type": "STRING",
                            "generation": {
                                "generator": "SEMANTIC",
                                "parameters": {
                                    "description": "Realistic aerospace product name.",
                                    "mode": "UNIQUE",
                                },
                            },
                        },
                    ],
                },
            ],
            "foreign_keys": [],
        },
        seed=42,
        chunk_size=chunk_size,
        algorithm_version=GENERATION_ALGORITHM_VERSION,
        attempt_id=attempt_id,
        entity_targets={"PRODUCT": 51},
    )

    artifact_writer = GenerationArtifactWriter(
        checkpoint_store=checkpoint_store,
    )
    artifact_writer._data_directory = artifact_directory

    artifact_reader = GenerationArtifactReader(
        checkpoint_store=checkpoint_store,
    )
    artifact_reader._data_directory = artifact_directory

    executor = GenerationExecutor(
        seed=42,
        ai_service=ai_service,
        semantic_store=semantic_store,
        checkpoint_store=checkpoint_store,
        artifact_writer=artifact_writer,
        artifact_reader=artifact_reader,
        event_broker=event_broker,
    )

    specification = {
        "entities": [
            {
                "name": "PRODUCT",
                "population": {"count": 51},
                "fields": [
                    {
                        "name": "PRODUCT_NAME",
                        "type": "STRING",
                        "generation": {
                            "generator": "SEMANTIC",
                            "parameters": {
                                "description": "Realistic aerospace product name.",
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
                target_rows=51,
            ),
        ),
    )

    executor.execute(
        specification=specification,
        plan=plan,
        data_model_id=data_model_id,
        job_id=job_id,
    )

    assert len(ai_service.calls) == 2

    progress_events = [
        call.kwargs["data"]
        for call in event_broker.publish.call_args_list
        if call.kwargs.get("event_type") == "SEMANTIC_CALL_PROGRESS"
    ]

    assert [
        (
            event["status"],
            event["attempt_number"],
            event["chunk_number"],
        )
        for event in progress_events
    ] == [
        ("STARTED", 1, 1),
        ("COMPLETED", 1, 1),
        ("STARTED", 2, 1),
        ("COMPLETED", 2, 1),
        ("STARTED", 1, 2),
        ("COMPLETED", 1, 2),
    ]

    first_chunk_completions = [
        event
        for event in progress_events
        if event["status"] == "COMPLETED"
        and event["chunk_number"] == 1
    ]

    assert [
        event["total_unique_count"]
        for event in first_chunk_completions
    ] == [30, 50]

    assert [
        event["new_unique_count"]
        for event in first_chunk_completions
    ] == [30, 20]

    assert all(
        event["entity_name"] == "PRODUCT"
        and event["field_name"] == "PRODUCT_NAME"
        and event["duplicate_count"] == 0
        for event in progress_events
        if event["status"] == "COMPLETED"
    )

    assert ai_service.calls[0]["exclude_values"] == []
    assert len(ai_service.calls[1]["exclude_values"]) == 50
    assert set(ai_service.calls[1]["exclude_values"]) == set(first_batch)

    persisted = semantic_store.get(
        data_model_id=data_model_id,
        job_id=job_id,
        entity_name="PRODUCT",
        field_name="PRODUCT_NAME",
    )

    assert persisted is not None
    assert persisted["mode"] == "UNIQUE"

    expected_by_row = {
        index: value
        for index, value in enumerate(first_batch + second_batch)
    }

    assert semantic_store.get_unique_values(
        data_model_id=data_model_id,
        job_id=job_id,
        entity_name="PRODUCT",
        field_name="PRODUCT_NAME",
    ) == expected_by_row

    assert persisted["values_by_row"] == {
        str(row_index): value
        for row_index, value in expected_by_row.items()
    }

    normalized = [
        value.strip().casefold()
        for value in expected_by_row.values()
    ]

    assert len(normalized) == 51
    assert len(set(normalized)) == 51

    manifest = checkpoint_store.get(data_model_id, job_id)
    assert manifest is not None
    assert manifest.attempt_id == attempt_id
    entity_state = manifest.entities["PRODUCT"]
    assert entity_state.committed_rows == 51
    assert sorted(chunk.chunk_number for chunk in entity_state.chunks) == [1, 2]


def test_executor_enforces_one_to_one_with_optional_parent_participation(
    tmp_path,
    monkeypatch,
) -> None:
    from app.constants.generation import GENERATION_ALGORITHM_VERSION
    from app.services.generation.artifact_reader import GenerationArtifactReader
    from app.services.generation.artifact_writer import GenerationArtifactWriter
    from app.services.generation.executor import GenerationExecutor
    from app.services.generation_checkpoint_store import GenerationCheckpointStore
    from app.services.generation_planner import GenerationPlanner

    specification = {
        "entities": [
            {
                "name": "PARENT",
                "population": {"count": 5},
                "identity": {"fields": ["PARENT_ID"]},
                "fields": [
                    {
                        "name": "PARENT_ID",
                        "type": "IDENTIFIER",
                        "identity": {"strategy": "SEQUENTIAL_ID"},
                    },
                ],
            },
            {
                "name": "CHILD",
                "population": {"count": 3},
                "fields": [
                    {"name": "PARENT_ID", "type": "STRING"},
                ],
            },
        ],
        "foreign_keys": [
            {
                "name": "FK_CHILD_PARENT",
                "source": {"entity": "CHILD", "fields": ["PARENT_ID"]},
                "target": {"entity": "PARENT", "fields": ["PARENT_ID"]},
            },
        ],
        "relationships": [
            {
                "source": {"entity": "CHILD", "fields": ["PARENT_ID"]},
                "target": {"entity": "PARENT", "fields": ["PARENT_ID"]},
                "type": "ONE_TO_ONE",
                "source_participation": "MANDATORY",
                "target_participation": "OPTIONAL",
            },
        ],
    }

    plan = GenerationPlanner().build(specification)

    mapped_groups = [
        group
        for group in plan.relationship_groups
        if (
            group.resolution_status == "MAPPED"
            and group.relationship_type.upper() == "ONE_TO_ONE"
        )
    ]

    assert len(mapped_groups) == 1
    assert mapped_groups[0].child_entity == "CHILD"
    assert mapped_groups[0].parent_entity == "PARENT"
    assert mapped_groups[0].child_participation.upper() == "MANDATORY"
    assert mapped_groups[0].parent_participation.upper() == "OPTIONAL"

    data_model_id = "ONE-TO-ONE-OPTIONAL-PARENT-TEST"
    job_id = "ONE-TO-ONE-OPTIONAL-PARENT-TEST-JOB"
    attempt_id = "one-to-one-optional-parent-attempt"
    chunk_size = 50
    artifact_directory = tmp_path / "artifacts"

    checkpoint_store = GenerationCheckpointStore()
    checkpoint_store._root = artifact_directory / "data_model"
    checkpoint_store.initialize(
        data_model_id=data_model_id,
        job_id=job_id,
        specification=specification,
        seed=42,
        chunk_size=chunk_size,
        algorithm_version=GENERATION_ALGORITHM_VERSION,
        attempt_id=attempt_id,
        entity_targets={"PARENT": 5, "CHILD": 3},
    )

    artifact_writer = GenerationArtifactWriter(
        checkpoint_store=checkpoint_store,
    )
    artifact_writer._data_directory = artifact_directory

    artifact_reader = GenerationArtifactReader(
        checkpoint_store=checkpoint_store,
    )
    artifact_reader._data_directory = artifact_directory

    completed_chunks: list[tuple[str, list[dict]]] = []

    def capture_chunk(*args) -> None:
        completed_chunks.append((args[0], args[4]))

    executor = GenerationExecutor(
        seed=42,
        checkpoint_store=checkpoint_store,
        artifact_writer=artifact_writer,
        artifact_reader=artifact_reader,
    )

    result = executor.execute(
        specification=specification,
        plan=plan,
        data_model_id=data_model_id,
        job_id=job_id,
        on_chunk_completed=capture_chunk,
    )

    parent_rows = [
        row
        for entity_name, rows in completed_chunks
        if entity_name == "PARENT"
        for row in rows
    ]

    child_rows = [
        row
        for entity_name, rows in completed_chunks
        if entity_name == "CHILD"
        for row in rows
    ]

    parent_ids = {str(row["PARENT_ID"]) for row in parent_rows}
    child_parent_ids = [str(row["PARENT_ID"]) for row in child_rows]

    assert len(parent_rows) == 5
    assert len(child_rows) == 3
    assert len(set(child_parent_ids)) == 3
    assert set(child_parent_ids).issubset(parent_ids)
    assert result.generated_rows == 8

    manifest = checkpoint_store.get(data_model_id, job_id)
    assert manifest is not None
    assert manifest.attempt_id == attempt_id
    assert manifest.entities["PARENT"].committed_rows == 5
    assert manifest.entities["CHILD"].committed_rows == 3

def _build_vocabulary_activity_executor(
    *,
    tmp_path,
    ai_service,
    event_broker,
    target_rows: int = 10,
):
    from app.constants.generation import GENERATION_ALGORITHM_VERSION
    from app.services.generation.artifact_reader import GenerationArtifactReader
    from app.services.generation.artifact_writer import GenerationArtifactWriter
    from app.services.generation.executor import GenerationExecutor
    from app.services.generation_checkpoint_store import GenerationCheckpointStore
    from app.services.generation_log_store import GenerationLogStore
    from app.services.generation_semantic_store import GenerationSemanticStore

    data_model_id = "FORGE-VOCABULARY-ACTIVITY-MODEL"
    job_id = "FORGE-VOCABULARY-ACTIVITY-TEST"
    artifact_directory = tmp_path / "artifacts"

    specification = {
        "entities": [
            {
                "name": "PRODUCT",
                "population": {"count": target_rows},
                "fields": [
                    {
                        "name": "PRODUCT_NAME",
                        "type": "STRING",
                        "generation": {
                            "generator": "SEMANTIC",
                            "parameters": {
                                "description": "Realistic aerospace product name.",
                                "mode": "VOCABULARY",
                            },
                        },
                    },
                ],
            },
        ],
        "foreign_keys": [],
    }

    checkpoint_store = GenerationCheckpointStore()
    checkpoint_store._root = artifact_directory / "data_model"
    checkpoint_store.initialize(
        data_model_id=data_model_id,
        job_id=job_id,
        specification=specification,
        seed=42,
        chunk_size=50,
        algorithm_version=GENERATION_ALGORITHM_VERSION,
        attempt_id="vocabulary-activity-attempt",
        entity_targets={"PRODUCT": target_rows},
    )

    artifact_writer = GenerationArtifactWriter(
        checkpoint_store=checkpoint_store
    )
    artifact_writer._data_directory = artifact_directory

    artifact_reader = GenerationArtifactReader(
        checkpoint_store=checkpoint_store
    )
    artifact_reader._data_directory = artifact_directory

    semantic_store = GenerationSemanticStore()
    semantic_store._root = tmp_path / "semantic"

    generation_log_store = GenerationLogStore(
        root=tmp_path / "generation-logs"
    )

    executor = GenerationExecutor(
        seed=42,
        ai_service=ai_service,
        semantic_store=semantic_store,
        checkpoint_store=checkpoint_store,
        event_broker=event_broker,
        generation_log_store=generation_log_store,
        artifact_writer=artifact_writer,
        artifact_reader=artifact_reader,
    )

    plan = GenerationPlan(
        entities=(
            GenerationEntityPlan(
                entity_name="PRODUCT",
                target_rows=target_rows,
            ),
        ),
    )

    return (
        executor,
        specification,
        plan,
        data_model_id,
        job_id,
        generation_log_store,
        semantic_store,
    )


def test_executor_publishes_vocabulary_activity_lifecycle(
    tmp_path,
) -> None:
    from unittest.mock import Mock

    event_broker = Mock()
    semantic_values = [
        f"Aerospace Product {index:02d}"
        for index in range(1, 11)
    ]

    class VocabularyAIService:
        def generate_semantic_values(
            self,
            *,
            description,
            mode,
            count,
            exclude_values=None,
            on_call_completed=None,
            on_progress=None,
        ):
            assert description == "Realistic aerospace product name."
            assert mode == "VOCABULARY"
            assert count == 10

            # The STARTED activity must already have been published
            # before control reaches the AI provider.
            assert any(
                call.kwargs.get("event_type") == "GENERATION_ACTIVITY"
                and call.kwargs.get("data", {}).get("stage")
                == "SEMANTIC_GENERATION"
                and call.kwargs.get("data", {}).get("status") == "STARTED"
                for call in event_broker.publish.call_args_list
            )

            if on_progress is not None:
                on_progress({
                    "status": "STARTED",
                    "attempt_number": 1,
                    "max_attempts": 6,
                    "requested_count": 10,
                    "total_count": 10,
                    "total_unique_count": 0,
                    "refill": False,
                })

            if on_call_completed is not None:
                on_call_completed(10, 10, 0.4, False)

            if on_progress is not None:
                on_progress({
                    "status": "COMPLETED",
                    "attempt_number": 1,
                    "max_attempts": 6,
                    "requested_count": 10,
                    "returned_count": 10,
                    "new_unique_count": 10,
                    "duplicate_count": 0,
                    "total_count": 10,
                    "total_unique_count": 10,
                    "elapsed_seconds": 0.4,
                    "refill": False,
                })

            return semantic_values

    (
        executor,
        specification,
        plan,
        data_model_id,
        job_id,
        generation_log_store,
        semantic_store,
    ) = _build_vocabulary_activity_executor(
        tmp_path=tmp_path,
        ai_service=VocabularyAIService(),
        event_broker=event_broker,
    )

    executor.execute(
        data_model_id=data_model_id,
        specification=specification,
        plan=plan,
        job_id=job_id,
    )

    journal = generation_log_store.get(
        data_model_id=data_model_id,
        job_id=job_id,
    )
    assert journal is not None

    semantic_entries = [
        entry
        for entry in journal.entries
        if entry.stage == "SEMANTIC_GENERATION"
    ]

    assert [entry.status for entry in semantic_entries] == [
        "STARTED",
        "COMPLETED",
    ]
    assert all(
        entry.entity_name == "PRODUCT"
        and entry.field_name == "PRODUCT_NAME"
        and entry.requested_count == 10
        for entry in semantic_entries
    )
    assert semantic_entries[1].elapsed_seconds is not None

    semantic_events = [
        call.kwargs["data"]
        for call in event_broker.publish.call_args_list
        if call.kwargs.get("event_type") == "GENERATION_ACTIVITY"
        and call.kwargs.get("data", {}).get("stage")
        == "SEMANTIC_GENERATION"
    ]

    assert [event["status"] for event in semantic_events] == [
        "STARTED",
        "COMPLETED",
    ]
    assert all(event["requested_count"] == 10 for event in semantic_events)

    progress_events = [
        call.kwargs["data"]
        for call in event_broker.publish.call_args_list
        if call.kwargs.get("event_type") == "SEMANTIC_CALL_PROGRESS"
    ]

    assert [event["status"] for event in progress_events] == [
        "STARTED",
        "COMPLETED",
    ]

    started, completed = progress_events

    assert started["entity_name"] == "PRODUCT"
    assert started["field_name"] == "PRODUCT_NAME"
    assert started["attempt_number"] == 1
    assert started["total_count"] == 10
    assert started["total_unique_count"] == 0
    assert "chunk_number" not in started

    assert completed["attempt_number"] == 1
    assert completed["requested_count"] == 10
    assert completed["returned_count"] == 10
    assert completed["new_unique_count"] == 10
    assert completed["duplicate_count"] == 0
    assert completed["total_unique_count"] == 10
    assert completed["elapsed_seconds"] == 0.4
    assert "chunk_number" not in completed

    persisted = semantic_store.get(
        data_model_id=data_model_id,
        job_id=job_id,
        entity_name="PRODUCT",
        field_name="PRODUCT_NAME",
    )

    assert persisted is not None
    assert persisted["mode"] == "VOCABULARY"
    assert persisted["values"] == semantic_values


def test_executor_publishes_failed_vocabulary_activity(
    tmp_path,
) -> None:
    from unittest.mock import Mock

    event_broker = Mock()

    class FailingVocabularyAIService:
        def generate_semantic_values(
            self,
            *,
            description,
            mode,
            count,
            exclude_values=None,
            on_call_completed=None,
            on_progress=None,
        ):
            assert mode == "VOCABULARY"
            assert count == 10
            raise RuntimeError("Vocabulary provider unavailable")

    (
        executor,
        specification,
        plan,
        data_model_id,
        job_id,
        generation_log_store,
        _semantic_store,
    ) = _build_vocabulary_activity_executor(
        tmp_path=tmp_path,
        ai_service=FailingVocabularyAIService(),
        event_broker=event_broker,
    )

    with pytest.raises(
        RuntimeError,
        match="Vocabulary provider unavailable",
    ):
        executor.execute(
            data_model_id=data_model_id,
            specification=specification,
            plan=plan,
            job_id=job_id,
        )

    journal = generation_log_store.get(
        data_model_id=data_model_id,
        job_id=job_id,
    )
    assert journal is not None

    semantic_entries = [
        entry
        for entry in journal.entries
        if entry.stage == "SEMANTIC_GENERATION"
    ]

    assert [entry.status for entry in semantic_entries] == [
        "STARTED",
        "FAILED",
    ]

    failed_entry = semantic_entries[-1]
    assert failed_entry.requested_count == 10
    assert failed_entry.error_type == "RuntimeError"
    assert failed_entry.error_message == "Vocabulary provider unavailable"
    assert failed_entry.elapsed_seconds is not None

    semantic_events = [
        call.kwargs["data"]
        for call in event_broker.publish.call_args_list
        if call.kwargs.get("event_type") == "GENERATION_ACTIVITY"
        and call.kwargs.get("data", {}).get("stage")
        == "SEMANTIC_GENERATION"
    ]

    assert [event["status"] for event in semantic_events] == [
        "STARTED",
        "FAILED",
    ]
    assert semantic_events[-1]["error_type"] == "RuntimeError"


def test_executor_accepts_larger_persisted_vocabulary_for_smaller_target(
    tmp_path,
) -> None:
    from unittest.mock import Mock

    event_broker = Mock()
    (
        executor,
        specification,
        plan,
        data_model_id,
        job_id,
        generation_log_store,
        semantic_store,
    ) = _build_vocabulary_activity_executor(
        tmp_path=tmp_path,
        ai_service=None,
        event_broker=event_broker,
        target_rows=10,
    )

    legacy_values = [
        f"Legacy aerospace product {index:02d}"
        for index in range(1, 51)
    ]
    semantic_store.save_vocabulary(
        data_model_id=data_model_id,
        job_id=job_id,
        entity_name="PRODUCT",
        field_name="PRODUCT_NAME",
        values=legacy_values,
    )

    executor.execute(
        data_model_id=data_model_id,
        specification=specification,
        plan=plan,
        job_id=job_id,
    )

    journal = generation_log_store.get(
        data_model_id=data_model_id,
        job_id=job_id,
    )
    assert journal is not None
    assert not any(
        entry.stage == "SEMANTIC_GENERATION"
        for entry in journal.entries
    )

    persisted = semantic_store.get(
        data_model_id=data_model_id,
        job_id=job_id,
        entity_name="PRODUCT",
        field_name="PRODUCT_NAME",
    )
    assert persisted is not None
    assert persisted["values"] == legacy_values

    semantic_events = [
        call.kwargs["data"]
        for call in event_broker.publish.call_args_list
        if call.kwargs.get("event_type") == "GENERATION_ACTIVITY"
        and call.kwargs.get("data", {}).get("stage")
        == "SEMANTIC_GENERATION"
    ]
    assert semantic_events == []
