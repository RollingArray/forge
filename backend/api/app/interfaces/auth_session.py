"""
============================================================================
FORGE — Framework for Observed Rules, Generation & Engineered Data
============================================================================

File: auth_session.py
Purpose: Authenticated FORGE session contract.

Author: Ranjoy Sen
Email: ranjoy.sen@collins.com

============================================================================
"""

from dataclasses import dataclass

from app.interfaces.auth_user import AuthUser


@dataclass(frozen=True)
class AuthSession:
    """Authenticated FORGE session returned after successful login."""

    access_token: str
    token_type: str
    user: AuthUser
