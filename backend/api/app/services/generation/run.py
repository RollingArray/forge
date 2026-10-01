from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.models.generation_model import GenerationSemanticCallProgress
from app.services.generation.context import GenerationContext


@dataclass(frozen=True)
class GenerationChunkRun:
    chunk_number: int
    target_rows: int
    generated_rows: int
    elapsed_seconds: float | None = None
    peak_memory_mb: float | None = None
    unique_semantic_calls: tuple[GenerationSemanticCallProgress, ...] = ()


@dataclass(frozen=True)
class GenerationEntityRun:
    entity_name: str
    target_rows: int
    generated_rows: int
    elapsed_seconds: float | None = None
    peak_memory_mb: float | None = None
    vocabulary_semantic_calls: tuple[GenerationSemanticCallProgress, ...] = ()
    chunks: tuple[GenerationChunkRun, ...] = ()


@dataclass(frozen=True)
class GenerationRun:
    context: GenerationContext
    elapsed_seconds: float
    entities: tuple[GenerationEntityRun, ...]

    @property
    def generated_rows(self) -> int:
        return sum(
            entity.generated_rows
            for entity in self.entities
        )

    @property
    def target_rows(self) -> int:
        return sum(
            entity.target_rows
            for entity in self.entities
        )
