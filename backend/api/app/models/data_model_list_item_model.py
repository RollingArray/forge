# FORGE — Framework for Observed Rules, Generation & Engineered Data
# Production API model for Data Model list responses.

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class DataModelListItemModel(BaseModel):
    """API representation of a Data Model visible to the current user."""

    data_model_id: str
    owner_user_id: str
    name: str
    description: str
    color: str
    tags: list[str] = Field(default_factory=list, max_length=20)
    status: str
    created_at: datetime
    updated_at: datetime
    access_role: Literal["OWNER", "CONTRIBUTOR", "VIEWER"]
