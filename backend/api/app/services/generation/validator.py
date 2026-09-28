from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.services.generation.context import GenerationContext


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
    """Validate generated data against the production specification."""

    def validate(
        self,
        *,
        specification: dict[str, Any],
        context: GenerationContext,
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

        # ------------------------------------------------------------
        # 1. Population counts
        # ------------------------------------------------------------

        for entity in entities:
            entity_name = entity["name"]
            expected = (
                entity.get("population") or {}
            ).get("count", 0)

            actual = len(
                context.get_rows(
                    entity_name=entity_name,
                )
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

        for entity in entities:
            entity_name = entity["name"]
            identity_fields = (
                entity.get("identity") or {}
            ).get("fields", [])

            if not identity_fields:
                continue

            rows = context.get_rows(
                entity_name=entity_name,
            )

            seen: set[tuple[Any, ...]] = set()

            for row_number, row in enumerate(
                rows,
                start=1,
            ):
                try:
                    identity = tuple(
                        row[field]
                        for field in identity_fields
                    )
                except KeyError as exc:
                    errors.append(
                        f"{entity_name}: identity field "
                        f"{exc.args[0]!r} missing at row "
                        f"{row_number}."
                    )
                    continue

                if identity in seen:
                    errors.append(
                        f"{entity_name}: duplicate identity "
                        f"{identity!r} at row {row_number}."
                    )
                    break

                seen.add(identity)

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

        for constraint in specification.get("constraints", []):
            entity_name = constraint["entity"]
            field_name = constraint["field"]
            operator = constraint["operator"]
            expected = constraint["value"]

            predicate = operators.get(operator)

            if predicate is None:
                errors.append(
                    f"{entity_name}.{field_name}: "
                    f"unsupported constraint operator "
                    f"{operator!r}."
                )
                continue

            rows = context.get_rows(
                entity_name=entity_name,
            )

            for row_number, row in enumerate(
                rows,
                start=1,
            ):
                if field_name not in row:
                    errors.append(
                        f"{entity_name}: constraint field "
                        f"{field_name!r} missing at row "
                        f"{row_number}."
                    )
                    break

                actual = row[field_name]

                try:
                    satisfied = predicate(actual, expected)
                except TypeError as exc:
                    errors.append(
                        f"{entity_name}.{field_name}: "
                        f"constraint comparison failed at row "
                        f"{row_number}: {exc}"
                    )
                    break

                if not satisfied:
                    errors.append(
                        f"{entity_name}.{field_name}: "
                        f"constraint violated at row "
                        f"{row_number}: "
                        f"{actual!r} {operator} {expected!r}."
                    )
                    break

        # ------------------------------------------------------------
        # 4. Foreign-key integrity
        # ------------------------------------------------------------

        for foreign_key in foreign_keys:
            source = foreign_key["source"]
            target = foreign_key["target"]

            child_entity = source["entity"]
            child_fields = tuple(source["fields"])

            parent_entity = target["entity"]
            parent_fields = tuple(target["fields"])

            parent_rows = context.get_rows(
                entity_name=parent_entity,
            )

            parent_keys = {
                tuple(row[field] for field in parent_fields)
                for row in parent_rows
            }

            child_rows = context.get_rows(
                entity_name=child_entity,
            )

            for row_number, row in enumerate(
                child_rows,
                start=1,
            ):
                try:
                    child_key = tuple(
                        row[field]
                        for field in child_fields
                    )
                except KeyError as exc:
                    errors.append(
                        f"{child_entity}: FK "
                        f"{foreign_key['name']} field "
                        f"{exc.args[0]!r} missing at row "
                        f"{row_number}."
                    )
                    break

                if child_key not in parent_keys:
                    errors.append(
                        f"{child_entity}: FK "
                        f"{foreign_key['name']} references "
                        f"missing {parent_entity} key "
                        f"{child_key!r} at row {row_number}."
                    )
                    break

        return GenerationValidationResult(
            valid=not errors,
            entity_count=len(entity_map),
            generated_rows=generated_rows,
            expected_rows=expected_rows,
            errors=errors,
            warnings=warnings,
            evidence=evidence,
        )
