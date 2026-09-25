"""
============================================================================
FORGE — Framework for Observed Rules, Generation & Engineered Data
============================================================================

File: ai_settings.py
Purpose: Loads and validates FORGE AI configuration.

Author: Ranjoy Sen
Email: ranjoy.sen@collins.com

============================================================================
"""

import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict


class AIConfiguration(BaseModel):
    """Configuration required by the FORGE AI provider."""

    model_config = ConfigDict(extra="forbid")

    provider: str
    base_url: str
    model: str
    capability_timeout_seconds: float
    generation_timeout_seconds: float


def load_ai_configuration() -> AIConfiguration:
    """Load and validate the FORGE AI configuration."""

    configuration_path = (
        Path(__file__).resolve().parents[2]
        / "config"
        / "ai.json"
    )

    with configuration_path.open(
        "r",
        encoding="utf-8",
    ) as configuration_file:
        configuration = json.load(configuration_file)

    return AIConfiguration.model_validate(configuration)
