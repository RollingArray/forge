"""
Canonical parsing for FORGE relationship endpoints.

Supports legacy ENTITY.FIELD references and structured composite endpoints.
Field order is preserved because composite FK mappings are positional.
"""

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class RelationshipEndpoint:
    entity: str
    fields: tuple[str, ...]

    @property
    def is_composite(self) -> bool:
        return len(self.fields) > 1

    @property
    def reference(self) -> str:
        return f"{self.entity}." + ",".join(self.fields)


def parse_relationship_endpoint(
    value: Any,
    role: str,
) -> RelationshipEndpoint:
    """Parse a legacy or structured relationship endpoint."""

    if isinstance(value, str):
        reference = value.strip()

        if reference.count(".") != 1:
            raise ValueError(
                f"Relationship {role} must use ENTITY.FIELD notation."
            )

        entity, field = reference.split(".", 1)
        entity = entity.strip()
        field = field.strip()

        if not entity or not field:
            raise ValueError(
                f"Relationship {role} must identify a non-empty entity "
                "and field."
            )

        return RelationshipEndpoint(
            entity=entity,
            fields=(field,),
        )

    if isinstance(value, dict):
        entity = value.get("entity")
        fields = value.get("fields")

        if not isinstance(entity, str) or not entity.strip():
            raise ValueError(
                f"Relationship {role} endpoint must define a non-empty entity."
            )

        if not isinstance(fields, list) or not fields:
            raise ValueError(
                f"Relationship {role} endpoint must define a non-empty "
                "fields list."
            )

        normalized_fields: list[str] = []

        for field in fields:
            if not isinstance(field, str) or not field.strip():
                raise ValueError(
                    f"Relationship {role} endpoint fields must be "
                    "non-empty strings."
                )

            normalized_fields.append(field.strip())

        if len(normalized_fields) != len(set(normalized_fields)):
            raise ValueError(
                f"Relationship {role} endpoint contains duplicate fields."
            )

        return RelationshipEndpoint(
            entity=entity.strip(),
            fields=tuple(normalized_fields),
        )

    raise ValueError(
        f"Relationship {role} endpoint must be a string or an object "
        "containing entity and fields."
    )


@dataclass(frozen=True)
class ForeignKeyMapping:
    """Canonical, ordered representation of a foreign-key mapping."""

    name: str
    child_entity: str
    child_fields: tuple[str, ...]
    parent_entity: str
    parent_fields: tuple[str, ...]


@dataclass(frozen=True)
class RelationshipResolution:
    """Result of resolving one relationship against declared foreign keys."""

    status: str
    source: RelationshipEndpoint | None
    target: RelationshipEndpoint | None
    relationship_type: str
    source_participation: str
    target_participation: str
    foreign_key: ForeignKeyMapping | None = None
    direction: str | None = None
    child_entity: str | None = None
    parent_entity: str | None = None
    reason: str | None = None
    diagnostic_code: str | None = None

    @property
    def is_mapped(self) -> bool:
        return self.status == "MAPPED"


