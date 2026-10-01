"""
File: artifact_writer.py
Purpose: Production-owned FORGE generation artifact writer.
"""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Any, Sequence


class GenerationArtifactWriter:
    """Persist generated entity data as chunked and consolidated CSV artifacts."""

    def __init__(self) -> None:
        self._data_directory = (
            Path(__file__).resolve().parents[3] / "data"
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

        chunk_paths = sorted(chunks_directory.glob("chunk_*.csv"))

        consolidated_path = (
            self._job_directory(data_model_id, job_id)
            / "generated"
            / f"{entity_name}.csv"
        )

        if not chunk_paths:
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
