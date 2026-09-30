
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
            / "generation"
        )

    def _job_path(self, job_id: str) -> Path:
        return self._root / job_id / "job.json"

    def save(self, job: GenerationJobResponse) -> None:
        """Persist one generation job atomically."""

        path = self._job_path(job.job_id)
        path.parent.mkdir(parents=True, exist_ok=True)

        temporary_path = path.with_suffix(".tmp")
        temporary_path.write_text(
            job.model_dump_json(indent=2),
            encoding="utf-8",
        )
        temporary_path.replace(path)

    def get(self, job_id: str) -> GenerationJobResponse | None:
        """Load a generation job from persistent storage."""

        path = self._job_path(job_id)

        if not path.is_file():
            return None

        try:
            return GenerationJobResponse.model_validate_json(
                path.read_text(encoding="utf-8")
            )
        except Exception:
            return None
