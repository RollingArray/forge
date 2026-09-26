"""
============================================================================
FORGE — Framework for Observed Rules, Generation & Engineered Data
============================================================================

File: ai_service.py
Purpose: Orchestrates FORGE AI provider capabilities.

Author: Ranjoy Sen
Email: ranjoy.sen@collins.com

============================================================================
"""

from app.interfaces.ai_provider import (
    AIDataModelProposal,
    AIFieldProposal,
    AISemanticPreview,
    AIProvider,
    AIProviderStatus,
)


class AIService:
    """Provides application-level AI capabilities."""

    def __init__(self, provider: AIProvider) -> None:
        self._provider = provider

    def get_capabilities(self) -> AIProviderStatus:
        """Return the current AI capability status."""

        return self._provider.get_status()

    def suggest_data_model(
        self,
        prompt: str,
    ) -> AIDataModelProposal:
        """Generate a Data Model proposal from user intent."""

        return self._provider.suggest_data_model(prompt)


    def preview_semantic_values(
        self,
        description: str,
    ) -> AISemanticPreview:
        """Generate representative semantic field values for preview."""

        return self._provider.preview_semantic_values(description)

    def propose_field(
        self,
        mode: str,
        entity_name: str,
        request: str,
        existing_field: dict[str, object] | None = None,
    ) -> AIFieldProposal:
        """Generate a structured FORGE field proposal."""

        return self._provider.propose_field(
            mode=mode,
            entity_name=entity_name,
            request=request,
            existing_field=existing_field,
        )
