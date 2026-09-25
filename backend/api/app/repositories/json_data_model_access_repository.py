"""
File: json_data_model_access_repository.py
Purpose: JSON-backed FORGE data model access repository.

Author: Ranjoy Sen
Email: ranjoy.sen@collins.com
"""

import json
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock
from uuid import uuid4

from app.constants.data_model_access import DataModelAccessRole
from app.interfaces.data_model_access import DataModelAccess
from app.interfaces.data_model_access_repository import (
    DataModelAccessRepository,
)


class JsonDataModelAccessRepository(DataModelAccessRepository):
    """Persist FORGE data model access in a local JSON store."""

    def __init__(self) -> None:
        self._file_path = (
            Path(__file__).resolve().parents[2]
            / "data"
            / "data_model_access.json"
        )
        self._lock = Lock()

        self._ensure_store()

    def grant_access(
        self,
        data_model_id: str,
        user_id: str,
        role: DataModelAccessRole,
    ) -> DataModelAccess:
        """Grant or replace access for a user on a data model."""

        now = datetime.now(timezone.utc)

        with self._lock:
            data = self._read_data()

            for record in data["access"]:
                if (
                    record["data_model_id"] == data_model_id
                    and record["user_id"] == user_id
                ):
                    record["role"] = role.value
                    self._write_data(data)
                    return self._to_access(record)

            access = DataModelAccess(
                data_model_id=data_model_id,
                user_id=user_id,
                role=role,
                granted_at=now,
            )

            data["access"].append(
                {
                    "access_id": str(uuid4()),
                    "data_model_id": access.data_model_id,
                    "user_id": access.user_id,
                    "role": access.role.value,
                    "granted_at": access.granted_at.isoformat(),
                }
            )

            self._write_data(data)

            return access

    def get_by_data_model_id(
        self,
        data_model_id: str,
    ) -> list[DataModelAccess]:
        """Return all access records for a data model."""

        with self._lock:
            data = self._read_data()

        return [
            self._to_access(record)
            for record in data["access"]
            if record["data_model_id"] == data_model_id
        ]

    def get_by_user_id(
        self,
        user_id: str,
    ) -> list[DataModelAccess]:
        """Return all data model access records for a user."""

        with self._lock:
            data = self._read_data()

        return [
            self._to_access(record)
            for record in data["access"]
            if record["user_id"] == user_id
        ]

    def get_access(
        self,
        data_model_id: str,
        user_id: str,
    ) -> DataModelAccess | None:
        """Return a user's access to a data model."""

        with self._lock:
            data = self._read_data()

        for record in data["access"]:
            if (
                record["data_model_id"] == data_model_id
                and record["user_id"] == user_id
            ):
                return self._to_access(record)

        return None

    def update_role(
        self,
        data_model_id: str,
        user_id: str,
        role: DataModelAccessRole,
    ) -> DataModelAccess | None:
        """Update a user's role for a data model."""

        with self._lock:
            data = self._read_data()

            for record in data["access"]:
                if (
                    record["data_model_id"] == data_model_id
                    and record["user_id"] == user_id
                ):
                    record["role"] = role.value
                    self._write_data(data)
                    return self._to_access(record)

        return None

    def revoke_access(
        self,
        data_model_id: str,
        user_id: str,
    ) -> bool:
        """Revoke a user's access to a data model."""

        with self._lock:
            data = self._read_data()

            original_count = len(data["access"])

            data["access"] = [
                record
                for record in data["access"]
                if not (
                    record["data_model_id"] == data_model_id
                    and record["user_id"] == user_id
                )
            ]

            revoked = len(data["access"]) < original_count

            if revoked:
                self._write_data(data)

            return revoked

    def _ensure_store(self) -> None:
        """Ensure the access repository storage exists."""

        self._file_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        if not self._file_path.exists():
            self._write_data({"access": []})

    def _read_data(self) -> dict:
        """Read the complete JSON access store."""

        self._ensure_store()

        with self._file_path.open(
            "r",
            encoding="utf-8",
        ) as file:
            return json.load(file)

    def _write_data(self, data: dict) -> None:
        """Write the JSON access store atomically."""

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
    def _to_access(record: dict) -> DataModelAccess:
        """Convert a persisted record into a DataModelAccess."""

        return DataModelAccess(
            data_model_id=record["data_model_id"],
            user_id=record["user_id"],
            role=DataModelAccessRole(record["role"]),
            granted_at=datetime.fromisoformat(record["granted_at"]),
        )
