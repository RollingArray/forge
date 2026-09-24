"""
File: authentication_errors.py
Purpose: Authentication errors used by the FORGE backend.

Author: Ranjoy Sen
Email: ranjoy.sen@collins.com
"""


class AuthenticationError(Exception):
    """Base error for FORGE authentication failures."""


class DomainNotAllowedError(AuthenticationError):
    """Raised when the user's email domain is not allowed."""


class DevelopmentUserNotConfiguredError(AuthenticationError):
    """Raised when a development user is not configured."""
