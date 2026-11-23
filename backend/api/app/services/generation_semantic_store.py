"""
Persist durable, position-aware FORGE semantic generation state.

UNIQUE semantic values are keyed by zero-based global row index.
VOCABULARY semantic values remain an ordered, reusable vocabulary.
"""

from __future__ import annotations

import json
import re
from collections.abc import Mapping
from pathlib import Path
from typing import Any


from app.services.generation_file_persistence import (
    atomic_write_text,
    generation_file_lock,
)


class SemanticStoreIntegrityError(ValueError):
    """Raised when persisted semantic generation state is invalid."""


class GenerationSemanticStore:
    """Persist semantic values safely across generation interruptions."""

    SCHEMA_VERSION = "2.0"
    SUPPORTED_MODES = {"UNIQUE", "VOCABULARY"}
    MAX_GLOBAL_ROW_INDEX = (1 << 63) - 1

    _WINDOWS_RESERVED = re.compile(
        r"^(CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])(?:\..*)?$",
        re.IGNORECASE,
    )

    def __init__(self) -> None:
        self._root = (
            Path(__file__).resolve().parents[2]
            / "data"
            / "data_model"
        )

    @classmethod
    def _validate_path_component(cls, value: str, label: str) -> str:
        if not isinstance(value, str) or not value:
            raise ValueError(f"{label} must be a non-empty string.")

        if (
            value in {".", ".."}
            or any(char in value for char in ("/", "\\"))
            or any(ord(char) < 32 for char in value)
            or any(char in value for char in '<>:"|?*')
            or value.endswith((" ", "."))
            or cls._WINDOWS_RESERVED.fullmatch(value)
        ):
            raise ValueError(f"Invalid {label}: {value!r}.")

        return value

    def _semantic_path(self, data_model_id: str, job_id: str) -> Path:
        model_component = self._validate_path_component(
            data_model_id,
            "data_model_id",
        )
        job_component = self._validate_path_component(job_id, "job_id")

        root = self._root.resolve()
        path = (
            root
            / model_component
            / "generation"
            / job_component
            / "semantic.json"
        )

        resolved_path = path.resolve()
        try:
            resolved_path.relative_to(root)
        except ValueError as exc:
            raise ValueError(
                "Semantic path escapes the configured data-model root."
            ) from exc

        return path

    @staticmethod
    def _normalized(value: str) -> str:
        return value.strip().casefold()

    @classmethod
    def _validate_values(
        cls,
        *,
        key: str,
        values: Any,
    ) -> list[str]:
        if not isinstance(values, list):
            raise SemanticStoreIntegrityError(
                f"Semantic values must be a list for {key!r}."
            )

        if not all(
            isinstance(value, str) and value.strip()
            for value in values
        ):
            raise SemanticStoreIntegrityError(
                f"Semantic values must be non-empty strings for {key!r}."
            )

        normalized = [cls._normalized(value) for value in values]
        if len(normalized) != len(set(normalized)):
            raise SemanticStoreIntegrityError(
                f"Duplicate semantic values detected for {key!r}."
            )

        return values

    @classmethod
    def _parse_row_index(cls, row_key: Any, key: str) -> int:
        maximum = str(cls.MAX_GLOBAL_ROW_INDEX)

        if (
            not isinstance(row_key, str)
            or not row_key.isascii()
            or not row_key.isdigit()
            or (len(row_key) > 1 and row_key.startswith("0"))
            or len(row_key) > len(maximum)
            or (
                len(row_key) == len(maximum)
                and row_key > maximum
            )
        ):
            raise SemanticStoreIntegrityError(
                f"Invalid row index {row_key!r} for {key!r}."
            )

        return int(row_key)

    @classmethod
    def _validate_unique_mapping(
        cls,
        *,
        key: str,
        values_by_row: Any,
    ) -> dict[str, str]:
        if not isinstance(values_by_row, dict):
            raise SemanticStoreIntegrityError(
                f"UNIQUE semantic row mapping is invalid for {key!r}."
            )

        normalized_values: set[str] = set()
        validated: dict[str, str] = {}

        for row_key, value in values_by_row.items():
            cls._parse_row_index(row_key, key)

            if not isinstance(value, str) or not value.strip():
                raise SemanticStoreIntegrityError(
                    f"Invalid UNIQUE semantic value at row "
                    f"{row_key!r} for {key!r}."
                )

            normalized = cls._normalized(value)
            if normalized in normalized_values:
                raise SemanticStoreIntegrityError(
                    f"Persisted UNIQUE semantic values contain "
                    f"duplicates for {key!r}."
                )

            normalized_values.add(normalized)
            validated[row_key] = value

        return validated

    @classmethod
    def _validate_document(
        cls,
        document: Any,
        *,
        data_model_id: str,
        job_id: str,
    ) -> dict[str, Any]:
        if not isinstance(document, dict):
            raise SemanticStoreIntegrityError(
                f"Semantic state for job {job_id!r} must be a JSON object."
            )

        if document.get("schema_version") != cls.SCHEMA_VERSION:
            raise SemanticStoreIntegrityError(
                f"Semantic state for job {job_id!r} has unsupported or "
                "missing schema version."
            )

        expected_keys = {
            "schema_version",
            "data_model_id",
            "job_id",
            "fields",
        }
        if set(document) != expected_keys:
            raise SemanticStoreIntegrityError(
                f"Semantic document structure is invalid for job {job_id!r}."
            )

        if document.get("data_model_id") != data_model_id:
            raise SemanticStoreIntegrityError(
                "Semantic state data model ID does not match the "
                f"requested data model {data_model_id!r}."
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

        for field_key, record in fields.items():
            if not isinstance(field_key, str) or not field_key.strip():
                raise SemanticStoreIntegrityError(
                    "Semantic state contains an invalid field key."
                )

            if not isinstance(record, dict):
                raise SemanticStoreIntegrityError(
                    f"Semantic state record {field_key!r} is invalid."
                )

            entity_name = record.get("entity_name")
            field_name = record.get("field_name")
            mode = record.get("mode")

            if (
                not isinstance(entity_name, str)
                or not entity_name.strip()
                or not isinstance(field_name, str)
                or not field_name.strip()
                or field_key != f"{entity_name}.{field_name}"
            ):
                raise SemanticStoreIntegrityError(
                    f"Semantic field identity is invalid for {field_key!r}."
                )

            if (
                not isinstance(mode, str)
                or mode not in cls.SUPPORTED_MODES
            ):
                raise SemanticStoreIntegrityError(
                    f"Semantic state mode is invalid for {field_key!r}."
                )

            if mode == "UNIQUE":
                if set(record) != {
                    "entity_name",
                    "field_name",
                    "mode",
                    "values_by_row",
                }:
                    raise SemanticStoreIntegrityError(
                        f"UNIQUE semantic record structure is invalid "
                        f"for {field_key!r}."
                    )

                cls._validate_unique_mapping(
                    key=field_key,
                    values_by_row=record["values_by_row"],
                )
            else:
                if set(record) != {
                    "entity_name",
                    "field_name",
                    "mode",
                    "values",
                }:
                    raise SemanticStoreIntegrityError(
                        f"VOCABULARY semantic record structure is invalid "
                        f"for {field_key!r}."
                    )

                cls._validate_values(
                    key=field_key,
                    values=record["values"],
                )

        return document

    @staticmethod
    def _field_key(entity_name: str, field_name: str) -> str:
        if not isinstance(entity_name, str) or not entity_name.strip():
            raise ValueError("entity_name must be a non-empty string.")

        if not isinstance(field_name, str) or not field_name.strip():
            raise ValueError("field_name must be a non-empty string.")

        return f"{entity_name}.{field_name}"

    def _read_document(
        self,
        path: Path,
        *,
        data_model_id: str,
        job_id: str,
    ) -> dict[str, Any] | None:
        try:
            raw_content = path.read_text(encoding="utf-8")
        except FileNotFoundError:
            return None
        except (OSError, UnicodeDecodeError) as exc:
            raise SemanticStoreIntegrityError(
                f"Semantic state for job {job_id!r} exists but cannot "
                f"be read: {exc}"
            ) from exc

        try:
            document = json.loads(raw_content)
        except json.JSONDecodeError as exc:
            raise SemanticStoreIntegrityError(
                f"Semantic state for job {job_id!r} exists but cannot "
                f"be parsed: {exc}"
            ) from exc

        return self._validate_document(
            document,
            data_model_id=data_model_id,
            job_id=job_id,
        )

    def _write_document(
        self,
        path: Path,
        document: dict[str, Any],
        *,
        data_model_id: str,
        job_id: str,
    ) -> None:
        self._validate_document(
            document,
            data_model_id=data_model_id,
            job_id=job_id,
        )

        try:
            atomic_write_text(
                path,
                json.dumps(
                    document,
                    ensure_ascii=False,
                    indent=2,
                    sort_keys=True,
                ),
            )
        except OSError as exc:
            raise SemanticStoreIntegrityError(
                f"Could not persist semantic state for job {job_id!r}: {exc}"
            ) from exc

    @staticmethod
    def _empty_document(
        data_model_id: str,
        job_id: str,
    ) -> dict[str, Any]:
        return {
            "schema_version": GenerationSemanticStore.SCHEMA_VERSION,
            "data_model_id": data_model_id,
            "job_id": job_id,
            "fields": {},
        }

    def get_all(
        self,
        data_model_id: str,
        job_id: str,
    ) -> dict[str, Any]:
        """Load and validate all persisted semantic state for a job."""

        path = self._semantic_path(data_model_id, job_id)

        with generation_file_lock(path):
            document = self._read_document(
                path,
                data_model_id=data_model_id,
                job_id=job_id,
            )

        if document is None:
            return self._empty_document(data_model_id, job_id)

        return document

    def get(
        self,
        *,
        data_model_id: str,
        job_id: str,
        entity_name: str,
        field_name: str,
    ) -> dict[str, Any] | None:
        """Return persisted state for one semantic field."""

        key = self._field_key(entity_name, field_name)
        document = self.get_all(data_model_id, job_id)
        record = document["fields"].get(key)

        if record is None:
            return None

        # Return a detached value so callers cannot mutate persisted state.
        return json.loads(json.dumps(record))

    def save_vocabulary(
        self,
        *,
        data_model_id: str,
        job_id: str,
        entity_name: str,
        field_name: str,
        values: list[str],
    ) -> None:
        """Persist a finite vocabulary without allowing silent replacement."""

        key = self._field_key(entity_name, field_name)
        validated_values = self._validate_values(key=key, values=values)

        if not validated_values:
            raise SemanticStoreIntegrityError(
                f"VOCABULARY semantic values cannot be empty for {key!r}."
            )

        path = self._semantic_path(data_model_id, job_id)
        path.parent.mkdir(parents=True, exist_ok=True)

        with generation_file_lock(path):
            document = self._read_document(
                path,
                data_model_id=data_model_id,
                job_id=job_id,
            )
            if document is None:
                document = self._empty_document(data_model_id, job_id)

            fields = dict(document["fields"])
            current = fields.get(key)

            new_record = {
                "entity_name": entity_name,
                "field_name": field_name,
                "mode": "VOCABULARY",
                "values": list(validated_values),
            }

            if current is not None:
                if current != new_record:
                    raise SemanticStoreIntegrityError(
                        f"Conflicting semantic state already exists "
                        f"for {key!r}; vocabulary replacement is not allowed."
                    )
                return

            fields[key] = new_record
            updated = {
                **document,
                "fields": fields,
            }

            self._write_document(
                path,
                updated,
                data_model_id=data_model_id,
                job_id=job_id,
            )

    def get_unique_values(
        self,
        *,
        data_model_id: str,
        job_id: str,
        entity_name: str,
        field_name: str,
    ) -> dict[int, str]:
        """Return UNIQUE values keyed by zero-based global row index."""

        record = self.get(
            data_model_id=data_model_id,
            job_id=job_id,
            entity_name=entity_name,
            field_name=field_name,
        )

        if record is None:
            return {}

        if record["mode"] != "UNIQUE":
            raise SemanticStoreIntegrityError(
                f"Semantic field {entity_name}.{field_name} is not UNIQUE."
            )

        return {
            int(row_index): value
            for row_index, value in record["values_by_row"].items()
        }

    def commit_unique_values(
        self,
        *,
        data_model_id: str,
        job_id: str,
        entity_name: str,
        field_name: str,
        values_by_row: Mapping[int, str],
    ) -> None:
        """Atomically commit UNIQUE values at explicit global row indices.

        Existing row assignments are immutable. Repeating an identical
        assignment is idempotent. Missing row indices remain missing.
        """

        key = self._field_key(entity_name, field_name)

        if not isinstance(values_by_row, Mapping):
            raise SemanticStoreIntegrityError(
                f"UNIQUE semantic values must be a row mapping for {key!r}."
            )

        incoming: dict[int, str] = {}
        incoming_normalized: set[str] = set()

        for row_index, value in values_by_row.items():
            if (
                isinstance(row_index, bool)
                or not isinstance(row_index, int)
                or row_index < 0
                or row_index > self.MAX_GLOBAL_ROW_INDEX
            ):
                raise SemanticStoreIntegrityError(
                    f"Invalid global row index {row_index!r} for {key!r}."
                )

            if not isinstance(value, str) or not value.strip():
                raise SemanticStoreIntegrityError(
                    f"UNIQUE semantic values must be non-empty strings "
                    f"for {key!r}."
                )

            normalized = self._normalized(value)
            if normalized in incoming_normalized:
                raise SemanticStoreIntegrityError(
                    f"Duplicate UNIQUE semantic values detected "
                    f"for {key!r}."
                )

            incoming_normalized.add(normalized)
            incoming[row_index] = value

        if not incoming:
            return

        path = self._semantic_path(data_model_id, job_id)
        path.parent.mkdir(parents=True, exist_ok=True)

        with generation_file_lock(path):
            document = self._read_document(
                path,
                data_model_id=data_model_id,
                job_id=job_id,
            )
            if document is None:
                document = self._empty_document(data_model_id, job_id)

            fields = dict(document["fields"])
            current = fields.get(key)

            if current is not None and current["mode"] != "UNIQUE":
                raise SemanticStoreIntegrityError(
                    f"Cannot commit UNIQUE values to semantic field "
                    f"{key!r} with mode {current['mode']!r}."
                )

            current_values: dict[int, str] = {}
            if current is not None:
                current_values = {
                    int(row_index): value
                    for row_index, value in current["values_by_row"].items()
                }

            # Existing row assignments cannot be changed.
            for row_index, value in incoming.items():
                existing_value = current_values.get(row_index)
                if existing_value is not None and existing_value != value:
                    raise SemanticStoreIntegrityError(
                        f"Conflicting UNIQUE semantic value for {key!r} "
                        f"at global row index {row_index}."
                    )

            combined = dict(current_values)
            combined.update(incoming)

            # Enforce uniqueness across all populated row positions.
            normalized_values = [
                self._normalized(value)
                for value in combined.values()
            ]
            if len(normalized_values) != len(set(normalized_values)):
                raise SemanticStoreIntegrityError(
                    f"Duplicate UNIQUE semantic values detected "
                    f"across row positions for {key!r}."
                )

            if combined == current_values:
                return

            fields[key] = {
                "entity_name": entity_name,
                "field_name": field_name,
                "mode": "UNIQUE",
                "values_by_row": {
                    str(row_index): value
                    for row_index, value in sorted(combined.items())
                },
            }

            updated = {
                **document,
                "fields": fields,
            }

            self._write_document(
                path,
                updated,
                data_model_id=data_model_id,
                job_id=job_id,
            )
