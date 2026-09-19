"""
FORGE Generation Core
Generation context.

Stores generated entity rows and identity combinations needed
for downstream generation and uniqueness checks.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class EntityGenerationContext:
    """Generated values and identities for one entity."""

    entity_name: str
    rows: list[dict[str, Any]] = field(default_factory=list)
    identities: set[tuple[Any, ...]] = field(default_factory=set)
    identity_fields: tuple[str, ...] = ()

    def _validate_identity_fields(
        self,
        identity_fields: tuple[str, ...],
    ) -> None:
        """Validate that identity fields remain consistent."""

        if (
            identity_fields
            and self.identity_fields
            and self.identity_fields != identity_fields
        ):
            raise ValueError(
                f"Identity fields for {self.entity_name} changed from "
                f"{self.identity_fields!r} to {identity_fields!r}."
            )

    def _build_incoming_identities(
        self,
        rows: list[dict[str, Any]],
        identity_fields: tuple[str, ...],
    ) -> set[tuple[Any, ...]]:
        """Build and validate identities before mutating context."""

        incoming_identities: set[tuple[Any, ...]] = set()

        for row in rows:
            identity = self.build_identity(
                row,
                identity_fields,
            )

            if identity in self.identities:
                raise ValueError(
                    f"Duplicate identity detected for "
                    f"{self.entity_name}: {identity!r}"
                )

            if identity in incoming_identities:
                raise ValueError(
                    f"Duplicate identity detected within generated rows "
                    f"for {self.entity_name}: {identity!r}"
                )

            incoming_identities.add(identity)

        return incoming_identities

    def add_rows(
        self,
        rows: list[dict[str, Any]],
        identity_fields: tuple[str, ...] = (),
    ) -> None:
        """Store generated rows and their identities atomically."""

        self._validate_identity_fields(identity_fields)

        incoming_identities: set[tuple[Any, ...]] = set()

        if identity_fields:
            incoming_identities = self._build_incoming_identities(
                rows,
                identity_fields,
            )

        self.rows.extend(rows)

        if identity_fields:
            self.identity_fields = identity_fields
            self.identities.update(incoming_identities)

    @staticmethod
    def build_identity(
        row: dict[str, Any],
        identity_fields: tuple[str, ...],
    ) -> tuple[Any, ...]:
        """Build an identity tuple from a generated row."""

        return tuple(row.get(field) for field in identity_fields)

    def get_identity_fields(self) -> tuple[str, ...]:
        """Return the declared identity fields for this entity."""

        return self.identity_fields

    def get_key_values(
        self,
        fields: tuple[str, ...],
    ) -> list[tuple[Any, ...]]:
        """Return unique values for the requested fields."""

        values: list[tuple[Any, ...]] = []
        seen: set[tuple[Any, ...]] = set()

        for row in self.rows:
            key = tuple(row.get(field) for field in fields)

            if any(value is None for value in key):
                continue

            if key not in seen:
                seen.add(key)
                values.append(key)

        return values


@dataclass
class GenerationContext:
    """Context accumulated while entities are generated."""

    entities: dict[str, EntityGenerationContext] = field(default_factory=dict)

    def register_entity(
        self,
        entity_name: str,
    ) -> EntityGenerationContext:
        """Create or return an entity context."""

        if entity_name not in self.entities:
            self.entities[entity_name] = EntityGenerationContext(
                entity_name=entity_name,
            )

        return self.entities[entity_name]

    def add_rows(
        self,
        entity_name: str,
        rows: list[dict[str, Any]],
        identity_fields: tuple[str, ...] = (),
    ) -> None:
        """Store generated rows and identity values."""

        context = self.register_entity(entity_name)

        context.add_rows(
            rows,
            identity_fields,
        )

    def get_identity_fields(
        self,
        entity_name: str,
    ) -> tuple[str, ...]:
        """Return the declared identity fields for a generated entity."""

        context = self.entities.get(entity_name)

        if context is None:
            return ()

        return context.get_identity_fields()

    def get_key_values(
        self,
        entity_name: str,
        fields: tuple[str, ...],
    ) -> list[tuple[Any, ...]]:
        """Return available key values from a generated entity."""

        context = self.entities.get(entity_name)

        if context is None:
            return []

        return context.get_key_values(fields)
