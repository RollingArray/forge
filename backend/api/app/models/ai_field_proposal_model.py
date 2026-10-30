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

from app.constants.specification_vocabulary import (
    Distribution,
    FieldType,
    GenerationStrategy,
    IdentityStrategy,
    StringGenerator,
)

from pydantic import BaseModel, ConfigDict, Field


FieldProposalStatus = Literal[
    "PROPOSE",
    "CLARIFY",
    "UNSUPPORTED",
]


class AIFieldIdentityProposalModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    strategy: IdentityStrategy


class AIFieldGenerationProposalModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    strategy: GenerationStrategy | None = None
    distribution: Distribution | None = None
    generator: StringGenerator | None = None
    parameters: dict[str, Any] | None = None


class AIFieldProposalModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1)
    type: FieldType
    identity: AIFieldIdentityProposalModel | None = None
    generation: AIFieldGenerationProposalModel | None = None


class AIFieldProposalResponseModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    proposal_id: str = Field(min_length=1)
    status: FieldProposalStatus
    message: str = Field(min_length=1)
    proposal: AIFieldProposalModel | None = None


class AIFieldProposalRequestModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    data_model_id: str = Field(min_length=1)
    regenerate: bool = False

    mode: Literal["CREATE", "EDIT"]
    entity_name: str = Field(min_length=1)
    request: str = Field(min_length=1)
    existing_field: dict[str, Any] | None = None
