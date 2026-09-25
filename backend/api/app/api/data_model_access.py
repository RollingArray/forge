"""
File: data_model_access.py
Purpose: Data model collaboration and access API endpoints for FORGE.

Author: Ranjoy Sen
Email: ranjoy.sen@collins.com
"""

from fastapi import APIRouter, Depends, HTTPException, status

from app.constants.data_model_access import DataModelAccessRole
from app.core.authentication_dependency import get_authenticated_user
from app.interfaces.auth_user import AuthUser
from app.models.data_model_access_model import (
    DataModelAccessModel,
    GrantDataModelAccessRequestModel,
    UpdateDataModelAccessRequestModel,
)
from app.services.json_user_repository import JsonUserRepository
from app.repositories.json_data_model_repository import JsonDataModelRepository
from app.services.data_model_access_service import DataModelAccessService


router = APIRouter(
    prefix="/data-models",
    tags=["Data Model Access"],
)

data_model_access_service = DataModelAccessService()
user_repository = JsonUserRepository()
data_model_repository = JsonDataModelRepository()


@router.post(
    "/{data_model_id}/access",
    response_model=DataModelAccessModel,
    status_code=status.HTTP_201_CREATED,
)
async def grant_data_model_access(
    data_model_id: str,
    request: GrantDataModelAccessRequestModel,
    user: AuthUser = Depends(get_authenticated_user),
) -> DataModelAccessModel:
    """Grant a contributor or viewer role to an existing FORGE user."""

    if request.user_id == user.user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The data model owner does not need an access record.",
        )

    target_user = user_repository.get_by_id(request.user_id)

    if target_user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Target user not found.",
        )

    access = data_model_access_service.grant_access(
        data_model_id=data_model_id,
        owner_user_id=user.user_id,
        target_user_id=request.user_id,
        role=request.role,
    )

    if access is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Data model not found or access is not permitted.",
        )

    return DataModelAccessModel(
        data_model_id=access.data_model_id,
        user_id=access.user_id,
        display_name=target_user.display_name,
        email=target_user.email,
        role=access.role.value,
        granted_at=access.granted_at,
    )


@router.put(
    "/{data_model_id}/access/{target_user_id}",
    response_model=DataModelAccessModel,
    status_code=status.HTTP_200_OK,
)
async def update_data_model_access(
    data_model_id: str,
    target_user_id: str,
    request: UpdateDataModelAccessRequestModel,
    user: AuthUser = Depends(get_authenticated_user),
) -> DataModelAccessModel:
    """Update an existing contributor or viewer role."""

    if target_user_id == user.user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The data model owner role cannot be changed.",
        )

    target_user = user_repository.get_by_id(target_user_id)

    if target_user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Target user not found.",
        )

    access = data_model_access_service.update_role(
        data_model_id=data_model_id,
        owner_user_id=user.user_id,
        target_user_id=target_user_id,
        role=request.role,
    )

    if access is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Access record not found or access is not permitted.",
        )

    return DataModelAccessModel(
        data_model_id=access.data_model_id,
        user_id=access.user_id,
        display_name=target_user.display_name,
        email=target_user.email,
        role=access.role.value,
        granted_at=access.granted_at,
    )


@router.delete(
    "/{data_model_id}/access/{target_user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def revoke_data_model_access(
    data_model_id: str,
    target_user_id: str,
    user: AuthUser = Depends(get_authenticated_user),
) -> None:
    """Remove a contributor or viewer from a data model."""

    if target_user_id == user.user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The data model owner cannot remove their own access.",
        )

    target_user = user_repository.get_by_id(target_user_id)

    if target_user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Target user not found.",
        )

    revoked = data_model_access_service.revoke_access(
        data_model_id=data_model_id,
        owner_user_id=user.user_id,
        target_user_id=target_user_id,
    )

    if not revoked:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Access record not found or access is not permitted.",
        )

    return None


@router.get(
    "/{data_model_id}/access",
    response_model=list[DataModelAccessModel],
    status_code=status.HTTP_200_OK,
)
async def get_data_model_access(
    data_model_id: str,
    user: AuthUser = Depends(get_authenticated_user),
) -> list[DataModelAccessModel]:
    """Return users with access to a data model."""

    access_records = data_model_access_service.get_access(
        data_model_id=data_model_id,
        user_id=user.user_id,
    )

    if access_records is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Data model not found or access is not permitted.",
        )

    results: list[DataModelAccessModel] = []

    data_model = data_model_repository.get_by_id_any(
        data_model_id=data_model_id,
    )

    if data_model is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Data model not found.",
        )

    owner_user = user_repository.get_by_id(data_model.owner_user_id)

    if owner_user is not None:
        results.append(
            DataModelAccessModel(
                data_model_id=data_model.data_model_id,
                user_id=owner_user.user_id,
                display_name=owner_user.display_name,
                email=owner_user.email,
                role="OWNER",
                granted_at=None,
            )
        )

    for access in access_records:
        target_user = user_repository.get_by_id(access.user_id)

        if target_user is None:
            continue

        results.append(
            DataModelAccessModel(
                data_model_id=access.data_model_id,
                user_id=access.user_id,
                display_name=target_user.display_name,
                email=target_user.email,
                role=access.role.value,
                granted_at=access.granted_at,
            )
        )

    return results
