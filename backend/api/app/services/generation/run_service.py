from __future__ import annotations

from typing import Any, Callable

from app.models.generation_model import (
    GenerationSemanticCallProgress,
    GenerationChunkProgress,
    GenerationEntityResult,
    GenerationJobStatus,
    GenerationResult,
    GenerationValidationSummary,
)
from app.services.generation.executor import GenerationExecutor
from app.services.generation_planner import GenerationPlan
from app.services.generation.validator import GenerationValidator


class GenerationRunService:
    """Compose production generation execution and validation."""

    def __init__(
        self,
        *,
        executor: GenerationExecutor,
        validator: GenerationValidator,
    ) -> None:
        self._executor = executor
        self._validator = validator

    def run(
        self,
        *,
        specification: dict[str, Any],
        plan: GenerationPlan,
        data_model_id: str,
        job_id: str,
        on_entity_completed: Callable[[Any], None] | None = None,
        on_chunk_completed: Callable[
            [str, int, int, int, list[dict[str, Any]], float, float],
            None,
        ] | None = None,
    ) -> GenerationResult:
        generation = specification.get("generation") or {}

        seed = generation.get("seed", 42)
        scenario = generation.get("scenario", "NORMAL")

        run = self._executor.execute(
            specification=specification,
            plan=plan,
            job_id=job_id,
            on_entity_completed=on_entity_completed,
            on_chunk_completed=on_chunk_completed,
        )

        validation = self._validator.validate(
            specification=specification,
            job_id=job_id,
        )

        entities = [
            GenerationEntityResult(
                entity_name=entity.entity_name,
                target_rows=entity.target_rows,
                generated_rows=entity.generated_rows,
                elapsed_seconds=entity.elapsed_seconds,
                peak_memory_mb=entity.peak_memory_mb,
                throughput_rows_per_second=(
                    entity.generated_rows / entity.elapsed_seconds
                    if entity.elapsed_seconds
                    and entity.elapsed_seconds > 0
                    else None
                ),
                vocabulary_semantic_calls=list(entity.vocabulary_semantic_calls),
                chunks=[
                    GenerationChunkProgress(
                        chunk_number=chunk.chunk_number,
                        target_rows=chunk.target_rows,
                        generated_rows=chunk.generated_rows,
                        status=GenerationJobStatus.COMPLETED,
                        elapsed_seconds=chunk.elapsed_seconds,
                        peak_memory_mb=chunk.peak_memory_mb,
                        throughput_rows_per_second=(
                            chunk.generated_rows / chunk.elapsed_seconds
                            if chunk.elapsed_seconds
                            and chunk.elapsed_seconds > 0
                            else None
                        ),
                        unique_semantic_calls=[
                            GenerationSemanticCallProgress.model_validate(
                                call
                            )
                            for call in chunk.unique_semantic_calls
                        ],
                    )
                    for chunk in entity.chunks
                ],
            )
            for entity in run.entities
        ]

        validation_summary = GenerationValidationSummary(
            valid=validation.valid,
            entity_count=validation.entity_count,
            expected_rows=validation.expected_rows,
            generated_rows=validation.generated_rows,
            error_count=validation.error_count,
            errors=validation.errors,
            warnings=validation.warnings,
        )

        status = (
            GenerationJobStatus.COMPLETED
            if validation.valid
            else GenerationJobStatus.FAILED
        )

        return GenerationResult(
            data_model_id=data_model_id,
            job_id=job_id,
            status=status,
            seed=seed,
            scenario=scenario,
            requested_rows=run.target_rows,
            generated_rows=run.generated_rows,
            elapsed_seconds=run.elapsed_seconds,
            entities=entities,
            validation=validation_summary,
        )
