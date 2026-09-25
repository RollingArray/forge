"""
File: data_model_model.py
Purpose: API models for FORGE data models.

Author: Ranjoy Sen
Email: ranjoy.sen@collins.com
"""

from datetime import datetime

from pydantic import BaseModel, Field


DATA_MODEL_COLOR_PATTERN = r"^#[0-9A-Fa-f]{6}$"
DATA_MODEL_TAG_PATTERN = r"^\S(?:.*\S)?$"


class CreateDataModelRequestModel(BaseModel):
    """Request to create a FORGE data model."""

    name: str = Field(
        min_length=1,
        max_length=120,
    )

    description: str = Field(
        default="",
        max_length=500,
    )

    color: str = Field(
        pattern=DATA_MODEL_COLOR_PATTERN,
    )

    tags: list[str] = Field(
        default_factory=list,
        max_length=20,
    )


class UpdateDataModelRequestModel(BaseModel):
    """Request to update a FORGE data model."""

    name: str = Field(
        min_length=1,
        max_length=120,
    )

    description: str = Field(
        default="",
        max_length=500,
    )

    color: str = Field(
        pattern=DATA_MODEL_COLOR_PATTERN,
    )

    tags: list[str] = Field(
        default_factory=list,
        max_length=20,
    )


class DataModelModel(BaseModel):
    """API representation of a FORGE data model."""

    data_model_id: str
    owner_user_id: str
    name: str
    description: str
    color: str
    tags: list[str]
    status: str
    created_at: datetime
    updated_at: datetime
