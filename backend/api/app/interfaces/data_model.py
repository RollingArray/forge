"""
File: data_model.py
Purpose: Domain interface for FORGE data models.

Author: Ranjoy Sen
Email: ranjoy.sen@collins.com
"""

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class DataModel:
    """Represent a FORGE synthetic data model."""

    data_model_id: str
    owner_user_id: str
    name: str
    description: str
    color: str
    tags: list[str]
    status: str
    created_at: datetime
    updated_at: datetime
