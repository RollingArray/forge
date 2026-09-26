"""
============================================================================
FORGE — Framework for Observed Rules, Generation & Engineered Data
============================================================================

File: ai_semantic_preview_model.py
Purpose: Defines the API contract for semantic field generation previews.

Author: Ranjoy Sen
Email: ranjoy.sen@collins.com

============================================================================
"""

from typing import Literal

from pydantic import BaseModel, Field


SemanticPreviewStatus = Literal[
    "PROPOSE",
    "CLARIFY",
    "UNSUPPORTED",
]


class AISemanticPreviewModel(BaseModel):
    """Represents an AI semantic generation preview."""

    status: SemanticPreviewStatus
    message: str
    preview_values: list[str] = Field(default_factory=list)


class AISemanticPreviewRequestModel(BaseModel):
    """Represents a request for semantic field value previews."""

    description: str = Field(min_length=1)
