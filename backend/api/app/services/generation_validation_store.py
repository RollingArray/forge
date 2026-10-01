"""
File: generation_validation_store.py
Purpose: Persist FORGE generated-dataset validation evidence.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class GenerationValidationStore:
    """Persist validation evidence for a generation job."""

    def __init__(self) -> None:
        self._root = (
            Path(__file__).resolve().parents[2]
            / "data"
            / "data_model"
        )

    def _validation_path(
        self,
        data_model_id: str,
        job_id: str,
    ) -> Path:
        return (
            self._root
            / data_model_id
            / "generation"
            / job_id
            / "validation.json"
        )

    def save(
        self,
        *,
        data_model_id: str,
        job_id: str,
        validation: dict[str, Any],
    ) -> None:
        """Persist the completed validation report."""

        path = self._validation_path(
            data_model_id,
            job_id,
        )

        path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        document = {
            "schema_version": "1.0",
            "job_id": job_id,
            "validation": validation,
        }

        temporary_path = path.with_suffix(".tmp")

        temporary_path.write_text(
            json.dumps(
                document,
                indent=2,
            ),
            encoding="utf-8",
        )

        temporary_path.replace(path)

    def get(
        self,
        *,
        data_model_id: str,
        job_id: str,
    ) -> dict[str, Any] | None:
        """Return persisted validation evidence."""

        path = self._validation_path(
            data_model_id,
            job_id,
        )

        if not path.is_file():
            return None

        try:
            document = json.loads(
                path.read_text(
                    encoding="utf-8",
                )
            )
        except (OSError, json.JSONDecodeError):
            return None

        if not isinstance(document, dict):
            return None

        validation = document.get("validation")

        return (
            validation
            if isinstance(validation, dict)
            else None
        )
