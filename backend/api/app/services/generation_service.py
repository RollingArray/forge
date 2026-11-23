"""
File: generation_service.py
Purpose: FORGE generation planning and readiness service.
"""

from datetime import datetime, timezone
import logging
import csv
from pathlib import Path
from math import ceil
from threading import Lock, Thread
from uuid import uuid4

import psutil

from app.repositories.file_lock import FileLockTimeout
from app.services.generation_execution_lease import generation_execution_lease

from app.constants.generation import (
    DEFAULT_GENERATION_CHUNK_SIZE,
    GENERATION_ALGORITHM_VERSION,
)

from app.models.generation_log_model import GenerationLogEntry
from app.models.generation_persistence import (
    GenerationCheckpointManifest,
    GenerationFinalizationStatus,
)
from app.models.generation_model import (
    GenerationChunkProgress,
    GenerationEntityProgress,
    GenerationEntityReadiness,
    GenerationEntityStatus,
    GenerationJobResponse,
    GenerationJobStatus,
    GenerationReadinessResponse,
    GenerationSemanticCallProgress,
    GenerationJobRecord,
    GenerationPreparationPhase,
    GenerationResumeIntent,
)
from app.services.ai_service import AIService
from app.services.generation_planner import GenerationPlanner
from app.services.generation.executor import GenerationExecutor
from app.services.generation.validator import GenerationValidator
from app.services.generation.run_service import GenerationRunService
from app.services.generation.quality import GenerationQualityService
from app.services.generation.artifact_reader import GenerationArtifactReader
from app.services.generation_checkpoint_store import (
    GenerationCheckpointStore,
    compute_specification_hash,
)
from app.services.generation_job_store import GenerationJobStore
from app.services.generation_quality_store import GenerationQualityStore
from app.services.generation_validation_store import GenerationValidationStore
from app.services.generation_event_broker import (
    GenerationEventBroker,
    SSE_DIAGNOSTICS_ENABLED,
)
from app.services.generation_log_store import GenerationLogStore
from app.services.specification_service import SpecificationService
from app.services.specification_validation_service import SpecificationValidationService
from app.services.specification_validation_error import SpecificationValidationError


logger = logging.getLogger(__name__)


def _format_sse_event_counts(counts: dict[str, int]) -> str:
    purposes = {
        "CHUNK_COMMITTED": "chunk/checkpoint progress",
        "ENTITY_COMPLETED": "entity completion",
        "GENERATION_ACTIVITY": "generation activity",
        "GENERATION_COMPLETED": "terminal job status",
        "SEMANTIC_CALL_STARTED": "semantic call started",
    }
    return ", ".join(
        f"{event_type}[{purposes.get(event_type, 'other')}]:{count}"
        for event_type, count in sorted(counts.items())
    ) or "none"



