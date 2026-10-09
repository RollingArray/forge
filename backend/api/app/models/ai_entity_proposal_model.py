"""Request and response contracts for FORGE AI entity proposals."""

from pydantic import BaseModel, ConfigDict, Field, field_validator


class AIEntityProposalRequestModel(BaseModel):
    """Request an entity proposal without persisting it."""

    model_config = ConfigDict(extra="forbid")

    prompt: str = Field(min_length=1, max_length=2000)

    @field_validator("prompt", mode="before")
    @classmethod
    def validate_prompt(cls, value: object) -> object:
        if not isinstance(value, str):
            raise ValueError("prompt must be a string.")
        value = value.strip()
        if not value:
            raise ValueError("prompt must not be empty.")
        return value


class AIEntityProposalModel(BaseModel):
    """Structured entity proposal for user review."""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1)
    description: str = Field(min_length=1)
    population: int = Field(ge=0)
    reasoning: str = Field(min_length=1)
