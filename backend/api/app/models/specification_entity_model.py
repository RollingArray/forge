"""
File: specification_entity_model.py
Purpose: Pydantic models for FORGE specification entities.

Author: Ranjoy Sen
Email: ranjoy.sen@collins.com
"""

from pydantic import BaseModel, ConfigDict, Field, field_validator


class EntityPopulationModel(BaseModel):
    """Population configuration for a FORGE entity."""

    model_config = ConfigDict(extra="forbid")

    count: int | None = Field(
        default=None,
        ge=0,
    )

    @field_validator("count", mode="before")
    @classmethod
    def validate_count(cls, value: object) -> object:
        """Reject booleans even though bool is an int subclass in Python."""

        if isinstance(value, bool):
            raise ValueError("population.count must be an integer.")

        return value


class CreateEntityRequest(BaseModel):
    """Request to create a FORGE specification entity."""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(
        min_length=1,
    )
    population: EntityPopulationModel | None = None

    @field_validator("name", mode="before")
    @classmethod
    def validate_name(cls, value: object) -> object:
        """Require a non-empty entity name after trimming whitespace."""

        if not isinstance(value, str):
            raise ValueError("name must be a string.")

        value = value.strip()

        if not value:
            raise ValueError("name must not be empty.")

        return value
