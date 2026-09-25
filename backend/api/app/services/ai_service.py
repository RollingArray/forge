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
