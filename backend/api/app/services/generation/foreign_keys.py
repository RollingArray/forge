"""
File: foreign_keys.py
Purpose: Foreign-key assignment for the production FORGE generator.
"""

from __future__ import annotations

import random
from typing import Any

from app.services.generation.context import GenerationContext


class ForeignKeyGenerationError(ValueError):
    """Raised when a foreign key cannot be resolved."""


class ForeignKeyGenerator:
    """Resolve foreign keys from generated parent key spaces."""

    def __init__(self, seed: int) -> None:
        self._random = random.Random(seed)

    def assign_from_context(
        self,
        *,
        row: dict[str, Any],
        child_fields: tuple[str, ...],
        parent_entity: str,
        parent_fields: tuple[str, ...],
        context: GenerationContext,
    ) -> None:
        """
        Assign a foreign key using a generated parent key space.

        Composite foreign keys are selected as complete tuples.
        """

        parent_keys = context.get_key_space(
            entity_name=parent_entity,
            fields=parent_fields,
        )

        self.assign(
            row=row,
            source_fields=child_fields,
            target_fields=parent_fields,
            parent_keys=parent_keys,
        )

    def assign(
        self,
        *,
        row: dict[str, Any],
        source_fields: tuple[str, ...],
        target_fields: tuple[str, ...],
        parent_keys: set[tuple[Any, ...]],
    ) -> None:
        """Assign one foreign-key relationship."""

        if not source_fields:
            raise ForeignKeyGenerationError(
                "Foreign-key source fields cannot be empty."
            )

        if len(source_fields) != len(target_fields):
            raise ForeignKeyGenerationError(
                "Foreign-key source and target field counts differ."
            )

        if not parent_keys:
            raise ForeignKeyGenerationError(
                "Parent key space is empty."
            )

        selected_key = self._random.choice(
            tuple(parent_keys)
        )

        for source_field, value in zip(
            source_fields,
            selected_key,
            strict=True,
        ):
            row[source_field] = value
