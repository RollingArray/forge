"""
File: row_generator.py
Purpose: Build production FORGE rows from scalar and FK semantics.
"""

from __future__ import annotations

from typing import Any

from app.services.generation.context import GenerationContext
from app.services.generation.foreign_keys import ForeignKeyGenerator
from app.services.generation.generator import Generator


class RowGenerationError(ValueError):
    """Raised when a row cannot be generated."""


class RowGenerator:
    """Generate one entity row using production generation semantics."""

    def __init__(
        self,
        *,
        seed: int,
    ) -> None:
        self._generator = Generator(seed=seed)
        self._foreign_keys = ForeignKeyGenerator(seed=seed)

    def generate_row(
        self,
        *,
        entity_name: str,
        fields: list[dict[str, Any]],
        foreign_keys: list[dict[str, Any]],
        context: GenerationContext,
        row_number: int,
        chunk_number: int | None = None,
        initial_values: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Generate one row.

        Composite foreign keys have precedence over independent
        single-field foreign keys. Scalar generation only fills
        fields that have not already been assigned.
        """

        row: dict[str, Any] = dict(initial_values or {})

        composite_foreign_keys = [
            foreign_key
            for foreign_key in foreign_keys
            if len(foreign_key["child_fields"]) > 1
        ]

        single_foreign_keys = [
            foreign_key
            for foreign_key in foreign_keys
            if len(foreign_key["child_fields"]) == 1
        ]

        for foreign_key in composite_foreign_keys:
            if all(
                field in row
                for field in foreign_key["child_fields"]
            ):
                continue

            self._assign_foreign_key(
                row=row,
                foreign_key=foreign_key,
                context=context,
            )

        for foreign_key in single_foreign_keys:
            source_field = foreign_key["child_fields"][0]

            if source_field in row:
                continue

            self._assign_foreign_key(
                row=row,
                foreign_key=foreign_key,
                context=context,
            )

        for field in fields:
            field_name = field["name"]

            if field_name in row:
                continue

            generation = field.get("generation") or {}

            if generation.get("generator") == "SEMANTIC":
                parameters = generation.get("parameters") or {}
                mode = str(parameters.get("mode", "")).strip().upper()

                if mode in {"UNIQUE", "VOCABULARY"}:
                    semantic_values = context.get_semantic_values(
                        entity_name=entity_name,
                        field_name=field_name,
                        chunk_number=(
                            chunk_number
                            if mode == "UNIQUE"
                            else None
                        ),
                    )

                    if not semantic_values:
                        raise RowGenerationError(
                            f"No semantic values available for "
                            f"{entity_name}.{field_name}."
                        )

                    if mode == "UNIQUE":
                        if chunk_number is not None:
                            value_index = (
                                (row_number - 1)
                                % len(semantic_values)
                            )
                        else:
                            value_index = row_number - 1

                        if value_index >= len(semantic_values):
                            raise RowGenerationError(
                                f"Semantic value missing for "
                                f"{entity_name}.{field_name} "
                                f"at row {row_number}."
                            )

                        row[field_name] = semantic_values[value_index]
                    else:
                        row[field_name] = self._generator.choose_from(
                            semantic_values
                        )

                    continue

            row[field_name] = self._generator.generate_value(
                field=field,
                row_number=row_number,
            )

        return row

    def _assign_foreign_key(
        self,
        *,
        row: dict[str, Any],
        foreign_key: dict[str, Any],
        context: GenerationContext,
    ) -> None:
        child_fields = tuple(
            foreign_key["child_fields"]
        )
        parent_entity = foreign_key["parent_entity"]
        parent_fields = tuple(
            foreign_key["parent_fields"]
        )

        self._foreign_keys.assign_from_context(
            row=row,
            child_fields=child_fields,
            parent_entity=parent_entity,
            parent_fields=parent_fields,
            context=context,
        )
