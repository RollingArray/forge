from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.services.generation.artifact_reader import GenerationArtifactReader
from app.services.generation.value_conversion import convert_value


class GenerationValidationError(ValueError):
    """Raised when generated data fails production validation."""


@dataclass
class ValidationEvidence:
    """Measured evidence collected during production dataset validation."""

    completeness: dict[str, Any] = field(default_factory=dict)
    schema: dict[str, Any] = field(default_factory=dict)
    primary_keys: dict[str, Any] = field(default_factory=dict)
    foreign_keys: dict[str, Any] = field(default_factory=dict)
    constraints: dict[str, Any] = field(default_factory=dict)
    domain_validity: dict[str, Any] = field(default_factory=dict)
    null_completeness: dict[str, Any] = field(default_factory=dict)
    coverage: dict[str, Any] = field(default_factory=dict)
    rule_results: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Return machine-readable validation evidence."""

        return {
            "completeness": self.completeness,
            "schema": self.schema,
            "primary_keys": self.primary_keys,
            "foreign_keys": self.foreign_keys,
            "constraints": self.constraints,
            "domain_validity": self.domain_validity,
            "null_completeness": self.null_completeness,
            "coverage": self.coverage,
            "rule_results": self.rule_results,
        }


@dataclass
class GenerationValidationResult:
    valid: bool
    entity_count: int
    generated_rows: int
    expected_rows: int
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    evidence: ValidationEvidence = field(
        default_factory=ValidationEvidence,
    )

    @property
    def error_count(self) -> int:
        return len(self.errors)


class GenerationValidator:
    """Validate committed generated artifacts against the specification."""

    def __init__(
        self,
        *,
        artifact_reader: GenerationArtifactReader | None = None,
    ) -> None:
        self._artifact_reader = (
            artifact_reader
            if artifact_reader is not None
            else GenerationArtifactReader()
        )

    def validate(
        self,
        *,
        specification: dict[str, Any],
        data_model_id: str,
        job_id: str,
    ) -> GenerationValidationResult:
        errors: list[str] = []
        warnings: list[str] = []
        evidence = ValidationEvidence()

        entities = specification.get("entities", [])
        foreign_keys = specification.get("foreign_keys", [])

        expected_rows = 0
        generated_rows = 0
        completeness_entities: dict[str, Any] = {}

        entity_map = {
            entity["name"]: entity
            for entity in entities
        }

        field_types = {
            entity["name"]: {
                field["name"]: field.get("type")
                for field in entity.get("fields", [])
            }
            for entity in entities
        }

        # ------------------------------------------------------------
        # 1. Population counts
        # ------------------------------------------------------------

        for entity in entities:
            entity_name = entity["name"]
            expected = (
                entity.get("population") or {}
            ).get("count", 0)

            actual = self._count_rows(
                data_model_id=data_model_id,
                job_id=job_id,
                entity_name=entity_name,
            )

            difference = actual - expected
            complete = actual == expected

            expected_rows += expected
            generated_rows += actual

            completeness_entities[entity_name] = {
                "requested_rows": expected,
                "generated_rows": actual,
                "difference": difference,
                "complete": complete,
            }

            if not complete:
                errors.append(
                    f"{entity_name}: expected {expected:,} rows, "
                    f"generated {actual:,}."
                )

        evidence.completeness = {
            "entities_checked": len(completeness_entities),
            "entities_complete": sum(
                1
                for metric in completeness_entities.values()
                if metric["complete"]
            ),
            "total_requested_rows": expected_rows,
            "total_generated_rows": generated_rows,
            "difference": generated_rows - expected_rows,
            "complete": (
                generated_rows == expected_rows
                and all(
                    metric["complete"]
                    for metric in completeness_entities.values()
                )
            ),
            "entities": completeness_entities,
        }

        # ------------------------------------------------------------
        # 2. Identity uniqueness
        # ------------------------------------------------------------

        identity_entities: dict[str, Any] = {}

        for entity in entities:
            entity_name = entity["name"]
            identity_fields = (
                entity.get("identity") or {}
            ).get("fields", [])

            if not identity_fields:
                continue

            seen: set[tuple[Any, ...]] = set()
            duplicate_count = 0
            missing_field_count = 0
            rows_checked = 0

            for row_number, row in enumerate(
                self._iter_typed_rows(
                    data_model_id=data_model_id,
                    job_id=job_id,
                    entity_name=entity_name,
                    field_types=field_types[entity_name],
                ),
                start=1,
            ):
                rows_checked += 1

                try:
                    identity = tuple(
                        row[field]
                        for field in identity_fields
                    )
                except KeyError as exc:
                    missing_field_count += 1
                    errors.append(
                        f"{entity_name}: identity field "
                        f"{exc.args[0]!r} missing at row "
                        f"{row_number}."
                    )
                    continue

                if identity in seen:
                    duplicate_count += 1
                    errors.append(
                        f"{entity_name}: duplicate identity "
                        f"{identity!r} at row {row_number}."
                    )
                else:
                    seen.add(identity)

            identity_entities[entity_name] = {
                "rows_checked": rows_checked,
                "unique_identities": len(seen),
                "duplicate_count": duplicate_count,
                "missing_field_count": missing_field_count,
                "identity_fields": list(identity_fields),
            }

        evidence.primary_keys = {
            "entities_checked": len(identity_entities),
            "entities": identity_entities,
            "rows_checked": sum(
                metric["rows_checked"]
                for metric in identity_entities.values()
            ),
            "duplicate_count": sum(
                metric["duplicate_count"]
                for metric in identity_entities.values()
            ),
            "missing_field_count": sum(
                metric["missing_field_count"]
                for metric in identity_entities.values()
            ),
        }

        # ------------------------------------------------------------
        # 3. Constraint validation
        # ------------------------------------------------------------

        operators = {
            ">": lambda actual, expected: actual > expected,
            ">=": lambda actual, expected: actual >= expected,
            "<": lambda actual, expected: actual < expected,
            "<=": lambda actual, expected: actual <= expected,
            "==": lambda actual, expected: actual == expected,
            "!=": lambda actual, expected: actual != expected,
        }

        constraint_metrics: dict[str, Any] = {}

        for index, constraint in enumerate(
            specification.get("constraints", []),
            start=1,
        ):
            entity_name = constraint["entity"]
            field_name = constraint["field"]
            operator = constraint["operator"]
            expected = constraint["value"]

            constraint_name = (
                constraint.get("name")
                or f"constraint_{index}"
            )

            predicate = operators.get(operator)

            violation_count = 0
            missing_field_count = 0
            evaluation_error_count = 0
            rows_checked = 0

            if predicate is None:
                evaluation_error_count += 1
                errors.append(
                    f"{entity_name}.{field_name}: "
                    f"unsupported constraint operator "
                    f"{operator!r}."
                )

                constraint_metrics[constraint_name] = {
                    "entity": entity_name,
                    "field": field_name,
                    "operator": operator,
                    "expected": expected,
                    "rows_checked": 0,
                    "violation_count": 0,
                    "missing_field_count": 0,
                    "evaluation_error_count": evaluation_error_count,
                }
                continue

            field_type = field_types.get(
                entity_name,
                {},
            ).get(field_name)

            typed_expected = None

            try:
                typed_expected = self._convert_value(
                    expected,
                    field_type,
                )
            except (TypeError, ValueError) as exc:
                evaluation_error_count += 1
                errors.append(
                    f"{entity_name}.{field_name}: "
                    f"constraint comparison failed while "
                    f"converting expected value "
                    f"{expected!r}: {exc}"
                )

                constraint_metrics[constraint_name] = {
                    "entity": entity_name,
                    "field": field_name,
                    "operator": operator,
                    "expected": expected,
                    "rows_checked": 0,
                    "violation_count": 0,
                    "missing_field_count": 0,
                    "evaluation_error_count": evaluation_error_count,
                }
                continue

            for row_number, row in enumerate(
                self._iter_typed_rows(
                    data_model_id=data_model_id,
                    job_id=job_id,
                    entity_name=entity_name,
                    field_types=field_types.get(entity_name, {}),
                ),
                start=1,
            ):
                rows_checked += 1

                if field_name not in row:
                    missing_field_count += 1
                    errors.append(
                        f"{entity_name}: constraint field "
                        f"{field_name!r} missing at row "
                        f"{row_number}."
                    )
                    continue

                actual = row[field_name]

                try:
                    satisfied = predicate(
                        actual,
                        typed_expected,
                    )
                except (TypeError, ValueError) as exc:
                    evaluation_error_count += 1
                    errors.append(
                        f"{entity_name}.{field_name}: "
                        f"constraint comparison failed at row "
                        f"{row_number}: {exc}"
                    )
                    continue

                if not satisfied:
                    violation_count += 1
                    errors.append(
                        f"{entity_name}.{field_name}: "
                        f"constraint violated at row "
                        f"{row_number}: "
                        f"{actual!r} {operator} "
                        f"{typed_expected!r}."
                    )

            constraint_metrics[constraint_name] = {
                "entity": entity_name,
                "field": field_name,
                "operator": operator,
                "expected": expected,
                "rows_checked": rows_checked,
                "violation_count": violation_count,
                "missing_field_count": missing_field_count,
                "evaluation_error_count": evaluation_error_count,
            }

        evidence.constraints = {
            "constraints_checked": len(constraint_metrics),
            "constraints": constraint_metrics,
            "rows_checked": sum(
                metric["rows_checked"]
                for metric in constraint_metrics.values()
            ),
            "violation_count": sum(
                metric["violation_count"]
                for metric in constraint_metrics.values()
            ),
            "missing_field_count": sum(
                metric["missing_field_count"]
                for metric in constraint_metrics.values()
            ),
            "evaluation_error_count": sum(
                metric["evaluation_error_count"]
                for metric in constraint_metrics.values()
            ),
        }

        # ------------------------------------------------------------
        # 4. Schema evidence
        # ------------------------------------------------------------

        schema_entities: dict[str, Any] = {}

        for entity in entities:
            entity_name = entity["name"]

            expected_fields = [
                field["name"]
                for field in entity.get("fields", [])
            ]
            expected_field_set = set(expected_fields)

            actual_fields: list[str] = []
            rows_checked = 0
            rows_with_missing_fields = 0

            artifact_rows = self._iter_typed_rows(
                data_model_id=data_model_id,
                job_id=job_id,
                entity_name=entity_name,
                field_types=field_types.get(entity_name, {}),
            )

            first_row = next(artifact_rows, None)

            if first_row is not None:
                actual_fields = list(first_row.keys())

                for row in artifact_rows:
                    rows_checked += 1

                rows_checked += 1

            actual_field_set = set(actual_fields)

            missing_fields = sorted(
                expected_field_set - actual_field_set
            )
            unexpected_fields = sorted(
                actual_field_set - expected_field_set
            )

            if missing_fields:
                rows_with_missing_fields = rows_checked

                errors.append(
                    f"{entity_name}: generated dataset is missing "
                    f"expected field(s): "
                    f"{missing_fields}."
                )

            if unexpected_fields:
                errors.append(
                    f"{entity_name}: generated dataset contains "
                    f"unexpected field(s): "
                    f"{unexpected_fields}."
                )

            schema_entities[entity_name] = {
                "expected_field_count": len(expected_fields),
                "actual_field_count": len(actual_fields),
                "expected_fields": expected_fields,
                "actual_fields": actual_fields,
                "missing_fields": missing_fields,
                "unexpected_fields": unexpected_fields,
                "rows_checked": rows_checked,
                "rows_with_missing_fields": rows_with_missing_fields,
            }

        evidence.schema = {
            "entities_checked": len(schema_entities),
            "entities": schema_entities,
            "rows_checked": sum(
                metric["rows_checked"]
                for metric in schema_entities.values()
            ),
            "entities_with_missing_fields": sum(
                1
                for metric in schema_entities.values()
                if metric["missing_fields"]
            ),
            "entities_with_unexpected_fields": sum(
                1
                for metric in schema_entities.values()
                if metric["unexpected_fields"]
            ),
        }

        # ------------------------------------------------------------
        # 5. Domain validity evidence
        # ------------------------------------------------------------

        domain_fields: dict[str, Any] = {}

        for entity in entities:
            entity_name = entity["name"]

            for field in entity.get("fields", []):
                field_name = field["name"]

                allowed_values = field.get("allowed_values")
                minimum = field.get("min")
                maximum = field.get("max")

                if (
                    allowed_values is None
                    and minimum is None
                    and maximum is None
                ):
                    continue

                field_type = field_types.get(
                    entity_name,
                    {},
                ).get(field_name)

                typed_allowed_values = None
                typed_minimum = None
                typed_maximum = None

                conversion_error_count = 0

                try:
                    if allowed_values is not None:
                        typed_allowed_values = {
                            self._convert_value(
                                value,
                                field_type,
                            )
                            for value in allowed_values
                        }

                    if minimum is not None:
                        typed_minimum = self._convert_value(
                            minimum,
                            field_type,
                        )

                    if maximum is not None:
                        typed_maximum = self._convert_value(
                            maximum,
                            field_type,
                        )

                except (TypeError, ValueError) as exc:
                    conversion_error_count += 1
                    errors.append(
                        f"{entity_name}.{field_name}: "
                        f"domain rule conversion failed: {exc}"
                    )

                    domain_fields[
                        f"{entity_name}.{field_name}"
                    ] = {
                        "entity": entity_name,
                        "field": field_name,
                        "allowed_values": allowed_values,
                        "min": minimum,
                        "max": maximum,
                        "rows_checked": 0,
                        "invalid_count": 0,
                        "missing_count": 0,
                        "conversion_error_count": conversion_error_count,
                    }
                    continue

                rows_checked = 0
                invalid_count = 0
                missing_count = 0

                for row_number, row in enumerate(
                    self._iter_typed_rows(
                        data_model_id=data_model_id,
                        job_id=job_id,
                        entity_name=entity_name,
                        field_types=field_types.get(
                            entity_name,
                            {},
                        ),
                    ),
                    start=1,
                ):
                    rows_checked += 1

                    if field_name not in row:
                        missing_count += 1
                        errors.append(
                            f"{entity_name}.{field_name}: "
                            f"domain field missing at row "
                            f"{row_number}."
                        )
                        continue

                    actual = row[field_name]

                    valid = True

                    if (
                        typed_allowed_values is not None
                        and actual not in typed_allowed_values
                    ):
                        valid = False

                    if (
                        typed_minimum is not None
                        and actual < typed_minimum
                    ):
                        valid = False

                    if (
                        typed_maximum is not None
                        and actual > typed_maximum
                    ):
                        valid = False

                    if not valid:
                        invalid_count += 1
                        errors.append(
                            f"{entity_name}.{field_name}: "
                            f"value {actual!r} violates domain "
                            f"rules at row {row_number}."
                        )

                domain_fields[
                    f"{entity_name}.{field_name}"
                ] = {
                    "entity": entity_name,
                    "field": field_name,
                    "allowed_values": allowed_values,
                    "min": minimum,
                    "max": maximum,
                    "rows_checked": rows_checked,
                    "invalid_count": invalid_count,
                    "missing_count": missing_count,
                    "conversion_error_count": conversion_error_count,
                }

        evidence.domain_validity = {
            "fields_checked": len(domain_fields),
            "fields": domain_fields,
            "rows_checked": sum(
                metric["rows_checked"]
                for metric in domain_fields.values()
            ),
            "invalid_count": sum(
                metric["invalid_count"]
                for metric in domain_fields.values()
            ),
            "missing_count": sum(
                metric["missing_count"]
                for metric in domain_fields.values()
            ),
            "conversion_error_count": sum(
                metric["conversion_error_count"]
                for metric in domain_fields.values()
            ),
        }

        # ------------------------------------------------------------
        # 6. Null completeness evidence
        # ------------------------------------------------------------

        null_fields: dict[str, Any] = {}

        for entity in entities:
            entity_name = entity["name"]

            for field in entity.get("fields", []):
                field_name = field["name"]

                rows_checked = 0
                missing_count = 0

                for row in self._iter_typed_rows(
                    data_model_id=data_model_id,
                    job_id=job_id,
                    entity_name=entity_name,
                    field_types=field_types.get(
                        entity_name,
                        {},
                    ),
                ):
                    rows_checked += 1

                    value = row.get(field_name)

                    if value is None or value == "":
                        missing_count += 1

                missing_rate = (
                    missing_count / rows_checked
                    if rows_checked
                    else 0.0
                )

                null_fields[
                    f"{entity_name}.{field_name}"
                ] = {
                    "entity": entity_name,
                    "field": field_name,
                    "rows_checked": rows_checked,
                    "missing_count": missing_count,
                    "missing_rate": missing_rate,
                }

        evidence.null_completeness = {
            "fields_checked": len(null_fields),
            "fields": null_fields,
            "rows_checked": sum(
                metric["rows_checked"]
                for metric in null_fields.values()
            ),
            "missing_count": sum(
                metric["missing_count"]
                for metric in null_fields.values()
            ),
        }

        # ------------------------------------------------------------
        # 7. Foreign-key integrity
        # ------------------------------------------------------------




        relationship_metrics: dict[str, Any] = {}

        for foreign_key in foreign_keys:
            name = foreign_key["name"]
            source = foreign_key["source"]
            target = foreign_key["target"]

            child_entity = source["entity"]
            child_fields = tuple(source["fields"])

            parent_entity = target["entity"]
            parent_fields = tuple(target["fields"])

            parent_field_types = field_types.get(
                parent_entity,
                {},
            )

            parent_keys = {
                tuple(
                    row[field]
                    for field in parent_fields
                )
                for row in self._iter_typed_rows(
                    data_model_id=data_model_id,
                    job_id=job_id,
                    entity_name=parent_entity,
                    field_types=parent_field_types,
                )
            }

            child_field_types = field_types.get(
                child_entity,
                {},
            )

            source_rows_checked = 0
            invalid_reference_count = 0
            missing_field_count = 0

            for row_number, row in enumerate(
                self._iter_typed_rows(
                    data_model_id=data_model_id,
                    job_id=job_id,
                    entity_name=child_entity,
                    field_types=child_field_types,
                ),
                start=1,
            ):
                source_rows_checked += 1

                try:
                    child_key = tuple(
                        row[field]
                        for field in child_fields
                    )
                except KeyError as exc:
                    missing_field_count += 1
                    errors.append(
                        f"{child_entity}: FK "
                        f"{name} field "
                        f"{exc.args[0]!r} missing at row "
                        f"{row_number}."
                    )
                    continue

                if child_key not in parent_keys:
                    invalid_reference_count += 1
                    errors.append(
                        f"{child_entity}: FK "
                        f"{name} references "
                        f"missing {parent_entity} key "
                        f"{child_key!r} at row {row_number}."
                    )

            relationship_metrics[name] = {
                "source_entity": child_entity,
                "target_entity": parent_entity,
                "source_fields": list(child_fields),
                "target_fields": list(parent_fields),
                "source_rows_checked": source_rows_checked,
                "target_keys_available": len(parent_keys),
                "invalid_reference_count": invalid_reference_count,
                "missing_field_count": missing_field_count,
            }

        evidence.foreign_keys = {
            "relationships_checked": len(relationship_metrics),
            "relationships": relationship_metrics,
            "source_rows_checked": sum(
                metric["source_rows_checked"]
                for metric in relationship_metrics.values()
            ),
            "invalid_reference_count": sum(
                metric["invalid_reference_count"]
                for metric in relationship_metrics.values()
            ),
            "missing_field_count": sum(
                metric["missing_field_count"]
                for metric in relationship_metrics.values()
            ),
        }

        # ------------------------------------------------------------
        # 8. Validation coverage evidence
        # ------------------------------------------------------------

        evidence.coverage = {
            "entities_declared": len(entities),
            "entities_population_checked": (
                evidence.completeness.get("entities_checked", 0)
            ),
            "entities_schema_checked": (
                evidence.schema.get("entities_checked", 0)
            ),
            "entities_identity_checked": (
                evidence.primary_keys.get("entities_checked", 0)
            ),
            "relationships_declared": len(foreign_keys),
            "relationships_checked": (
                evidence.foreign_keys.get(
                    "relationships_checked",
                    0,
                )
            ),
            "constraints_declared": len(
                specification.get("constraints", [])
            ),
            "constraints_checked": (
                evidence.constraints.get(
                    "constraints_checked",
                    0,
                )
            ),
            "domain_fields_checked": (
                evidence.domain_validity.get(
                    "fields_checked",
                    0,
                )
            ),
            "null_fields_checked": (
                evidence.null_completeness.get(
                    "fields_checked",
                    0,
                )
            ),
        }

        # ------------------------------------------------------------
        # 9. Rule-level conformance outcomes
        # ------------------------------------------------------------

        rule_results: list[dict[str, Any]] = []

        def record_rule(
            rule_id: str,
            category: str,
            status: str,
            *,
            details: dict[str, Any] | None = None,
        ) -> None:
            rule_results.append({
                "rule_id": rule_id,
                "category": category,
                "status": status,
                "evaluated": status != "NOT_EVALUATED",
                "details": details or {},
            })

        for entity_name, metric in completeness_entities.items():
            record_rule(
                f"population:{entity_name}",
                "POPULATION",
                "PASSED" if metric["complete"] else "FAILED",
                details=metric,
            )

        for entity_name, metric in identity_entities.items():
            if metric["rows_checked"] == 0:
                status = "NOT_EVALUATED"
            elif metric["duplicate_count"] or metric["missing_field_count"]:
                status = "FAILED"
            else:
                status = "PASSED"

            record_rule(
                f"identity:{entity_name}",
                "IDENTITY",
                status,
                details=metric,
            )

        for name, metric in constraint_metrics.items():
            if metric["evaluation_error_count"]:
                status = "NOT_EVALUATED"
            elif metric["violation_count"] or metric["missing_field_count"]:
                status = "FAILED"
            elif metric["rows_checked"] == 0:
                status = "NOT_EVALUATED"
            else:
                status = "PASSED"

            record_rule(
                f"constraint:{name}",
                "CONSTRAINT",
                status,
                details=metric,
            )

        for entity_name, metric in schema_entities.items():
            if metric["rows_checked"] == 0:
                status = "NOT_EVALUATED"
            elif metric["missing_fields"] or metric["unexpected_fields"]:
                status = "FAILED"
            else:
                status = "PASSED"

            record_rule(
                f"schema:{entity_name}",
                "SCHEMA",
                status,
                details=metric,
            )

        for field_id, metric in domain_fields.items():
            if metric["conversion_error_count"]:
                status = "NOT_EVALUATED"
            elif metric["invalid_count"] or metric["missing_count"]:
                status = "FAILED"
            elif metric["rows_checked"] == 0:
                status = "NOT_EVALUATED"
            else:
                status = "PASSED"

            record_rule(
                f"domain:{field_id}",
                "DOMAIN",
                status,
                details=metric,
            )

        for name, metric in relationship_metrics.items():
            if metric["missing_field_count"]:
                status = "FAILED"
            elif metric["invalid_reference_count"]:
                status = "FAILED"
            elif metric["source_rows_checked"] == 0:
                status = "NOT_EVALUATED"
            else:
                status = "PASSED"

            record_rule(
                f"foreign_key:{name}",
                "FOREIGN_KEY",
                status,
                details=metric,
            )

        # Evaluate relationship cardinality using explicit FK mappings
        # and row-level references. FK integrity rules above remain separate.
        for index, relationship in enumerate(
            specification.get("relationships", []),
            start=1,
        ):
            source_ref = relationship.get("source", f"relationship_{index}")
            target_ref = relationship.get("target", "unknown_target")
            relationship_type = str(
                relationship.get("type", "UNKNOWN")
            ).upper()
            source_participation = str(
                relationship.get("source_participation", "MANDATORY")
            ).upper()
            target_participation = str(
                relationship.get("target_participation", "MANDATORY")
            ).upper()

            details: dict[str, Any] = {
                "source": source_ref,
                "target": target_ref,
                "type": relationship_type,
                "source_participation": source_participation,
                "target_participation": target_participation,
            }
            status = "NOT_EVALUATED"

            if relationship_type == "MANY_TO_MANY":
                details["reason"] = (
                    "A direct MANY_TO_MANY declaration does not identify "
                    "an association mapping. Explicit junction or "
                    "association evidence is required."
                )
            elif relationship_type not in {
                "ONE_TO_ONE", "ONE_TO_MANY", "MANY_TO_ONE"
            }:
                details["reason"] = (
                    f"Unsupported relationship type: {relationship_type}."
                )
            elif (
                not isinstance(source_ref, str)
                or "." not in source_ref
                or not isinstance(target_ref, str)
                or "." not in target_ref
            ):
                status = "FAILED"
                details["reason"] = (
                    "Relationship endpoints must use ENTITY.FIELD notation."
                )
            elif (
                source_participation not in {"MANDATORY", "OPTIONAL"}
                or target_participation not in {"MANDATORY", "OPTIONAL"}
            ):
                status = "FAILED"
                details["reason"] = (
                    "Relationship participation must be MANDATORY or OPTIONAL."
                )
            else:
                source_entity, source_field = source_ref.split(".", 1)
                target_entity, target_field = target_ref.split(".", 1)
                details.update({
                    "source_entity": source_entity,
                    "source_field": source_field,
                    "target_entity": target_entity,
                    "target_field": target_field,
                })

                if (
                    source_entity not in entity_map
                    or target_entity not in entity_map
                    or source_field not in field_types.get(source_entity, {})
                    or target_field not in field_types.get(target_entity, {})
                ):
                    status = "FAILED"
                    details["reason"] = (
                        "A declared relationship endpoint entity or field "
                        "does not exist in the specification."
                    )
                else:
                    matching_fks = []
                    foreign_key_candidates = (
                        foreign_keys if isinstance(foreign_keys, list) else []
                    )

                    for foreign_key in foreign_key_candidates:
                        if not isinstance(foreign_key, dict):
                            continue

                        fk_source = foreign_key.get("source")
                        fk_target = foreign_key.get("target")
                        if (
                            not isinstance(fk_source, dict)
                            or not isinstance(fk_target, dict)
                        ):
                            continue

                        fk_source_fields = fk_source.get("fields")
                        fk_target_fields = fk_target.get("fields")
                        if (
                            not isinstance(fk_source_fields, list)
                            or not isinstance(fk_target_fields, list)
                            or any(
                                not isinstance(field, str)
                                for field in fk_source_fields
                            )
                            or any(
                                not isinstance(field, str)
                                for field in fk_target_fields
                            )
                        ):
                            continue

                        fk_source_fields = tuple(fk_source_fields)
                        fk_target_fields = tuple(fk_target_fields)

                        forward = (
                            fk_source.get("entity") == source_entity
                            and fk_source_fields == (source_field,)
                            and fk_target.get("entity") == target_entity
                            and fk_target_fields == (target_field,)
                        )
                        reverse = (
                            fk_source.get("entity") == target_entity
                            and fk_source_fields == (target_field,)
                            and fk_target.get("entity") == source_entity
                            and fk_target_fields == (source_field,)
                        )

                        if forward or reverse:
                            matching_fks.append({
                                "name": foreign_key.get("name"),
                                "direction": (
                                    "FORWARD" if forward else "REVERSE"
                                ),
                                "foreign_key": foreign_key,
                            })

                    expected_direction = {
                        "ONE_TO_ONE": None,
                        "ONE_TO_MANY": "REVERSE",
                        "MANY_TO_ONE": "FORWARD",
                    }[relationship_type]
                    compatible_fks = [
                        item for item in matching_fks
                        if expected_direction is None
                        or item["direction"] == expected_direction
                    ]

                    def describe_fk(item: dict[str, Any]) -> dict[str, Any]:
                        return {
                            "name": item["name"],
                            "direction": item["direction"],
                        }

                    details["matching_foreign_keys"] = [
                        describe_fk(item) for item in matching_fks
                    ]
                    details["compatible_foreign_keys"] = [
                        describe_fk(item) for item in compatible_fks
                    ]

                    if len(compatible_fks) != 1:
                        if matching_fks and not compatible_fks:
                            details["reason"] = (
                                "Endpoint-matching FK mappings exist, but "
                                "none matches the declared relationship "
                                "cardinality direction."
                            )
                        elif len(compatible_fks) > 1:
                            details["reason"] = (
                                "Multiple compatible FK mappings match this "
                                "relationship; the mapping is ambiguous."
                            )
                        else:
                            details["reason"] = (
                                "A unique FK mapping in the expected direction "
                                "could not be established for this relationship."
                            )
                    else:
                        mapping = compatible_fks[0]
                        fk = mapping["foreign_key"]

                        if mapping["direction"] == "FORWARD":
                            child_entity = source_entity
                            child_field = source_field
                            parent_entity = target_entity
                            parent_field = target_field
                        else:
                            child_entity = target_entity
                            child_field = target_field
                            parent_entity = source_entity
                            parent_field = source_field

                        child_rows = list(self._iter_typed_rows(
                            data_model_id=data_model_id,
                            job_id=job_id,
                            entity_name=child_entity,
                            field_types=field_types[child_entity],
                        ))
                        parent_rows = list(self._iter_typed_rows(
                            data_model_id=data_model_id,
                            job_id=job_id,
                            entity_name=parent_entity,
                            field_types=field_types[parent_entity],
                        ))

                        child_missing = sum(
                            1 for row in child_rows
                            if child_field not in row
                        )
                        parent_missing = sum(
                            1 for row in parent_rows
                            if parent_field not in row
                        )
                        details.update({
                            "child_entity": child_entity,
                            "child_field": child_field,
                            "parent_entity": parent_entity,
                            "parent_field": parent_field,
                            "child_rows_checked": len(child_rows),
                            "parent_rows_checked": len(parent_rows),
                            "source_missing_field_count": (
                                sum(1 for row in child_rows
                                    if source_entity == child_entity
                                    and source_field not in row)
                                + sum(1 for row in parent_rows
                                      if source_entity == parent_entity
                                      and source_field not in row)
                            ),
                            "target_missing_field_count": (
                                sum(1 for row in child_rows
                                    if target_entity == child_entity
                                    and target_field not in row)
                                + sum(1 for row in parent_rows
                                      if target_entity == parent_entity
                                      and target_field not in row)
                            ),
                        })

                        if not child_rows or not parent_rows:
                            details["reason"] = (
                                "At least one endpoint has no generated rows; "
                                "relationship conformance cannot be established."
                            )
                        elif child_missing or parent_missing:
                            status = "FAILED"
                            details["reason"] = (
                                "One or more generated rows are missing a "
                                "declared relationship endpoint field."
                            )
                        else:
                            parent_values = [
                                row[parent_field] for row in parent_rows
                            ]
                            parent_non_null = [
                                value for value in parent_values
                                if value is not None
                                and not (
                                    isinstance(value, str) and not value.strip()
                                )
                            ]
                            parent_value_counts: dict[Any, int] = {}
                            for value in parent_non_null:
                                parent_value_counts[value] = (
                                    parent_value_counts.get(value, 0) + 1
                                )

                            child_values = [
                                row[child_field] for row in child_rows
                            ]
                            child_null_count = sum(
                                1 for value in child_values
                                if value is None
                                or (
                                    isinstance(value, str) and not value.strip()
                                )
                            )
                            child_non_null = [
                                value for value in child_values
                                if value is not None
                                and not (
                                    isinstance(value, str) and not value.strip()
                                )
                            ]
                            parent_value_set = set(parent_non_null)
                            dangling_values = set(child_non_null) - parent_value_set
                            child_reference_counts: dict[Any, int] = {}
                            for value in child_non_null:
                                child_reference_counts[value] = (
                                    child_reference_counts.get(value, 0) + 1
                                )

                            duplicate_parent_values = sum(
                                count - 1
                                for count in parent_value_counts.values()
                                if count > 1
                            )
                            duplicate_child_references = sum(
                                count - 1
                                for count in child_reference_counts.values()
                                if count > 1
                            )
                            parents_without_children = sum(
                                1 for value in parent_value_set
                                if child_reference_counts.get(value, 0) == 0
                            )

                            details.update({
                                "parent_distinct_values": len(parent_value_set),
                                "parent_duplicate_rows": duplicate_parent_values,
                                "child_non_null_reference_count": len(child_non_null),
                                "child_null_count": child_null_count,
                                "dangling_reference_count": len(dangling_values),
                                "duplicate_child_reference_rows": (
                                    duplicate_child_references
                                ),
                                "parents_without_children": (
                                    parents_without_children
                                ),
                            })

                            reasons: list[str] = []

                            if duplicate_parent_values:
                                reasons.append(
                                    "The referenced parent endpoint is not unique."
                                )
                            if dangling_values:
                                reasons.append(
                                    "One or more child references do not match "
                                    "a parent endpoint value."
                                )

                            child_participation = (
                                source_participation
                                if child_entity == source_entity
                                else target_participation
                            )
                            parent_participation = (
                                source_participation
                                if parent_entity == source_entity
                                else target_participation
                            )

                            if (
                                child_participation == "MANDATORY"
                                and child_null_count
                            ):
                                reasons.append(
                                    "Mandatory child-side participation has "
                                    "null or blank references."
                                )
                            if (
                                parent_participation == "MANDATORY"
                                and parents_without_children
                            ):
                                reasons.append(
                                    "Mandatory parent-side participation has "
                                    "parent records with no related child."
                                )

                            if (
                                relationship_type == "ONE_TO_ONE"
                                and duplicate_child_references
                            ):
                                reasons.append(
                                    "ONE_TO_ONE cardinality is violated because "
                                    "multiple child records reference the same parent."
                                )

                            details["foreign_key_name"] = mapping["name"]
                            details["foreign_key_direction"] = mapping["direction"]

                            if reasons:
                                status = "FAILED"
                                details["reasons"] = reasons
                                details["reason"] = (
                                    "Row-level relationship checks found "
                                    "one or more conformance violations."
                                )
                            else:
                                status = "PASSED"
                                details["reason"] = (
                                    "Explicit FK mapping, parent endpoint "
                                    "uniqueness, reference validity, cardinality, "
                                    "and declared participation checks passed."
                                )

            record_rule(
                f"relationship:{index}:{source_ref}->{target_ref}",
                "RELATIONSHIP_CARDINALITY",
                status,
                details=details,
            )

        evidence.rule_results = rule_results

        rule_status_counts = {
            status: sum(
                1 for result in rule_results
                if result["status"] == status
            )
            for status in ("PASSED", "FAILED", "NOT_EVALUATED")
        }

        evidence.coverage.update({
            "conformance_rules_reported": len(rule_results),
            "conformance_rules_passed": rule_status_counts["PASSED"],
            "conformance_rules_failed": rule_status_counts["FAILED"],
            "conformance_rules_not_evaluated": (
                rule_status_counts["NOT_EVALUATED"]
            ),
            "conformance_status": (
                "NON_CONFORMANT"
                if rule_status_counts["FAILED"]
                else (
                    "INCOMPLETE"
                    if rule_status_counts["NOT_EVALUATED"]
                    else "CONFORMANT"
                )
            ),
        })

        return GenerationValidationResult(
            valid=not errors,
            entity_count=len(entity_map),
            generated_rows=generated_rows,
            expected_rows=expected_rows,
            errors=errors,
            warnings=warnings,
            evidence=evidence,
        )

    def _count_rows(
        self,
        *,
        data_model_id: str,
        job_id: str,
        entity_name: str,
    ) -> int:
        return sum(
            1
            for _ in self._artifact_reader.iter_entity_chunks(
                data_model_id=data_model_id,
                job_id=job_id,
                entity_name=entity_name,
            )
        )

    def _iter_typed_rows(
        self,
        *,
        data_model_id: str,
        job_id: str,
        entity_name: str,
        field_types: dict[str, Any],
    ):
        for row in self._artifact_reader.iter_entity_chunks(
            data_model_id=data_model_id,
            job_id=job_id,
            entity_name=entity_name,
        ):
            yield {
                field_name: self._convert_value(
                    value,
                    field_types.get(field_name),
                )
                for field_name, value in row.items()
            }

    @staticmethod
    def _convert_value(
        value: Any,
        field_type: Any,
    ) -> Any:
        return convert_value(value, field_type)
