"""
File: ad_profile_service.py
Purpose: Retrieve and validate corporate employee profiles from AD.
"""

import os
import ssl
from typing import Any

import httpx
import truststore
from pydantic import BaseModel, ConfigDict, Field, ValidationError


class ADUserProfile(BaseModel):
    """Validated corporate employee profile returned by AD."""

    model_config = ConfigDict(extra="ignore", str_strip_whitespace=True)

    user_id: str = Field(alias="userId", min_length=1)
    first_name: str = Field(alias="firstName", min_length=1)
    last_name: str = Field(alias="lastName", min_length=1)
    full_name: str = Field(alias="fullName", min_length=1)
    designation: str = Field(min_length=1)
    department: str = Field(min_length=1)
    email: str = Field(min_length=3)
    country: str = Field(min_length=1)
    company: str = Field(min_length=1)
    manager: str = Field(min_length=1)


class ADProfileLookupError(RuntimeError):
    """Raised when a corporate profile cannot be retrieved safely."""


class ADProfileService:
    """Backend client for the corporate AD user API."""

    def __init__(
        self,
        endpoint: str | None = None,
        timeout_seconds: float = 10.0,
    ) -> None:
        self._endpoint = (
            endpoint
            or os.environ.get(
                "FORGE_AD_USER_ENDPOINT",
                "https://blr1wkudpr1.utcapp.com/ADXUAPI/api/AD/user",
            )
        ).strip()
        self._timeout_seconds = timeout_seconds

        if not self._endpoint:
            raise ValueError("The AD user endpoint is required.")

    def get_profile(self, email: str) -> ADUserProfile:
        """Retrieve a validated profile for the supplied corporate email."""
        normalized_email = email.strip().lower()

        if not normalized_email or "@" not in normalized_email:
            raise ValueError("A valid email address is required.")

        try:
            ssl_context = truststore.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
            with httpx.Client(
                timeout=self._timeout_seconds,
                verify=ssl_context,
            ) as client:
                response = client.get(
                    self._endpoint,
                    params={"email": normalized_email},
                    headers={"Accept": "application/json"},
                )
                response.raise_for_status()
                payload: Any = response.json()
        except (httpx.HTTPError, ValueError) as error:
            raise ADProfileLookupError(
                "The corporate employee profile could not be retrieved."
            ) from error

        # Support either a single profile object or a documented wrapper.
        if isinstance(payload, dict) and isinstance(payload.get("data"), dict):
            payload = payload["data"]

        try:
            profile = ADUserProfile.model_validate(payload)
        except (ValidationError, TypeError) as error:
            raise ADProfileLookupError(
                "The corporate employee profile response is incomplete or invalid."
            ) from error

        if profile.email.strip().lower() != normalized_email:
            raise ADProfileLookupError(
                "The corporate directory returned a profile for a different email."
            )

        return profile
