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


class GenerationSemanticCallProgress(BaseModel):
    """Telemetry for one semantic Ollama call."""

    field: str
    call_number: int = Field(ge=1)
    requested_count: int = Field(ge=1)
    returned_count: int = Field(default=0, ge=0)
    elapsed_seconds: float | None = Field(default=None, ge=0)
    refill: bool = False


class GenerationChunkProgress(BaseModel):
    """Execution telemetry for one generation chunk."""

    chunk_number: int = Field(ge=1)
    target_rows: int = Field(ge=0)
    generated_rows: int = Field(default=0, ge=0)
    status: GenerationEntityStatus = GenerationEntityStatus.NOT_STARTED
    elapsed_seconds: float | None = Field(default=None, ge=0)
    peak_memory_mb: float | None = Field(default=None, ge=0)
    throughput_rows_per_second: float | None = Field(default=None, ge=0)
    unique_semantic_calls: list[GenerationSemanticCallProgress] = Field(
        default_factory=list,
    )


class GenerationEntityProgress(BaseModel):
    """Execution progress for one entity."""

    entity_name: str
    target_rows: int = Field(ge=0)
    generated_rows: int = Field(default=0, ge=0)
    chunk_size: int = Field(default=50, ge=1)
    completed_chunks: int = Field(default=0, ge=0)
    total_chunks: int = Field(default=0, ge=0)
    status: GenerationEntityStatus = GenerationEntityStatus.NOT_STARTED
    elapsed_seconds: float | None = Field(default=None, ge=0)
    peak_memory_mb: float | None = Field(default=None, ge=0)
    throughput_rows_per_second: float | None = Field(default=None, ge=0)
    vocabulary_semantic_calls: list[GenerationSemanticCallProgress] = Field(
        default_factory=list,
    )
    chunks: list[GenerationChunkProgress] = Field(
        default_factory=list,
    )


class GenerationValidationSummary(BaseModel):
    valid: bool
    entity_count: int = Field(ge=0)
    expected_rows: int = Field(ge=0)
    generated_rows: int = Field(ge=0)
    error_count: int = Field(ge=0)
    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    evidence: dict[str, Any] = Field(default_factory=dict)


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
    elapsed_seconds: float | None = Field(default=None, ge=0)
    peak_memory_mb: float | None = Field(default=None, ge=0)

    entities: list[GenerationEntityProgress] = Field(
        default_factory=list,
    )
    validation: GenerationValidationSummary | None = None

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

        if self.elapsed_seconds is None or self.elapsed_seconds <= 0:
            return None

        return self.total_generated_rows / self.elapsed_seconds

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
    elapsed_seconds: float | None = Field(default=None, ge=0)
    peak_memory_mb: float | None = Field(default=None, ge=0)
    throughput_rows_per_second: float | None = Field(default=None, ge=0)
    vocabulary_semantic_calls: list[GenerationSemanticCallProgress] = Field(
        default_factory=list,
    )
    chunks: list[GenerationChunkProgress] = Field(default_factory=list)


class GenerationQualityProfile(BaseModel):
    """Measured quality profile for a completed generation."""

    population_fidelity: dict[str, Any] = Field(default_factory=dict)
    distribution_fidelity: dict[str, Any] = Field(default_factory=dict)
    relationship_fidelity: dict[str, Any] = Field(default_factory=dict)
    identity_space_utilization: dict[str, Any] = Field(default_factory=dict)
    statistical_fidelity: dict[str, Any] = Field(default_factory=dict)
    performance: dict[str, Any] = Field(default_factory=dict)
    validation: dict[str, Any] = Field(default_factory=dict)


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
    quality: GenerationQualityProfile | None = None

