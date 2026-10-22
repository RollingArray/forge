
"""
File: generation_job_store.py
Purpose: Persist FORGE generation job metadata.
"""

from pathlib import Path

from app.models.generation_model import GenerationJobResponse


class GenerationJobStore:
    """Persist generation job metadata alongside generated artifacts."""

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

    def save(self, job: GenerationJobResponse) -> None:
        """Persist one generation job atomically."""

        path = self._job_path(job.data_model_id, job.job_id)
        path.parent.mkdir(parents=True, exist_ok=True)

        temporary_path = path.with_suffix(".tmp")
        temporary_path.write_text(
            job.model_dump_json(indent=2),
            encoding="utf-8",
        )
        temporary_path.replace(path)

    def list_for_data_model(
        self,
        data_model_id: str,
    ) -> list[GenerationJobResponse]:
        """Return persisted generation jobs for one data model."""

        jobs: list[GenerationJobResponse] = []
        jobs_root = self._root / data_model_id / "generation"

        if not jobs_root.is_dir():
            return jobs

        for job_path in jobs_root.glob("*/job.json"):
            try:
                job = GenerationJobResponse.model_validate_json(
                    job_path.read_text(encoding="utf-8")
                )
            except Exception:
                continue

            if (
                job.data_model_id == data_model_id
                and job_path == self._job_path(
                    job.data_model_id,
                    job.job_id,
                )
            ):
                jobs.append(job)

        return sorted(
            jobs,
            key=lambda job: job.created_at,
            reverse=True,
        )

    def list_running(self) -> list[GenerationJobResponse]:
        """Discover persisted RUNNING jobs across all data models."""

        jobs: list[GenerationJobResponse] = []

        if not self._root.is_dir():
            return jobs

        for job_path in self._root.glob("*/generation/*/job.json"):
            try:
                job = GenerationJobResponse.model_validate_json(
                    job_path.read_text(encoding="utf-8")
                )
            except Exception:
                continue

            if (
                job.status.value == "RUNNING"
                and job_path == self._job_path(
                    job.data_model_id,
                    job.job_id,
                )
            ):
                jobs.append(job)

        return jobs

    def get(
        self,
        data_model_id: str,
        job_id: str,
    ) -> GenerationJobResponse | None:
        """Load a generation job from persistent storage."""

        path = self._job_path(data_model_id, job_id)

        if not path.is_file():
            return None

        try:
            return GenerationJobResponse.model_validate_json(
                path.read_text(encoding="utf-8")
            )
        except Exception:
            return None
