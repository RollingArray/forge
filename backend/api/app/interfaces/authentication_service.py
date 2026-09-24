"""
File: authentication_service.py
Purpose: Authentication service contract.

Author: Ranjoy Sen
Email: ranjoy.sen@collins.com
"""

from abc import ABC, abstractmethod

from app.interfaces.auth_session import AuthSession
from app.interfaces.login_request import LoginRequest


class AuthenticationService(ABC):
    """Contract for FORGE authentication services."""

    @abstractmethod
    def login(self, request: LoginRequest) -> AuthSession:
        """Authenticate a user and return an authenticated session."""
        raise NotImplementedError

    @abstractmethod
    def logout(self, access_token: str) -> None:
        """Invalidate an authenticated session."""
        raise NotImplementedError
