"""
File: favorite_repository.py
Purpose: Persistence contract for user favorites.
"""

from abc import ABC, abstractmethod

from app.interfaces.favorite import Favorite, FavoriteResourceType


class FavoriteRepository(ABC):
    """Persistence contract for user favorites."""

    @abstractmethod
    def create(
        self,
        user_id: str,
        resource_type: FavoriteResourceType,
        data_model_id: str,
        job_id: str | None = None,
    ) -> Favorite:
        """Create a favorite or return the user's existing matching favorite."""
        raise NotImplementedError

    @abstractmethod
    def get_by_user_id(self, user_id: str) -> list[Favorite]:
        """Return favorites belonging to the specified user."""
        raise NotImplementedError

    @abstractmethod
    def delete(self, favorite_id: str, user_id: str) -> bool:
        """Delete a favorite only when it belongs to the specified user."""
        raise NotImplementedError
