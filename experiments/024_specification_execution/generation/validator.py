"""
FORGE Generation Core
Independent generated-dataset validation.

This module validates generated output against the FORGE specification.
It does not modify or repair generated data.
"""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Any


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


def validate_primary_keys(
    specification: dict[str, Any],
    output_directory: str | Path,
) -> list[str]:
    """Validate identity fields and composite identities."""

    errors: list[str] = []

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

        for row_number, row in enumerate(rows, start=1):
            try:
                key = tuple(row[field] for field in fields)
            except KeyError as exc:
                errors.append(
                    f"{entity_name}: identity field {exc.args[0]!r} "
                    f"is missing from generated row {row_number}."
                )
                continue

            if key in seen:
                errors.append(
                    f"{entity_name}: duplicate identity {key} "
                    f"at generated row {row_number}."
                )
            else:
                seen.add(key)

    return errors


def validate_foreign_keys(
    specification: dict[str, Any],
    output_directory: str | Path,
) -> list[str]:
    """Validate that every generated foreign-key value exists in its target."""

    errors: list[str] = []

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

        for row_number, row in enumerate(source_rows, start=1):
            source_key = tuple(row[field] for field in source_fields)

            if source_key not in target_keys:
                errors.append(
                    f"{name}: {source_entity} row {row_number} "
                    f"references missing {target_entity} key {source_key}."
                )

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
) -> list[str]:
    """Validate explicit field constraints."""

    errors: list[str] = []

    for constraint in specification.get("constraints", []):
        entity_name = constraint.get("entity")
        field_name = constraint.get("field")
        operator = constraint.get("operator")
        expected = constraint.get("value")

        rows = load_entity_rows(
            output_directory,
            entity_name,
        )

        for row_number, row in enumerate(rows, start=1):
            actual = row.get(field_name)

            if actual is None:
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
                errors.append(
                    f"{entity_name}: unable to evaluate constraint "
                    f"{field_name} {operator} {expected!r} at row "
                    f"{row_number}: {exc}"
                )
                continue

            if not valid:
                errors.append(
                    f"{entity_name}: constraint violated at row "
                    f"{row_number}: {field_name} {operator} {expected!r}; "
                    f"actual={actual!r}."
                )

    return errors


def validate_dataset(
    specification: dict[str, Any],
    output_directory: str | Path,
) -> list[str]:
    """Run all currently supported independent dataset validations."""

    errors: list[str] = []

    errors.extend(
        validate_primary_keys(
            specification,
            output_directory,
        )
    )

    errors.extend(
        validate_foreign_keys(
            specification,
            output_directory,
        )
    )

    errors.extend(
        validate_constraints(
            specification,
            output_directory,
        )
    )

    return errors
