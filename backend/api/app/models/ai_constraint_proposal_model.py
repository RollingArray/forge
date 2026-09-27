"""
FORGE AI constraint proposal models.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


ConstraintProposalStatus = Literal[
    "PROPOSE",
    "CLARIFY",
    "UNSUPPORTED",
]

ConstraintOperator = Literal[
    ">",
    ">=",
    "<",
    "<=",
    "==",
    "!=",
]


class AIConstraintProposalModel(BaseModel):
    """Proposed FORGE field constraint."""

    model_config = ConfigDict(extra="forbid")

    entity: str = Field(min_length=1)
    field: str = Field(min_length=1)
    operator: ConstraintOperator
    value: str | int | float | bool


class AIConstraintProposalResponseModel(BaseModel):
    """Response returned by FORGE AI constraint authoring."""

    model_config = ConfigDict(extra="forbid")

    status: ConstraintProposalStatus
    message: str = Field(min_length=1)
    proposal: AIConstraintProposalModel | None = None


class AIConstraintProposalRequestModel(BaseModel):
    """Request for an AI constraint proposal."""

    model_config = ConfigDict(extra="forbid")

    mode: Literal["CREATE", "EDIT"]
    entities: list[dict[str, Any]] = Field(min_length=1)
    request: str = Field(min_length=1)
    existing_constraint: dict[str, Any] | None = None
