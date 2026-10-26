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

from fastapi import APIRouter, Depends, HTTPException, status
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.core.authentication_dependency import get_authenticated_user
from app.interfaces.auth_user import AuthUser

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
from app.constants.activity import ActivityType
from app.repositories.json_data_model_repository import JsonDataModelRepository
from app.services.activity_service import ActivityService
from app.services.data_model_access_service import DataModelAccessService
from app.services.ollama_ai_provider import OllamaAIProvider

router = APIRouter(
    prefix="/ai",
    tags=["AI"],
    dependencies=[Depends(get_authenticated_user)],
)

data_model_access_service = DataModelAccessService()


class AIDataModelProposalActivityRequestModel(BaseModel):
    """Record acceptance of a workspace-level AI Data Model proposal."""

    model_config = ConfigDict(extra="forbid")

    action: Literal["ACCEPTED"]


class AIProposalActivityRequestModel(BaseModel):
    """Record a user decision about an AI-generated proposal."""

    model_config = ConfigDict(extra="forbid")

    data_model_id: str = Field(min_length=1)
    proposal_type: Literal[
        "entity",
        "identity",
        "relationship",
        "foreign key",
        "constraint",
        "field",
    ]
    action: Literal["ACCEPTED", "REGENERATED", "DISMISSED"]


activity_service = ActivityService()
data_model_repository = JsonDataModelRepository()


def _record_ai_proposal_activity(
    user: AuthUser,
    data_model_id: str,
    proposal_type: str,
    regenerated: bool = False,
) -> None:
    """Persist a successfully generated AI proposal in workspace activity."""

    data_model = data_model_repository.get_by_id_any(
        data_model_id=data_model_id,
    )

    if data_model is None:
        return

    try:
        activity_service.record(
            owner_user_id=data_model.owner_user_id,
            actor_user_id=user.user_id,
            activity_type=(
                ActivityType.AI_PROPOSAL_REGENERATED
                if regenerated
                else ActivityType.AI_PROPOSAL_GENERATED
            ),
            title=(
                f"AI regenerated {proposal_type} proposal"
                if regenerated
                else f"AI generated {proposal_type} proposal"
            ),
            description=(
                f"FORGE AI regenerated a {proposal_type} proposal."
                if regenerated
                else f"FORGE AI generated a {proposal_type} proposal."
            ),
            data_model_id=data_model_id,
            metadata={
                "operation": (
                    "REGENERATE_AI_PROPOSAL" if regenerated else "GENERATE_AI_PROPOSAL"
                ),
                "proposal_type": proposal_type,
                "outcome": ("REGENERATED" if regenerated else "GENERATED"),
            },
        )
    except Exception:
        # Activity telemetry must not turn a successful AI response into a failure.
        return


