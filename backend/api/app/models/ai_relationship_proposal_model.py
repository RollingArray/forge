from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


RelationshipProposalStatus = Literal[
    "PROPOSE",
    "CLARIFY",
    "UNSUPPORTED",
]


class AIRelationshipProposalModel(BaseModel):
    """Proposed FORGE relationship."""

    model_config = ConfigDict(extra="forbid")

    source_entity: str = Field(min_length=1)
    source_field: str = Field(min_length=1)
    target_entity: str = Field(min_length=1)
    target_field: str = Field(min_length=1)

    type: Literal[
        "ONE_TO_ONE",
        "ONE_TO_MANY",
        "MANY_TO_ONE",
        "MANY_TO_MANY",
    ]

    source_participation: Literal[
        "MANDATORY",
        "OPTIONAL",
    ]

    target_participation: Literal[
        "MANDATORY",
        "OPTIONAL",
    ]


class AIRelationshipProposalResponseModel(BaseModel):
    """Response returned by FORGE AI relationship authoring."""

    model_config = ConfigDict(extra="forbid")

    status: RelationshipProposalStatus
    message: str = Field(min_length=1)
    proposal: AIRelationshipProposalModel | None = None


class AIRelationshipProposalRequestModel(BaseModel):
    """Request for an AI relationship proposal."""

    model_config = ConfigDict(extra="forbid")

    mode: Literal["CREATE", "EDIT"]
    entities: list[dict[str, Any]] = Field(min_length=2)
    request: str = Field(min_length=1)
    existing_relationship: dict[str, Any] | None = None
