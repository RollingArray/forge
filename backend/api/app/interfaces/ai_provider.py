"""
============================================================================
FORGE — Framework for Observed Rules, Generation & Engineered Data
============================================================================

File: ai_provider.py
Purpose: Defines the contract for FORGE AI/LLM providers.

Author: Ranjoy Sen
Email: ranjoy.sen@collins.com

============================================================================
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True)
class AIProviderStatus:
    """Describes the current availability of an AI provider."""

    available: bool
    provider: str
    mode: str
    model: str | None
    message: str


@dataclass(frozen=True)
class AIDataModelProposal:
    """Represents an AI-generated proposal for a FORGE Data Model."""

    name: str
    description: str
    suggested_tags: list[str]
    reasoning: str


@dataclass(frozen=True)
class AISemanticPreview:
    """Represents an AI-generated semantic field preview."""

    status: str
    message: str
    preview_values: list[str]


class AIProvider(ABC):
    """Contract implemented by FORGE AI/LLM providers."""

    @abstractmethod
    def get_status(self) -> AIProviderStatus:
        """Return the current provider availability status."""
        raise NotImplementedError

    @abstractmethod
    def suggest_data_model(
        self,
        prompt: str,
    ) -> AIDataModelProposal:
        """Generate a structured Data Model proposal from user intent."""
        raise NotImplementedError

    @abstractmethod
    def preview_semantic_values(
        self,
        description: str,
    ) -> AISemanticPreview:
        """Generate representative semantic field values for preview."""
        raise NotImplementedError
