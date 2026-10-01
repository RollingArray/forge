"""
File: generation_service.py
Purpose: FORGE generation planning and readiness service.
"""

from datetime import datetime, timezone
from math import ceil
from uuid import uuid4

import psutil

from app.models.generation_model import (
    GenerationChunkProgress,
    GenerationEntityProgress,
    GenerationEntityReadiness,
    GenerationEntityStatus,
    GenerationJobResponse,
    GenerationJobStatus,
    GenerationReadinessResponse,
    GenerationSemanticCallProgress,
)
from app.services.ai_service import AIService
from app.services.generation_planner import GenerationPlanner
from app.services.generation.executor import GenerationExecutor
from app.services.generation.validator import GenerationValidator
from app.services.generation.run_service import GenerationRunService
from app.services.generation_checkpoint_store import (
    GenerationCheckpointStore,
)
from app.services.generation_job_store import GenerationJobStore
from app.services.specification_service import SpecificationService


class GenerationService:
    """Provide generation planning and readiness information."""

    def __init__(
        self,
        specification_service: SpecificationService | None = None,
        generation_planner: GenerationPlanner | None = None,
        generation_run_service: GenerationRunService | None = None,
        ai_service: AIService | None = None,
        checkpoint_store: GenerationCheckpointStore | None = None,
    ) -> None:
        self._specification_service = (
            specification_service
            if specification_service is not None
            else SpecificationService()
        )
        self._generation_planner = (
            generation_planner
            if generation_planner is not None
            else GenerationPlanner()
        )
        self._generation_run_service = generation_run_service
        self._ai_service = ai_service
        self._job_store = GenerationJobStore()
        self._checkpoint_store = (
            checkpoint_store
            if checkpoint_store is not None
            else GenerationCheckpointStore()
        )
        self._jobs: dict[str, GenerationJobResponse] = {}

    def get_readiness(
        self,
        data_model_id: str,
    ) -> GenerationReadinessResponse | None:
        """Build the generation readiness contract for a Data Model."""

        specification = self._specification_service.get_specification(
            data_model_id=data_model_id,
        )

        if specification is None:
            return None

        plan = self._generation_planner.build(
            specification=specification,
        )

        entity_plans = {
            entity_plan.entity_name: entity_plan for entity_plan in plan.entities
        }

        entities = [
            GenerationEntityReadiness(
                entity_name=entity_name,
                target_rows=entity_plans[entity_name].target_rows,
                generation_order=index,
                dependencies=[
                    dependency.parent_entity
                    for dependency in entity_plans[entity_name].dependencies
                ],
            )
            for index, entity_name in enumerate(
                plan.generation_order,
                start=1,
            )
        ]

        return GenerationReadinessResponse(
            data_model_id=data_model_id,
            ready=bool(entities),
            entity_count=len(entities),
            total_target_rows=sum(entity.target_rows for entity in entities),
            generation_order=[entity.entity_name for entity in entities],
            entities=entities,
            generation=specification.get("generation", {}),
        )

    def create_job(
        self,
        data_model_id: str,
    ) -> GenerationJobResponse | None:
        """Create a generation job without executing it."""

        specification = self._specification_service.get_specification(
            data_model_id=data_model_id,
        )

        if specification is None:
            return None

        plan = self._generation_planner.build(
            specification=specification,
        )

        entity_plans = {
            entity_plan.entity_name: entity_plan for entity_plan in plan.entities
        }

        now = datetime.now(timezone.utc)
        job_id = f"FORGE-{uuid4().hex.upper()}"

        chunk_size = 50

        entities = [
            GenerationEntityProgress(
                entity_name=entity_name,
                target_rows=entity_plans[entity_name].target_rows,
                chunk_size=chunk_size,
                total_chunks=(
                    ceil(entity_plans[entity_name].target_rows / chunk_size)
                    if entity_plans[entity_name].target_rows > 0
                    else 0
                ),
            )
            for entity_name in plan.generation_order
        ]

        job = GenerationJobResponse(
            data_model_id=data_model_id,
            job_id=job_id,
            status=GenerationJobStatus.CREATED,
            created_at=now,
            total_target_rows=sum(entity.target_rows for entity in entities),
            total_generated_rows=0,
            progress=0.0,
            entities=entities,
        )

        self._jobs[job_id] = job
        self._job_store.save(job)

        return job

    def start_job(
        self,
        data_model_id: str,
        job_id: str,
    ) -> GenerationJobResponse | None:
        """Prepare a generation job for asynchronous execution."""

        job = self._jobs.get(job_id)

        if job is None:
            return None

        if job.data_model_id != data_model_id:
            return None

        if job.status != GenerationJobStatus.CREATED:
            raise ValueError(
                f"Generation job '{job_id}' cannot be started from "
                f"status '{job.status}'."
            )

        specification = self._specification_service.get_specification(
            data_model_id=data_model_id,
        )

        if specification is None:
            return None

        job.status = GenerationJobStatus.PLANNING
        job.started_at = datetime.now(timezone.utc)
        self._job_store.save(job)

        plan = self._generation_planner.build(
            specification=specification,
        )

        job.status = GenerationJobStatus.RUNNING
        self._job_store.save(job)

        seed = specification.get("generation", {}).get("seed", 42)
        chunk_size = (
            job.entities[0].chunk_size
            if job.entities
            else 50
        )

        checkpoint = self._checkpoint_store.create_checkpoint(
            job_id=job.job_id,
            specification=specification,
            seed=seed,
            chunk_size=chunk_size,
            entity_targets={
                entity.entity_name: entity.target_rows
                for entity in job.entities
            },
        )

        self._checkpoint_store.save(
            job_id=job.job_id,
            seed=checkpoint["seed"],
            entities=checkpoint["entities"],
            specification_hash=checkpoint["specification_hash"],
            chunk_size=checkpoint["chunk_size"],
        )

        return job

    def execute_job(
        self,
        data_model_id: str,
        job_id: str,
    ) -> None:
        """Execute a started generation job in the background."""

        job = self._jobs.get(job_id)

        if job is None:
            return

        if job.data_model_id != data_model_id:
            return

        if job.status != GenerationJobStatus.RUNNING:
            return

        specification = self._specification_service.get_specification(
            data_model_id=data_model_id,
        )

        if specification is None:
            job.status = GenerationJobStatus.FAILED
            job.error = "Data model not found."
            job.completed_at = datetime.now(timezone.utc)
            self._job_store.save(job)
            return

        try:
            process = psutil.Process()
            peak_memory_bytes = process.memory_info().rss

            plan = self._generation_planner.build(
                specification=specification,
            )

            generation = specification.get("generation") or {}
            seed = generation.get("seed", 42)

            run_service = GenerationRunService(
                executor=GenerationExecutor(
                    seed=seed,
                    ai_service=self._ai_service,
                    checkpoint_store=self._checkpoint_store,
                ),
                validator=GenerationValidator(),
            )

            def on_chunk_completed(
                entity_name: str,
                chunk_number: int,
                total_chunks: int,
                generated_rows: int,
                _chunk_rows: list[dict[str, object]],
                chunk_elapsed_seconds: float | None = None,
                chunk_peak_memory_mb: float | None = None,
                unique_semantic_calls: list[dict[str, object]] | None = None,
                vocabulary_semantic_calls: list[dict[str, object]] | None = None,
            ) -> None:
                existing_checkpoint = (
                    self._checkpoint_store.get(
                        job.job_id,
                    )
                    or {}
                )

                previously_committed_rows = (
                    existing_checkpoint
                    .get("entities", {})
                    .get(entity_name, {})
                    .get("committed_rows", 0)
                )

                if not isinstance(previously_committed_rows, int):
                    previously_committed_rows = 0

                durable_generated_rows = (
                    previously_committed_rows + len(_chunk_rows)
                )

                for entity_progress in job.entities:
                    if entity_progress.entity_name == entity_name:
                        entity_progress.generated_rows = durable_generated_rows
                        entity_progress.completed_chunks = chunk_number
                        entity_progress.total_chunks = total_chunks
                        entity_progress.status = GenerationEntityStatus.RUNNING
                        entity_progress.vocabulary_semantic_calls = [
                            GenerationSemanticCallProgress.model_validate(call)
                            for call in (vocabulary_semantic_calls or [])
                        ]

                        entity_progress.chunks = [
                            chunk
                            for chunk in entity_progress.chunks
                            if chunk.chunk_number != chunk_number
                        ]

                        entity_progress.chunks.append(
                            GenerationChunkProgress(
                                chunk_number=chunk_number,
                                target_rows=len(_chunk_rows),
                                generated_rows=len(_chunk_rows),
                                status=GenerationEntityStatus.COMPLETED,
                                elapsed_seconds=chunk_elapsed_seconds,
                                peak_memory_mb=chunk_peak_memory_mb,
                                throughput_rows_per_second=(
                                    len(_chunk_rows) / chunk_elapsed_seconds
                                    if chunk_elapsed_seconds
                                    and chunk_elapsed_seconds > 0
                                    else None
                                ),
                                unique_semantic_calls=[
                                    GenerationSemanticCallProgress.model_validate(call)
                                    for call in (unique_semantic_calls or [])
                                ],
                            )
                        )

                        entity_progress.chunks.sort(
                            key=lambda chunk: chunk.chunk_number
                        )
                        break

                job.total_generated_rows = sum(
                    entity.generated_rows for entity in job.entities
                )

                job.progress = (
                    job.total_generated_rows / job.total_target_rows
                    if job.total_target_rows > 0
                    else 1.0
                )

                self._job_store.save(job)

                existing_entities = (
                    existing_checkpoint.get("entities") or {}
                )

                entities = {}

                for entity in job.entities:
                    existing_entity = (
                        existing_entities.get(
                            entity.entity_name,
                        )
                        or {}
                    )

                    completed_chunks = list(
                        existing_entity.get(
                            "completed_chunks",
                            [],
                        )
                    )

                    if (
                        entity.entity_name == entity_name
                        and chunk_number not in completed_chunks
                    ):
                        completed_chunks.append(chunk_number)
                        completed_chunks.sort()

                    entities[entity.entity_name] = {
                        "target_rows": entity.target_rows,
                        "completed_chunks": completed_chunks,
                    }

                self._checkpoint_store.save(
                    job_id=job.job_id,
                    seed=existing_checkpoint.get(
                        "seed",
                        seed,
                    ),
                    entities=entities,
                    specification_hash=existing_checkpoint.get(
                        "specification_hash",
                        "",
                    ),
                    chunk_size=existing_checkpoint.get(
                        "chunk_size",
                        job.entities[0].chunk_size
                        if job.entities
                        else 1,
                    ),
                )

            def on_entity_completed(entity_run) -> None:
                for entity_progress in job.entities:
                    if entity_progress.entity_name == entity_run.entity_name:
                        entity_progress.generated_rows = entity_run.generated_rows
                        entity_progress.status = GenerationEntityStatus.COMPLETED
                        entity_progress.elapsed_seconds = entity_run.elapsed_seconds
                        entity_progress.peak_memory_mb = entity_run.peak_memory_mb
                        entity_progress.throughput_rows_per_second = (
                            entity_run.generated_rows / entity_run.elapsed_seconds
                            if entity_run.elapsed_seconds
                            and entity_run.elapsed_seconds > 0
                            else None
                        )
                        entity_progress.vocabulary_semantic_calls = list(entity_run.vocabulary_semantic_calls)
                        break

                job.total_generated_rows = sum(
                    entity.generated_rows for entity in job.entities
                )

                job.progress = (
                    job.total_generated_rows / job.total_target_rows
                    if job.total_target_rows > 0
                    else 1.0
                )

                self._job_store.save(job)

            result = run_service.run(
                specification=specification,
                plan=plan,
                data_model_id=data_model_id,
                job_id=job_id,
                on_entity_completed=on_entity_completed,
                on_chunk_completed=on_chunk_completed,
            )

            peak_memory_bytes = max(
                peak_memory_bytes,
                process.memory_info().rss,
            )

            job.status = result.status
            job.total_generated_rows = result.generated_rows
            job.elapsed_seconds = result.elapsed_seconds
            job.peak_memory_mb = peak_memory_bytes / (1024 * 1024)
            job.progress = (
                result.generated_rows / result.requested_rows
                if result.requested_rows > 0
                else 1.0
            )

            job.entities = [
                GenerationEntityProgress(
                    entity_name=entity.entity_name,
                    target_rows=entity.target_rows,
                    generated_rows=entity.generated_rows,
                    chunk_size=50,
                    completed_chunks=(
                        ceil(entity.generated_rows / 50)
                        if entity.generated_rows > 0
                        else 0
                    ),
                    total_chunks=(
                        ceil(entity.target_rows / 50) if entity.target_rows > 0 else 0
                    ),
                    status=(
                        GenerationEntityStatus.COMPLETED
                        if entity.generated_rows == entity.target_rows
                        else GenerationEntityStatus.FAILED
                    ),
                    elapsed_seconds=entity.elapsed_seconds,
                    peak_memory_mb=entity.peak_memory_mb,
                    throughput_rows_per_second=(
                        entity.generated_rows / entity.elapsed_seconds
                        if entity.elapsed_seconds and entity.elapsed_seconds > 0
                        else None
                    ),
                    vocabulary_semantic_calls=list(entity.vocabulary_semantic_calls),
                    chunks=entity.chunks,
                )
                for entity in result.entities
            ]

            job.completed_at = datetime.now(timezone.utc)

            if not result.validation.valid:
                job.error = (
                    result.validation.errors[0]
                    if result.validation.errors
                    else "Generation validation failed."
                )

            self._job_store.save(job)

        except Exception as exc:
            job.status = GenerationJobStatus.FAILED
            job.error = str(exc)
            job.completed_at = datetime.now(timezone.utc)
            self._job_store.save(job)

    def get_job(
        self,
        job_id: str,
    ) -> GenerationJobResponse | None:
        """Return a generation job from memory or persistent storage."""

        job = self._jobs.get(job_id)

        if job is not None:
            return job

        job = self._job_store.get(job_id)

        if job is not None:
            self._jobs[job_id] = job

        return job
