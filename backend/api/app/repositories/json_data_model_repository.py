"""
File: json_data_model_repository.py
Purpose: JSON-backed FORGE data model repository.

Author: Ranjoy Sen
Email: ranjoy.sen@collins.com
"""

import json
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock
from uuid import uuid4

from app.interfaces.data_model import DataModel
from app.interfaces.data_model_repository import DataModelRepository


DEFAULT_DATA_MODEL_COLOR = "#7C5CFC"


class JsonDataModelRepository(DataModelRepository):
    """Persist FORGE data models in a local JSON store."""

    def __init__(self) -> None:
        self._file_path = (
            Path(__file__).resolve().parents[2]
            / "data"
            / "data_models.json"
        )
        self._lock = Lock()

        self._ensure_store()

    def create(
        self,
        owner_user_id: str,
        name: str,
        description: str,
        color: str,
        tags: list[str],
    ) -> DataModel:
        """Create and persist a FORGE data model."""

        now = datetime.now(timezone.utc)

        data_model = DataModel(
            data_model_id=str(uuid4()),
            owner_user_id=owner_user_id,
            name=name.strip(),
            description=description.strip(),
            color=color,
            tags=list(tags),
            status="Draft",
            created_at=now,
            updated_at=now,
        )

        with self._lock:
            data = self._read_data()

            data["data_models"].append(
                {
                    "data_model_id": data_model.data_model_id,
                    "owner_user_id": data_model.owner_user_id,
                    "name": data_model.name,
                    "description": data_model.description,
                    "color": data_model.color,
                    "tags": data_model.tags,
                    "status": data_model.status,
                    "created_at": data_model.created_at.isoformat(),
                    "updated_at": data_model.updated_at.isoformat(),
                }
            )

            self._write_data(data)

        return data_model

    def get_by_owner_user_id(
        self,
        owner_user_id: str,
    ) -> list[DataModel]:
        """Return data models owned by the specified user."""

        with self._lock:
            data = self._read_data()

        data_models = [
            self._to_data_model(record)
            for record in data["data_models"]
            if record["owner_user_id"] == owner_user_id
        ]

        return sorted(
            data_models,
            key=lambda data_model: data_model.updated_at,
            reverse=True,
        )

    def get_by_id_any(
        self,
        data_model_id: str,
    ):
        """Return a data model by ID without applying an owner filter."""

        with self._lock:
            data = self._read_data()

        for record in data["data_models"]:
            if record["data_model_id"] == data_model_id:
                return self._to_data_model(record)

        return None

    def get_by_id(
        self,
        data_model_id: str,
        owner_user_id: str,
    ) -> DataModel | None:
        """Return a data model owned by the specified user."""

        with self._lock:
            data = self._read_data()

        for record in data["data_models"]:
            if (
                record["data_model_id"] == data_model_id
                and record["owner_user_id"] == owner_user_id
            ):
                return self._to_data_model(record)

        return None

    def update(
        self,
        data_model_id: str,
        owner_user_id: str,
        name: str,
        description: str,
        color: str,
        tags: list[str],
    ) -> DataModel | None:
        """Update a data model owned by the specified user."""

        now = datetime.now(timezone.utc)

        with self._lock:
            data = self._read_data()

            for record in data["data_models"]:
                if (
                    record["data_model_id"] == data_model_id
                    and record["owner_user_id"] == owner_user_id
                ):
                    record["name"] = name.strip()
                    record["description"] = description.strip()
                    record["color"] = color
                    record["tags"] = list(tags)
                    record["updated_at"] = now.isoformat()

                    self._write_data(data)

                    return self._to_data_model(record)

        return None

    def delete(
        self,
        data_model_id: str,
        owner_user_id: str,
    ) -> bool:
        """Delete a data model owned by the specified user."""

        with self._lock:
            data = self._read_data()

            original_count = len(data["data_models"])

            data["data_models"] = [
                record
                for record in data["data_models"]
                if not (
                    record["data_model_id"] == data_model_id
                    and record["owner_user_id"] == owner_user_id
                )
            ]

            deleted = len(data["data_models"]) < original_count

            if deleted:
                self._write_data(data)

            return deleted

    def _ensure_store(self) -> None:
        """Ensure the data model repository storage exists."""

        self._file_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        if not self._file_path.exists():
            self._write_data({"data_models": []})

    def _read_data(self) -> dict:
        """Read the complete JSON data model store."""

        self._ensure_store()

        with self._file_path.open(
            "r",
            encoding="utf-8",
        ) as file:
            return json.load(file)

    def _write_data(self, data: dict) -> None:
        """Write the JSON data model store atomically."""

        self._file_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        temporary_path = self._file_path.with_suffix(".tmp")

        with temporary_path.open(
            "w",
            encoding="utf-8",
        ) as file:
            json.dump(
                data,
                file,
                indent=2,
            )
            file.write("\n")

        temporary_path.replace(self._file_path)

    @staticmethod
    def _to_data_model(record: dict) -> DataModel:
        """Convert a persisted record into a DataModel."""

        return DataModel(
            data_model_id=record["data_model_id"],
            owner_user_id=record["owner_user_id"],
            name=record["name"],
            description=record["description"],
            color=record.get("color", DEFAULT_DATA_MODEL_COLOR),
            tags=record.get("tags", []),
            status=record["status"],
            created_at=datetime.fromisoformat(record["created_at"]),
            updated_at=datetime.fromisoformat(record["updated_at"]),
        )
