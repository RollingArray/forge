"""
File: specification_field_model.py
Purpose: Pydantic models for FORGE specification fields.

Author: Ranjoy Sen
Email: ranjoy.sen@collins.com
"""

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


FieldType = Literal[
    "IDENTIFIER",
    "STRING",
    "INTEGER",
    "DECIMAL",
    "BOOLEAN",
    "CATEGORICAL",
]

IdentityStrategy = Literal[
    "SEQUENTIAL_ID",
]

GenerationStrategy = Literal[
    "RANDOM",
]

Distribution = Literal[
    "UNIFORM",
    "CATEGORICAL",
    "DISCRETE_UNIFORM",
    "NORMAL",
    "POISSON",
]

StringGenerator = Literal[
    "RANDOM_STRING",
    "PATTERN",
    "SEMANTIC",
]

StringCharacterSet = Literal[
    "ALPHA",
    "DIGITS",
    "ALPHANUMERIC",
]


class FieldIdentityModel(BaseModel):
    """Identity generation configuration for an IDENTIFIER field."""

    model_config = ConfigDict(extra="forbid")

    strategy: IdentityStrategy


class FieldGenerationModel(BaseModel):
    """Generation configuration for a FORGE field."""

    model_config = ConfigDict(extra="forbid")

    strategy: GenerationStrategy | None = None
    distribution: Distribution | None = None
    generator: StringGenerator | None = None
    parameters: dict[str, Any] | None = None


class CreateFieldRequest(BaseModel):
    """Request to add a field to a FORGE entity."""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1)
    type: FieldType
    identity: FieldIdentityModel | None = None
    generation: FieldGenerationModel | None = None

    @field_validator("name", mode="before")
    @classmethod
    def validate_name(cls, value: object) -> object:
        """Require a non-empty field name after trimming whitespace."""

        if not isinstance(value, str):
            raise ValueError("name must be a string.")

        value = value.strip()

        if not value:
            raise ValueError("name must not be empty.")

        return value


class UpdateFieldRequest(BaseModel):
    """Request to update an existing FORGE field."""

    model_config = ConfigDict(extra="forbid")

    name: str | None = Field(default=None, min_length=1)
    type: FieldType | None = None
    identity: FieldIdentityModel | None = None
    generation: FieldGenerationModel | None = None

    @field_validator("name", mode="before")
    @classmethod
    def validate_name(cls, value: object) -> object:
        """Require a non-empty field name when a name is supplied."""

        if value is None:
            return value

        if not isinstance(value, str):
            raise ValueError("name must be a string.")

        value = value.strip()

        if not value:
            raise ValueError("name must not be empty.")

        return value
