"""
File: json_favorite_repository.py
Purpose: Per-user JSON persistence for Favorites.
"""

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock
from uuid import uuid4

from app.interfaces.favorite import Favorite, FavoriteResourceType, JOB_RESOURCE_TYPES
from app.interfaces.favorite_repository import FavoriteRepository


_LOCKS_GUARD = Lock()
_USER_LOCKS: dict[str, Lock] = {}


def _lock_for(path: Path) -> Lock:
    """Return a process-wide lock shared by repository instances."""

    key = str(path.resolve())
    with _LOCKS_GUARD:
        lock = _USER_LOCKS.get(key)
        if lock is None:
            lock = Lock()
            _USER_LOCKS[key] = lock
        return lock


class JsonFavoriteRepository(FavoriteRepository):
    """Persist each user's Favorites in a separate JSON file."""

    def __init__(self, root: Path | None = None) -> None:
        self._root = (
            root
            if root is not None
            else Path(__file__).resolve().parents[2]
            / "data"
            / "favorites"
        )
        self._root.mkdir(parents=True, exist_ok=True)

    def create(
        self,
        user_id: str,
        resource_type: FavoriteResourceType,
        data_model_id: str,
        job_id: str | None = None,
        entity_name: str | None = None,
    ) -> Favorite:
        """Create a favorite or return an existing matching favorite."""

        if not user_id.strip():
            raise ValueError("user_id must not be empty.")
        if not data_model_id.strip():
            raise ValueError("data_model_id must not be empty.")
        if resource_type in JOB_RESOURCE_TYPES:
            if not job_id or not job_id.strip():
                raise ValueError("job_id is required for this resource type.")
        elif job_id is not None:
            raise ValueError("job_id is only valid for job-specific resources.")

        if resource_type == FavoriteResourceType.GENERATED_TABLE:
            if entity_name is None or not entity_name.strip():
                raise ValueError("entity_name is required for generated tables.")
        elif entity_name is not None:
            raise ValueError("entity_name is only valid for generated tables.")

        path = self._path_for_user(user_id)
        with _lock_for(path):
            data = self._read_data(path)

            for record in data["favorites"]:
                if (
                    record["resource_type"] == resource_type.value
                    and record["data_model_id"] == data_model_id
                    and record.get("job_id") == job_id
                    and record.get("entity_name") == entity_name
                ):
                    return self._to_favorite(record, user_id)

            favorite = Favorite(
                favorite_id=str(uuid4()),
                user_id=user_id,
                resource_type=resource_type,
                data_model_id=data_model_id,
                job_id=job_id,
                entity_name=entity_name,
                created_at=datetime.now(timezone.utc),
            )
            data["favorites"].append(self._to_record(favorite))
            self._write_data(path, data)
            return favorite

    def get_by_user_id(self, user_id: str) -> list[Favorite]:
        """Return only the specified user's favorites, newest first."""

        path = self._path_for_user(user_id)
        with _lock_for(path):
            data = self._read_data(path)

        favorites = [
            self._to_favorite(record, user_id)
            for record in data["favorites"]
        ]
        favorites.sort(key=lambda item: item.created_at, reverse=True)
        return favorites

    def delete(self, favorite_id: str, user_id: str) -> bool:
        """Delete a favorite only from its owner's file."""

        path = self._path_for_user(user_id)
        with _lock_for(path):
            data = self._read_data(path)

            for index, record in enumerate(data["favorites"]):
                if record["favorite_id"] == favorite_id:
                    del data["favorites"][index]
                    self._write_data(path, data)
                    return True

        return False

    def _path_for_user(self, user_id: str) -> Path:
        """Map a user identity to a safe, deterministic filename."""

        digest = hashlib.sha256(user_id.encode("utf-8")).hexdigest()
        return self._root / f"{digest}.json"

    @staticmethod
    def _read_data(path: Path) -> dict:
        """Read a user's JSON file, initializing it when absent."""

        if not path.exists():
            return {"favorites": []}

        with path.open("r", encoding="utf-8") as file:
            data = json.load(file)

        if not isinstance(data, dict) or not isinstance(
            data.get("favorites"), list
        ):
            raise ValueError(f"Invalid Favorites store: {path}")

        return data

    @staticmethod
    def _write_data(path: Path, data: dict) -> None:
        """Atomically replace a user's JSON file."""

        path.parent.mkdir(parents=True, exist_ok=True)
        temporary_path = path.with_suffix(".tmp")

        try:
            with temporary_path.open("w", encoding="utf-8") as file:
                json.dump(data, file, indent=2)
                file.write("\n")
            temporary_path.replace(path)
        finally:
            if temporary_path.exists():
                temporary_path.unlink()

    @staticmethod
    def _to_record(favorite: Favorite) -> dict:
        """Serialize a favorite without repeating its user ID."""

        return {
            "favorite_id": favorite.favorite_id,
            "resource_type": favorite.resource_type.value,
            "data_model_id": favorite.data_model_id,
            "job_id": favorite.job_id,
            "entity_name": favorite.entity_name,
            "created_at": favorite.created_at.isoformat(),
        }

    @staticmethod
    def _to_favorite(record: dict, user_id: str) -> Favorite:
        """Restore the domain model using the owning file's user ID."""

        return Favorite(
            favorite_id=record["favorite_id"],
            user_id=user_id,
            resource_type=FavoriteResourceType(record["resource_type"]),
            data_model_id=record["data_model_id"],
            job_id=record.get("job_id"),
            entity_name=record.get("entity_name"),
            created_at=datetime.fromisoformat(record["created_at"]),
        )
