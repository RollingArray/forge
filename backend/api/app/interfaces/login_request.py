"""
============================================================================
FORGE — Framework for Observed Rules, Generation & Engineered Data
============================================================================

File: login_request.py
Purpose: Authentication login request contract.

Author: Ranjoy Sen
Email: ranjoy.sen@collins.com

============================================================================
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class LoginRequest:
    """Request submitted to authenticate a FORGE user."""

    email: str
