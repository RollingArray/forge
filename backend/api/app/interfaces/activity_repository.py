"""
File: activity_repository.py
Purpose: FORGE activity repository contract.

Author: Ranjoy Sen
Email: ranjoy.sen@collins.com
"""

from abc import ABC, abstractmethod

from app.interfaces.activity import Activity


class ActivityRepository(ABC):
    """Define persistence operations for FORGE activity events."""

    @abstractmethod
    def create(
        self,
        owner_user_id: str,
        actor_user_id: str,
        activity_type: str,
        title: str,
        description: str,
        data_model_id: str | None = None,
        job_id: str | None = None,
        metadata: dict | None = None,
    ) -> Activity:
        """Create and persist an activity event."""
        raise NotImplementedError

    @abstractmethod
    def get_recent_by_owner_user_id(
        self,
        owner_user_id: str,
        limit: int = 10,
    ) -> list[Activity]:
        """Return recent activity events for a workspace owner."""
        raise NotImplementedError
