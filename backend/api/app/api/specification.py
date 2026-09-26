"""
File: specification.py
Purpose: FORGE model specification API endpoints.

Author: Ranjoy Sen
Email: ranjoy.sen@collins.com
"""

from fastapi import APIRouter, Depends, HTTPException, status

from app.core.authentication_dependency import get_authenticated_user
from app.interfaces.auth_user import AuthUser
from app.models.specification_entity_model import (
    CreateEntityRequest,
)
from app.models.specification_model import SpecificationModel
from app.services.data_model_access_service import DataModelAccessService
from app.services.specification_service import SpecificationService


router = APIRouter(
    prefix="/data-models",
    tags=["Specifications"],
)

specification_service = SpecificationService()
data_model_access_service = DataModelAccessService()


@router.get(
    "/{data_model_id}/specification",
    response_model=SpecificationModel,
    status_code=status.HTTP_200_OK,
)
async def get_specification(
    data_model_id: str,
    user: AuthUser = Depends(get_authenticated_user),
) -> SpecificationModel:
    """Return the canonical FORGE specification for a visible Data Model."""

    if not data_model_access_service.can_view(
        data_model_id=data_model_id,
        user_id=user.user_id,
    ):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Data model not found.",
        )

    specification = specification_service.get_specification(
        data_model_id=data_model_id,
    )

    if specification is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Data model not found.",
        )

    return SpecificationModel(**specification)


@router.post(
    "/{data_model_id}/specification/entities",
    status_code=status.HTTP_201_CREATED,
)
async def create_entity(
    data_model_id: str,
    request: CreateEntityRequest,
    user: AuthUser = Depends(get_authenticated_user),
) -> dict:
    """Create an entity in the canonical FORGE specification."""

    if not data_model_access_service.can_edit(
        data_model_id=data_model_id,
        user_id=user.user_id,
    ):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Data model not found.",
        )

    try:
        entity = specification_service.create_entity(
            data_model_id=data_model_id,
            actor_user_id=user.user_id,
            request=request,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc

    if entity is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Data model not found.",
        )

    return entity
