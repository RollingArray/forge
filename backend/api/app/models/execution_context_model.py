"""Minimal API models for the execution navigation selector."""

from datetime import datetime

from pydantic import BaseModel, Field

from app.models.generation_model import GenerationJobStatus


class ExecutionContextJobModel(BaseModel):
    """Minimal generation job information for navigation."""

    job_id: str
    status: GenerationJobStatus
    progress: float = Field(ge=0.0, le=1.0)
    total_target_rows: int = Field(ge=0)
    total_generated_rows: int = Field(ge=0)
    created_at: datetime


class ExecutionContextDataModel(BaseModel):
    """A visible data model and its generation jobs."""

    data_model_id: str
    name: str
    jobs: list[ExecutionContextJobModel] = Field(default_factory=list)


class ExecutionContextResponse(BaseModel):
    """All data models available to the execution navigation selector."""

    data_models: list[ExecutionContextDataModel] = Field(default_factory=list)
