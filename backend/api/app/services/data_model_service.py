"""
File: data_model_service.py
Purpose: Application service for FORGE data models.

Author: Ranjoy Sen
Email: ranjoy.sen@collins.com
"""

import logging
from copy import deepcopy

from app.constants.activity import ActivityType
from app.interfaces.data_model import DataModel
from app.interfaces.data_model_access_repository import DataModelAccessRepository
from app.interfaces.data_model_repository import DataModelRepository
from app.repositories.json_data_model_repository import (
    JsonDataModelRepository,
)
from app.repositories.json_data_model_access_repository import JsonDataModelAccessRepository
from app.services.activity_service import ActivityService
from app.services.data_model_access_service import DataModelAccessService
from app.repositories.json_specification_repository import JsonSpecificationRepository


logger = logging.getLogger(__name__)


class DataModelService:
    """Coordinate FORGE data model operations."""

    def __init__(
        self,
        data_model_repository: DataModelRepository | None = None,
        data_model_access_repository: DataModelAccessRepository | None = None,
        activity_service: ActivityService | None = None,
        data_model_access_service: DataModelAccessService | None = None,
        specification_repository: JsonSpecificationRepository | None = None,
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
        self._data_model_access_service = (
            data_model_access_service
            if data_model_access_service is not None
            else DataModelAccessService(
                data_model_repository=self._data_model_repository,
                access_repository=self._data_model_access_repository,
                activity_service=self._activity_service,
            )
        )
        self._specification_repository = (
            specification_repository
            if specification_repository is not None
            else JsonSpecificationRepository()
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

    def duplicate_data_model(
        self,
        data_model_id: str,
        owner_user_id: str,
    ) -> DataModel | None:
        """Duplicate an owner's model and its canonical specification."""

        source = self._data_model_repository.get_by_id(
            data_model_id=data_model_id,
            owner_user_id=owner_user_id,
        )
        if source is None:
            return None

        source_specification = self._specification_repository.read(
            data_model_id
        )
        if source_specification is None:
            return None

        source_model = source_specification.get("model")
        if not isinstance(source_model, dict):
            raise ValueError(
                "The source specification has no valid model object."
            )

        # Preserve the complete original ID while keeping the card name
        # within the existing 120-character API limit.
        suffix = f" - {source.data_model_id}"
        prefix = "Copy of "
        available_name_length = 120 - len(prefix) - len(suffix)
        copied_source_name = source.name[:available_name_length].rstrip()
        duplicate_name = f"{prefix}{copied_source_name}{suffix}"

        copied_specification = deepcopy(source_specification)
        copied_specification["model"]["name"] = duplicate_name

        duplicate = self._data_model_repository.create(
            owner_user_id=owner_user_id,
            name=duplicate_name,
            description=source.description,
            color=source.color,
            tags=list(source.tags),
        )

        try:
            self._specification_repository.save(
                duplicate.data_model_id,
                copied_specification,
            )
        except Exception:
            # Roll back both sides of the new model. Repository cleanup
            # removes only the canonical specification and temporary file.
            try:
                self._specification_repository.delete(
                    duplicate.data_model_id
                )
            finally:
                self._data_model_repository.delete(
                    data_model_id=duplicate.data_model_id,
                    owner_user_id=owner_user_id,
                )
            raise

        try:
            self._activity_service.record(
                owner_user_id=owner_user_id,
                actor_user_id=owner_user_id,
                activity_type=ActivityType.DATA_MODEL_DUPLICATED,
                title="Data Model duplicated",
                description=(
                    f"Duplicated Data Model '{source.name}' "
                    f"as '{duplicate.name}'"
                ),
                data_model_id=duplicate.data_model_id,
                metadata={
                    "data_model_name": duplicate.name,
                    "source_data_model_id": source.data_model_id,
                    "source_data_model_name": source.name,
                },
            )
        except Exception:
            # The model and specification are already safely persisted.
            # Activity history must not make a successful copy appear failed.
            logger.exception(
                "Failed to record duplication activity for Data Model %s",
                duplicate.data_model_id,
            )

        return duplicate

    def update_data_model(
        self,
        data_model_id: str,
        actor_user_id: str,
        name: str,
        description: str,
        color: str,
        tags: list[str],
    ) -> DataModel | None:
        """Update a FORGE data model when the actor has edit permission."""

        if not self._data_model_access_service.can_edit(
            data_model_id=data_model_id,
            user_id=actor_user_id,
        ):
            return None

        existing_data_model = self._data_model_repository.get_by_id_any(
            data_model_id=data_model_id,
        )

        if existing_data_model is None:
            return None

        owner_user_id = existing_data_model.owner_user_id

        normalized_name = name.strip()
        normalized_description = description.strip()
        normalized_tags = self._normalize_tags(tags)

        if not normalized_name:
            normalized_name = "Untitled Data Model"

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
            elif len(changes) == 1 and changes[0]["field"] == "description":
                title = "Updated Data Model description"
                description = (
                    f"Updated the description of Data Model "
                    f"'{data_model.name}'"
                )
            elif len(changes) == 1 and changes[0]["field"] == "tags":
                previous_tags = {
                    str(tag).lower(): str(tag)
                    for tag in changes[0]["from"]
                }
                current_tags = {
                    str(tag).lower(): str(tag)
                    for tag in changes[0]["to"]
                }

                added_tags = [
                    current_tags[key]
                    for key in current_tags
                    if key not in previous_tags
                ]
                removed_tags = [
                    previous_tags[key]
                    for key in previous_tags
                    if key not in current_tags
                ]

                if added_tags and removed_tags:
                    title = "Updated Data Model tags"
                    description = (
                        f"Updated tags for Data Model "
                        f"'{data_model.name}': "
                        f"added {', '.join(repr(tag) for tag in added_tags)} "
                        f"and removed {', '.join(repr(tag) for tag in removed_tags)}"
                    )
                elif added_tags:
                    title = "Updated Data Model tags"
                    description = (
                        f"Added {', '.join(repr(tag) for tag in added_tags)} "
                        f"to Data Model '{data_model.name}'"
                    )
                elif removed_tags:
                    title = "Updated Data Model tags"
                    description = (
                        f"Removed {', '.join(repr(tag) for tag in removed_tags)} "
                        f"from Data Model '{data_model.name}'"
                    )
                else:
                    title = "Updated Data Model tags"
                    description = (
                        f"Updated tags for Data Model "
                        f"'{data_model.name}'"
                    )
            elif len(changes) == 1 and changes[0]["field"] == "color":
                title = "Changed Data Model appearance"
                description = (
                    f"Changed the appearance of Data Model "
                    f"'{data_model.name}'"
                )
            elif changes:
                field_labels = {
                    "name": "name",
                    "description": "description",
                    "color": "appearance",
                    "tags": "tags",
                }

                changed_fields = [
                    field_labels[str(change["field"])]
                    for change in changes
                ]

                if len(changed_fields) == 2:
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
                    f"Updated {changed_summary} for Data Model "
                    f"'{data_model.name}'"
                )
            else:
                title = "Updated Data Model"
                description = (
                    f"Updated Data Model '{data_model.name}'"
                )

            self._activity_service.record(
                owner_user_id=owner_user_id,
                actor_user_id=actor_user_id,
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

    def get_data_model_counts(
        self,
        data_model: DataModel,
    ) -> tuple[int, int]:
        """Return entity and relationship counts from the canonical specification."""

        specification = self._specification_repository.get_or_create(
            data_model_id=data_model.data_model_id,
            model_name=data_model.name,
            model_description=data_model.description,
        )

        entities = specification.get("entities", [])
        relationships = specification.get("relationships", [])

        return (
            len(entities) if isinstance(entities, list) else 0,
            len(relationships) if isinstance(relationships, list) else 0,
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
