"""
File: generation_job_store.py
Purpose: Persist FORGE generation job metadata.
"""

import json
from pathlib import Path

from pydantic import ValidationError

from app.models.generation_model import (
    GenerationJobRecord,
    GenerationJobStatus,
)
from app.services.generation_file_persistence import (
    atomic_write_text,
    generation_file_lock,
)
from app.services.generation_persistence_errors import (
    JobRecordCorruptError,
    JobRecordValidationError,
    PersistenceOperationError,
)


class GenerationJobStore:
    """Persist internal generation job records."""

    def __init__(self) -> None:
        self._root = (
            Path(__file__).resolve().parents[2]
            / "data"
            / "data_model"
        )

    def _job_path(self, data_model_id: str, job_id: str) -> Path:
        return (
            self._root
            / data_model_id
            / "generation"
            / job_id
            / "job.json"
        )

    def save(self, job: GenerationJobRecord) -> None:
        """Persist one internal generation job record atomically."""

        if not isinstance(job, GenerationJobRecord):
            raise TypeError(
                "GenerationJobStore.save requires GenerationJobRecord."
            )

        path = self._job_path(job.data_model_id, job.job_id)

        try:
            with generation_file_lock(path):
                atomic_write_text(
                    path,
                    job.model_dump_json(
                    indent=2,
                    exclude={"throughput_rows_per_second"},
                ),
                )
        except OSError as exc:
            raise PersistenceOperationError(
                f"Unable to persist generation job "
                f"'{job.job_id}': {exc}"
            ) from exc

    def list_for_data_model(
        self,
        data_model_id: str,
    ) -> list[GenerationJobRecord]:
        """Return persisted generation jobs for one data model."""

        jobs: list[GenerationJobRecord] = []
        jobs_root = self._root / data_model_id / "generation"

        if not jobs_root.is_dir():
            return jobs

        for job_path in jobs_root.glob("*/job.json"):
            with generation_file_lock(job_path):
                job = self._read(job_path)

            if job is None:
                continue

            if (
                job.data_model_id != data_model_id
                or job_path != self._job_path(
                    job.data_model_id,
                    job.job_id,
                )
            ):
                raise JobRecordValidationError(
                    f"Job record identity does not match its path: "
                    f"'{job_path}'."
                )

            jobs.append(job)

        return sorted(
            jobs,
            key=lambda job: job.created_at,
            reverse=True,
        )

    def list_running(self) -> list[GenerationJobRecord]:
        """Return persisted RUNNING jobs."""

        return [
            job
            for job in self._list_all()
            if job.status == GenerationJobStatus.RUNNING
        ]

    def list_recoverable(self) -> list[GenerationJobRecord]:
        """Return jobs whose preparation or execution may need recovery."""

        recoverable_statuses = {
            GenerationJobStatus.PREPARING,
            GenerationJobStatus.RUNNING,
        }
        resume_intent_source_statuses = {
            GenerationJobStatus.INTERRUPTED,
            GenerationJobStatus.FAILED,
            GenerationJobStatus.PARTIALLY_COMPLETED,
            GenerationJobStatus.PAUSED,
            GenerationJobStatus.CANCELLED,
        }

        return [
            job
            for job in self._list_all()
            if (
                job.status in recoverable_statuses
                or (
                    job.status in resume_intent_source_statuses
                    and job.resume_intent is not None
                )
            )
        ]

    def _list_all(self) -> list[GenerationJobRecord]:
        """Discover persisted jobs across all data models."""

        jobs: list[GenerationJobRecord] = []

        if not self._root.is_dir():
            return jobs

        for job_path in self._root.glob("*/generation/*/job.json"):
            with generation_file_lock(job_path):
                job = self._read(job_path)

            if job is None:
                continue

            if job_path != self._job_path(
                job.data_model_id,
                job.job_id,
            ):
                raise JobRecordValidationError(
                    f"Job record identity does not match its path: "
                    f"'{job_path}'."
                )

            jobs.append(job)

        return jobs

    def get(
        self,
        data_model_id: str,
        job_id: str,
    ) -> GenerationJobRecord | None:
        """Load a persisted job record."""

        path = self._job_path(data_model_id, job_id)

        with generation_file_lock(path):
            job = self._read(path)

        if job is None:
            return None

        if (
            job.data_model_id != data_model_id
            or job.job_id != job_id
        ):
            raise JobRecordValidationError(
                "Persisted job identity does not match its requested "
                "location."
            )

        return job

    @staticmethod
    def _read(path: Path) -> GenerationJobRecord | None:
        """Read a record, distinguishing missing, corrupt and inaccessible."""

        try:
            content = path.read_text(encoding="utf-8")
        except FileNotFoundError:
            return None
        except UnicodeDecodeError as exc:
            raise JobRecordCorruptError(
                f"Generation job contains invalid UTF-8: '{path}'."
            ) from exc
        except OSError as exc:
            raise PersistenceOperationError(
                f"Unable to read generation job '{path}': {exc}"
            ) from exc

        try:
            payload = json.loads(content)
        except json.JSONDecodeError as exc:
            raise JobRecordCorruptError(
                f"Generation job contains invalid JSON: '{path}'."
            ) from exc

        if not isinstance(payload, dict):
            raise JobRecordCorruptError(
                f"Generation job root must be a JSON object: '{path}'."
            )

        try:
            return GenerationJobRecord.model_validate(payload)
        except ValidationError as exc:
            raise JobRecordValidationError(
                f"Generation job violates its persistence schema: "
                f"'{path}': {exc}"
            ) from exc
