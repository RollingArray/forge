"""
File: generation_job_control_store.py
Purpose: Persist cooperative generation job control requests.
"""

from enum import StrEnum
from pathlib import Path

from app.services.generation_file_persistence import (
    atomic_write_text,
    generation_file_lock,
)
from app.services.generation_persistence_errors import (
    PersistenceOperationError,
)


class GenerationJobControlRequest(StrEnum):
    PAUSE = "PAUSE"
    CANCEL = "CANCEL"


class GenerationJobControlStore:
    """Persist control requests independently of generation job metadata."""

    def __init__(self) -> None:
        self._root = (
            Path(__file__).resolve().parents[2]
            / "data"
            / "data_model"
        )

    def _control_path(self, data_model_id: str, job_id: str) -> Path:
        return (
            self._root
            / data_model_id
            / "generation"
            / job_id
            / "control.txt"
        )

    def request(
        self,
        data_model_id: str,
        job_id: str,
        request: GenerationJobControlRequest,
    ) -> GenerationJobControlRequest:
        """Persist a request, ensuring cancellation takes precedence."""

        if not isinstance(request, GenerationJobControlRequest):
            raise TypeError("Invalid generation control request.")

        path = self._control_path(data_model_id, job_id)

        try:
            with generation_file_lock(path):
                current = self._read(path)

                effective = (
                    GenerationJobControlRequest.CANCEL
                    if current == GenerationJobControlRequest.CANCEL
                    or request == GenerationJobControlRequest.CANCEL
                    else GenerationJobControlRequest.PAUSE
                )

                atomic_write_text(path, effective.value)
                return effective
        except OSError as exc:
            raise PersistenceOperationError(
                f"Unable to persist control request for job '{job_id}': {exc}"
            ) from exc

    def get_request(
        self,
        data_model_id: str,
        job_id: str,
    ) -> GenerationJobControlRequest | None:
        """Read the currently pending control request."""

        path = self._control_path(data_model_id, job_id)

        try:
            with generation_file_lock(path):
                return self._read(path)
        except OSError as exc:
            raise PersistenceOperationError(
                f"Unable to read control request for job '{job_id}': {exc}"
            ) from exc

    def clear_request(self, data_model_id: str, job_id: str) -> None:
        """Durably clear a request after its resulting status is persisted."""

        path = self._control_path(data_model_id, job_id)

        try:
            with generation_file_lock(path):
                atomic_write_text(path, "")
        except OSError as exc:
            raise PersistenceOperationError(
                f"Unable to clear control request for job '{job_id}': {exc}"
            ) from exc

    def clear_request_if_matches(
        self,
        data_model_id: str,
        job_id: str,
        expected: GenerationJobControlRequest,
    ) -> bool:
        """Clear only the request that was actually consumed.

        A newer request, such as CANCEL replacing PAUSE, must never
        be erased by a worker consuming the older request.
        """
        if not isinstance(expected, GenerationJobControlRequest):
            raise TypeError("Invalid expected generation control request.")

        path = self._control_path(data_model_id, job_id)

        try:
            with generation_file_lock(path):
                current = self._read(path)

                if current != expected:
                    return False

                atomic_write_text(path, "")
                return True
        except OSError as exc:
            raise PersistenceOperationError(
                f"Unable to conditionally clear control request "
                f"for job '{job_id}': {exc}"
            ) from exc

    @staticmethod
    def _read(
        path: Path,
    ) -> GenerationJobControlRequest | None:
        try:
            value = path.read_text(encoding="utf-8").strip()
        except FileNotFoundError:
            return None

        if not value:
            return None

        try:
            return GenerationJobControlRequest(value)
        except ValueError as exc:
            raise PersistenceOperationError(
                f"Invalid generation control request in '{path}'."
            ) from exc
