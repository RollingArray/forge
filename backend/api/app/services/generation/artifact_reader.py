"""
File: artifact_reader.py
Purpose: Production-owned FORGE generation artifact reader.
"""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Any, Iterator


class GenerationArtifactReader:
    """Stream committed FORGE generation chunks."""

    def __init__(self) -> None:
        self._data_directory = (
            Path(__file__).resolve().parents[3] / "data"
        )

    def iter_entity_chunks(
        self,
        data_model_id: str,
        job_id: str,
        entity_name: str,
    ) -> Iterator[dict[str, Any]]:
        """Yield rows from committed entity chunks one row at a time."""

        if not entity_name or "/" in entity_name or "\\" in entity_name:
            raise ValueError("Invalid entity name.")

        chunks_directory = (
            self._job_directory(data_model_id, job_id)
            / "generated"
            / entity_name
            / "chunks"
        )

        for chunk_path in sorted(
            chunks_directory.glob("chunk_*.csv"),
        ):
            with chunk_path.open(
                "r",
                newline="",
                encoding="utf-8",
            ) as chunk_file:
                reader = csv.DictReader(chunk_file)

                if reader.fieldnames is None:
                    raise ValueError(
                        f"Chunk file has no header: {chunk_path}"
                    )

                for row in reader:
                    yield row

    def get_entity_key_space(
        self,
        data_model_id: str,
        job_id: str,
        entity_name: str,
        identity_fields: tuple[str, ...],
    ) -> set[tuple[Any, ...]]:
        """Build an entity identity key space from committed artifacts."""

        if not identity_fields:
            return set()

        key_space: set[tuple[Any, ...]] = set()

        for row in self.iter_entity_chunks(
            data_model_id,
            job_id,
            entity_name,
        ):
            key_space.add(
                tuple(
                    row[field]
                    for field in identity_fields
                )
            )

        return key_space

    def _job_directory(
        self,
        data_model_id: str,
        job_id: str,
    ) -> Path:
        """Return the root artifact directory for a generation job."""

        return (
            self._data_directory
            / "data_model"
            / data_model_id
            / "generation"
            / job_id
        )
