"""
============================================================================
FORGE — Framework for Observed Rules, Generation & Engineered Data
============================================================================

File: ai.py
Purpose: Exposes FORGE AI capability and proposal APIs.

Author: Ranjoy Sen
Email: ranjoy.sen@collins.com

============================================================================
"""

from fastapi import APIRouter, HTTPException, status

from app.core.ai_settings import load_ai_configuration
from app.models.ai_capability_model import AICapabilityModel
from app.models.ai_data_model_proposal_model import (
    AIDataModelProposalModel,
    AIDataModelSuggestionRequestModel,
)
from app.models.ai_semantic_preview_model import (
    AISemanticPreviewModel,
    AISemanticPreviewRequestModel,
)
from app.services.ai_service import AIService
from app.services.ollama_ai_provider import OllamaAIProvider

router = APIRouter(
    prefix="/ai",
    tags=["AI"],
)

_ai_service = AIService(
    provider=OllamaAIProvider(
        configuration=load_ai_configuration(),
    ),
)


@router.get(
    "/capabilities",
    response_model=AICapabilityModel,
)
def get_ai_capabilities() -> AICapabilityModel:
    """Return the current FORGE AI capability status."""

    status_result = _ai_service.get_capabilities()

    return AICapabilityModel(
        available=status_result.available,
        provider=status_result.provider,
        mode=status_result.mode,
        model=status_result.model,
        message=status_result.message,
    )


@router.post(
    "/semantic/preview",
    response_model=AISemanticPreviewModel,
)
def preview_semantic_values(
    request: AISemanticPreviewRequestModel,
) -> AISemanticPreviewModel:
    """Generate representative semantic field values for preview."""

    try:
        preview = _ai_service.preview_semantic_values(
            description=request.description.strip(),
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except RuntimeError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc

    return AISemanticPreviewModel(
        status=preview.status,
        message=preview.message,
        preview_values=preview.preview_values,
    )


@router.post(
    "/data-models/suggest",
    response_model=AIDataModelProposalModel,
)
def suggest_data_model(
    request: AIDataModelSuggestionRequestModel,
) -> AIDataModelProposalModel:
    """Generate an AI proposal for a new FORGE Data Model."""

    try:
        proposal = _ai_service.suggest_data_model(
            prompt=request.prompt.strip(),
        )
    except RuntimeError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc

    return AIDataModelProposalModel(
        name=proposal.name,
        description=proposal.description,
        suggested_tags=proposal.suggested_tags,
        reasoning=proposal.reasoning,
    )
