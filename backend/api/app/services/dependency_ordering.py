"""Shared deterministic ordering for entity dependencies."""

from __future__ import annotations


class DependencyCycleError(ValueError):
    """Raised when entity dependencies cannot be topologically ordered."""

    def __init__(self, unresolved_entities: tuple[str, ...]) -> None:
        self.unresolved_entities = unresolved_entities
        super().__init__(
            "Dependency cycle involving: "
            + ", ".join(unresolved_entities)
        )


def resolve_dependency_order(
    entity_names: list[str] | tuple[str, ...],
    dependencies: list[tuple[str, str]] | tuple[tuple[str, str], ...],
) -> tuple[str, ...]:
    """Return a stable parent-before-child entity order.

    Each dependency is expressed as (parent_entity, child_entity).
    Entities becoming ready in the same pass retain their input order.
    Duplicate edges are ignored.
    """

    names = list(entity_names)

    if len(names) != len(set(names)):
        raise ValueError("Entity names must be unique.")

    entity_set = set(names)
    position = {name: index for index, name in enumerate(names)}
    outgoing = {name: set() for name in names}
    indegree = {name: 0 for name in names}

    for parent, child in dependencies:
        if parent not in entity_set or child not in entity_set:
            raise ValueError(
                f"Dependency references an unknown entity: {parent} -> {child}"
            )

        if child not in outgoing[parent]:
            outgoing[parent].add(child)
            indegree[child] += 1

    ready = [
        name for name in names
        if indegree[name] == 0
    ]
    order: list[str] = []

    while ready:
        # Process each ready group together. This preserves the generation
        # planner's existing batch ordering behavior.
        current_batch = sorted(ready, key=position.__getitem__)
        ready = []

        for current in current_batch:
            order.append(current)

        for current in current_batch:
            for child in sorted(
                outgoing[current],
                key=position.__getitem__,
            ):
                indegree[child] -= 1
                if indegree[child] == 0:
                    ready.append(child)

    if len(order) != len(names):
        unresolved = tuple(
            name for name in names if indegree[name] > 0
        )
        raise DependencyCycleError(unresolved)

    return tuple(order)
