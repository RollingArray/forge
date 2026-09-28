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

    def initialize_job(self, job_id: str) -> Path:
        """Create and return the generated-artifact directory for a job."""
        job_directory = self._job_directory(job_id)
        job_directory.mkdir(parents=True, exist_ok=True)
        return job_directory

    def write_entity(
        self,
        job_id: str,
        entity_name: str,
        rows: Sequence[dict[str, Any]],
        chunk_size: int = 50,
    ) -> int:
        """Write an entity's rows as chunks and a consolidated CSV file."""
        if chunk_size <= 0:
            raise ValueError("chunk_size must be greater than zero.")

        entity_directory = (
            self._job_directory(job_id)
            / "generated"
            / entity_name
        )
        chunks_directory = entity_directory / "chunks"

        chunks_directory.mkdir(
            parents=True,
            exist_ok=True,
        )

        if not rows:
            return 0

        fieldnames = list(rows[0].keys())

        for chunk_number, start in enumerate(
            range(0, len(rows), chunk_size),
            start=1,
        ):
            chunk_rows = rows[start : start + chunk_size]

            chunk_path = (
                chunks_directory
                / f"chunk_{chunk_number:06d}.csv"
            )

            self._write_csv(
                chunk_path,
                fieldnames,
                chunk_rows,
            )

        consolidated_path = (
            self._job_directory(job_id)
            / "generated"
            / f"{entity_name}.csv"
        )

        self._write_csv(
            consolidated_path,
            fieldnames,
            rows,
        )

        return len(rows)

    def write_chunk(
        self,
        job_id: str,
        entity_name: str,
        chunk_number: int,
        rows: Sequence[dict[str, Any]],
    ) -> int:
        """Persist one completed generation chunk immediately."""
        if not rows:
            return 0

        chunks_directory = (
            self._job_directory(job_id)
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

    def _job_directory(self, job_id: str) -> Path:
        """Return the root artifact directory for a generation job."""
        return self._data_directory / "generation" / job_id

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
