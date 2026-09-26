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
