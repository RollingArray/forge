"""
File: entity_generator.py
Purpose: Generate rows for one production FORGE entity.
"""

from __future__ import annotations

from bisect import bisect_right
from decimal import Decimal

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
        self._seed = seed
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
        mandatory_relationships: list[dict[str, Any]] | None = None,
        chunk_size: int = 50,
        start_chunk: int = 1,
        on_chunk_start: Callable[[str, int, int, int], None] | None = None,
        on_chunk_completed: Callable[[str, int, int, int, list[dict[str, Any]]], None] | None = None,
        on_field_activity: Callable[[str, int, str, str], None] | None = None,
    ) -> int:
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

        if start_chunk <= 0:
            raise EntityGenerationError(
                "Generation start chunk must be greater than zero."
            )

        fields = entity.get("fields") or []
        identity_fields = self._identity_fields(
            entity=entity,
            fields=fields,
        )

        mandatory_assignments: list[
            tuple[tuple[str, ...], list[tuple[Any, ...]]]
        ] = []

        seen_mandatory_mappings: set[
            tuple[tuple[str, ...], str, tuple[str, ...]]
        ] = set()

        for relationship in mandatory_relationships or []:
            child_fields = tuple(relationship["child_fields"])
            parent_entity = relationship["parent_entity"]
            parent_fields = tuple(relationship["parent_fields"])

            if not child_fields or len(child_fields) != len(parent_fields):
                raise EntityGenerationError(
                    f"{entity_name}: invalid mandatory relationship "
                    f"mapping {child_fields} -> {parent_entity}.{parent_fields}."
                )

            identity_overlap = set(child_fields).intersection(identity_fields)

            if identity_overlap and not set(child_fields).issubset(identity_fields):
                raise EntityGenerationError(
                    f"{entity_name}: mandatory relationship fields "
                    f"{child_fields} must either all participate in the "
                    "child identity or remain outside it."
                )

            matching_foreign_keys = [
                foreign_key
                for foreign_key in foreign_keys
                if tuple(foreign_key["child_fields"]) == child_fields
                and foreign_key["parent_entity"] == parent_entity
                and tuple(foreign_key["parent_fields"]) == parent_fields
            ]

            if len(matching_foreign_keys) != 1:
                raise EntityGenerationError(
                    f"{entity_name}: mandatory relationship "
                    f"{child_fields} -> {parent_entity}.{parent_fields} "
                    "does not resolve to exactly one generation FK."
                )

            mapping_key = (
                child_fields,
                parent_entity,
                parent_fields,
            )

            if mapping_key in seen_mandatory_mappings:
                continue

            seen_mandatory_mappings.add(mapping_key)

            indexed_parent_keys = context.get_indexed_key_space(
                entity_name=parent_entity,
                fields=parent_fields,
            )

            if not indexed_parent_keys:
                raise EntityGenerationError(
                    f"{entity_name}: mandatory parent participation "
                    f"cannot be satisfied because {parent_entity} "
                    "has no generated parent keys."
                )

            if len(indexed_parent_keys) > target_rows:
                raise EntityGenerationError(
                    f"{entity_name}: mandatory parent participation "
                    f"requires at least {len(indexed_parent_keys)} child "
                    f"rows, but the configured population is {target_rows}."
                )

            mandatory_assignments.append(
                (child_fields, indexed_parent_keys)
            )

        total_chunks = (
            (target_rows + chunk_size - 1) // chunk_size
            if target_rows > 0
            else 0
        )

        generated_rows = 0

        first_chunk_index = (start_chunk - 1) * chunk_size

        for chunk_number, chunk_start in enumerate(
            range(
                first_chunk_index,
                target_rows,
                chunk_size,
            ),
            start=start_chunk,
        ):
            chunk_end = min(
                chunk_start + chunk_size,
                target_rows,
            )

            if on_chunk_start is not None:
                on_chunk_start(
                    entity_name,
                    chunk_number,
                    chunk_start,
                    chunk_end,
                )

            identity_rows = self._allocate_fk_identity(
                target_rows=target_rows,
                row_start=chunk_start,
                row_count=chunk_end - chunk_start,
                identity_fields=identity_fields,
                foreign_keys=foreign_keys,
                context=context,
                fields=fields,
                mandatory_assignments=mandatory_assignments,
            )

            # Mandatory parent participation is allocated against global
            # child-row positions, not local chunk positions. This keeps
            # coverage deterministic across chunk boundaries and resumes.
            for local_index, row_index in enumerate(
                range(chunk_start, chunk_end)
            ):
                for child_fields, parent_keys in mandatory_assignments:
                    # Identity fields have already been assigned by the
                    # constrained Cartesian identity allocator.
                    if set(child_fields).issubset(identity_fields):
                        continue

                    if row_index >= len(parent_keys):
                        continue

                    parent_key = parent_keys[row_index]

                    for child_field, value in zip(
                        child_fields,
                        parent_key,
                        strict=True,
                    ):
                        identity_rows[local_index][child_field] = value

            self._prepare_chunk_semantic_values(
                entity_name=entity_name,
                fields=fields,
                context=context,
                chunk_number=chunk_number,
                chunk_start=chunk_start,
                chunk_end=chunk_end,
            )

            chunk_rows: list[dict[str, Any]] = []

            if on_field_activity is not None:
                for field in fields:
                    on_field_activity(
                        entity_name,
                        chunk_number,
                        field["name"],
                        "STARTED",
                    )

            for local_index, row_index in enumerate(
                range(chunk_start, chunk_end)
            ):
                row = self._row_generator.generate_row(
                    entity_name=entity_name,
                    fields=fields,
                    foreign_keys=foreign_keys,
                    context=context,
                    row_number=row_index + 1,
                    chunk_number=chunk_number,
                    initial_values=identity_rows[local_index],
                )

                chunk_rows.append(row)

            if on_field_activity is not None:
                for field in fields:
                    on_field_activity(
                        entity_name,
                        chunk_number,
                        field["name"],
                        "COMPLETED",
                    )

            generated_rows += len(chunk_rows)

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
                    generated_rows,
                    chunk_rows,
                )

        return generated_rows

    @staticmethod
    def _prepare_chunk_semantic_values(
        *,
        entity_name: str,
        fields: list[dict[str, Any]],
        context: GenerationContext,
        chunk_number: int,
        chunk_start: int,
        chunk_end: int,
    ) -> None:
        """Prepare the semantic values needed by the current chunk."""

        for field in fields:
            generation = field.get("generation") or {}

            if generation.get("generator") != "SEMANTIC":
                continue

            parameters = generation.get("parameters") or {}
            mode = str(
                parameters.get("mode", "")
            ).strip().upper()

            if mode != "UNIQUE":
                continue

            values = context.get_semantic_values(
                entity_name=entity_name,
                field_name=field["name"],
            )

            if not values:
                continue

            chunk_values = values[chunk_start:chunk_end]

            context.add_semantic_values(
                entity_name=entity_name,
                field_name=field["name"],
                values=chunk_values,
                chunk_number=chunk_number,
            )

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
        row_start: int,
        row_count: int,
        identity_fields: tuple[str, ...],
        foreign_keys: list[dict[str, Any]],
        context: GenerationContext,
        fields: list[dict[str, Any]] | None = None,
        mandatory_assignments: list[
            tuple[tuple[str, ...], list[tuple[Any, ...]]]
        ] | None = None,
    ) -> list[dict[str, Any]]:
        """Allocate identity values for one generation chunk."""

        if row_count == 0 or not identity_fields:
            return [{} for _ in range(row_count)]

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
            indexed_parent_keys = context.get_indexed_key_space(
                entity_name=foreign_key["parent_entity"],
                fields=tuple(foreign_key["parent_fields"]),
            )

            if not parent_keys or not indexed_parent_keys:
                raise EntityGenerationError(
                    "Cannot allocate identity for composite FK: "
                    f"{child_fields}"
                )

            components.append(
                (child_fields, list(indexed_parent_keys))
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
            indexed_parent_keys = context.get_indexed_key_space(
                entity_name=foreign_key["parent_entity"],
                fields=tuple(foreign_key["parent_fields"]),
            )

            if not parent_keys or not indexed_parent_keys:
                raise EntityGenerationError(
                    "Cannot allocate identity for FK: "
                    f"{child_field}"
                )

            components.append(
                (child_fields, list(indexed_parent_keys))
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
                ((field_name,), values)
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

        mandatory_identity_assignments = mandatory_assignments or []

        has_mandatory_identity = any(
            set(child_fields).issubset(identity_set)
            for child_fields, _ in mandatory_identity_assignments
        )

        if has_mandatory_identity:
            selected_indexes = self._select_mandatory_cartesian_indexes(
                components=components,
                mandatory_assignments=mandatory_identity_assignments,
                candidate_count=candidate_count,
                row_start=row_start,
                row_count=row_count,
                target_rows=target_rows,
                identity_fields=identity_fields,
            )
        else:
            selected_indexes = self._select_cartesian_indexes(
                candidate_count=candidate_count,
                row_start=row_start,
                row_count=row_count,
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

                if len(component_fields) == 1 and not isinstance(
                    key,
                    tuple,
                ):
                    key_values = (key,)
                else:
                    key_values = key

                for field, value in zip(
                    component_fields,
                    key_values,
                    strict=True,
                ):
                    row[field] = value

            candidates.append(row)

        return candidates

    def _select_mandatory_cartesian_indexes(
        self,
        *,
        components: list[tuple[tuple[str, ...], list[Any]]],
        mandatory_assignments: list[
            tuple[tuple[str, ...], list[tuple[Any, ...]]]
        ],
        candidate_count: int,
        row_start: int,
        row_count: int,
        target_rows: int,
        identity_fields: tuple[str, ...],
    ) -> list[int]:
        """Select a bounded chunk while preserving mandatory parent coverage.

        Mandatory parent keys receive reserved Cartesian combinations at
        the beginning of the global row sequence. Remaining rows follow
        the existing deterministic permutation, excluding those reserved
        combinations.

        Only the requested chunk is materialized. Resume selection locates
        its position in the permutation without constructing prior rows.
        """

        component_sizes = [
            len(values)
            for _, values in components
        ]

        mandatory_components: dict[int, list[int]] = {}

        for child_fields, parent_keys in mandatory_assignments:
            if not set(child_fields).issubset(identity_fields):
                continue

            matching_components = [
                index
                for index, (component_fields, _) in enumerate(components)
                if component_fields == child_fields
            ]

            if len(matching_components) != 1:
                raise EntityGenerationError(
                    "Mandatory identity relationship "
                    f"{child_fields} does not resolve to exactly one "
                    "identity allocation component."
                )

            component_index = matching_components[0]
            component_values = components[component_index][1]

            if component_index in mandatory_components:
                raise EntityGenerationError(
                    "Multiple mandatory relationships cannot allocate "
                    f"the same identity component: {child_fields}."
                )

            value_indexes = {
                tuple(value): index
                for index, value in enumerate(component_values)
            }

            parent_indexes: list[int] = []

            for parent_key in parent_keys:
                normalized_key = tuple(parent_key)

                if normalized_key not in value_indexes:
                    raise EntityGenerationError(
                        "Mandatory parent key "
                        f"{normalized_key} is missing from identity "
                        f"component {child_fields}."
                    )

                parent_indexes.append(value_indexes[normalized_key])

            mandatory_components[component_index] = parent_indexes

        if not mandatory_components:
            raise EntityGenerationError(
                "Mandatory identity allocation was requested without "
                "a matching identity component."
            )

        mandatory_prefix = max(
            len(indexes)
            for indexes in mandatory_components.values()
        )

        if mandatory_prefix > target_rows:
            raise EntityGenerationError(
                "Mandatory parent coverage exceeds the child population."
            )

        if mandatory_prefix > candidate_count:
            raise EntityGenerationError(
                "Mandatory parent coverage exceeds the available "
                "identity combinations."
            )

        # Recreate the existing deterministic Cartesian permutation.
        permutation_random = random.Random(
            self._seed ^ candidate_count
        )
        offset = permutation_random.randrange(candidate_count)
        multiplier = self._permutation_multiplier(candidate_count)

        # Convert reserved Cartesian indexes into positions in that
        # permutation. This lets us skip them without building the full
        # selected identity sequence.
        reserved_indexes: set[int] = set()

        for row_index in range(mandatory_prefix):
            coordinates = [
                row_index % size
                for size in component_sizes
            ]

            for component_index, parent_indexes in mandatory_components.items():
                if row_index < len(parent_indexes):
                    coordinates[component_index] = parent_indexes[row_index]

            flat_index = 0
            for coordinate, size in zip(
                coordinates,
                component_sizes,
                strict=True,
            ):
                flat_index = flat_index * size + coordinate

            if flat_index in reserved_indexes:
                raise EntityGenerationError(
                    "Mandatory parent coverage produced a duplicate "
                    "identity combination."
                )

            reserved_indexes.add(flat_index)

        if candidate_count == 1:
            inverse_multiplier = 0
        else:
            inverse_multiplier = pow(
                multiplier,
                -1,
                candidate_count,
            )

        reserved_positions = sorted(
            (
                (reserved_index - offset)
                * inverse_multiplier
            ) % candidate_count
            for reserved_index in reserved_indexes
        )
        reserved_position_set = set(reserved_positions)

        selected: list[int] = []
        chunk_end = row_start + row_count

        # Materialize only mandatory selections that belong to this chunk.
        mandatory_end = min(chunk_end, mandatory_prefix)

        for row_index in range(row_start, mandatory_end):
            coordinates = [
                row_index % size
                for size in component_sizes
            ]

            for component_index, parent_indexes in mandatory_components.items():
                if row_index < len(parent_indexes):
                    coordinates[component_index] = parent_indexes[row_index]

            flat_index = 0
            for coordinate, size in zip(
                coordinates,
                component_sizes,
                strict=True,
            ):
                flat_index = flat_index * size + coordinate

            selected.append(flat_index)

        # Locate the first non-mandatory row in this chunk. The number of
        # available permutation positions through p is:
        # p + 1 - count(reserved positions <= p).
        first_remaining_row = max(row_start, mandatory_prefix)

        if first_remaining_row < chunk_end:
            available_index = first_remaining_row - mandatory_prefix
            required_available_count = available_index + 1

            low = 0
            high = candidate_count - 1

            while low < high:
                middle = (low + high) // 2
                available_count = (
                    middle + 1
                    - bisect_right(reserved_positions, middle)
                )

                if available_count >= required_available_count:
                    high = middle
                else:
                    low = middle + 1

            permutation_position = low

            for _row_index in range(first_remaining_row, chunk_end):
                if permutation_position >= candidate_count:
                    raise EntityGenerationError(
                        "Unable to allocate enough unique identity "
                        "combinations after mandatory parent coverage."
                    )

                selected.append(
                    (
                        offset
                        + multiplier * permutation_position
                    ) % candidate_count
                )

                permutation_position += 1

                while permutation_position in reserved_position_set:
                    permutation_position += 1

        return selected

    def _select_cartesian_indexes(
        self,
        *,
        candidate_count: int,
        row_start: int,
        row_count: int,
        target_rows: int,
    ) -> list[int]:
        """Select unique Cartesian positions for the requested chunk."""

        if row_count == 0:
            return []

        if target_rows >= candidate_count:
            return list(
                range(
                    row_start,
                    row_start + row_count,
                )
            )

        multiplier = self._permutation_multiplier(candidate_count)

        # Derive one stable offset for this generation seed and candidate
        # space. Chunk boundaries must only select windows into the same
        # deterministic permutation, never create a new permutation.
        permutation_random = random.Random(
            self._seed ^ candidate_count
        )
        offset = permutation_random.randrange(candidate_count)

        return [
            (offset + multiplier * row_index) % candidate_count
            for row_index in range(
                row_start,
                row_start + row_count,
            )
        ]

    @staticmethod
    def _permutation_multiplier(candidate_count: int) -> int:
        """Return a multiplier coprime with the candidate-space size."""

        if candidate_count <= 1:
            return 1

        from math import gcd

        multiplier = candidate_count - 1

        while gcd(multiplier, candidate_count) != 1:
            multiplier -= 1

        return multiplier

    @staticmethod
    def _local_identity_values(
        *,
        field: dict[str, Any],
        target_rows: int,
    ) -> range | list[Any]:
        """Return the validated domain for a locally generated identity field."""

        generation = field.get("generation") or {}
        identity = field.get("identity") or {}

        generation_strategy = generation.get("strategy")
        identity_strategy = identity.get("strategy")
        distribution = generation.get("distribution")
        parameters = generation.get("parameters") or {}
        field_name = field.get("name", "FIELD")

        if (
            field.get("type") == "IDENTIFIER"
            and identity_strategy == "SEQUENTIAL_ID"
        ):
            return range(1, target_rows + 1)

        if generation_strategy == "RANDOM" and distribution == "CATEGORICAL":
            values = parameters.get("values")

            if not isinstance(values, list) or not values:
                raise EntityGenerationError(
                    f"Categorical identity field {field_name} requires "
                    "a non-empty values list."
                )

            # Identity capacity must reflect distinct candidate values.
            # Preserve their order so deterministic allocation is unchanged.
            unique_values = []
            for value in values:
                if value not in unique_values:
                    unique_values.append(value)

            return unique_values

        if (
            field.get("type") == "INTEGER"
            and generation_strategy == "RANDOM"
            and distribution in {"UNIFORM", "DISCRETE_UNIFORM"}
        ):
            minimum = parameters.get("minimum")
            maximum = parameters.get("maximum")

            if (
                minimum is None
                or maximum is None
                or isinstance(minimum, bool)
                or isinstance(maximum, bool)
            ):
                raise EntityGenerationError(
                    f"Integer identity field {field_name} requires "
                    "numeric minimum and maximum bounds."
                )

            try:
                minimum_decimal = Decimal(str(minimum))
                maximum_decimal = Decimal(str(maximum))
            except (ArithmeticError, TypeError, ValueError):
                raise EntityGenerationError(
                    f"Integer identity field {field_name} has invalid bounds."
                ) from None

            if (
                not minimum_decimal.is_finite()
                or not maximum_decimal.is_finite()
            ):
                raise EntityGenerationError(
                    f"Integer identity field {field_name} bounds must be finite."
                )

            if (
                minimum_decimal != minimum_decimal.to_integral_value()
                or maximum_decimal != maximum_decimal.to_integral_value()
            ):
                raise EntityGenerationError(
                    f"Integer identity field {field_name} bounds "
                    "must be whole numbers."
                )

            if minimum_decimal > maximum_decimal:
                raise EntityGenerationError(
                    f"Integer identity field {field_name} minimum "
                    "cannot exceed maximum."
                )

            return range(
                int(minimum_decimal),
                int(maximum_decimal) + 1,
            )

        raise EntityGenerationError(
            "Unsupported locally generated identity field: "
            f"{field_name}"
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
