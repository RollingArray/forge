from __future__ import annotations

import csv
import hashlib
from pathlib import Path

import pytest

from app.models.generation_persistence import GenerationArtifactEvidence
from app.services.generation.artifact_reader import GenerationArtifactReader
from app.services.generation_checkpoint_store import GenerationCheckpointStore
from app.services.generation_persistence_errors import ArtifactIntegrityError


MODEL_ID = "MODEL-TEST"
JOB_ID = "JOB-1"
ATTEMPT_ID = "ATTEMPT-001"
SPECIFICATION = {"entities": [{"name": "CUSTOMER"}]}
CHUNK_SIZE = 2


def _write_chunk(
    *,
    root: Path,
    entity_name: str,
    chunk_number: int,
    rows: list[dict[str, str]],
) -> Path:
    directory = (
        root
        / "generated"
        / entity_name
        / "chunks"
    )
    directory.mkdir(parents=True, exist_ok=True)

    path = directory / f"chunk_{chunk_number:06d}.csv"

    if not rows:
        raise ValueError("Test chunks must contain at least one row.")

    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=list(rows[0].keys()),
        )
        writer.writeheader()
        writer.writerows(rows)

    return path


def _reader_and_store(tmp_path: Path):
    reader = GenerationArtifactReader()
    reader._data_directory = tmp_path

    store = GenerationCheckpointStore()
    store._root = tmp_path / "data_model"
    reader._checkpoint_store = store

    return reader, store


def _commit_test_checkpoint(
    reader: GenerationArtifactReader,
    store: GenerationCheckpointStore,
    *,
    entity_name: str,
    chunk_numbers: list[int],
) -> None:
    job_directory = store._job_directory(MODEL_ID, JOB_ID)

    row_counts: dict[int, int] = {}
    artifacts: dict[int, GenerationArtifactEvidence] = {}

    for chunk_number in chunk_numbers:
        path = (
            job_directory
            / "generated"
            / entity_name
            / "chunks"
            / f"chunk_{chunk_number:06d}.csv"
        )

        content = path.read_bytes()

        with path.open("r", newline="", encoding="utf-8") as handle:
            row_counts[chunk_number] = sum(1 for _ in csv.DictReader(handle))

        relative_path = path.relative_to(job_directory).as_posix()
        artifacts[chunk_number] = GenerationArtifactEvidence(
            path=relative_path,
            size_bytes=len(content),
            sha256=hashlib.sha256(content).hexdigest(),
        )

    target_rows = max(
        (
            (number - 1) * CHUNK_SIZE + row_counts[number]
            for number in chunk_numbers
        ),
        default=0,
    )

    store.initialize(
        data_model_id=MODEL_ID,
        job_id=JOB_ID,
        specification=SPECIFICATION,
        seed=42,
        chunk_size=CHUNK_SIZE,
        algorithm_version="v1",
        attempt_id=ATTEMPT_ID,
        entity_targets={entity_name: target_rows},
    )

    for chunk_number in sorted(chunk_numbers):
        store.commit_chunk(
            data_model_id=MODEL_ID,
            job_id=JOB_ID,
            attempt_id=ATTEMPT_ID,
            entity_name=entity_name,
            chunk_number=chunk_number,
            row_start=(chunk_number - 1) * CHUNK_SIZE,
            row_count=row_counts[chunk_number],
            artifact=artifacts[chunk_number],
        )


def test_iter_entity_chunks_streams_rows_in_chunk_order(
    tmp_path: Path,
) -> None:
    reader, store = _reader_and_store(tmp_path)
    job_directory = store._job_directory(MODEL_ID, JOB_ID)

    _write_chunk(
        root=job_directory,
        entity_name="CUSTOMER",
        chunk_number=2,
        rows=[{"ID": "3"}, {"ID": "4"}],
    )
    _write_chunk(
        root=job_directory,
        entity_name="CUSTOMER",
        chunk_number=1,
        rows=[{"ID": "1"}, {"ID": "2"}],
    )

    _commit_test_checkpoint(
        reader,
        store,
        entity_name="CUSTOMER",
        chunk_numbers=[1, 2],
    )

    rows = list(
        reader.iter_entity_chunks(
            MODEL_ID,
            JOB_ID,
            "CUSTOMER",
        )
    )

    assert rows == [
        {"ID": "1"},
        {"ID": "2"},
        {"ID": "3"},
        {"ID": "4"},
    ]


