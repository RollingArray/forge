"""
File: generation_quality_store.py
Purpose: Persist measurable FORGE generation quality evidence.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.services.generation_file_persistence import (
    atomic_write_text,
    generation_file_lock,
)


class GenerationQualityStore:
    """Persist quality evidence for a generation job."""

    def __init__(self) -> None:
        self._root = (
            Path(__file__).resolve().parents[2]
            / "data"
            / "data_model"
        )

    def _quality_path(
        self,
        data_model_id: str,
        job_id: str,
    ) -> Path:
        return (
            self._root
            / data_model_id
            / "generation"
            / job_id
            / "quality.json"
        )

    def save(
        self,
        *,
        data_model_id: str,
        job_id: str,
        quality: dict[str, Any],
    ) -> None:
        """Persist the completed quality profile."""

        path = self._quality_path(data_model_id, job_id)

        document = {
            "schema_version": "1.0",
            "job_id": job_id,
            "quality": quality,
        }

        payload = json.dumps(document, indent=2)

        with generation_file_lock(path):
            atomic_write_text(path, payload)

    def get(
        self,
        *,
        data_model_id: str,
        job_id: str,
    ) -> dict[str, Any] | None:
        """Return persisted quality evidence."""

        path = self._quality_path(data_model_id, job_id)

        with generation_file_lock(path):
            if not path.is_file():
                return None

            try:
                document = json.loads(
                    path.read_text(encoding="utf-8")
                )
            except (OSError, json.JSONDecodeError):
                return None

            if not isinstance(document, dict):
                return None

            quality = document.get("quality")

            return quality if isinstance(quality, dict) else None
