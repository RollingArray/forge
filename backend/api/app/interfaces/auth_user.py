"""
File: auth_user.py
Purpose: Authenticated FORGE user identity.
"""

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class AuthUser:
    """Stable FORGE identity with optional corporate profile data."""

    user_id: str
    email: str
    display_name: str
    employee_id: str | None = None
    profile: dict[str, Any] | None = None
