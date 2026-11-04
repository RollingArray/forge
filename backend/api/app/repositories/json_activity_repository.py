"""
File: json_activity_repository.py
Purpose: Append-only JSONL persistence for FORGE activity events.
"""

import fcntl
import hashlib
import json
import os
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock, RLock
from typing import Any, Iterator
from uuid import uuid4

from app.interfaces.activity import Activity
from app.interfaces.activity_repository import ActivityRepository


class JsonActivityRepository(ActivityRepository):
    """Persist activity events in independently locked JSONL partitions."""

    _registry_guard = Lock()
    _path_locks: dict[str, RLock] = {}

    def __init__(self) -> None:
        self._data_directory = (
            Path(__file__).resolve().parents[2] / "data" / "activity"
        )
        self._lock_directory = self._data_directory / ".locks"

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
        """Append one authoritative event and its derived index entry."""

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

        scope = "data_model" if data_model_id else "workspace"
        identity = data_model_id or owner_user_id
        year = activity.timestamp.strftime("%Y")
        month = activity.timestamp.strftime("%m")

        event_path, index_path = self._partition_paths(
            scope=scope,
            identity=identity,
            year=year,
            month=month,
        )

        with self._partition_lock(scope, identity, year, month):
            event_path.parent.mkdir(parents=True, exist_ok=True)
            index_path.parent.mkdir(parents=True, exist_ok=True)

            self._repair_event_tail(event_path)

            record = self._to_record(activity)
            payload = (
                json.dumps(
                    record,
                    separators=(",", ":"),
                    ensure_ascii=False,
                    allow_nan=False,
                ) + "\n"
            ).encode("utf-8")

            with event_path.open("ab") as event_file:
                offset = event_file.tell()
                event_file.write(payload)
                event_file.flush()
                os.fsync(event_file.fileno())

            index_record = {
                "activity_id": activity.activity_id,
                "timestamp": activity.timestamp.isoformat(),
                "offset": offset,
                "length": len(payload),
            }

            try:
                self._append_index(index_path, index_record)
            except OSError:
                # The event is authoritative. Recover the derived index
                # rather than losing an already-persisted event.
                self._rebuild_index(event_path, index_path)

        return activity

    def get_recent_by_owner_user_id(
        self,
        owner_user_id: str,
        limit: int = 10,
    ) -> list[Activity]:
        """Return workspace-scoped events for the specified owner."""

        if limit <= 0:
            return []

        return self._get_recent(
            scope="workspace",
            identity=owner_user_id,
            limit=limit,
        )

    def get_by_data_model_id(
        self,
        data_model_id: str,
        limit: int = 50,
    ) -> list[Activity]:
        """Return events shared by all authorized users of a data model."""

        if limit <= 0:
            return []

        return self._get_recent(
            scope="data_model",
            identity=data_model_id,
            limit=limit,
        )

    def _get_recent(
        self,
        scope: str,
        identity: str,
        limit: int,
    ) -> list[Activity]:
        partition_root = self._partition_root(scope, identity)
        if not partition_root.exists():
            return []

        event_files = sorted(
            partition_root.glob("events/*/*.jsonl"),
            reverse=True,
        )

        activities: list[Activity] = []

        for event_path in event_files:
            year = event_path.parent.name
            month = event_path.stem

            _, index_path = self._partition_paths(
                scope=scope,
                identity=identity,
                year=year,
                month=month,
            )

            with self._partition_lock(scope, identity, year, month):
                self._repair_event_tail(event_path)
                self._ensure_index(event_path, index_path)

                try:
                    index_entries = self._read_index_entries(index_path)
                    index_entries.sort(
                        key=lambda entry: (
                            datetime.fromisoformat(entry["timestamp"]),
                            entry["activity_id"],
                        ),
                        reverse=True,
                    )
                    selected_entries = index_entries[:limit]

                    partition_activities = self._read_indexed_activities(
                        event_path=event_path,
                        index_entries=selected_entries,
                    )
                except (ValueError, KeyError, TypeError, json.JSONDecodeError):
                    self._rebuild_index(event_path, index_path)
                    index_entries = self._read_index_entries(index_path)
                    index_entries.sort(
                        key=lambda entry: (
                            datetime.fromisoformat(entry["timestamp"]),
                            entry["activity_id"],
                        ),
                        reverse=True,
                    )
                    partition_activities = self._read_indexed_activities(
                        event_path=event_path,
                        index_entries=index_entries[:limit],
                    )

                activities.extend(partition_activities)

        activities.sort(
            key=lambda activity: (
                activity.timestamp,
                activity.activity_id,
            ),
            reverse=True,
        )

        return activities[:limit]

    def _partition_root(self, scope: str, identity: str) -> Path:
        identity_key = hashlib.sha256(
            identity.encode("utf-8")
        ).hexdigest()

        return self._data_directory / scope / identity_key

    def _partition_paths(
        self,
        scope: str,
        identity: str,
        year: str,
        month: str,
    ) -> tuple[Path, Path]:
        root = self._partition_root(scope, identity)

        return (
            root / "events" / year / f"{month}.jsonl",
            root / "index" / year / f"{month}.jsonl",
        )

    @contextmanager
    def _partition_lock(
        self,
        scope: str,
        identity: str,
        year: str,
        month: str,
    ) -> Iterator[None]:
        """Serialize a partition across threads, instances and processes."""

        identity_key = hashlib.sha256(
            identity.encode("utf-8")
        ).hexdigest()

        lock_path = (
            self._lock_directory
            / f"{scope}-{identity_key}-{year}-{month}.lock"
        )
        lock_path.parent.mkdir(parents=True, exist_ok=True)

        lock_key = str(lock_path.resolve())

        with self._registry_guard:
            thread_lock = self._path_locks.setdefault(
                lock_key,
                RLock(),
            )

        with thread_lock:
            with lock_path.open("a+") as lock_file:
                fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)
                try:
                    yield
                finally:
                    fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)

    @staticmethod
    def _to_record(activity: Activity) -> dict[str, Any]:
        return {
            "activity_id": activity.activity_id,
            "owner_user_id": activity.owner_user_id,
            "actor_user_id": activity.actor_user_id,
            "type": activity.type,
            "title": activity.title,
            "description": activity.description,
            "timestamp": activity.timestamp.isoformat(),
            "data_model_id": activity.data_model_id,
            "job_id": activity.job_id,
            "metadata": activity.metadata or {},
        }

    @staticmethod
    def _append_index(
        index_path: Path,
        record: dict[str, Any],
    ) -> None:
        index_path.parent.mkdir(parents=True, exist_ok=True)

        payload = (
            json.dumps(record, separators=(",", ":")) + "\n"
        ).encode("utf-8")

        with index_path.open("ab") as index_file:
            index_file.write(payload)
            index_file.flush()
            os.fsync(index_file.fileno())

    def _ensure_index(
        self,
        event_path: Path,
        index_path: Path,
    ) -> None:
        """Rebuild an absent, incomplete or inconsistent index."""

        if not index_path.exists():
            self._rebuild_index(event_path, index_path)
            return

        event_size = event_path.stat().st_size

        try:
            expected_offset = 0

            with index_path.open("r", encoding="utf-8") as index_file:
                for line in index_file:
                    entry = json.loads(line)
                    offset = entry["offset"]
                    length = entry["length"]

                    if offset != expected_offset or length <= 0:
                        raise ValueError("Invalid activity index offsets.")

                    expected_offset += length

            if expected_offset != event_size:
                self._rebuild_index(event_path, index_path)

        except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError):
            self._rebuild_index(event_path, index_path)

    def _rebuild_index(
        self,
        event_path: Path,
        index_path: Path,
    ) -> None:
        """Reconstruct the index from authoritative event records."""

        index_path.parent.mkdir(parents=True, exist_ok=True)
        temporary_path = index_path.with_suffix(".tmp")

        offset = 0

        with event_path.open("rb") as event_file:
            with temporary_path.open("wb") as index_file:
                while True:
                    line = event_file.readline()
                    if not line:
                        break

                    if not line.endswith(b"\n"):
                        break

                    record = json.loads(line.decode("utf-8"))

                    entry = {
                        "activity_id": record["activity_id"],
                        "timestamp": record["timestamp"],
                        "offset": offset,
                        "length": len(line),
                    }

                    index_file.write(
                        (
                            json.dumps(entry, separators=(",", ":"))
                            + "\n"
                        ).encode("utf-8")
                    )
                    offset += len(line)

                index_file.flush()
                os.fsync(index_file.fileno())

        temporary_path.replace(index_path)

    @staticmethod
    def _repair_event_tail(event_path: Path) -> None:
        """Remove an incomplete final JSONL record after an interrupted write."""

        if not event_path.exists():
            return

        with event_path.open("r+b") as event_file:
            event_file.seek(0, os.SEEK_END)
            size = event_file.tell()

            if size == 0:
                return

            event_file.seek(-1, os.SEEK_END)
            if event_file.read(1) == b"\n":
                return

            event_file.seek(0)
            content = event_file.read()
            last_newline = content.rfind(b"\n")
            valid_size = last_newline + 1

            event_file.truncate(valid_size)
            event_file.flush()
            os.fsync(event_file.fileno())

    @staticmethod
    def _read_index_entries(index_path: Path) -> list[dict[str, Any]]:
        """Read lightweight index metadata without loading event records."""

        entries: list[dict[str, Any]] = []

        with index_path.open("r", encoding="utf-8") as index_file:
            for line in index_file:
                entries.append(json.loads(line))

        return entries

    def _read_indexed_activities(
        self,
        event_path: Path,
        index_entries: list[dict[str, Any]],
    ) -> list[Activity]:
        """Read only the event records selected by the activity index."""

        activities: list[Activity] = []

        with event_path.open("rb") as event_file:
            for entry in index_entries:
                event_file.seek(entry["offset"])
                record_bytes = event_file.read(entry["length"])
                record = json.loads(record_bytes.decode("utf-8"))

                if record["activity_id"] != entry["activity_id"]:
                    raise ValueError(
                        "Activity index does not match its event record."
                    )

                activities.append(self._to_activity(record))

        return activities

    @staticmethod
    def _to_activity(record: dict[str, Any]) -> Activity:
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
