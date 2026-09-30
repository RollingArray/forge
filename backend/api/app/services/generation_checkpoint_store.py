"""
File: generation_checkpoint_store.py
Purpose: Persist durable FORGE generation checkpoint state.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class GenerationCheckpointStore:
    """Persist durable generation progress for restart and resume."""

    def __init__(self) -> None:
        self._root = (
            Path(__file__).resolve().parents[2]
            / "data"
            / "generation"
        )

    def _checkpoint_path(self, job_id: str) -> Path:
        return self._root / job_id / "checkpoint.json"

    def save(
        self,
        *,
        job_id: str,
        seed: int,
        entities: dict[str, dict[str, Any]],
    ) -> None:
        """Persist the current durable generation checkpoint."""
        path = self._checkpoint_path(job_id)
        path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        checkpoint = {
            "job_id": job_id,
            "schema_version": "1.0",
            "seed": seed,
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "entities": entities,
        }

        temporary_path = path.with_suffix(".tmp")

        temporary_path.write_text(
            json.dumps(
                checkpoint,
                indent=2,
            ),
            encoding="utf-8",
        )

        temporary_path.replace(path)

    def get_committed_rows(
        self,
        *,
        job_id: str,
        entity_name: str,
    ) -> int:
        """Return the durably committed row count for an entity."""
        checkpoint = self.get(job_id)

        if checkpoint is None:
            return 0

        entity = (
            checkpoint.get("entities", {})
            .get(entity_name, {})
        )

        committed_rows = entity.get(
            "committed_rows",
            0,
        )

        return (
            committed_rows
            if isinstance(committed_rows, int) and committed_rows >= 0
            else 0
        )

    def is_chunk_committed(
        self,
        *,
        job_id: str,
        entity_name: str,
        chunk_number: int,
    ) -> bool:
        """Return whether a specific chunk is durably committed."""
        checkpoint = self.get(job_id)

        if checkpoint is None:
            return False

        entity = (
            checkpoint.get("entities", {})
            .get(entity_name, {})
        )

        committed_chunks = entity.get(
            "committed_chunks",
            [],
        )

        return chunk_number in committed_chunks

    def get(
        self,
        job_id: str,
    ) -> dict[str, Any] | None:
        """Return the persisted checkpoint for a generation job."""
        path = self._checkpoint_path(job_id)

        if not path.exists():
            return None

        try:
            return json.loads(
                path.read_text(
                    encoding="utf-8",
                )
            )
        except (OSError, json.JSONDecodeError):
            return None
