"""
File: activity_service.py
Purpose: FORGE activity business service.

Author: Ranjoy Sen
Email: ranjoy.sen@collins.com
"""

from typing import Any

from app.interfaces.activity import Activity
from app.interfaces.activity_repository import ActivityRepository
from app.repositories.json_activity_repository import (
    JsonActivityRepository,
)


class ActivityService:
    """Provide business operations for FORGE activity events."""

    def __init__(
        self,
        activity_repository: ActivityRepository | None = None,
    ) -> None:
        self._activity_repository = (
            activity_repository
            if activity_repository is not None
            else JsonActivityRepository()
        )

    def record(
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
        """Record a new FORGE activity event."""

        return self._activity_repository.create(
            owner_user_id=owner_user_id,
            actor_user_id=actor_user_id,
            activity_type=activity_type,
            title=title,
            description=description,
            data_model_id=data_model_id,
            job_id=job_id,
            metadata=metadata,
        )

    def get_recent(
        self,
        owner_user_id: str,
        limit: int = 10,
    ) -> list[Activity]:
        """Return recent activity events for a workspace owner."""

        return self._activity_repository.get_recent_by_owner_user_id(
            owner_user_id=owner_user_id,
            limit=limit,
        )
