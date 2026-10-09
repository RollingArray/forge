"""
File: auth.py
Purpose: Authentication API endpoints for FORGE.
"""

from fastapi import APIRouter, Depends, HTTPException, status

from app.core.authentication_dependency import get_authenticated_user
from app.core.authentication_errors import DomainNotAllowedError
from app.interfaces.auth_user import AuthUser
from app.models.auth_session_model import AuthSessionModel
from app.models.auth_user_model import AuthUserModel
from app.models.login_request_model import LoginRequestModel
from app.models.magic_link_request_response_model import (
    MagicLinkRequestResponseModel,
)
from app.models.magic_link_verify_request_model import (
    MagicLinkVerifyRequestModel,
)
from app.services.ad_profile_service import ADProfileLookupError
from app.services.magic_link_authentication_service import (
    MagicLinkAuthenticationService,
)

router = APIRouter(prefix="/auth", tags=["Authentication"])
magic_link_service = MagicLinkAuthenticationService()


@router.post(
    "/magic-link",
    response_model=MagicLinkRequestResponseModel,
)
async def request_magic_link(
    request: LoginRequestModel,
) -> MagicLinkRequestResponseModel:
    """Request an email sign-in link; does not authenticate the user."""
    try:
        magic_link_service.request_magic_link(request.email)
    except DomainNotAllowedError as error:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(error),
        ) from error
    except Exception as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Unable to send a sign-in email. Please try again.",
        ) from error

    return MagicLinkRequestResponseModel(
        message="If the address is eligible, a sign-in link has been sent."
    )


@router.post("/magic-link/verify", response_model=AuthSessionModel)
async def verify_magic_link(
    request: MagicLinkVerifyRequestModel,
) -> AuthSessionModel:
    """Validate a link, enrich the user from AD, and issue a session."""
    try:
        session = magic_link_service.verify_magic_link(request.token)
    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(error),
        ) from error
    except ADProfileLookupError as error:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Unable to verify your corporate profile. Request a new link or try again.",
        ) from error

    return AuthSessionModel(
        access_token=session.access_token,
        token_type=session.token_type,
        user={
            "user_id": session.user.user_id,
            "email": session.user.email,
            "display_name": session.user.display_name,
            "employee_id": session.user.employee_id,
            "profile": session.user.profile,
        },
    )


@router.get("/me", response_model=AuthUserModel)
async def get_current_user(
    user: AuthUser = Depends(get_authenticated_user),
) -> AuthUserModel:
    """Return the currently authenticated FORGE user."""
    return AuthUserModel(
        user_id=user.user_id,
        email=user.email,
        display_name=user.display_name,
    )