def test_iter_entity_rows_preserves_global_positions_for_sparse_chunks(
    tmp_path: Path,
) -> None:
    reader, store = _reader_and_store(tmp_path)
    job_directory = store._job_directory(MODEL_ID, JOB_ID)

    _write_chunk(
        root=job_directory,
        entity_name="CUSTOMER",
        chunk_number=1,
        rows=[{"ID": "C1"}, {"ID": "C2"}],
    )
    _write_chunk(
        root=job_directory,
        entity_name="CUSTOMER",
        chunk_number=3,
        rows=[{"ID": "C5"}, {"ID": "C6"}],
    )

    _commit_test_checkpoint(
        reader,
        store,
        entity_name="CUSTOMER",
        chunk_numbers=[1, 3],
    )

    rows = list(
        reader.iter_entity_rows(
            data_model_id=MODEL_ID,
            job_id=JOB_ID,
            entity_name="CUSTOMER",
        )
    )

    assert rows == [
        (0, {"ID": "C1"}),
        (1, {"ID": "C2"}),
        (4, {"ID": "C5"}),
        (5, {"ID": "C6"}),
    ]


def test_get_identity_keys_by_row_preserves_sparse_positions(
    tmp_path: Path,
) -> None:
    reader, store = _reader_and_store(tmp_path)
    job_directory = store._job_directory(MODEL_ID, JOB_ID)

    _write_chunk(
        root=job_directory,
        entity_name="CUSTOMER",
        chunk_number=1,
        rows=[
            {"CUSTOMER_ID": "C001"},
            {"CUSTOMER_ID": "C002"},
        ],
    )
    _write_chunk(
        root=job_directory,
        entity_name="CUSTOMER",
        chunk_number=3,
        rows=[
            {"CUSTOMER_ID": "C005"},
            {"CUSTOMER_ID": "C006"},
        ],
    )

    _commit_test_checkpoint(
        reader,
        store,
        entity_name="CUSTOMER",
        chunk_numbers=[1, 3],
    )

    key_space = reader.get_identity_keys_by_row(
        data_model_id=MODEL_ID,
        job_id=JOB_ID,
        entity_name="CUSTOMER",
        identity_fields=("CUSTOMER_ID",),
    )

    assert key_space == {
        0: ("C001",),
        1: ("C002",),
        4: ("C005",),
        5: ("C006",),
    }


def test_get_entity_key_space_retains_set_compatibility(
    tmp_path: Path,
) -> None:
    reader, store = _reader_and_store(tmp_path)
    job_directory = store._job_directory(MODEL_ID, JOB_ID)

    _write_chunk(
        root=job_directory,
        entity_name="CUSTOMER",
        chunk_number=1,
        rows=[
            {"CUSTOMER_ID": "C001"},
            {"CUSTOMER_ID": "C002"},
        ],
    )

    _commit_test_checkpoint(
        reader,
        store,
        entity_name="CUSTOMER",
        chunk_numbers=[1],
    )

    assert reader.get_entity_key_space(
        MODEL_ID,
        JOB_ID,
        "CUSTOMER",
        ("CUSTOMER_ID",),
    ) == {("C001",), ("C002",)}


def test_reader_returns_no_rows_when_entity_has_no_committed_chunks(
    tmp_path: Path,
) -> None:
    reader, store = _reader_and_store(tmp_path)

    _commit_test_checkpoint(
        reader,
        store,
        entity_name="CUSTOMER",
        chunk_numbers=[],
    )

    assert list(
        reader.iter_entity_chunks(
            MODEL_ID,
            JOB_ID,
            "CUSTOMER",
        )
    ) == []


@pytest.mark.parametrize(
    "entity_name",
    ["", ".", "..", "../CUSTOMER", "CUSTOMER/OTHER", "CUSTOMER\\\\OTHER"],
)
def test_reader_rejects_invalid_entity_name(
    tmp_path: Path,
    entity_name: str,
) -> None:
    reader, _ = _reader_and_store(tmp_path)

    with pytest.raises(ValueError, match="Invalid entity name"):
        list(
            reader.iter_entity_chunks(
                MODEL_ID,
                JOB_ID,
                entity_name,
            )
        )


