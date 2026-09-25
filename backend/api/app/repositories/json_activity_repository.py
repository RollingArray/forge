"""
File: json_activity_repository.py
Purpose: JSON-backed FORGE activity repository.

Author: Ranjoy Sen
Email: ranjoy.sen@collins.com
"""

import json
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock
from typing import Any
from uuid import uuid4

from app.interfaces.activity import Activity
from app.interfaces.activity_repository import ActivityRepository


class JsonActivityRepository(ActivityRepository):
    """Persist FORGE activity events in a local JSON store."""

    def __init__(self) -> None:
        self._file_path = (
            Path(__file__).resolve().parents[2]
            / "data"
            / "activities.json"
        )
        self._lock = Lock()

        self._ensure_store()

    def create(
        self,
        owner_user_id: str,
        actor_user_id: str,
        activity_type: str,
        title: str,
        description: str,
        data_model_id: str | None = None,
        job_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> Activity:
        """Create and persist a FORGE activity event."""

        activity = Activity(
            activity_id=str(uuid4()),
            owner_user_id=owner_user_id,
            actor_user_id=actor_user_id,
            type=activity_type,
            title=title.strip(),
            description=description.strip(),
            timestamp=datetime.now(timezone.utc),
            data_model_id=data_model_id,
            job_id=job_id,
            metadata=dict(metadata) if metadata is not None else {},
        )

        with self._lock:
            data = self._read_data()

            data["activities"].append(
                {
                    "activity_id": activity.activity_id,
                    "owner_user_id": activity.owner_user_id,
                    "actor_user_id": activity.actor_user_id,
                    "type": activity.type,
                    "title": activity.title,
                    "description": activity.description,
                    "timestamp": activity.timestamp.isoformat(),
                    "data_model_id": activity.data_model_id,
                    "job_id": activity.job_id,
                    "metadata": activity.metadata,
                }
            )

            self._write_data(data)

        return activity

    def get_recent_by_owner_user_id(
        self,
        owner_user_id: str,
        limit: int = 10,
    ) -> list[Activity]:
        """Return recent activity events for the specified workspace owner."""

        if limit <= 0:
            return []

        with self._lock:
            data = self._read_data()

        activities = [
            self._to_activity(record)
            for record in data["activities"]
            if record["owner_user_id"] == owner_user_id
        ]

        activities.sort(
            key=lambda activity: activity.timestamp,
            reverse=True,
        )

        return activities[:limit]

    def get_by_data_model_id(
        self,
        data_model_id: str,
        limit: int = 50,
    ) -> list[Activity]:
        """Return recent activity events for the specified data model."""

        if limit <= 0:
            return []

        with self._lock:
            data = self._read_data()

        activities = [
            self._to_activity(record)
            for record in data["activities"]
            if record.get("data_model_id") == data_model_id
        ]

        activities.sort(
            key=lambda activity: activity.timestamp,
            reverse=True,
        )

        return activities[:limit]

    def _ensure_store(self) -> None:
        """Ensure the activity repository storage exists."""

        self._file_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        if not self._file_path.exists():
            self._write_data({"activities": []})

    def _read_data(self) -> dict:
        """Read the complete JSON activity store."""

        self._ensure_store()

        with self._file_path.open(
            "r",
            encoding="utf-8",
        ) as file:
            return json.load(file)

    def _write_data(self, data: dict) -> None:
        """Write the JSON activity store atomically."""

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
    def _to_activity(record: dict) -> Activity:
        """Convert a persisted record into an Activity."""

        return Activity(
            activity_id=record["activity_id"],
            owner_user_id=record["owner_user_id"],
            actor_user_id=record["actor_user_id"],
            type=record["type"],
            title=record["title"],
            description=record["description"],
            timestamp=datetime.fromisoformat(record["timestamp"]),
            data_model_id=record.get("data_model_id"),
            job_id=record.get("job_id"),
            metadata=record.get("metadata", {}),
        )
