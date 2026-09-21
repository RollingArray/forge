"""
FORGE Generation Core
Synchronous generation execution.

This module coordinates planning, chunking, primitive generation,
relationship-aware generation, identity validation, and job progress.

It is UI-independent and intentionally contains no asynchronous
worker logic.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .checkpoint import (
    GenerationCheckpoint,
    compute_specification_hash,
    create_checkpoint,
    load_checkpoint,
    write_checkpoint,
)
from .chunking import build_chunks
from .context import GenerationContext
from .generator import generate_entity_chunk
from .job import EntityGenerationStatus, GenerationJob
from .output import (
    get_chunk_output_path,
    read_rows,
    write_chunk_atomically,
)
from .planner import GenerationPlan
from .progress import CLIProgressReporter
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

            if not isinstance(parameters, dict):
                raise ValueError(
                    f"{entity.get('name')}.{field_name}: "
                    "SEMANTIC generation parameters must be an object."
                )

            description = parameters.get("description")

            if not isinstance(description, str) or not description:
                raise ValueError(
                    f"{entity.get('name')}.{field_name}: "
                    "SEMANTIC generation requires a description."
                )

            mode = parameters.get(
                "mode",
                "VOCABULARY",
            )

            if not isinstance(mode, str) or not mode.strip():
                raise ValueError(
                    f"{entity.get('name')}.{field_name}: "
                    "SEMANTIC generation mode must be a non-empty string."
                )

            semantic_values_by_field[field_name] = generate_semantic_values(
                description,
                mode=mode,
            )

    return semantic_values_by_field


def _build_entity_targets(
    plan: GenerationPlan,
) -> dict[str, int]:
    """Return target row counts keyed by entity name."""

    return {
        entity.entity_name: entity.target_rows
        for entity in plan.entities
    }


def _load_or_create_checkpoint(
    *,
    checkpoint_path: str,
    job: GenerationJob,
    specification: dict[str, Any],
    plan: GenerationPlan,
    seed: int,
    chunk_size: int,
) -> GenerationCheckpoint:
    """
    Load an existing checkpoint or create a new one.

    Existing checkpoints are accepted only when their generation
    identity matches the current job and specification.
    """

    path = Path(checkpoint_path)

    if path.exists():
        checkpoint = load_checkpoint(path)

        checkpoint.validate_identity(
            job_id=job.job_id,
            specification_hash=compute_specification_hash(
                specification
            ),
            seed=seed,
            chunk_size=chunk_size,
        )

        return checkpoint

    checkpoint = create_checkpoint(
        job_id=job.job_id,
        specification=specification,
        seed=seed,
        chunk_size=chunk_size,
        entity_targets=_build_entity_targets(plan),
    )

    write_checkpoint(
        checkpoint,
        path,
    )

    return checkpoint


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

    identity_fields = get_identity_fields(entity)

    semantic_values_by_field = build_semantic_values(entity)

    return (
        entity,
        chunks,
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
    output_directory: str | Path,
    identity_fields: tuple[str, ...],
    semantic_values_by_field: dict[str, list[str]],
    dependencies: tuple[Any, ...],
    relationships: tuple[Any, ...],
    relationship_groups: tuple[Any, ...],
    constraints: tuple[Any, ...],
    context: GenerationContext,
    existing_identities: set[tuple[Any, ...]],
) -> GenerationChunkResult:
    """Generate, persist, and register one generation chunk."""

    entity_name = entity["name"]

    chunk_output_path = get_chunk_output_path(
        output_directory=output_directory,
        entity_name=entity_name,
        chunk_number=chunk.chunk_number,
    )

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
            relationship_groups=relationship_groups,
            existing_identities=existing_identities,
            constraints=constraints,
        )

        write_chunk_atomically(
            output_path=chunk_output_path,
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
            output_path=chunk_output_path,
            status=GenerationChunkStatus.COMPLETED,
        )

    except Exception as exc:
        return _build_chunk_result(
            entity_name=entity_name,
            chunk_number=chunk.chunk_number,
            row_count=0,
            output_path=chunk_output_path,
            status=GenerationChunkStatus.FAILED,
            error=str(exc),
        )


def _restore_completed_chunks(
    *,
    entity_name: str,
    chunks: tuple[Any, ...],
    completed_chunks: set[int],
    output_directory: str | Path,
    identity_fields: tuple[str, ...],
    context: GenerationContext,
    existing_identities: set[tuple[Any, ...]],
    job: GenerationJob,
) -> None:
    """Restore checkpointed chunks into the in-memory generation state."""

    if not completed_chunks:
        return

    for chunk in chunks:
        if chunk.chunk_number not in completed_chunks:
            continue

        chunk_path = get_chunk_output_path(
            output_directory=output_directory,
            entity_name=entity_name,
            chunk_number=chunk.chunk_number,
        )

        if not chunk_path.exists():
            raise FileNotFoundError(
                "Checkpoint marks chunk as completed, but the committed "
                f"chunk file does not exist: {chunk_path}"
            )

        rows = read_rows(chunk_path)

        if len(rows) != chunk.row_count:
            raise ValueError(
                f"Committed chunk row count mismatch for "
                f"{entity_name} chunk {chunk.chunk_number}: "
                f"expected {chunk.row_count}, found {len(rows)}."
            )

        context.add_rows(
            entity_name,
            rows,
            identity_fields,
        )

        if identity_fields:
            for row in rows:
                identity = context.entities[
                    entity_name
                ].build_identity(
                    row,
                    identity_fields,
                )
                existing_identities.add(identity)

        job.entities[entity_name].generated_rows += len(rows)

        if (
            job.entities[entity_name].generated_rows
            >= job.entities[entity_name].target_rows
        ):
            job.entities[entity_name].status = (
                EntityGenerationStatus.COMPLETED
            )
        else:
            job.entities[entity_name].status = (
                EntityGenerationStatus.RUNNING
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
    checkpoint: GenerationCheckpoint,
    checkpoint_path: str,
    dependencies: tuple[Any, ...] = (),
    relationships: tuple[Any, ...] = (),
    relationship_groups: tuple[Any, ...] = (),
    constraints: tuple[Any, ...] = (),
    progress_reporter: CLIProgressReporter | None = None,
) -> bool:
    """Synchronously execute all chunks for one entity."""

    (
        entity,
        chunks,
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

    completed_chunks = set(
        checkpoint.entities[entity_name].completed_chunks
    )

    _restore_completed_chunks(
        entity_name=entity_name,
        chunks=chunks,
        completed_chunks=completed_chunks,
        output_directory=output_directory,
        identity_fields=identity_fields,
        context=context,
        existing_identities=existing_identities,
        job=job,
    )

    if progress_reporter is not None:
        progress_reporter.start_entity(
            entity_name=entity_name,
            target_rows=target_rows,
            total_chunks=len(chunks),
        )

    for chunk in chunks:
        if checkpoint.is_chunk_completed(
            entity_name=entity_name,
            chunk_number=chunk.chunk_number,
        ):
            continue

        result = _execute_chunk(
            entity=entity,
            chunk=chunk,
            seed=seed,
            output_directory=output_directory,
            identity_fields=identity_fields,
            semantic_values_by_field=semantic_values_by_field,
            dependencies=dependencies,
            relationships=relationships,
            relationship_groups=relationship_groups,
            constraints=constraints,
            context=context,
            existing_identities=existing_identities,
        )

        job.record_chunk_result(result)

        if result.status == GenerationChunkStatus.FAILED:
            if progress_reporter is not None:
                progress_reporter.fail_entity(
                    entity_name=entity_name,
                    error=result.error or "Chunk generation failed.",
                )
            return False

        checkpoint.mark_chunk_completed(
            entity_name=entity_name,
            chunk_number=result.chunk_number,
        )

        write_checkpoint(
            checkpoint=checkpoint,
            checkpoint_path=checkpoint_path,
        )

        if progress_reporter is not None:
            progress_reporter.update_chunk(
                chunk_number=result.chunk_number,
                generated_rows=job.entities[entity_name].generated_rows,
                total_generated_rows=job.total_generated_rows,
            )

    if progress_reporter is not None:
        progress_reporter.complete_entity(
            entity_name=entity_name,
            generated_rows=job.entities[entity_name].generated_rows,
        )

    return True


def execute_generation_plan(
    specification: dict[str, Any],
    job: GenerationJob,
    plan: GenerationPlan,
    seed: int,
    chunk_size: int,
    output_directory: str,
    checkpoint_path: str | None = None,
    progress_reporter: CLIProgressReporter | None = None,
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

        if checkpoint_path is None:
            checkpoint_path = str(
                Path(output_directory).parent
                / f"{job.job_id}_checkpoint.json"
            )

        checkpoint = _load_or_create_checkpoint(
            checkpoint_path=checkpoint_path,
            job=job,
            specification=specification,
            plan=plan,
            seed=seed,
            chunk_size=chunk_size,
        )

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
                checkpoint=checkpoint,
                checkpoint_path=checkpoint_path,
                dependencies=entity_plan.dependencies,
                relationships=plan.relationships,
                relationship_groups=plan.relationship_groups,
                constraints=plan.constraints,
                progress_reporter=progress_reporter,
            )

            if not entity_completed:
                job.fail(job.error or "Entity generation failed.")
                return job

        job.complete()

        if progress_reporter is not None:
            progress_reporter.finish()

    except Exception as exc:
        job.fail(str(exc))

        if progress_reporter is not None:
            progress_reporter.finish()

    return job
