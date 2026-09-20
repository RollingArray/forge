"""
FORGE Generation Core
Independent generated-dataset validation.

This module validates generated output against the FORGE specification.
It does not modify or repair generated data.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class ValidationEvidence:
    """Measured evidence collected during independent dataset validation."""

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



def load_entity_rows(
    output_directory: str | Path,
    entity_name: str,
) -> list[dict[str, str]]:
    """Load one generated entity CSV."""

    path = Path(output_directory) / f"{entity_name}.csv"

    if not path.exists():
        raise ValueError(
            f"Generated output for entity {entity_name!r} was not found: {path}"
        )

    with path.open(
        "r",
        newline="",
        encoding="utf-8",
    ) as file:
        return list(csv.DictReader(file))


def _declared_entity_fields(
    entity: dict[str, Any],
) -> set[str]:
    """Return field names declared by an entity."""

    return {
        field.get("name")
        for field in entity.get("fields", [])
        if field.get("name")
    }


def validate_completeness(
    specification: dict[str, Any],
    output_directory: str | Path,
    evidence: ValidationEvidence | None = None,
) -> list[str]:
    """Validate requested population counts against generated row counts."""

    errors: list[str] = []
    entity_metrics: dict[str, Any] = {}

    for entity in specification.get("entities", []):
        entity_name = entity.get("name")
        requested_rows = entity.get("population", {}).get("count", 0)
        rows = load_entity_rows(output_directory, entity_name)
        actual_rows = len(rows)
        difference = actual_rows - requested_rows

        metric = {
            "requested_rows": requested_rows,
            "generated_rows": actual_rows,
            "difference": difference,
            "complete": actual_rows == requested_rows,
        }
        entity_metrics[entity_name] = metric

        if actual_rows != requested_rows:
            errors.append(
                f"{entity_name}: expected {requested_rows} generated rows "
                f"but found {actual_rows}."
            )

    if evidence is not None:
        total_requested = sum(
            metric["requested_rows"]
            for metric in entity_metrics.values()
        )
        total_generated = sum(
            metric["generated_rows"]
            for metric in entity_metrics.values()
        )

        evidence.completeness = {
            "entities_checked": len(entity_metrics),
            "entities_complete": sum(
                1
                for metric in entity_metrics.values()
                if metric["complete"]
            ),
            "total_requested_rows": total_requested,
            "total_generated_rows": total_generated,
            "difference": total_generated - total_requested,
            "complete": total_generated == total_requested
            and all(
                metric["complete"]
                for metric in entity_metrics.values()
            ),
            "entities": entity_metrics,
        }

    return errors


def validate_schema(
    specification: dict[str, Any],
    output_directory: str | Path,
    evidence: ValidationEvidence | None = None,
) -> list[str]:
    """Validate generated columns against the declared entity schema."""

    errors: list[str] = []
    entity_metrics: dict[str, Any] = {}

    for entity in specification.get("entities", []):
        entity_name = entity.get("name")
        expected_fields = _declared_entity_fields(entity)
        rows = load_entity_rows(output_directory, entity_name)

        actual_fields = set(rows[0].keys()) if rows else set()
        missing_fields = sorted(expected_fields - actual_fields)
        unexpected_fields = sorted(actual_fields - expected_fields)

        if rows:
            # Check every row because CSV rows can have missing values even
            # when the header itself is correct.
            row_missing_fields = 0
            for row_number, row in enumerate(rows, start=1):
                missing = expected_fields - set(row.keys())
                if missing:
                    row_missing_fields += 1
                    errors.append(
                        f"{entity_name}: missing fields {sorted(missing)} "
                        f"at generated row {row_number}."
                    )
        else:
            row_missing_fields = 0

        if missing_fields:
            errors.append(
                f"{entity_name}: generated schema is missing fields "
                f"{missing_fields}."
            )

        if unexpected_fields:
            errors.append(
                f"{entity_name}: generated schema contains unexpected "
                f"fields {unexpected_fields}."
            )

        entity_metrics[entity_name] = {
            "expected_field_count": len(expected_fields),
            "actual_field_count": len(actual_fields),
            "missing_fields": missing_fields,
            "unexpected_fields": unexpected_fields,
            "rows_with_missing_fields": row_missing_fields,
            "schema_valid": (
                not missing_fields
                and not unexpected_fields
                and row_missing_fields == 0
            ),
        }

    if evidence is not None:
        evidence.schema = {
            "entities_checked": len(entity_metrics),
            "entities_schema_valid": sum(
                1
                for metric in entity_metrics.values()
                if metric["schema_valid"]
            ),
            "missing_field_count": sum(
                len(metric["missing_fields"])
                for metric in entity_metrics.values()
            ),
            "unexpected_field_count": sum(
                len(metric["unexpected_fields"])
                for metric in entity_metrics.values()
            ),
            "rows_with_missing_fields": sum(
                metric["rows_with_missing_fields"]
                for metric in entity_metrics.values()
            ),
            "entities": entity_metrics,
        }

    return errors


def validate_domain_values(
    specification: dict[str, Any],
    output_directory: str | Path,
    evidence: ValidationEvidence | None = None,
) -> list[str]:
    """Validate declared categorical and numeric generation domains."""

    errors: list[str] = []
    field_metrics: dict[str, Any] = {}

    for entity in specification.get("entities", []):
        entity_name = entity.get("name")
        rows = load_entity_rows(output_directory, entity_name)

        for field in entity.get("fields", []):
            field_name = field.get("name")
            generation = field.get("generation", {})
            distribution = generation.get("distribution")
            parameters = generation.get("parameters", {})

            allowed_values = parameters.get("values")
            minimum = parameters.get("minimum")
            maximum = parameters.get("maximum")

            # Only validate fields for which the specification declares a
            # finite categorical or numeric domain.
            has_domain = (
                isinstance(allowed_values, list)
                or minimum is not None
                or maximum is not None
            )

            if not has_domain:
                continue

            invalid_count = 0
            missing_count = 0
            numeric_conversion_errors = 0

            for row_number, row in enumerate(rows, start=1):
                actual = row.get(field_name)

                if actual is None or actual == "":
                    missing_count += 1
                    continue

                valid = True

                if isinstance(allowed_values, list):
                    valid = actual in {
                        str(value)
                        for value in allowed_values
                    }

                if valid and (minimum is not None or maximum is not None):
                    try:
                        numeric_actual = float(actual)

                        if minimum is not None:
                            valid = valid and numeric_actual >= float(
                                minimum
                            )

                        if maximum is not None:
                            valid = valid and numeric_actual <= float(
                                maximum
                            )
                    except (TypeError, ValueError):
                        numeric_conversion_errors += 1
                        valid = False

                if not valid:
                    invalid_count += 1
                    errors.append(
                        f"{entity_name}: field {field_name!r} contains "
                        f"value {actual!r} outside its declared domain "
                        f"at row {row_number}."
                    )

            key = f"{entity_name}.{field_name}"
            field_metrics[key] = {
                "entity": entity_name,
                "field": field_name,
                "distribution": distribution,
                "allowed_values": allowed_values,
                "minimum": minimum,
                "maximum": maximum,
                "rows_checked": len(rows),
                "invalid_count": invalid_count,
                "missing_count": missing_count,
                "numeric_conversion_errors": numeric_conversion_errors,
                "valid": (
                    invalid_count == 0
                    and numeric_conversion_errors == 0
                ),
            }

    if evidence is not None:
        evidence.domain_validity = {
            "fields_checked": len(field_metrics),
            "fields_valid": sum(
                1
                for metric in field_metrics.values()
                if metric["valid"]
            ),
            "rows_checked": sum(
                metric["rows_checked"]
                for metric in field_metrics.values()
            ),
            "invalid_count": sum(
                metric["invalid_count"]
                for metric in field_metrics.values()
            ),
            "missing_count": sum(
                metric["missing_count"]
                for metric in field_metrics.values()
            ),
            "numeric_conversion_errors": sum(
                metric["numeric_conversion_errors"]
                for metric in field_metrics.values()
            ),
            "fields": field_metrics,
        }

    return errors


def validate_null_completeness(
    specification: dict[str, Any],
    output_directory: str | Path,
    evidence: ValidationEvidence | None = None,
) -> list[str]:
    """Measure missing and empty values without imposing nullability rules."""

    field_metrics: dict[str, Any] = {}

    for entity in specification.get("entities", []):
        entity_name = entity.get("name")
        rows = load_entity_rows(output_directory, entity_name)

        for field in entity.get("fields", []):
            field_name = field.get("name")
            missing_count = 0

            for row in rows:
                value = row.get(field_name)
                if value is None or value == "":
                    missing_count += 1

            key = f"{entity_name}.{field_name}"
            field_metrics[key] = {
                "entity": entity_name,
                "field": field_name,
                "rows_checked": len(rows),
                "missing_count": missing_count,
                "missing_rate": (
                    missing_count / len(rows)
                    if rows
                    else 0.0
                ),
                "complete": missing_count == 0,
            }

    if evidence is not None:
        evidence.null_completeness = {
            "fields_checked": len(field_metrics),
            "fields_without_missing_values": sum(
                1
                for metric in field_metrics.values()
                if metric["complete"]
            ),
            "rows_checked": sum(
                metric["rows_checked"]
                for metric in field_metrics.values()
            ),
            "missing_value_count": sum(
                metric["missing_count"]
                for metric in field_metrics.values()
            ),
            "fields": field_metrics,
        }

    return []


def build_validation_coverage(
    specification: dict[str, Any],
    evidence: ValidationEvidence,
) -> None:
    """Summarize what the validator actually inspected."""

    entities = specification.get("entities", [])
    relationships = specification.get("foreign_keys", [])
    constraints = specification.get("constraints", [])

    evidence.coverage = {
        "entities_declared": len(entities),
        "entities_population_checked": evidence.completeness.get(
            "entities_checked",
            0,
        ),
        "entities_schema_checked": evidence.schema.get(
            "entities_checked",
            0,
        ),
        "entities_identity_checked": evidence.primary_keys.get(
            "entities_checked",
            0,
        ),
        "relationships_declared": len(relationships),
        "relationships_checked": evidence.foreign_keys.get(
            "relationships_checked",
            0,
        ),
        "constraints_declared": len(constraints),
        "constraints_checked": evidence.constraints.get(
            "constraints_checked",
            0,
        ),
        "domain_fields_checked": evidence.domain_validity.get(
            "fields_checked",
            0,
        ),
        "null_fields_checked": evidence.null_completeness.get(
            "fields_checked",
            0,
        ),
    }


def validate_primary_keys(
    specification: dict[str, Any],
    output_directory: str | Path,
    evidence: ValidationEvidence | None = None,
) -> list[str]:
    """Validate identity fields and composite identities."""

    errors: list[str] = []
    entity_metrics: dict[str, Any] = {}

    for entity in specification.get("entities", []):
        entity_name = entity.get("name")
        identity = entity.get("identity", {})
        fields = identity.get("fields", [])

        if not fields:
            continue

        rows = load_entity_rows(
            output_directory,
            entity_name,
        )

        seen: set[tuple[str, ...]] = set()
        duplicate_count = 0
        missing_field_count = 0

        for row_number, row in enumerate(rows, start=1):
            try:
                key = tuple(row[field] for field in fields)
            except KeyError as exc:
                missing_field_count += 1
                errors.append(
                    f"{entity_name}: identity field {exc.args[0]!r} "
                    f"is missing from generated row {row_number}."
                )
                continue

            if key in seen:
                duplicate_count += 1
                errors.append(
                    f"{entity_name}: duplicate identity {key} "
                    f"at generated row {row_number}."
                )
            else:
                seen.add(key)

        entity_metrics[entity_name] = {
            "rows_checked": len(rows),
            "unique_identities": len(seen),
            "duplicate_count": duplicate_count,
            "missing_field_count": missing_field_count,
            "identity_fields": list(fields),
        }

    if evidence is not None:
        evidence.primary_keys = {
            "entities_checked": len(entity_metrics),
            "entities": entity_metrics,
            "rows_checked": sum(
                metric["rows_checked"]
                for metric in entity_metrics.values()
            ),
            "duplicate_count": sum(
                metric["duplicate_count"]
                for metric in entity_metrics.values()
            ),
            "missing_field_count": sum(
                metric["missing_field_count"]
                for metric in entity_metrics.values()
            ),
        }

    return errors


def validate_foreign_keys(
    specification: dict[str, Any],
    output_directory: str | Path,
    evidence: ValidationEvidence | None = None,
) -> list[str]:
    """Validate that every generated foreign-key value exists in its target."""

    errors: list[str] = []
    relationship_metrics: dict[str, Any] = {}

    for foreign_key in specification.get("foreign_keys", []):
        name = foreign_key.get("name")
        source = foreign_key.get("source", {})
        target = foreign_key.get("target", {})

        source_entity = source.get("entity")
        source_fields = source.get("fields", [])
        target_entity = target.get("entity")
        target_fields = target.get("fields", [])

        source_rows = load_entity_rows(
            output_directory,
            source_entity,
        )

        target_rows = load_entity_rows(
            output_directory,
            target_entity,
        )

        target_keys = {
            tuple(row[field] for field in target_fields)
            for row in target_rows
        }

        invalid_reference_count = 0
        missing_field_count = 0

        for row_number, row in enumerate(source_rows, start=1):
            try:
                source_key = tuple(row[field] for field in source_fields)
            except KeyError as exc:
                missing_field_count += 1
                errors.append(
                    f"{name}: source field {exc.args[0]!r} is missing "
                    f"from {source_entity} row {row_number}."
                )
                continue

            if source_key not in target_keys:
                invalid_reference_count += 1
                errors.append(
                    f"{name}: {source_entity} row {row_number} "
                    f"references missing {target_entity} key {source_key}."
                )

        relationship_metrics[name] = {
            "source_entity": source_entity,
            "target_entity": target_entity,
            "source_fields": list(source_fields),
            "target_fields": list(target_fields),
            "source_rows_checked": len(source_rows),
            "target_keys_available": len(target_keys),
            "invalid_reference_count": invalid_reference_count,
            "missing_field_count": missing_field_count,
        }

    if evidence is not None:
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

    return errors


def compare_value(
    actual: str,
    operator: str,
    expected: Any,
) -> bool:
    """Compare a generated value against a constraint."""

    if isinstance(expected, bool):
        normalized_actual: Any = actual.lower() == "true"

    elif isinstance(expected, (int, float)):
        try:
            normalized_actual = float(actual)
        except ValueError:
            return False

    else:
        normalized_actual = actual

    if operator == ">":
        return normalized_actual > expected

    if operator == ">=":
        return normalized_actual >= expected

    if operator == "<":
        return normalized_actual < expected

    if operator == "<=":
        return normalized_actual <= expected

    if operator == "==":
        return normalized_actual == expected

    if operator == "!=":
        return normalized_actual != expected

    raise ValueError(
        f"Unsupported constraint operator: {operator!r}"
    )


def validate_constraints(
    specification: dict[str, Any],
    output_directory: str | Path,
    evidence: ValidationEvidence | None = None,
) -> list[str]:
    """Validate explicit field constraints."""

    errors: list[str] = []
    constraint_metrics: dict[str, Any] = {}

    for index, constraint in enumerate(
        specification.get("constraints", []),
        start=1,
    ):
        entity_name = constraint.get("entity")
        field_name = constraint.get("field")
        operator = constraint.get("operator")
        expected = constraint.get("value")
        constraint_name = constraint.get("name") or f"constraint_{index}"

        rows = load_entity_rows(
            output_directory,
            entity_name,
        )

        violation_count = 0
        missing_field_count = 0
        evaluation_error_count = 0

        for row_number, row in enumerate(rows, start=1):
            actual = row.get(field_name)

            if actual is None:
                missing_field_count += 1
                errors.append(
                    f"{entity_name}: constraint field {field_name!r} "
                    f"is missing at row {row_number}."
                )
                continue

            try:
                valid = compare_value(
                    actual,
                    operator,
                    expected,
                )
            except Exception as exc:
                evaluation_error_count += 1
                errors.append(
                    f"{entity_name}: unable to evaluate constraint "
                    f"{field_name} {operator} {expected!r} at row "
                    f"{row_number}: {exc}"
                )
                continue

            if not valid:
                violation_count += 1
                errors.append(
                    f"{entity_name}: constraint violated at row "
                    f"{row_number}: {field_name} {operator} "
                    f"{expected!r}; actual={actual!r}."
                )

        constraint_metrics[constraint_name] = {
            "entity": entity_name,
            "field": field_name,
            "operator": operator,
            "expected": expected,
            "rows_checked": len(rows),
            "violation_count": violation_count,
            "missing_field_count": missing_field_count,
            "evaluation_error_count": evaluation_error_count,
        }

    if evidence is not None:
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

    return errors


def validate_dataset(
    specification: dict[str, Any],
    output_directory: str | Path,
    evidence: ValidationEvidence | None = None,
) -> list[str]:
    """Run all currently supported independent dataset validations."""

    errors: list[str] = []

    errors.extend(
        validate_completeness(
            specification,
            output_directory,
            evidence=evidence,
        )
    )

    errors.extend(
        validate_schema(
            specification,
            output_directory,
            evidence=evidence,
        )
    )

    errors.extend(
        validate_primary_keys(
            specification,
            output_directory,
            evidence=evidence,
        )
    )

    errors.extend(
        validate_foreign_keys(
            specification,
            output_directory,
            evidence=evidence,
        )
    )

    errors.extend(
        validate_constraints(
            specification,
            output_directory,
            evidence=evidence,
        )
    )

    errors.extend(
        validate_domain_values(
            specification,
            output_directory,
            evidence=evidence,
        )
    )

    errors.extend(
        validate_null_completeness(
            specification,
            output_directory,
            evidence=evidence,
        )
    )

    if evidence is not None:
        build_validation_coverage(
            specification,
            evidence,
        )

    return errors
