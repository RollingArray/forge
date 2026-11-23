"""Strict, versioned persistence models for FORGE generation state."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from pathlib import PurePosixPath
import unicodedata
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


_SHA256_PATTERN = r"(?i)^[0-9a-f]{64}$"


def _require_aware_datetime(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("Timestamp must include a timezone.")
    return value


def _validate_relative_artifact_path(value: str) -> str:
    """Require a normalized, portable relative POSIX artifact path."""

    if not value:
        raise ValueError("Artifact path must be non-empty.")

    if "\\" in value:
        raise ValueError("Artifact paths must use POSIX '/' separators.")

    if value.startswith("/"):
        raise ValueError("Artifact path must be relative.")

    if unicodedata.normalize("NFC", value) != value:
        raise ValueError("Artifact path must use Unicode NFC normalization.")

    parts = value.split("/")
    if any(part in ("", ".", "..") for part in parts):
        raise ValueError(
            "Artifact path must be normalized and cannot traverse directories."
        )

    windows_reserved_names = {
        "CON", "PRN", "AUX", "NUL",
        *(f"COM{i}" for i in range(1, 10)),
        *(f"LPT{i}" for i in range(1, 10)),
    }

    for part in parts:
        if any(ord(character) < 32 for character in part):
            raise ValueError("Artifact path cannot contain control characters.")

        if any(character in '<>:"|?*' for character in part):
            raise ValueError("Artifact path contains a character unsupported on Windows.")

        if part.endswith((" ", ".")):
            raise ValueError(
                "Artifact path components cannot end with spaces or periods."
            )

        reserved_basename = part.split(".", 1)[0].upper()
        if reserved_basename in windows_reserved_names:
            raise ValueError(
                f"Artifact path contains a reserved Windows name: '{part}'."
            )

    path = PurePosixPath(value)
    if path.is_absolute() or path.as_posix() != value:
        raise ValueError(
            "Artifact path must be a normalized relative POSIX path."
        )

    return value


def _artifact_path_collision_key(value: str) -> str:
    """Return a key that detects aliases on common case-insensitive filesystems."""

    return unicodedata.normalize("NFC", value).casefold()


class PersistenceModel(BaseModel):
    """Common strict configuration for persisted models."""

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        validate_assignment=True,
    )


class GenerationArtifactEvidence(PersistenceModel):
    """Integrity evidence for one atomically published artifact."""

    path: str = Field(min_length=1)
    size_bytes: int = Field(strict=True, ge=1)
    sha256: str = Field(pattern=_SHA256_PATTERN)

    @field_validator("path")
    @classmethod
    def validate_path(cls, value: str) -> str:
        return _validate_relative_artifact_path(value)

    @field_validator("sha256")
    @classmethod
    def normalize_sha256(cls, value: str) -> str:
        return value.lower()


class GenerationChunkEvidence(PersistenceModel):
    """Durable evidence for one committed entity chunk."""

    chunk_number: int = Field(strict=True, ge=1)
    row_start: int = Field(strict=True, ge=0)
    row_count: int = Field(strict=True, ge=1)
    artifact: GenerationArtifactEvidence
    committed_at: datetime

    @field_validator("committed_at")
    @classmethod
    def validate_committed_at(cls, value: datetime) -> datetime:
        return _require_aware_datetime(value)


class GenerationFinalizationStatus(StrEnum):
    """Publication state of an entity's consolidated output."""

    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    COMMITTED = "COMMITTED"


class GenerationFinalization(PersistenceModel):
    """Finalization state and evidence for one entity."""

    status: GenerationFinalizationStatus = GenerationFinalizationStatus.PENDING
    output: GenerationArtifactEvidence | None = None

    @model_validator(mode="after")
    def validate_output_for_status(self) -> GenerationFinalization:
        if self.status == GenerationFinalizationStatus.COMMITTED:
            if self.output is None:
                raise ValueError(
                    "Committed finalization requires consolidated output evidence."
                )
        elif self.output is not None:
            raise ValueError(
                "Consolidated output evidence is only valid for committed finalization."
            )

        return self


