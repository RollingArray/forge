import csv
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

import app.services.generation_service as generation_service_module
import app.services.generation.artifact_writer as artifact_writer_module
from app.models.generation_model import (
    GenerationEntityProgress,
    GenerationEntityStatus,
    GenerationJobResponse,
    GenerationJobStatus,
)
from app.services.generation_checkpoint_store import (
    GenerationCheckpointStore,
    compute_specification_hash,
)
from app.services.generation_service import GenerationService


DATA_MODEL_ID = "MODEL-TEST"
JOB_ID = "JOB-TEST"
ENTITY_NAME = "ORGANIZATION"

SPECIFICATION = {
    "name": "Test Model",
    "generation": {"seed": 42},
    "entities": [],
}


class FakePlanner:
    def build(self, *, specification):
        return SimpleNamespace(
            entities=[
                SimpleNamespace(
                    entity_name=ENTITY_NAME,
                    target_rows=75,
                )
            ]
        )


def write_chunk(path: Path, fieldnames: list[str], rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def build_reconciliation_case(
    tmp_path: Path,
    monkeypatch,
    *,
    second_chunk_fields: list[str],
    second_chunk_rows: list[dict],
):
    data_root = tmp_path / "data" / "data_model"
    data_root.mkdir(parents=True)

    fake_source_path = (
        tmp_path / "app" / "services" / "generation_service.py"
    )
    monkeypatch.setattr(
        generation_service_module,
        "__file__",
        str(fake_source_path),
    )

    fake_artifact_writer_path = (
        tmp_path / "app" / "services" / "generation"
        / "artifact_writer.py"
    )
    monkeypatch.setattr(
        artifact_writer_module,
        "__file__",
        str(fake_artifact_writer_path),
    )

    checkpoint_store = GenerationCheckpointStore()
    checkpoint_store._root = data_root

    service = GenerationService(
        generation_planner=FakePlanner(),
        checkpoint_store=checkpoint_store,
    )
    service._job_store = MagicMock()

    job = GenerationJobResponse(
        data_model_id=DATA_MODEL_ID,
        job_id=JOB_ID,
        status=GenerationJobStatus.INTERRUPTED,
        created_at=datetime.now(timezone.utc),
        total_target_rows=75,
        total_generated_rows=75,
        progress=1.0,
        entities=[
            GenerationEntityProgress(
                entity_name=ENTITY_NAME,
                target_rows=75,
                generated_rows=75,
                chunk_size=50,
                completed_chunks=2,
                total_chunks=2,
                status=GenerationEntityStatus.COMPLETED,
            )
        ],
    )

    checkpoint_store.save(
        data_model_id=DATA_MODEL_ID,
        job_id=JOB_ID,
        seed=42,
        specification_hash=compute_specification_hash(SPECIFICATION),
        chunk_size=50,
        entities={
            ENTITY_NAME: {
                "target_rows": 75,
                "completed_chunks": [1, 2],
                "committed_rows": 75,
            }
        },
    )

    chunks_dir = (
        data_root
        / DATA_MODEL_ID
        / "generation"
        / JOB_ID
        / "generated"
        / ENTITY_NAME
        / "chunks"
    )

    write_chunk(
        chunks_dir / "chunk_000001.csv",
        ["ID", "NAME"],
        [
            {"ID": str(number), "NAME": f"Record {number}"}
            for number in range(1, 51)
        ],
    )

    write_chunk(
        chunks_dir / "chunk_000002.csv",
        second_chunk_fields,
        second_chunk_rows,
    )

    return service, checkpoint_store, job, chunks_dir


def valid_second_chunk_rows():
    return [
        {"ID": str(number), "NAME": f"Record {number}"}
        for number in range(51, 76)
    ]


def test_reconciliation_retains_valid_short_final_chunk(
    tmp_path,
    monkeypatch,
):
    service, checkpoint_store, job, chunks_dir = (
        build_reconciliation_case(
            tmp_path,
            monkeypatch,
            second_chunk_fields=["ID", "NAME"],
            second_chunk_rows=valid_second_chunk_rows(),
        )
    )

    service._reconcile_recovery_checkpoint(
        data_model_id=DATA_MODEL_ID,
        job=job,
        specification=SPECIFICATION,
    )

    checkpoint = checkpoint_store.get(DATA_MODEL_ID, JOB_ID)
    entity_state = checkpoint["entities"][ENTITY_NAME]

    assert entity_state["completed_chunks"] == [1, 2]
    assert entity_state["committed_rows"] == 75
    assert job.entities[0].generated_rows == 75
    assert job.entities[0].status == GenerationEntityStatus.COMPLETED
    assert (chunks_dir / "chunk_000001.csv").exists()
    assert (chunks_dir / "chunk_000002.csv").exists()


def test_reconciliation_discards_chunk_with_incorrect_row_count(
    tmp_path,
    monkeypatch,
):
    service, checkpoint_store, job, chunks_dir = (
        build_reconciliation_case(
            tmp_path,
            monkeypatch,
            second_chunk_fields=["ID", "NAME"],
            second_chunk_rows=valid_second_chunk_rows()[:-1],
        )
    )

    service._reconcile_recovery_checkpoint(
        data_model_id=DATA_MODEL_ID,
        job=job,
        specification=SPECIFICATION,
    )

    checkpoint = checkpoint_store.get(DATA_MODEL_ID, JOB_ID)
    entity_state = checkpoint["entities"][ENTITY_NAME]

    assert entity_state["completed_chunks"] == [1]
    assert entity_state["committed_rows"] == 50
    assert job.entities[0].generated_rows == 50
    assert job.total_generated_rows == 50
    assert job.progress == pytest.approx(50 / 75)
    assert (chunks_dir / "chunk_000001.csv").exists()
    assert not (chunks_dir / "chunk_000002.csv").exists()


@pytest.mark.parametrize(
    "second_chunk_fields",
    [
        ["ID", "OTHER"],
        ["NAME", "ID"],
    ],
)
def test_reconciliation_discards_chunk_with_schema_mismatch(
    tmp_path,
    monkeypatch,
    second_chunk_fields,
):
    rows = [
        {
            second_chunk_fields[0]: str(number),
            second_chunk_fields[1]: f"Record {number}",
        }
        for number in range(51, 76)
    ]

    service, checkpoint_store, job, chunks_dir = (
        build_reconciliation_case(
            tmp_path,
            monkeypatch,
            second_chunk_fields=second_chunk_fields,
            second_chunk_rows=rows,
        )
    )

    service._reconcile_recovery_checkpoint(
        data_model_id=DATA_MODEL_ID,
        job=job,
        specification=SPECIFICATION,
    )

    checkpoint = checkpoint_store.get(DATA_MODEL_ID, JOB_ID)
    entity_state = checkpoint["entities"][ENTITY_NAME]

    assert entity_state["completed_chunks"] == [1]
    assert entity_state["committed_rows"] == 50
    assert job.entities[0].generated_rows == 50
    assert not (chunks_dir / "chunk_000002.csv").exists()


def test_post_generation_validation_exception_preserves_completed_generation(
    tmp_path,
    monkeypatch,
):
    service, checkpoint_store, job, _ = build_reconciliation_case(
        tmp_path,
        monkeypatch,
        second_chunk_fields=["ID", "NAME"],
        second_chunk_rows=valid_second_chunk_rows(),
    )

    class RaisingRunService:
        def __init__(self, **kwargs):
            pass

        def run(self, **kwargs):
            raise RuntimeError("Post-generation validation failed.")

    monkeypatch.setattr(
        generation_service_module,
        "GenerationRunService",
        RaisingRunService,
    )

    service._specification_service = SimpleNamespace(
        get_specification=lambda **kwargs: SPECIFICATION,
    )
    service._generation_log_store = MagicMock()
    service._event_broker = MagicMock()

    job.status = GenerationJobStatus.RUNNING
    service._jobs[job.job_id] = job

    service._execute_job_reserved(
        data_model_id=DATA_MODEL_ID,
        job_id=JOB_ID,
    )

    assert job.status == GenerationJobStatus.COMPLETED
    assert job.total_generated_rows == 75
    assert job.progress == 1.0
    assert job.entities[0].generated_rows == 75
    assert job.entities[0].status == GenerationEntityStatus.COMPLETED
    assert job.error == "Post-generation validation failed."

    service._job_store.save.assert_called()
    service._generation_log_store.append.assert_called()
