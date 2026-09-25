"""
File: activity.py
Purpose: FORGE activity domain contract.

Author: Ranjoy Sen
Email: ranjoy.sen@collins.com
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Any


@dataclass(frozen=True)
class Activity:
    """Represent a persisted FORGE activity event."""

    activity_id: str
    owner_user_id: str
    actor_user_id: str
    type: str
    title: str
    description: str
    timestamp: datetime
    data_model_id: str | None = None
    job_id: str | None = None
    metadata: dict[str, Any] | None = None
