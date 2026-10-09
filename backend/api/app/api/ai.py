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
from app.models.ai_constraint_proposal_model import (
    AIConstraintProposalRequestModel,
    AIConstraintProposalResponseModel,
)
from app.models.ai_foreign_key_proposal_model import (
    AIForeignKeyProposalRequestModel,
    AIForeignKeyProposalResponseModel,
)
from app.models.ai_field_proposal_model import (
    AIFieldProposalRequestModel,
    AIFieldProposalResponseModel,
)
from app.models.ai_entity_proposal_model import (
    AIEntityProposalModel,
    AIEntityProposalRequestModel,
)
from app.models.ai_identity_proposal_model import (
    AIIdentityProposalRequestModel,
    AIIdentityProposalResponseModel,
)
from app.models.ai_relationship_proposal_model import (
    AIRelationshipProposalRequestModel,
    AIRelationshipProposalResponseModel,
)
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
    "/entities/propose",
    response_model=AIEntityProposalModel,
)
def propose_entity(
    request: AIEntityProposalRequestModel,
) -> AIEntityProposalModel:
    """Generate an entity proposal for user review without saving it."""

    try:
        proposal = _ai_service.propose_entity(prompt=request.prompt)
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

    return AIEntityProposalModel(
        name=proposal.name,
        description=proposal.description,
        population=proposal.population,
        reasoning=proposal.reasoning,
    )


@router.post(
    "/identity/propose",
    response_model=AIIdentityProposalResponseModel,
)
def propose_identity(
    request: AIIdentityProposalRequestModel,
) -> AIIdentityProposalResponseModel:
    """Generate an AI proposal for a FORGE entity identity."""

    try:
        proposal = _ai_service.propose_identity(
            mode=request.mode,
            entity_name=request.entity_name.strip(),
            fields=request.fields,
            request=request.request.strip(),
            existing_identity=request.existing_identity,
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

    return AIIdentityProposalResponseModel(
        status=proposal.status,
        message=proposal.message,
        proposal=proposal.proposal,
    )


@router.post(
    "/relationships/propose",
    response_model=AIRelationshipProposalResponseModel,
)
def propose_relationship(
    request: AIRelationshipProposalRequestModel,
) -> AIRelationshipProposalResponseModel:
    """Generate an AI proposal for a FORGE relationship."""

    try:
        proposal = _ai_service.propose_relationship(
            mode=request.mode,
            entities=request.entities,
            request=request.request.strip(),
            existing_relationship=request.existing_relationship,
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

    return AIRelationshipProposalResponseModel(
        status=proposal.status,
        message=proposal.message,
        proposal=proposal.proposal,
    )


@router.post(
    "/foreign-keys/propose",
    response_model=AIForeignKeyProposalResponseModel,
)
def propose_foreign_key(
    request: AIForeignKeyProposalRequestModel,
) -> AIForeignKeyProposalResponseModel:
    """Generate an AI proposal for a FORGE foreign key."""

    try:
        proposal = _ai_service.propose_foreign_key(
            mode=request.mode,
            entities=request.entities,
            request=request.request.strip(),
            existing_foreign_key=request.existing_foreign_key,
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

    return AIForeignKeyProposalResponseModel(
        status=proposal.status,
        message=proposal.message,
        proposal=proposal.proposal,
    )


@router.post(
    "/constraints/propose",
    response_model=AIConstraintProposalResponseModel,
)
def propose_constraint(
    request: AIConstraintProposalRequestModel,
) -> AIConstraintProposalResponseModel:
    """Generate an AI proposal for a FORGE field constraint."""

    try:
        proposal = _ai_service.propose_constraint(
            mode=request.mode,
            entities=request.entities,
            request=request.request.strip(),
            existing_constraint=request.existing_constraint,
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

    return AIConstraintProposalResponseModel(
        status=proposal.status,
        message=proposal.message,
        proposal=proposal.proposal,
    )


@router.post(
    "/fields/propose",
    response_model=AIFieldProposalResponseModel,
)
def propose_field(
    request: AIFieldProposalRequestModel,
) -> AIFieldProposalResponseModel:
    """Generate an AI proposal for a FORGE field definition."""

    try:
        proposal = _ai_service.propose_field(
            mode=request.mode,
            entity_name=request.entity_name.strip(),
            request=request.request.strip(),
            existing_field=request.existing_field,
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

    return AIFieldProposalResponseModel(
        status=proposal.status,
        message=proposal.message,
        proposal=proposal.proposal,
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
