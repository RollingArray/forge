"""
File: token_service.py
Purpose: Create and validate development access tokens for FORGE.

Author: Ranjoy Sen
Email: ranjoy.sen@collins.com
"""

from datetime import datetime, timedelta, timezone

import jwt
from jwt import InvalidTokenError

from app.core.authentication_settings import load_authentication_configuration
from app.interfaces.auth_user import AuthUser


class TokenService:
    """Service responsible for development access token operations."""

    def __init__(self) -> None:
        configuration = load_authentication_configuration()
        self._configuration = configuration.development_token

    def create_access_token(self, user: AuthUser) -> str:
        """Create a signed development JWT for an authenticated user."""
        issued_at = datetime.now(timezone.utc)
        expires_at = issued_at + timedelta(
            minutes=self._configuration.expiration_minutes
        )

        payload = {
            "sub": user.user_id,
            "email": user.email,
            "display_name": user.display_name,
            "iat": issued_at,
            "exp": expires_at,
        }

        return jwt.encode(
            payload,
            self._configuration.secret,
            algorithm=self._configuration.algorithm,
        )

    def validate_access_token(self, access_token: str) -> AuthUser:
        """Validate a development JWT and return its authenticated user."""
        try:
            payload = jwt.decode(
                access_token,
                self._configuration.secret,
                algorithms=[self._configuration.algorithm],
            )
        except InvalidTokenError as error:
            raise ValueError(
                "Invalid or expired access token."
            ) from error

        user_id = payload.get("sub")
        email = payload.get("email")
        display_name = payload.get("display_name")

        if not all(
            isinstance(value, str)
            for value in (user_id, email, display_name)
        ):
            raise ValueError(
                "Access token does not contain a valid user."
            )

        return AuthUser(
            user_id=user_id,
            email=email,
            display_name=display_name,
        )
