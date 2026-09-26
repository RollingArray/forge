"""
File: specification_repository.py
Purpose: Repository contract for FORGE model specifications.

Author: Ranjoy Sen
Email: ranjoy.sen@collins.com
"""

from abc import ABC, abstractmethod
from typing import Any


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

    @abstractmethod
    def save(
        self,
        data_model_id: str,
        specification: dict[str, Any],
    ) -> dict[str, Any]:
        """Persist and return the canonical specification."""
        raise NotImplementedError
