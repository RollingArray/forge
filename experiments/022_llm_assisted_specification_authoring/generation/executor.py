"""
FORGE Generation Core
Synchronous generation execution.

This module coordinates planning, chunking, primitive generation,
and job progress updates.

It is UI-independent and intentionally contains no persistence
or asynchronous worker logic.
"""

from __future__ import annotations

from typing import Any

from .chunking import build_chunks
from .generator import generate_entity_chunk_result
from .job import GenerationJob, GenerationJobStatus
from .planner import GenerationPlan


def find_entity(
    specification: dict[str, Any],
    entity_name: str,
) -> dict[str, Any]:
    """Return an entity definition by name."""

    for entity in specification.get("entities", []):
        if entity.get("name") == entity_name:
            return entity

    raise ValueError(
        f"Entity {entity_name!r} was not found in the specification."
    )


def execute_entity(
    specification: dict[str, Any],
    job: GenerationJob,
    entity_name: str,
    target_rows: int,
    seed: int,
    chunk_size: int,
) -> None:
    """Synchronously execute all chunks for one entity."""

    entity = find_entity(
        specification,
        entity_name,
    )

    chunks = build_chunks(
        entity_name=entity_name,
        total_rows=target_rows,
        chunk_size=chunk_size,
    )

    for chunk in chunks:
        result = generate_entity_chunk_result(
            entity=entity,
            chunk_number=chunk.chunk_number,
            start_row=chunk.start_row,
            row_count=chunk.row_count,
            seed=seed,
        )

        job.record_chunk_result(result)

        if result.status.value == "FAILED":
            break


def execute_generation_plan(
    specification: dict[str, Any],
    job: GenerationJob,
    plan: GenerationPlan,
    seed: int,
    chunk_size: int,
) -> GenerationJob:
    """
    Execute a generation plan synchronously.

    This function coordinates existing generation contracts.
    It does not persist output or manage asynchronous execution.
    """

    job.start_planning()

    try:
        job.start_running()

        for entity_plan in plan.entities:
            execute_entity(
                specification=specification,
                job=job,
                entity_name=entity_plan.entity_name,
                target_rows=entity_plan.target_rows,
                seed=seed,
                chunk_size=chunk_size,
            )

            if job.status == GenerationJobStatus.FAILED:
                return job

        job.complete()

    except Exception as exc:
        job.fail(str(exc))

    return job