def test_reader_does_not_expose_uncommitted_orphan_chunk(
    tmp_path: Path,
) -> None:
    reader, store = _reader_and_store(tmp_path)
    job_directory = store._job_directory(MODEL_ID, JOB_ID)

    _write_chunk(
        root=job_directory,
        entity_name="CUSTOMER",
        chunk_number=1,
        rows=[{"ID": "1"}, {"ID": "2"}],
    )
    _write_chunk(
        root=job_directory,
        entity_name="CUSTOMER",
        chunk_number=2,
        rows=[{"ID": "ORPHAN-1"}, {"ID": "ORPHAN-2"}],
    )

    _commit_test_checkpoint(
        reader,
        store,
        entity_name="CUSTOMER",
        chunk_numbers=[1],
    )

    rows = list(
        reader.iter_entity_chunks(
            MODEL_ID,
            JOB_ID,
            "CUSTOMER",
        )
    )

    assert rows == [{"ID": "1"}, {"ID": "2"}]


def test_reader_rejects_missing_committed_artifact(
    tmp_path: Path,
) -> None:
    reader, store = _reader_and_store(tmp_path)
    job_directory = store._job_directory(MODEL_ID, JOB_ID)

    path = _write_chunk(
        root=job_directory,
        entity_name="CUSTOMER",
        chunk_number=1,
        rows=[{"ID": "1"}, {"ID": "2"}],
    )

    _commit_test_checkpoint(
        reader,
        store,
        entity_name="CUSTOMER",
        chunk_numbers=[1],
    )

    path.unlink()

    with pytest.raises(ArtifactIntegrityError):
        list(
            reader.iter_entity_chunks(
                MODEL_ID,
                JOB_ID,
                "CUSTOMER",
            )
        )


def test_reader_rejects_modified_committed_artifact(
    tmp_path: Path,
) -> None:
    reader, store = _reader_and_store(tmp_path)
    job_directory = store._job_directory(MODEL_ID, JOB_ID)

    path = _write_chunk(
        root=job_directory,
        entity_name="CUSTOMER",
        chunk_number=1,
        rows=[{"ID": "1"}, {"ID": "2"}],
    )

    _commit_test_checkpoint(
        reader,
        store,
        entity_name="CUSTOMER",
        chunk_numbers=[1],
    )

    path.write_text(
        "ID\\n1\\nALTERED\\n",
        encoding="utf-8",
    )

    with pytest.raises(ArtifactIntegrityError):
        list(
            reader.iter_entity_chunks(
                MODEL_ID,
                JOB_ID,
                "CUSTOMER",
            )
        )


def test_reader_rejects_csv_row_count_mismatch(
    tmp_path: Path,
) -> None:
    reader, store = _reader_and_store(tmp_path)
    job_directory = store._job_directory(MODEL_ID, JOB_ID)

    path = _write_chunk(
        root=job_directory,
        entity_name="CUSTOMER",
        chunk_number=1,
        rows=[{"ID": "1"}, {"ID": "2"}],
    )

    _commit_test_checkpoint(
        reader,
        store,
        entity_name="CUSTOMER",
        chunk_numbers=[1],
    )

    # Update the manifest evidence to match the modified bytes while
    # retaining the committed row count of two.
    content = b"ID\\n1\\n"
    path.write_bytes(content)

    from app.models.generation_persistence import GenerationArtifactEvidence

    evidence = GenerationArtifactEvidence(
        path="generated/CUSTOMER/chunks/chunk_000001.csv",
        size_bytes=len(content),
        sha256=hashlib.sha256(content).hexdigest(),
    )

    # A second checkpoint cannot replace committed evidence. This test
    # exercises the reader's independent CSV row-count validation by
    # directly changing the manifest evidence on disk.
    checkpoint_path = store._checkpoint_path(MODEL_ID, JOB_ID)
    import json

    payload = json.loads(checkpoint_path.read_text(encoding="utf-8"))
    payload["entities"]["CUSTOMER"]["chunks"][0]["artifact"] = (
        evidence.model_dump(mode="json")
    )
    checkpoint_path.write_text(
        json.dumps(payload),
        encoding="utf-8",
    )

    with pytest.raises(ArtifactIntegrityError, match="row count mismatch"):
        list(
            reader.iter_entity_chunks(
                MODEL_ID,
                JOB_ID,
                "CUSTOMER",
            )
        )
