"""
File: generation_semantic_store.py
Purpose: Persist durable FORGE semantic generation state.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class SemanticStoreIntegrityError(ValueError):
    """Raised when persisted semantic generation state is invalid."""


class GenerationSemanticStore:
    """Persist AI-generated semantic values for generation recovery."""

    SCHEMA_VERSION = "1.0"
    SUPPORTED_MODES = {"UNIQUE", "VOCABULARY"}

    def __init__(self) -> None:
        self._root = (
            Path(__file__).resolve().parents[2]
            / "data"
            / "data_model"
        )

    def _semantic_path(
        self,
        data_model_id: str,
        job_id: str,
    ) -> Path:
        return (
            self._root
            / data_model_id
            / "generation"
            / job_id
            / "semantic.json"
        )

    @staticmethod
    def _normalized(value: str) -> str:
        return value.strip().casefold()

    def _validate_document(
        self,
        document: Any,
        *,
        job_id: str,
    ) -> dict[str, Any]:
        """Validate the complete semantic document before it is used."""

        if not isinstance(document, dict):
            raise SemanticStoreIntegrityError(
                f"Semantic state for job {job_id!r} must be a JSON object."
            )

        if document.get("schema_version") != self.SCHEMA_VERSION:
            raise SemanticStoreIntegrityError(
                f"Semantic state for job {job_id!r} has unsupported or "
                "missing schema version."
            )

        if document.get("job_id") != job_id:
            raise SemanticStoreIntegrityError(
                f"Semantic state job ID does not match requested job "
                f"{job_id!r}."
            )

        fields = document.get("fields")
        if not isinstance(fields, dict):
            raise SemanticStoreIntegrityError(
                f"Semantic state fields are invalid for job {job_id!r}."
            )

        for key, record in fields.items():
            if not isinstance(key, str) or not key.strip():
                raise SemanticStoreIntegrityError(
                    f"Semantic state contains an invalid field key "
                    f"for job {job_id!r}."
                )

            if not isinstance(record, dict):
                raise SemanticStoreIntegrityError(
                    f"Semantic state record {key!r} is invalid."
                )

            entity_name = record.get("entity_name")
            field_name = record.get("field_name")
            mode = record.get("mode")
            values = record.get("values")

            if (
                not isinstance(entity_name, str)
                or not entity_name.strip()
                or not isinstance(field_name, str)
                or not field_name.strip()
                or key != f"{entity_name}.{field_name}"
            ):
                raise SemanticStoreIntegrityError(
                    f"Semantic state field identity is invalid for {key!r}."
                )

            if not isinstance(mode, str) or mode not in self.SUPPORTED_MODES:
                raise SemanticStoreIntegrityError(
                    f"Semantic state mode is invalid for {key!r}."
                )

            if (
                not isinstance(values, list)
                or not all(
                    isinstance(value, str) and value.strip()
                    for value in values
                )
            ):
                raise SemanticStoreIntegrityError(
                    f"Semantic state values are invalid for {key!r}."
                )

        return document

    def _ensure_unique_values(
        self,
        *,
        key: str,
        values: list[str],
    ) -> None:
        normalized = [self._normalized(value) for value in values]
        if len(normalized) != len(set(normalized)):
            raise SemanticStoreIntegrityError(
                f"Persisted UNIQUE semantic values contain "
                f"duplicates for {key!r}; generation cannot safely resume."
            )

    def _write_document(
        self,
        *,
        path: Path,
        document: dict[str, Any],
        job_id: str,
    ) -> None:
        """Write a validated document through a temporary file."""

        self._validate_document(document, job_id=job_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary_path = path.with_suffix(".tmp")

        try:
            temporary_path.write_text(
                json.dumps(document, indent=2),
                encoding="utf-8",
            )
            temporary_path.replace(path)
        except OSError as exc:
            raise SemanticStoreIntegrityError(
                f"Could not persist semantic state for job {job_id!r}: {exc}"
            ) from exc

    def save(
        self,
        *,
        data_model_id: str,
        job_id: str,
        entity_name: str,
        field_name: str,
        mode: str,
        values: list[str],
    ) -> None:
        """Persist semantic values for one generated field."""

        existing = self.get_all(data_model_id, job_id)
        fields = dict(existing.get("fields", {}))

        key = f"{entity_name}.{field_name}"
        fields[key] = {
            "entity_name": entity_name,
            "field_name": field_name,
            "mode": mode,
            "values": list(values) if isinstance(values, list) else values,
        }

        document = {
            "schema_version": self.SCHEMA_VERSION,
            "job_id": job_id,
            "fields": fields,
        }

        path = self._semantic_path(data_model_id, job_id)
        self._write_document(
            path=path,
            document=document,
            job_id=job_id,
        )

    def append_unique(
        self,
        *,
        data_model_id: str,
        job_id: str,
        entity_name: str,
        field_name: str,
        values: list[str],
    ) -> None:
        """Append a UNIQUE semantic batch to existing semantic state."""

        existing = self.get_all(data_model_id, job_id)
        fields = dict(existing.get("fields", {}))
        key = f"{entity_name}.{field_name}"
        current = fields.get(key)

        if current is not None and current["mode"] != "UNIQUE":
            raise ValueError(
                f"Cannot append UNIQUE values to semantic field {key!r} "
                f"with mode {current['mode']!r}."
            )

        current_values = current["values"] if current is not None else []

        if current is not None:
            self._ensure_unique_values(
                key=key,
                values=current_values,
            )

        if not isinstance(values, list):
            raise ValueError(
                f"Semantic values must be a list for {key!r}."
            )

        if not all(
            isinstance(value, str) and value.strip()
            for value in values
        ):
            raise ValueError(
                f"Semantic values must be non-empty strings for {key!r}."
            )

        normalized_existing = {
            self._normalized(value)
            for value in current_values
        }
        normalized_batch = [
            self._normalized(value)
            for value in values
        ]

        if (
            len(set(normalized_batch)) != len(normalized_batch)
            or normalized_existing.intersection(normalized_batch)
        ):
            raise ValueError(
                f"Duplicate UNIQUE semantic values detected for {key!r}."
            )

        fields[key] = {
            "entity_name": entity_name,
            "field_name": field_name,
            "mode": "UNIQUE",
            "values": [*current_values, *values],
        }

        document = {
            "schema_version": self.SCHEMA_VERSION,
            "job_id": job_id,
            "fields": fields,
        }

        path = self._semantic_path(data_model_id, job_id)
        self._write_document(
            path=path,
            document=document,
            job_id=job_id,
        )

    def get(
        self,
        *,
        data_model_id: str,
        job_id: str,
        entity_name: str,
        field_name: str,
    ) -> dict[str, Any] | None:
        """Return persisted semantic state for one field."""

        document = self.get_all(data_model_id, job_id)
        key = f"{entity_name}.{field_name}"
        record = document.get("fields", {}).get(key)

        if record is not None and record["mode"] == "UNIQUE":
            self._ensure_unique_values(
                key=key,
                values=record["values"],
            )

        return record

    def get_all(
        self,
        data_model_id: str,
        job_id: str,
    ) -> dict[str, Any]:
        """Load and validate all persisted semantic state for a job."""

        path = self._semantic_path(data_model_id, job_id)

        if not path.exists():
            return {}

        try:
            document = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise SemanticStoreIntegrityError(
                f"Semantic state for job {job_id!r} exists but cannot "
                f"be read or parsed: {exc}"
            ) from exc

        return self._validate_document(document, job_id=job_id)
