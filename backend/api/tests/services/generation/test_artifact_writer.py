import csv
from pathlib import Path

import pytest

from app.services.generation.artifact_writer import GenerationArtifactWriter
from app.services.generation_checkpoint_store import (
    GenerationCheckpointStore,
    compute_specification_hash,
)


DATA_MODEL_ID = "MODEL-TEST"
JOB_ID = "JOB-WRITER-TEST"
ENTITY_NAME = "ORGANIZATION"

SPECIFICATION = {
    "name": "Test Model",
    "generation": {"seed": 42},
    "entities": [],
}


def build_writer(tmp_path: Path):
    checkpoint_store = GenerationCheckpointStore()
    checkpoint_store._root = tmp_path / "data_model"

    writer = GenerationArtifactWriter(
        checkpoint_store=checkpoint_store,
    )
    writer._data_directory = tmp_path

    return writer, checkpoint_store


def commit_chunks(checkpoint_store, chunk_numbers):
    checkpoint_store.save(
        data_model_id=DATA_MODEL_ID,
        job_id=JOB_ID,
        seed=42,
        specification_hash=compute_specification_hash(SPECIFICATION),
        chunk_size=50,
        entities={
            ENTITY_NAME: {
                "target_rows": 75,
                "completed_chunks": chunk_numbers,
                "committed_rows": 75 if chunk_numbers else 0,
            }
        },
    )


def read_csv(path: Path):
    with path.open("r", newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def test_consolidate_entity_returns_and_persists_actual_row_count(tmp_path):
    writer, checkpoint_store = build_writer(tmp_path)

    first_chunk = [
        {"ID": str(i), "NAME": f"Record {i}"}
        for i in range(1, 51)
    ]
    second_chunk = [
        {"ID": str(i), "NAME": f"Record {i}"}
        for i in range(51, 76)
    ]

    assert writer.write_chunk(
        DATA_MODEL_ID,
        JOB_ID,
        ENTITY_NAME,
        1,
        first_chunk,
    ) == 50

    assert writer.write_chunk(
        DATA_MODEL_ID,
        JOB_ID,
        ENTITY_NAME,
        2,
        second_chunk,
    ) == 25

    commit_chunks(checkpoint_store, [1, 2])

    row_count = writer.consolidate_entity(
        DATA_MODEL_ID,
        JOB_ID,
        ENTITY_NAME,
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


def test_consolidate_entity_rejects_schema_mismatch_between_chunks(
    tmp_path,
):
    writer, checkpoint_store = build_writer(tmp_path)

    writer.write_chunk(
        DATA_MODEL_ID,
        JOB_ID,
        ENTITY_NAME,
        1,
        [
            {"ID": str(i), "NAME": f"Record {i}"}
            for i in range(1, 51)
        ],
    )

    writer.write_chunk(
        DATA_MODEL_ID,
        JOB_ID,
        ENTITY_NAME,
        2,
        [
            {"ID": str(i), "OTHER": f"Record {i}"}
            for i in range(51, 76)
        ],
    )

    commit_chunks(checkpoint_store, [1, 2])

    with pytest.raises(
        ValueError,
        match="Chunk schema mismatch",
    ):
        writer.consolidate_entity(
            DATA_MODEL_ID,
            JOB_ID,
            ENTITY_NAME,
        )
