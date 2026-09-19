"""
FORGE Generation Core
Relationship semantics.

This module determines how dependent rows are associated with
already-generated parent rows.

It does not generate field values and does not repair datasets.
"""

from __future__ import annotations

import random
from typing import Any

from .planner import RelationshipDependency


def get_parent_child_entities(
    relationship: RelationshipDependency,
) -> tuple[str, str] | None:
    """Return parent and child entities when the relationship is directional."""

    if relationship.relationship_type == "ONE_TO_ONE":
        return (
            relationship.source_entity,
            relationship.target_entity,
        )

    if relationship.relationship_type == "ONE_TO_MANY":
        return (
            relationship.source_entity,
            relationship.target_entity,
        )

    if relationship.relationship_type == "MANY_TO_ONE":
        return (
            relationship.target_entity,
            relationship.source_entity,
        )

    if relationship.relationship_type == "MANY_TO_MANY":
        return None

    raise ValueError(
        "Unsupported relationship type: " f"{relationship.relationship_type!r}"
    )


def get_parent_child_fields(
    relationship: RelationshipDependency,
) -> tuple[tuple[str, ...], tuple[str, ...]] | None:
    """Return parent and child fields for directional relationships."""

    if relationship.relationship_type == "ONE_TO_ONE":
        return (
            relationship.source_fields,
            relationship.target_fields,
        )

    if relationship.relationship_type == "ONE_TO_MANY":
        return (
            relationship.source_fields,
            relationship.target_fields,
        )

    if relationship.relationship_type == "MANY_TO_ONE":
        return (
            relationship.target_fields,
            relationship.source_fields,
        )

    if relationship.relationship_type == "MANY_TO_MANY":
        return None

    raise ValueError(
        "Unsupported relationship type: " f"{relationship.relationship_type!r}"
    )


def calculate_child_counts(
    parent_count: int,
    child_count: int,
    relationship_type: str,
) -> list[int]:
    """Calculate how many child rows each parent receives."""

    if parent_count <= 0:
        raise ValueError("parent_count must be greater than zero.")

    if child_count < 0:
        raise ValueError("child_count cannot be negative.")

    if relationship_type == "ONE_TO_ONE":
        if child_count > parent_count:
            raise ValueError(
                "ONE_TO_ONE relationship cannot assign more child "
                "rows than parent rows."
            )

        counts = [0] * parent_count

        for index in range(child_count):
            counts[index] = 1

        return counts

    if relationship_type in {
        "ONE_TO_MANY",
        "MANY_TO_ONE",
        "MANY_TO_MANY",
    }:
        return _calculate_balanced_counts(
            parent_count,
            child_count,
        )

    raise ValueError(f"Unsupported relationship type: {relationship_type!r}")


def _calculate_balanced_counts(
    parent_count: int,
    child_count: int,
) -> list[int]:
    """Distribute child rows as evenly as possible."""

    counts = [0] * parent_count

    for index in range(child_count):
        counts[index % parent_count] += 1

    return counts


def select_parent_keys(
    parent_keys: list[tuple[Any, ...]],
    child_count: int,
    relationship_type: str,
    rng: random.Random,
    start_offset: int = 0,
) -> list[tuple[Any, ...]]:
    """Select parent keys for generated child rows.

    Selection is based on the child's global position so that
    relationship assignments remain consistent across generation chunks.
    """

    if not parent_keys:
        raise ValueError("No parent keys are available.")

    if child_count < 0:
        raise ValueError("child_count cannot be negative.")

    if start_offset < 0:
        raise ValueError("start_offset cannot be negative.")

    parent_count = len(parent_keys)

    if relationship_type == "ONE_TO_ONE":
        end_offset = start_offset + child_count

        if end_offset > parent_count:
            raise ValueError(
                "ONE_TO_ONE relationship cannot assign child rows "
                "beyond the available parent rows."
            )

        return parent_keys[start_offset:end_offset]

    if relationship_type in {
        "ONE_TO_MANY",
        "MANY_TO_ONE",
        "MANY_TO_MANY",
    }:
        selected = [
            parent_keys[(start_offset + index) % parent_count]
            for index in range(child_count)
        ]

        if relationship_type == "MANY_TO_MANY":
            rng.shuffle(selected)

        return selected

    raise ValueError(
        f"Unsupported relationship type: {relationship_type!r}"
    )


def build_relationship_assignments(
    relationship: RelationshipDependency,
    parent_keys: list[tuple[Any, ...]],
    child_count: int,
    rng: random.Random,
    start_offset: int = 0,
) -> list[dict[str, Any]]:
    """Build assignments for relationship-managed child fields."""

    selected_keys = select_parent_keys(
        parent_keys=parent_keys,
        child_count=child_count,
        relationship_type=relationship.relationship_type,
        rng=rng,
        start_offset=start_offset,
    )

    parent_child_fields = get_parent_child_fields(
        relationship,
    )

    if parent_child_fields is None:
        return []

    _, child_fields = parent_child_fields

    return [
        dict(zip(child_fields, key))
        for key in selected_keys
    ]
