"""Strict, transactional v2 persistence for FORGE generation checkpoints."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from app.models.generation_persistence import (
    GenerationArtifactEvidence,
    GenerationCheckpointManifest,
    GenerationChunkEvidence,
    GenerationEntityCheckpoint,
    GenerationFinalization,
    GenerationFinalizationStatus,
)
from app.services.generation_file_persistence import (
    atomic_write_text,
    generation_file_lock,
)
from app.services.generation_persistence_errors import (
    ArtifactIntegrityError,
    CheckpointCorruptError,
    CheckpointIdentityMismatchError,
    CheckpointValidationError,
    PersistenceOperationError,
)


CHECKPOINT_SCHEMA_VERSION = 2


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def compute_specification_hash(
    specification: dict[str, Any],
) -> str:
    """Compute the deterministic identity of a FORGE specification."""

    payload = json.dumps(
        specification,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")

    return hashlib.sha256(payload).hexdigest()


class GenerationCheckpointStore:
    """Own all authoritative generation checkpoint state transitions."""

    def __init__(self) -> None:
        self._root = (
            Path(__file__).resolve().parents[2]
            / "data"
            / "data_model"
        )

    @staticmethod
    def _validate_path_component(value: str, label: str) -> None:
        if (
            not isinstance(value, str)
            or not value
            or value in {".", ".."}
            or "/" in value
            or "\\" in value
            or any(ord(character) < 32 for character in value)
            or any(character in '<>:"|?*' for character in value)
            or value.endswith((" ", "."))
        ):
            raise ValueError(f"Invalid {label} path component.")

        windows_reserved_names = {
            "CON", "PRN", "AUX", "NUL",
            *(f"COM{i}" for i in range(1, 10)),
            *(f"LPT{i}" for i in range(1, 10)),
        }

        reserved_basename = value.split(".", 1)[0].upper()
        if reserved_basename in windows_reserved_names:
            raise ValueError(
                f"Invalid {label}: reserved Windows path component."
            )

    def _checkpoint_path(
        self,
        data_model_id: str,
        job_id: str,
    ) -> Path:
        self._validate_path_component(data_model_id, "data_model_id")
        self._validate_path_component(job_id, "job_id")

        return (
            self._root
            / data_model_id
            / "generation"
            / job_id
            / "checkpoint.json"
        )

    def _job_directory(
        self,
        data_model_id: str,
        job_id: str,
    ) -> Path:
        return self._checkpoint_path(
            data_model_id,
            job_id,
        ).parent

    def initialize(
        self,
        *,
        data_model_id: str,
        job_id: str,
        specification: dict[str, Any],
        seed: int,
        chunk_size: int,
        algorithm_version: str,
        attempt_id: str,
        entity_targets: dict[str, int],
    ) -> GenerationCheckpointManifest:
        """Create a new checkpoint without overwriting existing state."""

        path = self._checkpoint_path(data_model_id, job_id)

        now = utc_now()

        try:
            manifest = GenerationCheckpointManifest(
                schema_version=CHECKPOINT_SCHEMA_VERSION,
                data_model_id=data_model_id,
                job_id=job_id,
                specification_hash=compute_specification_hash(
                    specification
                ),
                seed=seed,
                chunk_size=chunk_size,
                algorithm_version=algorithm_version,
                attempt_id=attempt_id,
                entities={
                    name: GenerationEntityCheckpoint(
                        target_rows=target_rows,
                    )
                    for name, target_rows in sorted(
                        entity_targets.items()
                    )
                },
                created_at=now,
                updated_at=now,
            )
        except ValidationError as exc:
            raise CheckpointValidationError(
                f"Initial checkpoint is invalid: {exc}"
            ) from exc

        path.parent.mkdir(parents=True, exist_ok=True)

        with generation_file_lock(path):
            if path.exists():
                raise FileExistsError(
                    f"Checkpoint already exists for job '{job_id}'."
                )

            self._write_locked(path, manifest)

        return manifest

    def get(
        self,
        data_model_id: str,
        job_id: str,
    ) -> GenerationCheckpointManifest | None:
        """Read and strictly validate the persisted manifest.

        None means only that the checkpoint file does not exist.
        Corrupt or inaccessible files are never treated as missing.
        """

        path = self._checkpoint_path(data_model_id, job_id)

        with generation_file_lock(path):
            manifest = self._read_locked(path)

        if manifest is None:
            return None

        if (
            manifest.data_model_id != data_model_id
            or manifest.job_id != job_id
        ):
            raise CheckpointIdentityMismatchError(
                "Checkpoint identity does not match its requested location."
            )

        return manifest

    @staticmethod
    def _read_locked(
        path: Path,
    ) -> GenerationCheckpointManifest | None:
        try:
            content = path.read_text(encoding="utf-8")
        except FileNotFoundError:
            return None
        except OSError as exc:
            raise PersistenceOperationError(
                f"Unable to read checkpoint '{path}': {exc}"
            ) from exc

        try:
            payload = json.loads(content)
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            raise CheckpointCorruptError(
                f"Checkpoint contains invalid JSON: '{path}'."
            ) from exc

        if not isinstance(payload, dict):
            raise CheckpointCorruptError(
                f"Checkpoint root must be a JSON object: '{path}'."
            )

        try:
            return GenerationCheckpointManifest.model_validate(payload)
        except ValidationError as exc:
            raise CheckpointValidationError(
                f"Checkpoint violates the v2 persistence contract: '{path}': {exc}"
            ) from exc

    @staticmethod
    def _write_locked(
        path: Path,
        manifest: GenerationCheckpointManifest,
    ) -> None:
        try:
            payload = json.dumps(
                manifest.model_dump(mode="json"),
                indent=2,
                sort_keys=True,
                ensure_ascii=False,
            )
            atomic_write_text(path, payload + "\n")
        except OSError as exc:
            raise PersistenceOperationError(
                f"Unable to persist checkpoint '{path}': {exc}"
            ) from exc

    @staticmethod
    def _updated_manifest(
        manifest: GenerationCheckpointManifest,
        *,
        entities: dict[str, GenerationEntityCheckpoint],
        attempt_id: str | None = None,
    ) -> GenerationCheckpointManifest:
        now = max(utc_now(), manifest.updated_at)

        try:
            payload = {
                **manifest.model_dump(mode="python"),
                "entities": entities,
                "updated_at": now,
            }
            if attempt_id is not None:
                payload["attempt_id"] = attempt_id

            return GenerationCheckpointManifest.model_validate(payload)
        except ValidationError as exc:
            raise CheckpointValidationError(
                f"Checkpoint transition violates the v2 contract: {exc}"
            ) from exc

    def verify_artifact(
        self,
        *,
        data_model_id: str,
        job_id: str,
        artifact: GenerationArtifactEvidence,
    ) -> None:
        """Verify published artifact bytes against committed evidence."""
        self._verify_artifact(
            data_model_id=data_model_id,
            job_id=job_id,
            artifact=artifact,
        )

    def _verify_artifact(
        self,
        *,
        data_model_id: str,
        job_id: str,
        artifact: GenerationArtifactEvidence,
    ) -> None:
        """Verify evidence against the published file under this job."""

        job_directory = self._job_directory(data_model_id, job_id)
        candidate = job_directory.joinpath(*artifact.path.split("/"))

        try:
            resolved_root = job_directory.resolve(strict=True)
            resolved_file = candidate.resolve(strict=True)
            resolved_file.relative_to(resolved_root)
        except FileNotFoundError as exc:
            raise ArtifactIntegrityError(
                f"Published artifact is missing: '{artifact.path}'."
            ) from exc
        except (OSError, ValueError) as exc:
            raise ArtifactIntegrityError(
                f"Artifact path is invalid or outside the job directory: "
                f"'{artifact.path}'."
            ) from exc

        if not resolved_file.is_file():
            raise ArtifactIntegrityError(
                f"Artifact is not a regular file: '{artifact.path}'."
            )

        digest = hashlib.sha256()
        size_bytes = 0

        try:
            with resolved_file.open("rb") as handle:
                while block := handle.read(1024 * 1024):
                    size_bytes += len(block)
                    digest.update(block)
        except OSError as exc:
            raise ArtifactIntegrityError(
                f"Unable to verify artifact '{artifact.path}': {exc}"
            ) from exc

        if size_bytes != artifact.size_bytes:
            raise ArtifactIntegrityError(
                f"Artifact size mismatch for '{artifact.path}': "
                f"expected {artifact.size_bytes}, found {size_bytes}."
            )

        if digest.hexdigest() != artifact.sha256:
            raise ArtifactIntegrityError(
                f"Artifact SHA-256 mismatch for '{artifact.path}'."
            )

    def commit_chunk(
        self,
        *,
        data_model_id: str,
        job_id: str,
        attempt_id: str,
        entity_name: str,
        chunk_number: int,
        row_start: int,
        row_count: int,
        artifact: GenerationArtifactEvidence,
    ) -> GenerationCheckpointManifest:
        """Commit verified chunk evidence transactionally and idempotently."""

        path = self._checkpoint_path(data_model_id, job_id)

        with generation_file_lock(path):
            manifest = self._read_locked(path)

            if manifest is None:
                raise CheckpointValidationError(
                    f"Cannot commit a chunk without a checkpoint for '{job_id}'."
                )

            if (
                manifest.data_model_id != data_model_id
                or manifest.job_id != job_id
                or manifest.attempt_id != attempt_id
            ):
                raise CheckpointIdentityMismatchError(
                    "Checkpoint identity or generation attempt does not "
                    "match the requested operation."
                )

            entity = manifest.entities.get(entity_name)
            if entity is None:
                raise CheckpointValidationError(
                    f"Unknown checkpoint entity '{entity_name}'."
                )

            self._verify_artifact(
                data_model_id=data_model_id,
                job_id=job_id,
                artifact=artifact,
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
                same_evidence = (
                    existing.row_start == row_start
                    and existing.row_count == row_count
                    and existing.artifact == artifact
                )

                if same_evidence:
                    return manifest

                raise CheckpointValidationError(
                    f"Chunk {chunk_number} for entity '{entity_name}' "
                    "is already committed with different evidence."
                )

            if entity.finalization.status != GenerationFinalizationStatus.PENDING:
                raise CheckpointValidationError(
                    f"Cannot commit a new chunk for '{entity_name}' "
                    "after finalization has started."
                )

            try:
                chunk = GenerationChunkEvidence(
                    chunk_number=chunk_number,
                    row_start=row_start,
                    row_count=row_count,
                    artifact=artifact,
                    committed_at=utc_now(),
                )

                updated_entity = GenerationEntityCheckpoint(
                    target_rows=entity.target_rows,
                    chunks=sorted(
                        [*entity.chunks, chunk],
                        key=lambda item: item.chunk_number,
                    ),
                    finalization=entity.finalization,
                )
            except ValidationError as exc:
                raise CheckpointValidationError(
                    f"Invalid chunk commit for '{entity_name}': {exc}"
                ) from exc

            entities = dict(manifest.entities)
            entities[entity_name] = updated_entity

            updated = self._updated_manifest(
                manifest,
                entities=entities,
            )
            self._write_locked(path, updated)

            return updated

    def get_entity_state(
        self,
        *,
        data_model_id: str,
        job_id: str,
        entity_name: str,
    ) -> GenerationEntityCheckpoint:
        manifest = self.get(data_model_id, job_id)

        if manifest is None:
            raise CheckpointValidationError(
                f"Checkpoint does not exist for job '{job_id}'."
            )

        entity = manifest.entities.get(entity_name)
        if entity is None:
            raise CheckpointValidationError(
                f"Unknown checkpoint entity '{entity_name}'."
            )

        return entity

    def get_committed_rows(
        self,
        *,
        data_model_id: str,
        job_id: str,
        entity_name: str,
    ) -> int:
        manifest = self.get(data_model_id, job_id)

        if manifest is None:
            return 0

        entity = manifest.entities.get(entity_name)
        if entity is None:
            raise CheckpointValidationError(
                f"Unknown checkpoint entity '{entity_name}'."
            )

        return entity.committed_rows

    def is_chunk_committed(
        self,
        *,
        data_model_id: str,
        job_id: str,
        entity_name: str,
        chunk_number: int,
    ) -> bool:
        if (
            not isinstance(chunk_number, int)
            or isinstance(chunk_number, bool)
            or chunk_number < 1
        ):
            raise ValueError("chunk_number must be a positive integer.")

        manifest = self.get(data_model_id, job_id)

        if manifest is None:
            return False

        entity = manifest.entities.get(entity_name)
        if entity is None:
            return False

        return any(
            chunk.chunk_number == chunk_number
            for chunk in entity.chunks
        )

    def supersede_attempt(
        self,
        *,
        data_model_id: str,
        job_id: str,
        expected_attempt_id: str,
        new_attempt_id: str,
    ) -> GenerationCheckpointManifest:
        """Atomically move a checkpoint to a new execution attempt.

        The caller must hold the job's OS-managed execution lease.
        Committed chunk and finalization evidence remain immutable.
        Only an IN_PROGRESS finalization is reset to PENDING.
        """

        if (
            not isinstance(expected_attempt_id, str)
            or not expected_attempt_id.strip()
        ):
            raise ValueError("expected_attempt_id must be a non-empty string.")

        if (
            not isinstance(new_attempt_id, str)
            or not new_attempt_id.strip()
        ):
            raise ValueError("new_attempt_id must be a non-empty string.")

        if new_attempt_id == expected_attempt_id:
            raise CheckpointValidationError(
                "A superseding attempt must have a different attempt ID."
            )

        path = self._checkpoint_path(data_model_id, job_id)

        with generation_file_lock(path):
            manifest = self._read_locked(path)

            if manifest is None:
                raise CheckpointValidationError(
                    f"Checkpoint does not exist for job '{job_id}'."
                )

            if (
                manifest.data_model_id != data_model_id
                or manifest.job_id != job_id
                or manifest.attempt_id != expected_attempt_id
            ):
                raise CheckpointIdentityMismatchError(
                    "Checkpoint identity or expected generation attempt "
                    "does not match the supersede request."
                )

            entities: dict[str, GenerationEntityCheckpoint] = {}

            for entity_name, entity in manifest.entities.items():
                finalization = entity.finalization

                if (
                    finalization.status
                    == GenerationFinalizationStatus.IN_PROGRESS
                ):
                    finalization = GenerationFinalization(
                        status=GenerationFinalizationStatus.PENDING,
                    )

                entities[entity_name] = GenerationEntityCheckpoint(
                    target_rows=entity.target_rows,
                    chunks=entity.chunks,
                    finalization=finalization,
                )

            updated = self._updated_manifest(
                manifest,
                entities=entities,
                attempt_id=new_attempt_id,
            )

            self._write_locked(path, updated)
            return updated

    def validate_identity(
        self,
        *,
        data_model_id: str,
        job_id: str,
        specification_hash: str,
        seed: int,
        chunk_size: int,
        algorithm_version: str,
        attempt_id: str,
    ) -> None:
        """Validate every immutable generation identity component."""

        manifest = self.get(data_model_id, job_id)

        if manifest is None:
            raise CheckpointValidationError(
                f"Checkpoint does not exist for job '{job_id}'."
            )

        expected = {
            "data_model_id": data_model_id,
            "job_id": job_id,
            "specification_hash": specification_hash.lower(),
            "seed": seed,
            "chunk_size": chunk_size,
            "algorithm_version": algorithm_version,
            "attempt_id": attempt_id,
        }

        actual = {
            "data_model_id": manifest.data_model_id,
            "job_id": manifest.job_id,
            "specification_hash": manifest.specification_hash,
            "seed": manifest.seed,
            "chunk_size": manifest.chunk_size,
            "algorithm_version": manifest.algorithm_version,
            "attempt_id": manifest.attempt_id,
        }

        mismatches = [
            key
            for key, value in expected.items()
            if actual[key] != value
        ]

        if mismatches:
            raise CheckpointIdentityMismatchError(
                "Checkpoint identity mismatch in: "
                + ", ".join(mismatches)
            )

    def begin_finalization(
        self,
        *,
        data_model_id: str,
        job_id: str,
        attempt_id: str,
        entity_name: str,
    ) -> GenerationCheckpointManifest:
        """Begin finalization only after all target rows are committed."""

        path = self._checkpoint_path(data_model_id, job_id)

        with generation_file_lock(path):
            manifest = self._read_locked(path)

            if manifest is None:
                raise CheckpointValidationError(
                    f"Checkpoint does not exist for job '{job_id}'."
                )

            if (
                manifest.data_model_id != data_model_id
                or manifest.job_id != job_id
                or manifest.attempt_id != attempt_id
            ):
                raise CheckpointIdentityMismatchError(
                    "Checkpoint identity or generation attempt does not "
                    "match the requested operation."
                )

            entity = manifest.entities.get(entity_name)
            if entity is None:
                raise CheckpointValidationError(
                    f"Unknown checkpoint entity '{entity_name}'."
                )

            status = entity.finalization.status

            if status == GenerationFinalizationStatus.COMMITTED:
                return manifest

            if status == GenerationFinalizationStatus.IN_PROGRESS:
                return manifest

            if entity.committed_rows != entity.target_rows:
                raise CheckpointValidationError(
                    f"Cannot finalize '{entity_name}': "
                    f"{entity.committed_rows}/{entity.target_rows} rows committed."
                )

            updated_entity = GenerationEntityCheckpoint(
                target_rows=entity.target_rows,
                chunks=entity.chunks,
                finalization=GenerationFinalization(
                    status=GenerationFinalizationStatus.IN_PROGRESS,
                ),
            )

            entities = dict(manifest.entities)
            entities[entity_name] = updated_entity

            updated = self._updated_manifest(
                manifest,
                entities=entities,
            )
            self._write_locked(path, updated)

            return updated

    def commit_finalization(
        self,
        *,
        data_model_id: str,
        job_id: str,
        attempt_id: str,
        entity_name: str,
        output: GenerationArtifactEvidence,
    ) -> GenerationCheckpointManifest:
        """Commit verified consolidated-output evidence."""

        path = self._checkpoint_path(data_model_id, job_id)

        with generation_file_lock(path):
            manifest = self._read_locked(path)

            if manifest is None:
                raise CheckpointValidationError(
                    f"Checkpoint does not exist for job '{job_id}'."
                )

            if (
                manifest.data_model_id != data_model_id
                or manifest.job_id != job_id
                or manifest.attempt_id != attempt_id
            ):
                raise CheckpointIdentityMismatchError(
                    "Checkpoint identity or generation attempt does not "
                    "match the requested operation."
                )

            entity = manifest.entities.get(entity_name)
            if entity is None:
                raise CheckpointValidationError(
                    f"Unknown checkpoint entity '{entity_name}'."
                )

            current = entity.finalization

            if current.status == GenerationFinalizationStatus.COMMITTED:
                if current.output == output:
                    self._verify_artifact(
                        data_model_id=data_model_id,
                        job_id=job_id,
                        artifact=output,
                    )
                    return manifest

                raise CheckpointValidationError(
                    f"Finalization for '{entity_name}' is already committed "
                    "with different evidence."
                )

            if current.status != GenerationFinalizationStatus.IN_PROGRESS:
                raise CheckpointValidationError(
                    f"Finalization for '{entity_name}' has not begun."
                )

            if entity.committed_rows != entity.target_rows:
                raise CheckpointValidationError(
                    f"Cannot commit finalization for '{entity_name}': "
                    "target rows are not fully committed."
                )

            self._verify_artifact(
                data_model_id=data_model_id,
                job_id=job_id,
                artifact=output,
            )

            updated_entity = GenerationEntityCheckpoint(
                target_rows=entity.target_rows,
                chunks=entity.chunks,
                finalization=GenerationFinalization(
                    status=GenerationFinalizationStatus.COMMITTED,
                    output=output,
                ),
            )

            entities = dict(manifest.entities)
            entities[entity_name] = updated_entity

            updated = self._updated_manifest(
                manifest,
                entities=entities,
            )
            self._write_locked(path, updated)

            return updated
