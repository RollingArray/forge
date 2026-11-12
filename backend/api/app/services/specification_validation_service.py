"""
File: specification_validation_service.py
Purpose: Deterministic validation of the canonical FORGE specification.

The canonical specification is authoritative.
No LLM or UI logic belongs in this service.
"""

from decimal import Decimal, InvalidOperation
from typing import Any

from app.services.dependency_ordering import DependencyCycleError, resolve_dependency_order

from app.services.field_generation_validation import validate_field_generation
from app.services.relationship_endpoint import parse_relationship_endpoint
from app.services.population.constraint_analysis import (
    analyze_specification_constraints,
)


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
            remediation: str | None = None,
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
                    "remediation": remediation,
                }
            )

        if not isinstance(specification, dict):
            add(
                "error",
                "Specification",
                "Invalid specification structure",
                "The specification must be an object.",
            )
            specification = {}

        entities = specification.get("entities", [])
        if not isinstance(entities, list):
            add(
                "error",
                "Specification",
                "Invalid entities collection",
                "The specification entities value must be a list.",
            )
            entities = []

        if not entities:
            add(
                "error",
                "Specification",
                "No entities defined",
                "The specification must contain at least one entity.",
            )

        valid_entities = []
        for index, entity in enumerate(entities, start=1):
            if not isinstance(entity, dict):
                add(
                    "error",
                    "Entity",
                    "Invalid entity definition",
                    f"Entity entry {index} must be an object.",
                )
                continue
            valid_entities.append(entity)

        entities = valid_entities

        foreign_keys = specification.get("foreign_keys", [])
        if not isinstance(foreign_keys, list):
            add(
                "error",
                "Foreign Key",
                "Invalid foreign key collection",
                "The foreign_keys value must be a list.",
            )
            foreign_keys = []

        relationships = specification.get("relationships", [])
        if not isinstance(relationships, list):
            add(
                "error",
                "Relationship",
                "Invalid relationship collection",
                "The relationships value must be a list.",
            )
            relationships = []

        constraints = specification.get("constraints", [])
        if not isinstance(constraints, list):
            add(
                "error",
                "Constraint",
                "Invalid constraint collection",
                "The constraints value must be a list.",
            )
            constraints = []

        additional_sections = (
            ("dependencies", "Dependency"),
            ("statistical_behavior", "Statistical behavior"),
            ("scenarios", "Scenario"),
        )
        normalized_additional_sections = {}

        for section_name, label in additional_sections:
            section = specification.get(section_name, [])

            if not isinstance(section, list):
                add(
                    "error",
                    "Specification",
                    f"Invalid {section_name} collection",
                    f"The {section_name} value must be a list of objects.",
                )
                section = []

            normalized_additional_sections[section_name] = section

            for index, item in enumerate(section, start=1):
                if not isinstance(item, dict):
                    add(
                        "error",
                        "Specification",
                        f"Invalid {label.lower()} definition",
                        f"{section_name} entry {index} must be an object.",
                    )

        specification = {
            **specification,
            "entities": entities,
            "foreign_keys": foreign_keys,
            "relationships": relationships,
            "constraints": constraints,
            **normalized_additional_sections,
        }

        foreign_key_source_fields: set[tuple[str, str]] = set()
        foreign_keys = specification.get("foreign_keys", [])
        if isinstance(foreign_keys, list):
            for foreign_key in foreign_keys:
                if not isinstance(foreign_key, dict):
                    continue
                source = foreign_key.get("source")
                if not isinstance(source, dict):
                    continue
                source_entity = source.get("entity")
                source_fields = source.get("fields")
                if isinstance(source_entity, str) and isinstance(source_fields, list):
                    foreign_key_source_fields.update(
                        (source_entity.strip(), field_name)
                        for field_name in source_fields
                        if isinstance(field_name, str)
                    )

        entity_names: set[str] = set()

        for entity in entities:
            raw_name = entity.get("name")
            name = raw_name.strip() if isinstance(raw_name, str) else ""

            if not name:
                add(
                    "error",
                    "Entity",
                    "Invalid entity name",
                    "Every entity must have a non-empty string name.",
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
        field_types_by_entity: dict[str, dict[str, str]] = {}

        for entity in entities:
            raw_entity_name = entity.get("name")
            if not isinstance(raw_entity_name, str) or not raw_entity_name.strip():
                continue

            self._validate_entity(
                entity=entity,
                entity_names=entity_names,
                fields_by_entity=fields_by_entity,
                add=add,
            )

            raw_entity_name = entity.get("name")
            entity_name = (
                raw_entity_name.strip()
                if isinstance(raw_entity_name, str)
                else ""
            )
            fields = entity.get("fields", [])

            if entity_name and isinstance(fields, list):
                for field_definition in fields:
                    if not isinstance(field_definition, dict):
                        continue

                    raw_field_name = field_definition.get("name")
                    field_name = (
                        raw_field_name.strip()
                        if isinstance(raw_field_name, str)
                        else ""
                    )
                    field_type = field_definition.get("type")

                    supported_field_types = {
                        "IDENTIFIER",
                        "STRING",
                        "INTEGER",
                        "DECIMAL",
                        "BOOLEAN",
                        "CATEGORICAL",
                    }

                    # Missing types are reported by entity validation.
                    if field_type is None or (
                        isinstance(field_type, str) and not field_type.strip()
                    ):
                        continue

                    if (
                        not isinstance(field_type, str)
                        or field_type not in supported_field_types
                    ):
                        add(
                            "error",
                            "Entity",
                            "Unsupported field type",
                            (
                                f"Field '{field_name or 'Unnamed'}' uses "
                                f"unsupported type {field_type!r}. Supported "
                                "types are IDENTIFIER, STRING, INTEGER, "
                                "DECIMAL, BOOLEAN and CATEGORICAL."
                            ),
                            entity_name,
                            field_name or None,
                        )
                        continue

                    is_fk_source = (
                        entity_name,
                        field_name,
                    ) in foreign_key_source_fields

                    for error in validate_field_generation(
                        field_definition,
                        require_generation=(
                            not is_fk_source or field_type == "IDENTIFIER"
                        ),
                    ):
                        add(
                            "error",
                            "Generation",
                            "Invalid field generation configuration",
                            error,
                            entity_name,
                            field_name or None,
                        )

            if entity_name:
                safe_fields = entity.get("fields", [])
                if not isinstance(safe_fields, list):
                    safe_fields = []
                field_types_by_entity[entity_name] = {
                    field["name"].strip(): field["type"].strip().upper()
                    for field in safe_fields
                    if isinstance(field, dict)
                    and isinstance(field.get("name"), str)
                    and field["name"].strip()
                    and isinstance(field.get("type"), str)
                }

        raw_version = specification.get("version")
        version = raw_version.strip() if isinstance(raw_version, str) else ""

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

        raw_vocabulary_version = specification.get("vocabulary_version")
        vocabulary_version = (
            raw_vocabulary_version.strip()
            if isinstance(raw_vocabulary_version, str)
            else ""
        )

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

        model = specification.get("model")
        model_is_object = isinstance(model, dict)
        if not model_is_object:
            add(
                "error",
                "Model",
                "Invalid model definition",
                "The specification model value must be an object.",
            )
            model = {}

        model_name_value = model.get("name")
        model_name = (
            model_name_value.strip()
            if isinstance(model_name_value, str)
            else ""
        )
        if model_is_object and model_name:
            add(
                "passed",
                "Model",
                "Model definition is valid",
                f"Model '{model_name}' is defined.",
            )
        elif model_is_object:
            add(
                "error",
                "Model",
                "Model name is missing",
                "The specification must identify the model with a non-empty string.",
            )

        generation = specification.get("generation")
        generation_is_object = isinstance(generation, dict)
        if not generation_is_object:
            add(
                "error",
                "Generation",
                "Invalid generation definition",
                "The specification generation value must be an object.",
            )
            generation = {}
        seed = generation.get("seed")

        if generation_is_object and isinstance(seed, int) and not isinstance(seed, bool):
            add(
                "passed",
                "Generation",
                "Generation seed is valid",
                f"Seed {seed} is configured.",
            )
        elif generation_is_object:
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

        valid_foreign_key_names = self._validate_foreign_keys(
            specification=specification,
            entity_names=entity_names,
            fields_by_entity=fields_by_entity,
            add=add,
        )

        self._validate_constraints(
            specification=specification,
            entity_names=entity_names,
            fields_by_entity=fields_by_entity,
            field_types_by_entity=field_types_by_entity,
            add=add,
        )

        # Capability analysis is independent of structural validation.
        # Run it even when structural findings exist so users see all
        # specification issues in one validation pass.
        # Population settings are neutralized inside the capability pass.
        self._validate_capabilities(
            specification=specification,
            valid_foreign_key_names=valid_foreign_key_names,
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

        unsupported = sum(
            finding["severity"] == "unsupported"
            for finding in findings
        )

        return {
            "model_name": model_name or "Untitled Model",
            "specification_version": version or "Unknown",
            "vocabulary_version": vocabulary_version or "Unknown",
            "errors": errors,
            "warnings": warnings,
            "unsupported": unsupported,
            "passed": passed,
            "total_checks": len(findings),
            "entities_validated": len(entities),
            "can_continue": errors == 0 and unsupported == 0,
            "findings": findings,
            "entities": self._build_entity_results(
                entities,
                findings,
            ),
        }

    def _validate_capabilities(
        self,
        specification: dict[str, Any],
        valid_foreign_key_names: set[str],
        add,
    ) -> None:
        """Validate identity and relationship capabilities without populations.

        Structural validators own malformed entity/FK/relationship definitions.
        This pass contributes identity capability, FK identity composition,
        relationship mapping, and dependency-cycle findings without repeating
        structural diagnostics.
        """
        safe_entities: list[dict[str, Any]] = []
        safe_entity_names: set[str] = set()

        for entity in specification.get("entities", []):
            if not isinstance(entity, dict):
                continue
            name = entity.get("name")
            if not isinstance(name, str) or not name.strip():
                continue
            fields = entity.get("fields", [])
            if not isinstance(fields, list):
                fields = []
            safe_fields = []
            for field_spec in fields:
                if not isinstance(field_spec, dict):
                    continue
                field_name = field_spec.get("name")
                if not isinstance(field_name, str) or not field_name.strip():
                    continue
                normalized_field = dict(field_spec)
                if not isinstance(normalized_field.get("identity"), dict):
                    normalized_field["identity"] = {}
                if not isinstance(normalized_field.get("generation"), dict):
                    normalized_field["generation"] = {}
                generation = normalized_field["generation"]
                if not isinstance(generation.get("parameters"), dict):
                    generation["parameters"] = {}
                safe_fields.append(normalized_field)

            identity = entity.get("identity")
            if not isinstance(identity, dict):
                identity = {"fields": []}
            else:
                identity_fields = identity.get("fields", [])
                if not isinstance(identity_fields, list):
                    identity_fields = []
                identity = {
                    **identity,
                    "fields": [
                        item for item in identity_fields
                        if isinstance(item, str) and item.strip()
                    ],
                }

            safe_entities.append({
                **entity,
                "name": name.strip(),
                "fields": safe_fields,
                "identity": identity,
                "population": {"count": None, "scaling": "SCALABLE"},
            })
            safe_entity_names.add(name.strip())

        safe_foreign_keys = []
        raw_foreign_keys = specification.get("foreign_keys", [])
        if isinstance(raw_foreign_keys, list):
            for foreign_key in raw_foreign_keys:
                if not isinstance(foreign_key, dict):
                    continue
                source = foreign_key.get("source")
                target = foreign_key.get("target")
                if not isinstance(source, dict) or not isinstance(target, dict):
                    continue
                child = source.get("entity")
                parent = target.get("entity")
                child_fields = source.get("fields")
                parent_fields = target.get("fields")
                if (
                    not isinstance(child, str)
                    or not isinstance(parent, str)
                    or child.strip() not in safe_entity_names
                    or parent.strip() not in safe_entity_names
                    or not isinstance(child_fields, list)
                    or not isinstance(parent_fields, list)
                    or not child_fields
                    or len(child_fields) != len(parent_fields)
                    or not all(isinstance(item, str) and item.strip() for item in child_fields)
                    or not all(isinstance(item, str) and item.strip() for item in parent_fields)
                ):
                    continue
                safe_foreign_keys.append({
                    **foreign_key,
                    "source": {**source, "entity": child.strip()},
                    "target": {**target, "entity": parent.strip()},
                })

        raw_relationships = specification.get("relationships", [])
        safe_relationships = (
            raw_relationships if isinstance(raw_relationships, list) else []
        )
        capability_specification = {
            **specification,
            "entities": safe_entities,
            "foreign_keys": safe_foreign_keys,
            "relationships": safe_relationships,
        }

        try:
            analysis = analyze_specification_constraints(capability_specification)
        except (AttributeError, KeyError, TypeError, ValueError) as exc:
            add(
                "error",
                "Specification",
                "Capability validation could not complete",
                (
                    "FORGE could not complete identity and relationship "
                    f"capability validation: {exc}"
                ),
                remediation=(
                    "Correct malformed identity, foreign-key, or relationship "
                    "definitions in Model Studio and validate again."
                ),
            )
            return

        structural_diagnostics_owned_by_validator = {
            # Entity structure is authoritatively checked by _validate_entity.
            "INVALID_ENTITIES",
            "EMPTY_ENTITIES",
            "INVALID_ENTITY",
            "DUPLICATE_ENTITY",
            # Foreign-key structure is authoritatively checked by
            # _validate_foreign_keys.
            "INVALID_FOREIGN_KEYS",
            "INVALID_FOREIGN_KEY",
            "INVALID_FOREIGN_KEY_ENDPOINT",
            "INVALID_FOREIGN_KEY_MAPPING",
            "SELF_REFERENCING_FOREIGN_KEY",
            "DUPLICATE_FOREIGN_KEY_FIELD",
            "FOREIGN_KEY_FIELD_MISSING",
            "FOREIGN_KEY_PARENT_IDENTITY_MISSING",
            "FOREIGN_KEY_TARGET_IDENTITY_MISMATCH",
            # Relationship declaration structure is checked by
            # _validate_relationships.
            "INVALID_RELATIONSHIPS",
            "INVALID_RELATIONSHIP",
            "INVALID_RELATIONSHIP_ENDPOINT",
            "INVALID_RELATIONSHIP_PARTICIPATION",
            "UNSUPPORTED_RELATIONSHIP_TYPE",
            "UNKNOWN_RELATIONSHIP_ENTITY",
            "UNKNOWN_RELATIONSHIP_FIELD",
            # Identity field structure is checked by _validate_entity.
            "INVALID_IDENTITY_FIELDS",
            "IDENTITY_FIELD_MISSING",
        }

        population_diagnostics_owned_by_planner = {
            "INVALID_POPULATION_COUNT",
            "UNSUPPORTED_SCALING",
            "FIXED_COUNT_MISSING",
        }

        suppressed_diagnostics = (
            structural_diagnostics_owned_by_validator
            | population_diagnostics_owned_by_planner
        )

        for diagnostic in analysis.diagnostics:
            code = diagnostic.get("code", "CAPABILITY_VALIDATION")
            if code in suppressed_diagnostics:
                continue

            message = diagnostic.get("message", "Capability check failed.")
            subject = diagnostic.get("subject", "")
            is_relationship = (
                "RELATIONSHIP" in code
                or code == "UNSUPPORTED_MANY_TO_MANY"
            )
            is_unsupported = (
                code == "UNSUPPORTED_LOCAL_IDENTITY"
                or code == "UNSUPPORTED_MANY_TO_MANY"
            )

            if code == "UNSUPPORTED_LOCAL_IDENTITY":
                category = "Generation"
                remediation = (
                    "Choose an identity configuration supported by FORGE, "
                    "such as a sequential identifier or a supported finite "
                    "identity domain."
                )
            elif is_relationship:
                category = "Relationship"
                remediation = (
                    "Correct the relationship endpoints and cardinality, or "
                    "add one complete ordered foreign-key mapping in the "
                    "direction required by the declared relationship."
                    if not is_unsupported
                    else "Model the association explicitly using supported "
                    "junction-entity and foreign-key definitions."
                )
            else:
                category = "Entity" if "IDENTITY" in code else "Foreign Key"
                remediation = (
                    "Correct the identity or foreign-key definition in "
                    "Model Studio and validate the specification again."
                )

            entity = None
            field = None
            if category == "Generation" and isinstance(subject, str) and "." in subject:
                entity, field = subject.split(".", 1)
            elif category == "Entity":
                entity = subject or None

            severity = "unsupported" if is_unsupported else "error"
            add(
                severity,
                category,
                code.replace("_", " ").title(),
                message,
                entity,
                field,
                remediation,
            )

        # A relationship is reported as passed only after the canonical
        # resolver has established exactly one complete ordered FK mapping.
        seen_mapped: set[tuple[str, str, str, str]] = set()
        for relationship in analysis.relationships:
            if (
                relationship.status != "MAPPED"
                or not relationship.fk_name
                or relationship.fk_name not in valid_foreign_key_names
            ):
                continue
            key = (
                relationship.source,
                relationship.target,
                relationship.relationship_type,
                relationship.fk_name,
            )
            if key in seen_mapped:
                continue
            seen_mapped.add(key)
            add(
                "passed",
                "Relationship",
                "Relationship mapping is valid",
                (
                    f"{relationship.source} → {relationship.target} is mapped "
                    f"through {relationship.fk_name} ({relationship.fk_direction}). "
                    f"Child entity: {relationship.child_entity}; parent entity: "
                    f"{relationship.parent_entity}. Endpoint fields match in "
                    "the declared order. Row-level cardinality and participation "
                    "remain subject to generation-time verification."
                ),
                relationship.child_entity,
            )

        self._validate_dependency_cycles(
            specification=capability_specification,
            add=add,
        )

    def _validate_dependency_cycles(
        self,
        specification: dict[str, Any],
        add,
    ) -> None:
        """Reject FK dependency graphs that cannot be topologically ordered."""

        entities = specification.get("entities", [])
        foreign_keys = specification.get("foreign_keys", [])

        entity_names = {
            entity.get("name")
            for entity in entities
            if isinstance(entity, dict)
            and isinstance(entity.get("name"), str)
            and entity.get("name")
        }

        dependencies: list[tuple[str, str]] = []

        for foreign_key in foreign_keys:
            if not isinstance(foreign_key, dict):
                continue

            source = foreign_key.get("source")
            target = foreign_key.get("target")

            if not isinstance(source, dict) or not isinstance(target, dict):
                continue

            child = source.get("entity")
            parent = target.get("entity")

            if (
                isinstance(child, str)
                and isinstance(parent, str)
                and child in entity_names
                and parent in entity_names
            ):
                dependencies.append((parent, child))

        try:
            resolve_dependency_order(
                sorted(entity_names),
                dependencies,
            )
        except DependencyCycleError as exc:
            add(
                "error",
                "Foreign Key",
                "Foreign-key dependency cycle detected",
                (
                    "FORGE cannot establish a valid generation order because "
                    "the foreign-key dependency graph contains a cycle "
                    f"involving: {', '.join(exc.unresolved_entities)}. "
                    "Revise the dependencies so parent entities can be "
                    "generated before their dependent child entities."
                ),
            )


    def _validate_entity(
        self,
        entity: dict[str, Any],
        entity_names: set[str],
        fields_by_entity: dict[str, set[str]],
        add,
    ) -> None:
        raw_name = entity.get("name")
        name = raw_name.strip() if isinstance(raw_name, str) else ""

        if not name:
            add(
                "error",
                "Entity",
                "Invalid entity name",
                "Entity name must be a non-empty string.",
            )
            return

        fields = entity.get("fields", [])
        field_names: set[str] = set()
        valid = True

        if not isinstance(fields, list):
            add(
                "error",
                "Entity",
                "Invalid field collection",
                f"Entity '{name}' fields must be a list.",
                name,
            )
            fields = []
            valid = False

        for index, field in enumerate(fields, start=1):
            if not isinstance(field, dict):
                add(
                    "error",
                    "Entity",
                    "Invalid field definition",
                    f"Field entry {index} in entity '{name}' must be an object.",
                    name,
                )
                valid = False
                continue

            raw_field_name = field.get("name")
            field_name = (
                raw_field_name.strip()
                if isinstance(raw_field_name, str)
                else ""
            )

            if not field_name:
                valid = False
                add(
                    "error",
                    "Entity",
                    "Invalid field name",
                    f"Entity '{name}' contains a field without a non-empty string name.",
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

        identity = entity.get("identity")
        if identity is None:
            identity_fields: list[str] = []
            identity_missing = True
        elif not isinstance(identity, dict):
            valid = False
            identity_fields = []
            identity_missing = False
            add(
                "error",
                "Entity",
                "Invalid identity definition",
                f"Entity '{name}' identity must be an object containing a fields list.",
                name,
            )
        else:
            raw_identity_fields = identity.get("fields", [])
            identity_missing = isinstance(raw_identity_fields, list) and not raw_identity_fields
            if not isinstance(raw_identity_fields, list):
                valid = False
                identity_fields = []
                add(
                    "error",
                    "Entity",
                    "Invalid identity fields",
                    f"Entity '{name}' identity.fields must be a list of field names.",
                    name,
                )
            else:
                identity_fields = [
                    item for item in raw_identity_fields
                    if isinstance(item, str) and item.strip()
                ]
                if len(identity_fields) != len(raw_identity_fields):
                    valid = False
                    add(
                        "error",
                        "Entity",
                        "Invalid identity field",
                        f"Entity '{name}' identity fields must be non-empty strings.",
                        name,
                    )

        if identity_missing:
            valid = False
            add(
                "error",
                "Entity",
                "Identity definition is missing",
                f"Entity '{name}' does not define an identity field.",
                name,
            )
        elif identity_fields:
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
                if identity_field not in field_names:
                    valid = False
                    add(
                        "error",
                        "Entity",
                        "Identity field is missing",
                        f"Identity field '{identity_field}' is not defined on '{name}'.",
                        name,
                        identity_field,
                    )

        if valid:
            add(
                "passed",
                "Entity",
                "Entity structure is valid",
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
        """Validate canonical structured relationship endpoints."""

        relationships = specification.get("relationships", [])

        valid_types = {
            "ONE_TO_ONE",
            "ONE_TO_MANY",
            "MANY_TO_ONE",
            "MANY_TO_MANY",
        }
        valid_participation = {"MANDATORY", "OPTIONAL"}
        seen_relationships: set[tuple] = set()

        for index, relationship in enumerate(relationships, start=1):
            if not isinstance(relationship, dict):
                add(
                    "error",
                    "Relationship",
                    "Invalid relationship definition",
                    f"Relationship entry {index} must be an object.",
                )
                continue

            endpoints: dict[str, Any] = {}
            endpoint_valid: dict[str, bool] = {}

            for role in ("source", "target"):
                raw = relationship.get(role)
                parsed = None
                valid = True

                try:
                    parsed = parse_relationship_endpoint(raw, role)
                except ValueError as exc:
                    add(
                        "error",
                        "Relationship",
                        f"Invalid {role} endpoint",
                        str(exc),
                        None,
                    )
                    valid = False

                if parsed is not None:
                    entity = parsed.entity
                    fields = parsed.fields

                    if entity not in entity_names:
                        add(
                            "error",
                            "Relationship",
                            f"Unknown {role} entity",
                            (
                                f"{role.capitalize()} entity '{entity}' "
                                "is not defined in the specification."
                            ),
                            entity,
                        )
                        valid = False
                    else:
                        for field in fields:
                            if field not in fields_by_entity.get(entity, set()):
                                add(
                                    "error",
                                    "Relationship",
                                    f"Unknown {role} field",
                                    (
                                        f"{role.capitalize()} field "
                                        f"'{entity}.{field}' is not defined "
                                        "in the specification."
                                    ),
                                    entity,
                                    field,
                                )
                                valid = False

                    endpoints[role] = parsed

                endpoint_valid[role] = valid

            source_endpoint = endpoints.get("source")
            target_endpoint = endpoints.get("target")
            source_entity = (
                source_endpoint.entity if source_endpoint else None
            )
            target_entity = (
                target_endpoint.entity if target_endpoint else None
            )
            source_field = (
                source_endpoint.fields[0]
                if source_endpoint and source_endpoint.fields
                else None
            )

            relationship_type = relationship.get("type")
            if not isinstance(relationship_type, str) or relationship_type not in valid_types:
                add(
                    "error",
                    "Relationship",
                    "Invalid relationship type",
                    (
                        f"Relationship uses invalid type "
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

            if (
                source_endpoint is not None
                and target_endpoint is not None
                and isinstance(relationship_type, str)
                and isinstance(source_participation, str)
                and isinstance(target_participation, str)
            ):
                relationship_key = (
                    source_endpoint.entity,
                    source_endpoint.fields,
                    target_endpoint.entity,
                    target_endpoint.fields,
                    relationship_type.strip().upper(),
                    source_participation.strip().upper(),
                    target_participation.strip().upper(),
                )
                if relationship_key in seen_relationships:
                    add(
                        "error",
                        "Relationship",
                        "Duplicate relationship definition",
                        (
                            f"Relationship {source_endpoint.reference} → "
                            f"{target_endpoint.reference} is declared more than once."
                        ),
                        source_entity,
                        source_field,
                    )
                else:
                    seen_relationships.add(relationship_key)

            if not isinstance(source_participation, str) or source_participation not in valid_participation:
                add(
                    "error",
                    "Relationship",
                    "Invalid source participation",
                    (
                        f"Relationship uses invalid source participation "
                        f"'{source_participation}'. Expected MANDATORY "
                        "or OPTIONAL."
                    ),
                    source_entity,
                    source_field,
                )

            if not isinstance(target_participation, str) or target_participation not in valid_participation:
                add(
                    "error",
                    "Relationship",
                    "Invalid target participation",
                    (
                        f"Relationship uses invalid target participation "
                        f"'{target_participation}'. Expected MANDATORY "
                        "or OPTIONAL."
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
    ) -> set[str]:
        foreign_keys = specification.get("foreign_keys", [])
        valid_foreign_key_names: set[str] = set()
        seen_names: set[str] = set()
        seen_mappings: set[tuple] = set()
        name_counts: dict[str, int] = {}
        for item in foreign_keys:
            if isinstance(item, dict) and isinstance(item.get("name"), str):
                candidate_name = item["name"].strip()
                if candidate_name:
                    name_counts[candidate_name] = name_counts.get(candidate_name, 0) + 1
        seen_source_fields: dict[tuple[str, str], str] = {}

        field_maps = {}
        for entity in specification.get("entities", []):
            if not isinstance(entity, dict):
                continue
            entity_name = entity.get("name")
            fields = entity.get("fields", [])
            if not isinstance(entity_name, str) or not isinstance(fields, list):
                continue
            field_maps[entity_name.strip()] = {
                field.get("name"): field
                for field in fields
                if isinstance(field, dict)
                and isinstance(field.get("name"), str)
            }

        for foreign_key in foreign_keys:
            if not isinstance(foreign_key, dict):
                add(
                    "error",
                    "Foreign Key",
                    "Invalid foreign key definition",
                    "Every foreign key must be an object.",
                )
                continue

            name = str(foreign_key.get("name", "")).strip()

            source = foreign_key.get("source")
            target = foreign_key.get("target")

            if not isinstance(source, dict):
                add(
                    "error",
                    "Foreign Key",
                    "Invalid foreign key source",
                    (
                        f"Foreign key '{name or 'unnamed'}' must define "
                        "source as an object containing entity and fields."
                    ),
                )
                continue

            if not isinstance(target, dict):
                add(
                    "error",
                    "Foreign Key",
                    "Invalid foreign key target",
                    (
                        f"Foreign key '{name or 'unnamed'}' must define "
                        "target as an object containing entity and fields."
                    ),
                    str(source.get("entity", "")).strip() or None,
                )
                continue

            source_entity_value = source.get("entity")
            target_entity_value = target.get("entity")

            if not isinstance(source_entity_value, str):
                add(
                    "error",
                    "Foreign Key",
                    "Invalid source entity",
                    (
                        f"Foreign key '{name or 'unnamed'}' must define "
                        "source.entity as a string."
                    ),
                )
                continue

            if not isinstance(target_entity_value, str):
                add(
                    "error",
                    "Foreign Key",
                    "Invalid target entity",
                    (
                        f"Foreign key '{name or 'unnamed'}' must define "
                        "target.entity as a string."
                    ),
                    source_entity_value.strip() or None,
                )
                continue

            source_entity = source_entity_value.strip()
            target_entity = target_entity_value.strip()

            source_fields = source.get("fields")
            target_fields = target.get("fields")

            if (
                not isinstance(source_fields, list)
                or not source_fields
                or not all(
                    isinstance(field, str) and field.strip()
                    for field in source_fields
                )
                or not isinstance(target_fields, list)
                or not target_fields
                or not all(
                    isinstance(field, str) and field.strip()
                    for field in target_fields
                )
            ):
                add(
                    "error",
                    "Foreign Key",
                    "Invalid foreign key fields",
                    (
                        f"Foreign key '{name or 'unnamed'}' must define "
                        "non-empty source.fields and target.fields arrays "
                        "containing field names."
                    ),
                    source_entity or None,
                )
                continue

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

            if name and name_counts.get(name, 0) > 1:
                valid = False
                if name not in seen_names:
                    add(
                        "error",
                        "Foreign Key",
                        "Duplicate foreign key name",
                        f"Foreign key '{name}' is defined more than once.",
                        source_entity or None,
                    )
            elif name and name in seen_names:
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

            if (
                source_entity in entity_names
                and all(
                    isinstance(field_name, str)
                    and field_name in source_map
                    for field_name in source_fields
                )
                and len(source_fields) == len(set(source_fields))
            ):
                overlapping_fields = []

                for field_name in source_fields:
                    key = (source_entity, field_name)
                    previous_fk = seen_source_fields.get(key)

                    if previous_fk is not None:
                        overlapping_fields.append(
                            (field_name, previous_fk)
                        )
                    else:
                        seen_source_fields[key] = name or expected_name

                if overlapping_fields:
                    valid = False

                    details = "; ".join(
                        f"{source_entity}.{field_name} is already assigned "
                        f"by '{previous_fk}'"
                        for field_name, previous_fk in overlapping_fields
                    )

                    add(
                        "error",
                        "Foreign Key",
                        "Overlapping source field assignments",
                        (
                            f"{name or expected_name}: source fields "
                            f"conflict with another foreign key: {details}."
                        ),
                        source_entity,
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
                    if isinstance(entity, dict)
                    and isinstance(entity.get("name"), str)
                    and entity["name"].strip() == target_entity
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
                valid_foreign_key_names.add(name)
                add(
                    "passed",
                    "Foreign Key",
                    "Foreign key declaration is valid",
                    f"Foreign key '{name}' maps "
                    f"{source_entity}.{', '.join(source_fields)} "
                    f"to {target_entity}.{', '.join(target_fields)}.",
                    source_entity,
                )

        return valid_foreign_key_names

    def _validate_constraints(
        self,
        specification: dict[str, Any],
        entity_names: set[str],
        fields_by_entity: dict[str, set[str]],
        field_types_by_entity: dict[str, dict[str, str]],
        add,
    ) -> None:
        supported_operators = {
            "INTEGER": {">", ">=", "<", "<="},
            "DECIMAL": {">", ">=", "<", "<="},
            "STRING": {"==", "!="},
            "CATEGORICAL": {"==", "!="},
        }

        constraints = specification.get("constraints", [])

        for index, constraint in enumerate(constraints, start=1):
            if not isinstance(constraint, dict):
                add(
                    "error",
                    "Constraint",
                    "Invalid constraint definition",
                    f"Constraint entry {index} must be an object.",
                )
                continue

            entity = str(constraint.get("entity", "")).strip()
            field = str(constraint.get("field", "")).strip()
            operator = constraint.get("operator")
            value = constraint.get("value")
            field_type = field_types_by_entity.get(entity, {}).get(field)
            reason = None

            if not entity:
                reason = "constraint entity is required."
            elif entity not in entity_names:
                reason = f"referenced entity '{entity}' does not exist."
            elif not field:
                reason = "constraint field is required."
            elif field not in fields_by_entity.get(entity, set()):
                reason = (
                    f"referenced field '{entity}.{field}' does not exist."
                )
            elif (
                not isinstance(operator, str)
                or operator not in supported_operators.get(field_type, set())
            ):
                reason = (
                    f"operator {operator!r} is not supported for "
                    f"field type {field_type!r}."
                )
            elif "value" not in constraint:
                reason = "comparison value is required."

            if reason is None and field_type in {"INTEGER", "DECIMAL"}:
                try:
                    if isinstance(value, bool) or value is None:
                        raise ValueError(
                            "Boolean or null values are not numeric."
                        )

                    if field_type == "DECIMAL":
                        if not isinstance(value, str):
                            raise ValueError(
                                "DECIMAL constraint values must be strings."
                            )
                        number = Decimal(value)
                    else:
                        number = Decimal(str(value))

                    if not number.is_finite():
                        raise ValueError("Value must be finite.")

                    if (
                        field_type == "INTEGER"
                        and number != number.to_integral_value()
                    ):
                        raise ValueError("Value must be an integer.")

                except (InvalidOperation, TypeError, ValueError):
                    reason = (
                        "comparison value must be a valid "
                        f"{'decimal string' if field_type == 'DECIMAL' else 'integer'}."
                    )

            if reason is None:
                add(
                    "passed",
                    "Constraint",
                    "Constraint is valid",
                    f"{entity}.{field} {operator} {value}".strip(),
                    entity,
                    field,
                )
            else:
                add(
                    "error",
                    "Constraint",
                    "Invalid constraint",
                    f"{entity or 'Unknown'}.{field or 'Unknown'} {reason}",
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

            unsupported = sum(
                finding["severity"] == "unsupported"
                for finding in entity_findings
            )

            results.append(
                {
                    "name": name,
                    "status": (
                        "error"
                        if errors > 0 or unsupported > 0
                        else "warning"
                        if warnings > 0
                        else "valid"
                    ),
                    "checks": len(entity_findings),
                    "errors": errors,
                    "warnings": warnings,
                    "unsupported": unsupported,
                }
            )

        return results
