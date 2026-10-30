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
