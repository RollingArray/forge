"""
File: specification_validation_service.py
Purpose: Deterministic validation of the canonical FORGE specification.

The canonical specification is authoritative.
No LLM or UI logic belongs in this service.
"""

from typing import Any


class SpecificationValidationService:
    """Validate a canonical FORGE specification deterministically."""

    def validate(
        self,
        specification: dict[str, Any],
    ) -> dict[str, Any]:
        findings: list[dict[str, Any]] = []
        sequence = 0

        def add(
            severity: str,
            category: str,
            title: str,
            details: str,
            entity: str | None = None,
            field: str | None = None,
        ) -> None:
            nonlocal sequence

            sequence += 1

            findings.append(
                {
                    "id": f"validation-{sequence}",
                    "severity": severity,
                    "category": category,
                    "title": title,
                    "details": details,
                    "entity": entity,
                    "field": field,
                }
            )

        entities = specification.get("entities", [])
        entity_names: set[str] = set()

        for entity in entities:
            name = str(entity.get("name", "")).strip()

            if not name:
                add(
                    "error",
                    "Entity",
                    "Entity name is missing",
                    "Every entity must have a non-empty name.",
                )
                continue

            if name in entity_names:
                add(
                    "error",
                    "Entity",
                    "Duplicate entity name",
                    f"Entity '{name}' is defined more than once.",
                    name,
                )

            entity_names.add(name)

        fields_by_entity: dict[str, set[str]] = {}

        for entity in entities:
            self._validate_entity(
                entity=entity,
                entity_names=entity_names,
                fields_by_entity=fields_by_entity,
                add=add,
            )

        version = str(specification.get("version", "")).strip()

        if version:
            add(
                "passed",
                "Specification",
                "Specification version is defined",
                f"Version {version}.",
            )
        else:
            add(
                "error",
                "Specification",
                "Specification version is missing",
                "A specification version is required.",
            )

        vocabulary_version = str(
            specification.get("vocabulary_version", "")
        ).strip()

        if vocabulary_version:
            add(
                "passed",
                "Specification",
                "Vocabulary version is defined",
                f"Vocabulary version {vocabulary_version}.",
            )
        else:
            add(
                "error",
                "Specification",
                "Vocabulary version is missing",
                "A vocabulary version is required.",
            )

        model = specification.get("model", {})

        if str(model.get("name", "")).strip():
            add(
                "passed",
                "Model",
                "Model definition is valid",
                f"Model '{model['name']}' is defined.",
            )
        else:
            add(
                "error",
                "Model",
                "Model name is missing",
                "The specification must identify the model.",
            )

        generation = specification.get("generation", {})
        seed = generation.get("seed")

        if isinstance(seed, int) and not isinstance(seed, bool):
            add(
                "passed",
                "Generation",
                "Generation seed is valid",
                f"Seed {seed} is configured.",
            )
        else:
            add(
                "error",
                "Generation",
                "Generation seed is invalid",
                "Generation seed must be an integer.",
            )

        self._validate_relationships(
            specification=specification,
            entity_names=entity_names,
            fields_by_entity=fields_by_entity,
            add=add,
        )

        self._validate_foreign_keys(
            specification=specification,
            entity_names=entity_names,
            fields_by_entity=fields_by_entity,
            add=add,
        )

        self._validate_constraints(
            specification=specification,
            entity_names=entity_names,
            fields_by_entity=fields_by_entity,
            add=add,
        )

        errors = sum(
            finding["severity"] == "error"
            for finding in findings
        )

        warnings = sum(
            finding["severity"] == "warning"
            for finding in findings
        )

        passed = sum(
            finding["severity"] == "passed"
            for finding in findings
        )

        return {
            "model_name": model.get("name", "Untitled Model"),
            "specification_version": version or "Unknown",
            "vocabulary_version": vocabulary_version or "Unknown",
            "errors": errors,
            "warnings": warnings,
            "passed": passed,
            "total_checks": len(findings),
            "entities_validated": len(entities),
            "can_continue": errors == 0,
            "findings": findings,
            "entities": self._build_entity_results(
                entities,
                findings,
            ),
        }

    def _validate_entity(
        self,
        entity: dict[str, Any],
        entity_names: set[str],
        fields_by_entity: dict[str, set[str]],
        add,
    ) -> None:
        name = str(entity.get("name", "")).strip()

        if not name:
            return

        fields = entity.get("fields", [])
        field_names: set[str] = set()
        valid = True

        for field in fields:
            field_name = str(field.get("name", "")).strip()

            if not field_name:
                valid = False
                add(
                    "error",
                    "Entity",
                    "Field name is missing",
                    f"Entity '{name}' contains a field without a name.",
                    name,
                )
                continue

            if field_name in field_names:
                valid = False
                add(
                    "error",
                    "Entity",
                    "Duplicate field name",
                    f"Field '{field_name}' is defined more than once.",
                    name,
                    field_name,
                )

            field_names.add(field_name)

            if not str(field.get("type", "")).strip():
                valid = False
                add(
                    "error",
                    "Entity",
                    "Field type is missing",
                    f"Field '{field_name}' does not define a type.",
                    name,
                    field_name,
                )

        fields_by_entity[name] = field_names

        identity = entity.get("identity", {})
        identity_fields = (
            identity.get("fields", [])
            if isinstance(identity, dict)
            else []
        )

        if not identity_fields:
            valid = False
            add(
                "error",
                "Entity",
                "Identity definition is missing",
                f"Entity '{name}' does not define an identity field.",
                name,
            )
        else:
            if len(identity_fields) != len(set(identity_fields)):
                valid = False
                add(
                    "error",
                    "Entity",
                    "Duplicate identity field",
                    f"Entity '{name}' identity contains duplicate fields.",
                    name,
                )

            for identity_field in identity_fields:
                if not isinstance(identity_field, str) or not identity_field:
                    valid = False
                    add(
                        "error",
                        "Entity",
                        "Invalid identity field",
                        f"Entity '{name}' contains an invalid identity field.",
                        name,
                    )
                elif identity_field not in field_names:
                    valid = False
                    add(
                        "error",
                        "Entity",
                        "Identity field is missing",
                        f"Identity field '{identity_field}' is not defined on '{name}'.",
                        name,
                        identity_field,
                    )

        population = entity.get("population", {}).get("count")

        if (
            not isinstance(population, int)
            or isinstance(population, bool)
            or population < 0
        ):
            valid = False
            add(
                "error",
                "Entity",
                "Population count is invalid",
                f"Entity '{name}' must define a non-negative integer population count.",
                name,
            )

        if valid:
            add(
                "passed",
                "Entity",
                "Entity definition is valid",
                f"{len(fields)} fields and {len(identity_fields)} identity field(s) are defined.",
                name,
            )

    def _validate_relationships(
        self,
        specification: dict[str, Any],
        entity_names: set[str],
        fields_by_entity: dict[str, set[str]],
        add,
    ) -> None:
        relationships = specification.get("relationships", [])

        valid_types = {
            "ONE_TO_ONE",
            "ONE_TO_MANY",
            "MANY_TO_ONE",
            "MANY_TO_MANY",
        }

        valid_participation = {
            "MANDATORY",
            "OPTIONAL",
        }

        def parse_reference(
            reference: Any,
            role: str,
        ) -> tuple[str | None, str | None]:
            if not isinstance(reference, str) or "." not in reference:
                add(
                    "error",
                    "Relationship",
                    f"Invalid {role} reference",
                    f"{role.capitalize()} must reference an entity and field using ENTITY.FIELD format.",
                    None,
                )
                return None, None

            entity, field = reference.split(".", 1)
            entity = entity.strip()
            field = field.strip()

            if not entity or not field:
                add(
                    "error",
                    "Relationship",
                    f"Invalid {role} reference",
                    f"{role.capitalize()} reference '{reference}' must use ENTITY.FIELD format.",
                    entity or None,
                    field or None,
                )
                return None, None

            if entity not in entity_names:
                add(
                    "error",
                    "Relationship",
                    f"Unknown {role} entity",
                    f"{role.capitalize()} entity '{entity}' is not defined in the specification.",
                    entity,
                    field,
                )
                return None, None

            if field not in fields_by_entity.get(entity, set()):
                add(
                    "error",
                    "Relationship",
                    f"Unknown {role} field",
                    f"{role.capitalize()} field '{entity}.{field}' is not defined in the specification.",
                    entity,
                    field,
                )
                return None, None

            return entity, field

        for relationship in relationships:
            source_reference = relationship.get("source")
            target_reference = relationship.get("target")

            source_entity, source_field = parse_reference(
                source_reference,
                "source",
            )
            target_entity, target_field = parse_reference(
                target_reference,
                "target",
            )

            relationship_type = relationship.get("type")

            if relationship_type not in valid_types:
                add(
                    "error",
                    "Relationship",
                    "Invalid relationship type",
                    (
                        f"Relationship '{source_reference or 'Unknown'} → "
                        f"{target_reference or 'Unknown'}' uses invalid type "
                        f"'{relationship_type}'. Expected one of: "
                        f"{', '.join(sorted(valid_types))}."
                    ),
                    source_entity,
                    source_field,
                )

            source_participation = relationship.get(
                "source_participation",
                "MANDATORY",
            )
            target_participation = relationship.get(
                "target_participation",
                "MANDATORY",
            )

            if source_participation not in valid_participation:
                add(
                    "error",
                    "Relationship",
                    "Invalid source participation",
                    (
                        f"Relationship '{source_reference or 'Unknown'} → "
                        f"{target_reference or 'Unknown'}' uses invalid source "
                        f"participation '{source_participation}'. Expected "
                        f"MANDATORY or OPTIONAL."
                    ),
                    source_entity,
                    source_field,
                )

            if target_participation not in valid_participation:
                add(
                    "error",
                    "Relationship",
                    "Invalid target participation",
                    (
                        f"Relationship '{source_reference or 'Unknown'} → "
                        f"{target_reference or 'Unknown'}' uses invalid target "
                        f"participation '{target_participation}'. Expected "
                        f"MANDATORY or OPTIONAL."
                    ),
                    source_entity,
                    source_field,
                )

            if (
                source_entity
                and source_field
                and target_entity
                and target_field
                and relationship_type in valid_types
                and source_participation in valid_participation
                and target_participation in valid_participation
            ):
                add(
                    "passed",
                    "Relationship",
                    "Relationship is valid",
                    (
                        f"{source_reference} → {target_reference} "
                        f"({relationship_type}, "
                        f"{source_participation} → "
                        f"{target_participation})."
                    ),
                    source_entity,
                    source_field,
                )

    def _validate_foreign_keys(
        self,
        specification: dict[str, Any],
        entity_names: set[str],
        fields_by_entity: dict[str, set[str]],
        add,
    ) -> None:
        foreign_keys = specification.get("foreign_keys", [])
        seen_names: set[str] = set()
        seen_mappings: set[tuple] = set()

        field_maps = {
            entity.get("name"): {
                field.get("name"): field
                for field in entity.get("fields", [])
                if isinstance(field, dict)
            }
            for entity in specification.get("entities", [])
            if entity.get("name")
        }

        for foreign_key in foreign_keys:
            name = str(foreign_key.get("name", "")).strip()

            source = foreign_key.get("source", {})
            target = foreign_key.get("target", {})

            source_entity = str(source.get("entity", "")).strip()
            target_entity = str(target.get("entity", "")).strip()

            source_fields = source.get("fields", [])
            target_fields = target.get("fields", [])

            expected_name = f"FK_{source_entity}_{target_entity}"

            valid = True

            if not name:
                valid = False
                add(
                    "error",
                    "Foreign Key",
                    "Foreign key name is missing",
                    "Foreign key name must be a non-empty string.",
                    source_entity or None,
                )
            elif name != expected_name:
                valid = False
                add(
                    "error",
                    "Foreign Key",
                    "Invalid foreign key name",
                    f"Foreign key name '{name}' does not match canonical name '{expected_name}'.",
                    source_entity or None,
                )

            if name and name in seen_names:
                valid = False
                add(
                    "error",
                    "Foreign Key",
                    "Duplicate foreign key name",
                    f"Foreign key '{name}' is defined more than once.",
                    source_entity or None,
                )

            seen_names.add(name)

            if source_entity not in entity_names:
                valid = False
                add(
                    "error",
                    "Foreign Key",
                    "Unknown source entity",
                    f"Foreign key references unknown source entity '{source_entity}'.",
                    source_entity or None,
                )

            if target_entity not in entity_names:
                valid = False
                add(
                    "error",
                    "Foreign Key",
                    "Unknown target entity",
                    f"Foreign key references unknown target entity '{target_entity}'.",
                    source_entity or None,
                )

            if source_entity == target_entity and source_entity:
                valid = False
                add(
                    "error",
                    "Foreign Key",
                    "Invalid self-referencing foreign key",
                    f"Foreign key '{name or expected_name}' must have different source and target entities.",
                    source_entity,
                )

            if (
                not isinstance(source_fields, list)
                or not source_fields
                or not isinstance(target_fields, list)
                or not target_fields
            ):
                valid = False
                add(
                    "error",
                    "Foreign Key",
                    "Foreign key fields are missing",
                    f"{expected_name}: source and target fields must contain at least one field.",
                    source_entity or None,
                )
                continue

            if len(source_fields) != len(target_fields):
                valid = False
                add(
                    "error",
                    "Foreign Key",
                    "Foreign key field counts do not match",
                    f"{expected_name}: source and target field counts must match.",
                    source_entity or None,
                )

            if len(source_fields) != len(set(source_fields)):
                valid = False
                add(
                    "error",
                    "Foreign Key",
                    "Duplicate source field",
                    f"{expected_name}: source fields must not contain duplicates.",
                    source_entity or None,
                )

            if len(target_fields) != len(set(target_fields)):
                valid = False
                add(
                    "error",
                    "Foreign Key",
                    "Duplicate target field",
                    f"{expected_name}: target fields must not contain duplicates.",
                    source_entity or None,
                )

            source_map = field_maps.get(source_entity, {})
            target_map = field_maps.get(target_entity, {})

            for field_name in source_fields:
                if field_name not in source_map:
                    valid = False
                    add(
                        "error",
                        "Foreign Key",
                        "Source field is missing",
                        f"{expected_name}: source references unknown field {source_entity}.{field_name}.",
                        source_entity,
                        field_name,
                    )

            for field_name in target_fields:
                if field_name not in target_map:
                    valid = False
                    add(
                        "error",
                        "Foreign Key",
                        "Target field is missing",
                        f"{expected_name}: target references unknown field {target_entity}.{field_name}.",
                        source_entity,
                        field_name,
                    )

            target_identity = next(
                (
                    entity.get("identity", {})
                    for entity in specification.get("entities", [])
                    if entity.get("name") == target_entity
                ),
                {},
            )

            target_identity_fields = (
                target_identity.get("fields", [])
                if isinstance(target_identity, dict)
                else []
            )

            if not target_identity_fields:
                valid = False
                add(
                    "error",
                    "Foreign Key",
                    "Target identity is missing",
                    f"{expected_name}: target entity '{target_entity}' must define an identity.",
                    source_entity,
                )
            elif target_fields != target_identity_fields:
                valid = False
                add(
                    "error",
                    "Foreign Key",
                    "Target fields do not match target identity",
                    f"{expected_name}: target fields must exactly match the target identity fields in the same order.",
                    source_entity,
                )

            mapping_key = (
                source_entity,
                tuple(source_fields),
                target_entity,
                tuple(target_fields),
            )

            if mapping_key in seen_mappings:
                valid = False
                add(
                    "error",
                    "Foreign Key",
                    "Duplicate foreign key mapping",
                    f"{expected_name}: duplicate foreign key mapping.",
                    source_entity,
                )

            seen_mappings.add(mapping_key)

            for source_field_name, target_field_name in zip(
                source_fields,
                target_fields,
            ):
                source_field = source_map.get(source_field_name)
                target_field = target_map.get(target_field_name)

                if source_field is None or target_field is None:
                    continue

                if source_field.get("type") != target_field.get("type"):
                    valid = False
                    add(
                        "error",
                        "Foreign Key",
                        "Incompatible foreign key field types",
                        f"{expected_name}: incompatible field types for "
                        f"{source_entity}.{source_field_name} "
                        f"({source_field.get('type')}) and "
                        f"{target_entity}.{target_field_name} "
                        f"({target_field.get('type')}).",
                        source_entity,
                        source_field_name,
                    )

            if valid:
                add(
                    "passed",
                    "Foreign Key",
                    "Foreign key is valid",
                    f"{source_entity}.{', '.join(source_fields)} "
                    f"maps to {target_entity}.{', '.join(target_fields)}.",
                    source_entity,
                )

    def _validate_constraints(
        self,
        specification: dict[str, Any],
        entity_names: set[str],
        fields_by_entity: dict[str, set[str]],
        add,
    ) -> None:
        for constraint in specification.get("constraints", []):
            entity = str(constraint.get("entity", "")).strip()
            field = str(constraint.get("field", "")).strip()
            operator = constraint.get("operator")

            valid = (
                bool(entity)
                and bool(field)
                and entity in entity_names
                and field in fields_by_entity.get(entity, set())
                and operator in {">", ">=", "<", "<=", "==", "!="}
            )

            if valid:
                add(
                    "passed",
                    "Constraint",
                    "Constraint is valid",
                    f"{entity}.{field} {operator} {constraint.get('value', '')}".strip(),
                    entity,
                    field,
                )
            else:
                add(
                    "error",
                    "Constraint",
                    "Invalid constraint",
                    f"{entity or 'Unknown'}.{field or 'Unknown'} references a missing entity, field, or unsupported operator.",
                    entity or None,
                    field or None,
                )

    @staticmethod
    def _validate_reference(
        reference: str,
        entity_names: set[str],
        fields_by_entity: dict[str, set[str]],
    ) -> bool:
        if "." not in reference:
            return False

        entity, field = reference.split(".", 1)

        return (
            entity in entity_names
            and field in fields_by_entity.get(entity, set())
        )

    @staticmethod
    def _build_entity_results(
        entities: list[dict[str, Any]],
        findings: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        results = []

        for entity in entities:
            name = entity.get("name", "Unnamed Entity")

            entity_findings = [
                finding
                for finding in findings
                if (
                    finding.get("entity") == name
                    or (
                        isinstance(finding.get("entity"), str)
                        and finding["entity"].split(".", 1)[0] == name
                    )
                )
            ]

            errors = sum(
                finding["severity"] == "error"
                for finding in entity_findings
            )

            warnings = sum(
                finding["severity"] == "warning"
                for finding in entity_findings
            )

            results.append(
                {
                    "name": name,
                    "status": (
                        "error"
                        if errors > 0
                        else "warning"
                        if warnings > 0
                        else "valid"
                    ),
                    "checks": len(entity_findings),
                    "errors": errors,
                    "warnings": warnings,
                }
            )

        return results
