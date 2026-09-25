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
    def get_by_id(self, user_id: str) -> AuthUser | None:
        """Return an existing FORGE user by stable user ID."""
        raise NotImplementedError

    @abstractmethod
    def create(self, email: str, display_name: str) -> AuthUser:
        """Create and persist a new FORGE user."""
        raise NotImplementedError

    @abstractmethod
    def search(
        self,
        query: str,
        limit: int = 10,
    ) -> list[AuthUser]:
        """Search existing FORGE users by email or display name."""
        raise NotImplementedError
