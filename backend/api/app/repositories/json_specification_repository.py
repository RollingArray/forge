"""
File: json_specification_repository.py
Purpose: JSON-backed FORGE specification repository.

Author: Ranjoy Sen
Email: ranjoy.sen@collins.com
"""

from __future__ import annotations

import json
import hashlib
import fcntl
from contextlib import contextmanager
from pathlib import Path
from threading import Lock, RLock, local
from typing import Any, Iterator


FORGE_VERSION = "1.0.0"
FORGE_VOCABULARY_VERSION = "1.0"


class SpecificationRevisionConflict(Exception):
    """Raised when a specification changed after it was reviewed."""


class JsonSpecificationRepository:
    """Persist one canonical FORGE specification per Data Model."""

    _registry_guard = Lock()
    _path_locks: dict[str, RLock] = {}
    _transaction_state = local()

    def __init__(self) -> None:
        self._data_directory = (
            Path(__file__).resolve().parents[2] / "data"
        )

    def get_or_create(
        self,
        data_model_id: str,
        model_name: str,
        model_description: str,
    ) -> dict[str, Any]:
        """Return the canonical specification for a Data Model."""

        specification_path = self._specification_path(data_model_id)

        with self.transaction(data_model_id):
            if specification_path.exists():
                return self._read(specification_path)

            specification = self._create_empty_specification(
                model_name=model_name,
                model_description=model_description,
            )

            self._write(
                specification_path,
                specification,
            )

            return specification

    def save(
        self,
        data_model_id: str,
        specification: dict[str, Any],
    ) -> dict[str, Any]:
        """Persist the canonical specification."""

        specification_path = self._specification_path(data_model_id)

        with self.transaction(data_model_id):
            self._write(
                specification_path,
                specification,
            )

        return specification

    @contextmanager
    def transaction(self, data_model_id: str) -> Iterator[None]:
        """Serialize operations across threads, instances, and processes."""

        lock_path = (
            self._data_directory
            / ".locks"
            / f"{data_model_id}.lock"
        )
        lock_path.parent.mkdir(parents=True, exist_ok=True)
        lock_key = str(lock_path.resolve())

        with self._registry_guard:
            thread_lock = self._path_locks.setdefault(
                lock_key,
                RLock(),
            )

        with thread_lock:
            depths = getattr(self._transaction_state, "depths", {})
            descriptors = getattr(
                self._transaction_state,
                "descriptors",
                {},
            )
            depth = depths.get(lock_key, 0)

            if depth == 0:
                descriptor = lock_path.open("a+")
                try:
                    fcntl.flock(descriptor.fileno(), fcntl.LOCK_EX)
                except Exception:
                    descriptor.close()
                    raise
                descriptors[lock_key] = descriptor

            depths[lock_key] = depth + 1
            self._transaction_state.depths = depths
            self._transaction_state.descriptors = descriptors

            try:
                yield
            finally:
                remaining = depths[lock_key] - 1
                if remaining:
                    depths[lock_key] = remaining
                else:
                    depths.pop(lock_key, None)
                    descriptor = descriptors.pop(lock_key)
                    try:
                        fcntl.flock(
                            descriptor.fileno(),
                            fcntl.LOCK_UN,
                        )
                    finally:
                        descriptor.close()

    @staticmethod
    def revision(specification: dict[str, Any]) -> str:
        """Return a stable SHA-256 revision for a specification."""

        canonical = json.dumps(
            specification,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        ).encode("utf-8")
        return hashlib.sha256(canonical).hexdigest()

    def read(self, data_model_id: str) -> dict[str, Any] | None:
        """Read without creating a missing specification."""

        specification_path = self._specification_path(data_model_id)
        with self.transaction(data_model_id):
            if not specification_path.exists():
                return None
            return self._read(specification_path)

    def save_if_revision(
        self,
        data_model_id: str,
        expected_revision: str,
        specification: dict[str, Any],
        missing_specification: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Atomically compare the current revision and persist the candidate."""

        specification_path = self._specification_path(data_model_id)

        with self.transaction(data_model_id):
            if specification_path.exists():
                current = self._read(specification_path)
            else:
                current = missing_specification

            current_revision = (
                self.revision(current)
                if current is not None
                else None
            )

            if current_revision != expected_revision:
                raise SpecificationRevisionConflict(
                    "The specification changed after preview. "
                    "Refresh the preview before applying the import."
                )

            self._write(specification_path, specification)
            return specification

    def _specification_path(
        self,
        data_model_id: str,
    ) -> Path:
        """Return the canonical specification path for a Data Model."""

        return (
            self._data_directory
            / "data_model"
            / data_model_id
            / "specification.json"
        )

    @staticmethod
    def _create_empty_specification(
        model_name: str,
        model_description: str,
    ) -> dict[str, Any]:
        """Create the canonical empty FORGE authoring model."""

        return {
            "version": FORGE_VERSION,
            "vocabulary_version": FORGE_VOCABULARY_VERSION,
            "model": {
                "name": model_name,
                "description": model_description,
            },
            "generation": {
                "seed": 42,
                "scenario": "NORMAL",
            },
            "entities": [],
            "relationships": [],
            "foreign_keys": [],
            "constraints": [],
            "dependencies": [],
            "statistical_behavior": [],
            "scenarios": [],
        }

    @staticmethod
    def _read(
        path: Path,
    ) -> dict[str, Any]:
        """Read a JSON specification."""

        with path.open(
            "r",
            encoding="utf-8",
        ) as file:
            specification = json.load(file)

        if not isinstance(specification, dict):
            raise ValueError(
                f"FORGE specification root must be an object: {path}"
            )

        return specification

    @staticmethod
    def _write(
        path: Path,
        specification: dict[str, Any],
    ) -> None:
        """Write a specification atomically."""

        path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        temporary_path = path.with_suffix(".tmp")

        with temporary_path.open(
            "w",
            encoding="utf-8",
        ) as file:
            json.dump(
                specification,
                file,
                indent=2,
            )
            file.write("\n")

        temporary_path.replace(path)