def normalize_foreign_key_mappings(
    foreign_keys: Any,
) -> tuple[ForeignKeyMapping, ...]:
    """Normalize raw specification FK declarations.

    This function validates the mapping structure and ordered field lists.
    Entity and field existence, identity compatibility, and other
    specification-level rules remain the responsibility of their existing
    validators.
    """

    if foreign_keys is None:
        return ()

    if not isinstance(foreign_keys, list):
        raise ValueError("Foreign keys must be a list.")

    mappings: list[ForeignKeyMapping] = []

    for index, foreign_key in enumerate(foreign_keys, start=1):
        label = f"foreign_key_{index}"

        if not isinstance(foreign_key, dict):
            raise ValueError(f"{label} must be an object.")

        name = foreign_key.get("name", label)
        if not isinstance(name, str) or not name.strip():
            raise ValueError(f"{label} must have a non-empty name.")

        source = foreign_key.get("source")
        target = foreign_key.get("target")

        if not isinstance(source, dict) or not isinstance(target, dict):
            raise ValueError(
                f"Foreign key {name!r} source and target must be objects."
            )

        child_entity = source.get("entity")
        parent_entity = target.get("entity")
        child_fields = source.get("fields")
        parent_fields = target.get("fields")

        if (
            not isinstance(child_entity, str)
            or not child_entity.strip()
            or not isinstance(parent_entity, str)
            or not parent_entity.strip()
        ):
            raise ValueError(
                f"Foreign key {name!r} must identify non-empty source "
                "and target entities."
            )

        if (
            not isinstance(child_fields, list)
            or not isinstance(parent_fields, list)
            or not child_fields
            or len(child_fields) != len(parent_fields)
        ):
            raise ValueError(
                f"Foreign key {name!r} must have non-empty, equally sized "
                "source and target field lists."
            )

        if any(
            not isinstance(field, str) or not field.strip()
            for field in child_fields + parent_fields
        ):
            raise ValueError(
                f"Foreign key {name!r} fields must be non-empty strings."
            )

        normalized_child_fields = tuple(
            field.strip() for field in child_fields
        )
        normalized_parent_fields = tuple(
            field.strip() for field in parent_fields
        )

        if (
            len(set(normalized_child_fields)) != len(normalized_child_fields)
            or len(set(normalized_parent_fields)) != len(normalized_parent_fields)
        ):
            raise ValueError(
                f"Foreign key {name!r} contains duplicate fields."
            )

        mappings.append(
            ForeignKeyMapping(
                name=name.strip(),
                child_entity=child_entity.strip(),
                child_fields=normalized_child_fields,
                parent_entity=parent_entity.strip(),
                parent_fields=normalized_parent_fields,
            )
        )

    return tuple(mappings)


