"""
============================================================================
FORGE — Framework for Observed Rules, Generation & Engineered Data
============================================================================

File: ai_data_model_proposal_model.py
Purpose: Defines the API contract for AI-generated Data Model proposals.

Author: Ranjoy Sen
Email: ranjoy.sen@collins.com

============================================================================
"""

from pydantic import BaseModel, Field


class AIDataModelSuggestionRequestModel(BaseModel):
    """Request for an AI-generated Data Model proposal."""

    prompt: str = Field(
        min_length=1,
        max_length=4000,
    )


class AIDataModelProposalModel(BaseModel):
    """Structured AI proposal for a FORGE Data Model."""

    name: str
    description: str
    suggested_tags: list[str]
    reasoning: str
