"""E2E-only session bootstrap endpoint.

This module is copied into the isolated extracted E2E deployment.
It must never be registered in the normal FORGE backend.
"""

import hmac
import os
from typing import Literal

from fastapi import APIRouter, Header, HTTPException, status
from pydantic import BaseModel, ConfigDict

from app.core.token_service import TokenService
from app.interfaces.auth_user import AuthUser
from app.models.auth_session_model import AuthSessionModel
from app.models.auth_user_model import AuthUserModel
from app.services.json_user_repository import JsonUserRepository


router = APIRouter(tags=["E2E Authentication"])

IDENTITIES = {
    "owner": ("forge.owner@collins.com", "FORGE E2E Owner"),
    "contributor": (
        "forge.contributor@collins.com",
        "FORGE E2E Contributor",
    ),
    "viewer": ("forge.viewer@collins.com", "FORGE E2E Viewer"),
}


class E2ESessionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    identity: Literal["owner", "contributor", "viewer"]


@router.post(
    "/session",
    response_model=AuthSessionModel,
    response_model_by_alias=True,
)
def create_e2e_session(
    request: E2ESessionRequest,
    x_forge_e2e_key: str | None = Header(default=None),
) -> AuthSessionModel:
    """Create a real FORGE session for one predefined E2E identity."""

    expected_key = os.environ.get("FORGE_E2E_BOOTSTRAP_KEY", "")

    if not expected_key:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Not found.",
        )

    if not x_forge_e2e_key or not hmac.compare_digest(
        x_forge_e2e_key,
        expected_key,
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid E2E bootstrap credential.",
        )

    email, display_name = IDENTITIES[request.identity]

    repository = JsonUserRepository()
    user = repository.get_by_email(email)

    if user is None:
        user = repository.create(
            email=email,
            display_name=display_name,
        )

    token = TokenService().create_access_token(user)

    return AuthSessionModel(
        access_token=token,
        token_type="Bearer",
        user=AuthUserModel(
            user_id=user.user_id,
            email=user.email,
            display_name=user.display_name,
            employee_id=user.employee_id,
            profile=user.profile,
        ),
    )
