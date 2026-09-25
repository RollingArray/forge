"""
File: json_user_repository.py
Purpose: JSON-backed FORGE user repository.

Author: Ranjoy Sen
Email: ranjoy.sen@collins.com
"""

import json
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock
from uuid import uuid4

from app.interfaces.auth_user import AuthUser
from app.interfaces.user_repository import UserRepository


class JsonUserRepository(UserRepository):
    """Persist FORGE users in a local JSON store."""

    def __init__(self) -> None:
        self._file_path = (
            Path(__file__).resolve().parents[2]
            / "data"
            / "users.json"
        )
        self._lock = Lock()

        self._ensure_store()

    def get_by_email(self, email: str) -> AuthUser | None:
        """Return an existing FORGE user by normalized email."""
        normalized_email = self._normalize_email(email)

        with self._lock:
            data = self._read_data()

        for record in data["users"]:
            if record["email"] == normalized_email:
                return self._to_auth_user(record)

        return None

    def search(
        self,
        query: str,
        limit: int = 10,
    ) -> list[AuthUser]:
        """Search existing FORGE users by email or display name."""
        normalized_query = query.strip().lower()
        normalized_limit = max(1, min(limit, 50))

        if not normalized_query:
            return []

        with self._lock:
            data = self._read_data()

        matches = [
            self._to_auth_user(record)
            for record in data["users"]
            if (
                normalized_query in record["email"].lower()
                or normalized_query in record["display_name"].lower()
            )
        ]

        return matches[:normalized_limit]

    def create(self, email: str, display_name: str) -> AuthUser:
        """Create and persist a new FORGE user."""
        normalized_email = self._normalize_email(email)

        with self._lock:
            data = self._read_data()

            for record in data["users"]:
                if record["email"] == normalized_email:
                    return self._to_auth_user(record)

            user = AuthUser(
                user_id=str(uuid4()),
                email=normalized_email,
                display_name=display_name,
            )

            data["users"].append(
                {
                    "user_id": user.user_id,
                    "email": user.email,
                    "display_name": user.display_name,
                    "created_at": datetime.now(
                        timezone.utc
                    ).isoformat(),
                }
            )

            self._write_data(data)

        return user

    def _ensure_store(self) -> None:
        """Ensure the FORGE user repository storage exists."""
        self._file_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        if not self._file_path.exists():
            self._write_data({"users": []})

    def _read_data(self) -> dict:
        """Read the complete JSON user store."""
        self._ensure_store()

        with self._file_path.open(
            "r",
            encoding="utf-8",
        ) as file:
            return json.load(file)

    def _write_data(self, data: dict) -> None:
        """Write the JSON user store atomically."""
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
    def _normalize_email(email: str) -> str:
        """Normalize an email address for repository lookup."""
        return email.strip().lower()

    @staticmethod
    def _to_auth_user(record: dict) -> AuthUser:
        """Convert a persisted record into a FORGE user."""
        return AuthUser(
            user_id=record["user_id"],
            email=record["email"],
            display_name=record["display_name"],
        )
