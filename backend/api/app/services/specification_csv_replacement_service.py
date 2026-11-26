"""Build a complete replacement specification from the five wizard CSVs."""

from __future__ import annotations

import copy
import json
from typing import Any

from app.services.specification_csv_export_service import (
    SpecificationCsvExportService,
)
from app.services.specification_csv_parser import SpecificationCsvParser
from app.services.relationship_endpoint import (
    normalize_foreign_key_mappings,
    resolve_relationship_mapping,
)


class SpecificationCsvReplacementService:
    """Convert edited wizard CSV sections into a canonical specification.

    Unlike the additive importer, this service treats the five CSV sections
    as the complete desired state. Rows omitted from a section are deleted.

    Existing metadata that is not represented in CSV is retained for matching
    entities and fields. Top-level sections outside the five CSV sections are
    preserved unchanged.
    """

    SECTIONS = (
        "entities",
        "fields_and_keys",
        "foreign_keys",
        "relationships",
        "constraints",
    )

    REQUIRED_HEADERS = {
        "entities": ("entity",),
        "fields_and_keys": ("entity", "field", "type"),
        "foreign_keys": (
            "source_entity", "source_fields", "target_entity",
        ),
        "relationships": (
            "source_entity",
            "target_entity",
            "type",
            "source_participation",
            "target_participation",
        ),
        "constraints": (
            "entity", "field", "operator", "value",
        ),
    }

    PARAMETER_COLUMNS = {
        "minimum": "minimum",
        "maximum": "maximum",
        "minimum_length": "minimum_length",
        "maximum_length": "maximum_length",
        "character_set": "character_set",
        "pattern": "pattern",
        "values": "values",
        "semantic_description": "description",
        "semantic_mode": "mode",
    }

    def __init__(self, csv_parser: SpecificationCsvParser | None = None):
        self._parser = csv_parser or SpecificationCsvParser()
        self._headers = SpecificationCsvExportService.SECTION_HEADERS

    def convert(
        self,
        csv_sections: dict[str, str],
        existing_specification: dict[str, Any],
    ) -> dict[str, Any]:
        """Return a candidate specification and structured conversion issues."""
        if not isinstance(existing_specification, dict):
            raise ValueError("Existing specification must be a JSON object.")

        parsed: dict[str, Any] = {}
        issues: list[dict[str, Any]] = []

        for section in self.SECTIONS:
            content = csv_sections.get(section, "")
            if not isinstance(content, str) or not content.strip():
                issues.append({
                    "section": section,
                    "row": None,
                    "column": None,
                    "message": (
                        "This replacement section is required and must "
                        "include its CSV header, even when it has no rows."
                    ),
                })
                continue

            result = self._parser.parse_section(
                section=section,
                content=content,
                expected_headers=self._headers[section],
                required_headers=self.REQUIRED_HEADERS[section],
            )
            parsed[section] = result
            for error in result.get("errors", []):
                issues.append({
                    "section": section,
                    "row": error.get("row"),
                    "column": error.get("column"),
                    "message": error.get("message", "Invalid CSV input."),
                })

        if issues:
            return {"specification": None, "issues": issues}

        candidate = copy.deepcopy(existing_specification)

        try:
            entities, entity_lookup = self._convert_entities(
                parsed["entities"], existing_specification
            )
            self._convert_fields(
                parsed["fields_and_keys"],
                entities,
                entity_lookup,
                existing_specification,
            )
            candidate["entities"] = entities
            candidate["foreign_keys"] = self._convert_foreign_keys(
                parsed["foreign_keys"],
                entities,
                existing_specification.get("foreign_keys", []),
            )
            candidate["relationships"] = self._convert_relationships(
                parsed["relationships"],
                candidate["foreign_keys"],
                existing_specification.get("relationships", []),
            )
            candidate["constraints"] = self._convert_constraints(
                parsed["constraints"],
                existing_specification.get("constraints", []),
            )
        except ValueError as exc:
            issues.append({
                "section": "fields_and_keys",
                "row": None,
                "column": None,
                "message": str(exc),
            })
            return {"specification": None, "issues": issues}

        return {"specification": candidate, "issues": []}

    def _convert_entities(
        self,
        parsed: dict[str, Any],
        existing: dict[str, Any],
    ) -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]]]:
        old_entities = {
            item.get("name"): item
            for item in existing.get("entities", [])
            if isinstance(item, dict) and isinstance(item.get("name"), str)
        }

        entities: list[dict[str, Any]] = []
        lookup: dict[str, dict[str, Any]] = {}

        for row in parsed["rows"]:
            values = row["values"]
            name = values.get("entity", "").strip()
            if not name:
                raise ValueError(
                    f"Entities row {row['row_number']}: entity name is required."
                )
            if name in lookup:
                raise ValueError(f"Duplicate entity row: {name!r}.")

            old = old_entities.get(name, {})
            entity = copy.deepcopy(old)
            entity["name"] = name

            description = values.get("description", "")
            if description:
                entity["description"] = description
            elif entity.get("description") == "":
                pass
            else:
                entity.pop("description", None)

            population = entity.get("population")
            if not isinstance(population, dict):
                population = {}

            count_text = values.get("population_count", "").strip()
            scaling_text = values.get("population_scaling", "").strip()

            if count_text:
                try:
                    count = int(count_text)
                except ValueError as exc:
                    raise ValueError(
                        f"Entities row {row['row_number']}: "
                        "population_count must be a whole number."
                    ) from exc
                if count < 0:
                    raise ValueError(
                        f"Entities row {row['row_number']}: "
                        "population_count cannot be negative."
                    )
                population["count"] = count
            else:
                population.pop("count", None)

            if scaling_text:
                scaling = scaling_text.upper()
                if scaling not in {"FIXED", "SCALABLE"}:
                    raise ValueError(
                        f"Entities row {row['row_number']}: "
                        "population_scaling must be FIXED or SCALABLE."
                    )
                population["scaling"] = scaling
            else:
                population.pop("scaling", None)

            if population or "population" in old:
                entity["population"] = population
            else:
                entity.pop("population", None)

            # Rebuild CSV-managed field and identity content below.
            entity["fields"] = []
            identity = entity.get("identity")
            entity["identity"] = (
                copy.deepcopy(identity) if isinstance(identity, dict) else {}
            )
            entity["identity"]["fields"] = []

            entities.append(entity)
            lookup[name] = entity

        return entities, lookup

    def _convert_fields(
        self,
        parsed: dict[str, Any],
        entities: list[dict[str, Any]],
        entity_lookup: dict[str, dict[str, Any]],
        existing_specification: dict[str, Any],
    ) -> None:
        # Read prior field metadata from the untouched source specification.
        old_fields_by_entity: dict[str, dict[str, dict[str, Any]]] = {}
        for old_entity in existing_specification.get("entities", []):
            if not isinstance(old_entity, dict):
                continue
            entity_name = old_entity.get("name")
            if not isinstance(entity_name, str):
                continue
            old_fields_by_entity[entity_name] = {
                item.get("name"): item
                for item in old_entity.get("fields", [])
                if isinstance(item, dict) and isinstance(item.get("name"), str)
            }

        positions: dict[str, list[tuple[int, str]]] = {
            name: [] for name in entity_lookup
        }
        seen_fields: set[tuple[str, str]] = set()

        for row in parsed["rows"]:
            values = row["values"]
            number = row["row_number"]
            entity_name = values.get("entity", "").strip()
            field_name = values.get("field", "").strip()
            field_type = values.get("type", "").strip().upper()

            if entity_name not in entity_lookup:
                raise ValueError(
                    f"Fields row {number}: unknown entity {entity_name!r}."
                )
            if not field_name:
                raise ValueError(f"Fields row {number}: field name is required.")
            key = (entity_name, field_name)
            if key in seen_fields:
                raise ValueError(
                    f"Fields row {number}: duplicate field "
                    f"{entity_name}.{field_name}."
                )
            seen_fields.add(key)

            old_field = old_fields_by_entity.get(entity_name, {}).get(field_name, {})
            field = copy.deepcopy(old_field)
            field["name"] = field_name
            field["type"] = field_type

            identity_strategy = values.get("identity_strategy", "").strip()
            identity = field.get("identity")
            identity = copy.deepcopy(identity) if isinstance(identity, dict) else {}
            if identity_strategy:
                identity["strategy"] = identity_strategy.upper()
            else:
                identity.pop("strategy", None)
            if identity:
                field["identity"] = identity
            else:
                field.pop("identity", None)

            generation = self._convert_generation(
                values, old_field, number, field_type
            )
            if generation:
                field["generation"] = generation
            else:
                field.pop("generation", None)

            entity_lookup[entity_name]["fields"].append(field)

            position_text = values.get("identity_position", "").strip()
            if position_text:
                try:
                    position = int(position_text)
                except ValueError as exc:
                    raise ValueError(
                        f"Fields row {number}: identity_position "
                        "must be a positive whole number."
                    ) from exc
                if position < 1:
                    raise ValueError(
                        f"Fields row {number}: identity_position must be at least 1."
                    )
                positions[entity_name].append((position, field_name))

        for entity_name, entity in entity_lookup.items():
            ordered = sorted(positions[entity_name])
            numeric_positions = [position for position, _ in ordered]
            if len(numeric_positions) != len(set(numeric_positions)):
                raise ValueError(
                    f"Entity {entity_name!r} has duplicate identity positions."
                )
            if numeric_positions and numeric_positions != list(
                range(1, len(numeric_positions) + 1)
            ):
                raise ValueError(
                    f"Entity {entity_name!r} identity positions must be "
                    "contiguous starting at 1."
                )
            entity["identity"]["fields"] = [
                field_name for _, field_name in ordered
            ]

    def _convert_generation(
        self,
        values: dict[str, str],
        old_field: dict[str, Any],
        row_number: int,
        field_type: str,
    ) -> dict[str, Any]:
        old_generation = old_field.get("generation")
        generation = (
            copy.deepcopy(old_generation)
            if isinstance(old_generation, dict)
            else {}
        )

        old_parameters = generation.get("parameters")
        parameters = (
            copy.deepcopy(old_parameters)
            if isinstance(old_parameters, dict)
            else {}
        )

        for column, parameter in self.PARAMETER_COLUMNS.items():
            text = values.get(column, "").strip()
            if not text:
                parameters.pop(parameter, None)
                continue

            if column in {"values"}:
                try:
                    value = json.loads(text)
                except json.JSONDecodeError as exc:
                    raise ValueError(
                        f"Fields row {row_number}: {column} must be valid JSON."
                    ) from exc
                if not isinstance(value, list):
                    raise ValueError(
                        f"Fields row {row_number}: {column} must be a JSON array."
                    )
            elif column in {
                "minimum_length", "maximum_length", "precision", "scale"
            }:
                try:
                    value = int(text)
                except ValueError as exc:
                    raise ValueError(
                        f"Fields row {row_number}: {column} must be an integer."
                    ) from exc
            elif column in {"minimum", "maximum"}:
                if field_type == "INTEGER":
                    try:
                        value = int(text)
                    except ValueError as exc:
                        raise ValueError(
                            f"Fields row {row_number}: {column} "
                            "must be a whole number for INTEGER fields."
                        ) from exc
                else:
                    # DECIMAL bounds must remain strings to preserve precision.
                    value = text
            else:
                value = text

            parameters[parameter] = value

        for column, key in (
            ("generation_strategy", "strategy"),
            ("distribution", "distribution"),
            ("generator", "generator"),
        ):
            text = values.get(column, "").strip()
            if text:
                generation[key] = text.upper()
            else:
                generation.pop(key, None)

        if parameters:
            generation["parameters"] = parameters
        elif "parameters" in generation:
            generation.pop("parameters", None)

        return generation

    def _convert_foreign_keys(
        self,
        parsed: dict[str, Any],
        entities: list[dict[str, Any]],
        existing: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        entity_lookup = {
            entity.get("name"): entity
            for entity in entities
            if isinstance(entity, dict)
        }

        old_by_key: dict[str, list[dict[str, Any]]] = {}
        for item in existing:
            if not isinstance(item, dict):
                continue
            source = item.get("source") or {}
            target = item.get("target") or {}
            if not isinstance(source, dict) or not isinstance(target, dict):
                continue

            key = SpecificationCsvReplacementService._record_key([
                source.get("entity"),
                source.get("fields", []),
                target.get("entity"),
            ])
            old_by_key.setdefault(key, []).append(item)

        result = []

        for row in parsed["rows"]:
            values = row["values"]
            number = row["row_number"]

            source_entity = values.get("source_entity", "").strip()
            target_entity = values.get("target_entity", "").strip()

            source_fields = self._json_value(
                values.get("source_fields", ""),
                "source_fields",
                number,
            )

            if (
                not isinstance(source_fields, list)
                or not source_fields
                or any(not isinstance(field, str) or not field.strip()
                       for field in source_fields)
            ):
                raise ValueError(
                    f"Foreign keys row {number}: source_fields must be "
                    "a non-empty JSON array of field names."
                )

            key = SpecificationCsvReplacementService._record_key([
                source_entity, source_fields, target_entity
            ])
            matches = old_by_key.get(key, [])

            # A deleted entity removes its dependent existing FK. Do not
            # silently discard a genuinely new declaration with an unknown
            # entity name.
            source_exists = source_entity in entity_lookup
            target_exists = target_entity in entity_lookup

            if not source_exists or not target_exists:
                existing_pair = [
                    item for item in existing
                    if isinstance(item, dict)
                    and (item.get("source") or {}).get("entity") == source_entity
                    and (item.get("target") or {}).get("entity") == target_entity
                ]
                if existing_pair:
                    continue
                raise ValueError(
                    f"Foreign keys row {number}: unknown source or target "
                    f"entity ({source_entity!r}, {target_entity!r})."
                )

            if len(matches) > 1:
                raise ValueError(
                    f"Foreign keys row {number}: multiple existing foreign "
                    "keys match this legacy declaration. The original CSV "
                    "format cannot distinguish them."
                )

            old = matches[0] if matches else {}
            old_source = old.get("source") or {}
            old_target = old.get("target") or {}

            target = entity_lookup[target_entity]
            identity = target.get("identity") or {}
            identity_fields = (
                identity.get("fields")
                if isinstance(identity, dict)
                else None
            )

            old_target_fields = (
                old_target.get("fields")
                if isinstance(old_target, dict)
                else None
            )

            # Prefer the current identity when it has a compatible arity.
            # Otherwise retain the old explicit mapping for an unchanged FK.
            if (
                isinstance(identity_fields, list)
                and identity_fields
                and len(identity_fields) == len(source_fields)
            ):
                target_fields = list(identity_fields)
            elif (
                isinstance(old_target_fields, list)
                and len(old_target_fields) == len(source_fields)
            ):
                target_fields = list(old_target_fields)
            else:
                raise ValueError(
                    f"Foreign keys row {number}: cannot derive a compatible "
                    f"target-field mapping for {target_entity!r}. "
                    "The target identity and existing FK mapping do not "
                    "provide a matching number of fields."
                )

            record_metadata = {
                name: value for name, value in old.items()
                if name not in {"name", "source", "target"}
            }
            source_metadata = {
                name: value for name, value in old_source.items()
                if name not in {"entity", "fields"}
            } if isinstance(old_source, dict) else {}
            target_metadata = {
                name: value for name, value in old_target.items()
                if name not in {"entity", "fields"}
            } if isinstance(old_target, dict) else {}

            name = old.get("name") or (
                f"FK_{source_entity}_{'_'.join(source_fields)}_{target_entity}"
            )

            source_record = copy.deepcopy(source_metadata)
            source_record.update({
                "entity": source_entity,
                "fields": source_fields,
            })

            target_record = copy.deepcopy(target_metadata)
            target_record.update({
                "entity": target_entity,
                "fields": target_fields,
            })

            foreign_key = copy.deepcopy(record_metadata)
            foreign_key.update({
                "name": name,
                "source": source_record,
                "target": target_record,
            })
            result.append(foreign_key)

        return result

    def _record_key(values: list[Any]) -> str:
        return json.dumps(
            values,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        )

    def _convert_relationships(
        self,
        parsed: dict[str, Any],
        foreign_keys: list[dict[str, Any]],
        existing: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        mappings = normalize_foreign_key_mappings(foreign_keys)
        result = []

        for row in parsed["rows"]:
            values = row["values"]
            number = row["row_number"]

            source_entity = values.get("source_entity", "").strip()
            target_entity = values.get("target_entity", "").strip()
            relationship_type = values.get("type", "").strip().upper()
            source_participation = (
                values.get("source_participation", "").strip().upper()
                or "MANDATORY"
            )
            target_participation = (
                values.get("target_participation", "").strip().upper()
                or "MANDATORY"
            )

            def existing_endpoint_entity(endpoint):
                if isinstance(endpoint, dict):
                    return endpoint.get("entity")
                if isinstance(endpoint, str):
                    return endpoint.split(".", 1)[0]
                return None

            unchanged_matches = [
                old for old in existing
                if isinstance(old, dict)
                and existing_endpoint_entity(old.get("source")) == source_entity
                and existing_endpoint_entity(old.get("target")) == target_entity
                and old.get("type") == relationship_type
                and old.get("source_participation", "MANDATORY")
                    == source_participation
                and old.get("target_participation", "MANDATORY")
                    == target_participation
            ]

            if len(unchanged_matches) == 1:
                result.append(copy.deepcopy(unchanged_matches[0]))
                continue

            if len(unchanged_matches) > 1:
                raise ValueError(
                    f"Relationships row {number}: multiple existing "
                    "relationships match this declaration."
                )

            if relationship_type not in {
                "ONE_TO_ONE", "ONE_TO_MANY", "MANY_TO_ONE"
            }:
                raise ValueError(
                    f"Relationships row {number}: unsupported relationship "
                    f"type {relationship_type!r}. A new or edited "
                    "relationship of this type cannot be reconstructed "
                    "from the original CSV format."
                )

            if relationship_type == "MANY_TO_ONE":
                expected = [
                    fk for fk in mappings
                    if fk.child_entity == source_entity
                    and fk.parent_entity == target_entity
                ]
            elif relationship_type == "ONE_TO_MANY":
                expected = [
                    fk for fk in mappings
                    if fk.child_entity == target_entity
                    and fk.parent_entity == source_entity
                ]
            else:
                expected = [
                    fk for fk in mappings
                    if (
                        fk.child_entity == source_entity
                        and fk.parent_entity == target_entity
                    ) or (
                        fk.child_entity == target_entity
                        and fk.parent_entity == source_entity
                    )
                ]

            resolved = []

            for fk in expected:
                forward = fk.child_entity == source_entity
                if forward:
                    source_endpoint = {
                        "entity": fk.child_entity,
                        "fields": list(fk.child_fields),
                    }
                    target_endpoint = {
                        "entity": fk.parent_entity,
                        "fields": list(fk.parent_fields),
                    }
                else:
                    source_endpoint = {
                        "entity": fk.parent_entity,
                        "fields": list(fk.parent_fields),
                    }
                    target_endpoint = {
                        "entity": fk.child_entity,
                        "fields": list(fk.child_fields),
                    }

                candidate = {
                    "source": source_endpoint,
                    "target": target_endpoint,
                    "type": relationship_type,
                    "source_participation": source_participation,
                    "target_participation": target_participation,
                }

                resolution = resolve_relationship_mapping(
                    candidate, mappings
                )
                if resolution.is_mapped:
                    resolved.append(candidate)

            if len(resolved) != 1:
                if not resolved:
                    raise ValueError(
                        f"Relationships row {number}: no complete ordered "
                        f"foreign-key mapping supports "
                        f"{source_entity} -> {target_entity} "
                        f"({relationship_type})."
                    )
                raise ValueError(
                    f"Relationships row {number}: multiple foreign keys "
                    "support this relationship. The original CSV format "
                    "cannot distinguish them."
                )

            relationship = resolved[0]

            # Preserve metadata from a matching existing relationship.
            old_matches = []
            for old in existing:
                if not isinstance(old, dict):
                    continue
                if (
                    old.get("type") != relationship_type
                    or old.get("source_participation", "MANDATORY")
                        != source_participation
                    or old.get("target_participation", "MANDATORY")
                        != target_participation
                ):
                    continue

                old_source = old.get("source")
                old_target = old.get("target")

                try:
                    old_resolution = resolve_relationship_mapping(
                        {
                            "source": old_source,
                            "target": old_target,
                            "type": relationship_type,
                            "source_participation": source_participation,
                            "target_participation": target_participation,
                        },
                        mappings,
                    )
                except (ValueError, TypeError):
                    continue

                if not old_resolution.is_mapped:
                    continue

                if (
                    old_resolution.source.entity == source_entity
                    and old_resolution.target.entity == target_entity
                    and old_resolution.foreign_key.name
                        == next(
                            fk.name for fk in mappings
                            if fk.child_entity == (
                                source_entity if relationship_type != "ONE_TO_MANY"
                                else target_entity
                            )
                            and fk.parent_entity == (
                                target_entity if relationship_type != "ONE_TO_MANY"
                                else source_entity
                            )
                        )
                ):
                    old_matches.append(old)

            if len(old_matches) > 1:
                raise ValueError(
                    f"Relationships row {number}: multiple existing "
                    "relationships match this declaration."
                )

            if old_matches:
                old = old_matches[0]
                metadata = {
                    key: value for key, value in old.items()
                    if key not in {
                        "source", "target", "type",
                        "source_participation", "target_participation",
                    }
                }
                relationship = copy.deepcopy(metadata) | relationship

            result.append(relationship)

        return result

    def _convert_constraints(
        self,
        parsed: dict[str, Any],
        existing: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        old_by_key: dict[str, list[dict[str, Any]]] = {}

        for item in existing:
            if not isinstance(item, dict):
                continue
            key = SpecificationCsvReplacementService._record_key([
                item.get("entity"),
                item.get("field"),
                item.get("operator"),
            ])
            old_by_key.setdefault(key, []).append(item)

        result = []

        for row in parsed["rows"]:
            values = row["values"]
            number = row["row_number"]

            entity = values.get("entity", "").strip()
            field = values.get("field", "").strip()
            operator = values.get("operator", "").strip()
            raw = values.get("value", "")

            key = SpecificationCsvReplacementService._record_key([entity, field, operator])
            matches = old_by_key.get(key, [])

            if len(matches) > 1:
                raise ValueError(
                    f"Constraints row {number}: multiple existing "
                    "constraints match this entity, field and operator."
                )

            old = matches[0] if matches else {}
            old_value = old.get("value")

            if old and isinstance(old_value, str):
                value = raw
            elif old and isinstance(old_value, bool):
                if raw.strip().lower() not in {"true", "false"}:
                    raise ValueError(
                        f"Constraints row {number}: value must be "
                        "true or false."
                    )
                value = raw.strip().lower() == "true"
            elif old and isinstance(old_value, int):
                try:
                    value = int(raw)
                except ValueError as exc:
                    raise ValueError(
                        f"Constraints row {number}: value must be an integer."
                    ) from exc
            elif old and isinstance(old_value, float):
                try:
                    value = float(raw)
                except ValueError as exc:
                    raise ValueError(
                        f"Constraints row {number}: value must be numeric."
                    ) from exc
            elif old and old_value is None and raw == "":
                value = None
            else:
                # New legacy values: infer only unambiguous numeric scalars.
                stripped = raw.strip()
                try:
                    value = int(stripped)
                except ValueError:
                    try:
                        value = float(stripped)
                    except ValueError:
                        value = raw

            metadata = {
                name: item for name, item in old.items()
                if name not in {"entity", "field", "operator", "value"}
            }

            constraint = copy.deepcopy(metadata)
            constraint.update({
                "entity": entity,
                "field": field,
                "operator": operator,
                "value": value,
            })
            result.append(constraint)

        return result

    def _metadata_object(value: str, row_number: int) -> dict[str, Any]:
        if not value.strip():
            return {}
        try:
            metadata = json.loads(value)
        except json.JSONDecodeError as exc:
            raise ValueError(
                f"Row {row_number}: metadata_json must contain valid JSON."
            ) from exc
        if not isinstance(metadata, dict):
            raise ValueError(
                f"Row {row_number}: metadata_json must be a JSON object."
            )
        return metadata

    @staticmethod
    def _json_value(value: str, column: str, row_number: int) -> Any:
        try:
            return json.loads(value)
        except json.JSONDecodeError as exc:
            raise ValueError(
                f"Row {row_number}: {column} must contain valid JSON."
            ) from exc
