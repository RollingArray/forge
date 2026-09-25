"""
File: user_search_result_model.py
Purpose: API response model for FORGE user search.

Author: Ranjoy Sen
Email: ranjoy.sen@collins.com
"""

from pydantic import BaseModel


class UserSearchResultModel(BaseModel):
    """Represent an existing FORGE user returned by user search."""

    user_id: str
    email: str
    display_name: str
