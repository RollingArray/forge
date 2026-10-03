"""
Durable generation execution journal.

The generation log is the historical record for a generation job.
It is separate from job state, checkpoint state, and semantic state.
"""

import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from app.models.generation_log_model import (
    GenerationLogDocument,
    GenerationLogEntry,
)


GENERATION_LOG_SCHEMA_VERSION = 1


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class GenerationLogStore:
    """
    Persists the ordered execution history for generation jobs.

    Storage:
        data/data_model/<data_model_id>/generation/<job_id>/generation_log.json
    """

    def __init__(self, root: Path | None = None) -> None:
        self._root = root or (
            Path(__file__).resolve().parents[2]
            / "data"
            / "data_model"
        )

    def _generation_directory(
        self,
        data_model_id: str,
        job_id: str,
    ) -> Path:
        return (
            self._root
            / data_model_id
            / "generation"
            / job_id
        )

    def _log_path(
        self,
        data_model_id: str,
        job_id: str,
    ) -> Path:
        return self._generation_directory(
            data_model_id,
            job_id,
        ) / "generation_log.json"

    def create(
        self,
        *,
        data_model_id: str,
        job_id: str,
        user_id: str | None = None,
    ) -> GenerationLogDocument:
        return GenerationLogDocument(
            schema_version=GENERATION_LOG_SCHEMA_VERSION,
            data_model_id=data_model_id,
            job_id=job_id,
            user_id=user_id,
            entries=[],
        )

    def save(
        self,
        document: GenerationLogDocument,
    ) -> None:
        path = self._log_path(
            document.data_model_id,
            document.job_id,
        )

        path.parent.mkdir(parents=True, exist_ok=True)

        payload = document.model_dump(mode="json")

        file_descriptor, temporary_path = tempfile.mkstemp(
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
        )

        try:
            with os.fdopen(
                file_descriptor,
                "w",
                encoding="utf-8",
            ) as handle:
                json.dump(
                    payload,
                    handle,
                    indent=2,
                    ensure_ascii=False,
                )
                handle.write("\n")
                handle.flush()
                os.fsync(handle.fileno())

            os.replace(temporary_path, path)

        except Exception:
            try:
                os.unlink(temporary_path)
            except FileNotFoundError:
                pass
            raise

    def get(
        self,
        *,
        data_model_id: str,
        job_id: str,
    ) -> GenerationLogDocument | None:
        path = self._log_path(
            data_model_id,
            job_id,
        )

        if not path.exists():
            return None

        with path.open(
            "r",
            encoding="utf-8",
        ) as handle:
            payload = json.load(handle)

        return GenerationLogDocument.model_validate(payload)

    def append(
        self,
        entry: GenerationLogEntry,
    ) -> GenerationLogEntry:
        document = self.get(
            data_model_id=entry.data_model_id,
            job_id=entry.job_id,
        )

        if document is None:
            document = self.create(
                data_model_id=entry.data_model_id,
                job_id=entry.job_id,
                user_id=entry.user_id,
            )

        next_sequence = (
            document.entries[-1].sequence + 1
            if document.entries
            else 1
        )

        recorded_entry = entry.model_copy(
            update={
                "sequence": next_sequence,
                "timestamp": entry.timestamp or utc_now(),
            }
        )

        document.entries.append(recorded_entry)

        self.save(document)

        return recorded_entry
