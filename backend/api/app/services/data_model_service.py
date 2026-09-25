"""
File: data_model_service.py
Purpose: Application service for FORGE data models.

Author: Ranjoy Sen
Email: ranjoy.sen@collins.com
"""

from app.constants.activity import ActivityType
from app.interfaces.data_model import DataModel
from app.interfaces.data_model_access_repository import DataModelAccessRepository
from app.interfaces.data_model_repository import DataModelRepository
from app.repositories.json_data_model_repository import (
    JsonDataModelRepository,
)
from app.repositories.json_data_model_access_repository import JsonDataModelAccessRepository
from app.services.activity_service import ActivityService


class DataModelService:
    """Coordinate FORGE data model operations."""

    def __init__(
        self,
        data_model_repository: DataModelRepository | None = None,
        data_model_access_repository: DataModelAccessRepository | None = None,
        activity_service: ActivityService | None = None,
    ) -> None:
        self._data_model_repository = (
            data_model_repository
            if data_model_repository is not None
            else JsonDataModelRepository()
        )
        self._data_model_access_repository = (
            data_model_access_repository
            if data_model_access_repository is not None
            else JsonDataModelAccessRepository()
        )
        self._activity_service = (
            activity_service
            if activity_service is not None
            else ActivityService()
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

        data_model = self._data_model_repository.create(
            owner_user_id=owner_user_id,
            name=normalized_name,
            description=normalized_description,
            color=color,
            tags=normalized_tags,
        )

        self._activity_service.record(
            owner_user_id=owner_user_id,
            actor_user_id=owner_user_id,
            activity_type=ActivityType.DATA_MODEL_CREATED,
            title="Data Model created",
            description=f"Created Data Model '{data_model.name}'",
            data_model_id=data_model.data_model_id,
            metadata={
                "data_model_name": data_model.name,
            },
        )

        return data_model

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

        existing_data_model = self._data_model_repository.get_by_id(
            data_model_id=data_model_id,
            owner_user_id=owner_user_id,
        )

        data_model = self._data_model_repository.update(
            data_model_id=data_model_id,
            owner_user_id=owner_user_id,
            name=normalized_name,
            description=normalized_description,
            color=color,
            tags=normalized_tags,
        )

        if data_model is not None:
            changes: list[dict[str, object]] = []

            if (
                existing_data_model is not None
                and existing_data_model.name != data_model.name
            ):
                changes.append(
                    {
                        "field": "name",
                        "from": existing_data_model.name,
                        "to": data_model.name,
                    }
                )

            if (
                existing_data_model is not None
                and existing_data_model.description
                != data_model.description
            ):
                changes.append(
                    {
                        "field": "description",
                        "from": existing_data_model.description,
                        "to": data_model.description,
                    }
                )

            if (
                existing_data_model is not None
                and existing_data_model.color != data_model.color
            ):
                changes.append(
                    {
                        "field": "color",
                        "from": existing_data_model.color,
                        "to": data_model.color,
                    }
                )

            if (
                existing_data_model is not None
                and existing_data_model.tags != data_model.tags
            ):
                changes.append(
                    {
                        "field": "tags",
                        "from": existing_data_model.tags,
                        "to": data_model.tags,
                    }
                )

            metadata: dict[str, object] = {
                "data_model_name": data_model.name,
                "changes": changes,
            }

            if len(changes) == 1 and changes[0]["field"] == "name":
                title = "Renamed Data Model"
                description = (
                    f"Renamed Data Model "
                    f"'{changes[0]['from']}' to '{changes[0]['to']}'"
                )
            elif changes:
                field_labels = {
                    "name": "name",
                    "description": "description",
                    "color": "color",
                    "tags": "tags",
                }

                changed_fields = [
                    field_labels[str(change["field"])]
                    for change in changes
                ]

                if len(changed_fields) == 1:
                    changed_summary = changed_fields[0]
                elif len(changed_fields) == 2:
                    changed_summary = (
                        f"{changed_fields[0]} and {changed_fields[1]}"
                    )
                else:
                    changed_summary = (
                        ", ".join(changed_fields[:-1])
                        + f", and {changed_fields[-1]}"
                    )

                title = "Updated Data Model"
                description = (
                    f"Updated Data Model '{data_model.name}': "
                    f"{changed_summary} changed"
                )
            else:
                title = "Updated Data Model"
                description = (
                    f"Updated Data Model '{data_model.name}'"
                )

            self._activity_service.record(
                owner_user_id=owner_user_id,
                actor_user_id=owner_user_id,
                activity_type=ActivityType.DATA_MODEL_UPDATED,
                title=title,
                description=description,
                data_model_id=data_model.data_model_id,
                metadata=metadata,
            )

        return data_model

    def delete_data_model(
        self,
        data_model_id: str,
        owner_user_id: str,
    ) -> bool:
        """Delete a FORGE data model owned by the specified user."""

        data_model = self._data_model_repository.get_by_id(
            data_model_id=data_model_id,
            owner_user_id=owner_user_id,
        )

        deleted = self._data_model_repository.delete(
            data_model_id=data_model_id,
            owner_user_id=owner_user_id,
        )

        if deleted:
            data_model_name = (
                data_model.name
                if data_model is not None
                else data_model_id
            )

            self._activity_service.record(
                owner_user_id=owner_user_id,
                actor_user_id=owner_user_id,
                activity_type=ActivityType.DATA_MODEL_DELETED,
                title="Data Model deleted",
                description=f"Deleted Data Model '{data_model_name}'",
                data_model_id=data_model_id,
                metadata={
                    "data_model_name": data_model_name,
                },
            )

        return deleted

    def get_data_models(
        self,
        owner_user_id: str,
    ) -> list[DataModel]:
        """Return data models owned by or shared with the specified user."""

        owned_models = self._data_model_repository.get_by_owner_user_id(
            owner_user_id=owner_user_id,
        )

        access_records = self._data_model_access_repository.get_by_user_id(
            user_id=owner_user_id,
        )

        shared_models: list[DataModel] = []

        for access in access_records:
            data_model = self._data_model_repository.get_by_id_any(
                data_model_id=access.data_model_id,
            )

            if data_model is not None:
                shared_models.append(data_model)

        data_models_by_id = {
            data_model.data_model_id: data_model
            for data_model in owned_models
        }

        for data_model in shared_models:
            data_models_by_id[data_model.data_model_id] = data_model

        return sorted(
            data_models_by_id.values(),
            key=lambda data_model: data_model.updated_at,
            reverse=True,
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
