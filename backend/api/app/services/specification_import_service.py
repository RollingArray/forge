"""
File: specification_import_service.py
Purpose: Parse and convert Specification Wizard CSV input.

CSV structure and row conversion only. Specification merging, dependency
validation, preview revision handling, and persistence are separate steps.
"""

from __future__ import annotations

import json
import math
from decimal import Decimal, InvalidOperation
from typing import Any, get_args

from app.constants.specification_vocabulary import (
    ConstraintOperator,
    Distribution,
    FieldType,
    GenerationStrategy,
    IdentityStrategy,
    RelationshipParticipation,
    RelationshipType,
    SemanticMode,
    StringCharacterSet,
    StringGenerator,
)
from app.models.specification_entity_model import PopulationScaling

from app.services.specification_csv_parser import SpecificationCsvParser


class SpecificationImportService:
    """Parse and convert the five Specification Wizard CSV sections."""

    SECTION_HEADERS: dict[str, tuple[str, ...]] = {
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

    REQUIRED_HEADERS: dict[str, tuple[str, ...]] = {
        "entities": ("entity",),
        "fields_and_keys": ("entity", "field", "type"),
        "foreign_keys": (
            "source_entity",
            "source_fields",
            "target_entity",
        ),
        "relationships": (
            "source_entity",
            "target_entity",
            "type",
        ),
        "constraints": ("entity", "field", "operator", "value"),
    }

    FIELD_TYPES = set(get_args(FieldType))
    IDENTITY_STRATEGIES = set(get_args(IdentityStrategy))
    GENERATION_STRATEGIES = set(get_args(GenerationStrategy))
    DISTRIBUTIONS = set(get_args(Distribution))
    STRING_GENERATORS = set(get_args(StringGenerator))
    CHARACTER_SETS = set(get_args(StringCharacterSet))
    SEMANTIC_MODES = set(get_args(SemanticMode))
    RELATIONSHIP_TYPES = set(get_args(RelationshipType))
    PARTICIPATION_TYPES = set(get_args(RelationshipParticipation))
    CONSTRAINT_OPERATORS = set(get_args(ConstraintOperator))
    POPULATION_SCALING = {item.value for item in PopulationScaling}

    def __init__(
        self,
        csv_parser: SpecificationCsvParser | None = None,
    ) -> None:
        self._csv_parser = csv_parser or SpecificationCsvParser()

    def parse_and_convert(
        self,
        csv_sections: dict[str, str],
    ) -> dict[str, Any]:
        """Parse all sections and convert valid rows to FORGE structures."""

        parsed_sections: dict[str, Any] = {}
        converted_sections: dict[str, list[dict[str, Any]]] = {}
        issues: list[dict[str, Any]] = []

        for section, expected_headers in self.SECTION_HEADERS.items():
            parsed = self._csv_parser.parse_section(
                section=section,
                content=csv_sections.get(section, ""),
                expected_headers=expected_headers,
                required_headers=self.REQUIRED_HEADERS[section],
            )
            parsed_sections[section] = parsed
            for error in parsed["errors"]:
                issues.append({
                    "section": section,
                    "row": error.get("row"),
                    "column": error.get("column"),
                    "message": error["message"],
                })

        converted_sections["entities"] = self._convert_entities(
            parsed_sections["entities"], issues
        )
        converted_sections["fields_and_keys"] = self._convert_fields(
            parsed_sections["fields_and_keys"], issues
        )
        converted_sections["foreign_keys"] = self._convert_foreign_keys(
            parsed_sections["foreign_keys"], issues
        )
        converted_sections["relationships"] = self._convert_relationships(
            parsed_sections["relationships"], issues
        )
        converted_sections["constraints"] = self._convert_constraints(
            parsed_sections["constraints"], issues
        )

        return {
            "sections": parsed_sections,
            "converted": converted_sections,
            "issues": issues,
        }

    @staticmethod
    def _issue(
        issues: list[dict[str, Any]],
        section: str,
        row: int,
        column: str | None,
        message: str,
    ) -> None:
        issues.append({
            "section": section,
            "row": row,
            "column": column,
            "message": message,
        })

    @staticmethod
    def _required_text(
        values: dict[str, str],
        column: str,
    ) -> str:
        return values.get(column, "").strip()

    @staticmethod
    def _optional_integer(
        value: str,
        *,
        minimum: int | None = None,
    ) -> int | None:
        if not value.strip():
            return None
        if not value.strip().isdigit():
            raise ValueError("must be a whole number.")
        result = int(value.strip())
        if minimum is not None and result < minimum:
            raise ValueError(f"must be at least {minimum}.")
        return result

    @staticmethod
    def _optional_number(value: str) -> int | float | None:
        if not value.strip():
            return None
        try:
            number = Decimal(value.strip())
        except InvalidOperation as exc:
            raise ValueError("must be a numeric value.") from exc
        if not number.is_finite():
            raise ValueError("must be a finite numeric value.")
        if number == number.to_integral_value():
            return int(number)
        result = float(number)
        if not math.isfinite(result):
            raise ValueError("must be a finite numeric value.")
        return result

    @staticmethod
    def _json_array(value: str, column: str) -> list[Any]:
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError as exc:
            raise ValueError(
                f"{column} must contain a valid JSON array."
            ) from exc
        if not isinstance(parsed, list):
            raise ValueError(f"{column} must contain a JSON array.")
        return parsed

    def _convert_entities(
        self,
        parsed: dict[str, Any],
        issues: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        converted = []

        for row in parsed["rows"]:
            number = row["row_number"]
            values = row["values"]
            name = self._required_text(values, "entity")

            if not name:
                self._issue(
                    issues, "entities", number, "entity",
                    "Entity name is required.",
                )
                continue

            entity: dict[str, Any] = {
                "name": name,
                "description": values.get("description", "").strip(),
            }

            count_text = values.get("population_count", "")
            scaling_text = values.get("population_scaling", "").upper()

            try:
                count = self._optional_integer(count_text, minimum=0)
            except ValueError as exc:
                self._issue(
                    issues, "entities", number, "population_count", str(exc)
                )
                continue

            if scaling_text and scaling_text not in self.POPULATION_SCALING:
                self._issue(
                    issues, "entities", number, "population_scaling",
                    "Must be FIXED or SCALABLE.",
                )
                continue

            if count is not None or scaling_text:
                entity["population"] = {
                    "count": 100 if count is None else count,
                    "scaling": scaling_text or "SCALABLE",
                }

            converted.append({
                "row_number": number,
                "definition": entity,
            })

        return converted

    def _convert_fields(
        self,
        parsed: dict[str, Any],
        issues: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        converted = []

        for row in parsed["rows"]:
            number = row["row_number"]
            values = row["values"]
            entity_name = self._required_text(values, "entity")
            field_name = self._required_text(values, "field")
            field_type = self._required_text(values, "type").upper()

            if not entity_name or not field_name:
                self._issue(
                    issues, "fields_and_keys", number, None,
                    "Entity and field names are required.",
                )
                continue

            if field_type not in self.FIELD_TYPES:
                self._issue(
                    issues, "fields_and_keys", number, "type",
                    f"Unsupported field type: {field_type!r}.",
                )
                continue

            field: dict[str, Any] = {
                "name": field_name,
                "type": field_type,
            }

            identity_strategy = values.get(
                "identity_strategy", ""
            ).strip().upper()

            if identity_strategy:
                if identity_strategy not in self.IDENTITY_STRATEGIES:
                    self._issue(
                        issues, "fields_and_keys", number,
                        "identity_strategy",
                        "Must be SEQUENTIAL_ID.",
                    )
                    continue
                if field_type != "IDENTIFIER":
                    self._issue(
                        issues, "fields_and_keys", number,
                        "identity_strategy",
                        "identity_strategy is only supported for IDENTIFIER fields.",
                    )
                    continue
                field["identity"] = {"strategy": identity_strategy}

            try:
                identity_position = self._optional_integer(
                    values.get("identity_position", ""),
                    minimum=1,
                )
            except ValueError as exc:
                self._issue(
                    issues, "fields_and_keys", number,
                    "identity_position", str(exc),
                )
                continue

            try:
                generation = self._convert_generation(
                    field_type=field_type,
                    values=values,
                )
            except ValueError as exc:
                self._issue(
                    issues, "fields_and_keys", number, None, str(exc)
                )
                continue

            if generation is not None:
                field["generation"] = generation

            converted.append({
                "row_number": number,
                "entity": entity_name,
                "field": field,
                "identity_position": identity_position,
            })

        return converted

    def _convert_generation(
        self,
        field_type: str,
        values: dict[str, str],
    ) -> dict[str, Any] | None:
        strategy = values.get("generation_strategy", "").strip().upper()
        distribution = values.get("distribution", "").strip().upper()
        generator = values.get("generator", "").strip().upper()

        if strategy and strategy not in self.GENERATION_STRATEGIES:
            raise ValueError("generation_strategy must be RANDOM.")
        if distribution and distribution not in self.DISTRIBUTIONS:
            raise ValueError(
                f"Unsupported distribution: {distribution!r}."
            )
        if generator and generator not in self.STRING_GENERATORS:
            raise ValueError(f"Unsupported string generator: {generator!r}.")

        parameters: dict[str, Any] = {}

        if field_type == "IDENTIFIER":
            if any((strategy, distribution, generator)):
                raise ValueError(
                    "IDENTIFIER fields use identity_strategy, not generation settings."
                )
            return None

        if field_type == "BOOLEAN":
            if distribution or generator:
                raise ValueError(
                    "BOOLEAN fields support generation_strategy only."
                )

        elif field_type == "STRING":
            if distribution:
                raise ValueError("STRING fields do not use a distribution.")
            if generator == "RANDOM_STRING":
                minimum = self._optional_integer(
                    values.get("minimum_length", ""), minimum=1
                )
                maximum = self._optional_integer(
                    values.get("maximum_length", ""), minimum=1
                )
                charset = values.get("character_set", "").strip().upper()

                if minimum is not None:
                    parameters["minimum_length"] = minimum
                if maximum is not None:
                    parameters["maximum_length"] = maximum
                if charset:
                    if charset not in self.CHARACTER_SETS:
                        raise ValueError(
                            "character_set must be ALPHA, DIGITS, or ALPHANUMERIC."
                        )
                    parameters["character_set"] = charset

            elif generator == "PATTERN":
                pattern = values.get("pattern", "").strip()
                if pattern:
                    parameters["pattern"] = pattern

            elif generator == "SEMANTIC":
                description = values.get("semantic_description", "").strip()
                mode = values.get("semantic_mode", "").strip().upper()
                if description:
                    parameters["description"] = description
                if mode:
                    if mode not in self.SEMANTIC_MODES:
                        raise ValueError(
                            "semantic_mode must be UNIQUE or VOCABULARY."
                        )
                    parameters["mode"] = mode

            elif any(
                values.get(column, "").strip()
                for column in (
                    "minimum_length", "maximum_length", "character_set",
                    "pattern", "semantic_description", "semantic_mode",
                )
            ):
                raise ValueError(
                    "Specify a supported generator before supplying its parameters."
                )

        elif field_type in {"INTEGER", "DECIMAL"}:
            if generator:
                raise ValueError(
                    f"{field_type} fields use distribution, not generator."
                )
            minimum = self._optional_number(values.get("minimum", ""))
            maximum = self._optional_number(values.get("maximum", ""))
            if minimum is not None:
                parameters["minimum"] = minimum
            if maximum is not None:
                parameters["maximum"] = maximum

            if field_type == "INTEGER":
                if distribution and distribution not in {
                    "UNIFORM", "DISCRETE_UNIFORM"
                }:
                    raise ValueError(
                        "INTEGER supports UNIFORM or DISCRETE_UNIFORM."
                    )
                for key, value in (
                    ("minimum", minimum), ("maximum", maximum)
                ):
                    if value is not None and isinstance(value, float):
                        raise ValueError(
                            f"INTEGER {key} must be a whole number."
                        )
            elif distribution and distribution != "UNIFORM":
                raise ValueError("DECIMAL supports UNIFORM only.")

        elif field_type == "CATEGORICAL":
            if generator:
                raise ValueError(
                    "CATEGORICAL fields use distribution, not generator."
                )
            if distribution and distribution != "CATEGORICAL":
                raise ValueError(
                    "CATEGORICAL fields require CATEGORICAL distribution."
                )
            raw_values = values.get("values", "").strip()
            if raw_values:
                parsed_values = self._json_array(raw_values, "values")
                if not parsed_values:
                    raise ValueError("values must not be an empty array.")
                parameters["values"] = parsed_values

        has_configuration = any(
            (strategy, distribution, generator, parameters)
        )
        if not has_configuration:
            return None

        generation: dict[str, Any] = {}
        if strategy:
            generation["strategy"] = strategy
        if distribution:
            generation["distribution"] = distribution
        if generator:
            generation["generator"] = generator
        if parameters:
            generation["parameters"] = parameters

        return generation

    def _convert_foreign_keys(
        self,
        parsed: dict[str, Any],
        issues: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        converted = []

        for row in parsed["rows"]:
            number = row["row_number"]
            values = row["values"]
            source_entity = self._required_text(values, "source_entity")
            target_entity = self._required_text(values, "target_entity")

            try:
                source_fields = self._json_array(
                    values.get("source_fields", ""), "source_fields"
                )
            except ValueError as exc:
                self._issue(
                    issues, "foreign_keys", number, "source_fields", str(exc)
                )
                continue

            if not source_entity or not target_entity:
                self._issue(
                    issues, "foreign_keys", number, None,
                    "Source and target entity names are required.",
                )
                continue
            if not source_fields or any(
                not isinstance(name, str) or not name.strip()
                for name in source_fields
            ):
                self._issue(
                    issues, "foreign_keys", number, "source_fields",
                    "source_fields must be a non-empty JSON array of field names.",
                )
                continue
            source_fields = [name.strip() for name in source_fields]
            if len(source_fields) != len(set(source_fields)):
                self._issue(
                    issues, "foreign_keys", number, "source_fields",
                    "source_fields must not contain duplicates.",
                )
                continue

            name = (
                f"FK_{source_entity}_"
                f"{'_'.join(source_fields)}_{target_entity}"
            )
            converted.append({
                "row_number": number,
                "definition": {
                    "name": name,
                    "source": {
                        "entity": source_entity,
                        "fields": source_fields,
                    },
                    "target": {
                        "entity": target_entity,
                        "fields": [],
                    },
                },
            })

        return converted

    def _convert_relationships(
        self,
        parsed: dict[str, Any],
        issues: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        converted = []

        for row in parsed["rows"]:
            number = row["row_number"]
            values = row["values"]
            source_entity = self._required_text(values, "source_entity")
            target_entity = self._required_text(values, "target_entity")
            relationship_type = self._required_text(
                values, "type"
            ).upper()
            source_participation = (
                values.get("source_participation", "").strip().upper()
                or "MANDATORY"
            )
            target_participation = (
                values.get("target_participation", "").strip().upper()
                or "MANDATORY"
            )

            row_errors = []
            if not source_entity or not target_entity:
                row_errors.append("Source and target entity names are required.")
            if relationship_type not in self.RELATIONSHIP_TYPES:
                row_errors.append(
                    f"Unsupported relationship type: {relationship_type!r}."
                )
            if source_participation not in self.PARTICIPATION_TYPES:
                row_errors.append(
                    "source_participation must be MANDATORY or OPTIONAL."
                )
            if target_participation not in self.PARTICIPATION_TYPES:
                row_errors.append(
                    "target_participation must be MANDATORY or OPTIONAL."
                )

            if row_errors:
                for message in row_errors:
                    self._issue(
                        issues, "relationships", number, None, message
                    )
                continue

            converted.append({
                "row_number": number,
                "source_entity": source_entity,
                "target_entity": target_entity,
                "type": relationship_type,
                "source_participation": source_participation,
                "target_participation": target_participation,
            })

        return converted

    def _convert_constraints(
        self,
        parsed: dict[str, Any],
        issues: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        converted = []

        for row in parsed["rows"]:
            number = row["row_number"]
            values = row["values"]
            entity = self._required_text(values, "entity")
            field = self._required_text(values, "field")
            operator = self._required_text(values, "operator")
            raw_value = values.get("value", "").strip()

            if not entity or not field or not operator or not raw_value:
                self._issue(
                    issues, "constraints", number, None,
                    "Entity, field, operator, and value are required.",
                )
                continue
            if operator not in self.CONSTRAINT_OPERATORS:
                self._issue(
                    issues, "constraints", number, "operator",
                    f"Unsupported constraint operator: {operator!r}.",
                )
                continue

            converted.append({
                "row_number": number,
                "entity": entity,
                "field": field,
                "operator": operator,
                "raw_value": raw_value,
            })

        return converted


    @staticmethod
    def _entity_by_name(
        specification: dict[str, Any],
        name: str,
    ) -> dict[str, Any] | None:
        return next(
            (
                entity
                for entity in specification.get("entities", [])
                if entity.get("name") == name
            ),
            None,
        )

    @staticmethod
    def _field_by_name(
        entity: dict[str, Any],
        name: str,
    ) -> dict[str, Any] | None:
        return next(
            (
                field
                for field in entity.get("fields", [])
                if field.get("name") == name
            ),
            None,
        )

    @staticmethod
    def _record_issue(
        issues: list[dict[str, Any]],
        section: str,
        row: int | None,
        message: str,
        column: str | None = None,
    ) -> None:
        issues.append({
            "section": section,
            "row": row,
            "column": column,
            "message": message,
        })

    @staticmethod
    def _classify(
        bucket: list[dict[str, Any]],
        section: str,
        row: int,
        definition: dict[str, Any],
        message: str,
    ) -> None:
        bucket.append({
            "section": section,
            "row": row,
            "definition": definition,
            "message": message,
        })

    def merge_into_specification(
        self,
        existing_specification: dict[str, Any],
        parsed_result: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Build an additions-only candidate without mutating the input.

        Exact existing definitions are no-ops. Definitions that reuse an
        existing natural key with different content are conflicts. Existing
        definitions not present in the import are always preserved.
        """

        from copy import deepcopy

        candidate = deepcopy(existing_specification)
        candidate.setdefault("entities", [])
        candidate.setdefault("foreign_keys", [])
        candidate.setdefault("relationships", [])
        candidate.setdefault("constraints", [])

        additions: list[dict[str, Any]] = []
        already_present: list[dict[str, Any]] = []
        conflicts: list[dict[str, Any]] = []
        issues: list[dict[str, Any]] = list(parsed_result.get("issues", []))

        converted = parsed_result.get("converted", {})

        # Track natural keys to catch duplicates within the submitted CSV.
        seen_entities: set[str] = set()
        seen_fields: set[tuple[str, str]] = set()
        seen_foreign_keys: set[str] = set()
        seen_relationships: set[tuple[str, str, str]] = set()
        seen_constraints: set[str] = set()

        # 1. Entities
        for item in converted.get("entities", []):
            row = item["row_number"]
            definition = item["definition"]
            name = definition["name"]

            if name in seen_entities:
                self._record_issue(
                    issues, "entities", row,
                    f"Duplicate entity row in this import: {name}.",
                )
                continue
            seen_entities.add(name)

            existing = self._entity_by_name(candidate, name)
            if existing is not None:
                differences = []
                supplied_description = definition.get("description", "")
                if supplied_description and (
                    existing.get("description", "") != supplied_description
                ):
                    differences.append("description")

                supplied_population = definition.get("population")
                if supplied_population is not None:
                    current_population = existing.get("population") or {}
                    for key, value in supplied_population.items():
                        if current_population.get(key) != value:
                            differences.append(f"population.{key}")

                if differences:
                    message = (
                        f"Entity {name} already exists with different "
                        f"{', '.join(differences)}. Existing values were preserved."
                    )
                    self._classify(
                        conflicts, "entities", row, definition, message
                    )
                    self._record_issue(issues, "entities", row, message)
                else:
                    self._classify(
                        already_present, "entities", row, definition,
                        f"Entity {name} is already present.",
                    )
                continue

            new_entity = {
                "name": name,
                "description": definition.get("description", ""),
                "fields": [],
                "population": definition.get(
                    "population",
                    {"count": 100, "scaling": "SCALABLE"},
                ),
            }
            candidate["entities"].append(new_entity)
            self._classify(
                additions, "entities", row, new_entity,
                f"Entity {name} will be added.",
            )

        # 2. Fields and ordered entity identities
        identity_positions: dict[str, dict[int, str]] = {}
        identity_members: dict[str, set[str]] = {}

        for entity in candidate["entities"]:
            entity_name = entity.get("name")
            identity_fields = list(
                (entity.get("identity") or {}).get("fields") or []
            )
            identity_members[entity_name] = set(identity_fields)
            identity_positions[entity_name] = {
                position: field_name
                for position, field_name in enumerate(identity_fields, 1)
            }

        for item in converted.get("fields_and_keys", []):
            row = item["row_number"]
            entity_name = item["entity"]
            field = item["field"]
            field_name = field["name"]
            position = item.get("identity_position")
            natural_key = (entity_name, field_name)

            if natural_key in seen_fields:
                self._record_issue(
                    issues, "fields_and_keys", row,
                    f"Duplicate field row in this import: "
                    f"{entity_name}.{field_name}.",
                )
                continue
            seen_fields.add(natural_key)

            entity = self._entity_by_name(candidate, entity_name)
            if entity is None:
                message = (
                    f"Unknown entity {entity_name} for field {field_name}. "
                    "Add the entity in the Entities section first."
                )
                self._record_issue(
                    issues, "fields_and_keys", row, message, "entity"
                )
                continue

            existing_field = self._field_by_name(entity, field_name)
            if existing_field is not None:
                if existing_field != field:
                    message = (
                        f"Field {entity_name}.{field_name} already exists "
                        "with a different definition. Existing field was preserved."
                    )
                    self._classify(
                        conflicts, "fields_and_keys", row, field, message
                    )
                    self._record_issue(
                        issues, "fields_and_keys", row, message
                    )
                    continue

                self._classify(
                    already_present, "fields_and_keys", row, field,
                    f"Field {entity_name}.{field_name} is already present.",
                )
            else:
                entity.setdefault("fields", []).append(deepcopy(field))
                self._classify(
                    additions, "fields_and_keys", row, field,
                    f"Field {entity_name}.{field_name} will be added.",
                )

            if position is None:
                continue

            current_positions = identity_positions.setdefault(
                entity_name, {}
            )
            current_members = identity_members.setdefault(
                entity_name, set()
            )
            occupied = current_positions.get(position)

            if occupied is not None and occupied != field_name:
                message = (
                    f"Identity position {position} for {entity_name} "
                    f"is already occupied by {occupied}, not {field_name}."
                )
                self._classify(
                    conflicts, "fields_and_keys", row, field, message
                )
                self._record_issue(
                    issues, "fields_and_keys", row, message,
                    "identity_position",
                )
                continue

            existing_position = next(
                (
                    existing_position
                    for existing_position, existing_name
                    in current_positions.items()
                    if existing_name == field_name
                ),
                None,
            )
            if (
                existing_position is not None
                and existing_position != position
            ):
                message = (
                    f"{entity_name}.{field_name} is already identity "
                    f"position {existing_position}, not {position}."
                )
                self._classify(
                    conflicts, "fields_and_keys", row, field, message
                )
                self._record_issue(
                    issues, "fields_and_keys", row, message,
                    "identity_position",
                )
                continue

            current_positions[position] = field_name
            current_members.add(field_name)

        for entity_name, positions in identity_positions.items():
            if not positions:
                continue
            ordered_positions = sorted(positions)
            expected_positions = list(range(1, len(ordered_positions) + 1))
            if ordered_positions != expected_positions:
                message = (
                    f"Identity positions for {entity_name} must be "
                    "contiguous and start at 1."
                )
                self._record_issue(
                    issues, "fields_and_keys", None, message,
                    "identity_position",
                )
                continue

            entity = self._entity_by_name(candidate, entity_name)
            if entity is not None:
                ordered_fields = [
                    positions[position]
                    for position in expected_positions
                ]
                if ordered_fields:
                    entity["identity"] = {"fields": ordered_fields}

        # 3. Foreign keys. Target fields are derived from target identity.
        for item in converted.get("foreign_keys", []):
            row = item["row_number"]
            definition = deepcopy(item["definition"])
            source_entity_name = definition["source"]["entity"]
            target_entity_name = definition["target"]["entity"]
            source_fields = definition["source"]["fields"]

            if source_entity_name == target_entity_name:
                message = "A foreign key must connect two different entities."
                self._record_issue(issues, "foreign_keys", row, message)
                continue

            source_entity = self._entity_by_name(
                candidate, source_entity_name
            )
            target_entity = self._entity_by_name(
                candidate, target_entity_name
            )
            if source_entity is None or target_entity is None:
                missing = (
                    source_entity_name
                    if source_entity is None
                    else target_entity_name
                )
                message = f"Unknown foreign-key entity: {missing}."
                self._record_issue(issues, "foreign_keys", row, message)
                continue

            source_field_names = {
                field.get("name")
                for field in source_entity.get("fields", [])
            }
            missing_source_fields = [
                name for name in source_fields
                if name not in source_field_names
            ]
            if missing_source_fields:
                message = (
                    "Unknown source field(s): "
                    + ", ".join(missing_source_fields)
                    + "."
                )
                self._record_issue(issues, "foreign_keys", row, message)
                continue

            target_identity = list(
                (target_entity.get("identity") or {}).get("fields") or []
            )
            if not target_identity:
                message = (
                    f"Target entity {target_entity_name} must define "
                    "identity fields before it can be referenced."
                )
                self._record_issue(issues, "foreign_keys", row, message)
                continue

            if len(source_fields) != len(target_identity):
                message = (
                    "The number of source fields must match the number "
                    "of target identity fields."
                )
                self._record_issue(issues, "foreign_keys", row, message)
                continue

            definition["target"]["fields"] = target_identity
            name = definition["name"]

            if name in seen_foreign_keys:
                self._record_issue(
                    issues, "foreign_keys", row,
                    f"Duplicate foreign-key row in this import: {name}.",
                )
                continue
            seen_foreign_keys.add(name)

            existing = next(
                (
                    foreign_key
                    for foreign_key in candidate["foreign_keys"]
                    if foreign_key.get("name") == name
                ),
                None,
            )
            if existing is not None:
                if existing != definition:
                    message = (
                        f"Foreign key {name} already exists with a "
                        "different mapping. Existing mapping was preserved."
                    )
                    self._classify(
                        conflicts, "foreign_keys", row, definition, message
                    )
                    self._record_issue(issues, "foreign_keys", row, message)
                else:
                    self._classify(
                        already_present, "foreign_keys", row, definition,
                        f"Foreign key {name} is already present.",
                    )
                continue

            candidate["foreign_keys"].append(definition)
            self._classify(
                additions, "foreign_keys", row, definition,
                f"Foreign key {name} will be added.",
            )

        # 4. Relationships. Derive endpoints from exactly one FK.
        for item in converted.get("relationships", []):
            row = item["row_number"]
            source_entity = item["source_entity"]
            target_entity = item["target_entity"]

            if source_entity == target_entity:
                self._record_issue(
                    issues, "relationships", row,
                    "A relationship must connect two different entities.",
                )
                continue

            if (
                self._entity_by_name(candidate, source_entity) is None
                or self._entity_by_name(candidate, target_entity) is None
            ):
                self._record_issue(
                    issues, "relationships", row,
                    f"Unknown relationship entity: {source_entity} or {target_entity}.",
                )
                continue

            compatible = [
                foreign_key
                for foreign_key in candidate["foreign_keys"]
                if (
                    foreign_key.get("source", {}).get("entity")
                    == source_entity
                    and foreign_key.get("target", {}).get("entity")
                    == target_entity
                )
                or (
                    foreign_key.get("source", {}).get("entity")
                    == target_entity
                    and foreign_key.get("target", {}).get("entity")
                    == source_entity
                )
            ]

            if len(compatible) != 1:
                message = (
                    "A relationship requires exactly one foreign key "
                    f"between {source_entity} and {target_entity}; "
                    f"found {len(compatible)}."
                )
                self._record_issue(
                    issues, "relationships", row, message
                )
                continue

            foreign_key = compatible[0]
            fk_source = foreign_key["source"]
            fk_target = foreign_key["target"]

            if fk_source["entity"] == source_entity:
                relationship_source = (
                    f"{fk_source['entity']}.{fk_source['fields'][0]}"
                )
                relationship_target = (
                    f"{fk_target['entity']}.{fk_target['fields'][0]}"
                )
            else:
                relationship_source = (
                    f"{fk_target['entity']}.{fk_target['fields'][0]}"
                )
                relationship_target = (
                    f"{fk_source['entity']}.{fk_source['fields'][0]}"
                )

            definition = {
                "source": relationship_source,
                "target": relationship_target,
                "type": item["type"],
                "source_participation": item["source_participation"],
                "target_participation": item["target_participation"],
            }
            natural_key = (
                definition["source"],
                definition["target"],
                definition["type"],
            )

            if natural_key in seen_relationships:
                self._record_issue(
                    issues, "relationships", row,
                    "Duplicate relationship row in this import.",
                )
                continue
            seen_relationships.add(natural_key)

            if definition in candidate["relationships"]:
                self._classify(
                    already_present, "relationships", row, definition,
                    "Relationship is already present.",
                )
                continue

            candidate["relationships"].append(definition)
            self._classify(
                additions, "relationships", row, definition,
                "Relationship will be added.",
            )

        # 5. Constraints. Convert the value using the referenced field type.
        for item in converted.get("constraints", []):
            row = item["row_number"]
            entity_name = item["entity"]
            field_name = item["field"]
            entity = self._entity_by_name(candidate, entity_name)

            if entity is None:
                self._record_issue(
                    issues, "constraints", row,
                    f"Unknown entity: {entity_name}.",
                )
                continue

            field = self._field_by_name(entity, field_name)
            if field is None:
                self._record_issue(
                    issues, "constraints", row,
                    f"Unknown field: {entity_name}.{field_name}.",
                )
                continue

            field_type = field.get("type")
            operator = item["operator"]
            allowed_operators = {
                "INTEGER": {">", ">=", "<", "<="},
                "DECIMAL": {">", ">=", "<", "<="},
                "STRING": {"==", "!="},
                "CATEGORICAL": {"==", "!="},
            }
            if operator not in allowed_operators.get(field_type, set()):
                self._record_issue(
                    issues, "constraints", row,
                    f"Operator {operator!r} is not supported for "
                    f"{field_type} fields.",
                )
                continue

            raw_value = item["raw_value"]
            try:
                if field_type == "INTEGER":
                    parsed_value = self._optional_integer(raw_value)
                    if parsed_value is None:
                        raise ValueError("Constraint value is required.")
                elif field_type == "DECIMAL":
                    parsed_value = self._optional_number(raw_value)
                    if parsed_value is None:
                        raise ValueError("Constraint value is required.")
                else:
                    parsed_value = raw_value
            except ValueError as exc:
                self._record_issue(
                    issues, "constraints", row, str(exc), "value"
                )
                continue

            definition = {
                "entity": entity_name,
                "field": field_name,
                "operator": operator,
                "value": parsed_value,
            }

            if definition in candidate["constraints"]:
                self._classify(
                    already_present, "constraints", row, definition,
                    "Constraint is already present.",
                )
                continue

            candidate["constraints"].append(definition)
            self._classify(
                additions, "constraints", row, definition,
                "Constraint will be added.",
            )

        return {
            "candidate": candidate,
            "additions": additions,
            "already_present": already_present,
            "conflicts": conflicts,
            "issues": issues,
            "can_apply": not issues and not conflicts,
            "summary": {
                "additions": len(additions),
                "already_present": len(already_present),
                "conflicts": len(conflicts),
                "issues": len(issues),
            },
        }
