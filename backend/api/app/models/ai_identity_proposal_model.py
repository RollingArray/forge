"""
File: ai_identity_proposal_model.py
Purpose: Pydantic models for FORGE AI entity identity proposals.

Author: Ranjoy Sen
Email: ranjoy.sen@collins.com
"""

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


IdentityProposalStatus = Literal[
    "PROPOSE",
    "CLARIFY",
    "UNSUPPORTED",
]


class AIIdentityProposalModel(BaseModel):
    """Proposed entity identity."""

    model_config = ConfigDict(extra="forbid")

    fields: list[str] = Field(
        min_length=1,
    )


class AIIdentityProposalResponseModel(BaseModel):
    """Response returned by FORGE AI identity authoring."""

    model_config = ConfigDict(extra="forbid")

    status: IdentityProposalStatus
    message: str = Field(min_length=1)
    proposal: AIIdentityProposalModel | None = None


class AIIdentityProposalRequestModel(BaseModel):
    """Request for an AI identity proposal."""

    model_config = ConfigDict(extra="forbid")

    mode: Literal["CREATE", "EDIT"]
    entity_name: str = Field(min_length=1)
    fields: list[dict[str, Any]] = Field(min_length=1)
    request: str = Field(min_length=1)
    existing_identity: dict[str, Any] | None = None
