"""
File: session_model.py
Purpose: API models for FORGE sessions.

Author: Ranjoy Sen
Email: ranjoy.sen@collins.com
"""

from datetime import datetime

from pydantic import BaseModel, Field


class CreateSessionRequestModel(BaseModel):
    """Request to create a FORGE session."""

    name: str = Field(
        default="Untitled Session",
        min_length=1,
        max_length=120,
    )


class SessionModel(BaseModel):
    """API representation of a FORGE session."""

    session_id: str
    owner_user_id: str
    name: str
    status: str
    created_at: datetime
    updated_at: datetime
