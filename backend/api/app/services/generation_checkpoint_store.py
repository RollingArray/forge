"""
File: generation_checkpoint_store.py
Purpose: Persist durable FORGE generation checkpoint state.
"""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


CHECKPOINT_SCHEMA_VERSION = 1


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


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
    """Persist and restore durable generation checkpoints."""

    def __init__(self):
        self._root = (
            Path(__file__).resolve().parents[2]
            / "data"
            / "data_model"
        )

    def _checkpoint_path(
        self,
        data_model_id: str,
        job_id: str,
    ) -> Path:
        return (
            self._root
            / data_model_id
            / "generation"
            / job_id
            / "checkpoint.json"
        )

    def create_checkpoint(
        self,
        *,
        data_model_id: str,
        job_id: str,
        specification: dict[str, Any],
        seed: int,
        chunk_size: int,
        entity_targets: dict[str, int],
    ) -> dict[str, Any]:
        """Create a new checkpoint using the Experiment 024 contract."""

        if not job_id:
            raise ValueError("job_id must be non-empty.")

        if not isinstance(seed, int) or isinstance(seed, bool):
            raise ValueError("seed must be an integer.")

        if (
            not isinstance(chunk_size, int)
            or isinstance(chunk_size, bool)
            or chunk_size <= 0
        ):
            raise ValueError(
                "chunk_size must be a positive integer."
            )

        return {
            "schema_version": CHECKPOINT_SCHEMA_VERSION,
            "job_id": job_id,
            "specification_hash": compute_specification_hash(
                specification
            ),
            "seed": seed,
            "chunk_size": chunk_size,
            "entities": {
                entity_name: {
                    "target_rows": target_rows,
                    "completed_chunks": [],
                }
                for entity_name, target_rows in sorted(
                    entity_targets.items()
                )
            },
            "updated_at": utc_now(),
        }

    def save(
        self,
        *,
        data_model_id: str,
        job_id: str,
        seed: int,
        entities: dict[str, Any],
        specification_hash: str | None = None,
        chunk_size: int | None = None,
    ) -> dict[str, Any]:
        """Persist checkpoint state atomically and return the saved state."""

        path = self._checkpoint_path(data_model_id, job_id)
        path.parent.mkdir(parents=True, exist_ok=True)

        existing = self.get(
            data_model_id=data_model_id,
            job_id=job_id,
        ) or {}

        checkpoint = {
            "schema_version": CHECKPOINT_SCHEMA_VERSION,
            "job_id": job_id,
            "specification_hash": (
                specification_hash
                if specification_hash is not None
                else existing.get("specification_hash", "")
            ),
            "seed": seed,
            "chunk_size": (
                chunk_size
                if chunk_size is not None
                else existing.get("chunk_size", 0)
            ),
            "entities": entities,
            "updated_at": utc_now(),
        }

        payload = json.dumps(
            checkpoint,
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

            os.replace(temporary_path, path)

        except Exception:
            temporary_path.unlink(missing_ok=True)
            raise

        return checkpoint

    def get(
        self,
        data_model_id: str,
        job_id: str,
    ) -> dict[str, Any] | None:
        path = self._checkpoint_path(data_model_id, job_id)

        if not path.exists():
            return None

        try:
            data = json.loads(
                path.read_text(encoding="utf-8")
            )
        except (OSError, json.JSONDecodeError):
            return None

        if not isinstance(data, dict):
            return None

        return data

    def get_committed_rows(
        self,
        *,
        data_model_id: str,
        job_id: str,
        entity_name: str,
    ) -> int:
        """
        Derive committed rows from completed chunks.

        The checkpoint stores completed chunk identity, not telemetry.
        """

        checkpoint = self.get(
            data_model_id=data_model_id,
            job_id=job_id,
        )

        if checkpoint is None:
            return 0

        entity = (
            checkpoint.get("entities", {})
            .get(entity_name, {})
        )

        completed_chunks = entity.get(
            "completed_chunks",
            [],
        )

        chunk_size = checkpoint.get("chunk_size", 0)

        if (
            not isinstance(completed_chunks, list)
            or not isinstance(chunk_size, int)
            or chunk_size <= 0
        ):
            return 0

        return len(completed_chunks) * chunk_size

    def is_chunk_committed(
        self,
        *,
        data_model_id: str,
        job_id: str,
        entity_name: str,
        chunk_number: int,
    ) -> bool:
        checkpoint = self.get(
            data_model_id=data_model_id,
            job_id=job_id,
        )

        if checkpoint is None:
            return False

        entity = (
            checkpoint.get("entities", {})
            .get(entity_name, {})
        )

        completed_chunks = entity.get(
            "completed_chunks",
            [],
        )

        return chunk_number in completed_chunks

    def validate_identity(
        self,
        *,
        data_model_id: str,
        job_id: str,
        specification_hash: str,
        seed: int,
        chunk_size: int,
    ) -> None:
        """Validate checkpoint identity before resume."""

        checkpoint = self.get(
            data_model_id=data_model_id,
            job_id=job_id,
        )

        if checkpoint is None:
            raise ValueError(
                f"Checkpoint does not exist for job: {job_id}"
            )

        if checkpoint.get("job_id") != job_id:
            raise ValueError(
                "Checkpoint job identity does not match "
                "the requested job."
            )

        if checkpoint.get("specification_hash") != specification_hash:
            raise ValueError(
                "Checkpoint specification identity does not match "
                "the requested specification."
            )

        if checkpoint.get("seed") != seed:
            raise ValueError(
                "Checkpoint seed does not match "
                "the requested generation."
            )

        if checkpoint.get("chunk_size") != chunk_size:
            raise ValueError(
                "Checkpoint chunk size does not match "
                "the requested generation."
            )
