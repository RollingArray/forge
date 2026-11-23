import csv
from pathlib import Path

import pytest

from app.services.generation.artifact_writer import GenerationArtifactWriter
from app.services.generation_checkpoint_store import GenerationCheckpointStore
from app.services.generation_persistence_errors import (
    ArtifactIntegrityError,
    CheckpointValidationError,
)


DATA_MODEL_ID = "MODEL-TEST"
JOB_ID = "JOB-WRITER-TEST"
ENTITY_NAME = "ORGANIZATION"
ATTEMPT_ID = "ATTEMPT-WRITER-001"

SPECIFICATION = {
    "name": "Test Model",
    "generation": {"seed": 42},
    "entities": [],
}


def build_writer(
    tmp_path: Path,
    *,
    target_rows: int = 75,
):
    checkpoint_store = GenerationCheckpointStore()
    checkpoint_store._root = tmp_path / "data_model"

    writer = GenerationArtifactWriter(
        checkpoint_store=checkpoint_store,
    )
    writer._data_directory = tmp_path

    checkpoint_store.initialize(
        data_model_id=DATA_MODEL_ID,
        job_id=JOB_ID,
        specification=SPECIFICATION,
        seed=42,
        chunk_size=50,
        algorithm_version="v1",
        attempt_id=ATTEMPT_ID,
        entity_targets={ENTITY_NAME: target_rows},
    )

    writer.initialize_job(DATA_MODEL_ID, JOB_ID)

    return writer, checkpoint_store


def write_chunk(
    writer,
    chunk_number: int,
    row_start: int,
    rows: list[dict],
):
    return writer.write_chunk(
        DATA_MODEL_ID,
        JOB_ID,
        ENTITY_NAME,
        chunk_number,
        rows,
        attempt_id=ATTEMPT_ID,
        row_start=row_start,
    )


