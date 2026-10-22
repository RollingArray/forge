"""
File: generation_service.py
Purpose: FORGE generation planning and readiness service.
"""

from datetime import datetime, timezone
import csv
from pathlib import Path
from math import ceil
from threading import Lock, Thread
from uuid import uuid4

import psutil

from app.models.generation_log_model import GenerationLogEntry
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
from app.services.generation.quality import GenerationQualityService
from app.services.generation.artifact_reader import GenerationArtifactReader
from app.services.generation_checkpoint_store import (
    GenerationCheckpointStore,
    compute_specification_hash,
)
from app.services.generation_job_store import GenerationJobStore
from app.services.generation_quality_store import GenerationQualityStore
from app.services.generation_validation_store import GenerationValidationStore
from app.services.generation_event_broker import GenerationEventBroker
from app.services.generation_log_store import GenerationLogStore
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
        event_broker: GenerationEventBroker | None = None,
        generation_log_store: GenerationLogStore | None = None,
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
            else GenerationEventBroker()
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
        """Return a cached job or load its persisted representation."""

        job = self._jobs.get(job_id)
        if job is None:
            job = self._job_store.get(
                data_model_id=data_model_id,
                job_id=job_id,
            )
        if job is None or job.data_model_id != data_model_id:
            return None

        self._jobs[job_id] = job
        return job

    def _reconcile_recovery_checkpoint(
        self,
        *,
        data_model_id: str,
        job: GenerationJobResponse,
        specification: dict,
    ) -> dict:
        """Reconcile persisted progress against committed chunk artifacts."""

        checkpoint = self._checkpoint_store.get(
            data_model_id=data_model_id,
            job_id=job.job_id,
        )
        if checkpoint is None:
            raise ValueError(
                f"Cannot recover job '{job.job_id}': checkpoint is missing."
            )

        seed = (specification.get("generation") or {}).get("seed", 42)
        chunk_size = checkpoint.get("chunk_size")
        if (
            chunk_size != 50
            or any(entity.chunk_size != chunk_size for entity in job.entities)
        ):
            raise ValueError("Recovery requires the supported 50-row chunk contract.")

        expected_hash = compute_specification_hash(specification)
        self._checkpoint_store.validate_identity(
            data_model_id=data_model_id,
            job_id=job.job_id,
            specification_hash=expected_hash,
            seed=seed,
            chunk_size=chunk_size,
        )

        states = checkpoint.get("entities")
        targets = {entity.entity_name: entity.target_rows for entity in job.entities}
        if not isinstance(states, dict) or set(states) != set(targets):
            raise ValueError("Checkpoint entities do not match the generation job.")

        artifact_root = (
            Path(__file__).resolve().parents[2]
            / "data" / "data_model" / data_model_id
            / "generation" / job.job_id / "generated"
        )

        # Only an entity explicitly marked RUNNING may lose its final chunk.
        active = next(
            (entity for entity in job.entities
             if entity.status == GenerationEntityStatus.RUNNING),
            None,
        )
        if active is None:
            active = next(
                (entity for entity in job.entities
                 if entity.generated_rows < entity.target_rows),
                None,
            )

        repaired_states = {}
        retained_counts = {}

        for entity in job.entities:
            name = entity.entity_name
            state = states[name]
            if not isinstance(state, dict) or state.get("target_rows") != entity.target_rows:
                raise ValueError(f"Invalid checkpoint target for '{name}'.")

            raw_chunks = state.get("completed_chunks", [])
            if not isinstance(raw_chunks, list):
                raw_chunks = []

            committed = {
                number for number in raw_chunks
                if isinstance(number, int)
                and not isinstance(number, bool)
                and 1 <= number <= ceil(entity.target_rows / chunk_size)
            }

            chunks_dir = artifact_root / name / "chunks"
            prefix = 0
            max_chunks = ceil(entity.target_rows / chunk_size)

            for number in range(1, max_chunks + 1):
                if number not in committed:
                    break
                chunk_path = chunks_dir / f"chunk_{number:06d}.csv"
                if not chunk_path.is_file():
                    break

                expected_rows = min(
                    chunk_size,
                    entity.target_rows - (number - 1) * chunk_size,
                )
                try:
                    with chunk_path.open(
                        "r", newline="", encoding="utf-8"
                    ) as handle:
                        reader = csv.DictReader(handle)
                        if not reader.fieldnames:
                            break
                        actual_rows = sum(1 for _ in reader)
                except (OSError, UnicodeError, csv.Error):
                    break

                if actual_rows != expected_rows:
                    break
                prefix = number

            # Discard the last committed chunk of the interrupted entity.
            if entity is active and prefix:
                prefix -= 1

            retained_counts[name] = prefix
            repaired = dict(state)
            repaired["target_rows"] = entity.target_rows
            repaired["completed_chunks"] = list(range(1, prefix + 1))
            repaired["committed_rows"] = min(
                prefix * chunk_size, entity.target_rows
            )
            repaired_states[name] = repaired


        # Persist checkpoint first; startup reconciliation is safe to repeat.
        self._checkpoint_store.save(
            data_model_id=data_model_id,
            job_id=job.job_id,
            seed=seed,
            entities=repaired_states,
            specification_hash=expected_hash,
            chunk_size=chunk_size,
        )

        # Cleanup is deliberately after the atomic checkpoint save.
        for entity in job.entities:
            name = entity.entity_name
            prefix = retained_counts[name]
            chunks_dir = artifact_root / name / "chunks"
            if chunks_dir.is_dir():
                for file_path in chunks_dir.glob("chunk_*.csv"):
                    try:
                        number = int(file_path.stem.removeprefix("chunk_"))
                    except ValueError:
                        continue
                    if number > prefix:
                        file_path.unlink()

            consolidated = artifact_root / f"{name}.csv"
            if (
                prefix * chunk_size < entity.target_rows
                and consolidated.exists()
            ):
                consolidated.unlink()

        for entity in job.entities:
            prefix = retained_counts[entity.entity_name]
            rows = min(prefix * chunk_size, entity.target_rows)
            entity.generated_rows = rows
            entity.completed_chunks = prefix
            entity.total_chunks = ceil(entity.target_rows / chunk_size)
            entity.chunks = [
                chunk for chunk in entity.chunks
                if chunk.chunk_number <= prefix
            ]

            if rows >= entity.target_rows:
                entity.status = GenerationEntityStatus.COMPLETED
            elif entity is active:
                entity.status = GenerationEntityStatus.RUNNING
            else:
                entity.status = GenerationEntityStatus.NOT_STARTED

        job.total_generated_rows = sum(
            entity.generated_rows for entity in job.entities
        )
        job.progress = (
            job.total_generated_rows / job.total_target_rows
            if job.total_target_rows else 1.0
        )
        self._job_store.save(job)
        self._jobs[job.job_id] = job
        return self._validate_recovery_checkpoint(
            data_model_id=data_model_id,
            job=job,
            specification=specification,
        )

    def _validate_recovery_checkpoint(
        self,
        *,
        data_model_id: str,
        job: GenerationJobResponse,
        specification: dict,
    ) -> dict:
        """Validate durable recovery state without changing persisted data."""

        if job.data_model_id != data_model_id:
            raise ValueError(
                "Persisted generation job belongs to a different data model."
            )

        checkpoint = self._checkpoint_store.get(
            data_model_id=data_model_id,
            job_id=job.job_id,
        )
        if checkpoint is None:
            raise ValueError(
                f"Cannot resume job '{job.job_id}': checkpoint is missing."
            )

        seed = (specification.get("generation") or {}).get("seed", 42)
        chunk_size = job.entities[0].chunk_size if job.entities else 50
        if chunk_size != 50 or any(
            entity.chunk_size != chunk_size for entity in job.entities
        ):
            raise ValueError(
                "Persisted generation job does not use the supported "
                "50-row chunk contract."
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
        if plan_targets != job_targets:
            raise ValueError(
                "Rebuilt generation plan does not match persisted job targets."
            )

        self._checkpoint_store.validate_identity(
            data_model_id=data_model_id,
            job_id=job.job_id,
            specification_hash=compute_specification_hash(specification),
            seed=seed,
            chunk_size=chunk_size,
        )

        checkpoint_entities = checkpoint.get("entities")
        if not isinstance(checkpoint_entities, dict):
            raise ValueError("Checkpoint entity state is invalid.")

        expected_targets = {
            entity.entity_name: entity.target_rows
            for entity in job.entities
        }
        if set(checkpoint_entities) != set(expected_targets):
            raise ValueError(
                "Checkpoint entities do not match the persisted generation job."
            )

        entity_progress_total = sum(
            entity.generated_rows for entity in job.entities
        )
        if entity_progress_total != job.total_generated_rows:
            raise ValueError(
                "Persisted job aggregate row count does not match its "
                "entity-level progress."
            )

        if job.total_generated_rows > job.total_target_rows:
            raise ValueError(
                "Persisted job generated rows exceed its target row count."
            )

        for entity_name, target_rows in expected_targets.items():
            entity_checkpoint = checkpoint_entities[entity_name]
            if not isinstance(entity_checkpoint, dict):
                raise ValueError(
                    f"Checkpoint state is invalid for entity '{entity_name}'."
                )
            if entity_checkpoint.get("target_rows") != target_rows:
                raise ValueError(
                    f"Checkpoint target rows do not match for entity "
                    f"'{entity_name}'."
                )

            completed_chunks = entity_checkpoint.get("completed_chunks")
            if (
                not isinstance(completed_chunks, list)
                or any(
                    not isinstance(number, int)
                    or isinstance(number, bool)
                    or number < 1
                    for number in completed_chunks
                )
                or len(completed_chunks) != len(set(completed_chunks))
            ):
                raise ValueError(
                    f"Checkpoint committed chunks are invalid for entity "
                    f"'{entity_name}'."
                )

            total_chunks = (
                ceil(target_rows / chunk_size) if target_rows > 0 else 0
            )
            if any(number > total_chunks for number in completed_chunks):
                raise ValueError(
                    f"Checkpoint contains an out-of-range chunk for entity "
                    f"'{entity_name}'."
                )

            expected_chunk_numbers = list(range(1, len(completed_chunks) + 1))
            if sorted(completed_chunks) != expected_chunk_numbers:
                raise ValueError(
                    f"Checkpoint committed chunks are not contiguous for "
                    f"entity '{entity_name}'."
                )

            committed_rows = entity_checkpoint.get("committed_rows", 0)
            derived_committed_rows = min(
                len(completed_chunks) * chunk_size,
                target_rows,
            )
            if (
                not isinstance(committed_rows, int)
                or isinstance(committed_rows, bool)
                or committed_rows < 0
                or committed_rows > target_rows
                or committed_rows != derived_committed_rows
            ):
                raise ValueError(
                    f"Checkpoint committed row count is invalid for entity "
                    f"'{entity_name}'."
                )

            if committed_rows != sum(
                entity_progress.generated_rows
                for entity_progress in job.entities
                if entity_progress.entity_name == entity_name
            ):
                raise ValueError(
                    f"Checkpoint committed rows do not match persisted job "
                    f"progress for entity '{entity_name}'."
                )

        return checkpoint

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
        user_id: str,
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
        job_id = uuid4().hex.upper()

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

    def recover_interrupted_jobs(self) -> int:
        """Validate persisted RUNNING jobs without starting workers."""

        recovered = 0
        for persisted_job in self._job_store.list_running():
            try:
                data_model_id = persisted_job.data_model_id
                job = self._get_or_load_job(
                    data_model_id=data_model_id,
                    job_id=persisted_job.job_id,
                )
                if job is None or job.status != GenerationJobStatus.RUNNING:
                    continue

                specification = self._specification_service.get_specification(
                    data_model_id=data_model_id,
                )
                if specification is None:
                    raise ValueError(
                        "Data model specification was not found."
                    )

                self._reconcile_recovery_checkpoint(
                    data_model_id=data_model_id,
                    job=job,
                    specification=specification,
                )

                job.status = GenerationJobStatus.INTERRUPTED
                job.error = None
                self._job_store.save(job)
                self._jobs[job.job_id] = job
                recovered += 1
            except Exception as exc:
                print(
                    f"Generation recovery skipped job "
                    f"{persisted_job.job_id}: {exc}"
                )

        return recovered

    def start_job(
        self,
        data_model_id: str,
        job_id: str,
    ) -> GenerationJobResponse | None:
        """Prepare a generation job for asynchronous execution."""

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

            self._reconcile_recovery_checkpoint(
                data_model_id=data_model_id,
                job=job,
                specification=specification,
            )

            with self._worker_lock:
                if worker_key in self._active_workers:
                    raise ValueError(
                        f"Generation job '{job_id}' already has a scheduled "
                        "or active worker."
                    )
                self._active_workers.add(worker_key)
                job.status = GenerationJobStatus.RUNNING
                job.error = None
                try:
                    self._job_store.save(job)
                except Exception:
                    self._active_workers.discard(worker_key)
                    raise
                self._jobs[job.job_id] = job

            return job

        if job.status != GenerationJobStatus.CREATED:
            raise ValueError(
                f"Generation job '{job_id}' cannot be started from "
                f"status '{job.status}'. Only CREATED jobs and validated "
                "INTERRUPTED jobs can be resumed."
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
            return job

        self._generation_log_store.append(
            data_model_id=data_model_id,
            job_id=job_id,
            entry=GenerationLogEntry(
                sequence=0,
                stage="PREPARING",
                status="STARTED",
            ),
        )

        job.status = GenerationJobStatus.PLANNING
        job.started_at = datetime.now(timezone.utc)
        self._job_store.save(job)

        try:
            plan = self._generation_planner.build(
                specification=specification,
            )
        except Exception as exc:
            import traceback

            job.status = GenerationJobStatus.FAILED
            job.error = str(exc)
            job.completed_at = datetime.now(timezone.utc)
            self._job_store.save(job)

            self._generation_log_store.append(
                data_model_id=job.data_model_id,
                job_id=job.job_id,
                entry=GenerationLogEntry(
                    sequence=0,
                    stage="FAILED",
                    status="FAILED",
                    error_type=type(exc).__name__,
                    error_message=str(exc),
                    traceback=traceback.format_exc(),
                ),
            )
            self._publish_terminal_event(
                job,
                valid=False,
                error_count=1,
            )
            return job

        seed = specification.get("generation", {}).get("seed", 42)
        chunk_size = (
            job.entities[0].chunk_size
            if job.entities
            else 50
        )

        checkpoint = self._checkpoint_store.create_checkpoint(
            data_model_id=job.data_model_id,
            job_id=job.job_id,
            specification=specification,
            seed=seed,
            chunk_size=chunk_size,
            entity_targets={
                entity.entity_name: entity.target_rows
                for entity in job.entities
            },
        )

        existing_checkpoint = self._checkpoint_store.get(
            data_model_id=job.data_model_id,
            job_id=job.job_id,
        )

        if existing_checkpoint is not None:
            self._checkpoint_store.validate_identity(
                data_model_id=job.data_model_id,
                job_id=job.job_id,
                specification_hash=checkpoint["specification_hash"],
                seed=seed,
                chunk_size=chunk_size,
            )
        else:
            self._checkpoint_store.save(
                data_model_id=job.data_model_id,
                job_id=job.job_id,
                seed=checkpoint["seed"],
                entities=checkpoint["entities"],
                specification_hash=checkpoint["specification_hash"],
                chunk_size=checkpoint["chunk_size"],
            )

        with self._worker_lock:
            if worker_key in self._active_workers:
                raise ValueError(
                    f"Generation job '{job_id}' already has a scheduled "
                    "or active worker."
                )
            self._active_workers.add(worker_key)

        previous_status = job.status
        job.status = GenerationJobStatus.RUNNING

        try:
            self._job_store.save(job)
            self._generation_log_store.append(
                data_model_id=job.data_model_id,
                job_id=job.job_id,
                entry=GenerationLogEntry(
                    sequence=0,
                    stage="PREPARING",
                    status="COMPLETED",
                ),
            )
        except Exception:
            with self._worker_lock:
                self._active_workers.discard(worker_key)

            # Preserve RUNNING if it was already persisted and only the log
            # append failed. This leaves the job eligible for validated recovery.
            try:
                persisted_job = self._job_store.get(
                    data_model_id=data_model_id,
                    job_id=job_id,
                )
            except Exception:
                persisted_job = None

            if persisted_job is None or persisted_job.status != GenerationJobStatus.RUNNING:
                job.status = previous_status
                try:
                    self._job_store.save(job)
                except Exception:
                    # Preserve the original start-transition failure.
                    pass
            raise

        return job

    def execute_job(
        self,
        data_model_id: str,
        job_id: str,
    ) -> None:
        """Execute a started or explicitly resumed generation job."""

        worker_key = (data_model_id, job_id)
        with self._worker_lock:
            if worker_key not in self._active_workers:
                return

        try:
            self._execute_job_reserved(
                data_model_id=data_model_id,
                job_id=job_id,
            )
        finally:
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
                existing_checkpoint = (
                    self._checkpoint_store.get(
                        data_model_id=job.data_model_id,
                        job_id=job.job_id,
                    )
                    or {}
                )

                existing_entity_checkpoint = (
                    existing_checkpoint
                    .get("entities", {})
                    .get(entity_name, {})
                )
                completed_chunks_for_entity = list(
                    existing_entity_checkpoint.get("completed_chunks", [])
                )

                if chunk_number not in completed_chunks_for_entity:
                    completed_chunks_for_entity.append(chunk_number)
                    completed_chunks_for_entity.sort()

                entity_target_rows = next(
                    (
                        item.target_rows
                        for item in job.entities
                        if item.entity_name == entity_name
                    ),
                    None,
                )
                chunk_size = existing_checkpoint.get("chunk_size", 50)

                if (
                    entity_target_rows is None
                    or not isinstance(chunk_size, int)
                    or isinstance(chunk_size, bool)
                    or chunk_size <= 0
                    or any(
                        not isinstance(number, int)
                        or isinstance(number, bool)
                        or number < 1
                        for number in completed_chunks_for_entity
                    )
                    or len(completed_chunks_for_entity)
                    != len(set(completed_chunks_for_entity))
                ):
                    raise ValueError(
                        f"Cannot account for committed chunks of entity "
                        f"'{entity_name}'."
                    )

                durable_generated_rows = min(
                    len(completed_chunks_for_entity) * chunk_size,
                    entity_target_rows,
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

                    completed_chunks = (
                        completed_chunks_for_entity
                        if entity.entity_name == entity_name
                        else list(
                            existing_entity.get("completed_chunks", [])
                        )
                    )

                    entities[entity.entity_name] = {
                        "target_rows": entity.target_rows,
                        "completed_chunks": completed_chunks,
                        "committed_rows": entity.generated_rows,
                    }

                saved_checkpoint = self._checkpoint_store.save(
                    data_model_id=job.data_model_id,
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

                # Persist UI-facing progress only after the durable checkpoint.
                self._job_store.save(job)

                entity_progress = next(
                    (
                        item
                        for item in job.entities
                        if item.entity_name == entity_name
                    ),
                    None,
                )

                entity_generated_rows = (
                    entity_progress.generated_rows
                    if entity_progress
                    else 0
                )
                entity_target_rows = (
                    entity_progress.target_rows
                    if entity_progress
                    else 0
                )

                self._event_broker.publish(
                    data_model_id=job.data_model_id,
                    job_id=job.job_id,
                    event_type="CHUNK_COMMITTED",
                    data={
                        "entity_name": entity_name,
                        "chunk_number": chunk_number,
                        "total_chunks": total_chunks,
                        "generated_rows": job.total_generated_rows,
                        "entity_generated_rows": entity_generated_rows,
                        "entity_target_rows": entity_target_rows,
                        "checkpoint_updated_at": saved_checkpoint["updated_at"],
                        "entity_progress": (
                            entity_generated_rows / entity_target_rows
                            if entity_target_rows > 0
                            else 0
                        ),
                        "progress": job.progress,
                    },
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

                self._event_broker.publish(
                    data_model_id=job.data_model_id,
                    job_id=job.job_id,
                    event_type="ENTITY_COMPLETED",
                    data={
                        "entity_name": entity_run.entity_name,
                        "target_rows": entity_run.target_rows,
                        "generated_rows": entity_run.generated_rows,
                        "status": GenerationEntityStatus.COMPLETED.value,
                        "elapsed_seconds": entity_progress.elapsed_seconds,
                        "throughput_rows_per_second": (
                            entity_progress.throughput_rows_per_second
                        ),
                        "peak_memory_mb": entity_progress.peak_memory_mb,
                        "progress": job.progress,
                    },
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

            from app.services.generation.artifact_writer import (
                GenerationArtifactWriter,
            )

            usable_rows = 0
            recovered_rows: dict[str, int] = {}
            checkpoint = self._checkpoint_store.get(
                data_model_id=job.data_model_id,
                job_id=job.job_id,
            )
            checkpoint_entities = (
                checkpoint.get("entities", {})
                if isinstance(checkpoint, dict)
                else {}
            )

            artifact_writer = GenerationArtifactWriter(
                checkpoint_store=self._checkpoint_store,
            )

            if isinstance(checkpoint_entities, dict):
                for entity_name in checkpoint_entities:
                    try:
                        row_count = artifact_writer.consolidate_entity(
                            data_model_id=job.data_model_id,
                            job_id=job.job_id,
                            entity_name=entity_name,
                        )
                        if row_count > 0:
                            recovered_rows[entity_name] = row_count
                            usable_rows += row_count
                    except Exception as recovery_exc:
                        print(
                            f"[GENERATION ARTIFACT RECOVERY FAILURE] "
                            f"job_id={job.job_id} entity={entity_name} "
                            f"error_type={type(recovery_exc).__name__} "
                            f"error={recovery_exc}",
                            flush=True,
                        )

            job.total_generated_rows = usable_rows
            job.progress = (
                min(usable_rows / job.total_target_rows, 1.0)
                if job.total_target_rows > 0
                else 0.0
            )
            job.status = (
                GenerationJobStatus.PARTIALLY_COMPLETED
                if usable_rows > 0
                else GenerationJobStatus.FAILED
            )
            job.error = str(exc)
            job.completed_at = datetime.now(timezone.utc)

            for entity in job.entities:
                recovered = recovered_rows.get(entity.entity_name, 0)
                entity.generated_rows = recovered
                entity.status = (
                    GenerationEntityStatus.COMPLETED
                    if recovered >= entity.target_rows
                    else GenerationEntityStatus.FAILED
                )
                entity.completed_chunks = (
                    ceil(recovered / entity.chunk_size)
                    if recovered > 0 and entity.chunk_size > 0
                    else 0
                )

            self._job_store.save(job)

            is_partial = (
                job.status == GenerationJobStatus.PARTIALLY_COMPLETED
            )
            self._generation_log_store.append(
                data_model_id=job.data_model_id,
                job_id=job.job_id,
                entry=GenerationLogEntry(
                    sequence=0,
                    stage=(
                        "CHUNK_COMMITTED"
                        if is_partial
                        else "FAILED"
                    ),
                    status=(
                        "COMPLETED"
                        if is_partial
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
        """Return a generation job from memory or persistent storage."""

        job = self._jobs.get(job_id)

        if job is None:
            job = self._job_store.get(
                data_model_id=data_model_id,
                job_id=job_id,
            )

        if job is None:
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
