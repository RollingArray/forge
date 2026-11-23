import csv
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

import app.services.generation_service as generation_service_module
import app.services.generation.artifact_reader as artifact_reader_module
import app.services.generation.artifact_writer as artifact_writer_module
from app.constants.generation import GENERATION_ALGORITHM_VERSION
from app.models.generation_model import (
    GenerationEntityProgress,
    GenerationEntityStatus,
    GenerationJobRecord,
    GenerationJobStatus,
)
from app.services.generation.artifact_reader import GenerationArtifactReader
from app.services.generation.artifact_writer import GenerationArtifactWriter
from app.services.generation_checkpoint_store import GenerationCheckpointStore
from app.services.generation_persistence_errors import ArtifactIntegrityError
from app.services.generation_service import GenerationService


DATA_MODEL_ID = "MODEL-TEST"
JOB_ID = "JOB-TEST"
ENTITY_NAME = "ORGANIZATION"
ATTEMPT_ID = "test-attempt"

SPECIFICATION = {
    "name": "Test Model",
    "generation": {"seed": 42},
    "entities": [],
}


class FakePlanner:
    def __init__(self, target_rows: int = 75):
        self.target_rows = target_rows

    def build(self, *, specification):
        return SimpleNamespace(
            entities=[
                SimpleNamespace(
                    entity_name=ENTITY_NAME,
                    target_rows=self.target_rows,
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
    chunk_size: int = 50,
    target_rows: int = 75,
):
    data_directory = tmp_path / "data"
    data_root = data_directory / "data_model"
    data_root.mkdir(parents=True)

    monkeypatch.setattr(
        generation_service_module,
        "__file__",
        str(tmp_path / "app" / "services" / "generation_service.py"),
    )
    monkeypatch.setattr(
        artifact_reader_module,
        "__file__",
        str(
            tmp_path
            / "app"
            / "services"
            / "generation"
            / "artifact_reader.py"
        ),
    )
    monkeypatch.setattr(
        artifact_writer_module,
        "__file__",
        str(
            tmp_path
            / "app"
            / "services"
            / "generation"
            / "artifact_writer.py"
        ),
    )

    checkpoint_store = GenerationCheckpointStore()
    checkpoint_store._root = data_root

    service = GenerationService(
        generation_planner=FakePlanner(target_rows=target_rows),
        checkpoint_store=checkpoint_store,
    )
    service._job_store = MagicMock()

    job = GenerationJobRecord(
        data_model_id=DATA_MODEL_ID,
        job_id=JOB_ID,
        status=GenerationJobStatus.INTERRUPTED,
        created_at=datetime.now(timezone.utc),
        total_target_rows=target_rows,
        total_generated_rows=target_rows,
        progress=1.0,
        attempt_id=ATTEMPT_ID,
        entities=[
            GenerationEntityProgress(
                entity_name=ENTITY_NAME,
                target_rows=target_rows,
                generated_rows=target_rows,
                chunk_size=chunk_size,
                completed_chunks=2,
                total_chunks=2,
                status=GenerationEntityStatus.COMPLETED,
            )
        ],
    )

    checkpoint_store.initialize(
        data_model_id=DATA_MODEL_ID,
        job_id=JOB_ID,
        specification=SPECIFICATION,
        seed=42,
        chunk_size=chunk_size,
        algorithm_version=GENERATION_ALGORITHM_VERSION,
        attempt_id=ATTEMPT_ID,
        entity_targets={ENTITY_NAME: target_rows},
    )

    job_directory = (
        data_root / DATA_MODEL_ID / "generation" / JOB_ID
    )
    chunks_dir = (
        job_directory
        / "generated"
        / ENTITY_NAME
        / "chunks"
    )

    first_chunk_rows = [
        {"ID": str(number), "NAME": f"Record {number}"}
        for number in range(1, min(chunk_size, target_rows) + 1)
    ]

    first_chunk_path = chunks_dir / "chunk_000001.csv"
    second_chunk_path = chunks_dir / "chunk_000002.csv"

    write_chunk(first_chunk_path, ["ID", "NAME"], first_chunk_rows)
    write_chunk(second_chunk_path, second_chunk_fields, second_chunk_rows)

    first_evidence = GenerationArtifactWriter._evidence(
        job_directory,
        first_chunk_path,
    )
    checkpoint_store.commit_chunk(
        data_model_id=DATA_MODEL_ID,
        job_id=JOB_ID,
        attempt_id=ATTEMPT_ID,
        entity_name=ENTITY_NAME,
        chunk_number=1,
        row_start=0,
        row_count=len(first_chunk_rows),
        artifact=first_evidence,
    )

    expected_second_chunk_rows = max(target_rows - chunk_size, 0)
    second_evidence = GenerationArtifactWriter._evidence(
        job_directory,
        second_chunk_path,
    )
    checkpoint_store.commit_chunk(
        data_model_id=DATA_MODEL_ID,
        job_id=JOB_ID,
        attempt_id=ATTEMPT_ID,
        entity_name=ENTITY_NAME,
        chunk_number=2,
        row_start=chunk_size,
        row_count=expected_second_chunk_rows,
        artifact=second_evidence,
    )

    return (
        service,
        checkpoint_store,
        job,
        chunks_dir,
        data_directory,
        job_directory,
    )


def valid_second_chunk_rows():
    return [
        {"ID": str(number), "NAME": f"Record {number}"}
        for number in range(51, 76)
    ]


def test_reconciliation_retains_valid_250_row_chunks(
    tmp_path,
    monkeypatch,
):
    (
        service,
        checkpoint_store,
        job,
        chunks_dir,
        _,
        _,
    ) = build_reconciliation_case(
        tmp_path,
        monkeypatch,
        second_chunk_fields=["ID", "NAME"],
        second_chunk_rows=[
            {"ID": "251", "NAME": "Record 251"},
        ],
        chunk_size=250,
        target_rows=251,
    )

    service._reconcile_recovery_checkpoint(
        data_model_id=DATA_MODEL_ID,
        job=job,
        specification=SPECIFICATION,
    )

    manifest = checkpoint_store.get(DATA_MODEL_ID, JOB_ID)
    entity_state = manifest.entities[ENTITY_NAME]

    assert manifest.chunk_size == 250
    assert [chunk.chunk_number for chunk in entity_state.chunks] == [1, 2]
    assert entity_state.committed_rows == 251
    assert job.entities[0].chunk_size == 250
    assert job.entities[0].generated_rows == 251
    assert job.entities[0].total_chunks == 2
    assert job.entities[0].status == GenerationEntityStatus.RUNNING
    assert (chunks_dir / "chunk_000001.csv").exists()
    assert (chunks_dir / "chunk_000002.csv").exists()


def test_reconciliation_retains_valid_short_final_chunk(
    tmp_path,
    monkeypatch,
):
    (
        service,
        checkpoint_store,
        job,
        chunks_dir,
        _,
        _,
    ) = build_reconciliation_case(
        tmp_path,
        monkeypatch,
        second_chunk_fields=["ID", "NAME"],
        second_chunk_rows=valid_second_chunk_rows(),
    )

    service._reconcile_recovery_checkpoint(
        data_model_id=DATA_MODEL_ID,
        job=job,
        specification=SPECIFICATION,
    )

    manifest = checkpoint_store.get(DATA_MODEL_ID, JOB_ID)
    entity_state = manifest.entities[ENTITY_NAME]

    assert [chunk.chunk_number for chunk in entity_state.chunks] == [1, 2]
    assert entity_state.committed_rows == 75
    assert job.entities[0].generated_rows == 75
    assert job.entities[0].status == GenerationEntityStatus.RUNNING
    assert (chunks_dir / "chunk_000001.csv").exists()
    assert (chunks_dir / "chunk_000002.csv").exists()


def test_reconciliation_does_not_discard_chunk_with_incorrect_row_count(
    tmp_path,
    monkeypatch,
):
    (
        service,
        checkpoint_store,
        job,
        chunks_dir,
        data_directory,
        _,
    ) = build_reconciliation_case(
        tmp_path,
        monkeypatch,
        second_chunk_fields=["ID", "NAME"],
        second_chunk_rows=valid_second_chunk_rows()[:-1],
    )

    service._reconcile_recovery_checkpoint(
        data_model_id=DATA_MODEL_ID,
        job=job,
        specification=SPECIFICATION,
    )

    manifest = checkpoint_store.get(DATA_MODEL_ID, JOB_ID)
    entity_state = manifest.entities[ENTITY_NAME]

    # Recovery verifies committed bytes and metadata. CSV structure and
    # physical row count are checked by the artifact reader.
    assert [chunk.chunk_number for chunk in entity_state.chunks] == [1, 2]
    assert entity_state.committed_rows == 75
    assert (chunks_dir / "chunk_000002.csv").exists()

    reader = GenerationArtifactReader(checkpoint_store)
    reader._data_directory = data_directory

    with pytest.raises(ArtifactIntegrityError):
        list(
            reader.iter_entity_rows(
                data_model_id=DATA_MODEL_ID,
                job_id=JOB_ID,
                entity_name=ENTITY_NAME,
            )
        )

    # A read-time integrity failure must not silently rewrite the manifest
    # or delete the committed artifact.
    manifest_after_read = checkpoint_store.get(DATA_MODEL_ID, JOB_ID)
    assert [
        chunk.chunk_number
        for chunk in manifest_after_read.entities[ENTITY_NAME].chunks
    ] == [1, 2]
    assert (chunks_dir / "chunk_000002.csv").exists()


@pytest.mark.parametrize(
    "second_chunk_fields",
    [
        ["ID", "OTHER"],
        ["NAME", "ID"],
    ],
)
def test_consolidation_rejects_chunk_schema_mismatch_without_discarding_chunks(
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

    (
        service,
        checkpoint_store,
        job,
        chunks_dir,
        data_directory,
        job_directory,
    ) = build_reconciliation_case(
        tmp_path,
        monkeypatch,
        second_chunk_fields=second_chunk_fields,
        second_chunk_rows=rows,
    )

    service._reconcile_recovery_checkpoint(
        data_model_id=DATA_MODEL_ID,
        job=job,
        specification=SPECIFICATION,
    )

    writer = GenerationArtifactWriter(checkpoint_store)
    writer._data_directory = data_directory

    with pytest.raises(ValueError, match="Chunk schema mismatch"):
        writer.consolidate_entity(
            DATA_MODEL_ID,
            JOB_ID,
            ENTITY_NAME,
            attempt_id=ATTEMPT_ID,
            fieldnames=["ID", "NAME"],
        )

    manifest = checkpoint_store.get(DATA_MODEL_ID, JOB_ID)
    entity_state = manifest.entities[ENTITY_NAME]

    assert [chunk.chunk_number for chunk in entity_state.chunks] == [1, 2]
    assert entity_state.committed_rows == 75
    assert (chunks_dir / "chunk_000001.csv").exists()
    assert (chunks_dir / "chunk_000002.csv").exists()
    assert not (
        job_directory / "generated" / f"{ENTITY_NAME}.csv"
    ).exists()


def test_reconciliation_rejects_modified_committed_artifact_without_repairing_it(
    tmp_path,
    monkeypatch,
):
    (
        service,
        checkpoint_store,
        job,
        chunks_dir,
        _,
        _,
    ) = build_reconciliation_case(
        tmp_path,
        monkeypatch,
        second_chunk_fields=["ID", "NAME"],
        second_chunk_rows=valid_second_chunk_rows(),
    )

    second_chunk_path = chunks_dir / "chunk_000002.csv"
    with second_chunk_path.open("a", encoding="utf-8") as handle:
        handle.write("tampered,data\\n")

    with pytest.raises(ArtifactIntegrityError):
        service._reconcile_recovery_checkpoint(
            data_model_id=DATA_MODEL_ID,
            job=job,
            specification=SPECIFICATION,
        )

    manifest = checkpoint_store.get(DATA_MODEL_ID, JOB_ID)
    assert [chunk.chunk_number for chunk in manifest.entities[ENTITY_NAME].chunks] == [1, 2]
    assert second_chunk_path.exists()


def test_post_generation_validation_exception_preserves_completed_generation(
    tmp_path,
    monkeypatch,
):
    (
        service,
        checkpoint_store,
        job,
        _,
        data_directory,
        _,
    ) = build_reconciliation_case(
        tmp_path,
        monkeypatch,
        second_chunk_fields=["ID", "NAME"],
        second_chunk_rows=valid_second_chunk_rows(),
    )

    writer = GenerationArtifactWriter(checkpoint_store)
    writer._data_directory = data_directory
    writer.consolidate_entity(
        DATA_MODEL_ID,
        JOB_ID,
        ENTITY_NAME,
        attempt_id=ATTEMPT_ID,
        fieldnames=["ID", "NAME"],
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
    service._job_store.get.return_value = job

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

    manifest = checkpoint_store.get(DATA_MODEL_ID, JOB_ID)
    finalization = manifest.entities[ENTITY_NAME].finalization
    assert finalization.status.value == "COMMITTED"
    assert finalization.output is not None

    service._job_store.save.assert_called()
    service._generation_log_store.append.assert_called()
