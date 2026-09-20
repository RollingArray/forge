"""
FORGE Generation Core
Quality analysis for generated datasets.

This module consumes generation results and independent validation
evidence to produce measurable quality characteristics.

It does not modify generated data.
It does not perform validation or repair.
"""

from __future__ import annotations

import csv
import math
from datetime import datetime
from collections import Counter, defaultdict
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
            f"Generated output for entity {entity_name!r} "
            f"was not found: {path}"
        )

    with path.open(
        "r",
        newline="",
        encoding="utf-8",
    ) as file:
        return list(csv.DictReader(file))


def analyze_population_fidelity(
    specification: dict[str, Any],
    output_directory: str | Path,
) -> dict[str, Any]:
    """Compare requested population with generated population."""

    entities: dict[str, Any] = {}

    for entity in specification.get("entities", []):
        entity_name = entity.get("name")
        requested = entity.get("population", {}).get("count", 0)
        actual = len(load_entity_rows(output_directory, entity_name))

        entities[entity_name] = {
            "requested_rows": requested,
            "generated_rows": actual,
            "difference": actual - requested,
            "fidelity_rate": (
                actual / requested
                if requested
                else 1.0
            ),
        }

    total_requested = sum(
        metric["requested_rows"]
        for metric in entities.values()
    )
    total_generated = sum(
        metric["generated_rows"]
        for metric in entities.values()
    )

    return {
        "total_requested_rows": total_requested,
        "total_generated_rows": total_generated,
        "difference": total_generated - total_requested,
        "fidelity_rate": (
            total_generated / total_requested
            if total_requested
            else 1.0
        ),
        "entities": entities,
    }


def _distribution_counts(
    rows: list[dict[str, str]],
    field_name: str,
) -> Counter[str]:
    """Count observed values for one field."""

    return Counter(
        row[field_name]
        for row in rows
        if row.get(field_name) not in (None, "")
    )


def analyze_distribution_fidelity(
    specification: dict[str, Any],
    output_directory: str | Path,
) -> dict[str, Any]:
    """Compare declared finite categorical distributions with observations."""

    fields: dict[str, Any] = {}

    for entity in specification.get("entities", []):
        entity_name = entity.get("name")
        rows = load_entity_rows(output_directory, entity_name)

        for field in entity.get("fields", []):
            field_name = field.get("name")
            generation = field.get("generation", {})
            distribution = generation.get("distribution")
            parameters = generation.get("parameters", {})
            values = parameters.get("values")

            if distribution != "CATEGORICAL" or not isinstance(
                values,
                list,
            ):
                continue

            observed_counts = _distribution_counts(
                rows,
                field_name,
            )

            observed_total = sum(observed_counts.values())
            expected_probability = (
                1.0 / len(values)
                if values
                else 0.0
            )

            value_metrics: dict[str, Any] = {}

            for value in values:
                value_string = str(value)
                observed_count = observed_counts.get(
                    value_string,
                    0,
                )
                observed_probability = (
                    observed_count / observed_total
                    if observed_total
                    else 0.0
                )

                value_metrics[value_string] = {
                    "observed_count": observed_count,
                    "observed_probability": observed_probability,
                    "expected_probability": expected_probability,
                    "absolute_probability_difference": abs(
                        observed_probability
                        - expected_probability
                    ),
                }

            fields[f"{entity_name}.{field_name}"] = {
                "entity": entity_name,
                "field": field_name,
                "distribution": distribution,
                "rows_observed": observed_total,
                "declared_values": [
                    str(value)
                    for value in values
                ],
                "values": value_metrics,
            }

    return {
        "fields_analyzed": len(fields),
        "fields": fields,
    }


def _relationship_key(
    row: dict[str, str],
    fields: tuple[str, ...],
) -> tuple[str, ...]:
    """Build a relationship key from a generated row."""

    return tuple(row[field] for field in fields)


