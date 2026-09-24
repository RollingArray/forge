"""
File: login_request_model.py
Purpose: Pydantic model for the authentication login API request.

Author: Ranjoy Sen
Email: ranjoy.sen@collins.com
"""

from pydantic import BaseModel


class LoginRequestModel(BaseModel):
    """HTTP request model for FORGE login."""

    email: str
