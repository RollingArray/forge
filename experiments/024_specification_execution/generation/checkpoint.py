"""
FORGE Generation Core
Durable checkpoint persistence for generation resume.

The checkpoint records only work that has been confirmed as completed.
It is intentionally independent of generation execution and output
commit semantics.
"""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


CHECKPOINT_SCHEMA_VERSION = 1


def utc_now() -> str:
    """Return the current UTC timestamp in ISO-8601 format."""

    return datetime.now(timezone.utc).isoformat()


def compute_specification_hash(
    specification: dict[str, Any],
) -> str:
    """
    Compute a deterministic identity for a FORGE specification.

    Dictionary ordering and insignificant JSON formatting do not affect
    the resulting hash.
    """

    payload = json.dumps(
        specification,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")

    return hashlib.sha256(payload).hexdigest()


@dataclass
class EntityCheckpoint:
    """Durable progress for one entity."""

    target_rows: int
    completed_chunks: list[int] = field(default_factory=list)

    def mark_completed(self, chunk_number: int) -> None:
        """Record a successfully completed chunk exactly once."""

        if chunk_number not in self.completed_chunks:
            self.completed_chunks.append(chunk_number)
            self.completed_chunks.sort()

    def to_dict(self) -> dict[str, Any]:
        """Return the machine-readable representation."""

        return {
            "target_rows": self.target_rows,
            "completed_chunks": list(self.completed_chunks),
        }

    @classmethod
    def from_dict(
        cls,
        data: dict[str, Any],
    ) -> "EntityCheckpoint":
        """Restore an entity checkpoint from persisted data."""

        target_rows = data.get("target_rows")
        completed_chunks = data.get("completed_chunks", [])

        if (
            not isinstance(target_rows, int)
            or isinstance(target_rows, bool)
            or target_rows < 0
        ):
            raise ValueError(
                "Checkpoint target_rows must be a non-negative integer."
            )

        if not isinstance(completed_chunks, list):
            raise ValueError(
                "Checkpoint completed_chunks must be a list."
            )

        if any(
            not isinstance(chunk, int) or isinstance(chunk, bool) or chunk < 1
            for chunk in completed_chunks
        ):
            raise ValueError(
                "Checkpoint chunk numbers must be positive integers."
            )

        return cls(
            target_rows=target_rows,
            completed_chunks=sorted(set(completed_chunks)),
        )


@dataclass
class GenerationCheckpoint:
    """Durable checkpoint for one FORGE generation job."""

    job_id: str
    specification_hash: str
    seed: int
    chunk_size: int
    entities: dict[str, EntityCheckpoint] = field(default_factory=dict)
    updated_at: str = field(default_factory=utc_now)

    def mark_chunk_completed(
        self,
        entity_name: str,
        chunk_number: int,
    ) -> None:
        """Mark one chunk as durably completed."""

        entity = self.entities.get(entity_name)

        if entity is None:
            raise ValueError(
                f"Unknown entity in checkpoint: {entity_name!r}"
            )

        if (
            not isinstance(chunk_number, int)
            or isinstance(chunk_number, bool)
            or chunk_number < 1
        ):
            raise ValueError(
                "chunk_number must be a positive integer."
            )

        entity.mark_completed(chunk_number)
        self.updated_at = utc_now()

    def is_chunk_completed(
        self,
        entity_name: str,
        chunk_number: int,
    ) -> bool:
        """Return whether a chunk has already been completed."""

        entity = self.entities.get(entity_name)

        if entity is None:
            return False

        return chunk_number in entity.completed_chunks

    def validate_identity(
        self,
        *,
        job_id: str,
        specification_hash: str,
        seed: int,
        chunk_size: int,
    ) -> None:
        """
        Validate that a checkpoint belongs to the requested generation.

        Resume is rejected if any generation identity parameter differs.
        """

        if self.job_id != job_id:
            raise ValueError(
                "Checkpoint job identity does not match the requested job."
            )

        if self.specification_hash != specification_hash:
            raise ValueError(
                "Checkpoint specification identity does not match "
                "the requested specification."
            )

        if self.seed != seed:
            raise ValueError(
                "Checkpoint seed does not match the requested generation."
            )

        if self.chunk_size != chunk_size:
            raise ValueError(
                "Checkpoint chunk size does not match the requested generation."
            )

    def to_dict(self) -> dict[str, Any]:
        """Return the complete machine-readable checkpoint."""

        return {
            "schema_version": CHECKPOINT_SCHEMA_VERSION,
            "job_id": self.job_id,
            "specification_hash": self.specification_hash,
            "seed": self.seed,
            "chunk_size": self.chunk_size,
            "entities": {
                entity_name: entity.to_dict()
                for entity_name, entity in sorted(self.entities.items())
            },
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(
        cls,
        data: dict[str, Any],
    ) -> "GenerationCheckpoint":
        """Restore a checkpoint from persisted JSON."""

        schema_version = data.get("schema_version")

        if schema_version != CHECKPOINT_SCHEMA_VERSION:
            raise ValueError(
                "Unsupported checkpoint schema version: "
                f"{schema_version!r}"
            )

        job_id = data.get("job_id")
        specification_hash = data.get("specification_hash")
        seed = data.get("seed")
        chunk_size = data.get("chunk_size")
        entities = data.get("entities", {})
        updated_at = data.get("updated_at")

        if not isinstance(job_id, str) or not job_id:
            raise ValueError(
                "Checkpoint job_id must be a non-empty string."
            )

        if (
            not isinstance(specification_hash, str)
            or not specification_hash
        ):
            raise ValueError(
                "Checkpoint specification_hash must be a non-empty string."
            )

        if not isinstance(seed, int) or isinstance(seed, bool):
            raise ValueError(
                "Checkpoint seed must be an integer."
            )

        if (
            not isinstance(chunk_size, int)
            or isinstance(chunk_size, bool)
            or chunk_size <= 0
        ):
            raise ValueError(
                "Checkpoint chunk_size must be a positive integer."
            )

        if not isinstance(entities, dict):
            raise ValueError(
                "Checkpoint entities must be an object."
            )

        if updated_at is not None and not isinstance(updated_at, str):
            raise ValueError(
                "Checkpoint updated_at must be a string."
            )

        return cls(
            job_id=job_id,
            specification_hash=specification_hash,
            seed=seed,
            chunk_size=chunk_size,
            entities={
                entity_name: EntityCheckpoint.from_dict(entity_data)
                for entity_name, entity_data in entities.items()
            },
            updated_at=updated_at or utc_now(),
        )


def create_checkpoint(
    *,
    job_id: str,
    specification: dict[str, Any],
    seed: int,
    chunk_size: int,
    entity_targets: dict[str, int],
) -> GenerationCheckpoint:
    """Create a new checkpoint for a generation job."""

    if not job_id:
        raise ValueError("job_id must be non-empty.")

    if (
        not isinstance(seed, int)
        or isinstance(seed, bool)
    ):
        raise ValueError("seed must be an integer.")

    if (
        not isinstance(chunk_size, int)
        or isinstance(chunk_size, bool)
        or chunk_size <= 0
    ):
        raise ValueError("chunk_size must be a positive integer.")

    return GenerationCheckpoint(
        job_id=job_id,
        specification_hash=compute_specification_hash(
            specification
        ),
        seed=seed,
        chunk_size=chunk_size,
        entities={
            entity_name: EntityCheckpoint(
                target_rows=target_rows,
            )
            for entity_name, target_rows in entity_targets.items()
        },
    )


def load_checkpoint(
    checkpoint_path: str | Path,
) -> GenerationCheckpoint:
    """Load and validate a persisted checkpoint."""

    path = Path(checkpoint_path)

    if not path.exists():
        raise FileNotFoundError(
            f"Checkpoint does not exist: {path}"
        )

    data = json.loads(
        path.read_text(encoding="utf-8")
    )

    if not isinstance(data, dict):
        raise ValueError(
            "Checkpoint root must be a JSON object."
        )

    return GenerationCheckpoint.from_dict(data)


def write_checkpoint(
    checkpoint: GenerationCheckpoint,
    checkpoint_path: str | Path,
) -> Path:
    """
    Atomically persist a checkpoint.

    The temporary file is created in the same directory as the target
    so os.replace() remains an atomic filesystem operation.
    """

    path = Path(checkpoint_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    payload = json.dumps(
        checkpoint.to_dict(),
        indent=2,
        sort_keys=True,
        ensure_ascii=False,
    )

    file_descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.",
        suffix=".tmp",
        dir=path.parent,
        text=True,
    )

    temporary_path = Path(temporary_name)

    try:
        with os.fdopen(
            file_descriptor,
            "w",
            encoding="utf-8",
        ) as handle:
            handle.write(payload)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())

        os.replace(
            temporary_path,
            path,
        )

        try:
            directory_fd = os.open(
                path.parent,
                os.O_RDONLY,
            )
            try:
                os.fsync(directory_fd)
            finally:
                os.close(directory_fd)
        except OSError:
            # Some filesystems do not permit fsync on directories.
            # The file itself has already been flushed and atomically
            # replaced, so preserve the committed checkpoint.
            pass

    except Exception:
        try:
            temporary_path.unlink(missing_ok=True)
        finally:
            raise

    return path
