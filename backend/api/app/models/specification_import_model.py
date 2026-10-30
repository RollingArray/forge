"""
File: specification_import_model.py
Purpose: API contracts for incremental FORGE specification CSV imports.
"""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class SpecificationImportCsvModel(BaseModel):
    """CSV text supplied for each Specification Wizard section."""

    model_config = ConfigDict(extra="forbid")

    entities: str = ""
    fields_and_keys: str = ""
    foreign_keys: str = ""
    relationships: str = ""
    constraints: str = ""


class SpecificationImportPreviewRequest(BaseModel):
    """Request to preview an incremental specification import."""

    model_config = ConfigDict(extra="forbid")

    csv: SpecificationImportCsvModel


class SpecificationImportApplyRequest(BaseModel):
    """Request to apply the exact CSV reviewed in a preview."""

    model_config = ConfigDict(extra="forbid")

    base_revision: str = Field(
        min_length=64,
        max_length=64,
        pattern=r"^[a-f0-9]{64}$",
    )
    csv_digest: str = Field(
        min_length=64,
        max_length=64,
        pattern=r"^[a-f0-9]{64}$",
    )
    csv: SpecificationImportCsvModel


class SpecificationImportPreviewResponse(BaseModel):
    """Structured preview of additions and import findings."""

    model_config = ConfigDict(extra="forbid")

    base_revision: str
    csv_digest: str
    can_apply: bool
    summary: dict[str, int]
    sections: dict[str, dict[str, Any]]
    additions: list[dict[str, Any]]
    already_present: list[dict[str, Any]]
    conflicts: list[dict[str, Any]]
    issues: list[dict[str, Any]]


class SpecificationImportApplyResponse(BaseModel):
    """Result of applying a reviewed specification import."""

    model_config = ConfigDict(extra="forbid")

    applied: bool
    summary: dict[str, int]
    specification_revision: str