def resolve_relationship_mapping(
    relationship: Any,
    foreign_keys: tuple[ForeignKeyMapping, ...],
) -> RelationshipResolution:
    """Resolve one relationship using exact ordered FK endpoint mappings.

    Direction is defined relative to the relationship declaration:
      FORWARD: FK child is relationship source.
      REVERSE: FK child is relationship target.

    ONE_TO_MANY requires REVERSE direction.
    MANY_TO_ONE requires FORWARD direction.
    ONE_TO_ONE accepts either direction.
    Direct MANY_TO_MANY remains unsupported until an explicit association
    mapping contract is introduced.
    """

    if not isinstance(relationship, dict):
        return RelationshipResolution(
            status="INVALID",
            source=None,
            target=None,
            relationship_type="UNKNOWN",
            source_participation="MANDATORY",
            target_participation="MANDATORY",
            reason="Relationship must be an object.",
            diagnostic_code="INVALID_RELATIONSHIP",
        )

    relationship_type = str(
        relationship.get("type", "UNKNOWN")
    ).strip().upper()

    source_participation = str(
        relationship.get("source_participation", "MANDATORY")
    ).strip().upper()
    target_participation = str(
        relationship.get("target_participation", "MANDATORY")
    ).strip().upper()

    source: RelationshipEndpoint | None = None
    target: RelationshipEndpoint | None = None

    try:
        source = parse_relationship_endpoint(
            relationship.get("source"), "source"
        )
        target = parse_relationship_endpoint(
            relationship.get("target"), "target"
        )
    except ValueError as exc:
        return RelationshipResolution(
            status="INVALID",
            source=source,
            target=target,
            relationship_type=relationship_type,
            source_participation=source_participation,
            target_participation=target_participation,
            reason=str(exc),
            diagnostic_code="INVALID_RELATIONSHIP_ENDPOINT",
        )

    if (
        source_participation not in {"MANDATORY", "OPTIONAL"}
        or target_participation not in {"MANDATORY", "OPTIONAL"}
    ):
        return RelationshipResolution(
            status="INVALID",
            source=source,
            target=target,
            relationship_type=relationship_type,
            source_participation=source_participation,
            target_participation=target_participation,
            reason="Participation must be MANDATORY or OPTIONAL.",
            diagnostic_code="INVALID_RELATIONSHIP_PARTICIPATION",
        )

    if relationship_type == "MANY_TO_MANY":
        return RelationshipResolution(
            status="UNSUPPORTED",
            source=source,
            target=target,
            relationship_type=relationship_type,
            source_participation=source_participation,
            target_participation=target_participation,
            reason=(
                "Direct MANY_TO_MANY declarations do not identify an "
                "association mapping."
            ),
            diagnostic_code="UNSUPPORTED_MANY_TO_MANY",
        )

    if relationship_type not in {"ONE_TO_ONE", "ONE_TO_MANY", "MANY_TO_ONE"}:
        return RelationshipResolution(
            status="UNSUPPORTED",
            source=source,
            target=target,
            relationship_type=relationship_type,
            source_participation=source_participation,
            target_participation=target_participation,
            reason=f"Unsupported relationship type: {relationship_type}.",
            diagnostic_code="UNSUPPORTED_RELATIONSHIP_TYPE",
        )

    matching: list[tuple[ForeignKeyMapping, str]] = []
    partial_composite = False

    for foreign_key in foreign_keys:
        forward = (
            foreign_key.child_entity == source.entity
            and foreign_key.child_fields == source.fields
            and foreign_key.parent_entity == target.entity
            and foreign_key.parent_fields == target.fields
        )
        reverse = (
            foreign_key.child_entity == target.entity
            and foreign_key.child_fields == target.fields
            and foreign_key.parent_entity == source.entity
            and foreign_key.parent_fields == source.fields
        )

        if forward:
            matching.append((foreign_key, "FORWARD"))
        elif reverse:
            matching.append((foreign_key, "REVERSE"))
        elif (
            foreign_key.child_entity == source.entity
            and foreign_key.parent_entity == target.entity
            and bool(set(source.fields) & set(foreign_key.child_fields))
            and bool(set(target.fields) & set(foreign_key.parent_fields))
        ) or (
            foreign_key.child_entity == target.entity
            and foreign_key.parent_entity == source.entity
            and bool(set(target.fields) & set(foreign_key.child_fields))
            and bool(set(source.fields) & set(foreign_key.parent_fields))
        ):
            partial_composite = True

    expected_direction = {
        "ONE_TO_ONE": None,
        "ONE_TO_MANY": "REVERSE",
        "MANY_TO_ONE": "FORWARD",
    }[relationship_type]

    compatible = [
        (foreign_key, direction)
        for foreign_key, direction in matching
        if expected_direction is None or direction == expected_direction
    ]

    if len(compatible) != 1:
        if len(compatible) > 1:
            reason = "Multiple compatible foreign keys match this relationship."
            code = "AMBIGUOUS_RELATIONSHIP_MAPPING"
        elif partial_composite:
            reason = (
                "Relationship endpoints match only part of a composite "
                "foreign key."
            )
            code = "PARTIAL_COMPOSITE_RELATIONSHIP_MAPPING"
        elif matching:
            reason = (
                "Matching foreign keys exist, but their direction conflicts "
                "with the declared cardinality."
            )
            code = "RELATIONSHIP_DIRECTION_MISMATCH"
        else:
            reason = (
                "A complete ordered foreign key mapping in the expected "
                "direction could not be established."
            )
            code = "RELATIONSHIP_FK_NOT_FOUND"

        return RelationshipResolution(
            status="UNMAPPED",
            source=source,
            target=target,
            relationship_type=relationship_type,
            source_participation=source_participation,
            target_participation=target_participation,
            reason=reason,
            diagnostic_code=code,
        )

    foreign_key, direction = compatible[0]
    child_entity = (
        source.entity if direction == "FORWARD" else target.entity
    )
    parent_entity = (
        target.entity if direction == "FORWARD" else source.entity
    )

    return RelationshipResolution(
        status="MAPPED",
        source=source,
        target=target,
        relationship_type=relationship_type,
        source_participation=source_participation,
        target_participation=target_participation,
        foreign_key=foreign_key,
        direction=direction,
        child_entity=child_entity,
        parent_entity=parent_entity,
        reason=(
            "Complete ordered FK mapping matches the declared relationship. "
            "Row-level cardinality and participation require generation-time "
            "verification."
        ),
    )
