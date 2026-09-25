"""
File: data_model_access_repository.py
Purpose: Repository contract for FORGE data model access.

Author: Ranjoy Sen
Email: ranjoy.sen@collins.com
"""

from abc import ABC, abstractmethod

from app.constants.data_model_access import DataModelAccessRole
from app.interfaces.data_model_access import DataModelAccess


class DataModelAccessRepository(ABC):
    """Persistence contract for FORGE data model access."""

    @abstractmethod
    def grant_access(
        self,
        data_model_id: str,
        user_id: str,
        role: DataModelAccessRole,
    ) -> DataModelAccess:
        """Grant access to a user for a data model."""
        raise NotImplementedError

    @abstractmethod
    def get_by_data_model_id(
        self,
        data_model_id: str,
    ) -> list[DataModelAccess]:
        """Return all access records for a data model."""
        raise NotImplementedError

    @abstractmethod
    def get_by_user_id(
        self,
        user_id: str,
    ) -> list[DataModelAccess]:
        """Return all data model access records for a user."""
        raise NotImplementedError

    @abstractmethod
    def get_access(
        self,
        data_model_id: str,
        user_id: str,
    ) -> DataModelAccess | None:
        """Return a user's access to a data model."""
        raise NotImplementedError

    @abstractmethod
    def update_role(
        self,
        data_model_id: str,
        user_id: str,
        role: DataModelAccessRole,
    ) -> DataModelAccess | None:
        """Update a user's role for a data model."""
        raise NotImplementedError

    @abstractmethod
    def revoke_access(
        self,
        data_model_id: str,
        user_id: str,
    ) -> bool:
        """Revoke a user's access to a data model."""
        raise NotImplementedError
