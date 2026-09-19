"""
FORGE Generation Core
Synchronous generation execution.

This module coordinates planning, chunking, primitive generation,
relationship-aware generation, identity validation, and job progress.

It is UI-independent and intentionally contains no asynchronous
worker logic.
"""

from __future__ import annotations

from typing import Any

from .chunking import build_chunks
from .context import GenerationContext
from .generator import generate_entity_chunk
from .job import GenerationJob
from .output import get_entity_output_path, write_rows
from .planner import GenerationPlan
from .result import GenerationChunkResult, GenerationChunkStatus
from .semantic import generate_semantic_values


def find_entity(
    specification: dict[str, Any],
    entity_name: str,
) -> dict[str, Any]:
    """Return an entity definition by name."""

    for entity in specification.get("entities", []):
        if entity.get("name") == entity_name:
            return entity

    raise ValueError(f"Entity {entity_name!r} was not found in the specification.")


def get_identity_fields(
    entity: dict[str, Any],
) -> tuple[str, ...]:
    """Return the declared identity fields for an entity."""

    identity = entity.get(
        "identity",
        {},
    )

    if not isinstance(identity, dict):
        return ()

    fields = identity.get(
        "fields",
        [],
    )

    if not isinstance(fields, list):
        return ()

    return tuple(fields)


def build_semantic_values(
    entity: dict[str, Any],
) -> dict[str, list[str]]:
    """Generate semantic preview values required by an entity."""

    semantic_values_by_field: dict[str, list[str]] = {}

    for field in entity.get("fields", []):
        generation = field.get("generation")

        if (
            field.get("type") == "STRING"
            and isinstance(generation, dict)
            and generation.get("generator") == "SEMANTIC"
        ):
            field_name = field.get("name")

            if not isinstance(field_name, str) or not field_name:
                raise ValueError(
                    f"{entity.get('name')}: semantic field "
                    "must have a non-empty name."
                )

            parameters = generation.get(
                "parameters",
                {},
            )

            description = parameters.get("description")

            if not isinstance(description, str) or not description:
                raise ValueError(
                    f"{entity.get('name')}.{field_name}: "
                    "SEMANTIC generation requires a description."
                )

            semantic_values_by_field[field_name] = generate_semantic_values(description)

    return semantic_values_by_field


def _prepare_entity_execution(
    specification: dict[str, Any],
    entity_name: str,
    target_rows: int,
    chunk_size: int,
    output_directory: str,
) -> tuple[
    dict[str, Any],
    list[Any],
    Any,
    tuple[str, ...],
    dict[str, list[str]],
]:
    """Prepare all immutable state required for entity execution."""

    entity = find_entity(
        specification,
        entity_name,
    )

    chunks = build_chunks(
        entity_name=entity_name,
        total_rows=target_rows,
        chunk_size=chunk_size,
    )

    output_path = get_entity_output_path(
        output_directory=output_directory,
        entity_name=entity_name,
    )

    identity_fields = get_identity_fields(entity)

    semantic_values_by_field = build_semantic_values(entity)

    return (
        entity,
        chunks,
        output_path,
        identity_fields,
        semantic_values_by_field,
    )


def _build_chunk_result(
    entity_name: str,
    chunk_number: int,
    row_count: int,
    output_path: Any,
    status: GenerationChunkStatus,
    error: str | None = None,
) -> GenerationChunkResult:
    """Build a generation result for one chunk."""

    return GenerationChunkResult(
        entity_name=entity_name,
        chunk_number=chunk_number,
        row_count=row_count,
        status=status,
        elapsed_seconds=0.0,
        output_path=str(output_path),
        error=error,
    )


def _execute_chunk(
    entity: dict[str, Any],
    chunk: Any,
    seed: int,
    output_path: Any,
    identity_fields: tuple[str, ...],
    semantic_values_by_field: dict[str, list[str]],
    dependencies: tuple[Any, ...],
    relationships: tuple[Any, ...],
    constraints: tuple[Any, ...],
    context: GenerationContext,
    existing_identities: set[tuple[Any, ...]],
) -> GenerationChunkResult:
    """Generate, persist, and register one generation chunk."""

    entity_name = entity["name"]

    try:
        rows = generate_entity_chunk(
            entity=entity,
            start_row=chunk.start_row,
            row_count=chunk.row_count,
            seed=seed,
            semantic_values_by_field=semantic_values_by_field,
            dependencies=dependencies,
            context=context,
            relationships=relationships,
            existing_identities=existing_identities,
            constraints=constraints,
        )

        write_rows(
            output_path=output_path,
            rows=rows,
        )

        context.add_rows(
            entity_name,
            rows,
            identity_fields,
        )

        return _build_chunk_result(
            entity_name=entity_name,
            chunk_number=chunk.chunk_number,
            row_count=len(rows),
            output_path=output_path,
            status=GenerationChunkStatus.COMPLETED,
        )

    except Exception as exc:
        return _build_chunk_result(
            entity_name=entity_name,
            chunk_number=chunk.chunk_number,
            row_count=0,
            output_path=output_path,
            status=GenerationChunkStatus.FAILED,
            error=str(exc),
        )