def read_csv(path: Path):
    with path.open("r", newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def test_write_chunk_publishes_and_commits_v2_evidence(tmp_path):
    writer, checkpoint_store = build_writer(tmp_path)

    rows = [
        {"ID": str(index), "NAME": f"Record {index}"}
        for index in range(1, 51)
    ]

    assert write_chunk(writer, 1, 0, rows) == 50

    manifest = checkpoint_store.get(DATA_MODEL_ID, JOB_ID)
    assert manifest is not None

    entity = manifest.entities[ENTITY_NAME]
    assert entity.committed_rows == 50
    assert len(entity.chunks) == 1
    assert entity.chunks[0].chunk_number == 1
    assert entity.chunks[0].row_start == 0
    assert entity.chunks[0].row_count == 50

    checkpoint_store.verify_artifact(
        data_model_id=DATA_MODEL_ID,
        job_id=JOB_ID,
        artifact=entity.chunks[0].artifact,
    )


def test_consolidate_entity_returns_and_commits_actual_row_count(tmp_path):
    writer, checkpoint_store = build_writer(tmp_path)

    first_chunk = [
        {"ID": str(index), "NAME": f"Record {index}"}
        for index in range(1, 51)
    ]
    second_chunk = [
        {"ID": str(index), "NAME": f"Record {index}"}
        for index in range(51, 76)
    ]

    assert write_chunk(writer, 1, 0, first_chunk) == 50
    assert write_chunk(writer, 2, 50, second_chunk) == 25

    row_count = writer.consolidate_entity(
        DATA_MODEL_ID,
        JOB_ID,
        ENTITY_NAME,
        attempt_id=ATTEMPT_ID,
    )

    output_path = writer.get_entity_csv_path(
        DATA_MODEL_ID,
        JOB_ID,
        ENTITY_NAME,
    )
    rows = read_csv(output_path)

    assert row_count == 75
    assert len(rows) == 75
    assert rows[0] == {"ID": "1", "NAME": "Record 1"}
    assert rows[-1] == {"ID": "75", "NAME": "Record 75"}

    manifest = checkpoint_store.get(DATA_MODEL_ID, JOB_ID)
    assert manifest is not None

    finalization = manifest.entities[ENTITY_NAME].finalization
    assert finalization.status.value == "COMMITTED"
    assert finalization.output is not None

    checkpoint_store.verify_artifact(
        data_model_id=DATA_MODEL_ID,
        job_id=JOB_ID,
        artifact=finalization.output,
    )


def test_consolidation_is_idempotent_after_finalization(tmp_path):
    writer, _ = build_writer(tmp_path, target_rows=2)

    write_chunk(
        writer,
        1,
        0,
        [{"ID": "1"}, {"ID": "2"}],
    )

    assert writer.consolidate_entity(
        DATA_MODEL_ID,
        JOB_ID,
        ENTITY_NAME,
        attempt_id=ATTEMPT_ID,
    ) == 2

    output_path = writer.get_entity_csv_path(
        DATA_MODEL_ID,
        JOB_ID,
        ENTITY_NAME,
    )
    original_bytes = output_path.read_bytes()

    assert writer.consolidate_entity(
        DATA_MODEL_ID,
        JOB_ID,
        ENTITY_NAME,
        attempt_id=ATTEMPT_ID,
    ) == 2

    assert output_path.read_bytes() == original_bytes


def test_consolidate_entity_rejects_schema_mismatch_between_chunks(
    tmp_path,
):
    writer, _ = build_writer(tmp_path)

    write_chunk(
        writer,
        1,
        0,
        [
            {"ID": str(index), "NAME": f"Record {index}"}
            for index in range(50)
        ],
    )

    write_chunk(
        writer,
        2,
        50,
        [
            {"ID": str(index), "OTHER": f"Record {index}"}
            for index in range(50, 75)
        ],
    )

    with pytest.raises(ValueError, match="Chunk schema mismatch"):
        writer.consolidate_entity(
            DATA_MODEL_ID,
            JOB_ID,
            ENTITY_NAME,
            attempt_id=ATTEMPT_ID,
        )

    assert not writer.get_entity_csv_path(
        DATA_MODEL_ID,
        JOB_ID,
        ENTITY_NAME,
    ).exists()


def test_committed_chunk_cannot_be_overwritten_with_different_content(
    tmp_path,
):
    writer, _ = build_writer(tmp_path, target_rows=2)

    write_chunk(
        writer,
        1,
        0,
        [{"ID": "1"}, {"ID": "2"}],
    )

    chunk_path = (
        writer._job_directory(DATA_MODEL_ID, JOB_ID)
        / "generated"
        / ENTITY_NAME
        / "chunks"
        / "chunk_000001.csv"
    )
    original_bytes = chunk_path.read_bytes()

    with pytest.raises(CheckpointValidationError, match="already committed"):
        write_chunk(
            writer,
            1,
            0,
            [{"ID": "1"}, {"ID": "DIFFERENT"}],
        )

    assert chunk_path.read_bytes() == original_bytes


def test_identical_chunk_retry_is_idempotent(tmp_path):
    writer, checkpoint_store = build_writer(tmp_path, target_rows=2)
    rows = [{"ID": "1"}, {"ID": "2"}]

    assert write_chunk(writer, 1, 0, rows) == 2
    assert write_chunk(writer, 1, 0, rows) == 2

    manifest = checkpoint_store.get(DATA_MODEL_ID, JOB_ID)
    assert manifest is not None
    assert len(manifest.entities[ENTITY_NAME].chunks) == 1


def test_uncommitted_orphan_chunk_is_replaced_on_retry(tmp_path):
    writer, checkpoint_store = build_writer(tmp_path, target_rows=2)

    chunk_path = (
        writer._job_directory(DATA_MODEL_ID, JOB_ID)
        / "generated"
        / ENTITY_NAME
        / "chunks"
        / "chunk_000001.csv"
    )
    chunk_path.parent.mkdir(parents=True, exist_ok=True)
    chunk_path.write_text("ID\nORPHAN\n", encoding="utf-8")

    write_chunk(
        writer,
        1,
        0,
        [{"ID": "1"}, {"ID": "2"}],
    )

    manifest = checkpoint_store.get(DATA_MODEL_ID, JOB_ID)
    assert manifest is not None
    assert manifest.entities[ENTITY_NAME].committed_rows == 2
    assert read_csv(chunk_path) == [{"ID": "1"}, {"ID": "2"}]


def test_zero_row_entity_publishes_header_only_output(tmp_path):
    writer, checkpoint_store = build_writer(tmp_path, target_rows=0)

    assert writer.consolidate_entity(
        DATA_MODEL_ID,
        JOB_ID,
        ENTITY_NAME,
        attempt_id=ATTEMPT_ID,
        fieldnames=["ID", "NAME"],
    ) == 0

    output_path = writer.get_entity_csv_path(
        DATA_MODEL_ID,
        JOB_ID,
        ENTITY_NAME,
    )

    with output_path.open("r", newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        assert reader.fieldnames == ["ID", "NAME"]
        assert list(reader) == []

    manifest = checkpoint_store.get(DATA_MODEL_ID, JOB_ID)
    assert manifest is not None
    assert (
        manifest.entities[ENTITY_NAME].finalization.status.value
        == "COMMITTED"
    )


def test_consolidation_requires_all_target_rows_committed(tmp_path):
    writer, _ = build_writer(tmp_path)

    write_chunk(
        writer,
        1,
        0,
        [{"ID": str(index)} for index in range(50)],
    )

    with pytest.raises(CheckpointValidationError, match="rows committed"):
        writer.consolidate_entity(
            DATA_MODEL_ID,
            JOB_ID,
            ENTITY_NAME,
            attempt_id=ATTEMPT_ID,
        )


def test_finalized_output_corruption_is_not_silently_repaired(tmp_path):
    writer, _ = build_writer(tmp_path, target_rows=2)

    write_chunk(
        writer,
        1,
        0,
        [{"ID": "1"}, {"ID": "2"}],
    )

    writer.consolidate_entity(
        DATA_MODEL_ID,
        JOB_ID,
        ENTITY_NAME,
        attempt_id=ATTEMPT_ID,
    )

    output_path = writer.get_entity_csv_path(
        DATA_MODEL_ID,
        JOB_ID,
        ENTITY_NAME,
    )
    output_path.write_text("ID\nALTERED\n", encoding="utf-8")

    with pytest.raises(ArtifactIntegrityError):
        writer.consolidate_entity(
            DATA_MODEL_ID,
            JOB_ID,
            ENTITY_NAME,
            attempt_id=ATTEMPT_ID,
        )
