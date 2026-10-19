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
        self._documents: dict[Path, GenerationLogDocument] = {}
        self._journal_sizes: dict[Path, int] = {}

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
        document = GenerationLogDocument(
            schema_version=GENERATION_LOG_SCHEMA_VERSION,
            data_model_id=data_model_id,
            job_id=job_id,
            user_id=user_id,
            entries=[],
        )

        event_path = self._event_path(data_model_id, job_id)
        event_path.unlink(missing_ok=True)
        self.save(document)

        return document

    def save(
        self,
        document: GenerationLogDocument,
    ) -> None:
        """Atomically write a compatible JSON snapshot."""

        path = self._log_path(
            document.data_model_id,
            document.job_id,
        )
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = document.model_dump(mode="json", exclude_none=True)

        file_descriptor, temporary_path = tempfile.mkstemp(
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
        )

        try:
            with os.fdopen(file_descriptor, "w", encoding="utf-8") as handle:
                json.dump(payload, handle, indent=2, ensure_ascii=False)
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

        self._documents[path] = document
        event_path = self._event_path(
            document.data_model_id,
            document.job_id,
        )
        self._journal_sizes[path] = (
            event_path.stat().st_size if event_path.exists() else 0
        )

    def get(
        self,
        *,
        data_model_id: str,
        job_id: str,
    ) -> GenerationLogDocument | None:
        """Load a snapshot and merge durable journal events by sequence."""

        path = self._log_path(data_model_id, job_id)
        event_path = self._event_path(data_model_id, job_id)

        payload = None
        if path.is_file():
            with path.open("r", encoding="utf-8") as handle:
                payload = json.load(handle)

        journal_entries = []
        if event_path.is_file():
            with event_path.open("r", encoding="utf-8") as handle:
                lines = handle.readlines()

            last_nonempty_line = max(
                (index for index, line in enumerate(lines) if line.strip()),
                default=-1,
            )
            for line_index, line in enumerate(lines):
                line_number = line_index + 1
                if not line.strip():
                    continue
                try:
                    payload_entry = json.loads(line)
                except json.JSONDecodeError as exc:
                    # Ignore a truncated final record, but preserve errors
                    # for malformed records earlier in the journal.
                    if line_index == last_nonempty_line:
                        break
                    raise ValueError(
                        f"Invalid generation journal entry at "
                        f"{event_path}:{line_number}."
                    ) from exc

                try:
                    journal_entries.append(
                        GenerationLogEntry.model_validate(payload_entry)
                    )
                except ValueError as exc:
                    raise ValueError(
                        f"Invalid generation journal entry at "
                        f"{event_path}:{line_number}."
                    ) from exc

        if payload is None and not journal_entries:
            return None

        if payload is None:
            document = GenerationLogDocument(
                schema_version=GENERATION_LOG_SCHEMA_VERSION,
                data_model_id=data_model_id,
                job_id=job_id,
                entries=[],
            )
            snapshot_entries = []
        else:
            document = GenerationLogDocument.model_validate(
                {**payload, "entries": []}
            )
            snapshot_entries = payload.get("entries", [])

        entries_by_sequence = {
            entry.sequence: entry
            for entry in (
                GenerationLogEntry.model_validate(entry)
                for entry in snapshot_entries
            )
        }
        for entry in journal_entries:
            entries_by_sequence[entry.sequence] = entry

        document.entries = [
            entries_by_sequence[sequence]
            for sequence in sorted(entries_by_sequence)
        ]

        self._documents[path] = document
        self._journal_sizes[path] = (
            event_path.stat().st_size if event_path.exists() else 0
        )
        return document

    def append(
        self,
        *,
        data_model_id: str,
        job_id: str,
        entry: GenerationLogEntry,
    ) -> GenerationLogEntry:
        """Durably append one event; periodically refresh the JSON snapshot."""

        path = self._log_path(data_model_id, job_id)
        event_path = self._event_path(data_model_id, job_id)
        current_size = event_path.stat().st_size if event_path.exists() else 0

        document = self._documents.get(path)
        if (
            document is None
            or self._journal_sizes.get(path) != current_size
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

        event_path.parent.mkdir(parents=True, exist_ok=True)
        with event_path.open("a", encoding="utf-8") as handle:
            json.dump(
                recorded_entry.model_dump(mode="json", exclude_none=True),
                handle,
                ensure_ascii=False,
                separators=(",", ":"),
            )
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())

        document.entries.append(recorded_entry)
        self._documents[path] = document
        self._journal_sizes[path] = event_path.stat().st_size

        # Keep snapshots useful for inspection without rewriting the complete
        # document for every field/chunk event.
        if (
            len(document.entries) % 100 == 0
            or recorded_entry.stage in ("COMPLETED", "FAILED")
        ):
            self.save(document)

        return recorded_entry
