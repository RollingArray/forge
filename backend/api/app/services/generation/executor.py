"""
File: executor.py
Purpose: Execute the production FORGE generation plan.
"""

from __future__ import annotations

from time import perf_counter
from typing import Any, Callable

from app.services.generation.context import GenerationContext
from app.services.generation.run import (
    GenerationEntityRun,
    GenerationRun,
)
from app.services.generation.entity_generator import EntityGenerator
from app.services.generation.artifact_writer import GenerationArtifactWriter
from app.services.generation_planner import GenerationPlan
from app.constants.generation import SEMANTIC_VOCABULARY_SIZE
from app.services.ai_service import AIService


class GenerationExecutionError(RuntimeError):
    """Raised when production generation execution fails."""


class GenerationExecutor:
    """Execute entities in dependency-safe production order."""

    def __init__(
        self,
        *,
        seed: int,
        ai_service: AIService | None = None,
    ) -> None:
        self._seed = seed
        self._ai_service = ai_service

    def execute(
        self,
        *,
        specification: dict[str, Any],
        plan: GenerationPlan,
        job_id: str,
        on_entity_completed: Callable[[GenerationEntityRun], None] | None = None,
        on_chunk_completed: Callable[[str, int, int, int, list[dict[str, Any]]], None] | None = None,
    ) -> GenerationRun:
        """Generate every entity in the supplied generation plan."""

        started_at = perf_counter()
        context = GenerationContext()
        entity_runs: list[GenerationEntityRun] = []

        artifact_writer = GenerationArtifactWriter()
        artifact_writer.initialize_job(job_id)

        entities_by_name = {
            entity["name"]: entity
            for entity in specification.get("entities", [])
        }

        foreign_keys_by_child: dict[
            str,
            list[dict[str, Any]],
        ] = {}

        for foreign_key in specification.get(
            "foreign_keys",
            [],
        ):
            child_entity = foreign_key["source"]["entity"]

            foreign_keys_by_child.setdefault(
                child_entity,
                [],
            ).append(
                {
                    "child_entity": child_entity,
                    "child_fields": foreign_key["source"]["fields"],
                    "parent_entity": foreign_key["target"]["entity"],
                    "parent_fields": foreign_key["target"]["fields"],
                }
            )

        total_entities = len(plan.generation_order)

        for index, entity_name in enumerate(
            plan.generation_order,
            start=1,
        ):
            entity = entities_by_name.get(entity_name)

            if entity is None:
                raise GenerationExecutionError(
                    f"Entity {entity_name!r} is missing "
                    "from the specification."
                )

            target_rows = (
                entity.get("population") or {}
            ).get("count", 0)

            print(
                f"[{index:02d}/{total_entities:02d}] "
                f"Generating {entity_name:<20} "
                f"{target_rows:>8,} rows...",
                flush=True,
            )

            if self._ai_service is not None:
                for field in entity.get("fields", []):
                    generation = field.get("generation") or {}

                    if generation.get("generator") != "SEMANTIC":
                        continue

                    parameters = generation.get("parameters") or {}
                    description = parameters.get("description")
                    mode = parameters.get("mode")

                    if not isinstance(description, str) or not description.strip():
                        raise GenerationExecutionError(
                            f"Semantic field {entity_name}.{field['name']} "
                            "is missing a valid description."
                        )

                    if not isinstance(mode, str) or not mode.strip():
                        raise GenerationExecutionError(
                            f"Semantic field {entity_name}.{field['name']} "
                            "is missing a valid mode."
                        )

                    normalized_mode = mode.strip().upper()

                    if normalized_mode == "UNIQUE":
                        requested_count = target_rows
                    elif normalized_mode == "VOCABULARY":
                        requested_count = SEMANTIC_VOCABULARY_SIZE
                    else:
                        raise GenerationExecutionError(
                            f"Unsupported semantic generation mode "
                            f"{mode!r} for "
                            f"{entity_name}.{field['name']}."
                        )

                    semantic_values = self._ai_service.generate_semantic_values(
                        description=description,
                        mode=normalized_mode,
                        count=requested_count,
                    )

                    if len(semantic_values) != requested_count:
                        raise GenerationExecutionError(
                            f"Semantic generation for "
                            f"{entity_name}.{field['name']} returned "
                            f"{len(semantic_values)} values; "
                            f"expected {requested_count}."
                        )

                    context.add_semantic_values(
                        entity_name=entity_name,
                        field_name=field["name"],
                        values=semantic_values,
                    )

            generator = EntityGenerator(
                seed=self._seed,
            )

            def handle_chunk_completed(
                completed_entity_name: str,
                chunk_number: int,
                total_chunks: int,
                generated_rows: int,
                chunk_rows: list[dict[str, Any]],
            ) -> None:
                artifact_writer.write_chunk(
                    job_id=job_id,
                    entity_name=completed_entity_name,
                    chunk_number=chunk_number,
                    rows=chunk_rows,
                )

                if on_chunk_completed is not None:
                    on_chunk_completed(
                        completed_entity_name,
                        chunk_number,
                        total_chunks,
                        generated_rows,
                        chunk_rows,
                    )

            try:
                generated_rows = generator.generate(
                    entity=entity,
                    foreign_keys=foreign_keys_by_child.get(
                        entity_name,
                        [],
                    ),
                    context=context,
                    on_chunk_completed=handle_chunk_completed,
                )
            except Exception as exc:
                print(
                    f"[{index:02d}/{total_entities:02d}] "
                    f"{entity_name:<20} FAILED: {exc}",
                    flush=True,
                )
                raise

            artifact_writer.consolidate_entity(
                job_id=job_id,
                entity_name=entity_name,
            )

            print(
                f"[{index:02d}/{total_entities:02d}] "
                f"{entity_name:<20} "
                f"OK ({generated_rows:,} rows)",
                flush=True,
            )

            entity_run = GenerationEntityRun(
                entity_name=entity_name,
                target_rows=target_rows,
                generated_rows=generated_rows,
            )

            entity_runs.append(entity_run)

            if on_entity_completed is not None:
                on_entity_completed(entity_run)

        elapsed_seconds = perf_counter() - started_at

        return GenerationRun(
            context=context,
            elapsed_seconds=elapsed_seconds,
            entities=tuple(entity_runs),
        )
