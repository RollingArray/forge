"""
Production-owned FORGE generation artifact writer.

Chunk publication and consolidated-output publication are separate
transactions. The checkpoint manifest is the sole authority for visibility.
"""

from __future__ import annotations

import csv
import hashlib
import io
from pathlib import Path
from typing import Any, Sequence

from app.models.generation_persistence import (
    GenerationArtifactEvidence,
    GenerationFinalizationStatus,
)
from app.services.generation_checkpoint_store import GenerationCheckpointStore
from app.services.generation_file_persistence import (
    atomic_write_file,
    atomic_write_text,
    generation_file_lock,
)
from app.services.generation_persistence_errors import (
    ArtifactIntegrityError,
    CheckpointValidationError,
)


class GenerationArtifactWriter:
    """Publish and commit generated entity chunks and consolidated outputs."""

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
        self._checkpoint_store._checkpoint_path(data_model_id, job_id)

        job_directory = self._job_directory(data_model_id, job_id)
        job_directory.mkdir(parents=True, exist_ok=True)
        return job_directory

    @staticmethod
    def _validate_component(value: str, label: str) -> None:
        GenerationCheckpointStore._validate_path_component(value, label)

    @staticmethod
    def _validate_fieldnames(fieldnames: Sequence[str]) -> list[str]:
        names = list(fieldnames)

        if (
            not names
            or any(
                not isinstance(name, str) or not name.strip()
                for name in names
            )
            or len(names) != len(set(names))
        ):
            raise ValueError("CSV field names must be non-empty and unique.")

        return names

    @classmethod
    def _serialize_chunk(
        cls,
        rows: Sequence[dict[str, Any]],
    ) -> tuple[str, list[str]]:
        if not rows:
            raise ValueError("A committed generation chunk cannot be empty.")

        if not all(isinstance(row, dict) for row in rows):
            raise ValueError("Every generation row must be a dictionary.")

        fieldnames = cls._validate_fieldnames(list(rows[0].keys()))

        for index, row in enumerate(rows):
            if list(row.keys()) != fieldnames:
                raise ValueError(
                    f"Generation row {index} has a different field schema."
                )

        buffer = io.StringIO(newline="")
        writer = csv.DictWriter(
            buffer,
            fieldnames=fieldnames,
            extrasaction="raise",
        )
        writer.writeheader()
        writer.writerows(rows)

        return buffer.getvalue(), fieldnames

    @staticmethod
    def _evidence(
        job_directory: Path,
        artifact_path: Path,
    ) -> GenerationArtifactEvidence:
        content_hash = hashlib.sha256()
        size_bytes = 0

        try:
            with artifact_path.open("rb") as handle:
                while block := handle.read(1024 * 1024):
                    size_bytes += len(block)
                    content_hash.update(block)
        except OSError as exc:
            raise ArtifactIntegrityError(
                f"Unable to calculate artifact evidence: {artifact_path}: {exc}"
            ) from exc

        relative_path = artifact_path.relative_to(
            job_directory
        ).as_posix()

        return GenerationArtifactEvidence(
            path=relative_path,
            size_bytes=size_bytes,
            sha256=content_hash.hexdigest(),
        )

    def write_chunk(
        self,
        data_model_id: str,
        job_id: str,
        entity_name: str,
        chunk_number: int,
        rows: Sequence[dict[str, Any]],
        *,
        attempt_id: str,
        row_start: int,
    ) -> int:
        """
        Atomically publish one chunk and commit its evidence.

        row_start is the zero-based global row position of the first row.
        """
        self._validate_component(entity_name, "entity_name")

        if (
            not isinstance(chunk_number, int)
            or isinstance(chunk_number, bool)
            or chunk_number < 1
        ):
            raise ValueError("chunk_number must be a positive integer.")

        if (
            not isinstance(row_start, int)
            or isinstance(row_start, bool)
            or row_start < 0
        ):
            raise ValueError("row_start must be a non-negative integer.")

        if not isinstance(attempt_id, str) or not attempt_id:
            raise ValueError("attempt_id must be a non-empty string.")

        manifest = self._checkpoint_store.get(data_model_id, job_id)
        if manifest is None:
            raise CheckpointValidationError(
                f"Cannot publish a chunk without checkpoint for job {job_id}."
            )

        if manifest.attempt_id != attempt_id:
            raise CheckpointValidationError(
                "Generation attempt does not match the checkpoint."
            )

        entity = manifest.entities.get(entity_name)
        if entity is None:
            raise CheckpointValidationError(
                f"Unknown checkpoint entity '{entity_name}'."
            )

        expected_start = (chunk_number - 1) * manifest.chunk_size
        expected_count = min(
            manifest.chunk_size,
            entity.target_rows - expected_start,
        )

        if (
            row_start != expected_start
            or expected_count <= 0
            or len(rows) != expected_count
        ):
            raise CheckpointValidationError(
                f"Chunk {chunk_number} for {entity_name} must cover "
                f"row_start={expected_start} and row_count={expected_count}; "
                f"received row_start={row_start}, row_count={len(rows)}."
            )

        content, _ = self._serialize_chunk(rows)

        chunks_directory = (
            self._job_directory(data_model_id, job_id)
            / "generated"
            / entity_name
            / "chunks"
        )
        chunk_path = chunks_directory / f"chunk_{chunk_number:06d}.csv"
        job_directory = self._job_directory(data_model_id, job_id)

        relative_path = chunk_path.relative_to(job_directory).as_posix()
        content_bytes = content.encode("utf-8")

        expected_evidence = GenerationArtifactEvidence(
            path=relative_path,
            size_bytes=len(content_bytes),
            sha256=hashlib.sha256(content_bytes).hexdigest(),
        )

        existing = next(
            (
                chunk
                for chunk in entity.chunks
                if chunk.chunk_number == chunk_number
            ),
            None,
        )

        if existing is not None:
            if (
                existing.row_start != row_start
                or existing.row_count != len(rows)
                or existing.artifact != expected_evidence
            ):
                raise CheckpointValidationError(
                    f"Chunk {chunk_number} for {entity_name} is already "
                    "committed with different content or row positions."
                )

            self._checkpoint_store.verify_artifact(
                data_model_id=data_model_id,
                job_id=job_id,
                artifact=existing.artifact,
            )
            return len(rows)

        with generation_file_lock(chunk_path):
            # An uncommitted orphan may be safely replaced.
            # A committed chunk was rejected above and is never overwritten.
            atomic_write_text(chunk_path, content)

        self._checkpoint_store.commit_chunk(
            data_model_id=data_model_id,
            job_id=job_id,
            attempt_id=attempt_id,
            entity_name=entity_name,
            chunk_number=chunk_number,
            row_start=row_start,
            row_count=len(rows),
            artifact=expected_evidence,
        )

        return len(rows)

    def consolidate_entity(
        self,
        data_model_id: str,
        job_id: str,
        entity_name: str,
        *,
        attempt_id: str,
        fieldnames: Sequence[str] | None = None,
    ) -> int:
        """
        Publish the consolidated CSV from committed, verified chunks.

        For zero-row entities, fieldnames must be supplied from the
        entity specification so a header-only output can be published.
        """
        self._validate_component(entity_name, "entity_name")

        manifest = self._checkpoint_store.get(data_model_id, job_id)
        if manifest is None:
            raise CheckpointValidationError(
                f"Cannot consolidate {entity_name}: checkpoint is missing."
            )

        if manifest.attempt_id != attempt_id:
            raise CheckpointValidationError(
                "Generation attempt does not match the checkpoint."
            )

        entity = manifest.entities.get(entity_name)
        if entity is None:
            raise CheckpointValidationError(
                f"Unknown checkpoint entity '{entity_name}'."
            )

        finalization = entity.finalization

        if finalization.status == GenerationFinalizationStatus.COMMITTED:
            assert finalization.output is not None
            self._checkpoint_store.verify_artifact(
                data_model_id=data_model_id,
                job_id=job_id,
                artifact=finalization.output,
            )
            return entity.target_rows

        if entity.committed_rows != entity.target_rows:
            raise CheckpointValidationError(
                f"Cannot consolidate {entity_name}: "
                f"{entity.committed_rows}/{entity.target_rows} rows committed."
            )

        if not entity.chunks and entity.target_rows > 0:
            raise CheckpointValidationError(
                f"{entity_name} has a positive target but no committed chunks."
            )

        supplied_fieldnames = (
            self._validate_fieldnames(fieldnames)
            if fieldnames is not None
            else None
        )

        if not entity.chunks and supplied_fieldnames is None:
            raise ValueError(
                f"Zero-row entity {entity_name} requires specification fieldnames."
            )

        self._checkpoint_store.begin_finalization(
            data_model_id=data_model_id,
            job_id=job_id,
            attempt_id=attempt_id,
            entity_name=entity_name,
        )

        manifest = self._checkpoint_store.get(data_model_id, job_id)
        if manifest is None:
            raise CheckpointValidationError(
                f"Checkpoint disappeared while finalizing {entity_name}."
            )

        entity = manifest.entities[entity_name]
        job_directory = self._job_directory(data_model_id, job_id)

        output_path = (
            job_directory
            / "generated"
            / f"{entity_name}.csv"
        )

        selected_fieldnames = supplied_fieldnames
        total_rows = 0

        def write_consolidated(output_file) -> None:
            nonlocal selected_fieldnames, total_rows

            csv_writer = None

            for chunk in entity.chunks:
                self._checkpoint_store.verify_artifact(
                    data_model_id=data_model_id,
                    job_id=job_id,
                    artifact=chunk.artifact,
                )

                chunk_path = (
                    job_directory
                    / Path(*chunk.artifact.path.split("/"))
                )

                try:
                    with chunk_path.open(
                        "r",
                        newline="",
                        encoding="utf-8",
                    ) as chunk_file:
                        reader = csv.DictReader(chunk_file)
                        current_fieldnames = reader.fieldnames

                        if not current_fieldnames:
                            raise ArtifactIntegrityError(
                                f"Chunk {chunk.chunk_number} has no CSV header."
                            )

                        current_fieldnames = self._validate_fieldnames(
                            current_fieldnames
                        )

                        if selected_fieldnames is None:
                            selected_fieldnames = current_fieldnames
                        elif current_fieldnames != selected_fieldnames:
                            raise ValueError(
                                "Chunk schema mismatch while consolidating "
                                f"{entity_name}: {chunk_path}"
                            )

                        if csv_writer is None:
                            csv_writer = csv.DictWriter(
                                output_file,
                                fieldnames=selected_fieldnames,
                                extrasaction="raise",
                            )
                            csv_writer.writeheader()

                        chunk_rows = 0

                        for row in reader:
                            if None in row or any(
                                value is None for value in row.values()
                            ):
                                raise ArtifactIntegrityError(
                                    f"Malformed CSV row in {entity_name} "
                                    f"chunk {chunk.chunk_number}."
                                )

                            csv_writer.writerow(row)
                            chunk_rows += 1
                            total_rows += 1

                        if chunk_rows != chunk.row_count:
                            raise ArtifactIntegrityError(
                                f"CSV row count mismatch for {entity_name} "
                                f"chunk {chunk.chunk_number}: expected "
                                f"{chunk.row_count}, found {chunk_rows}."
                            )

                except ArtifactIntegrityError:
                    raise
                except (OSError, UnicodeError, csv.Error) as exc:
                    raise ArtifactIntegrityError(
                        f"Unable to consolidate {entity_name} "
                        f"chunk {chunk.chunk_number}: {exc}"
                    ) from exc

            if selected_fieldnames is None:
                raise ValueError(
                    f"Unable to determine CSV schema for {entity_name}."
                )

            if csv_writer is None:
                csv_writer = csv.DictWriter(
                    output_file,
                    fieldnames=selected_fieldnames,
                )
                csv_writer.writeheader()

            if total_rows != entity.target_rows:
                raise ArtifactIntegrityError(
                    f"Consolidated row count mismatch for {entity_name}: "
                    f"expected {entity.target_rows}, found {total_rows}."
                )

        with generation_file_lock(output_path):
            atomic_write_file(output_path, write_consolidated)

        output_evidence = self._evidence(
            job_directory,
            output_path,
        )

        self._checkpoint_store.commit_finalization(
            data_model_id=data_model_id,
            job_id=job_id,
            attempt_id=attempt_id,
            entity_name=entity_name,
            output=output_evidence,
        )

        return total_rows

    def get_entity_csv_path(
        self,
        data_model_id: str,
        job_id: str,
        entity_name: str,
    ) -> Path:
        """Return the consolidated CSV path for one generated entity."""
        self._validate_component(data_model_id, "data_model_id")
        self._validate_component(job_id, "job_id")
        self._validate_component(entity_name, "entity_name")

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
        self._validate_component(data_model_id, "data_model_id")
        self._validate_component(job_id, "job_id")

        return (
            self._data_directory
            / "data_model"
            / data_model_id
            / "generation"
            / job_id
        )
