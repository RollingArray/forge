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