class GenerationService:
    """Provide generation planning and readiness information."""

    def __init__(
        self,
        specification_service: SpecificationService | None = None,
        generation_planner: GenerationPlanner | None = None,
        generation_run_service: GenerationRunService | None = None,
        ai_service: AIService | None = None,
        checkpoint_store: GenerationCheckpointStore | None = None,
        event_broker: GenerationEventBroker | None = None,
        generation_log_store: GenerationLogStore | None = None,
        specification_validation_service: SpecificationValidationService | None = None,
    ) -> None:
        self._specification_service = (
            specification_service
            if specification_service is not None
            else SpecificationService()
        )
        self._specification_validation_service = (
            specification_validation_service
            if specification_validation_service is not None
            else SpecificationValidationService()
        )
        self._generation_planner = (
            generation_planner
            if generation_planner is not None
            else GenerationPlanner()
        )
        self._generation_run_service = generation_run_service
        self._ai_service = ai_service
        self._job_store = GenerationJobStore()
        self._quality_store = GenerationQualityStore()
        self._validation_store = GenerationValidationStore()
        self._checkpoint_store = (
            checkpoint_store
            if checkpoint_store is not None
            else GenerationCheckpointStore()
        )
        self._event_broker = (
            event_broker
            if event_broker is not None
            else GenerationEventBroker(
                diagnostics_enabled=SSE_DIAGNOSTICS_ENABLED,
            )
        )
        self._generation_log_store = (
            generation_log_store
            if generation_log_store is not None
            else GenerationLogStore()
        )
        self._jobs: dict[str, GenerationJobResponse] = {}
        self._active_workers: set[tuple[str, str]] = set()
        self._worker_lock = Lock()

    def _get_or_load_job(
        self,
        *,
        data_model_id: str,
        job_id: str,
    ) -> GenerationJobResponse | None:
        """Load the authoritative persisted job and refresh the local cache."""

        job = self._job_store.get(
            data_model_id=data_model_id,
            job_id=job_id,
        )
        if job is None or job.data_model_id != data_model_id:
            self._jobs.pop(job_id, None)
            return None

        self._jobs[job_id] = job
        return job


    def _reconcile_recovery_checkpoint(
        self,
        *,
        data_model_id: str,
        job: GenerationJobRecord,
        specification: dict,
    ) -> GenerationCheckpointManifest:
        """Compatibility wrapper for validation and projection restoration."""

        manifest = self._validate_recovery_checkpoint(
            data_model_id=data_model_id,
            job=job,
            specification=specification,
        )

        self._restore_job_progress_from_manifest(
            job=job,
            manifest=manifest,
        )

        return manifest


    def _apply_manifest_progress_to_job(
        self,
        *,
        job: GenerationJobRecord,
        manifest: GenerationCheckpointManifest,
    ) -> None:
        """Rebuild the in-memory job projection from verified manifest evidence.

        This method does not persist the job or modify checkpoint state.
        """

        if (
            job.data_model_id != manifest.data_model_id
            or job.job_id != manifest.job_id
        ):
            raise ValueError(
                "Job identity does not match the checkpoint manifest."
            )

        if job.attempt_id != manifest.attempt_id:
            raise ValueError(
                "Job attempt ID does not match the checkpoint manifest."
            )

        if any(
            entity.chunk_size != manifest.chunk_size
            for entity in job.entities
        ):
            raise ValueError(
                "Job and checkpoint chunk sizes do not match."
            )

        if set(entity.entity_name for entity in job.entities) != set(
            manifest.entities
        ):
            raise ValueError(
                "Job entities do not match checkpoint manifest entities."
            )

        for entity in job.entities:
            entity_checkpoint = manifest.entities[entity.entity_name]

            if entity_checkpoint.target_rows != entity.target_rows:
                raise ValueError(
                    f"Checkpoint target rows do not match for "
                    f"'{entity.entity_name}'."
                )

            entity.generated_rows = entity_checkpoint.committed_rows
            entity.completed_chunks = len(entity_checkpoint.chunks)
            entity.total_chunks = (
                ceil(entity.target_rows / manifest.chunk_size)
                if entity.target_rows > 0
                else 0
            )

            entity.chunks = [
                GenerationChunkProgress(
                    chunk_number=chunk.chunk_number,
                    target_rows=chunk.row_count,
                    generated_rows=chunk.row_count,
                    status=GenerationEntityStatus.COMPLETED,
                )
                for chunk in entity_checkpoint.chunks
            ]

            # Runtime telemetry cannot be reconstructed from the manifest.
            entity.elapsed_seconds = None
            entity.peak_memory_mb = None
            entity.throughput_rows_per_second = None
            entity.vocabulary_semantic_calls = []

            if (
                entity_checkpoint.finalization.status
                == GenerationFinalizationStatus.COMMITTED
            ):
                entity.status = GenerationEntityStatus.COMPLETED
            elif entity_checkpoint.committed_rows > 0:
                entity.status = GenerationEntityStatus.RUNNING
            else:
                entity.status = GenerationEntityStatus.NOT_STARTED

        job.total_generated_rows = sum(
            entity.generated_rows for entity in job.entities
        )

        job.progress = (
            job.total_generated_rows / job.total_target_rows
            if job.total_target_rows > 0
            else 1.0
        )

    def _restore_job_progress_from_manifest(
        self,
        *,
        job: GenerationJobRecord,
        manifest: GenerationCheckpointManifest,
    ) -> None:
        """Rebuild and persist the job projection from verified evidence."""

        self._apply_manifest_progress_to_job(
            job=job,
            manifest=manifest,
        )

        self._job_store.save(job)
        self._jobs[job.job_id] = job

    def _ensure_initial_checkpoint(
        self,
        *,
        data_model_id: str,
        job: GenerationJobRecord,
        specification: dict,
    ) -> GenerationCheckpointManifest:
        """Create or validate the checkpoint for an initial preparation.

        CHECKPOINT_PENDING permits create-only initialization when the
        checkpoint is absent. An existing checkpoint is always validated.
        CHECKPOINT_READY requires an existing valid checkpoint.
        """

        if job.data_model_id != data_model_id:
            raise ValueError(
                "Persisted generation job belongs to a different data model."
            )

        if not job.attempt_id:
            raise ValueError(
                "Cannot prepare a checkpoint without a persisted attempt ID."
            )

        phase = job.preparation_phase

        if phase not in (
            GenerationPreparationPhase.CHECKPOINT_PENDING,
            GenerationPreparationPhase.CHECKPOINT_READY,
        ):
            raise ValueError(
                "Cannot recover initial preparation without a valid "
                "preparation phase."
            )

        manifest = self._checkpoint_store.get(
            data_model_id=data_model_id,
            job_id=job.job_id,
        )

        if manifest is None:
            if phase == GenerationPreparationPhase.CHECKPOINT_READY:
                raise ValueError(
                    f"Job '{job.job_id}' is marked CHECKPOINT_READY, "
                    "but its checkpoint is missing."
                )

            plan = self._generation_planner.build(
                specification=specification,
            )

            plan_targets = {
                entity.entity_name: entity.target_rows
                for entity in plan.entities
            }

            job_targets = {
                entity.entity_name: entity.target_rows
                for entity in job.entities
            }

            if plan_targets != job_targets:
                raise ValueError(
                    "Generation plan targets do not match persisted job targets."
                )

            if job.total_target_rows != sum(job_targets.values()):
                raise ValueError(
                    "Persisted job aggregate target rows are inconsistent."
                )

            if not job.entities:
                raise ValueError(
                    "Cannot initialize a checkpoint without generation entities."
                )

            chunk_size = job.entities[0].chunk_size

            if (
                not isinstance(chunk_size, int)
                or isinstance(chunk_size, bool)
                or chunk_size <= 0
                or any(
                    entity.chunk_size != chunk_size
                    for entity in job.entities
                )
            ):
                raise ValueError(
                    "All generation entities must use the same positive "
                    "chunk size."
                )

            generation = specification.get("generation") or {}
            seed = generation.get("seed", 42)

            # initialize() is deliberately create-only. If another actor
            # created the checkpoint, this call fails rather than replacing it.
            self._checkpoint_store.initialize(
                data_model_id=job.data_model_id,
                job_id=job.job_id,
                specification=specification,
                seed=seed,
                chunk_size=chunk_size,
                algorithm_version=GENERATION_ALGORITHM_VERSION,
                attempt_id=job.attempt_id,
                entity_targets=job_targets,
            )

        # Validate the complete persisted identity, plan, and every committed
        # artifact before declaring preparation ready.
        manifest = self._validate_recovery_checkpoint(
            data_model_id=data_model_id,
            job=job,
            specification=specification,
        )

        if phase == GenerationPreparationPhase.CHECKPOINT_PENDING:
            previous_phase = job.preparation_phase
            job.preparation_phase = (
                GenerationPreparationPhase.CHECKPOINT_READY
            )

            try:
                self._job_store.save(job)
            except Exception:
                job.preparation_phase = previous_phase
                raise

            self._jobs[job.job_id] = job

        return manifest


    def _validate_recovery_checkpoint(
        self,
        *,
        data_model_id: str,
        job: GenerationJobRecord,
        specification: dict,
        expected_attempt_id: str | None = None,
    ) -> GenerationCheckpointManifest:
        """Validate the authoritative v2 manifest and committed artifacts.

        This method is read-only. It never repairs, deletes, or rewrites
        checkpoint state or published artifacts.
        """

        if job.data_model_id != data_model_id:
            raise ValueError(
                "Persisted generation job belongs to a different data model."
            )

        checkpoint_attempt_id = (
            expected_attempt_id
            if expected_attempt_id is not None
            else job.attempt_id
        )

        if not checkpoint_attempt_id:
            raise ValueError(
                "Persisted generation job has no attempt ID; "
                "its checkpoint cannot be safely validated."
            )

        manifest = self._checkpoint_store.get(
            data_model_id=data_model_id,
            job_id=job.job_id,
        )
        if manifest is None:
            raise ValueError(
                f"Cannot recover job '{job.job_id}': checkpoint is missing."
            )

        seed = (specification.get("generation") or {}).get("seed", 42)

        self._checkpoint_store.validate_identity(
            data_model_id=data_model_id,
            job_id=job.job_id,
            specification_hash=compute_specification_hash(specification),
            seed=seed,
            chunk_size=manifest.chunk_size,
            algorithm_version=GENERATION_ALGORITHM_VERSION,
            attempt_id=checkpoint_attempt_id,
        )

        if any(
            entity.chunk_size != manifest.chunk_size
            for entity in job.entities
        ):
            raise ValueError(
                "Persisted generation job and checkpoint must use the same "
                "positive chunk size."
            )

        plan = self._generation_planner.build(specification=specification)

        plan_targets = {
            entity.entity_name: entity.target_rows
            for entity in plan.entities
        }
        job_targets = {
            entity.entity_name: entity.target_rows
            for entity in job.entities
        }
        manifest_targets = {
            name: entity.target_rows
            for name, entity in manifest.entities.items()
        }

        if len(job_targets) != len(job.entities):
            raise ValueError("Persisted job contains duplicate entity names.")

        if plan_targets != job_targets:
            raise ValueError(
                "Rebuilt generation plan does not match persisted job targets."
            )

        if plan_targets != manifest_targets:
            raise ValueError(
                "Generation plan targets do not match checkpoint manifest."
            )

        if job.total_target_rows != sum(plan_targets.values()):
            raise ValueError(
                "Persisted job aggregate target rows are inconsistent."
            )

        # Every manifest-listed chunk is committed evidence.
        # Never discard a committed chunk because verification fails.
        for entity_name, entity_checkpoint in manifest.entities.items():
            for chunk in entity_checkpoint.chunks:
                self._checkpoint_store.verify_artifact(
                    data_model_id=data_model_id,
                    job_id=job.job_id,
                    artifact=chunk.artifact,
                )

            if (
                entity_checkpoint.finalization.status
                == GenerationFinalizationStatus.COMMITTED
            ):
                output = entity_checkpoint.finalization.output
                if output is None:
                    raise ValueError(
                        f"Committed finalization for '{entity_name}' "
                        "has no output evidence."
                    )

                self._checkpoint_store.verify_artifact(
                    data_model_id=data_model_id,
                    job_id=job.job_id,
                    artifact=output,
                )

        return manifest


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

        self._validate_specification(specification)

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

    def _validate_specification(
        self,
        specification: dict,
    ) -> None:
        """Enforce canonical validation before generation."""
        result = self._specification_validation_service.validate(
            specification
        )
        if not result.get("can_continue", False):
            raise SpecificationValidationError(result)

    def create_job(
        self,
        data_model_id: str,
        user_id: str,
    ) -> GenerationJobResponse | None:
        """Create a generation job without executing it."""

        specification = self._specification_service.get_specification(
            data_model_id=data_model_id,
        )

        if specification is None:
            return None

        self._validate_specification(specification)

        plan = self._generation_planner.build(
            specification=specification,
        )

        entity_plans = {
            entity_plan.entity_name: entity_plan for entity_plan in plan.entities
        }

        now = datetime.now(timezone.utc)
        job_id = uuid4().hex.upper()

        chunk_size = DEFAULT_GENERATION_CHUNK_SIZE

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

        job = GenerationJobRecord(
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

        self._generation_log_store.create(
            data_model_id=data_model_id,
            job_id=job_id,
            user_id=user_id,
        )

        return job

    def _publish_terminal_event(
        self,
        job: GenerationJobResponse,
        *,
        valid: bool,
        error_count: int,
    ) -> None:
        """Publish the existing terminal event for any completed job outcome."""

        diagnostics_enabled = self._event_broker.diagnostics_enabled

        if diagnostics_enabled:
            self._event_broker.begin_job_diagnostics(
                data_model_id=job.data_model_id,
                job_id=job.job_id,
            )

        try:
            self._event_broker.publish(
                data_model_id=job.data_model_id,
                job_id=job.job_id,
                event_type="GENERATION_COMPLETED",
                data={
                    "job_id": job.job_id,
                    "status": job.status.value,
                    "generated_rows": job.total_generated_rows,
                    "expected_rows": job.total_target_rows,
                    "elapsed_seconds": job.elapsed_seconds,
                    "throughput_rows_per_second": (
                        job.total_generated_rows / job.elapsed_seconds
                        if job.elapsed_seconds and job.elapsed_seconds > 0
                        else None
                    ),
                    "peak_memory_mb": job.peak_memory_mb,
                    "valid": valid,
                    "error_count": error_count,
                    "progress": job.progress,
                },
            )

            if diagnostics_enabled:
                diagnostics = self._event_broker.diagnostics_snapshot(
                    data_model_id=job.data_model_id,
                    job_id=job.job_id,
                )
                logger.info(
                    "[FORGE SSE][JOB] timestamp=%s job_id=%s status=%s "
                    "published={%s} scheduled={%s}",
                    datetime.now(timezone.utc).isoformat(),
                    job.job_id,
                    job.status.value,
                    _format_sse_event_counts(
                        diagnostics["published_by_type"]
                    ),
                    _format_sse_event_counts(
                        diagnostics["scheduled_by_type"]
                    ),
                )
        finally:
            if diagnostics_enabled:
                self._event_broker.end_job_diagnostics(
                    data_model_id=job.data_model_id,
                    job_id=job.job_id,
                )

    def _reconcile_resume_intent_under_lease(
        self,
        *,
        data_model_id: str,
        job: GenerationJobRecord,
        specification: dict,
        final_status: GenerationJobStatus,
    ) -> GenerationCheckpointManifest:
        """Finish a durable resume transition while holding the execution lease.

        The job record retains the previous attempt ID and resume intent
        until the checkpoint has been verified under the new attempt.
        """

        if job.status != GenerationJobStatus.INTERRUPTED:
            raise ValueError(
                "A resume intent can only be reconciled for an "
                "INTERRUPTED job."
            )

        intent = job.resume_intent
        if intent is None:
            raise ValueError("Interrupted job has no resume intent.")

        if job.attempt_id != intent.previous_attempt_id:
            raise ValueError(
                "Resume intent previous attempt does not match the job record."
            )

        if final_status not in {
            GenerationJobStatus.PREPARING,
            GenerationJobStatus.INTERRUPTED,
        }:
            raise ValueError("Unsupported final status for resume recovery.")

        manifest = self._checkpoint_store.get(
            data_model_id=data_model_id,
            job_id=job.job_id,
        )

        if manifest is None:
            raise ValueError(
                f"Cannot resume job '{job.job_id}': checkpoint is missing."
            )

        if manifest.attempt_id not in {
            intent.previous_attempt_id,
            intent.new_attempt_id,
        }:
            raise ValueError(
                "Checkpoint attempt does not match either side of the "
                "persisted resume intent."
            )

        # Verify the old checkpoint before supersession, or verify the
        # already-superseded checkpoint if a previous process crashed
        # after the checkpoint write.
        self._validate_recovery_checkpoint(
            data_model_id=data_model_id,
            job=job,
            specification=specification,
            expected_attempt_id=manifest.attempt_id,
        )

        if manifest.attempt_id == intent.previous_attempt_id:
            self._checkpoint_store.supersede_attempt(
                data_model_id=data_model_id,
                job_id=job.job_id,
                expected_attempt_id=intent.previous_attempt_id,
                new_attempt_id=intent.new_attempt_id,
            )

        # Always re-read and fully validate the new authoritative checkpoint.
        new_manifest = self._validate_recovery_checkpoint(
            data_model_id=data_model_id,
            job=job,
            specification=specification,
            expected_attempt_id=intent.new_attempt_id,
        )

        # Preserve the durable intent state in memory if the final job write
        # fails. The checkpoint may already have moved to the new attempt.
        snapshot = job.model_copy(deep=True)

        try:
            job.attempt_id = intent.new_attempt_id
            job.resume_intent = None
            job.preparation_phase = (
                GenerationPreparationPhase.CHECKPOINT_READY
            )
            job.status = final_status
            job.started_at = datetime.now(timezone.utc)
            job.completed_at = None
            job.error = None

            self._apply_manifest_progress_to_job(
                job=job,
                manifest=new_manifest,
            )

            self._job_store.save(job)
            self._jobs[job.job_id] = job

        except Exception:
            job.__dict__.clear()
            job.__dict__.update(snapshot.__dict__)
            self._jobs[job.job_id] = job
            raise

        return new_manifest

    def recover_interrupted_jobs(self) -> int:
        """Recover stranded jobs and reconcile durable resume intents."""

        recovered = 0

        for persisted_job in self._job_store.list_recoverable():
            try:
                data_model_id = persisted_job.data_model_id
                job_id = persisted_job.job_id

                job_directory = (
                    Path(__file__).resolve().parents[2]
                    / "data"
                    / "data_model"
                    / data_model_id
                    / "generation"
                    / job_id
                )

                with generation_execution_lease(
                    job_directory,
                    timeout=0.0,
                ):
                    job = self._get_or_load_job(
                        data_model_id=data_model_id,
                        job_id=job_id,
                    )

                    if job is None:
                        continue

                    pending_resume = (
                        job.status == GenerationJobStatus.INTERRUPTED
                        and job.resume_intent is not None
                    )

                    if not pending_resume and job.status not in {
                        GenerationJobStatus.PREPARING,
                        GenerationJobStatus.RUNNING,
                    }:
                        continue

                    specification = (
                        self._specification_service.get_specification(
                            data_model_id=data_model_id,
                        )
                    )

                    if specification is None:
                        raise ValueError(
                            "Data model specification was not found."
                        )

                    self._validate_specification(specification)

                    if pending_resume:
                        self._reconcile_resume_intent_under_lease(
                            data_model_id=data_model_id,
                            job=job,
                            specification=specification,
                            final_status=GenerationJobStatus.INTERRUPTED,
                        )
                        recovered += 1
                        continue

                    if job.status == GenerationJobStatus.PREPARING:
                        self._ensure_initial_checkpoint(
                            data_model_id=data_model_id,
                            job=job,
                            specification=specification,
                        )

                    self._reconcile_recovery_checkpoint(
                        data_model_id=data_model_id,
                        job=job,
                        specification=specification,
                    )

                    previous_status = job.status
                    previous_error = job.error

                    job.status = GenerationJobStatus.INTERRUPTED
                    job.error = None

                    try:
                        self._job_store.save(job)
                    except Exception:
                        job.status = previous_status
                        job.error = previous_error
                        raise

                    self._jobs[job.job_id] = job
                    recovered += 1

            except FileLockTimeout:
                continue
            except Exception as exc:
                print(
                    f"Generation recovery skipped job {persisted_job.job_id}: "
                    f"{exc}"
                )

        return recovered

    def start_job(
        self,
        data_model_id: str,
        job_id: str,
    ) -> GenerationJobResponse | None:
        """Prepare a generation job while holding its execution lease."""

        job_directory = (
            Path(__file__).resolve().parents[2]
            / "data"
            / "data_model"
            / data_model_id
            / "generation"
            / job_id
        )

        with generation_execution_lease(
            job_directory,
            timeout=0.0,
        ):
            return self._start_job_under_lease(
                data_model_id=data_model_id,
                job_id=job_id,
            )

    def _start_job_under_lease(
        self,
        data_model_id: str,
        job_id: str,
    ) -> GenerationJobResponse | None:
        """Prepare a generation job while its execution lease is held."""

        job = self._get_or_load_job(
            data_model_id=data_model_id,
            job_id=job_id,
        )

        if job is None:
            return None

        worker_key = (data_model_id, job_id)

        with self._worker_lock:
            if worker_key in self._active_workers:
                raise ValueError(
                    f"Generation job '{job_id}' already has a scheduled "
                    "or active worker."
                )

        if job.status == GenerationJobStatus.INTERRUPTED:
            specification = self._specification_service.get_specification(
                data_model_id=data_model_id,
            )

            if specification is None:
                raise ValueError(
                    "Cannot resume generation: data model specification "
                    "was not found."
                )

            self._validate_specification(specification)

            with self._worker_lock:
                if worker_key in self._active_workers:
                    raise ValueError(
                        f"Generation job '{job_id}' already has a scheduled "
                        "or active worker."
                    )
                self._active_workers.add(worker_key)

            try:
                if job.resume_intent is None:
                    # Validate all existing evidence before recording an
                    # intention to supersede the current attempt.
                    self._validate_recovery_checkpoint(
                        data_model_id=data_model_id,
                        job=job,
                        specification=specification,
                    )

                    if not job.attempt_id:
                        raise ValueError(
                            "Cannot resume a job without an existing "
                            "attempt ID."
                        )

                    snapshot = job.model_copy(deep=True)

                    job.resume_intent = GenerationResumeIntent(
                        previous_attempt_id=job.attempt_id,
                        new_attempt_id=uuid4().hex,
                    )

                    try:
                        # This durable write must precede checkpoint
                        # supersession.
                        self._job_store.save(job)
                        self._jobs[job.job_id] = job
                    except Exception:
                        job.__dict__.clear()
                        job.__dict__.update(snapshot.__dict__)
                        self._jobs[job.job_id] = job
                        raise

                self._reconcile_resume_intent_under_lease(
                    data_model_id=data_model_id,
                    job=job,
                    specification=specification,
                    final_status=GenerationJobStatus.PREPARING,
                )

                return job

            except Exception:
                with self._worker_lock:
                    self._active_workers.discard(worker_key)
                raise

        if job.status != GenerationJobStatus.CREATED:
            raise ValueError(
                f"Generation job '{job_id}' cannot be started from "
                f"status '{job.status}'."
            )

        specification = self._specification_service.get_specification(
            data_model_id=data_model_id,
        )

        if specification is None:
            job.status = GenerationJobStatus.FAILED
            job.error = "Data model specification not found."
            job.started_at = datetime.now(timezone.utc)
            job.completed_at = job.started_at
            self._job_store.save(job)

            self._publish_terminal_event(
                job,
                valid=False,
                error_count=1,
            )
            return job

        self._validate_specification(specification)

        with self._worker_lock:
            if worker_key in self._active_workers:
                raise ValueError(
                    f"Generation job '{job_id}' already has a scheduled "
                    "or active worker."
                )
            self._active_workers.add(worker_key)

        previous_status = job.status
        previous_attempt_id = job.attempt_id
        previous_started_at = job.started_at
        previous_preparation_phase = job.preparation_phase

        attempt_id = uuid4().hex

        job.status = GenerationJobStatus.PREPARING
        job.attempt_id = attempt_id
        job.preparation_phase = (
            GenerationPreparationPhase.CHECKPOINT_PENDING
        )
        job.started_at = datetime.now(timezone.utc)
        job.completed_at = None
        job.error = None

        try:
            # PREPARING must be durable before checkpoint initialization.
            self._job_store.save(job)
        except Exception:
            with self._worker_lock:
                self._active_workers.discard(worker_key)

            job.status = previous_status
            job.attempt_id = previous_attempt_id
            job.started_at = previous_started_at
            job.preparation_phase = previous_preparation_phase
            raise

        try:
            self._ensure_initial_checkpoint(
                data_model_id=data_model_id,
                job=job,
                specification=specification,
            )

        except Exception as exc:
            job.status = GenerationJobStatus.FAILED
            job.error = str(exc)
            job.completed_at = datetime.now(timezone.utc)

            try:
                self._job_store.save(job)
            finally:
                with self._worker_lock:
                    self._active_workers.discard(worker_key)

            self._publish_terminal_event(
                job,
                valid=False,
                error_count=1,
            )
            return job

        self._jobs[job.job_id] = job
        return job

    def execute_job(
        self,
        data_model_id: str,
        job_id: str,
        attempt_id: str | None = None,
    ) -> None:
        """Execute only the exact attempt persisted by the scheduler."""

        worker_key = (data_model_id, job_id)

        if not isinstance(attempt_id, str) or not attempt_id.strip():
            return

        with self._worker_lock:
            if worker_key not in self._active_workers:
                return

        diagnostics_enabled = self._event_broker.diagnostics_enabled

        if diagnostics_enabled:
            self._event_broker.begin_job_diagnostics(
                data_model_id=data_model_id,
                job_id=job_id,
            )

        try:
            job_directory = (
                Path(__file__).resolve().parents[2]
                / "data"
                / "data_model"
                / data_model_id
                / "generation"
                / job_id
            )

            try:
                with generation_execution_lease(
                    job_directory,
                    timeout=0.0,
                ):
                    job = self._get_or_load_job(
                        data_model_id=data_model_id,
                        job_id=job_id,
                    )

                    if job is None or job.data_model_id != data_model_id:
                        return

                    if job.attempt_id != attempt_id:
                        print(
                            f"Ignoring stale generation task for job {job_id}: "
                            "attempt ID does not match persisted state.",
                            flush=True,
                        )
                        return

                    if job.status not in {
                        GenerationJobStatus.PREPARING,
                        GenerationJobStatus.RUNNING,
                    }:
                        return

                    specification = self._specification_service.get_specification(
                        data_model_id=data_model_id,
                    )

                    if specification is not None:
                        self._validate_specification(specification)
                        self._validate_recovery_checkpoint(
                            data_model_id=data_model_id,
                            job=job,
                            specification=specification,
                        )

                    job.status = GenerationJobStatus.RUNNING
                    job.error = None
                    self._job_store.save(job)
                    self._jobs[job.job_id] = job

                    self._execute_job_reserved(
                        data_model_id=data_model_id,
                        job_id=job_id,
                    )

            except FileLockTimeout:
                # Another process owns the execution lease.
                # Do not alter persisted job state.
                return

        finally:
            if diagnostics_enabled:
                self._event_broker.end_job_diagnostics(
                    data_model_id=data_model_id,
                    job_id=job_id,
                )

            with self._worker_lock:
                self._active_workers.discard(worker_key)

    def _execute_job_reserved(
        self,
        *,
        data_model_id: str,
        job_id: str,
    ) -> None:
        """Run generation using the reservation acquired by start_job."""

        job = self._get_or_load_job(
            data_model_id=data_model_id,
            job_id=job_id,
        )

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
            self._generation_log_store.append(
                data_model_id=job.data_model_id,
                job_id=job.job_id,
                entry=GenerationLogEntry(
                    sequence=0,
                    stage="FAILED",
                    status="FAILED",
                    error_type="SpecificationNotFoundError",
                    error_message=job.error,
                ),
            )
            self._publish_terminal_event(
                job,
                valid=False,
                error_count=1,
            )
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
                    event_broker=self._event_broker,
                    generation_log_store=self._generation_log_store,
                ),
                validator=GenerationValidator(),
                quality_service=GenerationQualityService(
                    artifact_reader=GenerationArtifactReader(
                        checkpoint_store=self._checkpoint_store,
                    ),
                ),
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
                manifest = self._checkpoint_store.get(
                    data_model_id=job.data_model_id,
                    job_id=job.job_id,
                )

                if manifest is None:
                    raise RuntimeError(
                        "Checkpoint manifest disappeared after chunk commit."
                    )

                entity_checkpoint = manifest.entities.get(entity_name)
                if entity_checkpoint is None:
                    raise RuntimeError(
                        f"Committed checkpoint entity '{entity_name}' is missing."
                    )

                committed_chunk = next(
                    (
                        item
                        for item in entity_checkpoint.chunks
                        if item.chunk_number == chunk_number
                    ),
                    None,
                )

                if committed_chunk is None:
                    raise RuntimeError(
                        f"Chunk {chunk_number} of '{entity_name}' "
                        "was reported complete without manifest evidence."
                    )

                if (
                    committed_chunk.row_count != len(_chunk_rows)
                    or committed_chunk.row_start
                    != (chunk_number - 1) * manifest.chunk_size
                ):
                    raise RuntimeError(
                        f"Chunk {chunk_number} of '{entity_name}' "
                        "does not match its committed manifest evidence."
                    )

                entity_progress = next(
                    (
                        item
                        for item in job.entities
                        if item.entity_name == entity_name
                    ),
                    None,
                )

                if entity_progress is None:
                    raise RuntimeError(
                        f"Job projection has no entity '{entity_name}'."
                    )

                entity_progress.generated_rows = (
                    entity_checkpoint.committed_rows
                )
                entity_progress.completed_chunks = len(
                    entity_checkpoint.chunks
                )
                entity_progress.total_chunks = (
                    ceil(entity_checkpoint.target_rows / manifest.chunk_size)
                    if entity_checkpoint.target_rows > 0
                    else 0
                )
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
                        target_rows=committed_chunk.row_count,
                        generated_rows=committed_chunk.row_count,
                        status=GenerationEntityStatus.COMPLETED,
                        elapsed_seconds=chunk_elapsed_seconds,
                        peak_memory_mb=chunk_peak_memory_mb,
                        throughput_rows_per_second=(
                            committed_chunk.row_count / chunk_elapsed_seconds
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

                job.total_generated_rows = sum(
                    item.committed_rows
                    for item in manifest.entities.values()
                )
                job.progress = (
                    job.total_generated_rows / job.total_target_rows
                    if job.total_target_rows > 0
                    else 1.0
                )

                self._job_store.save(job)

                self._event_broker.publish(
                    data_model_id=job.data_model_id,
                    job_id=job.job_id,
                    event_type="CHUNK_COMMITTED",
                    data={
                        "entity_name": entity_name,
                        "chunk_number": chunk_number,
                        "total_chunks": total_chunks,
                        "generated_rows": job.total_generated_rows,
                        "entity_generated_rows": entity_progress.generated_rows,
                        "entity_target_rows": entity_progress.target_rows,
                        "checkpoint_updated_at": manifest.updated_at.isoformat(),
                        "entity_progress": (
                            entity_progress.generated_rows
                            / entity_progress.target_rows
                            if entity_progress.target_rows > 0
                            else 0
                        ),
                        "progress": job.progress,
                    },
                )

            def on_entity_completed(entity_run) -> None:
                manifest = self._checkpoint_store.get(
                    data_model_id=job.data_model_id,
                    job_id=job.job_id,
                )

                if manifest is None:
                    raise RuntimeError(
                        "Checkpoint manifest disappeared during entity completion."
                    )

                entity_checkpoint = manifest.entities.get(
                    entity_run.entity_name
                )

                if entity_checkpoint is None:
                    raise RuntimeError(
                        f"Checkpoint entity '{entity_run.entity_name}' is missing."
                    )

                finalization = entity_checkpoint.finalization

                if (
                    entity_checkpoint.committed_rows
                    != entity_checkpoint.target_rows
                    or finalization.status.value != "COMMITTED"
                    or finalization.output is None
                ):
                    raise RuntimeError(
                        f"Entity '{entity_run.entity_name}' cannot be marked "
                        "complete without committed finalization evidence."
                    )

                self._checkpoint_store.verify_artifact(
                    data_model_id=job.data_model_id,
                    job_id=job.job_id,
                    artifact=finalization.output,
                )

                entity_progress = next(
                    (
                        item
                        for item in job.entities
                        if item.entity_name == entity_run.entity_name
                    ),
                    None,
                )

                if entity_progress is None:
                    raise RuntimeError(
                        f"Job projection has no entity "
                        f"'{entity_run.entity_name}'."
                    )

                entity_progress.generated_rows = (
                    entity_checkpoint.committed_rows
                )
                entity_progress.completed_chunks = len(
                    entity_checkpoint.chunks
                )
                entity_progress.total_chunks = (
                    ceil(entity_checkpoint.target_rows / manifest.chunk_size)
                    if entity_checkpoint.target_rows > 0
                    else 0
                )
                entity_progress.status = GenerationEntityStatus.COMPLETED
                entity_progress.elapsed_seconds = entity_run.elapsed_seconds
                entity_progress.peak_memory_mb = entity_run.peak_memory_mb
                entity_progress.throughput_rows_per_second = (
                    entity_run.generated_rows / entity_run.elapsed_seconds
                    if entity_run.elapsed_seconds
                    and entity_run.elapsed_seconds > 0
                    else None
                )
                entity_progress.vocabulary_semantic_calls = list(
                    entity_run.vocabulary_semantic_calls
                )

                job.total_generated_rows = sum(
                    item.committed_rows
                    for item in manifest.entities.values()
                )
                job.progress = (
                    job.total_generated_rows / job.total_target_rows
                    if job.total_target_rows > 0
                    else 1.0
                )

                self._job_store.save(job)

                self._event_broker.publish(
                    data_model_id=job.data_model_id,
                    job_id=job.job_id,
                    event_type="ENTITY_COMPLETED",
                    data={
                        "entity_name": entity_run.entity_name,
                        "target_rows": entity_checkpoint.target_rows,
                        "generated_rows": entity_checkpoint.committed_rows,
                        "status": GenerationEntityStatus.COMPLETED.value,
                        "elapsed_seconds": entity_progress.elapsed_seconds,
                        "throughput_rows_per_second": (
                            entity_progress.throughput_rows_per_second
                        ),
                        "peak_memory_mb": entity_progress.peak_memory_mb,
                        "progress": job.progress,
                    },
                )

                if self._event_broker.diagnostics_enabled:
                    diagnostics = self._event_broker.diagnostics_snapshot(
                        data_model_id=job.data_model_id,
                        job_id=job.job_id,
                    )
                    published = diagnostics["published_by_entity"].get(
                        entity_run.entity_name, {}
                    )
                    scheduled = diagnostics["scheduled_by_entity"].get(
                        entity_run.entity_name, {}
                    )
                    logger.info(
                        "[FORGE SSE][ENTITY] timestamp=%s job_id=%s "
                        "entity=%s published={%s} scheduled={%s}",
                        datetime.now(timezone.utc).isoformat(),
                        job.job_id,
                        entity_run.entity_name,
                        _format_sse_event_counts(published),
                        _format_sse_event_counts(scheduled),
                    )

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

            self._validation_store.save(
                data_model_id=data_model_id,
                job_id=job_id,
                validation={
                    "valid": result.validation.valid,
                    "entity_count": result.validation.entity_count,
                    "expected_rows": result.validation.expected_rows,
                    "generated_rows": result.validation.generated_rows,
                    "error_count": result.validation.error_count,
                    "errors": result.validation.errors,
                    "warnings": result.validation.warnings,
                    "evidence": result.validation.evidence,
                },
            )

            if result.quality is not None:
                self._quality_store.save(
                    data_model_id=data_model_id,
                    job_id=job_id,
                    quality=result.quality.model_dump(),
                )
                job.quality = result.quality

            job.status = result.status
            job.validation = result.validation
            job.total_generated_rows = result.generated_rows
            job.elapsed_seconds = result.elapsed_seconds
            job.peak_memory_mb = peak_memory_bytes / (1024 * 1024)
            job.progress = (
                result.generated_rows / result.requested_rows
                if result.requested_rows > 0
                else 1.0
            )

            manifest = self._checkpoint_store.get(
                data_model_id=job.data_model_id,
                job_id=job.job_id,
            )

            if manifest is None:
                raise RuntimeError(
                    "Checkpoint manifest is missing after generation."
                )

            projected_entities = []

            for result_entity in result.entities:
                entity_checkpoint = manifest.entities.get(
                    result_entity.entity_name
                )

                if entity_checkpoint is None:
                    raise RuntimeError(
                        f"Checkpoint entity '{result_entity.entity_name}' "
                        "is missing after generation."
                    )

                finalization = entity_checkpoint.finalization

                if (
                    entity_checkpoint.committed_rows
                    != entity_checkpoint.target_rows
                    or finalization.status.value != "COMMITTED"
                    or finalization.output is None
                ):
                    raise RuntimeError(
                        f"Entity '{result_entity.entity_name}' lacks "
                        "committed finalization evidence."
                    )

                self._checkpoint_store.verify_artifact(
                    data_model_id=job.data_model_id,
                    job_id=job.job_id,
                    artifact=finalization.output,
                )

                projected_entities.append(
                    GenerationEntityProgress(
                        entity_name=result_entity.entity_name,
                        target_rows=entity_checkpoint.target_rows,
                        generated_rows=entity_checkpoint.committed_rows,
                        chunk_size=manifest.chunk_size,
                        completed_chunks=len(entity_checkpoint.chunks),
                        total_chunks=(
                            ceil(
                                entity_checkpoint.target_rows
                                / manifest.chunk_size
                            )
                            if entity_checkpoint.target_rows > 0
                            else 0
                        ),
                        status=GenerationEntityStatus.COMPLETED,
                        elapsed_seconds=result_entity.elapsed_seconds,
                        peak_memory_mb=result_entity.peak_memory_mb,
                        throughput_rows_per_second=(
                            result_entity.generated_rows
                            / result_entity.elapsed_seconds
                            if result_entity.elapsed_seconds
                            and result_entity.elapsed_seconds > 0
                            else None
                        ),
                        vocabulary_semantic_calls=list(
                            result_entity.vocabulary_semantic_calls
                        ),
                        chunks=result_entity.chunks,
                    )
                )

            job.entities = projected_entities
            job.total_generated_rows = sum(
                item.committed_rows
                for item in manifest.entities.values()
            )
            job.progress = (
                job.total_generated_rows / job.total_target_rows
                if job.total_target_rows > 0
                else 1.0
            )

            job.completed_at = datetime.now(timezone.utc)

            if not result.validation.valid:
                job.error = (
                    result.validation.errors[0]
                    if result.validation.errors
                    else "Generation validation failed."
                )

            self._job_store.save(job)

            is_successful_completion = (
                job.status == GenerationJobStatus.COMPLETED
            )
            terminal_stage = (
                "COMPLETED"
                if is_successful_completion
                else "FAILED"
            )
            terminal_status = terminal_stage

            self._generation_log_store.append(
                data_model_id=job.data_model_id,
                job_id=job.job_id,
                entry=GenerationLogEntry(
                    sequence=0,
                    stage=terminal_stage,
                    status=terminal_status,
                    generated_rows=job.total_generated_rows,
                    elapsed_seconds=job.elapsed_seconds,
                    throughput_rows_per_second=(
                        job.total_generated_rows / job.elapsed_seconds
                        if job.elapsed_seconds and job.elapsed_seconds > 0
                        else None
                    ),
                    peak_memory_mb=job.peak_memory_mb,
                    error_type=(
                        "GenerationValidationError"
                        if job.status == GenerationJobStatus.FAILED
                        else None
                    ),
                    error_message=job.error,
                )
            )

            self._publish_terminal_event(
                job,
                valid=result.validation.valid,
                error_count=result.validation.error_count,
            )

        except Exception as exc:
            import traceback

            print(
                f"[GENERATION FAILURE] job_id={job.job_id} "
                f"data_model_id={job.data_model_id} "
                f"error_type={type(exc).__name__} error={exc}",
                flush=True,
            )
            traceback.print_exception(
                type(exc),
                exc,
                exc.__traceback__,
            )

            cause = exc.__cause__
            depth = 0
            while cause is not None and depth < 5:
                print(
                    f"[GENERATION FAILURE CAUSE {depth + 1}] "
                    f"type={type(cause).__name__} error={cause}",
                    flush=True,
                )
                cause = cause.__cause__
                depth += 1

            manifest = self._checkpoint_store.get(
                data_model_id=job.data_model_id,
                job_id=job.job_id,
            )

            usable_rows = 0
            recovered_rows: dict[str, int] = {}
            committed_rows_total = 0
            recovery_errors: list[str] = []

            if manifest is not None:
                for entity in job.entities:
                    entity_checkpoint = manifest.entities.get(
                        entity.entity_name
                    )

                    if entity_checkpoint is None:
                        recovery_errors.append(
                            f"Missing manifest entity '{entity.entity_name}'."
                        )
                        entity.generated_rows = 0
                        entity.completed_chunks = 0
                        entity.status = GenerationEntityStatus.FAILED
                        continue

                    committed_rows_total += (
                        entity_checkpoint.committed_rows
                    )

                    entity.generated_rows = (
                        entity_checkpoint.committed_rows
                    )
                    entity.completed_chunks = len(
                        entity_checkpoint.chunks
                    )
                    entity.total_chunks = (
                        ceil(
                            entity_checkpoint.target_rows
                            / manifest.chunk_size
                        )
                        if entity_checkpoint.target_rows > 0
                        else 0
                    )

                    artifacts_valid = True

                    for chunk in entity_checkpoint.chunks:
                        try:
                            self._checkpoint_store.verify_artifact(
                                data_model_id=job.data_model_id,
                                job_id=job.job_id,
                                artifact=chunk.artifact,
                            )
                        except Exception as recovery_exc:
                            artifacts_valid = False
                            recovery_errors.append(
                                f"Chunk {chunk.chunk_number} of "
                                f"'{entity.entity_name}' failed integrity "
                                f"verification: {recovery_exc}"
                            )

                    finalization = entity_checkpoint.finalization
                    finalized = (
                        finalization.status.value == "COMMITTED"
                        and finalization.output is not None
                    )

                    if finalized and artifacts_valid:
                        try:
                            self._checkpoint_store.verify_artifact(
                                data_model_id=job.data_model_id,
                                job_id=job.job_id,
                                artifact=finalization.output,
                            )
                        except Exception as recovery_exc:
                            finalized = False
                            recovery_errors.append(
                                f"Final output of '{entity.entity_name}' "
                                f"failed integrity verification: {recovery_exc}"
                            )

                    if (
                        finalized
                        and artifacts_valid
                        and entity_checkpoint.committed_rows
                        == entity_checkpoint.target_rows
                    ):
                        entity.status = GenerationEntityStatus.COMPLETED
                        recovered_rows[entity.entity_name] = (
                            entity_checkpoint.target_rows
                        )
                        usable_rows += entity_checkpoint.target_rows
                    else:
                        entity.status = GenerationEntityStatus.FAILED

            else:
                recovery_errors.append(
                    "Checkpoint manifest is missing during exception recovery."
                )
                for entity in job.entities:
                    entity.generated_rows = 0
                    entity.completed_chunks = 0
                    entity.status = GenerationEntityStatus.FAILED

            job.total_generated_rows = committed_rows_total
            job.progress = (
                min(
                    committed_rows_total / job.total_target_rows,
                    1.0,
                )
                if job.total_target_rows > 0
                else 1.0
            )

            all_entities_finalized = (
                manifest is not None
                and len(manifest.entities) == len(job.entities)
                and all(
                    entity.status == GenerationEntityStatus.COMPLETED
                    for entity in job.entities
                )
            )

            if all_entities_finalized:
                job.status = GenerationJobStatus.COMPLETED
            elif usable_rows > 0:
                job.status = GenerationJobStatus.PARTIALLY_COMPLETED
            else:
                job.status = GenerationJobStatus.FAILED

            job.error = str(exc)
            if recovery_errors:
                job.error += " | Recovery verification: " + "; ".join(
                    recovery_errors
                )

            job.completed_at = datetime.now(timezone.utc)
            self._job_store.save(job)

            is_partial = (
                job.status == GenerationJobStatus.PARTIALLY_COMPLETED
            )
            is_completed = (
                job.status == GenerationJobStatus.COMPLETED
            )
            self._generation_log_store.append(
                data_model_id=job.data_model_id,
                job_id=job.job_id,
                entry=GenerationLogEntry(
                    sequence=0,
                    stage=(
                        "CHUNK_COMMITTED"
                        if is_partial
                        else "COMPLETED"
                        if is_completed
                        else "FAILED"
                    ),
                    status=(
                        "COMPLETED"
                        if is_partial or is_completed
                        else "FAILED"
                    ),
                    generated_rows=usable_rows,
                    error_type=type(exc).__name__,
                    error_message=(
                        f"Generation stopped with usable output: {exc}"
                        if is_partial
                        else str(exc)
                    ),
                    traceback=traceback.format_exc(),
                )
            )
            self._publish_terminal_event(
                job,
                valid=False,
                error_count=1,
            )

    def get_generation_log(
        self,
        data_model_id: str,
        job_id: str,
    ):
        """Return durable generation history for an existing job."""

        job = self.get_job(
            data_model_id=data_model_id,
            job_id=job_id,
        )
        if job is None or job.data_model_id != data_model_id:
            return None

        return self._generation_log_store.get(
            data_model_id=data_model_id,
            job_id=job_id,
        )

    def list_jobs(
        self,
        data_model_id: str,
    ) -> list[GenerationJobResponse]:
        """Return persisted generation jobs for one data model."""

        jobs = self._job_store.list_for_data_model(data_model_id)

        for job in jobs:
            validation = self._validation_store.get(
                data_model_id=data_model_id,
                job_id=job.job_id,
            )
            if validation is not None:
                job.validation = validation

            quality = self._quality_store.get(
                data_model_id=data_model_id,
                job_id=job.job_id,
            )
            if quality is not None:
                job.quality = quality

        return jobs

    def get_job(
        self,
        data_model_id: str,
        job_id: str,
    ) -> GenerationJobResponse | None:
        """Return the authoritative persisted job with attached result data."""

        job = self._job_store.get(
            data_model_id=data_model_id,
            job_id=job_id,
        )
        if job is None or job.data_model_id != data_model_id:
            self._jobs.pop(job_id, None)
            return None

        validation = self._validation_store.get(
            data_model_id=data_model_id,
            job_id=job_id,
        )
        if validation is not None:
            job.validation = validation

        quality = self._quality_store.get(
            data_model_id=data_model_id,
            job_id=job_id,
        )
        if quality is not None:
            job.quality = quality

        self._jobs[job_id] = job
        return job
