"""
File: auth_session_model.py
Purpose: Pydantic model for an authenticated FORGE session.

Author: Ranjoy Sen
Email: ranjoy.sen@collins.com
"""

from pydantic import BaseModel, ConfigDict

from app.models.auth_user_model import AuthUserModel


class AuthSessionModel(BaseModel):
    """HTTP response model for a successful FORGE authentication."""

    model_config = ConfigDict(
        populate_by_name=True,
        alias_generator=lambda field_name: {
            "access_token": "accessToken",
            "token_type": "tokenType",
        }.get(field_name, field_name),
    )

    access_token: str
    token_type: str
    user: AuthUserModel
