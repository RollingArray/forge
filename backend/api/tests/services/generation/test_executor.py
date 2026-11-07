from dataclasses import dataclass
from typing import Any

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

    checkpoint_store = FakeCheckpointStore(
        checkpoint={
            "entities": {
                "PRODUCT": {
                    "target_rows": 3,
                    "chunk_size": 50,
                    "completed_chunks": [],
                    "committed_rows": 0,
                },
            },
        },
    )

    executor = GenerationExecutor(
        seed=42,
        ai_service=ai_service,
        semantic_store=semantic_store,
        checkpoint_store=checkpoint_store,
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

    def commit_semantic_chunk(
        entity_name,
        chunk_number,
        total_chunks,
        generated_rows,
        chunk_rows,
        *_,
    ) -> None:
        entity_state = checkpoint_store.checkpoint["entities"][entity_name]
        completed = entity_state.setdefault("completed_chunks", [])

        if chunk_number not in completed:
            completed.append(chunk_number)
            completed.sort()

        entity_state["committed_rows"] = min(
            len(completed) * entity_state["chunk_size"],
            entity_state["target_rows"],
        )

    executor.execute(
        data_model_id="FORGE-SEMANTIC-MODEL",
        specification=specification,
        plan=plan,
        job_id="FORGE-SEMANTIC-TEST",
        on_chunk_completed=commit_semantic_chunk,
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

    def get(self, *, data_model_id: str, job_id: str):
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


class _FakeCheckpointStore:
    def __init__(self, checkpoint=None):
        self._checkpoint = checkpoint

    def get(self, *, data_model_id: str, job_id: str):
        return self._checkpoint


def test_get_start_chunk_returns_one_without_checkpoint() -> None:
    from app.services.generation.executor import GenerationExecutor

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
    from app.services.generation.executor import GenerationExecutor

    checkpoint = {
        "entities": {
            "CUSTOMER": {
                "completed_chunks": [1, 2, 3, 4, 5, 6],
            },
        },
    }

    executor = GenerationExecutor(
        seed=42,
        checkpoint_store=_FakeCheckpointStore(checkpoint),
    )

    assert executor._get_start_chunk(
        data_model_id="FORGE-TEST-MODEL",
        job_id="FORGE-TEST",
        entity_name="CUSTOMER",
    ) == 7


def test_get_start_chunk_handles_non_contiguous_committed_chunks() -> None:
    from app.services.generation.executor import GenerationExecutor

    checkpoint = {
        "entities": {
            "CUSTOMER": {
                "completed_chunks": [1, 2, 4, 5],
            },
        },
    }

    executor = GenerationExecutor(
        seed=42,
        checkpoint_store=_FakeCheckpointStore(checkpoint),
    )

    assert executor._get_start_chunk(
        data_model_id="FORGE-TEST-MODEL",
        job_id="FORGE-TEST",
        entity_name="CUSTOMER",
    ) == 3


class FakeArtifactReader:
    def __init__(self, key_space):
        self.key_space = key_space
        self.calls = []

    def get_ordered_entity_key_space(
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
        return list(self.key_space)


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


def test_entity_is_fully_committed_when_all_chunks_are_present() -> None:
    executor = GenerationExecutor(
        seed=42,
        checkpoint_store=FakeCheckpointStore(
            checkpoint={
                "entities": {
                    "CUSTOMER": {
                        "total_chunks": 3,
                        "completed_chunks": [1, 2, 3],
                    },
                },
            },
        ),
    )

    assert executor._is_entity_fully_committed(
        data_model_id="FORGE-TEST-MODEL",
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
                        "completed_chunks": [1, 2],
                    },
                },
            },
        ),
    )

    assert not executor._is_entity_fully_committed(
        data_model_id="FORGE-TEST-MODEL",
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
                        "completed_chunks": [1, 3],
                    },
                },
            },
        ),
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

    checkpoint_store = FakeCheckpointStore(
        checkpoint={
            "entities": {
                "CUSTOMER": {
                    "target_rows": 3,
                    "chunk_size": 50,
                    "total_chunks": 1,
                    "completed_chunks": [1],
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
        checkpoint_store=FakeCheckpointStore(),
    )

    assert executor._get_committed_rows(
        data_model_id="FORGE-TEST-MODEL",
        job_id="FORGE-TEST",
        entity_name="CUSTOMER",
    ) == 0


def test_get_durable_generated_rows_returns_checkpoint_total() -> None:
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
        data_model_id="FORGE-TEST-MODEL",
        job_id="FORGE-TEST",
        entity_name="CUSTOMER",
    ) == 300


def test_executor_resumes_partial_entity_from_checkpoint() -> None:
    from app.services.generation.context import GenerationContext

    data_model_id = "FORGE-RESUME-MODEL"

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
                    "completed_chunks": [1, 2],
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
    artifact_writer.initialize_job(data_model_id, "FORGE-RESUME-TEST")

    artifact_writer.write_chunk(
        data_model_id,
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
        data_model_id,
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

    def commit_resumed_chunk(
        entity_name,
        chunk_number,
        total_chunks,
        generated_rows,
        chunk_rows,
        *_,
    ) -> None:
        entity_state = checkpoint_store.checkpoint["entities"][entity_name]
        completed = entity_state.setdefault("completed_chunks", [])

        if chunk_number not in completed:
            completed.append(chunk_number)
            completed.sort()

        entity_state["committed_rows"] = min(
            len(completed) * entity_state["chunk_size"],
            entity_state["target_rows"],
        )

    result = executor.execute(
        data_model_id=data_model_id,
        specification=specification,
        plan=plan,
        job_id="FORGE-RESUME-TEST",
        on_chunk_completed=commit_resumed_chunk,
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
            "data_model_id": data_model_id,
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

    data_model_id = "FORGE-REAL-RESUME-MODEL"
    job_id = "FORGE-REAL-RESUME-TEST"

    checkpoint_store = GenerationCheckpointStore()
    checkpoint_store._root = tmp_path / "generation"

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

    semantic_values = [
        f"Product {index:03d}"
        for index in range(1, 126)
    ]

    semantic_store.save(
        data_model_id=data_model_id,
        job_id=job_id,
        entity_name="PRODUCT",
        field_name="PRODUCT_NAME",
        mode="UNIQUE",
        values=semantic_values,
    )

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
    )

    checkpoint_store.save(
        data_model_id=data_model_id,
        job_id=job_id,
        seed=42,
        entities={
            "PRODUCT": {
                "target_rows": 125,
                "chunk_size": 50,
                "total_chunks": 3,
                "completed_chunks": [1, 2],
                "committed_rows": 100,
            }
        },
        chunk_size=50,
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

    def commit_resumed_chunk(
        entity_name,
        chunk_number,
        total_chunks,
        generated_rows,
        chunk_rows,
        *_,
    ) -> None:
        checkpoint = checkpoint_store.get(
            data_model_id=data_model_id,
            job_id=job_id,
        ) or {}
        entities = checkpoint.get("entities", {})
        entity_state = dict(entities.get(entity_name, {}))
        completed_chunks = list(
            entity_state.get("completed_chunks", [])
        )

        if chunk_number not in completed_chunks:
            completed_chunks.append(chunk_number)
            completed_chunks.sort()

        chunk_size = checkpoint.get(
            "chunk_size",
            entity_state.get("chunk_size", 50),
        )
        target_rows = entity_state["target_rows"]

        entity_state["completed_chunks"] = completed_chunks
        entity_state["committed_rows"] = min(
            len(completed_chunks) * chunk_size,
            target_rows,
        )
        entities[entity_name] = entity_state

        checkpoint_store.save(
            data_model_id=data_model_id,
            job_id=job_id,
            seed=checkpoint.get("seed", 42),
            entities=entities,
            specification_hash=checkpoint.get("specification_hash", ""),
            chunk_size=chunk_size,
        )

    result = executor.execute(
        data_model_id=data_model_id,
        specification=specification,
        plan=plan,
        job_id=job_id,
        on_chunk_completed=commit_resumed_chunk,
    )

    saved_checkpoint = checkpoint_store.get(
        data_model_id=data_model_id,
        job_id=job_id,
    )
    assert saved_checkpoint["entities"]["PRODUCT"]["completed_chunks"] == [1, 2, 3]
    assert saved_checkpoint["entities"]["PRODUCT"]["committed_rows"] == 125
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
    from app.services.generation.artifact_writer import GenerationArtifactWriter
    from app.services.generation_checkpoint_store import GenerationCheckpointStore

    monkeypatch.chdir(tmp_path)

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
                "source": {
                    "entity": "CHILD",
                    "fields": ["PARENT_ID"],
                },
                "target": {
                    "entity": "PARENT",
                    "fields": ["PARENT_ID"],
                },
            },
        ],
        "relationships": [
            {
                "source": {
                    "entity": "PARENT",
                    "fields": ["PARENT_ID"],
                },
                "target": {
                    "entity": "CHILD",
                    "fields": ["PARENT_ID"],
                },
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

    checkpoint_store = GenerationCheckpointStore()
    checkpoint_store._root = tmp_path / "checkpoints"

    initial_checkpoint = checkpoint_store.create_checkpoint(
        data_model_id=data_model_id,
        job_id=job_id,
        specification=specification,
        seed=42,
        chunk_size=50,
        entity_targets={
            "PARENT": 3,
            "CHILD": 3,
        },
    )

    checkpoint_store.save(
        data_model_id=data_model_id,
        job_id=job_id,
        seed=42,
        entities=initial_checkpoint["entities"],
        specification_hash=initial_checkpoint["specification_hash"],
        chunk_size=50,
    )

    artifact_writer = GenerationArtifactWriter(
        checkpoint_store=checkpoint_store,
    )
    artifact_writer._data_directory = tmp_path / "artifacts"

    completed_chunks: list[tuple[str, list[dict]]] = []

    def capture_chunk(*args) -> None:
        entity_name = args[0]
        chunk_number = args[1]
        rows = args[4]

        completed_chunks.append((entity_name, rows))

        checkpoint = checkpoint_store.get(
            data_model_id=data_model_id,
            job_id=job_id,
        )
        assert checkpoint is not None

        entity_state = checkpoint["entities"][entity_name]
        completed = entity_state.setdefault("completed_chunks", [])

        if chunk_number not in completed:
            completed.append(chunk_number)
            completed.sort()

        entity_state["committed_rows"] = min(
            len(completed) * 50,
            entity_state["target_rows"],
        )

        checkpoint_store.save(
            data_model_id=data_model_id,
            job_id=job_id,
            seed=42,
            entities=checkpoint["entities"],
            specification_hash=checkpoint["specification_hash"],
            chunk_size=50,
        )

    executor = GenerationExecutor(
        seed=42,
        checkpoint_store=checkpoint_store,
        artifact_writer=artifact_writer,
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

    parent_ids = {
        str(row["PARENT_ID"])
        for row in parent_rows
    }

    child_parent_ids = {
        str(row["PARENT_ID"])
        for row in child_rows
    }

    assert len(parent_rows) == 3
    assert len(child_rows) == 3
    assert child_parent_ids == parent_ids
    assert len(child_parent_ids) == 3
    assert result.generated_rows == 6


def test_executor_excludes_previous_chunk_values_for_unique_semantics(
    tmp_path,
    monkeypatch,
) -> None:
    from app.services.generation_semantic_store import GenerationSemanticStore
    from app.services.generation_checkpoint_store import GenerationCheckpointStore

    monkeypatch.chdir(tmp_path)

    data_model_id = "FORGE-UNIQUE-REGRESSION"
    job_id = "FORGE-UNIQUE-CHUNK-TEST"

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
    checkpoint_store._root = tmp_path / "checkpoints"

    executor = GenerationExecutor(
        seed=42,
        ai_service=ai_service,
        semantic_store=semantic_store,
        checkpoint_store=checkpoint_store,
    )

    specification = {
        "entities": [
            {
                "name": "PRODUCT",
                "population": {
                    "count": 51,
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
                target_rows=51,
            ),
        ),
    )

    checkpoint = checkpoint_store.create_checkpoint(
        data_model_id=data_model_id,
        job_id=job_id,
        specification=specification,
        seed=42,
        chunk_size=50,
        entity_targets={"PRODUCT": 51},
    )
    checkpoint_store.save(
        data_model_id=data_model_id,
        job_id=job_id,
        seed=42,
        entities=checkpoint["entities"],
        specification_hash=checkpoint["specification_hash"],
        chunk_size=50,
    )

    executor.execute(
        specification=specification,
        plan=plan,
        data_model_id=data_model_id,
        job_id=job_id,
    )

    assert len(ai_service.calls) == 2

    assert ai_service.calls[0]["exclude_values"] == []

    assert ai_service.calls[1]["exclude_values"] == first_batch

    persisted = semantic_store.get(
        data_model_id=data_model_id,
        job_id=job_id,
        entity_name="PRODUCT",
        field_name="PRODUCT_NAME",
    )

    assert persisted is not None
    assert persisted["mode"] == "UNIQUE"
    assert persisted["values"] == first_batch + second_batch

    normalized = [
        value.strip().casefold()
        for value in persisted["values"]
    ]

    assert len(normalized) == 51
    assert len(set(normalized)) == 51
