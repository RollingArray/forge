"""
File: development_authentication_service.py
Purpose: Development authentication service for FORGE.

Author: Ranjoy Sen
Email: ranjoy.sen@collins.com
"""

from app.core.authentication_errors import DomainNotAllowedError
from app.core.authentication_settings import load_authentication_configuration
from app.core.token_service import TokenService
from app.interfaces.auth_session import AuthSession
from app.interfaces.authentication_service import AuthenticationService
from app.interfaces.login_request import LoginRequest
from app.interfaces.user_repository import UserRepository
from app.services.json_user_repository import JsonUserRepository


class DevelopmentAuthenticationService(AuthenticationService):
    """Development implementation of the FORGE authentication service."""

    def __init__(
        self,
        user_repository: UserRepository | None = None,
    ) -> None:
        self._configuration = load_authentication_configuration()
        self._token_service = TokenService()
        self._user_repository = (
            user_repository
            if user_repository is not None
            else JsonUserRepository()
        )

    def login(self, request: LoginRequest) -> AuthSession:
        """Authenticate a user using the configured organization domain."""
        email = request.email.strip().lower()

        if not email or "@" not in email:
            raise DomainNotAllowedError(
                "A valid organization email is required."
            )

        domain = email.rsplit("@", 1)[-1]

        if domain not in self._configuration.allowed_domains:
            raise DomainNotAllowedError(
                f"Email domain '{domain}' is not allowed."
            )

        display_name = email.split("@", 1)[0]

        user = self._user_repository.get_by_email(email)

        if user is None:
            user = self._user_repository.create(
                email=email,
                display_name=display_name,
            )

        access_token = self._token_service.create_access_token(user)

        return AuthSession(
            access_token=access_token,
            token_type="Bearer",
            user=user,
        )

    def logout(self, access_token: str) -> None:
        """Invalidate a development authentication session."""
        return None
