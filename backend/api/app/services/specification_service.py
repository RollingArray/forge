"""
File: specification_service.py
Purpose: Application service for FORGE model specifications.

Author: Ranjoy Sen
Email: ranjoy.sen@collins.com
"""

from __future__ import annotations

from typing import Any

from app.interfaces.data_model_repository import DataModelRepository
from app.repositories.json_data_model_repository import (
    JsonDataModelRepository,
)
from app.repositories.json_specification_repository import (
    JsonSpecificationRepository,
)


class SpecificationService:
    """Coordinate access to canonical FORGE specifications."""

    def __init__(
        self,
        data_model_repository: DataModelRepository | None = None,
        specification_repository: JsonSpecificationRepository | None = None,
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

    def get_specification(
        self,
        data_model_id: str,
    ) -> dict[str, Any] | None:
        """Return or initialize the specification for a Data Model."""

        data_model = self._data_model_repository.get_by_id_any(
            data_model_id=data_model_id,
        )

        if data_model is None:
            return None

        return self._specification_repository.get_or_create(
            data_model_id=data_model.data_model_id,
            model_name=data_model.name,
            model_description=data_model.description,
        )
