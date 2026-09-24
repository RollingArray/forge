"""
File: authentication_dependency.py
Purpose: FastAPI authentication dependency for protected FORGE APIs.

Author: Ranjoy Sen
Email: ranjoy.sen@collins.com
"""

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.token_service import TokenService
from app.interfaces.auth_user import AuthUser


_bearer_scheme = HTTPBearer(auto_error=False)
_token_service = TokenService()


def get_authenticated_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(
        _bearer_scheme
    ),
) -> AuthUser:
    """Return the authenticated FORGE user from a Bearer token."""

    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication is required.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        return _token_service.validate_access_token(
            credentials.credentials
        )
    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired access token.",
            headers={"WWW-Authenticate": "Bearer"},
        ) from error
