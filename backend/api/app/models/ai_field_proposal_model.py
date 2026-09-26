"""
============================================================================
FORGE — Framework for Observed Rules, Generation & Engineered Data
============================================================================

File: ai_field_proposal_model.py
Purpose: Defines the API contract for AI-assisted field proposals.

Author: Ranjoy Sen
Email: ranjoy.sen@collins.com

============================================================================
"""

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


FieldProposalStatus = Literal[
    "PROPOSE",
    "CLARIFY",
    "UNSUPPORTED",
]

FieldType = Literal[
    "IDENTIFIER",
    "STRING",
    "INTEGER",
    "DECIMAL",
    "BOOLEAN",
    "CATEGORICAL",
]


class AIFieldIdentityProposalModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    strategy: Literal["SEQUENTIAL_ID"]


class AIFieldGenerationProposalModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    strategy: Literal["RANDOM"] | None = None
    distribution: str | None = None
    generator: str | None = None
    parameters: dict[str, Any] | None = None


class AIFieldProposalModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1)
    type: FieldType
    identity: AIFieldIdentityProposalModel | None = None
    generation: AIFieldGenerationProposalModel | None = None


class AIFieldProposalResponseModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: FieldProposalStatus
    message: str = Field(min_length=1)
    proposal: AIFieldProposalModel | None = None


class AIFieldProposalRequestModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    mode: Literal["CREATE", "EDIT"]
    entity_name: str = Field(min_length=1)
    request: str = Field(min_length=1)
    existing_field: dict[str, Any] | None = None