def _prepare_entity_execution(
    specification: dict[str, Any],
    entity_name: str,
    target_rows: int,
    chunk_size: int,
    output_directory: str,
) -> tuple[
    dict[str, Any],
    list[Any],
    Any,
    tuple[str, ...],
    dict[str, list[str]],
]:
    """Prepare all immutable state required for entity execution."""

    entity = find_entity(
        specification,
        entity_name,
    )

    chunks = build_chunks(
        entity_name=entity_name,
        total_rows=target_rows,
        chunk_size=chunk_size,
    )

    output_path = get_entity_output_path(
        output_directory=output_directory,
        entity_name=entity_name,
    )

    identity_fields = get_identity_fields(entity)

    semantic_values_by_field = build_semantic_values(entity)

    return (
        entity,
        chunks,
        output_path,
        identity_fields,
        semantic_values_by_field,
    )


def _build_chunk_result(
    entity_name: str,
    chunk_number: int,
    row_count: int,
    output_path: Any,
    status: GenerationChunkStatus,
    error: str | None = None,
) -> GenerationChunkResult:
    """Build a generation result for one chunk."""

    return GenerationChunkResult(
        entity_name=entity_name,
        chunk_number=chunk_number,
        row_count=row_count,
        status=status,
        elapsed_seconds=0.0,
        output_path=str(output_path),
        error=error,
    )


def _execute_chunk(
    entity: dict[str, Any],
    chunk: Any,
    seed: int,
    output_path: Any,
    identity_fields: tuple[str, ...],
    semantic_values_by_field: dict[str, list[str]],
    dependencies: tuple[Any, ...],
    relationships: tuple[Any, ...],
    constraints: tuple[Any, ...],
    context: GenerationContext,
    existing_identities: set[tuple[Any, ...]],
) -> GenerationChunkResult:
    """Generate, persist, and register one generation chunk."""

    entity_name = entity["name"]

    try:
        rows = generate_entity_chunk(
            entity=entity,
            start_row=chunk.start_row,
            row_count=chunk.row_count,
            seed=seed,
            semantic_values_by_field=semantic_values_by_field,
            dependencies=dependencies,
            context=context,
            relationships=relationships,
            existing_identities=existing_identities,
            constraints=constraints,
        )

        write_rows(
            output_path=output_path,
            rows=rows,
        )

        context.add_rows(
            entity_name,
            rows,
            identity_fields,
        )

        return _build_chunk_result(
            entity_name=entity_name,
            chunk_number=chunk.chunk_number,
            row_count=len(rows),
            output_path=output_path,
            status=GenerationChunkStatus.COMPLETED,
        )

    except Exception as exc:
        return _build_chunk_result(
            entity_name=entity_name,
            chunk_number=chunk.chunk_number,
            row_count=0,
            output_path=output_path,
            status=GenerationChunkStatus.FAILED,
            error=str(exc),
        )


def execute_entity(
    specification: dict[str, Any],
    job: GenerationJob,
    entity_name: str,
    target_rows: int,
    seed: int,
    chunk_size: int,
    output_directory: str,
    context: GenerationContext,
    dependencies: tuple[Any, ...] = (),
    relationships: tuple[Any, ...] = (),
    constraints: tuple[Any, ...] = (),
) -> bool:
    """Synchronously execute all chunks for one entity."""

    (
        entity,
        chunks,
        output_path,
        identity_fields,
        semantic_values_by_field,
    ) = _prepare_entity_execution(
        specification=specification,
        entity_name=entity_name,
        target_rows=target_rows,
        chunk_size=chunk_size,
        output_directory=output_directory,
    )

    existing_identities: set[tuple[Any, ...]] = set()

    for chunk in chunks:
        result = _execute_chunk(
            entity=entity,
            chunk=chunk,
            seed=seed,
            output_path=output_path,
            identity_fields=identity_fields,
            semantic_values_by_field=semantic_values_by_field,
            dependencies=dependencies,
            relationships=relationships,
            constraints=constraints,
            context=context,
            existing_identities=existing_identities,
        )

        job.record_chunk_result(result)

        if result.status == GenerationChunkStatus.FAILED:
            return False

    return True


def execute_generation_plan(
    specification: dict[str, Any],
    job: GenerationJob,
    plan: GenerationPlan,
    seed: int,
    chunk_size: int,
    output_directory: str,
) -> GenerationJob:
    """
    Execute a generation plan synchronously.

    Entities are generated in dependency order so that generated
    parent context is available to dependent entities.
    """

    job.start_planning()

    try:
        job.start_running()

        context = GenerationContext()

        entity_plans = {entity.entity_name: entity for entity in plan.entities}

        for entity_name in plan.generation_order:

            entity_plan = entity_plans[entity_name]

            entity_completed = execute_entity(
                specification=specification,
                job=job,
                entity_name=entity_plan.entity_name,
                target_rows=entity_plan.target_rows,
                seed=seed,
                chunk_size=chunk_size,
                output_directory=output_directory,
                context=context,
                dependencies=entity_plan.dependencies,
                relationships=plan.relationships,
                constraints=plan.constraints,
            )

            if not entity_completed:
                job.fail(job.error or "Entity generation failed.")
                return job

        job.complete()

    except Exception as exc:
        job.fail(str(exc))

    return job
