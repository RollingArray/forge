"""
File: data_model_service.py
Purpose: Application service for FORGE data models.

Author: Ranjoy Sen
Email: ranjoy.sen@collins.com
"""

from app.interfaces.data_model import DataModel
from app.interfaces.data_model_repository import DataModelRepository
from app.repositories.json_data_model_repository import (
    JsonDataModelRepository,
)


class DataModelService:
    """Coordinate FORGE data model operations."""

    def __init__(
        self,
        data_model_repository: DataModelRepository | None = None,
    ) -> None:
        self._data_model_repository = (
            data_model_repository
            if data_model_repository is not None
            else JsonDataModelRepository()
        )

    def create_data_model(
        self,
        owner_user_id: str,
        name: str,
        description: str,
        color: str,
        tags: list[str],
    ) -> DataModel:
        """Create a new FORGE data model."""

        normalized_name = name.strip()
        normalized_description = description.strip()
        normalized_tags = self._normalize_tags(tags)

        if not normalized_name:
            normalized_name = "Untitled Data Model"

        return self._data_model_repository.create(
            owner_user_id=owner_user_id,
            name=normalized_name,
            description=normalized_description,
            color=color,
            tags=normalized_tags,
        )

    def update_data_model(
        self,
        data_model_id: str,
        owner_user_id: str,
        name: str,
        description: str,
        color: str,
        tags: list[str],
    ) -> DataModel | None:
        """Update a FORGE data model owned by the specified user."""

        normalized_name = name.strip()
        normalized_description = description.strip()
        normalized_tags = self._normalize_tags(tags)

        if not normalized_name:
            normalized_name = "Untitled Data Model"

        return self._data_model_repository.update(
            data_model_id=data_model_id,
            owner_user_id=owner_user_id,
            name=normalized_name,
            description=normalized_description,
            color=color,
            tags=normalized_tags,
        )

    def delete_data_model(
        self,
        data_model_id: str,
        owner_user_id: str,
    ) -> bool:
        """Delete a FORGE data model owned by the specified user."""

        return self._data_model_repository.delete(
            data_model_id=data_model_id,
            owner_user_id=owner_user_id,
        )

    def get_data_models(
        self,
        owner_user_id: str,
    ) -> list[DataModel]:
        """Return data models owned by the specified user."""

        return self._data_model_repository.get_by_owner_user_id(
            owner_user_id=owner_user_id,
        )

    @staticmethod
    def _normalize_tags(tags: list[str]) -> list[str]:
        """Normalize and deduplicate Data Model tags."""

        normalized_tags: list[str] = []

        for tag in tags:
            normalized_tag = tag.strip()

            if not normalized_tag:
                continue

            if normalized_tag.lower() in {
                existing.lower()
                for existing in normalized_tags
            }:
                continue

            normalized_tags.append(normalized_tag)

        return normalized_tags[:20]
