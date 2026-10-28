"""
FORGE API contracts for whole-specification authoring proposals.
"""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class AIWholeSpecificationProposalRequestModel(BaseModel):
    """Plain-English or tabular input for specification authoring."""

    model_config = ConfigDict(extra="forbid")

    prompt: str = Field(min_length=1, max_length=20000)


class AIWholeSpecificationProposalResponseModel(BaseModel):
    """Reviewable specification proposal and deterministic findings."""

    model_config = ConfigDict(extra="forbid")

    status: str
    message: str
    specification: dict[str, Any] | None
    assumptions: list[str]
    clarification_questions: list[str]
    reasoning: str
    validation: dict[str, Any]
    recommendations: list[dict[str, Any]] = Field(default_factory=list)
    decision_items: list[dict[str, Any]] = Field(default_factory=list)
