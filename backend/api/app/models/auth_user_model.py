"""
File: auth_user_model.py
Purpose: Pydantic model for an authenticated FORGE user.
"""

from typing import Any

from pydantic import BaseModel, ConfigDict


class AuthUserModel(BaseModel):
    """HTTP response model representing an authenticated FORGE user."""

    model_config = ConfigDict(
        populate_by_name=True,
        alias_generator=lambda field_name: {
            "user_id": "userId",
            "display_name": "displayName",
            "employee_id": "employeeId",
        }.get(field_name, field_name),
    )

    user_id: str
    email: str
    display_name: str
    employee_id: str | None = None
    profile: dict[str, Any] | None = None
