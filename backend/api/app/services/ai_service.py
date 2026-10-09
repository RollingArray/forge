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

from typing import Callable

from app.interfaces.ai_provider import (
    AIDataModelProposal,
    AIEntityProposal,
    AIConstraintProposal,
    AIForeignKeyProposal,
    AIFieldProposal,
    AIIdentityProposal,
    AIRelationshipProposal,
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

    def propose_entity(self, prompt: str) -> AIEntityProposal:
        """Generate an entity proposal without persisting it."""

        return self._provider.propose_entity(prompt)

    def suggest_data_model(
        self,
        prompt: str,
    ) -> AIDataModelProposal:
        """Generate a Data Model proposal from user intent."""

        return self._provider.suggest_data_model(prompt)

    def generate_semantic_values(
        self,
        description: str,
        mode: str,
        count: int,
        on_call_completed: Callable[[int, int, float, bool], None] | None = None,
    ) -> list[str]:
        """Generate semantic values for production data generation."""

        return self._provider.generate_semantic_values(
            description=description,
            mode=mode,
            count=count,
            on_call_completed=on_call_completed,
        )


    def preview_semantic_values(
        self,
        description: str,
    ) -> AISemanticPreview:
        """Generate representative semantic field values for preview."""

        return self._provider.preview_semantic_values(description)

    def propose_identity(
        self,
        mode: str,
        entity_name: str,
        fields: list[dict[str, object]],
        request: str,
        existing_identity: dict[str, object] | None = None,
    ) -> AIIdentityProposal:
        return self._provider.propose_identity(
            mode=mode,
            entity_name=entity_name,
            fields=fields,
            request=request,
            existing_identity=existing_identity,
        )

    def propose_relationship(
        self,
        mode: str,
        entities: list[dict[str, object]],
        request: str,
        existing_relationship: dict[str, object] | None = None,
    ) -> AIRelationshipProposal:
        """Generate a structured FORGE relationship proposal."""

        return self._provider.propose_relationship(
            mode=mode,
            entities=entities,
            request=request,
            existing_relationship=existing_relationship,
        )


    def propose_foreign_key(
        self,
        mode: str,
        entities: list[dict[str, object]],
        request: str,
        existing_foreign_key: dict[str, object] | None = None,
    ) -> AIForeignKeyProposal:
        """Generate a structured FORGE foreign key proposal."""

        return self._provider.propose_foreign_key(
            mode=mode,
            entities=entities,
            request=request,
            existing_foreign_key=existing_foreign_key,
        )

    def propose_constraint(
        self,
        mode: str,
        entities: list[dict[str, object]],
        request: str,
        existing_constraint: dict[str, object] | None = None,
    ) -> AIConstraintProposal:
        """Generate a structured FORGE constraint proposal."""

        return self._provider.propose_constraint(
            mode=mode,
            entities=entities,
            request=request,
            existing_constraint=existing_constraint,
        )

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
