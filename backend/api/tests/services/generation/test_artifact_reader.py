from __future__ import annotations

import csv
from pathlib import Path

import pytest

from app.services.generation.artifact_reader import (
    GenerationArtifactReader,
)


def _write_chunk(
    *,
    root: Path,
    entity_name: str,
    chunk_number: int,
    rows: list[dict[str, str]],
) -> None:
    directory = (
        root
        / "generated"
        / entity_name
        / "chunks"
    )
    directory.mkdir(
        parents=True,
        exist_ok=True,
    )

    path = directory / f"chunk_{chunk_number:06d}.csv"

    with path.open(
        "w",
        newline="",
        encoding="utf-8",
    ) as file:
        writer = csv.DictWriter(
            file,
            fieldnames=list(rows[0].keys()),
        )
        writer.writeheader()
        writer.writerows(rows)


def test_iter_entity_chunks_streams_rows_in_chunk_order(
    tmp_path: Path,
) -> None:
    reader = GenerationArtifactReader()

    reader._data_directory = tmp_path

    _write_chunk(
        root=tmp_path / "generation" / "JOB-1",
        entity_name="CUSTOMER",
        chunk_number=2,
        rows=[
            {"ID": "3"},
            {"ID": "4"},
        ],
    )

    _write_chunk(
        root=tmp_path / "generation" / "JOB-1",
        entity_name="CUSTOMER",
        chunk_number=1,
        rows=[
            {"ID": "1"},
            {"ID": "2"},
        ],
    )

    rows = list(
        reader.iter_entity_chunks(
            job_id="JOB-1",
            entity_name="CUSTOMER",
        )
    )

    assert rows == [
        {"ID": "1"},
        {"ID": "2"},
        {"ID": "3"},
        {"ID": "4"},
    ]


def test_iter_entity_chunks_returns_no_rows_when_no_chunks_exist(
    tmp_path: Path,
) -> None:
    reader = GenerationArtifactReader()

    reader._data_directory = tmp_path

    rows = list(
        reader.iter_entity_chunks(
            job_id="JOB-1",
            entity_name="CUSTOMER",
        )
    )

    assert rows == []


@pytest.mark.parametrize(
    "entity_name",
    ["", "../CUSTOMER", "CUSTOMER/OTHER", "CUSTOMER\\OTHER"],
)
def test_iter_entity_chunks_rejects_invalid_entity_name(
    tmp_path: Path,
    entity_name: str,
) -> None:
    reader = GenerationArtifactReader()

    reader._data_directory = tmp_path

    with pytest.raises(
        ValueError,
        match="Invalid entity name",
    ):
        list(
            reader.iter_entity_chunks(
                job_id="JOB-1",
                entity_name=entity_name,
            )
        )
