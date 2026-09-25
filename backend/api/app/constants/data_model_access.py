"""
File: data_model_access.py
Purpose: Access roles for shared FORGE data models.

Author: Ranjoy Sen
Email: ranjoy.sen@collins.com
"""

from enum import StrEnum


class DataModelAccessRole(StrEnum):
    """Roles granted to users other than the data model owner."""

    CONTRIBUTOR = "CONTRIBUTOR"
    VIEWER = "VIEWER"
