"""
File: entity_generator.py
Purpose: Generate rows for one production FORGE entity.
"""

from __future__ import annotations

import random
from itertools import product
from typing import Any, Callable

from app.services.generation.context import GenerationContext
from app.services.generation.row_generator import RowGenerator


class EntityGenerationError(ValueError):
    """Raised when an entity cannot be generated."""


class EntityGenerator:
    """Generate and register rows for one entity."""

    def __init__(
        self,
        *,
        seed: int,
    ) -> None:
        self._random = random.Random(seed)
        self._row_generator = RowGenerator(
            seed=seed,
        )

    def generate(
        self,
        *,
        entity: dict[str, Any],
        foreign_keys: list[dict[str, Any]],
        context: GenerationContext,
        chunk_size: int = 50,
        on_chunk_completed: Callable[[str, int, int, int, list[dict[str, Any]]], None] | None = None,
    ) -> list[dict[str, Any]]:
        """Generate the configured population in bounded execution chunks."""

        entity_name = entity["name"]
        population = entity.get("population") or {}
        target_rows = population.get("count", 0)

        if target_rows < 0:
            raise EntityGenerationError(
                f"Negative population for {entity_name}: {target_rows}"
            )

        if chunk_size <= 0:
            raise EntityGenerationError(
                "Generation chunk size must be greater than zero."
            )

        fields = entity.get("fields") or []
        identity_fields = self._identity_fields(
            entity=entity,
            fields=fields,
        )

        identity_rows = self._allocate_fk_identity(
            target_rows=target_rows,
            identity_fields=identity_fields,
            foreign_keys=foreign_keys,
            context=context,
            fields=fields,
        )

        total_chunks = (
            (target_rows + chunk_size - 1) // chunk_size
            if target_rows > 0
            else 0
        )

        rows: list[dict[str, Any]] = []

        for chunk_number, chunk_start in enumerate(
            range(0, target_rows, chunk_size),
            start=1,
        ):
            chunk_end = min(
                chunk_start + chunk_size,
                target_rows,
            )

            chunk_rows: list[dict[str, Any]] = []

            for row_index in range(chunk_start, chunk_end):
                row = self._row_generator.generate_row(
                    entity_name=entity_name,
                    fields=fields,
                    foreign_keys=foreign_keys,
                    context=context,
                    row_number=row_index + 1,
                    initial_values=identity_rows[row_index],
                )

                chunk_rows.append(row)

            rows.extend(chunk_rows)

            context.add_rows(
                entity_name=entity_name,
                rows=chunk_rows,
                identity_fields=identity_fields,
            )

            if on_chunk_completed is not None:
                on_chunk_completed(
                    entity_name,
                    chunk_number,
                    total_chunks,
                    len(rows),
                    chunk_rows,
                )

        self._validate_identity_uniqueness(
            entity_name=entity_name,
            rows=rows,
            identity_fields=identity_fields,
        )

        return rows

    @staticmethod
    def _identity_fields(
        *,
        entity: dict[str, Any],
        fields: list[dict[str, Any]],
    ) -> tuple[str, ...]:
        identity = entity.get("identity") or {}

        explicit_fields = identity.get("fields")

        if explicit_fields:
            return tuple(explicit_fields)

        return tuple(
            field["name"]
            for field in fields
            if field.get("identity")
        )

    def _allocate_fk_identity(
        self,
        *,
        target_rows: int,
        identity_fields: tuple[str, ...],
        foreign_keys: list[dict[str, Any]],
        context: GenerationContext,
        fields: list[dict[str, Any]] | None = None,
    ) -> list[dict[str, Any]]:
        """Allocate unique identity values without materializing the full Cartesian product."""

        if target_rows == 0 or not identity_fields:
            return [{} for _ in range(target_rows)]

        fields_by_name = {
            field["name"]: field
            for field in (fields or [])
        }

        identity_set = set(identity_fields)

        components: list[
            tuple[tuple[str, ...], list[tuple[Any, ...]]]
        ] = []

        covered_fields: set[str] = set()

        composite_fks = [
            foreign_key
            for foreign_key in foreign_keys
            if len(foreign_key["child_fields"]) > 1
        ]

        for foreign_key in composite_fks:
            child_fields = tuple(
                foreign_key["child_fields"]
            )

            if not set(child_fields).issubset(identity_set):
                continue

            parent_keys = context.get_key_space(
                entity_name=foreign_key["parent_entity"],
                fields=tuple(foreign_key["parent_fields"]),
            )

            if not parent_keys:
                raise EntityGenerationError(
                    "Cannot allocate identity for composite FK: "
                    f"{child_fields}"
                )

            components.append(
                (child_fields, list(parent_keys))
            )

            covered_fields.update(child_fields)

        for foreign_key in foreign_keys:
            child_fields = tuple(
                foreign_key["child_fields"]
            )

            if len(child_fields) != 1:
                continue

            child_field = child_fields[0]

            if child_field not in identity_set:
                continue

            if child_field in covered_fields:
                continue

            parent_keys = context.get_key_space(
                entity_name=foreign_key["parent_entity"],
                fields=tuple(foreign_key["parent_fields"]),
            )

            if not parent_keys:
                raise EntityGenerationError(
                    "Cannot allocate identity for FK: "
                    f"{child_field}"
                )

            components.append(
                (child_fields, list(parent_keys))
            )

            covered_fields.add(child_field)

        for field_name in identity_fields:
            if field_name in covered_fields:
                continue

            field = fields_by_name.get(field_name)

            if field is None:
                raise EntityGenerationError(
                    f"Identity field {field_name!r} "
                    "is missing from the entity fields."
                )

            values = self._local_identity_values(
                field=field,
                target_rows=target_rows,
            )

            components.append(
                ((field_name,), [
                    (value,)
                    for value in values
                ])
            )

            covered_fields.add(field_name)

        if covered_fields != identity_set:
            raise EntityGenerationError(
                "Unable to cover all identity fields for "
                f"{identity_fields}"
            )

        component_sizes = [
            len(values)
            for _, values in components
        ]

        candidate_count = 1

        for size in component_sizes:
            candidate_count *= size

        if target_rows > candidate_count:
            raise EntityGenerationError(
                f"Requested {target_rows} rows but only "
                f"{candidate_count} unique identity combinations "
                "are available."
            )

        if not components:
            return [{} for _ in range(target_rows)]

        # Select unique positions in the Cartesian product without
        # materializing the complete product.
        selected_indexes = self._select_cartesian_indexes(
            candidate_count=candidate_count,
            target_rows=target_rows,
        )

        candidates: list[dict[str, Any]] = []

        for flat_index in selected_indexes:
            row: dict[str, Any] = {}
            remaining = flat_index

            for component_index in range(
                len(components) - 1,
                -1,
                -1,
            ):
                component_fields, values = components[component_index]
                size = len(values)

                value_index = remaining % size
                remaining //= size

                key = values[value_index]

                for field, value in zip(
                    component_fields,
                    key,
                    strict=True,
                ):
                    row[field] = value

            candidates.append(row)

        return candidates

    def _select_cartesian_indexes(
        self,
        *,
        candidate_count: int,
        target_rows: int,
    ) -> list[int]:
        """Select unique Cartesian-product positions deterministically."""

        if target_rows >= candidate_count:
            return list(range(candidate_count))

        return self._random.sample(
            range(candidate_count),
            target_rows,
        )

    @staticmethod
    def _local_identity_values(
        *,
        field: dict[str, Any],
        target_rows: int,
    ) -> list[Any]:
        """Return the valid domain for a locally generated identity field."""

        generation = field.get("generation") or {}
        identity = field.get("identity") or {}

        generation_strategy = generation.get("strategy")
        identity_strategy = identity.get("strategy")
        parameters = generation.get("parameters") or {}

        if (
            field.get("type") == "IDENTIFIER"
            and identity_strategy == "SEQUENTIAL_ID"
        ):
            return list(range(1, target_rows + 1))

        if (
            generation_strategy == "RANDOM"
            and generation.get("distribution") == "CATEGORICAL"
        ):
            values = parameters.get("values")

            if not isinstance(values, list) or not values:
                raise EntityGenerationError(
                    "Categorical identity field requires "
                    "a non-empty values list."
                )

            return list(values)

        if (
            generation_strategy == "RANDOM"
            and generation.get("distribution") == "CATEGORICAL"
        ):
            values = parameters.get("values")

            if not isinstance(values, list) or not values:
                raise EntityGenerationError(
                    "Categorical identity field requires "
                    "a non-empty values list."
                )

            return list(values)

        if (
            field.get("type") == "INTEGER"
            and generation_strategy == "RANDOM"
            and generation.get("distribution") == "UNIFORM"
        ):
            minimum = parameters.get("minimum")
            maximum = parameters.get("maximum")

            if minimum is None or maximum is None:
                raise EntityGenerationError(
                    "Uniform identity field requires "
                    "minimum and maximum."
                )

            if minimum > maximum:
                raise EntityGenerationError(
                    "Identity field minimum cannot exceed maximum."
                )

            return list(range(minimum, maximum + 1))

        if (
            field.get("type") == "INTEGER"
            and generation_strategy == "RANDOM"
            and generation.get("distribution") == "DISCRETE_UNIFORM"
        ):
            minimum = parameters.get("minimum")
            maximum = parameters.get("maximum")

            if minimum is None or maximum is None:
                raise EntityGenerationError(
                    "Discrete uniform identity field requires "
                    "minimum and maximum."
                )

            if minimum > maximum:
                raise EntityGenerationError(
                    "Identity field minimum cannot exceed maximum."
                )

            return list(range(minimum, maximum + 1))

        raise EntityGenerationError(
            "Unsupported locally generated identity field: "
            f"{field.get('name')}"
        )

    @staticmethod
    def _validate_identity_uniqueness(
        *,
        entity_name: str,
        rows: list[dict[str, Any]],
        identity_fields: tuple[str, ...],
    ) -> None:
        """Ensure generated identity keys are unique."""

        if not identity_fields:
            return

        keys = {
            tuple(row[field] for field in identity_fields)
            for row in rows
        }

        if len(keys) != len(rows):
            raise EntityGenerationError(
                f"Duplicate identity detected for {entity_name}: "
                f"{identity_fields}"
            )
