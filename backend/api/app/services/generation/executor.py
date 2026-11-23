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
            else GenerationArtifactReader(
                checkpoint_store=self._checkpoint_store,
            )
        )
        self._artifact_writer = (
            artifact_writer
            if artifact_writer is not None
            else GenerationArtifactWriter(
                checkpoint_store=self._checkpoint_store,
            )
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
        """Return the first chunk after the contiguous committed prefix.

        Retained for compatibility with callers that require a contiguous
        starting point. Sparse recovery must use _get_missing_chunks().
        """
        checkpoint = self._checkpoint_store.get(
            data_model_id=data_model_id,
            job_id=job_id,
        )

        if checkpoint is None:
            return 1

        entity_state = checkpoint.entities.get(entity_name)
        if entity_state is None:
            return 1

        committed = {
            chunk.chunk_number
            for chunk in entity_state.chunks
        }

        next_chunk = 1
        while next_chunk in committed:
            next_chunk += 1

        return next_chunk

    def _get_missing_chunks(
        self,
        *,
        data_model_id: str,
        job_id: str,
        entity_name: str,
        total_chunks: int,
    ) -> list[int]:
        """Return every uncommitted chunk in original generation order."""
        checkpoint = self._checkpoint_store.get(
            data_model_id=data_model_id,
            job_id=job_id,
        )

        if checkpoint is None:
            raise GenerationExecutionError(
                f"Generation checkpoint is missing for job: {job_id}"
            )

        entity_state = checkpoint.entities.get(entity_name)
        if entity_state is None:
            raise GenerationExecutionError(
                f"Entity {entity_name!r} is missing from the checkpoint."
            )

        committed = {
            chunk.chunk_number
            for chunk in entity_state.chunks
        }

        return [
            chunk_number
            for chunk_number in range(1, total_chunks + 1)
            if chunk_number not in committed
        ]



    def _get_committed_rows(
        self,
        *,
        data_model_id: str,
        job_id: str,
        entity_name: str,
    ) -> int:
        """Return the authoritative committed row count from the v2 manifest."""
        return self._checkpoint_store.get_committed_rows(
            data_model_id=data_model_id,
            job_id=job_id,
            entity_name=entity_name,
        )


    def _get_durable_generated_rows(
        self,
        *,
        data_model_id: str,
        job_id: str,
        entity_name: str,
    ) -> int:
        # Chunk callbacks have already persisted the current committed total.
        # Adding this invocation's generated_rows would count those rows twice.
        return self._get_committed_rows(
            data_model_id=data_model_id,
            job_id=job_id,
            entity_name=entity_name,
        )


    def _is_entity_fully_committed(
        self,
        *,
        data_model_id: str,
        job_id: str,
        entity_name: str,
        total_chunks: int,
    ) -> bool:
        """Completion requires committed chunks and committed final output."""
        from app.models.generation_persistence import (
            GenerationFinalizationStatus,
        )

        checkpoint = self._checkpoint_store.get(
            data_model_id=data_model_id,
            job_id=job_id,
        )

        if checkpoint is None:
            return False

        entity_state = checkpoint.entities.get(entity_name)
        if entity_state is None:
            return False

        return (
            entity_state.committed_rows == entity_state.target_rows
            and entity_state.finalization.status
            == GenerationFinalizationStatus.COMMITTED
            and entity_state.finalization.output is not None
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
        """Restore committed identity keys without losing global row positions."""
        if not identity_fields:
            return

        indexed_key_space = self._artifact_reader.get_identity_keys_by_row(
            data_model_id=data_model_id,
            job_id=job_id,
            entity_name=entity_name,
            identity_fields=identity_fields,
        )

        if not indexed_key_space:
            return

        typed_key_space = {
            row_index: tuple(
                convert_value(
                    value,
                    field_types.get(field_name),
                )
                for field_name, value in zip(
                    identity_fields,
                    key,
                    strict=True,
                )
            )
            for row_index, key in indexed_key_space.items()
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

        checkpoint = self._checkpoint_store.get(
            data_model_id=data_model_id,
            job_id=job_id,
        )
        if checkpoint is None:
            raise GenerationExecutionError(
                f"Generation checkpoint is missing for job: {job_id}"
            )

        chunk_size = checkpoint.chunk_size
        if (
            not isinstance(chunk_size, int)
            or isinstance(chunk_size, bool)
            or chunk_size <= 0
        ):
            raise GenerationExecutionError(
                f"Invalid generation checkpoint chunk size: {chunk_size!r}"
            )

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

            total_chunks = (
                (target_rows + chunk_size - 1) // chunk_size
                if target_rows > 0
                else 0
            )

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

            missing_chunk_numbers = self._get_missing_chunks(
                data_model_id=data_model_id,
                job_id=job_id,
                entity_name=entity_name,
                total_chunks=total_chunks,
            )

            entity_checkpoint = checkpoint.entities.get(entity_name)
            if entity_checkpoint is None:
                raise GenerationExecutionError(
                    f"Entity {entity_name!r} is missing from the checkpoint."
                )

            is_resuming = bool(entity_checkpoint.chunks)

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

                    self._semantic_store.save_vocabulary(
                        data_model_id=data_model_id,
                        job_id=job_id,
                        entity_name=entity_name,
                        field_name=field["name"],
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
                    persist=False,
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

                    # Reconcile semantic assignments with every committed
                    # artifact using original global row positions.
                    values_by_row = self._semantic_store.get_unique_values(
                        data_model_id=data_model_id,
                        job_id=job_id,
                        entity_name=entity_name,
                        field_name=field_name,
                    )

                    if not isinstance(values_by_row, dict):
                        raise GenerationExecutionError(
                            f"Invalid UNIQUE semantic state for "
                            f"{entity_name}.{field_name}."
                        )

                    values_by_row = dict(values_by_row)

                    if any(
                        isinstance(row_index, bool)
                        or not isinstance(row_index, int)
                        or row_index < 0
                        or row_index >= target_rows
                        for row_index in values_by_row
                    ):
                        raise GenerationExecutionError(
                            f"UNIQUE semantic state contains an invalid row "
                            f"position for {entity_name}.{field_name}."
                        )

                    # Committed artifacts are authoritative for rows already
                    # published. Recover missing semantic assignments, but
                    # never silently overwrite a conflicting assignment.
                    recovered_values: dict[int, str] = {}

                    try:
                        for row_index, row in self._artifact_reader.iter_entity_rows(
                            data_model_id=data_model_id,
                            job_id=job_id,
                            entity_name=entity_name,
                        ):
                            if field_name not in row:
                                raise GenerationExecutionError(
                                    f"Committed artifact is missing "
                                    f"{entity_name}.{field_name}."
                                )

                            value = row[field_name]

                            if not isinstance(value, str) or not value.strip():
                                raise GenerationExecutionError(
                                    f"Committed artifact contains a blank or "
                                    f"invalid UNIQUE value for "
                                    f"{entity_name}.{field_name} at row "
                                    f"{row_index}."
                                )

                            existing_value = values_by_row.get(row_index)

                            if (
                                existing_value is not None
                                and existing_value != value
                            ):
                                raise GenerationExecutionError(
                                    f"Semantic store conflicts with committed "
                                    f"artifact for {entity_name}.{field_name} "
                                    f"at row {row_index}."
                                )

                            if existing_value is None:
                                recovered_values[row_index] = value

                    except GenerationExecutionError:
                        raise
                    except Exception as exc:
                        raise GenerationExecutionError(
                            f"Could not reconcile UNIQUE semantic state for "
                            f"{entity_name}.{field_name}: {exc}"
                        ) from exc

                    if recovered_values:
                        try:
                            self._semantic_store.commit_unique_values(
                                data_model_id=data_model_id,
                                job_id=job_id,
                                entity_name=entity_name,
                                field_name=field_name,
                                values_by_row=recovered_values,
                            )
                        except Exception as exc:
                            raise GenerationExecutionError(
                                f"Could not recover UNIQUE semantic values for "
                                f"{entity_name}.{field_name}: {exc}"
                            ) from exc

                        values_by_row.update(recovered_values)

                    # Only request values for unassigned positions in this
                    # chunk. Existing assignments elsewhere remain reserved.
                    missing_row_indices = [
                        row_index
                        for row_index in range(chunk_start, chunk_end)
                        if row_index not in values_by_row
                    ]

                    if missing_row_indices:
                        if self._ai_service is None:
                            raise GenerationExecutionError(
                                f"Semantic generation requires an AI service "
                                f"for {entity_name}.{field_name}."
                            )

                        missing_count = len(missing_row_indices)
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
                                    "call_number": 1,
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
                            exclude_values=list(values_by_row.values()),
                            on_call_completed=record_semantic_call,
                        )

                        semantic_elapsed_seconds = (
                            perf_counter() - semantic_started_at
                        )

                        if (
                            not isinstance(semantic_batch, list)
                            or len(semantic_batch) != missing_count
                            or any(
                                not isinstance(value, str) or not value.strip()
                                for value in semantic_batch
                            )
                        ):
                            raise GenerationExecutionError(
                                f"Semantic generation for "
                                f"{entity_name}.{field_name} returned an "
                                f"invalid batch; expected {missing_count} "
                                "non-empty string values."
                            )

                        normalized_existing = {
                            value.strip().casefold()
                            for value in values_by_row.values()
                        }
                        normalized_batch = [
                            value.strip().casefold()
                            for value in semantic_batch
                        ]

                        if (
                            len(set(normalized_batch)) != missing_count
                            or normalized_existing.intersection(normalized_batch)
                        ):
                            raise GenerationExecutionError(
                                f"Semantic generation for "
                                f"{entity_name}.{field_name} returned "
                                "duplicate or previously assigned UNIQUE values."
                            )

                        new_assignments = dict(
                            zip(
                                missing_row_indices,
                                semantic_batch,
                                strict=True,
                            )
                        )

                        # Persist assignments before row generation. A crash
                        # after this point can safely reuse these assignments.
                        self._semantic_store.commit_unique_values(
                            data_model_id=data_model_id,
                            job_id=job_id,
                            entity_name=entity_name,
                            field_name=field_name,
                            values_by_row=new_assignments,
                        )

                        values_by_row.update(new_assignments)

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

                    # Register the complete row-indexed mapping. The row
                    # generator resolves values by global row position.
                    context.add_unique_semantic_values(
                        entity_name=entity_name,
                        field_name=field_name,
                        values_by_row=values_by_row,
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
                    persist=False,
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
                    attempt_id=checkpoint.attempt_id,
                    row_start=(chunk_number - 1) * chunk_size,
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
                    mandatory_relationships=[
                        {
                            "child_fields": group.child_fields,
                            "parent_entity": group.parent_entity,
                            "parent_fields": group.parent_fields,
                        }
                        for group in plan.relationship_groups
                        if (
                            group.child_entity == entity_name
                            and group.resolution_status == "MAPPED"
                            and group.relationship_type.upper() in {
                                "ONE_TO_MANY",
                                "ONE_TO_ONE",
                            }
                            and group.parent_participation.upper() == "MANDATORY"
                        )
                    ],
                    one_to_one_relationships=[
                        {
                            "child_fields": group.child_fields,
                            "parent_entity": group.parent_entity,
                            "parent_fields": group.parent_fields,
                            "parent_participation": group.parent_participation,
                        }
                        for group in plan.relationship_groups
                        if (
                            group.child_entity == entity_name
                            and group.resolution_status == "MAPPED"
                            and group.relationship_type.upper() == "ONE_TO_ONE"
                            and group.child_participation.upper() == "MANDATORY"
                        )
                    ],
                    chunk_size=chunk_size,
                    start_chunk=1,
                    chunk_numbers=missing_chunk_numbers,
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
                attempt_id=checkpoint.attempt_id,
                fieldnames=[
                    field["name"]
                    for field in entity.get("fields", [])
                ],
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
