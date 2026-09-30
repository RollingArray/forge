from __future__ import annotations

from typing import Any, Callable

from app.models.generation_model import (
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
        on_chunk_completed: Callable[[str, int, int, int], None] | None = None,
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
