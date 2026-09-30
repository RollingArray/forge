"""
File: generation_semantic_store.py
Purpose: Persist durable FORGE semantic generation state.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class GenerationSemanticStore:
    """Persist AI-generated semantic values for generation recovery."""

    def __init__(self) -> None:
        self._root = (
            Path(__file__).resolve().parents[2]
            / "data"
            / "generation"
        )

    def _semantic_path(self, job_id: str) -> Path:
        return self._root / job_id / "semantic.json"

    def save(
        self,
        *,
        job_id: str,
        entity_name: str,
        field_name: str,
        mode: str,
        values: list[str],
    ) -> None:
        """Persist semantic values for one generated field."""

        path = self._semantic_path(job_id)
        path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        existing = self.get_all(job_id)

        fields = existing.get("fields", {})

        fields[f"{entity_name}.{field_name}"] = {
            "entity_name": entity_name,
            "field_name": field_name,
            "mode": mode,
            "values": list(values),
        }

        document = {
            "schema_version": "1.0",
            "job_id": job_id,
            "fields": fields,
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
        job_id: str,
        entity_name: str,
        field_name: str,
    ) -> dict[str, Any] | None:
        """Return persisted semantic state for one field."""

        document = self.get_all(job_id)

        return (
            document.get("fields", {})
            .get(f"{entity_name}.{field_name}")
        )

    def get_all(
        self,
        job_id: str,
    ) -> dict[str, Any]:
        """Return all persisted semantic state for a generation job."""

        path = self._semantic_path(job_id)

        if not path.is_file():
            return {}

        try:
            document = json.loads(
                path.read_text(
                    encoding="utf-8",
                )
            )
        except (OSError, json.JSONDecodeError):
            return {}

        if not isinstance(document, dict):
            return {}

        return document
