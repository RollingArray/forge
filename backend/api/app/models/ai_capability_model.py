"""
============================================================================
FORGE — Framework for Observed Rules, Generation & Engineered Data
============================================================================

File: ai_capability_model.py
Purpose: Defines the API contract for FORGE AI capabilities.

Author: Ranjoy Sen
Email: ranjoy.sen@collins.com

============================================================================
"""

from pydantic import BaseModel


class AICapabilityModel(BaseModel):
    """Represents the current availability of FORGE AI."""

    available: bool
    provider: str
    mode: str
    model: str | None
    message: str
