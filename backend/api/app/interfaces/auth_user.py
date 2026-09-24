"""
File: auth_user.py
Purpose: Authenticated FORGE user contract.

Author: Ranjoy Sen
Email: ranjoy.sen@collins.com
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class AuthUser:
    """Authenticated FORGE user identity."""

    user_id: str
    email: str
    display_name: str
