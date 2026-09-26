"""
File: specification_model.py
Purpose: API model for FORGE model specifications.

Author: Ranjoy Sen
Email: ranjoy.sen@collins.com
"""

from typing import Any

from pydantic import BaseModel, ConfigDict


class SpecificationModel(BaseModel):
    """Canonical FORGE specification returned by the API."""

    model_config = ConfigDict(extra="allow")

    version: str
    vocabulary_version: str
    model: dict[str, Any]
    generation: dict[str, Any]
    entities: list[dict[str, Any]]
    relationships: list[dict[str, Any]]
    foreign_keys: list[dict[str, Any]]
    constraints: list[dict[str, Any]]
    dependencies: list[dict[str, Any]]
    statistical_behavior: list[dict[str, Any]]
    scenarios: list[dict[str, Any]]