class GenerationEntityCheckpoint(PersistenceModel):
    """Authoritative checkpoint state for one generated entity."""

    target_rows: int = Field(strict=True, ge=0)
    chunks: list[GenerationChunkEvidence] = Field(default_factory=list)
    finalization: GenerationFinalization = Field(
        default_factory=GenerationFinalization
    )

    @model_validator(mode="after")
    def validate_chunks(self) -> GenerationEntityCheckpoint:
        chunk_numbers = [chunk.chunk_number for chunk in self.chunks]

        if len(chunk_numbers) != len(set(chunk_numbers)):
            raise ValueError("Chunk numbers must be unique.")

        if chunk_numbers != sorted(chunk_numbers):
            raise ValueError("Chunks must be ordered by ascending chunk number.")

        previous_end = 0
        for chunk in self.chunks:
            if chunk.row_start < previous_end:
                raise ValueError("Committed chunk row ranges cannot overlap.")

            chunk_end = chunk.row_start + chunk.row_count
            if chunk_end > self.target_rows:
                raise ValueError("Committed chunk rows exceed the entity target.")

            previous_end = chunk_end

        if (
            self.finalization.status == GenerationFinalizationStatus.COMMITTED
            and sum(chunk.row_count for chunk in self.chunks) != self.target_rows
        ):
            raise ValueError(
                "Entity finalization requires all target rows to be committed."
            )

        return self

    @property
    def committed_rows(self) -> int:
        """Derive committed rows exclusively from committed chunk evidence."""

        return sum(chunk.row_count for chunk in self.chunks)


class GenerationCheckpointManifest(PersistenceModel):
    """Authoritative v2 checkpoint manifest for one generation job."""

    schema_version: Literal[2] = 2
    data_model_id: str = Field(min_length=1)
    job_id: str = Field(min_length=1)
    specification_hash: str = Field(pattern=_SHA256_PATTERN)
    seed: int = Field(strict=True)
    chunk_size: int = Field(strict=True, ge=1)
    algorithm_version: str = Field(min_length=1)
    attempt_id: str = Field(min_length=1)
    entities: dict[str, GenerationEntityCheckpoint] = Field(min_length=1)
    created_at: datetime
    updated_at: datetime

    @field_validator("specification_hash")
    @classmethod
    def normalize_specification_hash(cls, value: str) -> str:
        return value.lower()

    @field_validator("created_at", "updated_at")
    @classmethod
    def validate_timestamps(cls, value: datetime) -> datetime:
        return _require_aware_datetime(value)

    @model_validator(mode="after")
    def validate_manifest(self) -> GenerationCheckpointManifest:
        if self.updated_at < self.created_at:
            raise ValueError("updated_at cannot be earlier than created_at.")

        artifact_paths: set[str] = set()

        for entity_name, entity in self.entities.items():
            if not entity_name.strip():
                raise ValueError("Entity names must be non-empty.")

            for chunk in entity.chunks:
                expected_row_start = (chunk.chunk_number - 1) * self.chunk_size

                if chunk.row_start != expected_row_start:
                    raise ValueError(
                        f"Entity '{entity_name}' chunk {chunk.chunk_number} "
                        f"must start at row {expected_row_start}."
                    )

                expected_row_count = min(
                    self.chunk_size,
                    entity.target_rows - expected_row_start,
                )

                if expected_row_count <= 0:
                    raise ValueError(
                        f"Entity '{entity_name}' chunk {chunk.chunk_number} "
                        "starts beyond the entity target."
                    )

                if chunk.row_count != expected_row_count:
                    raise ValueError(
                        f"Entity '{entity_name}' chunk {chunk.chunk_number} "
                        f"must contain exactly {expected_row_count} rows."
                    )

                artifact_key = _artifact_path_collision_key(
                    chunk.artifact.path
                )
                if artifact_key in artifact_paths:
                    raise ValueError(
                        f"Artifact path '{chunk.artifact.path}' collides with "
                        "another artifact path in the manifest."
                    )

                artifact_paths.add(artifact_key)

            output = entity.finalization.output
            if output is not None:
                output_key = _artifact_path_collision_key(output.path)
                if output_key in artifact_paths:
                    raise ValueError(
                        f"Artifact path '{output.path}' collides with "
                        "another artifact path in the manifest."
                    )

                artifact_paths.add(output_key)

        return self
