"""
File: data_model_access.py
Purpose: Domain interface for FORGE data model access.

Author: Ranjoy Sen
Email: ranjoy.sen@collins.com
"""

from dataclasses import dataclass
from datetime import datetime

from app.constants.data_model_access import DataModelAccessRole


@dataclass(frozen=True)
class DataModelAccess:
    """Represent a user's access to a shared FORGE data model."""

    data_model_id: str
    user_id: str
    role: DataModelAccessRole
    granted_at: datetime
