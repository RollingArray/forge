"""
File: data_model_access_model.py
Purpose: API models for FORGE data model access.

Author: Ranjoy Sen
Email: ranjoy.sen@collins.com
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.constants.data_model_access import DataModelAccessRole


class GrantDataModelAccessRequestModel(BaseModel):
    """Request to grant a user access to a data model."""

    user_id: str
    role: DataModelAccessRole


class UpdateDataModelAccessRequestModel(BaseModel):
    role: DataModelAccessRole


class DataModelAccessModel(BaseModel):
    """Represent a data model access record in the API."""

    model_config = ConfigDict(from_attributes=True)

    data_model_id: str
    user_id: str
    display_name: str
    email: str
    role: str
    granted_at: datetime | None
