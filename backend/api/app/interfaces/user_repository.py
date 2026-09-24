"""
File: user_repository.py
Purpose: FORGE user repository contract.

Author: Ranjoy Sen
Email: ranjoy.sen@collins.com
"""

from abc import ABC, abstractmethod

from app.interfaces.auth_user import AuthUser


class UserRepository(ABC):
    """Contract for persistent FORGE user management."""

    @abstractmethod
    def get_by_email(self, email: str) -> AuthUser | None:
        """Return the FORGE user associated with an email address."""
        raise NotImplementedError

    @abstractmethod
    def create(self, email: str, display_name: str) -> AuthUser:
        """Create and persist a new FORGE user."""
        raise NotImplementedError
