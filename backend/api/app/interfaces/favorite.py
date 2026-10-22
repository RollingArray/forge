"""
File: favorite.py
Purpose: Domain model for a user's favorite resource.
"""

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum


class FavoriteResourceType(StrEnum):
    """Supported canonical resources and temporary legacy values."""

    MODEL_STUDIO = "model_studio"
    MODEL_VALIDATION = "model_validation"
    POPULATION_PLAN = "population_plan"
    GENERATION = "generation"
    GENERATION_EXECUTION = "generation_execution"
    GENERATION_RESULTS = "generation_results"
    VALIDATION_ANALYSIS = "validation_analysis"
    QUALITY_ANALYSIS = "quality_analysis"

    # Temporary compatibility for existing callers and persisted records.
    DATA_MODEL = "data_model"
    EXECUTION = "execution"


JOB_RESOURCE_TYPES = frozenset({
    FavoriteResourceType.GENERATION_EXECUTION,
    FavoriteResourceType.GENERATION_RESULTS,
    FavoriteResourceType.VALIDATION_ANALYSIS,
    FavoriteResourceType.QUALITY_ANALYSIS,
    FavoriteResourceType.EXECUTION,
})


@dataclass(frozen=True)
class Favorite:
    """Represent a resource favorited by an authenticated user."""

    favorite_id: str
    user_id: str
    resource_type: FavoriteResourceType
    data_model_id: str
    job_id: str | None
    created_at: datetime
