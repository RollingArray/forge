"""
FORGE Generation Core
Generation job contract.

This module is UI-independent.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from uuid import uuid4


class GenerationJobStatus(str, Enum):
    """Lifecycle states for a generation job."""

    CREATED = "CREATED"
    PLANNING = "PLANNING"
    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class EntityGenerationStatus(str, Enum):
    """Lifecycle states for generation of an individual entity."""

    NOT_STARTED = "NOT_STARTED"
    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


def utc_now() -> str:
    """Return the current UTC timestamp as an ISO-8601 string."""

    return datetime.now(timezone.utc).isoformat()


@dataclass
class EntityGenerationProgress:
    """Progress information for one entity."""

    entity_name: str
    target_rows: int
    generated_rows: int = 0
    status: EntityGenerationStatus = EntityGenerationStatus.NOT_STARTED

    @property
    def progress(self) -> float:
        """Return entity progress as a value between 0 and 1."""

        if self.target_rows <= 0:
            return 0.0

        return min(self.generated_rows / self.target_rows, 1.0)


@dataclass
class GenerationJob:
    """Durable logical representation of a FORGE generation job."""

    specification_path: str
    job_id: str = field(
        default_factory=lambda: f"FORGE-{uuid4().hex[:12].upper()}"
    )
    status: GenerationJobStatus = GenerationJobStatus.CREATED
    created_at: str = field(default_factory=utc_now)
    started_at: str | None = None
    completed_at: str | None = None
    error: str | None = None
    entities: dict[str, EntityGenerationProgress] = field(
        default_factory=dict
    )

    @property
    def total_target_rows(self) -> int:
        """Return total rows requested across all entities."""

        return sum(
            entity.target_rows
            for entity in self.entities.values()
        )

    @property
    def total_generated_rows(self) -> int:
        """Return total rows generated across all entities."""

        return sum(
            entity.generated_rows
            for entity in self.entities.values()
        )

    @property
    def progress(self) -> float:
        """Return overall job progress as a value between 0 and 1."""

        if self.total_target_rows <= 0:
            return 0.0

        return min(
            self.total_generated_rows / self.total_target_rows,
            1.0,
        )


def create_generation_job(
    specification_path: str,
) -> GenerationJob:
    """
    Create a new generation job.

    Entity-level progress is populated later by the generation planner.
    """

    return GenerationJob(
        specification_path=specification_path,
    )