def analyze_relationship_fidelity(
    specification: dict[str, Any],
    output_directory: str | Path,
    relationship_groups: tuple[Any, ...] = (),
) -> dict[str, Any]:
    """Measure observed fidelity of grouped relationships.

    RelationshipGroup is authoritative for composite relationship
    semantics. Raw specification relationships are used only when
    no grouped relationship information is supplied.
    """

    relationships: dict[str, Any] = {}

    if relationship_groups:
        groups = relationship_groups
    else:
        groups = ()

        for relationship in specification.get("relationships", []):
            source = relationship.get("source")
            target = relationship.get("target")

            if not isinstance(source, str) or not isinstance(target, str):
                continue

            if "." not in source or "." not in target:
                continue

            source_entity, source_field = source.split(".", 1)
            target_entity, target_field = target.split(".", 1)

            # Compatibility fallback for older callers.
            groups += (
                type(
                    "RelationshipGroupFallback",
                    (),
                    {
                        "parent_entity": source_entity,
                        "child_entity": target_entity,
                        "parent_fields": (source_field,),
                        "child_fields": (target_field,),
                        "relationship_type": relationship.get("type"),
                        "parent_participation": relationship.get(
                            "source_participation"
                        ),
                        "child_participation": relationship.get(
                            "target_participation"
                        ),
                    },
                )(),
            )

    for index, group in enumerate(groups, start=1):
        parent_entity = group.parent_entity
        child_entity = group.child_entity
        parent_fields = tuple(group.parent_fields)
        child_fields = tuple(group.child_fields)

        parent_rows = load_entity_rows(
            output_directory,
            parent_entity,
        )
        child_rows = load_entity_rows(
            output_directory,
            child_entity,
        )

        parent_keys = {
            _relationship_key(row, parent_fields)
            for row in parent_rows
        }

        child_counts: Counter[tuple[str, ...]] = Counter()

        for row in child_rows:
            child_counts[
                _relationship_key(row, child_fields)
            ] += 1

        participating_parent_count = sum(
            1
            for key in parent_keys
            if child_counts.get(key, 0) > 0
        )

        orphan_child_count = sum(
            count
            for key, count in child_counts.items()
            if key not in parent_keys
        )

        observed_counts = list(child_counts.values())

        relationships[f"relationship_group_{index}"] = {
            "parent_entity": parent_entity,
            "child_entity": child_entity,
            "parent_fields": list(parent_fields),
            "child_fields": list(child_fields),
            "relationship_type": group.relationship_type,
            "parent_participation": group.parent_participation,
            "child_participation": group.child_participation,
            "composite": len(parent_fields) > 1,
            "parent_keys": len(parent_keys),
            "participating_parent_keys": (
                participating_parent_count
            ),
            "parent_participation_rate": (
                participating_parent_count / len(parent_keys)
                if parent_keys
                else 0.0
            ),
            "child_rows": len(child_rows),
            "orphan_child_rows": orphan_child_count,
            "minimum_children_per_parent": (
                min(observed_counts)
                if observed_counts
                else 0
            ),
            "maximum_children_per_parent": (
                max(observed_counts)
                if observed_counts
                else 0
            ),
            "average_children_per_participating_parent": (
                sum(observed_counts)
                / len(observed_counts)
                if observed_counts
                else 0.0
            ),
        }

    return {
        "relationships_analyzed": len(relationships),
        "relationships": relationships,
    }



def _finite_domain_size(
    field: dict[str, Any],
) -> int | None:
    """Return finite domain size when explicitly determinable."""

    generation = field.get("generation", {})
    parameters = generation.get("parameters", {})
    distribution = generation.get("distribution")

    values = parameters.get("values")

    if distribution == "CATEGORICAL" and isinstance(
        values,
        list,
    ):
        return len(values)

    if distribution in {
        "DISCRETE_UNIFORM",
        "UNIFORM",
    }:
        minimum = parameters.get("minimum")
        maximum = parameters.get("maximum")

        if (
            isinstance(minimum, (int, float))
            and isinstance(maximum, (int, float))
            and minimum.is_integer()
            and maximum.is_integer()
        ):
            return int(maximum - minimum + 1)

    return None


def _field_domain_size(
    field: dict[str, Any],
) -> int | None:
    """Return a directly declared finite domain size."""

    generation = field.get("generation", {})
    parameters = generation.get("parameters", {})
    distribution = generation.get("distribution")

    values = parameters.get("values")

    if distribution == "CATEGORICAL" and isinstance(
        values,
        list,
    ):
        return len(values)

    if distribution in {
        "DISCRETE_UNIFORM",
        "UNIFORM",
    }:
        minimum = parameters.get("minimum")
        maximum = parameters.get("maximum")

        if (
            isinstance(minimum, int)
            and isinstance(maximum, int)
            and maximum >= minimum
        ):
            return maximum - minimum + 1

    return None


