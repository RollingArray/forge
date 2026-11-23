"""
Durable generation execution journal.

The JSONL journal is the authoritative persisted generation history.
Job state and checkpoint state are stored independently.
"""

import json
import os
from datetime import datetime, timezone
from pathlib import Path

from app.services.generation_file_persistence import (
    atomic_write_text,
    generation_file_lock,
)

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
        """Initialize an empty journal under its cross-process lock."""

        event_path = self._event_path(data_model_id, job_id)

        with generation_file_lock(event_path):
            if event_path.exists():
                raise FileExistsError(
                    f"Generation journal already exists for job '{job_id}'."
                )

            event_path.parent.mkdir(parents=True, exist_ok=True)
            atomic_write_text(event_path, "")

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
        """Read a consistent journal snapshot and validate its sequence."""

        event_path = self._event_path(data_model_id, job_id)

        if not event_path.is_file():
            return None

        with generation_file_lock(event_path):
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
                    if line_index == last_nonempty_line:
                        break
                    raise ValueError(
                        f"Invalid generation journal entry at "
                        f"{event_path}:{line_number}."
                    ) from exc

                try:
                    entry = GenerationLogEntry.model_validate(payload_entry)
                except ValueError as exc:
                    raise ValueError(
                        f"Invalid generation journal entry at "
                        f"{event_path}:{line_number}."
                    ) from exc

                if entries and entry.sequence <= entries[-1].sequence:
                    raise ValueError(
                        f"Invalid generation journal sequence at "
                        f"{event_path}:{line_number}: expected a value "
                        f"greater than {entries[-1].sequence}, "
                        f"received {entry.sequence}."
                    )

                entries.append(entry)

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

    def _repair_incomplete_tail(self, event_path: Path) -> None:
        """Remove an incomplete final JSON record before another append."""

        if not event_path.exists():
            return

        raw = event_path.read_bytes()
        lines = raw.splitlines(keepends=True)
        last_nonempty = max(
            (
                index
                for index, line in enumerate(lines)
                if line.strip()
            ),
            default=-1,
        )

        offset = 0
        truncate_at = None

        for index, line in enumerate(lines):
            payload = line.rstrip(b"\r\n")

            if not payload.strip():
                offset += len(line)
                continue

            try:
                json.loads(payload.decode("utf-8"))
            except json.JSONDecodeError as exc:
                if index != last_nonempty:
                    raise ValueError(
                        f"Invalid generation journal entry at "
                        f"{event_path}:{index + 1}."
                    ) from exc

                truncate_at = offset
                break

            offset += len(line)

        if truncate_at is not None:
            with event_path.open("r+b") as handle:
                handle.truncate(truncate_at)
                handle.flush()
                os.fsync(handle.fileno())

        # A complete JSON record can survive a crash before its newline.
        # Terminate it before appending the next record.
        with event_path.open("rb") as handle:
            handle.seek(0, os.SEEK_END)
            size = handle.tell()
            if size == 0:
                return
            handle.seek(-1, os.SEEK_END)
            last_byte = handle.read(1)

        if last_byte != b"\n":
            with event_path.open("ab") as handle:
                handle.write(b"\n")
                handle.flush()
                os.fsync(handle.fileno())

    def append(
        self,
        *,
        data_model_id: str,
        job_id: str,
        entry: GenerationLogEntry,
        persist: bool = True,
    ) -> GenerationLogEntry:
        """Append a durable event under a cross-process journal transaction."""

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

        with generation_file_lock(event_path):
            event_path.parent.mkdir(parents=True, exist_ok=True)

            if not event_path.exists():
                self.create(
                    data_model_id=data_model_id,
                    job_id=job_id,
                )

            self._repair_incomplete_tail(event_path)

            # Always reload under the lock. Process-local caches cannot
            # safely allocate sequence numbers across independent writers.
            document = self.get(
                data_model_id=data_model_id,
                job_id=job_id,
            )

            if document is None:
                raise RuntimeError(
                    f"Generation journal disappeared for job '{job_id}'."
                )

            last_sequence = max(
                (item.sequence for item in document.entries),
                default=0,
            )
            next_sequence = max(
                last_sequence,
                self._sequence_numbers.get(event_path, 0),
            ) + 1

            recorded_entry = entry.model_copy(
                update={
                    "sequence": next_sequence,
                    "timestamp": entry.timestamp or utc_now(),
                }
            )

            with event_path.open(
                "a",
                encoding="utf-8",
                newline="",
            ) as handle:
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
            self._sequence_numbers[event_path] = next_sequence
            self._journal_sizes[event_path] = event_path.stat().st_size

            return recorded_entry