@router.post("/proposals/activity", status_code=status.HTTP_204_NO_CONTENT)
def record_ai_proposal_activity(
    request: AIProposalActivityRequestModel,
    user: AuthUser = Depends(get_authenticated_user),
) -> None:
    """Record an authenticated user decision for an AI proposal."""

    if not data_model_access_service.can_edit(
        data_model_id=request.data_model_id,
        user_id=user.user_id,
    ):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Data model not found.",
        )

    data_model = data_model_repository.get_by_id_any(
        data_model_id=request.data_model_id,
    )
    if data_model is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Data model not found.",
        )

    activity_type = {
        "ACCEPTED": ActivityType.AI_PROPOSAL_ACCEPTED,
        "REGENERATED": ActivityType.AI_PROPOSAL_REGENERATED,
        "DISMISSED": ActivityType.AI_PROPOSAL_DISMISSED,
    }[request.action]

    try:
        activity_service.record(
            owner_user_id=data_model.owner_user_id,
            actor_user_id=user.user_id,
            activity_type=activity_type,
            title=f"AI {request.action.lower()} {request.proposal_type} proposal",
            description=(
                f"User {request.action.lower()} an AI "
                f"{request.proposal_type} proposal."
            ),
            data_model_id=request.data_model_id,
            metadata={
                "operation": {
                    "ACCEPTED": "ACCEPT_AI_PROPOSAL",
                    "REGENERATED": "REGENERATE_AI_PROPOSAL",
                    "DISMISSED": "DISMISS_AI_PROPOSAL",
                }[request.action],
                "proposal_type": request.proposal_type,
                "outcome": request.action,
            },
        )
    except Exception:
        # Telemetry must not interfere with the user's model-studio workflow.
        return


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
    user: AuthUser = Depends(get_authenticated_user),
) -> AIEntityProposalModel:
    """Generate an entity proposal for user review without saving it."""

    if not data_model_access_service.can_edit(
        data_model_id=request.data_model_id,
        user_id=user.user_id,
    ):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Data model not found.",
        )

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

    _record_ai_proposal_activity(
        user=user,
        data_model_id=request.data_model_id,
        proposal_type="entity",
        regenerated=request.regenerate,
    )

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
    user: AuthUser = Depends(get_authenticated_user),
) -> AIIdentityProposalResponseModel:
    """Generate an AI proposal for a FORGE entity identity."""

    if not data_model_access_service.can_edit(
        data_model_id=request.data_model_id,
        user_id=user.user_id,
    ):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Data model not found.",
        )

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

    _record_ai_proposal_activity(
        user=user,
        data_model_id=request.data_model_id,
        proposal_type="identity",
        regenerated=request.regenerate,
    )

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
    user: AuthUser = Depends(get_authenticated_user),
) -> AIRelationshipProposalResponseModel:
    """Generate an AI proposal for a FORGE relationship."""

    if not data_model_access_service.can_edit(
        data_model_id=request.data_model_id,
        user_id=user.user_id,
    ):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Data model not found.",
        )

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

    _record_ai_proposal_activity(
        user=user,
        data_model_id=request.data_model_id,
        proposal_type="relationship",
        regenerated=request.regenerate,
    )

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
    user: AuthUser = Depends(get_authenticated_user),
) -> AIForeignKeyProposalResponseModel:
    """Generate an AI proposal for a FORGE foreign key."""

    if not data_model_access_service.can_edit(
        data_model_id=request.data_model_id,
        user_id=user.user_id,
    ):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Data model not found.",
        )

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

    _record_ai_proposal_activity(
        user=user,
        data_model_id=request.data_model_id,
        proposal_type="foreign key",
        regenerated=request.regenerate,
    )

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
    user: AuthUser = Depends(get_authenticated_user),
) -> AIConstraintProposalResponseModel:
    """Generate an AI proposal for a FORGE field constraint."""

    if not data_model_access_service.can_edit(
        data_model_id=request.data_model_id,
        user_id=user.user_id,
    ):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Data model not found.",
        )

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

    _record_ai_proposal_activity(
        user=user,
        data_model_id=request.data_model_id,
        proposal_type="constraint",
        regenerated=request.regenerate,
    )

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
    user: AuthUser = Depends(get_authenticated_user),
) -> AIFieldProposalResponseModel:
    """Generate an AI proposal for a FORGE field definition."""

    if not data_model_access_service.can_edit(
        data_model_id=request.data_model_id,
        user_id=user.user_id,
    ):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Data model not found.",
        )

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

    _record_ai_proposal_activity(
        user=user,
        data_model_id=request.data_model_id,
        proposal_type="field",
        regenerated=request.regenerate,
    )

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
    user: AuthUser = Depends(get_authenticated_user),
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

    try:
        activity_service.record(
            owner_user_id=user.user_id,
            actor_user_id=user.user_id,
            activity_type=(
                ActivityType.AI_PROPOSAL_REGENERATED
                if request.regenerate
                else ActivityType.AI_PROPOSAL_GENERATED
            ),
            title=(
                "AI data model proposal regenerated"
                if request.regenerate
                else "AI data model proposal generated"
            ),
            description=(
                "FORGE AI regenerated a data model proposal."
                if request.regenerate
                else "FORGE AI generated a data model proposal."
            ),
            metadata={
                "operation": (
                    "REGENERATE_AI_PROPOSAL"
                    if request.regenerate
                    else "GENERATE_AI_PROPOSAL"
                ),
                "proposal_type": "data model",
                "outcome": ("REGENERATED" if request.regenerate else "GENERATED"),
            },
        )
    except Exception:
        # Activity telemetry must not turn a successful AI response into a failure.
        pass

    return AIDataModelProposalModel(
        name=proposal.name,
        description=proposal.description,
        suggested_tags=proposal.suggested_tags,
        reasoning=proposal.reasoning,
    )


@router.post(
    "/data-models/proposals/activity",
    status_code=status.HTTP_204_NO_CONTENT,
)
def record_data_model_proposal_activity(
    request: AIDataModelProposalActivityRequestModel,
    user: AuthUser = Depends(get_authenticated_user),
) -> None:
    """Record that the user chose to use a new Data Model proposal."""

    try:
        activity_service.record(
            owner_user_id=user.user_id,
            actor_user_id=user.user_id,
            activity_type=ActivityType.AI_PROPOSAL_ACCEPTED,
            title="AI data model proposal accepted",
            description="Used an AI-generated data model proposal.",
            metadata={
                "operation": "ACCEPT_AI_PROPOSAL",
                "proposal_type": "data model",
                "outcome": "ACCEPTED",
            },
        )
    except Exception:
        # Activity telemetry must not interfere with proposal use.
        return
