"""
File: authentication_settings.py
Purpose: Load and validate FORGE authentication configuration.

Author: Ranjoy Sen
Email: ranjoy.sen@collins.com
"""

import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict


class DevelopmentTokenConfiguration(BaseModel):
    """Configuration for development access tokens."""

    model_config = ConfigDict(extra="forbid")

    secret: str
    algorithm: str
    expiration_minutes: int


class AuthenticationConfiguration(BaseModel):
    """FORGE authentication configuration."""

    model_config = ConfigDict(extra="forbid")

    allowed_domains: list[str]
    development_token: DevelopmentTokenConfiguration


def load_authentication_configuration() -> AuthenticationConfiguration:
    """Load and validate authentication configuration from JSON."""

    configuration_path = (
        Path(__file__).resolve().parents[2]
        / "config"
        / "authentication.json"
    )

    with configuration_path.open("r", encoding="utf-8") as configuration_file:
        configuration = json.load(configuration_file)

    return AuthenticationConfiguration.model_validate(configuration)
