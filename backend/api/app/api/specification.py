"""
File: specification.py
Purpose: FORGE model specification API endpoints.

Author: Ranjoy Sen
Email: ranjoy.sen@collins.com
"""

from fastapi import APIRouter, Depends, HTTPException, status

from app.core.authentication_dependency import get_authenticated_user
from app.interfaces.auth_user import AuthUser
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
