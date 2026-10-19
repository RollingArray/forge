"""
File: artifact_writer.py
Purpose: Production-owned FORGE generation artifact writer.
"""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Any, Sequence

from app.services.generation_checkpoint_store import GenerationCheckpointStore


class GenerationArtifactWriter:
    """Persist generated entity data as chunked and consolidated CSV artifacts."""

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

    def initialize_job(
        self,
        data_model_id: str,
        job_id: str,
    ) -> Path:
        """Create and return the generated-artifact directory for a job."""
        job_directory = self._job_directory(data_model_id, job_id)
        job_directory.mkdir(parents=True, exist_ok=True)
        return job_directory

    def write_chunk(
        self,
        data_model_id: str,
        job_id: str,
        entity_name: str,
        chunk_number: int,
        rows: Sequence[dict[str, Any]],
    ) -> int:
        """Persist one completed generation chunk immediately."""
        if not rows:
            return 0

        chunks_directory = (
            self._job_directory(data_model_id, job_id)
            / "generated"
            / entity_name
            / "chunks"
        )

        chunks_directory.mkdir(
            parents=True,
            exist_ok=True,
        )

        fieldnames = list(rows[0].keys())

        chunk_path = (
            chunks_directory
            / f"chunk_{chunk_number:06d}.csv"
        )

        self._write_csv(
            chunk_path,
            fieldnames,
            rows,
        )

        return len(rows)

    def consolidate_entity(
        self,
        data_model_id: str,
        job_id: str,
        entity_name: str,
    ) -> int:
        """Build the consolidated entity CSV by streaming committed chunks."""
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
                f"Cannot consolidate {entity_name}: generation checkpoint "
                f"is missing for job {job_id}."
            )

        entities = checkpoint.get("entities")
        if not isinstance(entities, dict):
            raise ValueError(
                f"Invalid checkpoint entities for job {job_id}."
            )

        entity_checkpoint = entities.get(entity_name, {})
        if not isinstance(entity_checkpoint, dict):
            raise ValueError(
                f"Invalid checkpoint state for entity {entity_name}."
            )

        completed_chunks = entity_checkpoint.get("completed_chunks", [])
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
        chunk_paths = []
        for chunk_path in chunks_directory.glob("chunk_*.csv"):
            suffix = chunk_path.stem.removeprefix("chunk_")
            if suffix.isdigit() and int(suffix) in committed_chunk_numbers:
                chunk_paths.append(chunk_path)
        chunk_paths.sort()

        consolidated_path = (
            self._job_directory(data_model_id, job_id)
            / "generated"
            / f"{entity_name}.csv"
        )

        if not chunk_paths:
            consolidated_path.unlink(missing_ok=True)
            return 0

        total_rows = 0
        fieldnames: list[str] | None = None

        consolidated_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        with consolidated_path.open(
            "w",
            newline="",
            encoding="utf-8",
        ) as output_file:
            writer: csv.DictWriter | None = None

            for chunk_path in chunk_paths:
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

                    if fieldnames is None:
                        fieldnames = list(reader.fieldnames)

                        writer = csv.DictWriter(
                            output_file,
                            fieldnames=fieldnames,
                        )
                        writer.writeheader()
                    elif list(reader.fieldnames) != fieldnames:
                        raise ValueError(
                            "Chunk schema mismatch while consolidating "
                            f"{entity_name}: {chunk_path}"
                        )

                    for row in reader:
                        writer.writerow(row)
                        total_rows += 1

        return total_rows

    def get_entity_csv_path(
        self,
        data_model_id: str,
        job_id: str,
        entity_name: str,
    ) -> Path:
        """Return the consolidated CSV path for one generated entity."""
        if not entity_name or "/" in entity_name or "\\" in entity_name:
            raise ValueError("Invalid entity name.")

        return (
            self._job_directory(data_model_id, job_id)
            / "generated"
            / f"{entity_name}.csv"
        )

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

    @staticmethod
    def _write_csv(
        path: Path,
        fieldnames: list[str],
        rows: Sequence[dict[str, Any]],
    ) -> None:
        """Write rows to a CSV file."""
        path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        with path.open(
            "w",
            newline="",
            encoding="utf-8",
        ) as file:
            writer = csv.DictWriter(
                file,
                fieldnames=fieldnames,
            )

            writer.writeheader()
            writer.writerows(rows)
