"""
File: artifact_reader.py
Purpose: Production-owned FORGE generation artifact reader.
"""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Any, Iterator

from ..generation_checkpoint_store import GenerationCheckpointStore


class GenerationArtifactReader:
    """Stream committed FORGE generation chunks."""

    def __init__(
        self,
        checkpoint_store: GenerationCheckpointStore | None = None,
    ) -> None:
        self._data_directory = (
            Path(__file__).resolve().parents[3] / "data"
        )
        self._checkpoint_store = (
            checkpoint_store
            if checkpoint_store is not None
            else GenerationCheckpointStore()
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

        checkpoint = self._checkpoint_store.get(
            data_model_id=data_model_id,
            job_id=job_id,
        )
        if checkpoint is None:
            raise ValueError(
                f"Cannot read committed chunks: checkpoint is missing "
                f"for job {job_id}."
            )

        entities = checkpoint.get("entities")
        if not isinstance(entities, dict):
            raise ValueError(
                f"Invalid checkpoint entities for job {job_id}."
            )

        entity_checkpoint = entities.get(entity_name)
        if not isinstance(entity_checkpoint, dict):
            raise ValueError(
                f"Missing or invalid checkpoint for entity {entity_name}."
            )

        completed_chunks = entity_checkpoint.get("completed_chunks")
        if (
            not isinstance(completed_chunks, list)
            or any(
                isinstance(number, bool)
                or not isinstance(number, int)
                or number < 1
                for number in completed_chunks
            )
            or len(completed_chunks) != len(set(completed_chunks))
        ):
            raise ValueError(
                f"Invalid committed chunk list for entity {entity_name}."
            )

        committed_chunk_numbers = set(completed_chunks)
        chunk_paths_by_number: dict[int, Path] = {}

        for chunk_path in chunks_directory.glob("chunk_*.csv"):
            suffix = chunk_path.stem.removeprefix("chunk_")
            if suffix.isdigit():
                number = int(suffix)
                if number in committed_chunk_numbers:
                    chunk_paths_by_number[number] = chunk_path

        missing_chunks = committed_chunk_numbers - set(
            chunk_paths_by_number
        )
        if missing_chunks:
            raise ValueError(
                f"Committed chunk files are missing for entity "
                f"{entity_name}: {sorted(missing_chunks)}."
            )

        for chunk_path in (
            chunk_paths_by_number[number]
            for number in sorted(committed_chunk_numbers)
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

        return set(
            self.get_ordered_entity_key_space(
                data_model_id=data_model_id,
                job_id=job_id,
                entity_name=entity_name,
                identity_fields=identity_fields,
            )
        )

    def get_ordered_entity_key_space(
        self,
        data_model_id: str,
        job_id: str,
        entity_name: str,
        identity_fields: tuple[str, ...],
    ) -> list[tuple[Any, ...]]:
        """Build a deduplicated, ordered identity key space from committed artifacts."""

        if not identity_fields:
            return []

        key_space: list[tuple[Any, ...]] = []
        seen_keys: set[tuple[Any, ...]] = set()

        for row in self.iter_entity_chunks(
            data_model_id,
            job_id,
            entity_name,
        ):
            key = tuple(
                row[field]
                for field in identity_fields
            )
            if key not in seen_keys:
                seen_keys.add(key)
                key_space.append(key)

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
