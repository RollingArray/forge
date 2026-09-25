"""
File: data_models.py
Purpose: Data model API endpoints for FORGE.

Author: Ranjoy Sen
Email: ranjoy.sen@collins.com
"""

from fastapi import APIRouter, Depends, HTTPException, status

from app.core.authentication_dependency import get_authenticated_user
from app.interfaces.auth_user import AuthUser
from app.models.data_model_model import (
    CreateDataModelRequestModel,
    DataModelModel,
    UpdateDataModelRequestModel,
)
from app.models.data_model_list_item_model import DataModelListItemModel
from app.services.data_model_access_service import DataModelAccessService
from app.services.data_model_service import DataModelService


router = APIRouter(
    prefix="/data-models",
    tags=["Data Models"],
)

data_model_service = DataModelService()
data_model_access_service = DataModelAccessService()


@router.post(
    "",
    response_model=DataModelModel,
    status_code=status.HTTP_201_CREATED,
)
async def create_data_model(
    request: CreateDataModelRequestModel,
    user: AuthUser = Depends(get_authenticated_user),
) -> DataModelModel:
    """Create a new authenticated user's FORGE data model."""

    data_model = data_model_service.create_data_model(
        owner_user_id=user.user_id,
        name=request.name,
        description=request.description,
        color=request.color,
        tags=request.tags,
    )

    return DataModelModel(
        data_model_id=data_model.data_model_id,
        owner_user_id=data_model.owner_user_id,
        name=data_model.name,
        description=data_model.description,
        color=data_model.color,
        tags=data_model.tags,
        status=data_model.status,
        created_at=data_model.created_at,
        updated_at=data_model.updated_at,
    )


@router.put(
    "/{data_model_id}",
    response_model=DataModelModel,
    status_code=status.HTTP_200_OK,
)
async def update_data_model(
    data_model_id: str,
    request: UpdateDataModelRequestModel,
    user: AuthUser = Depends(get_authenticated_user),
) -> DataModelModel:
    """Update an authenticated user's FORGE data model."""

    data_model = data_model_service.update_data_model(
        data_model_id=data_model_id,
        owner_user_id=user.user_id,
        name=request.name,
        description=request.description,
        color=request.color,
        tags=request.tags,
    )

    if data_model is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Data model not found.",
        )

    return DataModelModel(
        data_model_id=data_model.data_model_id,
        owner_user_id=data_model.owner_user_id,
        name=data_model.name,
        description=data_model.description,
        color=data_model.color,
        tags=data_model.tags,
        status=data_model.status,
        created_at=data_model.created_at,
        updated_at=data_model.updated_at,
    )


@router.delete(
    "/{data_model_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_data_model(
    data_model_id: str,
    user: AuthUser = Depends(get_authenticated_user),
) -> None:
    """Delete an authenticated user's FORGE data model."""

    deleted = data_model_service.delete_data_model(
        data_model_id=data_model_id,
        owner_user_id=user.user_id,
    )

    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Data model not found.",
        )


@router.get(
    "",
    response_model=list[DataModelListItemModel],
    status_code=status.HTTP_200_OK,
)
async def get_data_models(
    user: AuthUser = Depends(get_authenticated_user),
) -> list[DataModelListItemModel]:
    """Return FORGE data models visible to the authenticated user."""

    data_models = data_model_service.get_data_models(
        owner_user_id=user.user_id,
    )

    return [
        DataModelListItemModel(
            data_model_id=data_model.data_model_id,
            owner_user_id=data_model.owner_user_id,
            name=data_model.name,
            description=data_model.description,
            color=data_model.color,
            tags=data_model.tags,
            status=data_model.status,
            created_at=data_model.created_at,
            updated_at=data_model.updated_at,
            access_role=data_model_access_service.get_role(
                data_model_id=data_model.data_model_id,
                user_id=user.user_id,
            )
            or "VIEWER",
        )
        for data_model in data_models
    ]