def analyze_identity_space_utilization(
    specification: dict[str, Any],
    output_directory: str | Path,
    relationship_groups: tuple[Any, ...] = (),
) -> dict[str, Any]:
    """Measure identity-space utilization where capacity is determinable.

    Parent-backed identity fields are treated as one identity dimension
    when they belong to the same relationship group. Remaining identity
    fields are evaluated as independent finite domains.
    """

    entity_map = {
        entity.get("name"): entity
        for entity in specification.get("entities", [])
    }

    group_by_child: dict[str, list[Any]] = defaultdict(list)

    for group in relationship_groups:
        group_by_child[group.child_entity].append(group)

    entities: dict[str, Any] = {}

    for entity in specification.get("entities", []):
        entity_name = entity.get("name")

        identity_fields = tuple(
            entity.get("identity", {}).get("fields", [])
        )

        if not identity_fields:
            continue

        identity_field_set = set(identity_fields)

        field_map = {
            field.get("name"): field
            for field in entity.get("fields", [])
        }

        dimensions: list[int] = []
        dimension_sources: list[str] = []
        parent_backed_fields: set[str] = set()
        determinable = True

        # --------------------------------------------------------------
        # Parent-backed identity dimensions.
        #
        # A relationship group maps one or more child identity fields
        # to one parent key space. The complete group is ONE dimension.
        # --------------------------------------------------------------
        for group in group_by_child.get(entity_name, []):
            child_fields = tuple(group.child_fields)

            if not child_fields:
                continue

            if not all(
                field in identity_field_set
                for field in child_fields
            ):
                continue

            # Do not count the same identity fields through overlapping
            # relationship groups more than once.
            if parent_backed_fields.intersection(child_fields):
                continue

            parent_entity = entity_map.get(
                group.parent_entity
            )

            if parent_entity is None:
                determinable = False
                break

            parent_rows = load_entity_rows(
                output_directory,
                group.parent_entity,
            )

            parent_fields = tuple(group.parent_fields)

            parent_keys = {
                _relationship_key(
                    row,
                    parent_fields,
                )
                for row in parent_rows
            }

            if not parent_keys:
                determinable = False
                break

            dimensions.append(len(parent_keys))

            dimension_sources.append(
                "parent:"
                f"{group.parent_entity}"
                f"{parent_fields}"
            )

            parent_backed_fields.update(child_fields)

        if not determinable:
            entities[entity_name] = {
                "identity_fields": list(identity_fields),
                "capacity_determinable": False,
            }
            continue

        # --------------------------------------------------------------
        # Remaining identity fields are independently generated fields.
        # --------------------------------------------------------------
        for field_name in identity_fields:
            if field_name in parent_backed_fields:
                continue

            field = field_map.get(field_name)

            if field is None:
                determinable = False
                break

            domain_size = _field_domain_size(field)

            if domain_size is None:
                determinable = False
                break

            dimensions.append(domain_size)
            dimension_sources.append(
                f"field:{field_name}"
            )

        if not determinable or not dimensions:
            entities[entity_name] = {
                "identity_fields": list(identity_fields),
                "capacity_determinable": False,
            }
            continue

        capacity = math.prod(dimensions)

        rows = load_entity_rows(
            output_directory,
            entity_name,
        )

        identities = {
            tuple(row[field] for field in identity_fields)
            for row in rows
        }

        entities[entity_name] = {
            "identity_fields": list(identity_fields),
            "capacity_determinable": True,
            "dimension_sizes": dimensions,
            "dimension_sources": dimension_sources,
            "identity_space_capacity": capacity,
            "generated_unique_identities": len(identities),
            "utilization_rate": (
                len(identities) / capacity
                if capacity
                else 0.0
            ),
        }

    return {
        "entities_analyzed": len(entities),
        "entities": entities,
    }



