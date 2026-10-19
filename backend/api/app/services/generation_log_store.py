"""
Durable generation execution journal.

The JSONL journal is the authoritative persisted generation history.
Job state and checkpoint state are stored independently.
"""

import json
import os
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
    """Persist ordered generation history in an append-only JSONL journal."""

    def __init__(self, root: Path | None = None) -> None:
        self._root = root or (
            Path(__file__).resolve().parents[2]
            / "data"
            / "data_model"
        )
        self._documents: dict[Path, GenerationLogDocument] = {}
        self._journal_sizes: dict[Path, int] = {}
        self._sequence_numbers: dict[Path, int] = {}

    def _generation_directory(
        self,
        data_model_id: str,
        job_id: str,
    ) -> Path:
        return self._root / data_model_id / "generation" / job_id

    def _event_path(
        self,
        data_model_id: str,
        job_id: str,
    ) -> Path:
        return self._generation_directory(
            data_model_id,
            job_id,
        ) / "generation_log.events.jsonl"

    def create(
        self,
        *,
        data_model_id: str,
        job_id: str,
        user_id: str | None = None,
    ) -> GenerationLogDocument:
        """Initialize an empty durable journal for a generation job."""

        event_path = self._event_path(data_model_id, job_id)

        # Never destroy an existing execution journal. Job IDs are unique;
        # an existing journal indicates a duplicate initialization attempt.
        if event_path.exists():
            raise FileExistsError(
                f"Generation journal already exists for job '{job_id}'."
            )

        event_path.parent.mkdir(parents=True, exist_ok=True)
        event_path.touch(exist_ok=False)

        document = GenerationLogDocument(
            schema_version=GENERATION_LOG_SCHEMA_VERSION,
            data_model_id=data_model_id,
            job_id=job_id,
            user_id=user_id,
            entries=[],
        )
        self._documents[event_path] = document
        self._journal_sizes[event_path] = 0
        self._sequence_numbers[event_path] = 0
        return document

    def get(
        self,
        *,
        data_model_id: str,
        job_id: str,
    ) -> GenerationLogDocument | None:
        """Reconstruct generation history exclusively from the JSONL journal."""

        event_path = self._event_path(data_model_id, job_id)
        if not event_path.is_file():
            return None

        with event_path.open("r", encoding="utf-8") as handle:
            lines = handle.readlines()

        last_nonempty_line = max(
            (index for index, line in enumerate(lines) if line.strip()),
            default=-1,
        )
        entries: list[GenerationLogEntry] = []

        for line_index, line in enumerate(lines):
            line_number = line_index + 1
            if not line.strip():
                continue

            try:
                payload_entry = json.loads(line)
            except json.JSONDecodeError as exc:
                # A partially written final record must not discard earlier
                # durable events. Malformed records in the middle are errors.
                if line_index == last_nonempty_line:
                    break
                raise ValueError(
                    f"Invalid generation journal entry at "
                    f"{event_path}:{line_number}."
                ) from exc

            try:
                entries.append(
                    GenerationLogEntry.model_validate(payload_entry)
                )
            except ValueError as exc:
                raise ValueError(
                    f"Invalid generation journal entry at "
                    f"{event_path}:{line_number}."
                ) from exc

        entries.sort(key=lambda entry: entry.sequence)

        document = GenerationLogDocument(
            schema_version=GENERATION_LOG_SCHEMA_VERSION,
            data_model_id=data_model_id,
            job_id=job_id,
            entries=entries,
        )
        self._documents[event_path] = document
        self._journal_sizes[event_path] = event_path.stat().st_size
        self._sequence_numbers[event_path] = max(
            self._sequence_numbers.get(event_path, 0),
            entries[-1].sequence if entries else 0,
        )
        return document

    def append(
        self,
        *,
        data_model_id: str,
        job_id: str,
        entry: GenerationLogEntry,
        persist: bool = True,
    ) -> GenerationLogEntry:
        """Append a durable event or return a live-only transient event."""

        event_path = self._event_path(data_model_id, job_id)

        if not persist:
            document = self._documents.get(event_path)
            if document is None:
                document = self.get(
                    data_model_id=data_model_id,
                    job_id=job_id,
                )

            last_sequence = (
                document.entries[-1].sequence
                if document is not None and document.entries
                else 0
            )
            next_sequence = max(
                last_sequence,
                self._sequence_numbers.get(event_path, 0),
            ) + 1
            self._sequence_numbers[event_path] = next_sequence

            return entry.model_copy(
                update={
                    "sequence": next_sequence,
                    "timestamp": entry.timestamp or utc_now(),
                }
            )

        current_size = (
            event_path.stat().st_size if event_path.exists() else 0
        )
        document = self._documents.get(event_path)

        if (
            document is None
            or self._journal_sizes.get(event_path) != current_size
        ):
            document = self.get(
                data_model_id=data_model_id,
                job_id=job_id,
            )

        if document is None:
            document = self.create(
                data_model_id=data_model_id,
                job_id=job_id,
            )

        last_sequence = (
            document.entries[-1].sequence if document.entries else 0
        )
        next_sequence = max(
            last_sequence,
            self._sequence_numbers.get(event_path, 0),
        ) + 1
        self._sequence_numbers[event_path] = next_sequence

        recorded_entry = entry.model_copy(
            update={
                "sequence": next_sequence,
                "timestamp": entry.timestamp or utc_now(),
            }
        )

        event_path.parent.mkdir(parents=True, exist_ok=True)
        with event_path.open("a", encoding="utf-8") as handle:
            json.dump(
                recorded_entry.model_dump(
                    mode="json",
                    exclude_none=True,
                ),
                handle,
                ensure_ascii=False,
                separators=(",", ":"),
            )
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())

        document.entries.append(recorded_entry)
        self._documents[event_path] = document
        self._journal_sizes[event_path] = event_path.stat().st_size

        return recorded_entry
