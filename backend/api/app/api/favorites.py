"""
File: favorites.py
Purpose: Authenticated Favorites API for data models and executions.
"""

from fastapi import APIRouter, Depends, HTTPException, status

from app.core.authentication_dependency import get_authenticated_user
from app.interfaces.auth_user import AuthUser
from app.interfaces.favorite import Favorite, FavoriteResourceType, JOB_RESOURCE_TYPES
from app.models.favorite_model import (
    CreateFavoriteRequestModel,
    FavoriteResponseModel,
)
from app.repositories.json_data_model_repository import JsonDataModelRepository
from app.repositories.json_favorite_repository import JsonFavoriteRepository
from app.services.data_model_access_service import DataModelAccessService
from app.api.generation import generation_service


router = APIRouter(prefix="/favorites", tags=["Favorites"])

favorite_repository = JsonFavoriteRepository()
data_model_repository = JsonDataModelRepository()
data_model_access_service = DataModelAccessService()


def _resource_is_visible(
    resource_type: FavoriteResourceType,
    data_model_id: str,
    job_id: str | None,
    user_id: str,
) -> bool:
    """Check visibility before exposing a favorite."""

    if resource_type not in JOB_RESOURCE_TYPES:
        return data_model_access_service.can_view(
            data_model_id=data_model_id,
            user_id=user_id,
        )

    if not data_model_access_service.can_view_results(
        data_model_id=data_model_id,
        user_id=user_id,
    ):
        return False

    if job_id is None:
        return False

    return generation_service.get_job(
        data_model_id=data_model_id,
        job_id=job_id,
    ) is not None


def _to_response(favorite: Favorite) -> FavoriteResponseModel | None:
    """Resolve a favorite into its current display information."""

    data_model = data_model_repository.get_by_id_any(
        favorite.data_model_id
    )
    if data_model is None:
        return None

    job_status: str | None = None
    if favorite.resource_type in JOB_RESOURCE_TYPES:
        if favorite.job_id is None:
            return None

        job = generation_service.get_job(
            data_model_id=favorite.data_model_id,
            job_id=favorite.job_id,
        )
        if job is None:
            return None

        job_status = (
            job.status.value
            if hasattr(job.status, "value")
            else str(job.status)
        )

    return FavoriteResponseModel(
        favorite_id=favorite.favorite_id,
        resource_type=favorite.resource_type,
        data_model_id=favorite.data_model_id,
        data_model_name=data_model.name,
        job_id=favorite.job_id,
        entity_name=favorite.entity_name,
        status=job_status,
        created_at=favorite.created_at,
    )


@router.get(
    "",
    response_model=list[FavoriteResponseModel],
    status_code=status.HTTP_200_OK,
)
async def get_favorites(
    user: AuthUser = Depends(get_authenticated_user),
) -> list[FavoriteResponseModel]:
    """List favorites visible to the authenticated user."""

    responses: list[FavoriteResponseModel] = []

    for favorite in favorite_repository.get_by_user_id(user.user_id):
        if not _resource_is_visible(
            resource_type=favorite.resource_type,
            data_model_id=favorite.data_model_id,
            job_id=favorite.job_id,
            user_id=user.user_id,
        ):
            continue

        response = _to_response(favorite)
        if response is not None:
            responses.append(response)

    return responses


@router.post(
    "",
    response_model=FavoriteResponseModel,
    status_code=status.HTTP_201_CREATED,
)
async def create_favorite(
    request: CreateFavoriteRequestModel,
    user: AuthUser = Depends(get_authenticated_user),
) -> FavoriteResponseModel:
    """Create a favorite after checking access to the target resource."""

    if not _resource_is_visible(
        resource_type=request.resource_type,
        data_model_id=request.data_model_id,
        job_id=request.job_id,
        user_id=user.user_id,
    ):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Favorite resource not found.",
        )

    favorite = favorite_repository.create(
        user_id=user.user_id,
        resource_type=request.resource_type,
        data_model_id=request.data_model_id,
        job_id=request.job_id,
        entity_name=request.entity_name,
    )

    response = _to_response(favorite)
    if response is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Favorite resource not found.",
        )

    return response


@router.delete(
    "/{favorite_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_favorite(
    favorite_id: str,
    user: AuthUser = Depends(get_authenticated_user),
) -> None:
    """Remove a favorite only from the authenticated user's store."""

    deleted = favorite_repository.delete(
        favorite_id=favorite_id,
        user_id=user.user_id,
    )

    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Favorite not found.",
        )
