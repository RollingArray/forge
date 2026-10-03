"""
FORGE generation execution journal models.

This module defines the durable, structured history of a generation job.
It is intentionally scoped to model/job/generation activity rather than
general application logging.
"""

from enum import StrEnum

from pydantic import BaseModel, Field


class GenerationLogStage(StrEnum):
    PREPARING = "PREPARING"
    ENTITY_GENERATION = "ENTITY_GENERATION"
    CHUNK_GENERATION = "CHUNK_GENERATION"
    FIELD_GENERATION = "FIELD_GENERATION"
    SEMANTIC_GENERATION = "SEMANTIC_GENERATION"
    CHUNK_COMMITTED = "CHUNK_COMMITTED"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class GenerationLogStatus(StrEnum):
    STARTED = "STARTED"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class GenerationLogEntry(BaseModel):
    """
    One meaningful activity recorded during a generation job.
    """

    sequence: int
    timestamp: str | None = None

    entity_name: str | None = None
    stage: GenerationLogStage
    status: GenerationLogStatus

    field_name: str | None = None
    chunk_number: int | None = None
    call_number: int | None = None
    requested_count: int | None = None
    generated_rows: int | None = None

    elapsed_seconds: float | None = None
    throughput_rows_per_second: float | None = None
    peak_memory_mb: float | None = None


class GenerationLogDocument(BaseModel):
    """
    Durable generation history for one generation job.
    """

    schema_version: int = 1
    data_model_id: str
    job_id: str
    user_id: str | None = None
    entries: list[GenerationLogEntry] = Field(default_factory=list)
