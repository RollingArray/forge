"""
File: generation_model.py
Purpose: FORGE generation API models.
"""

from typing import Any

from pydantic import BaseModel, Field, computed_field


class GenerationEntityReadiness(BaseModel):
    """Readiness information for one entity."""

    entity_name: str
    target_rows: int = Field(ge=0)
    generation_order: int = Field(ge=0)
    dependencies: list[str] = Field(default_factory=list)


class GenerationReadinessResponse(BaseModel):
    """Structured readiness information for data generation."""

    data_model_id: str
    ready: bool
    entity_count: int = Field(ge=0)
    total_target_rows: int = Field(ge=0)
    generation_order: list[str] = Field(default_factory=list)
    entities: list[GenerationEntityReadiness] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    generation: dict[str, Any] = Field(default_factory=dict)


from datetime import datetime
from enum import StrEnum


class GenerationJobStatus(StrEnum):
    """Lifecycle state of a generation job."""

    CREATED = "CREATED"
    PLANNING = "PLANNING"
    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class GenerationEntityStatus(StrEnum):
    """Lifecycle state of one entity within a generation job."""

    NOT_STARTED = "NOT_STARTED"
    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class GenerationEntityProgress(BaseModel):
    """Execution progress for one entity."""

    entity_name: str
    target_rows: int = Field(ge=0)
    generated_rows: int = Field(default=0, ge=0)
    chunk_size: int = Field(default=50, ge=1)
    completed_chunks: int = Field(default=0, ge=0)
    total_chunks: int = Field(default=0, ge=0)
    status: GenerationEntityStatus = GenerationEntityStatus.NOT_STARTED


class GenerationJobResponse(BaseModel):
    """Production API representation of a generation job."""

    data_model_id: str
    job_id: str
    status: GenerationJobStatus

    created_at: datetime
    started_at: datetime | None = None
    completed_at: datetime | None = None

    total_target_rows: int = Field(ge=0)
    total_generated_rows: int = Field(default=0, ge=0)
    progress: float = Field(default=0.0, ge=0.0, le=1.0)

    entities: list[GenerationEntityProgress] = Field(
        default_factory=list,
    )

    error: str | None = None

    @computed_field
    @property
    def throughput_rows_per_second(self) -> float | None:
        if (
            self.started_at is None
            or self.completed_at is None
            or self.total_generated_rows <= 0
        ):
            return None

        elapsed_seconds = (
            self.completed_at - self.started_at
        ).total_seconds()

        if elapsed_seconds <= 0:
            return None

        return self.total_generated_rows / elapsed_seconds

class GenerationArtifactResponse(BaseModel):
    """One generated CSV artifact."""

    entity_name: str
    filename: str
    rows: int = Field(ge=0)
    size_bytes: int = Field(ge=0)


class GenerationArtifactPreviewResponse(BaseModel):
    """Preview of one generated CSV artifact."""

    entity_name: str
    filename: str
    columns: list[str] = Field(default_factory=list)
    rows: list[dict[str, Any]] = Field(default_factory=list)
    total_rows: int = Field(ge=0)
    preview_rows: int = Field(ge=0)


class GenerationEntityResult(BaseModel):
    entity_name: str
    target_rows: int = Field(ge=0)
    generated_rows: int = Field(ge=0)


class GenerationValidationSummary(BaseModel):
    valid: bool
    entity_count: int = Field(ge=0)
    expected_rows: int = Field(ge=0)
    generated_rows: int = Field(ge=0)
    error_count: int = Field(ge=0)
    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class GenerationResult(BaseModel):
    data_model_id: str
    job_id: str
    status: GenerationJobStatus
    seed: int
    scenario: str
    requested_rows: int = Field(ge=0)
    generated_rows: int = Field(ge=0)
    elapsed_seconds: float = Field(ge=0)
    entities: list[GenerationEntityResult] = Field(default_factory=list)
    validation: GenerationValidationSummary

