"""
FORGE Generation Core
Generation result contracts.

This module contains UI-independent result models for generation work.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class GenerationChunkStatus(str, Enum):
    """Execution status of a generation chunk."""

    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


@dataclass(frozen=True)
class GenerationChunkResult:
    """Result produced after processing one generation chunk."""

    entity_name: str
    chunk_number: int
    row_count: int
    status: GenerationChunkStatus
    elapsed_seconds: float
    output_path: str | None = None
    error: str | None = None