def _numeric_statistics(
    values: list[str],
) -> dict[str, Any] | None:
    """Calculate descriptive statistics for numeric values."""

    numeric_values: list[float] = []

    for value in values:
        try:
            numeric_values.append(float(value))
        except (TypeError, ValueError):
            return None

    if not numeric_values:
        return None

    ordered = sorted(numeric_values)
    count = len(ordered)

    def percentile(percent: float) -> float:
        if count == 1:
            return ordered[0]

        position = (count - 1) * percent
        lower = math.floor(position)
        upper = math.ceil(position)

        if lower == upper:
            return ordered[lower]

        weight = position - lower
        return (
            ordered[lower] * (1.0 - weight)
            + ordered[upper] * weight
        )

    mean = sum(ordered) / count

    variance = (
        sum((value - mean) ** 2 for value in ordered)
        / count
    )

    return {
        "count": count,
        "minimum": ordered[0],
        "maximum": ordered[-1],
        "mean": mean,
        "standard_deviation": math.sqrt(variance),
        "p50": percentile(0.50),
        "p95": percentile(0.95),
    }


def analyze_statistical_fidelity(
    specification: dict[str, Any],
    output_directory: str | Path,
) -> dict[str, Any]:
    """Report descriptive statistics for numeric generated fields."""

    fields: dict[str, Any] = {}

    for entity in specification.get("entities", []):
        entity_name = entity.get("name")
        rows = load_entity_rows(output_directory, entity_name)

        for field in entity.get("fields", []):
            field_name = field.get("name")

            values = [
                row[field_name]
                for row in rows
                if row.get(field_name) not in (None, "")
            ]

            statistics = _numeric_statistics(values)

            if statistics is None:
                continue

            fields[f"{entity_name}.{field_name}"] = {
                "entity": entity_name,
                "field": field_name,
                "statistics": statistics,
            }

    return {
        "numeric_fields_analyzed": len(fields),
        "fields": fields,
    }


def analyze_performance(
    generation_result: Any | None,
) -> dict[str, Any]:
    """Extract generation performance from a completed generation result."""

    if generation_result is None:
        return {
            "available": False,
        }

    total_rows = getattr(
        generation_result,
        "total_generated_rows",
        None,
    )

    if total_rows is None:
        return {
            "available": False,
        }

    # Prefer an explicit elapsed duration when the execution result
    # provides one.
    elapsed_seconds = getattr(
        generation_result,
        "elapsed_seconds",
        None,
    )

    # GenerationJob does not expose elapsed_seconds directly. Derive
    # the duration from its lifecycle timestamps instead.
    if elapsed_seconds is None:
        started_at = getattr(
            generation_result,
            "started_at",
            None,
        )
        completed_at = getattr(
            generation_result,
            "completed_at",
            None,
        )

        if started_at and completed_at:
            try:
                started = datetime.fromisoformat(started_at)
                completed = datetime.fromisoformat(completed_at)
                elapsed_seconds = (
                    completed - started
                ).total_seconds()
            except (TypeError, ValueError):
                elapsed_seconds = None

    if elapsed_seconds is None:
        return {
            "available": False,
        }

    return {
        "available": True,
        "total_generated_rows": total_rows,
        "elapsed_seconds": elapsed_seconds,
        "rows_per_second": (
            total_rows / elapsed_seconds
            if elapsed_seconds > 0
            else None
        ),
    }


def build_quality_profile(
    specification: dict[str, Any],
    output_directory: str | Path,
    validation_evidence: dict[str, Any] | None = None,
    generation_result: Any | None = None,
    generation_plan: Any | None = None,
) -> dict[str, Any]:
    """Build the measurable FORGE quality profile."""

    return {
        "population_fidelity": analyze_population_fidelity(
            specification,
            output_directory,
        ),
        "distribution_fidelity": analyze_distribution_fidelity(
            specification,
            output_directory,
        ),
        "relationship_fidelity": analyze_relationship_fidelity(
            specification,
            output_directory,
            (
                generation_plan.relationship_groups
                if generation_plan is not None
                else ()
            ),
        ),
        "identity_space_utilization": (
            analyze_identity_space_utilization(
                specification,
                output_directory,
                (
                    generation_plan.relationship_groups
                    if generation_plan is not None
                    else ()
                ),
            )
        ),
        "statistical_fidelity": analyze_statistical_fidelity(
            specification,
            output_directory,
        ),
        "performance": analyze_performance(
            generation_result,
        ),
        "validation": validation_evidence or {},
    }
