"""
File: specification_service.py
Purpose: Business service for FORGE model specifications.

Author: Ranjoy Sen
Email: ranjoy.sen@collins.com
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from app.interfaces.data_model_repository import DataModelRepository
from app.interfaces.specification_repository import SpecificationRepository
from app.models.specification_entity_model import CreateEntityRequest
from app.constants.activity import ActivityType
from app.services.activity_service import ActivityService
from app.repositories.json_data_model_repository import (
    JsonDataModelRepository,
)
from app.repositories.json_specification_repository import (
    JsonSpecificationRepository,
)


class SpecificationService:
    """Provide business operations for FORGE specifications."""

    def __init__(
        self,
        data_model_repository: DataModelRepository | None = None,
        specification_repository: SpecificationRepository | None = None,
        activity_service: ActivityService | None = None,
    ) -> None:
        self._data_model_repository = (
            data_model_repository
            if data_model_repository is not None
            else JsonDataModelRepository()
        )
        self._specification_repository = (
            specification_repository
            if specification_repository is not None
            else JsonSpecificationRepository()
        )
        self._activity_service = (
            activity_service
            if activity_service is not None
            else ActivityService()
        )

    def get_specification(
        self,
        data_model_id: str,
    ) -> dict[str, Any] | None:
        """Return the canonical specification for a Data Model."""

        data_model = self._data_model_repository.get_by_id_any(
            data_model_id=data_model_id,
        )

        if data_model is None:
            return None

        return self._specification_repository.get_or_create(
            data_model_id=data_model_id,
            model_name=data_model.name,
            model_description=data_model.description,
        )

    def create_entity(
        self,
        data_model_id: str,
        actor_user_id: str,
        request: CreateEntityRequest,
    ) -> dict[str, Any] | None:
        """Create and persist an entity in the canonical specification."""

        specification = self.get_specification(
            data_model_id=data_model_id,
        )

        if specification is None:
            return None

        entities = specification.setdefault(
            "entities",
            [],
        )

        if any(
            entity.get("name") == request.name
            for entity in entities
        ):
            raise ValueError(
                f"Entity already exists: {request.name}"
            )

        entity: dict[str, Any] = {
            "name": request.name,
            "fields": [],
        }

        if request.population is not None:
            entity["population"] = {
                "count": request.population.count,
            }
        else:
            entity["population"] = {}

        candidate = deepcopy(specification)
        candidate["entities"].append(entity)

        self._specification_repository.save(
            data_model_id=data_model_id,
            specification=candidate,
        )

        data_model = self._data_model_repository.get_by_id_any(
            data_model_id=data_model_id,
        )

        if data_model is not None:
            self._activity_service.record(
                owner_user_id=data_model.owner_user_id,
                actor_user_id=actor_user_id,
                activity_type=ActivityType.ENTITY_ADDED,
                title="Entity added",
                description=f"Added entity '{request.name}'",
                data_model_id=data_model_id,
                metadata={
                    "entity_name": request.name,
                    "population": (
                        request.population.count
                        if request.population is not None
                        else None
                    ),
                },
            )

        return entity


    def update_entity_population(
        self,
        data_model_id: str,
        actor_user_id: str,
        entity_name: str,
        count: int,
    ) -> dict[str, Any] | None:
        """Update an entity population using UPDATE_POPULATION semantics."""

        specification = self.get_specification(
            data_model_id=data_model_id,
        )

        if specification is None:
            return None

        entities = specification.setdefault("entities", [])

        entity = next(
            (
                item
                for item in entities
                if item.get("name") == entity_name
            ),
            None,
        )

        if entity is None:
            raise ValueError(
                f"Unknown entity: {entity_name}"
            )

        candidate = deepcopy(specification)

        updated_entity = next(
            item
            for item in candidate["entities"]
            if item.get("name") == entity_name
        )

        updated_entity["population"] = {
            "count": count,
        }

        self._specification_repository.save(
            data_model_id=data_model_id,
            specification=candidate,
        )

        data_model = self._data_model_repository.get_by_id_any(
            data_model_id=data_model_id,
        )

        if data_model is not None:
            self._activity_service.record(
                owner_user_id=data_model.owner_user_id,
                actor_user_id=actor_user_id,
                activity_type=ActivityType.ENTITY_UPDATED,
                title="Entity updated",
                description=(
                    f"Updated population for entity '{entity_name}'"
                ),
                data_model_id=data_model_id,
                metadata={
                    "entity_name": entity_name,
                    "operation": "UPDATE_POPULATION",
                    "population": count,
                },
            )

        return updated_entity

    def delete_entity(
        self,
        data_model_id: str,
        actor_user_id: str,
        entity_name: str,
    ) -> bool:
        """Delete an entity when no specification references depend on it."""

        specification = self.get_specification(
            data_model_id=data_model_id,
        )

        if specification is None:
            return False

        entities = specification.setdefault("entities", [])

        entity = next(
            (
                item
                for item in entities
                if item.get("name") == entity_name
            ),
            None,
        )

        if entity is None:
            return False

        relationships = specification.get(
            "relationships",
            [],
        )

        for relationship in relationships:
            for key in ("source", "target"):
                reference = relationship.get(key)

                if (
                    isinstance(reference, str)
                    and reference.split(".", 1)[0] == entity_name
                ):
                    raise ValueError(
                        f"Entity '{entity_name}' is referenced by "
                        "a relationship."
                    )

        foreign_keys = specification.get(
            "foreign_keys",
            [],
        )

        for foreign_key in foreign_keys:
            for key in ("source", "target"):
                endpoint = foreign_key.get(key, {})

                if (
                    isinstance(endpoint, dict)
                    and endpoint.get("entity") == entity_name
                ):
                    raise ValueError(
                        f"Entity '{entity_name}' is referenced by "
                        "a foreign key."
                    )

        dependencies = specification.get(
            "dependencies",
            [],
        )

        for dependency in dependencies:
            references = [
                dependency.get("target"),
                *dependency.get("source_fields", []),
            ]

            if any(
                isinstance(reference, str)
                and reference.split(".", 1)[0] == entity_name
                for reference in references
            ):
                raise ValueError(
                    f"Entity '{entity_name}' is referenced by "
                    "a dependency."
                )

        candidate = deepcopy(specification)

        candidate["entities"] = [
            item
            for item in candidate["entities"]
            if item.get("name") != entity_name
        ]

        self._specification_repository.save(
            data_model_id=data_model_id,
            specification=candidate,
        )

        data_model = self._data_model_repository.get_by_id_any(
            data_model_id=data_model_id,
        )

        if data_model is not None:
            self._activity_service.record(
                owner_user_id=data_model.owner_user_id,
                actor_user_id=actor_user_id,
                activity_type=ActivityType.ENTITY_DELETED,
                title="Entity deleted",
                description=f"Deleted entity '{entity_name}'",
                data_model_id=data_model_id,
                metadata={
                    "entity_name": entity_name,
                },
            )

        return True
