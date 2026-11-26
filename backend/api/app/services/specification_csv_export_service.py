"""Export a canonical FORGE specification into the five editable CSV sections."""

import csv
import io
import json
from collections.abc import Mapping

from app.services.relationship_endpoint import parse_relationship_endpoint
from typing import Any


class SpecificationCsvExportService:
    """Convert canonical specification JSON into editable CSV sections.

    The exporter is read-only. It does not modify the supplied specification.

    JSON-valued columns are deliberately used where flattening would lose
    information, including relationship endpoints, foreign-key field mappings,
    constraint values, and generation parameters.
    """

    SECTION_HEADERS = {
        "entities": (
            "entity",
            "description",
            "population_count",
            "population_scaling",
        ),
        "fields_and_keys": (
            "entity",
            "field",
            "type",
            "identity_position",
            "identity_strategy",
            "generation_strategy",
            "distribution",
            "generator",
            "minimum",
            "maximum",
            "minimum_length",
            "maximum_length",
            "character_set",
            "pattern",
            "semantic_description",
            "semantic_mode",
            "values",
        ),
        "foreign_keys": (
            "source_entity",
            "source_fields",
            "target_entity",
        ),
        "relationships": (
            "source_entity",
            "target_entity",
            "type",
            "source_participation",
            "target_participation",
        ),
        "constraints": (
            "entity",
            "field",
            "operator",
            "value",
        ),
    }

    GENERATION_PARAMETER_COLUMNS = (
        "minimum",
        "maximum",
        "minimum_length",
        "maximum_length",
        "character_set",
        "pattern",
        "values",
    )

    def export(self, specification: Mapping[str, Any]) -> dict[str, str]:
        """Return CSV text for all five sections."""
        if not isinstance(specification, Mapping):
            raise ValueError("Specification must be a JSON object.")

        sections = {
            "entities": self._export_entities(specification),
            "fields_and_keys": self._export_fields(specification),
            "foreign_keys": self._export_foreign_keys(specification),
            "relationships": self._export_relationships(specification),
            "constraints": self._export_constraints(specification),
        }
        return {
            section: self._to_csv(section, rows)
            for section, rows in sections.items()
        }

    def _export_entities(self, specification: Mapping[str, Any]) -> list[dict]:
        entities = self._collection(specification, "entities")
        rows = []

        for entity in entities:
            population = entity.get("population") or {}
            if not isinstance(population, Mapping):
                raise ValueError(
                    f"Entity {entity.get('name')!r} has invalid population data."
                )

            rows.append({
                "entity": self._text(entity.get("name")),
                "description": self._text(entity.get("description")),
                "population_count": self._text(population.get("count")),
                "population_scaling": self._text(population.get("scaling")),
            })

        return rows

    def _export_fields(self, specification: Mapping[str, Any]) -> list[dict]:
        entities = self._collection(specification, "entities")
        rows = []

        for entity in entities:
            entity_name = self._text(entity.get("name"))
            identity = entity.get("identity") or {}
            if not isinstance(identity, Mapping):
                raise ValueError(
                    f"Entity {entity_name!r} has invalid identity data."
                )

            identity_fields = identity.get("fields") or []
            if not isinstance(identity_fields, list):
                raise ValueError(
                    f"Entity {entity_name!r} identity.fields must be a list."
                )

            identity_positions = {
                field_name: position
                for position, field_name in enumerate(identity_fields, start=1)
            }

            fields = entity.get("fields") or []
            if not isinstance(fields, list):
                raise ValueError(
                    f"Entity {entity_name!r} fields must be a list."
                )

            for field in fields:
                if not isinstance(field, Mapping):
                    raise ValueError(
                        f"Entity {entity_name!r} contains a non-object field."
                    )

                field_name = self._text(field.get("name"))
                generation = field.get("generation") or {}
                if not isinstance(generation, Mapping):
                    raise ValueError(
                        f"Field {entity_name}.{field_name} has invalid generation data."
                    )

                parameters = generation.get("parameters") or {}
                if not isinstance(parameters, Mapping):
                    raise ValueError(
                        f"Field {entity_name}.{field_name} generation.parameters "
                        "must be an object."
                    )

                row = {
                    "entity": entity_name,
                    "field": field_name,
                    "type": self._text(field.get("type")),
                    "identity_position": self._text(
                        identity_positions.get(field_name)
                    ),
                    "identity_strategy": self._text(
                        (field.get("identity") or {}).get("strategy")
                        if isinstance(field.get("identity") or {}, Mapping)
                        else None
                    ),
                    "generation_strategy": self._text(generation.get("strategy")),
                    "distribution": self._text(generation.get("distribution")),
                    "generator": self._text(generation.get("generator")),
                }

                for column in self.GENERATION_PARAMETER_COLUMNS:
                    value = parameters.get(column)
                    if column == "values" and value is not None:
                        row[column] = self._json(value)
                    else:
                        row[column] = self._text(value)

                row["semantic_description"] = self._text(
                    parameters.get("description")
                )
                row["semantic_mode"] = self._text(parameters.get("mode"))

                rows.append(row)

        return rows

    def _export_foreign_keys(
        self, specification: Mapping[str, Any]
    ) -> list[dict]:
        rows = []

        for foreign_key in self._collection(specification, "foreign_keys"):
            source = foreign_key.get("source") or {}
            target = foreign_key.get("target") or {}

            if not isinstance(source, Mapping) or not isinstance(target, Mapping):
                raise ValueError("Foreign-key source and target must be objects.")

            source_fields = source.get("fields", [])
            if not isinstance(source_fields, list):
                raise ValueError("Foreign-key source fields must be a list.")

            rows.append({
                "source_entity": self._text(source.get("entity")),
                "source_fields": self._json(source_fields),
                "target_entity": self._text(target.get("entity")),
            })

        return rows

    def _export_relationships(
        self, specification: Mapping[str, Any]
    ) -> list[dict]:
        rows = []

        def endpoint_entity(value: Any, role: str) -> str:
            if isinstance(value, Mapping):
                entity = value.get("entity")
                if not isinstance(entity, str) or not entity.strip():
                    raise ValueError(
                        f"Relationship {role} endpoint has no entity."
                    )
                return entity.strip()

            if isinstance(value, str):
                value = value.strip()
                if not value:
                    raise ValueError(
                        f"Relationship {role} endpoint has no entity."
                    )
                if "." in value:
                    return parse_relationship_endpoint(value, role).entity
                return value

            raise ValueError(
                f"Relationship {role} endpoint must identify an entity."
            )

        for relationship in self._collection(specification, "relationships"):
            rows.append({
                "source_entity": endpoint_entity(
                    relationship.get("source"), "source"
                ),
                "target_entity": endpoint_entity(
                    relationship.get("target"), "target"
                ),
                "type": self._text(relationship.get("type")),
                "source_participation": self._text(
                    relationship.get("source_participation")
                ),
                "target_participation": self._text(
                    relationship.get("target_participation")
                ),
            })

        return rows

    def _export_constraints(
        self, specification: Mapping[str, Any]
    ) -> list[dict]:
        rows = []

        for constraint in self._collection(specification, "constraints"):
            value = constraint.get("value")

            if isinstance(value, (dict, list)):
                raise ValueError(
                    "Constraint values containing objects or arrays cannot "
                    "be represented in the original CSV format."
                )

            rows.append({
                "entity": self._text(constraint.get("entity")),
                "field": self._text(constraint.get("field")),
                "operator": self._text(constraint.get("operator")),
                "value": "" if value is None else str(value),
            })

        return rows

    def _collection(
        self, specification: Mapping[str, Any], section: str
    ) -> list[Mapping[str, Any]]:
        value = specification.get(section, [])
        if value is None:
            return []
        if not isinstance(value, list):
            raise ValueError(f"Specification section {section!r} must be a list.")

        for index, item in enumerate(value):
            if not isinstance(item, Mapping):
                raise ValueError(
                    f"Specification section {section!r} item {index} "
                    "must be an object."
                )

        return value

    def _to_csv(self, section: str, rows: list[dict]) -> str:
        output = io.StringIO(newline="")
        writer = csv.DictWriter(
            output,
            fieldnames=self.SECTION_HEADERS[section],
            extrasaction="ignore",
            lineterminator="\n",
        )
        writer.writeheader()
        writer.writerows(rows)
        return output.getvalue()

    @staticmethod
    def _text(value: Any) -> str:
        if value is None:
            return ""
        if isinstance(value, bool):
            return "true" if value else "false"
        return str(value)

    @staticmethod
    def _json(value: Any) -> str:
        return json.dumps(
            value,
            ensure_ascii=False,
            separators=(",", ":"),
            allow_nan=False,
        )
