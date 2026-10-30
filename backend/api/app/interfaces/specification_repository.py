"""
File: specification_repository.py
Purpose: Repository contract for FORGE model specifications.

Author: Ranjoy Sen
Email: ranjoy.sen@collins.com
"""

from abc import ABC, abstractmethod
from typing import Any
from contextlib import AbstractContextManager


class SpecificationRepository(ABC):
    """Persistence contract for FORGE model specifications."""

    @abstractmethod
    def get_or_create(
        self,
        data_model_id: str,
        model_name: str,
        model_description: str,
    ) -> dict[str, Any]:
        """Return the canonical specification, creating it when absent."""
        raise NotImplementedError


    def transaction(
        self,
        data_model_id: str,
    ) -> AbstractContextManager[None]:
        """Serialize a complete read-modify-write operation."""
        raise NotImplementedError

    def read(
        self,
        data_model_id: str,
    ) -> dict[str, Any] | None:
        """Read without creating a missing specification."""
        raise NotImplementedError

    def save_if_revision(
        self,
        data_model_id: str,
        expected_revision: str,
        specification: dict[str, Any],
        missing_specification: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Save only if the current canonical revision matches."""
        raise NotImplementedError

    @abstractmethod
    def save(
        self,
        data_model_id: str,
        specification: dict[str, Any],
    ) -> dict[str, Any]:
        """Persist and return the canonical specification."""
        raise NotImplementedError
