"""
File: context.py
Purpose: Runtime context for the production FORGE generation engine.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class GenerationContext:
    """Hold generated data and key spaces during one generation run."""

    rows_by_entity: dict[str, list[dict[str, Any]]] = field(
        default_factory=dict,
    )

    keys_by_entity: dict[
        str,
        dict[tuple[str, ...], set[tuple[Any, ...]]],
    ] = field(
        default_factory=dict,
    )

    semantic_values_by_field: dict[
        tuple[str, str],
        list[str],
    ] = field(
        default_factory=dict,
    )

    def add_semantic_values(
        self,
        *,
        entity_name: str,
        field_name: str,
        values: list[str],
    ) -> None:
        """Register semantic values prepared for a field."""

        self.semantic_values_by_field[
            (entity_name, field_name)
        ] = list(values)

    def get_semantic_values(
        self,
        *,
        entity_name: str,
        field_name: str,
    ) -> list[str]:
        """Return semantic values prepared for a field."""

        return self.semantic_values_by_field.get(
            (entity_name, field_name),
            [],
        )

    def add_rows(
        self,
        *,
        entity_name: str,
        rows: list[dict[str, Any]],
        identity_fields: tuple[str, ...],
    ) -> None:
        """Register generated rows and their identity key space."""

        self.rows_by_entity.setdefault(
            entity_name,
            [],
        ).extend(rows)

        key_space = self.keys_by_entity.setdefault(
            entity_name,
            {},
        ).setdefault(
            identity_fields,
            set(),
        )

        for row in rows:
            key = tuple(
                row[field]
                for field in identity_fields
            )
            key_space.add(key)

    def get_key_space(
        self,
        *,
        entity_name: str,
        fields: tuple[str, ...],
    ) -> set[tuple[Any, ...]]:
        """Return the generated key space for an entity."""

        return self.keys_by_entity.get(
            entity_name,
            {},
        ).get(
            fields,
            set(),
        )

    def get_rows(
        self,
        *,
        entity_name: str,
    ) -> list[dict[str, Any]]:
        """Return generated rows for an entity."""

        return self.rows_by_entity.get(
            entity_name,
            [],
        )
