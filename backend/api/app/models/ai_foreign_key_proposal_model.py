from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


ForeignKeyProposalStatus = Literal[
    "PROPOSE",
    "CLARIFY",
    "UNSUPPORTED",
]


class AIForeignKeyProposalModel(BaseModel):
    """Proposed FORGE foreign key mapping."""

    model_config = ConfigDict(extra="forbid")

    source_entity: str = Field(min_length=1)
    source_fields: list[str] = Field(min_length=1)
    target_entity: str = Field(min_length=1)


class AIForeignKeyProposalResponseModel(BaseModel):
    """Response returned by FORGE AI foreign-key authoring."""

    model_config = ConfigDict(extra="forbid")

    status: ForeignKeyProposalStatus
    message: str = Field(min_length=1)
    proposal: AIForeignKeyProposalModel | None = None


class AIForeignKeyProposalRequestModel(BaseModel):
    """Request for an AI foreign-key proposal."""

    model_config = ConfigDict(extra="forbid")

    mode: Literal["CREATE", "EDIT"]
    entities: list[dict[str, Any]] = Field(min_length=2)
    request: str = Field(min_length=1)
    existing_foreign_key: dict[str, Any] | None = None
