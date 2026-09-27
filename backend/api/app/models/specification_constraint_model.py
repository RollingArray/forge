"""
FORGE constraint request models.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


ConstraintOperator = Literal[
    ">",
    ">=",
    "<",
    "<=",
    "==",
    "!=",
]


class CreateConstraintRequest(BaseModel):
    """Request to create a FORGE constraint."""

    model_config = ConfigDict(extra="forbid")

    entity: str = Field(min_length=1)
    field: str = Field(min_length=1)
    operator: ConstraintOperator
    value: str | int | float | bool

    @field_validator("entity", "field")
    @classmethod
    def validate_name(cls, value: str) -> str:
        value = value.strip()

        if not value:
            raise ValueError("Value must not be empty.")

        return value


class DeleteConstraintRequest(BaseModel):
    """Identifies an existing FORGE constraint."""

    model_config = ConfigDict(extra="forbid")

    entity: str = Field(min_length=1)
    field: str = Field(min_length=1)
    operator: ConstraintOperator
    value: str | int | float | bool


class UpdateConstraintRequest(BaseModel):
    """Request to replace an existing FORGE constraint."""

    model_config = ConfigDict(extra="forbid")

    existing: DeleteConstraintRequest
    constraint: CreateConstraintRequest
