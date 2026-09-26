"""
File: json_specification_repository.py
Purpose: JSON-backed FORGE specification repository.

Author: Ranjoy Sen
Email: ranjoy.sen@collins.com
"""

from __future__ import annotations

import json
from pathlib import Path
from threading import Lock
from typing import Any


FORGE_VERSION = "1.0.0"
FORGE_VOCABULARY_VERSION = "1.0"


class JsonSpecificationRepository:
    """Persist one canonical FORGE specification per Data Model."""

    def __init__(self) -> None:
        self._data_directory = (
            Path(__file__).resolve().parents[2] / "data"
        )
        self._lock = Lock()

    def get_or_create(
        self,
        data_model_id: str,
        model_name: str,
        model_description: str,
    ) -> dict[str, Any]:
        """Return the canonical specification for a Data Model."""

        specification_path = self._specification_path(data_model_id)

        with self._lock:
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

    def _specification_path(
        self,
        data_model_id: str,
    ) -> Path:
        """Return the canonical specification path for a Data Model."""

        return (
            self._data_directory
            / f"forge_{data_model_id}_data_model"
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
