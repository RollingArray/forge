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
    UpdateEntityPopulationRequest,
)
from app.models.specification_field_model import (
    CreateFieldRequest,
    UpdateFieldRequest,
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


@router.post(
    "/{data_model_id}/specification/entities/{entity_name}/fields",
    status_code=status.HTTP_201_CREATED,
)
async def create_field(
    data_model_id: str,
    entity_name: str,
    request: CreateFieldRequest,
    user: AuthUser = Depends(get_authenticated_user),
) -> dict:
    """Create a field in an existing FORGE entity."""

    if not data_model_access_service.can_edit(
        data_model_id=data_model_id,
        user_id=user.user_id,
    ):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Data model not found.",
        )

    try:
        field = specification_service.create_field(
            data_model_id=data_model_id,
            actor_user_id=user.user_id,
            entity_name=entity_name,
            request=request,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc

    if field is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Data model not found.",
        )

    return field


@router.put(
    "/{data_model_id}/specification/entities/{entity_name}/fields/{field_name}",
    status_code=status.HTTP_200_OK,
)
async def update_field(
    data_model_id: str,
    entity_name: str,
    field_name: str,
    request: UpdateFieldRequest,
    user: AuthUser = Depends(get_authenticated_user),
) -> dict:
    """Update an existing field in a FORGE entity."""

    if not data_model_access_service.can_edit(
        data_model_id=data_model_id,
        user_id=user.user_id,
    ):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Data model not found.",
        )

    try:
        field = specification_service.update_field(
            data_model_id=data_model_id,
            actor_user_id=user.user_id,
            entity_name=entity_name,
            field_name=field_name,
            request=request,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

    if field is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Data model not found.",
        )

    return field


@router.put(
    "/{data_model_id}/specification/entities/{entity_name}/population",
    status_code=status.HTTP_200_OK,
)
async def update_entity_population(
    data_model_id: str,
    entity_name: str,
    request: UpdateEntityPopulationRequest,
    user: AuthUser = Depends(get_authenticated_user),
) -> dict:
    """Update the population of an existing FORGE entity."""

    if not data_model_access_service.can_edit(
        data_model_id=data_model_id,
        user_id=user.user_id,
    ):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Data model not found.",
        )

    try:
        entity = specification_service.update_entity_population(
            data_model_id=data_model_id,
            actor_user_id=user.user_id,
            entity_name=entity_name,
            count=request.count,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

    if entity is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Data model not found.",
        )

    return entity


@router.delete(
    "/{data_model_id}/specification/entities/{entity_name}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_entity(
    data_model_id: str,
    entity_name: str,
    user: AuthUser = Depends(get_authenticated_user),
) -> None:
    """Delete an entity from the canonical FORGE specification."""

    if not data_model_access_service.can_edit(
        data_model_id=data_model_id,
        user_id=user.user_id,
    ):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Data model not found.",
        )

    try:
        deleted = specification_service.delete_entity(
            data_model_id=data_model_id,
            actor_user_id=user.user_id,
            entity_name=entity_name,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc

    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Entity not found.",
        )
