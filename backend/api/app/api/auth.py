"""
File: auth.py
Purpose: Authentication API endpoints for FORGE.

Author: Ranjoy Sen
Email: ranjoy.sen@collins.com
"""

from fastapi import APIRouter, Depends, HTTPException, status

from app.core.authentication_dependency import get_authenticated_user
from app.core.authentication_errors import DomainNotAllowedError
from app.interfaces.auth_user import AuthUser
from app.interfaces.login_request import LoginRequest
from app.models.auth_session_model import AuthSessionModel
from app.models.auth_user_model import AuthUserModel
from app.models.login_request_model import LoginRequestModel
from app.services.development_authentication_service import (
    DevelopmentAuthenticationService,
)

router = APIRouter(
    prefix="/auth",
    tags=["Authentication"],
)

authentication_service = DevelopmentAuthenticationService()


@router.post(
    "/login",
    response_model=AuthSessionModel,
)
async def login(request: LoginRequestModel) -> AuthSessionModel:
    """Authenticate a FORGE user."""
    try:
        session = authentication_service.login(
            LoginRequest(email=str(request.email))
        )
    except DomainNotAllowedError as error:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(error),
        ) from error

    return AuthSessionModel(
        access_token=session.access_token,
        token_type=session.token_type,
        user={
            "user_id": session.user.user_id,
            "email": session.user.email,
            "display_name": session.user.display_name,
        },
    )


@router.get(
    "/me",
    response_model=AuthUserModel,
)
async def get_current_user(
    user: AuthUser = Depends(get_authenticated_user),
) -> AuthUserModel:
    """Return the currently authenticated FORGE user."""
    return AuthUserModel(
        user_id=user.user_id,
        email=user.email,
        display_name=user.display_name,
    )
