"""
File: development_authentication_service.py
Purpose: Development authentication service for FORGE.

Author: Ranjoy Sen
Email: ranjoy.sen@collins.com
"""

from app.constants.activity import ActivityType
from app.core.authentication_errors import DomainNotAllowedError
from app.core.authentication_settings import load_authentication_configuration
from app.core.token_service import TokenService
from app.interfaces.auth_session import AuthSession
from app.interfaces.authentication_service import AuthenticationService
from app.interfaces.login_request import LoginRequest
from app.interfaces.user_repository import UserRepository
from app.services.activity_service import ActivityService
from app.services.json_user_repository import JsonUserRepository


class DevelopmentAuthenticationService(AuthenticationService):
    """Development implementation of the FORGE authentication service."""

    def __init__(
        self,
        user_repository: UserRepository | None = None,
        activity_service: ActivityService | None = None,
    ) -> None:
        self._configuration = load_authentication_configuration()
        self._token_service = TokenService()
        self._user_repository = (
            user_repository
            if user_repository is not None
            else JsonUserRepository()
        )
        self._activity_service = (
            activity_service
            if activity_service is not None
            else ActivityService()
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

        self._activity_service.record(
            owner_user_id=user.user_id,
            actor_user_id=user.user_id,
            activity_type=ActivityType.USER_SIGNED_IN,
            title="Signed in to FORGE",
            description="User signed in successfully",
        )

        return AuthSession(
            access_token=access_token,
            token_type="Bearer",
            user=user,
        )

    def logout(self, access_token: str) -> None:
        """Invalidate a development authentication session."""
        return None
