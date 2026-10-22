"""
File: favorite_model.py
Purpose: Request and response models for Favorites.
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, model_validator

from app.interfaces.favorite import FavoriteResourceType, JOB_RESOURCE_TYPES


class CreateFavoriteRequestModel(BaseModel):
    """Request to favorite a data model or generation execution."""

    model_config = ConfigDict(extra="forbid")

    resource_type: FavoriteResourceType
    data_model_id: str
    job_id: str | None = None

    @model_validator(mode="after")
    def validate_resource_reference(self):
        if not self.data_model_id.strip():
            raise ValueError("data_model_id must not be empty.")

        if self.resource_type in JOB_RESOURCE_TYPES:
            if self.job_id is None or not self.job_id.strip():
                raise ValueError("job_id is required for this resource type.")
        elif self.job_id is not None:
            raise ValueError("job_id is only valid for job-specific resources.")

        return self


class FavoriteResponseModel(BaseModel):
    """Favorite details returned to the authenticated user."""

    favorite_id: str
    resource_type: FavoriteResourceType
    data_model_id: str
    data_model_name: str
    job_id: str | None
    status: str | None = None
    created_at: datetime
