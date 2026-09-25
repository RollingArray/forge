"""
File: data_model_repository.py
Purpose: Repository contract for FORGE data models.

Author: Ranjoy Sen
Email: ranjoy.sen@collins.com
"""

from abc import ABC, abstractmethod

from app.interfaces.data_model import DataModel


class DataModelRepository(ABC):
    """Persistence contract for FORGE data models."""

    @abstractmethod
    def create(
        self,
        owner_user_id: str,
        name: str,
        description: str,
        color: str,
        tags: list[str],
    ) -> DataModel:
        """Create and persist a data model."""
        raise NotImplementedError

    @abstractmethod
    def get_by_owner_user_id(
        self,
        owner_user_id: str,
    ) -> list[DataModel]:
        """Return data models owned by the specified user."""
        raise NotImplementedError

    @abstractmethod
    def update(
        self,
        data_model_id: str,
        owner_user_id: str,
        name: str,
        description: str,
        color: str,
        tags: list[str],
    ) -> DataModel | None:
        """Update a data model owned by the specified user."""
        raise NotImplementedError

    @abstractmethod
    def delete(
        self,
        data_model_id: str,
        owner_user_id: str,
    ) -> bool:
        """Delete a data model owned by the specified user."""
        raise NotImplementedError
