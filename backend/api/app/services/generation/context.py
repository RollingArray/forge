"""
File: context.py
Purpose: Runtime context for the production FORGE generation engine.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any


class GenerationContextIntegrityError(ValueError):
    """Raised when generated identity keys conflict with registered row positions."""


@dataclass
class GenerationContext:
    """Hold generated data and position-aware key spaces during one generation run."""

    rows_by_entity: dict[str, list[dict[str, Any]]] = field(
        default_factory=dict,
    )

    # Authoritative identity representation:
    # entity -> identity fields -> zero-based global row position -> identity key.
    identity_keys_by_row: dict[
        str,
        dict[tuple[str, ...], dict[int, tuple[Any, ...]]],
    ] = field(default_factory=dict)

    # Reverse index used to detect duplicate identities efficiently.
    identity_row_by_key: dict[
        str,
        dict[tuple[str, ...], dict[tuple[Any, ...], int]],
    ] = field(default_factory=dict)

    semantic_values_by_field: dict[
        tuple[str, str],
        list[str],
    ] = field(default_factory=dict)

    semantic_values_by_chunk: dict[
        tuple[str, str, int],
        list[str],
    ] = field(default_factory=dict)

    # Authoritative UNIQUE semantic representation:
    # (entity, field) -> zero-based global row position -> value.
    semantic_values_by_row: dict[
        tuple[str, str],
        dict[int, str],
    ] = field(default_factory=dict)

    def add_semantic_values(
        self,
        *,
        entity_name: str,
        field_name: str,
        values: list[str],
        chunk_number: int | None = None,
    ) -> None:
        """Register semantic values prepared for a field."""

        if chunk_number is None:
            self.semantic_values_by_field[
                (entity_name, field_name)
            ] = list(values)
            return

        self.semantic_values_by_chunk[
            (entity_name, field_name, chunk_number)
        ] = list(values)

    def get_semantic_values(
        self,
        *,
        entity_name: str,
        field_name: str,
        chunk_number: int | None = None,
    ) -> list[str]:
        """Return semantic values prepared for a field."""

        if chunk_number is None:
            return self.semantic_values_by_field.get(
                (entity_name, field_name),
                [],
            )

        return self.semantic_values_by_chunk.get(
            (entity_name, field_name, chunk_number),
            [],
        )

    def add_unique_semantic_values(
        self,
        *,
        entity_name: str,
        field_name: str,
        values_by_row: Mapping[int, str],
    ) -> None:
        """Register immutable UNIQUE semantic values at global row positions."""

        key = (entity_name, field_name)

        if not isinstance(values_by_row, Mapping):
            raise GenerationContextIntegrityError(
                "UNIQUE semantic values must be supplied as a row mapping."
            )

        existing = self.semantic_values_by_row.get(key, {})
        incoming: dict[int, str] = {}

        for row_index, value in values_by_row.items():
            if (
                isinstance(row_index, bool)
                or not isinstance(row_index, int)
                or row_index < 0
            ):
                raise GenerationContextIntegrityError(
                    f"Invalid UNIQUE semantic row position: {row_index!r}."
                )

            if not isinstance(value, str) or not value.strip():
                raise GenerationContextIntegrityError(
                    f"Invalid UNIQUE semantic value at row {row_index}."
                )

            previous = existing.get(row_index)
            if previous is not None and previous != value:
                raise GenerationContextIntegrityError(
                    f"Conflicting UNIQUE semantic value for "
                    f"{entity_name}.{field_name} at row {row_index}."
                )

            pending = incoming.get(row_index)
            if pending is not None and pending != value:
                raise GenerationContextIntegrityError(
                    f"Conflicting incoming UNIQUE semantic value at row "
                    f"{row_index}."
                )

            incoming[row_index] = value

        combined = dict(existing)
        combined.update(incoming)

        normalized = [
            value.strip().casefold()
            for value in combined.values()
        ]
        if len(normalized) != len(set(normalized)):
            raise GenerationContextIntegrityError(
                f"Duplicate UNIQUE semantic values for "
                f"{entity_name}.{field_name}."
            )

        if combined != existing:
            self.semantic_values_by_row[key] = combined

    def get_unique_semantic_values(
        self,
        *,
        entity_name: str,
        field_name: str,
    ) -> dict[int, str] | None:
        """Return a defensive copy, or None if no mapping is registered."""

        values = self.semantic_values_by_row.get((entity_name, field_name))
        return None if values is None else dict(values)

    def get_unique_semantic_value(
        self,
        *,
        entity_name: str,
        field_name: str,
        row_index: int,
    ) -> str | None:
        """Return the UNIQUE semantic value assigned to one global row."""

        if (
            isinstance(row_index, bool)
            or not isinstance(row_index, int)
            or row_index < 0
        ):
            raise GenerationContextIntegrityError(
                f"Invalid UNIQUE semantic row position: {row_index!r}."
            )

        values = self.semantic_values_by_row.get((entity_name, field_name))
        if values is None:
            return None

        return values.get(row_index)

    def add_rows(
        self,
        *,
        entity_name: str,
        rows: list[dict[str, Any]],
        identity_fields: tuple[str, ...],
        row_start: int,
    ) -> None:
        """Register generated identity keys at their global row positions."""

        if isinstance(row_start, bool) or not isinstance(row_start, int):
            raise GenerationContextIntegrityError(
                "Identity row_start must be a non-negative integer."
            )

        if row_start < 0:
            raise GenerationContextIntegrityError(
                "Identity row_start must be a non-negative integer."
            )

        if not identity_fields or not rows:
            return

        incoming = {
            row_start + offset: self._identity_key(
                row=row,
                identity_fields=identity_fields,
            )
            for offset, row in enumerate(rows)
        }

        self._register_identity_rows(
            entity_name=entity_name,
            identity_fields=identity_fields,
            incoming=incoming,
        )

    def restore_key_space(
        self,
        *,
        entity_name: str,
        identity_fields: tuple[str, ...],
        key_space: Mapping[int, tuple[Any, ...]] | Sequence[tuple[Any, ...]],
    ) -> None:
        """Restore identity keys with explicit or contiguous global positions.

        A mapping preserves sparse global row positions. An ordered sequence
        is interpreted as a contiguous range beginning at row zero.
        Unordered sets are deliberately rejected because they carry no
        reliable row-position information.
        """

        if not identity_fields:
            return

        if isinstance(key_space, Mapping):
            incoming = dict(key_space)
        elif (
            isinstance(key_space, Sequence)
            and not isinstance(key_space, (str, bytes, bytearray))
        ):
            incoming = {
                row_index: key
                for row_index, key in enumerate(key_space)
            }
        else:
            raise GenerationContextIntegrityError(
                "Identity key restoration requires a row-position mapping "
                "or an ordered sequence."
            )

        normalized: dict[int, tuple[Any, ...]] = {}

        for row_index, key in incoming.items():
            if (
                isinstance(row_index, bool)
                or not isinstance(row_index, int)
                or row_index < 0
            ):
                raise GenerationContextIntegrityError(
                    f"Invalid identity row position: {row_index!r}."
                )

            if not isinstance(key, tuple):
                raise GenerationContextIntegrityError(
                    f"Identity key at row {row_index} must be a tuple."
                )

            if len(key) != len(identity_fields):
                raise GenerationContextIntegrityError(
                    f"Identity key at row {row_index} has {len(key)} "
                    f"values; expected {len(identity_fields)}."
                )

            normalized[row_index] = key

        self._register_identity_rows(
            entity_name=entity_name,
            identity_fields=identity_fields,
            incoming=normalized,
        )

    def _register_identity_rows(
        self,
        *,
        entity_name: str,
        identity_fields: tuple[str, ...],
        incoming: Mapping[int, tuple[Any, ...]],
    ) -> None:
        """Validate a complete registration before mutating context state."""

        entity_positions = self.identity_keys_by_row.get(entity_name, {})
        existing_positions = entity_positions.get(identity_fields, {})

        entity_reverse = self.identity_row_by_key.get(entity_name, {})
        existing_reverse = entity_reverse.get(identity_fields, {})

        pending_positions: dict[int, tuple[Any, ...]] = {}
        pending_reverse: dict[tuple[Any, ...], int] = {}

        for row_index, key in incoming.items():
            try:
                hash(key)
            except TypeError as exc:
                raise GenerationContextIntegrityError(
                    f"Identity key at row {row_index} is not hashable."
                ) from exc

            existing_key = existing_positions.get(row_index)
            if existing_key is not None:
                if existing_key != key:
                    raise GenerationContextIntegrityError(
                        f"Conflicting identity at row {row_index} for "
                        f"{entity_name}{identity_fields}: "
                        f"{existing_key!r} versus {key!r}."
                    )
                continue

            pending_key = pending_positions.get(row_index)
            if pending_key is not None and pending_key != key:
                raise GenerationContextIntegrityError(
                    f"Conflicting identity registrations at row {row_index}."
                )

            existing_row = existing_reverse.get(key)
            if existing_row is not None and existing_row != row_index:
                raise GenerationContextIntegrityError(
                    f"Duplicate identity {key!r} for {entity_name}"
                    f"{identity_fields} at rows {existing_row} and {row_index}."
                )

            pending_row = pending_reverse.get(key)
            if pending_row is not None and pending_row != row_index:
                raise GenerationContextIntegrityError(
                    f"Duplicate identity {key!r} in incoming rows "
                    f"{pending_row} and {row_index}."
                )

            pending_positions[row_index] = key
            pending_reverse[key] = row_index

        if not pending_positions:
            return

        self.identity_keys_by_row.setdefault(
            entity_name,
            {},
        ).setdefault(
            identity_fields,
            {},
        ).update(pending_positions)

        self.identity_row_by_key.setdefault(
            entity_name,
            {},
        ).setdefault(
            identity_fields,
            {},
        ).update(pending_reverse)

    @staticmethod
    def _identity_key(
        *,
        row: dict[str, Any],
        identity_fields: tuple[str, ...],
    ) -> tuple[Any, ...]:
        try:
            return tuple(row[field] for field in identity_fields)
        except KeyError as exc:
            raise GenerationContextIntegrityError(
                f"Generated row is missing identity field {exc.args[0]!r}."
            ) from exc

    def get_key_space(
        self,
        *,
        entity_name: str,
        fields: tuple[str, ...],
    ) -> set[tuple[Any, ...]]:
        """Return the generated identity key space for an entity."""

        positions = self.identity_keys_by_row.get(
            entity_name,
            {},
        ).get(
            fields,
            {},
        )

        return set(positions.values())

    def get_identity_keys_by_row(
        self,
        *,
        entity_name: str,
        fields: tuple[str, ...],
    ) -> dict[int, tuple[Any, ...]]:
        """Return identity keys mapped to their original global row positions."""

        positions = self.identity_keys_by_row.get(
            entity_name,
            {},
        ).get(
            fields,
            {},
        )

        return dict(positions)

    def get_indexed_key_space(
        self,
        *,
        entity_name: str,
        fields: tuple[str, ...],
    ) -> list[tuple[Any, ...]]:
        """Return identity keys ordered by global row position."""

        positions = self.identity_keys_by_row.get(
            entity_name,
            {},
        ).get(
            fields,
            {},
        )

        return [
            positions[row_index]
            for row_index in sorted(positions)
        ]

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
