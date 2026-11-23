"""Read only committed, integrity-verified FORGE generation artifacts."""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Any, Iterator

from app.models.generation_persistence import GenerationChunkEvidence
from app.services.generation_checkpoint_store import GenerationCheckpointStore
from app.services.generation_persistence_errors import (
    ArtifactIntegrityError,
    CheckpointValidationError,
)


class GenerationArtifactReader:
    """Stream committed generation artifacts using the v2 manifest."""

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

    def _job_directory(
        self,
        data_model_id: str,
        job_id: str,
    ) -> Path:
        return (
            self._data_directory
            / "data_model"
            / data_model_id
            / "generation"
            / job_id
        )

    @staticmethod
    def _validate_entity_name(entity_name: str) -> None:
        if (
            not isinstance(entity_name, str)
            or not entity_name
            or entity_name in {".", ".."}
            or "/" in entity_name
            or "\\" in entity_name
        ):
            raise ValueError("Invalid entity name.")

    def _get_entity_chunks(
        self,
        *,
        data_model_id: str,
        job_id: str,
        entity_name: str,
    ) -> tuple[Path, list[GenerationChunkEvidence]]:
        self._validate_entity_name(entity_name)

        manifest = self._checkpoint_store.get(
            data_model_id=data_model_id,
            job_id=job_id,
        )
        if manifest is None:
            raise CheckpointValidationError(
                f"Cannot read committed artifacts: checkpoint is missing "
                f"for job {job_id}."
            )

        entity = manifest.entities.get(entity_name)
        if entity is None:
            raise CheckpointValidationError(
                f"Missing checkpoint for entity {entity_name}."
            )

        return (
            self._job_directory(data_model_id, job_id),
            list(entity.chunks),
        )

    @staticmethod
    def _artifact_path(
        job_directory: Path,
        chunk: GenerationChunkEvidence,
    ) -> Path:
        return job_directory.joinpath(*chunk.artifact.path.split("/"))

    def _validate_chunk_csv(
        self,
        *,
        path: Path,
        chunk: GenerationChunkEvidence,
        entity_name: str,
    ) -> None:
        """Validate the complete CSV before exposing any of its rows."""

        row_count = 0

        try:
            with path.open(
                "r",
                newline="",
                encoding="utf-8",
            ) as handle:
                reader = csv.DictReader(handle)
                fieldnames = reader.fieldnames

                if (
                    not fieldnames
                    or any(
                        not isinstance(name, str) or not name.strip()
                        for name in fieldnames
                    )
                    or len(fieldnames) != len(set(fieldnames))
                ):
                    raise ArtifactIntegrityError(
                        f"Invalid CSV header for {entity_name} "
                        f"chunk {chunk.chunk_number}."
                    )

                for row in reader:
                    if None in row or any(
                        value is None for value in row.values()
                    ):
                        raise ArtifactIntegrityError(
                            f"Malformed CSV row in {entity_name} "
                            f"chunk {chunk.chunk_number}."
                        )

                    row_count += 1

        except ArtifactIntegrityError:
            raise
        except (OSError, UnicodeError, csv.Error) as exc:
            raise ArtifactIntegrityError(
                f"Unable to parse {entity_name} chunk "
                f"{chunk.chunk_number}: {exc}"
            ) from exc

        if row_count != chunk.row_count:
            raise ArtifactIntegrityError(
                f"CSV row count mismatch for {entity_name} "
                f"chunk {chunk.chunk_number}: expected "
                f"{chunk.row_count}, found {row_count}."
            )

    def iter_entity_rows(
        self,
        *,
        data_model_id: str,
        job_id: str,
        entity_name: str,
    ) -> Iterator[tuple[int, dict[str, Any]]]:
        """Yield (zero-based global row index, row) from committed chunks.

        Chunk positions are taken from the manifest. Sparse chunk layouts
        therefore retain their original global row positions.
        """

        job_directory, chunks = self._get_entity_chunks(
            data_model_id=data_model_id,
            job_id=job_id,
            entity_name=entity_name,
        )

        for chunk in chunks:
            self._checkpoint_store.verify_artifact(
                data_model_id=data_model_id,
                job_id=job_id,
                artifact=chunk.artifact,
            )

            path = self._artifact_path(job_directory, chunk)

            # Validate the complete CSV before yielding any row from it.
            self._validate_chunk_csv(
                path=path,
                chunk=chunk,
                entity_name=entity_name,
            )

            try:
                with path.open(
                    "r",
                    newline="",
                    encoding="utf-8",
                ) as handle:
                    reader = csv.DictReader(handle)

                    for local_index, row in enumerate(reader):
                        yield chunk.row_start + local_index, row

            except (OSError, UnicodeError, csv.Error) as exc:
                raise ArtifactIntegrityError(
                    f"Unable to read {entity_name} chunk "
                    f"{chunk.chunk_number}: {exc}"
                ) from exc

    def iter_entity_chunks(
        self,
        data_model_id: str,
        job_id: str,
        entity_name: str,
    ) -> Iterator[dict[str, Any]]:
        """Compatibility iterator yielding rows without their positions."""

        for _, row in self.iter_entity_rows(
            data_model_id=data_model_id,
            job_id=job_id,
            entity_name=entity_name,
        ):
            yield row

    def get_identity_keys_by_row(
        self,
        *,
        data_model_id: str,
        job_id: str,
        entity_name: str,
        identity_fields: tuple[str, ...],
    ) -> dict[int, tuple[Any, ...]]:
        """Return identity keys indexed by their original global row positions."""

        if not identity_fields:
            return {}

        key_space: dict[int, tuple[Any, ...]] = {}
        seen_keys: dict[tuple[Any, ...], int] = {}

        for row_index, row in self.iter_entity_rows(
            data_model_id=data_model_id,
            job_id=job_id,
            entity_name=entity_name,
        ):
            missing_fields = [
                field for field in identity_fields if field not in row
            ]
            if missing_fields:
                raise ArtifactIntegrityError(
                    f"Committed artifact for {entity_name} is missing "
                    f"identity field(s): {missing_fields}."
                )

            key = tuple(row[field] for field in identity_fields)

            if key in seen_keys:
                raise ArtifactIntegrityError(
                    f"Duplicate identity key in {entity_name} at global "
                    f"rows {seen_keys[key]} and {row_index}."
                )

            seen_keys[key] = row_index
            key_space[row_index] = key

        return key_space

    def get_entity_key_space(
        self,
        data_model_id: str,
        job_id: str,
        entity_name: str,
        identity_fields: tuple[str, ...],
    ) -> set[tuple[Any, ...]]:
        """Build a set of identity keys from committed artifacts."""

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
        """Return identity keys ordered by global row position.

        This compatibility API intentionally returns a compact list.
        Call get_identity_keys_by_row() when global positions matter.
        """

        indexed = self.get_identity_keys_by_row(
            data_model_id=data_model_id,
            job_id=job_id,
            entity_name=entity_name,
            identity_fields=identity_fields,
        )

        return [indexed[index] for index in sorted(indexed)]
