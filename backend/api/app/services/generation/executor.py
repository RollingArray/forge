"""
File: executor.py
Purpose: Execute the production FORGE generation plan.
"""

from __future__ import annotations

from time import perf_counter
from typing import Any, Callable

import psutil

from app.models.generation_model import GenerationSemanticCallProgress
from app.models.generation_log_model import GenerationLogEntry
from app.services.generation.context import GenerationContext
from app.services.generation.run import (
    GenerationChunkRun,
    GenerationEntityRun,
    GenerationRun,
)
from app.services.generation.entity_generator import EntityGenerator
from app.services.generation.artifact_writer import GenerationArtifactWriter
from app.services.generation_planner import GenerationPlan
from app.constants.generation import SEMANTIC_VOCABULARY_SIZE
from app.services.ai_service import AIService
from app.services.generation_semantic_store import GenerationSemanticStore
from app.services.generation_checkpoint_store import GenerationCheckpointStore
from app.services.generation_event_broker import GenerationEventBroker
from app.services.generation_log_store import GenerationLogStore
from app.services.generation.artifact_reader import GenerationArtifactReader
from app.services.generation.value_conversion import convert_value


class GenerationExecutionError(RuntimeError):
    """Raised when production generation execution fails."""


class GenerationExecutor:
    """Execute entities in dependency-safe production order."""

    def __init__(
        self,
        *,
        seed: int,
        ai_service: AIService | None = None,
        semantic_store: GenerationSemanticStore | None = None,
        checkpoint_store: GenerationCheckpointStore | None = None,
        event_broker: GenerationEventBroker | None = None,
        generation_log_store: GenerationLogStore | None = None,
        artifact_reader: GenerationArtifactReader | None = None,
        artifact_writer: GenerationArtifactWriter | None = None,
    ) -> None:
        self._seed = seed
        self._ai_service = ai_service
        self._semantic_store = (
            semantic_store if semantic_store is not None else GenerationSemanticStore()
        )
        self._checkpoint_store = (
            checkpoint_store
            if checkpoint_store is not None
            else GenerationCheckpointStore()
        )
        self._event_broker = event_broker
        self._generation_log_store = (
            generation_log_store
            if generation_log_store is not None
            else GenerationLogStore()
        )
        self._artifact_reader = (
            artifact_reader
            if artifact_reader is not None
            else GenerationArtifactReader()
        )
        self._artifact_writer = (
            artifact_writer
            if artifact_writer is not None
            else GenerationArtifactWriter()
        )

    def has_existing_checkpoint(
        self,
        data_model_id: str,
        job_id: str,
    ) -> bool:
        """Return whether durable execution state already exists."""
        return self._checkpoint_store.get(data_model_id=data_model_id, job_id=job_id) is not None

    def _get_start_chunk(
        self,
        *,
        data_model_id: str,
        job_id: str,
        entity_name: str,
    ) -> int:
        checkpoint = self._checkpoint_store.get(data_model_id=data_model_id, job_id=job_id)

        if checkpoint is None:
            return 1

        entity_state = checkpoint.get("entities", {}).get(entity_name, {})

        committed_chunks = entity_state.get(
            "committed_chunks",
            [],
        )

        if not committed_chunks:
            return 1

        committed_chunk_set = {int(chunk) for chunk in committed_chunks}

        next_chunk = 1

        while next_chunk in committed_chunk_set:
            next_chunk += 1

        return next_chunk

    def _get_committed_rows(
        self,
        *,
        data_model_id: str,
        job_id: str,
        entity_name: str,
    ) -> int:
        checkpoint = self._checkpoint_store.get(data_model_id=data_model_id, job_id=job_id)

        if checkpoint is None:
            return 0

        entity_state = checkpoint.get("entities", {}).get(entity_name, {})

        committed_rows = entity_state.get(
            "committed_rows",
            0,
        )

        if not isinstance(committed_rows, int):
            return 0

        return max(committed_rows, 0)

    def _get_durable_generated_rows(
        self,
        *,
        data_model_id: str,
        job_id: str,
        entity_name: str,
        generated_rows: int,
    ) -> int:
        committed_rows = self._get_committed_rows(
            data_model_id=data_model_id,
            job_id=job_id,
            entity_name=entity_name,
        )

        return committed_rows + max(generated_rows, 0)

    def _is_entity_fully_committed(
        self,
        *,
        data_model_id: str,
        job_id: str,
        entity_name: str,
        total_chunks: int,
    ) -> bool:
        if total_chunks <= 0:
            return True

        checkpoint = self._checkpoint_store.get(data_model_id=data_model_id, job_id=job_id)

        if checkpoint is None:
            return False

        entity_state = checkpoint.get("entities", {}).get(entity_name, {})

        committed_chunks = entity_state.get(
            "committed_chunks",
            [],
        )

        committed_chunk_set = {int(chunk) for chunk in committed_chunks}

        return all(
            chunk_number in committed_chunk_set
            for chunk_number in range(1, total_chunks + 1)
        )

    def _restore_entity_key_space(
        self,
        *,
        data_model_id: str,
        job_id: str,
        entity_name: str,
        identity_fields: tuple[str, ...],
        field_types: dict[str, Any],
        context: GenerationContext,
    ) -> None:
        if not identity_fields:
            return

        key_space = self._artifact_reader.get_entity_key_space(
            data_model_id=data_model_id,
            job_id=job_id,
            entity_name=entity_name,
            identity_fields=identity_fields,
        )

        if not key_space:
            return

        typed_key_space = {
            tuple(
                convert_value(
                    value,
                    field_types.get(field_name),
                )
                for field_name, value in zip(
                    identity_fields,
                    key,
                )
            )
            for key in key_space
        }

        context.restore_key_space(
            entity_name=entity_name,
            identity_fields=identity_fields,
            key_space=typed_key_space,
        )

    def execute(
        self,
        *,
        specification: dict[str, Any],
        plan: GenerationPlan,
        data_model_id: str,
        job_id: str,
        on_entity_completed: Callable[[GenerationEntityRun], None] | None = None,
        on_chunk_completed: (
            Callable[
                [
                    str,
                    int,
                    int,
                    int,
                    list[dict[str, Any]],
                    float,
                    float,
                    list[dict[str, Any]],
                    list[dict[str, object]],
                ],
                None,
            ]
            | None
        ) = None,
    ) -> GenerationRun:
        """Generate every entity in the supplied generation plan."""

        started_at = perf_counter()
        context = GenerationContext()
        entity_runs: list[GenerationEntityRun] = []

        self._artifact_writer.initialize_job(data_model_id, job_id)

        entities_by_name = {
            entity["name"]: entity for entity in specification.get("entities", [])
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
                    f"Entity {entity_name!r} is missing " "from the specification."
                )

            target_rows = (entity.get("population") or {}).get("count", 0)

            total_chunks = (target_rows + 50 - 1) // 50 if target_rows > 0 else 0

            if self._is_entity_fully_committed(
                data_model_id=data_model_id,
                job_id=job_id,
                entity_name=entity_name,
                total_chunks=total_chunks,
            ):
                identity_fields = tuple(
                    (entity.get("identity") or {}).get(
                        "fields",
                        [],
                    )
                )

                field_types = {
                    field["name"]: field.get("type")
                    for field in entity.get("fields", [])
                }

                self._restore_entity_key_space(
                    data_model_id=data_model_id,
                    job_id=job_id,
                    entity_name=entity_name,
                    identity_fields=identity_fields,
                    field_types=field_types,
                    context=context,
                )

                print(
                    f"[{index:02d}/{total_entities:02d}] "
                    f"{entity_name:<20} "
                    f"SKIPPED ({target_rows:,} rows already committed)",
                    flush=True,
                )

                entity_run = GenerationEntityRun(
                    entity_name=entity_name,
                    target_rows=target_rows,
                    generated_rows=target_rows,
                )

                entity_runs.append(entity_run)

                if on_entity_completed is not None:
                    on_entity_completed(entity_run)

                continue

            activity = self._generation_log_store.append(
                data_model_id=data_model_id,
                job_id=job_id,
                entry=GenerationLogEntry(
                    sequence=0,
                    entity_name=entity_name,
                    stage="ENTITY_GENERATION",
                    status="STARTED",
                ),
            )

            if self._event_broker is not None:
                self._event_broker.publish(
                    data_model_id=data_model_id,
                    job_id=job_id,
                    event_type="GENERATION_ACTIVITY",
                    data=activity.model_dump(
                        mode="json",
                        exclude_none=True,
                    ),
                )

            entity_started_at = perf_counter()
            process = psutil.Process()
            entity_peak_memory_bytes = process.memory_info().rss
            chunk_runs: list[GenerationChunkRun] = []
            chunk_started_at: dict[int, float] = {}
            chunk_peak_memory_bytes: dict[int, int] = {}
            entity_semantic_calls: list[dict[str, object]] = []
            chunk_semantic_calls: dict[
                int,
                list[dict[str, object]],
            ] = {}

            print(
                f"[{index:02d}/{total_entities:02d}] "
                f"Generating {entity_name:<20} "
                f"{target_rows:>8,} rows...",
                flush=True,
            )

            start_chunk = self._get_start_chunk(
                data_model_id=data_model_id,
                job_id=job_id,
                entity_name=entity_name,
            )

            is_resuming = start_chunk > 1

            # VOCABULARY semantic values are prepared once per entity.
            # UNIQUE values are prepared per generation chunk below.
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
                    continue

                if normalized_mode != "VOCABULARY":
                    raise GenerationExecutionError(
                        f"Unsupported semantic generation mode "
                        f"{mode!r} for "
                        f"{entity_name}.{field['name']}."
                    )

                persisted = self._semantic_store.get(
                    data_model_id=data_model_id,
                    job_id=job_id,
                    entity_name=entity_name,
                    field_name=field["name"],
                )

                if persisted is not None:
                    semantic_values = persisted.get("values", [])

                    if (
                        persisted.get("mode") != normalized_mode
                        or len(semantic_values) != SEMANTIC_VOCABULARY_SIZE
                    ):
                        raise GenerationExecutionError(
                            f"Persisted semantic state is invalid for "
                            f"{entity_name}.{field['name']}."
                        )
                else:
                    if self._ai_service is None:
                        raise GenerationExecutionError(
                            f"Semantic generation requires an AI service "
                            f"for {entity_name}.{field['name']}."
                        )

                    def record_entity_semantic_call(
                        requested_count: int,
                        returned_count: int,
                        elapsed_seconds: float,
                        refill: bool,
                    ) -> None:
                        entity_semantic_calls.append(
                            {
                                "field": field["name"],
                                "call_number": len(entity_semantic_calls) + 1,
                                "requested_count": requested_count,
                                "returned_count": returned_count,
                                "elapsed_seconds": elapsed_seconds,
                                "refill": refill,
                            }
                        )

                    semantic_values = self._ai_service.generate_semantic_values(
                        description=description,
                        mode=normalized_mode,
                        count=SEMANTIC_VOCABULARY_SIZE,
                        on_call_completed=record_entity_semantic_call,
                    )

                    if len(semantic_values) != SEMANTIC_VOCABULARY_SIZE:
                        raise GenerationExecutionError(
                            f"Semantic generation for "
                            f"{entity_name}.{field['name']} returned "
                            f"{len(semantic_values)} values; "
                            f"expected {SEMANTIC_VOCABULARY_SIZE}."
                        )

                    self._semantic_store.save(
                        data_model_id=data_model_id,
                        job_id=job_id,
                        entity_name=entity_name,
                        field_name=field["name"],
                        mode=normalized_mode,
                        values=semantic_values,
                    )

                context.add_semantic_values(
                    entity_name=entity_name,
                    field_name=field["name"],
                    values=semantic_values,
                )

            if is_resuming:
                identity_fields = tuple(
                    (entity.get("identity") or {}).get(
                        "fields",
                        [],
                    )
                )

                field_types = {
                    field["name"]: field.get("type")
                    for field in entity.get("fields", [])
                }

                self._restore_entity_key_space(
                    data_model_id=data_model_id,
                    job_id=job_id,
                    entity_name=entity_name,
                    identity_fields=identity_fields,
                    field_types=field_types,
                    context=context,
                )

            generator = EntityGenerator(
                seed=self._seed,
            )

            def handle_chunk_start(
                completed_entity_name: str,
                chunk_number: int,
                chunk_start: int,
                chunk_end: int,
            ) -> None:
                chunk_started_at[chunk_number] = perf_counter()
                chunk_peak_memory_bytes[chunk_number] = process.memory_info().rss
                chunk_semantic_calls[chunk_number] = []

                activity = self._generation_log_store.append(
                    data_model_id=data_model_id,
                    job_id=job_id,
                    entry=GenerationLogEntry(
                        sequence=0,
                        entity_name=entity_name,
                        stage="CHUNK_GENERATION",
                        status="STARTED",
                        chunk_number=chunk_number,
                    ),
                )

                if self._event_broker is not None:
                    self._event_broker.publish(
                        data_model_id=data_model_id,
                        job_id=job_id,
                        event_type="GENERATION_ACTIVITY",
                        data=activity.model_dump(
                            mode="json",
                            exclude_none=True,
                        ),
                    )

                for field in entity.get("fields", []):
                    generation = field.get("generation") or {}

                    if generation.get("generator") != "SEMANTIC":
                        continue

                    parameters = generation.get("parameters") or {}
                    mode = str(parameters.get("mode", "")).strip().upper()

                    if mode != "UNIQUE":
                        continue

                    field_name = field["name"]
                    description = parameters.get("description")

                    if not isinstance(description, str) or not description.strip():
                        raise GenerationExecutionError(
                            f"Semantic field {entity_name}.{field_name} "
                            "is missing a valid description."
                        )

                    required_end = chunk_end
                    persisted = self._semantic_store.get(
                        data_model_id=data_model_id,
                        job_id=job_id,
                        entity_name=entity_name,
                        field_name=field_name,
                    )

                    persisted_values = (
                        persisted.get("values", []) if persisted is not None else []
                    )

                    if persisted is not None and persisted.get("mode") != "UNIQUE":
                        raise GenerationExecutionError(
                            f"Persisted semantic state is invalid for "
                            f"{entity_name}.{field_name}."
                        )

                    if len(persisted_values) < required_end:
                        missing_count = required_end - len(persisted_values)

                        if self._ai_service is None:
                            raise GenerationExecutionError(
                                f"Semantic generation requires an AI service "
                                f"for {entity_name}.{field_name}."
                            )

                        semantic_call_number = 0

                        def record_semantic_call(
                            requested_count: int,
                            returned_count: int,
                            elapsed_seconds: float,
                            refill: bool,
                        ) -> None:
                            nonlocal semantic_call_number

                            semantic_call_number += 1

                            print(
                                f"[SEMANTIC-CALL] "
                                f"{entity_name}.{field_name} "
                                f"chunk={chunk_number} "
                                f"call={semantic_call_number} "
                                f"requested={requested_count} "
                                f"returned={returned_count} "
                                f"elapsed={elapsed_seconds:.3f}s "
                                f"refill={refill}",
                                flush=True,
                            )

                            chunk_semantic_calls[chunk_number].append(
                                {
                                    "field": field_name,
                                    "call_number": semantic_call_number,
                                    "requested_count": requested_count,
                                    "returned_count": returned_count,
                                    "elapsed_seconds": elapsed_seconds,
                                    "refill": refill,
                                }
                            )

                        if self._event_broker is not None:
                            self._event_broker.publish(
                                data_model_id=data_model_id,
                                job_id=job_id,
                                event_type="SEMANTIC_CALL_STARTED",
                                data={
                                    "entity_name": entity_name,
                                    "field_name": field_name,
                                    "chunk_number": chunk_number,
                                    "call_number": semantic_call_number + 1,
                                    "requested_count": missing_count,
                                },
                            )

                        semantic_activity = self._generation_log_store.append(
                            data_model_id=data_model_id,
                            job_id=job_id,
                            entry=GenerationLogEntry(
                                sequence=0,
                                entity_name=entity_name,
                                stage="SEMANTIC_GENERATION",
                                status="STARTED",
                                field_name=field_name,
                                chunk_number=chunk_number,
                                requested_count=missing_count,
                            ),
                        )

                        if self._event_broker is not None:
                            self._event_broker.publish(
                                data_model_id=data_model_id,
                                job_id=job_id,
                                event_type="GENERATION_ACTIVITY",
                                data=semantic_activity.model_dump(
                                    mode="json",
                                    exclude_none=True,
                                ),
                            )

                        semantic_started_at = perf_counter()

                        semantic_batch = self._ai_service.generate_semantic_values(
                            description=description,
                            mode="UNIQUE",
                            count=missing_count,
                            on_call_completed=record_semantic_call,
                        )

                        semantic_elapsed_seconds = perf_counter() - semantic_started_at

                        print(
                            f"[SEMANTIC] "
                            f"{entity_name}.{field_name} "
                            f"chunk={chunk_number} "
                            f"requested={missing_count} "
                            f"returned={len(semantic_batch)} "
                            f"time={semantic_elapsed_seconds:.3f}s",
                            flush=True,
                        )

                        if len(semantic_batch) != missing_count:
                            raise GenerationExecutionError(
                                f"Semantic generation for "
                                f"{entity_name}.{field_name} returned "
                                f"{len(semantic_batch)} values; "
                                f"expected {missing_count}."
                            )

                        semantic_activity = self._generation_log_store.append(
                            data_model_id=data_model_id,
                            job_id=job_id,
                            entry=GenerationLogEntry(
                                sequence=0,
                                entity_name=entity_name,
                                stage="SEMANTIC_GENERATION",
                                status="COMPLETED",
                                field_name=field_name,
                                chunk_number=chunk_number,
                                requested_count=missing_count,
                                elapsed_seconds=semantic_elapsed_seconds,
                            ),
                        )

                        if self._event_broker is not None:
                            self._event_broker.publish(
                                data_model_id=data_model_id,
                                job_id=job_id,
                                event_type="GENERATION_ACTIVITY",
                                data=semantic_activity.model_dump(
                                    mode="json",
                                    exclude_none=True,
                                ),
                            )

                        self._semantic_store.append_unique(
                            data_model_id=data_model_id,
                            job_id=job_id,
                            entity_name=entity_name,
                            field_name=field_name,
                            values=semantic_batch,
                        )

                        persisted_values = [
                            *persisted_values,
                            *semantic_batch,
                        ]

                    chunk_values = persisted_values[chunk_start:chunk_end]

                    if len(chunk_values) != chunk_end - chunk_start:
                        raise GenerationExecutionError(
                            f"Semantic state is incomplete for "
                            f"{entity_name}.{field_name}."
                        )

                    context.add_semantic_values(
                        entity_name=entity_name,
                        field_name=field_name,
                        values=chunk_values,
                        chunk_number=chunk_number,
                    )

            def handle_field_activity(
                completed_entity_name: str,
                chunk_number: int,
                field_name: str,
                status: str,
            ) -> None:
                activity = self._generation_log_store.append(
                    data_model_id=data_model_id,
                    job_id=job_id,
                    entry=GenerationLogEntry(
                        sequence=0,
                        entity_name=completed_entity_name,
                        stage="FIELD_GENERATION",
                        status=status,
                        field_name=field_name,
                        chunk_number=chunk_number,
                    ),
                )

                if self._event_broker is not None:
                    self._event_broker.publish(
                        data_model_id=data_model_id,
                        job_id=job_id,
                        event_type="GENERATION_ACTIVITY",
                        data=activity.model_dump(
                            mode="json",
                            exclude_none=True,
                        ),
                    )

            def handle_chunk_completed(
                completed_entity_name: str,
                chunk_number: int,
                total_chunks: int,
                generated_rows: int,
                chunk_rows: list[dict[str, Any]],
            ) -> None:
                self._artifact_writer.write_chunk(
                    data_model_id=data_model_id,
                    job_id=job_id,
                    entity_name=completed_entity_name,
                    chunk_number=chunk_number,
                    rows=chunk_rows,
                )

                chunk_peak_memory_bytes[chunk_number] = max(
                    chunk_peak_memory_bytes.get(
                        chunk_number,
                        process.memory_info().rss,
                    ),
                    process.memory_info().rss,
                )

                chunk_elapsed_seconds = perf_counter() - chunk_started_at.get(
                    chunk_number,
                    perf_counter(),
                )

                chunk_runs.append(
                    GenerationChunkRun(
                        chunk_number=chunk_number,
                        target_rows=len(chunk_rows),
                        generated_rows=len(chunk_rows),
                        elapsed_seconds=chunk_elapsed_seconds,
                        peak_memory_mb=(
                            chunk_peak_memory_bytes[chunk_number] / (1024 * 1024)
                        ),
                        unique_semantic_calls=tuple(
                            chunk_semantic_calls.get(
                                chunk_number,
                                [],
                            )
                        ),
                    )
                )

                if on_chunk_completed is not None:
                    on_chunk_completed(
                        completed_entity_name,
                        chunk_number,
                        total_chunks,
                        generated_rows,
                        chunk_rows,
                        chunk_elapsed_seconds,
                        (chunk_peak_memory_bytes[chunk_number] / (1024 * 1024)),
                        list(
                            chunk_semantic_calls.get(
                                chunk_number,
                                [],
                            )
                        ),
                        list(entity_semantic_calls),
                    )

            try:
                generated_rows = generator.generate(
                    entity=entity,
                    foreign_keys=foreign_keys_by_child.get(
                        entity_name,
                        [],
                    ),
                    context=context,
                    start_chunk=start_chunk,
                    on_chunk_start=handle_chunk_start,
                    on_chunk_completed=handle_chunk_completed,
                    on_field_activity=handle_field_activity,
                )
            except Exception as exc:
                print(
                    f"[{index:02d}/{total_entities:02d}] "
                    f"{entity_name:<20} FAILED: {exc}",
                    flush=True,
                )
                raise

            self._artifact_writer.consolidate_entity(
                data_model_id=data_model_id,
                job_id=job_id,
                entity_name=entity_name,
            )

            entity_peak_memory_bytes = max(
                entity_peak_memory_bytes,
                process.memory_info().rss,
            )
            entity_elapsed_seconds = perf_counter() - entity_started_at

            print(
                f"[{index:02d}/{total_entities:02d}] "
                f"{entity_name:<20} "
                f"OK ({generated_rows:,} rows)",
                flush=True,
            )

            durable_generated_rows = (
                self._get_durable_generated_rows(
                    data_model_id=data_model_id,
                    job_id=job_id,
                    entity_name=entity_name,
                    generated_rows=generated_rows,
                )
                if is_resuming
                else generated_rows
            )

            entity_run = GenerationEntityRun(
                entity_name=entity_name,
                target_rows=target_rows,
                generated_rows=durable_generated_rows,
                elapsed_seconds=entity_elapsed_seconds,
                peak_memory_mb=(entity_peak_memory_bytes / (1024 * 1024)),
                vocabulary_semantic_calls=tuple(
                    GenerationSemanticCallProgress.model_validate(call)
                    for call in entity_semantic_calls
                ),
                chunks=tuple(chunk_runs),
            )

            activity = self._generation_log_store.append(
                data_model_id=data_model_id,
                job_id=job_id,
                entry=GenerationLogEntry(
                    sequence=0,
                    entity_name=entity_name,
                    stage="ENTITY_GENERATION",
                    status="COMPLETED",
                    generated_rows=durable_generated_rows,
                    elapsed_seconds=entity_elapsed_seconds,
                    throughput_rows_per_second=(
                        durable_generated_rows / entity_elapsed_seconds
                        if entity_elapsed_seconds > 0
                        else None
                    ),
                    peak_memory_mb=(
                        entity_peak_memory_bytes / (1024 * 1024)
                    ),
                ),
            )

            if self._event_broker is not None:
                self._event_broker.publish(
                    data_model_id=data_model_id,
                    job_id=job_id,
                    event_type="GENERATION_ACTIVITY",
                    data=activity.model_dump(
                        mode="json",
                        exclude_none=True,
                    ),
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
