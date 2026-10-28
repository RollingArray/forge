from __future__ import annotations

from collections import Counter
from typing import Any

from app.services.generation.artifact_reader import GenerationArtifactReader
from app.services.generation_planner import GenerationPlan


class GenerationQualityService:
    """Measure quality characteristics of generated data."""

    def __init__(
        self,
        *,
        artifact_reader: GenerationArtifactReader,
    ) -> None:
        self._artifact_reader = artifact_reader

    def analyze_population_fidelity(
        self,
        *,
        specification: dict[str, Any],
        plan: GenerationPlan,
        data_model_id: str,
        job_id: str,
    ) -> dict[str, Any]:
        """Compare requested population with generated population."""

        entities: dict[str, Any] = {}

        for entity in specification.get("entities", []):
            entity_name = entity.get("name")
            requested = self._target_rows(plan, entity_name)
            actual = self._count_rows(
                data_model_id=data_model_id,
                job_id=job_id,
                entity_name=entity_name,
            )

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

    @staticmethod
    def _field_domain_size(
        field: dict[str, Any],
    ) -> int | None:
        """Return a directly declared finite domain size."""

        generation = field.get("generation") or {}
        parameters = generation.get("parameters") or {}
        distribution = generation.get("distribution")

        values = parameters.get("values")

        if distribution == "CATEGORICAL" and isinstance(values, list):
            return len(values)

        if distribution in {"DISCRETE_UNIFORM", "UNIFORM"}:
            minimum = parameters.get("minimum")
            maximum = parameters.get("maximum")

            if (
                isinstance(minimum, int)
                and isinstance(maximum, int)
                and maximum >= minimum
            ):
                return maximum - minimum + 1

        return None

    @staticmethod
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
            lower = int(position // 1)
            upper = int(-(-position // 1))

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
            "standard_deviation": variance ** 0.5,
            "p50": percentile(0.50),
            "p95": percentile(0.95),
        }

    @staticmethod
    def analyze_performance(
        *,
        total_generated_rows: int,
        elapsed_seconds: float | None,
    ) -> dict[str, Any]:
        """Report generation performance from completed execution."""

        if elapsed_seconds is None or elapsed_seconds < 0:
            return {
                "available": False,
            }

        return {
            "available": True,
            "total_generated_rows": total_generated_rows,
            "elapsed_seconds": elapsed_seconds,
            "rows_per_second": (
                total_generated_rows / elapsed_seconds
                if elapsed_seconds > 0
                else None
            ),
        }

    def build_quality_profile(
        self,
        *,
        specification: dict[str, Any],
        plan: GenerationPlan,
        data_model_id: str,
        job_id: str,
        total_generated_rows: int,
        elapsed_seconds: float | None,
        validation: dict[str, Any],
    ) -> dict[str, Any]:
        """Build the measurable FORGE quality profile."""

        return {
            "population_fidelity": (
                self.analyze_population_fidelity(
                    specification=specification,
                    plan=plan,
                    data_model_id=data_model_id,
                    job_id=job_id,
                )
            ),
            "distribution_fidelity": (
                self.analyze_distribution_fidelity(
                    specification=specification,
                    data_model_id=data_model_id,
                    job_id=job_id,
                )
            ),
            "relationship_fidelity": (
                self.analyze_relationship_fidelity(
                    specification=specification,
                    plan=plan,
                    data_model_id=data_model_id,
                    job_id=job_id,
                )
            ),
            "identity_space_utilization": (
                self.analyze_identity_space_utilization(
                    specification=specification,
                    plan=plan,
                    data_model_id=data_model_id,
                    job_id=job_id,
                )
            ),
            "statistical_fidelity": (
                self.analyze_statistical_fidelity(
                    specification=specification,
                    data_model_id=data_model_id,
                    job_id=job_id,
                )
            ),
            "performance": self.analyze_performance(
                total_generated_rows=total_generated_rows,
                elapsed_seconds=elapsed_seconds,
            ),
            "validation": validation,
        }

    def analyze_statistical_fidelity(
        self,
        *,
        specification: dict[str, Any],
        data_model_id: str,
        job_id: str,
    ) -> dict[str, Any]:
        """Report descriptive statistics for numeric generated fields."""

        fields: dict[str, Any] = {}

        for entity in specification.get("entities", []):
            entity_name = entity.get("name")

            field_values: dict[str, list[str]] = {
                field.get("name"): []
                for field in entity.get("fields", [])
            }

            for row in self._artifact_reader.iter_entity_chunks(
                data_model_id=data_model_id,
                job_id=job_id,
                entity_name=entity_name,
            ):
                for field_name in field_values:
                    value = row.get(field_name)

                    if value not in (None, ""):
                        field_values[field_name].append(value)

            for field_name, values in field_values.items():
                statistics = self._numeric_statistics(values)

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

    def analyze_identity_space_utilization(
        self,
        *,
        specification: dict[str, Any],
        plan: GenerationPlan,
        data_model_id: str,
        job_id: str,
    ) -> dict[str, Any]:
        """Measure identity-space utilization where capacity is determinable."""

        entity_map = {
            entity.get("name"): entity
            for entity in specification.get("entities", [])
        }

        group_by_child: dict[str, list[Any]] = {}

        for group in plan.relationship_groups:
            relationship_type = group.relationship_type.upper()

            # These relationship types do not establish a child-side
            # identity capacity from the group's parent key count.
            if relationship_type in {"MANY_TO_ONE", "MANY_TO_MANY"}:
                continue

            group_by_child.setdefault(
                group.child_entity,
                [],
            ).append(group)

        entities: dict[str, Any] = {}

        for entity in specification.get("entities", []):
            entity_name = entity.get("name")

            identity_fields = tuple(
                entity.get("identity", {}).get("fields", [])
            )

            if not identity_fields:
                continue

            identity_field_set = set(identity_fields)

            identities: set[tuple[Any, ...]] = set()

            for row in self._artifact_reader.iter_entity_chunks(
                data_model_id=data_model_id,
                job_id=job_id,
                entity_name=entity_name,
            ):
                identities.add(
                    tuple(
                        row[field]
                        for field in identity_fields
                    )
                )

            generated_unique_identities = len(identities)

            field_map = {
                field.get("name"): field
                for field in entity.get("fields", [])
            }

            dimensions: list[int] = []
            dimension_sources: list[str] = []
            parent_backed_fields: set[str] = set()
            determinable = True

            for group in group_by_child.get(entity_name, []):
                child_fields = tuple(group.child_fields)

                if not child_fields:
                    continue

                if not all(
                    field in identity_field_set
                    for field in child_fields
                ):
                    continue

                if parent_backed_fields.intersection(child_fields):
                    continue

                parent_entity = entity_map.get(group.parent_entity)

                if parent_entity is None:
                    determinable = False
                    break

                parent_keys: set[tuple[str, ...]] = set()

                for row in self._artifact_reader.iter_entity_chunks(
                    data_model_id=data_model_id,
                    job_id=job_id,
                    entity_name=group.parent_entity,
                ):
                    parent_keys.add(
                        tuple(
                            row[field]
                            for field in group.parent_fields
                        )
                    )

                if not parent_keys:
                    determinable = False
                    break

                dimensions.append(len(parent_keys))
                dimension_sources.append(
                    "parent:"
                    f"{group.parent_entity}"
                    f"{group.parent_fields}"
                )
                parent_backed_fields.update(child_fields)

            if not determinable:
                entities[entity_name] = {
                    "identity_fields": list(identity_fields),
                    "capacity_determinable": False,
                    "generated_unique_identities": generated_unique_identities,
                }
                continue

            for field_name in identity_fields:
                if field_name in parent_backed_fields:
                    continue

                field = field_map.get(field_name)

                if field is None:
                    determinable = False
                    break

                domain_size = self._field_domain_size(field)

                if domain_size is None:
                    determinable = False
                    break

                dimensions.append(domain_size)
                dimension_sources.append(f"field:{field_name}")

            if not determinable or not dimensions:
                entities[entity_name] = {
                    "identity_fields": list(identity_fields),
                    "capacity_determinable": False,
                    "generated_unique_identities": generated_unique_identities,
                }
                continue

            capacity = 1
            for dimension in dimensions:
                capacity *= dimension

            entities[entity_name] = {
                "identity_fields": list(identity_fields),
                "capacity_determinable": True,
                "dimension_sizes": dimensions,
                "dimension_sources": dimension_sources,
                "identity_space_capacity": capacity,
                "generated_unique_identities": generated_unique_identities,
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

    def analyze_relationship_fidelity(
        self,
        *,
        specification: dict[str, Any],
        plan: GenerationPlan,
        data_model_id: str,
        job_id: str,
    ) -> dict[str, Any]:
        """Measure observed fidelity of grouped relationships."""

        relationships: dict[str, Any] = {}

        def is_missing_key_value(value: Any) -> bool:
            return value is None or (
                isinstance(value, str) and not value.strip()
            )

        for index, group in enumerate(
            plan.relationship_groups,
            start=1,
        ):
            relationship_type = group.relationship_type.upper()

            if relationship_type == "MANY_TO_MANY":
                relationships[f"relationship_group_{index}"] = {
                    "measurement_status": "not_measurable",
                    "measurement_note": (
                        "A direct MANY_TO_MANY declaration does not "
                        "establish a parent-key/child-FK mapping. "
                        "Cardinality and participation require explicit "
                        "association or junction evidence."
                    ),
                    "source_entity": group.parent_entity,
                    "target_entity": group.child_entity,
                    "source_fields": list(group.parent_fields),
                    "target_fields": list(group.child_fields),
                    "relationship_type": group.relationship_type,
                    "source_participation": group.parent_participation,
                    "target_participation": group.child_participation,
                }
                continue

            if relationship_type == "MANY_TO_ONE":
                parent_entity = group.child_entity
                child_entity = group.parent_entity
                parent_fields = group.child_fields
                child_fields = group.parent_fields
                parent_participation = group.child_participation
                child_participation = group.parent_participation
            else:
                parent_entity = group.parent_entity
                child_entity = group.child_entity
                parent_fields = group.parent_fields
                child_fields = group.child_fields
                parent_participation = group.parent_participation
                child_participation = group.child_participation

            parent_key_counts: Counter[tuple[Any, ...]] = Counter()
            parent_rows_checked = 0
            parent_rows_with_null_key = 0

            for row in self._artifact_reader.iter_entity_chunks(
                data_model_id=data_model_id,
                job_id=job_id,
                entity_name=parent_entity,
            ):
                parent_rows_checked += 1
                key = tuple(row[field] for field in parent_fields)

                if any(is_missing_key_value(value) for value in key):
                    parent_rows_with_null_key += 1
                    continue

                parent_key_counts[key] += 1

            parent_keys = set(parent_key_counts)
            duplicate_parent_key_rows = sum(
                count - 1
                for count in parent_key_counts.values()
                if count > 1
            )

            child_counts: Counter[tuple[Any, ...]] = Counter()
            child_rows_checked = 0
            null_reference_rows = 0
            partial_null_reference_rows = 0

            for row in self._artifact_reader.iter_entity_chunks(
                data_model_id=data_model_id,
                job_id=job_id,
                entity_name=child_entity,
            ):
                child_rows_checked += 1
                key = tuple(row[field] for field in child_fields)
                null_count = sum(is_missing_key_value(value) for value in key)

                if null_count == len(key):
                    null_reference_rows += 1
                    continue

                if null_count:
                    partial_null_reference_rows += 1
                    continue

                child_counts[key] += 1

            matched_child_rows = sum(
                count
                for key, count in child_counts.items()
                if key in parent_keys
            )

            orphan_child_count = sum(
                count
                for key, count in child_counts.items()
                if key not in parent_keys
            )

            children_per_parent = [
                child_counts.get(key, 0)
                for key in parent_keys
            ]
            participating_parent_count = sum(
                count > 0 for count in children_per_parent
            )
            parents_without_children = sum(
                count == 0 for count in children_per_parent
            )
            one_to_one_cardinality_violations = (
                sum(count > 1 for count in children_per_parent)
                if relationship_type == "ONE_TO_ONE"
                else None
            )

            measurement_notes = []
            if not parent_keys:
                measurement_notes.append(
                    "No usable non-null parent keys were found."
                )
            if duplicate_parent_key_rows:
                measurement_notes.append(
                    "Duplicate parent keys make reference matching "
                    "ambiguous."
                )
            if partial_null_reference_rows:
                measurement_notes.append(
                    "Partially null composite references were excluded "
                    "from matched and orphan counts."
                )

            measurement_status = (
                "inconclusive"
                if not parent_keys or duplicate_parent_key_rows
                else "measured"
            )

            relationships[f"relationship_group_{index}"] = {
                "measurement_status": measurement_status,
                "measurement_note": (
                    " ".join(measurement_notes)
                    if measurement_notes
                    else None
                ),
                "parent_entity": parent_entity,
                "child_entity": child_entity,
                "parent_fields": list(parent_fields),
                "child_fields": list(child_fields),
                "relationship_type": group.relationship_type,
                "parent_participation": parent_participation,
                "child_participation": child_participation,
                "composite": len(group.parent_fields) > 1,
                "parent_rows_checked": parent_rows_checked,
                "parent_rows_with_null_key": parent_rows_with_null_key,
                "parent_keys": len(parent_keys),
                "duplicate_parent_key_rows": duplicate_parent_key_rows,
                "child_rows_checked": child_rows_checked,
                "child_rows": child_rows_checked,
                "matched_child_rows": matched_child_rows,
                "orphan_child_rows": orphan_child_count,
                "null_reference_rows": null_reference_rows,
                "partial_null_reference_rows": partial_null_reference_rows,
                "mandatory_child_reference_violations": (
                    null_reference_rows + partial_null_reference_rows
                    if child_participation.upper() == "MANDATORY"
                    else 0
                ),
                "participating_parent_keys": participating_parent_count,
                "parents_without_children": parents_without_children,
                "parent_participation_rate": (
                    participating_parent_count / len(parent_keys)
                    if parent_keys
                    else None
                ),
                "mandatory_parent_participation_violations": (
                    parents_without_children
                    if parent_participation.upper() == "MANDATORY"
                    else 0
                ),
                "minimum_children_per_parent": (
                    min(children_per_parent)
                    if children_per_parent
                    else None
                ),
                "maximum_children_per_parent": (
                    max(children_per_parent)
                    if children_per_parent
                    else None
                ),
                "average_children_per_participating_parent": (
                    sum(
                        count for count in children_per_parent if count > 0
                    ) / participating_parent_count
                    if participating_parent_count
                    else None
                ),
                "one_to_one_cardinality_violations": (
                    one_to_one_cardinality_violations
                ),
            }

        return {
            "relationships_analyzed": len(relationships),
            "relationships": relationships,
        }

    def analyze_distribution_fidelity(
        self,
        *,
        specification: dict[str, Any],
        data_model_id: str,
        job_id: str,
    ) -> dict[str, Any]:
        """Measure declared categorical distributions against observations."""

        fields: dict[str, Any] = {}

        for entity in specification.get("entities", []):
            entity_name = entity.get("name")

            for field in entity.get("fields", []):
                field_name = field.get("name")
                generation = field.get("generation") or {}
                distribution = generation.get("distribution")
                parameters = generation.get("parameters") or {}
                values = parameters.get("values")

                if distribution != "CATEGORICAL" or not isinstance(
                    values,
                    list,
                ):
                    continue

                observed_counts, rows_total, missing_count = (
                    self._distribution_counts(
                        data_model_id=data_model_id,
                        job_id=job_id,
                        entity_name=entity_name,
                        field_name=field_name,
                    )
                )

                observed_total = sum(observed_counts.values())

                # Match random.choice(values): duplicate entries contribute
                # additional probability to their stringified category.
                configured_counts = Counter(str(value) for value in values)
                configured_total = len(values)
                value_metrics: dict[str, Any] = {}
                probability_differences: list[float] = []

                for value_string, configured_count in configured_counts.items():
                    expected_probability = (
                        configured_count / configured_total
                        if configured_total
                        else 0.0
                    )
                    observed_count = observed_counts.get(
                        value_string,
                        0,
                    )
                    observed_probability = (
                        observed_count / observed_total
                        if observed_total
                        else 0.0
                    )
                    absolute_difference = abs(
                        observed_probability - expected_probability
                    )
                    probability_differences.append(absolute_difference)

                    value_metrics[value_string] = {
                        "observed_count": observed_count,
                        "observed_probability": observed_probability,
                        "expected_probability": expected_probability,
                        "absolute_probability_difference": absolute_difference,
                    }

                declared_category_count = len(configured_counts)
                observed_category_count = sum(
                    1
                    for value_string in configured_counts
                    if observed_counts.get(value_string, 0) > 0
                )

                fields[f"{entity_name}.{field_name}"] = {
                    "entity": entity_name,
                    "field": field_name,
                    "distribution": distribution,
                    "rows_observed": observed_total,
                    "rows_total": rows_total,
                    "missing_count": missing_count,
                    "missing_rate": (
                        missing_count / rows_total
                        if rows_total
                        else 0.0
                    ),
                    "declared_category_count": declared_category_count,
                    "observed_category_count": observed_category_count,
                    "category_coverage": (
                        observed_category_count / declared_category_count
                        if declared_category_count
                        else 0.0
                    ),
                    "maximum_absolute_probability_difference": max(
                        probability_differences,
                        default=0.0,
                    ),
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

    def _target_rows(
        self,
        plan: GenerationPlan,
        entity_name: str,
    ) -> int:
        for entity in plan.entities:
            if entity.entity_name == entity_name:
                return entity.target_rows
        return 0

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

    def _distribution_counts(
        self,
        *,
        data_model_id: str,
        job_id: str,
        entity_name: str,
        field_name: str,
    ) -> tuple[Counter[str], int, int]:
        counts: Counter[str] = Counter()
        rows_total = 0
        missing_count = 0

        for row in self._artifact_reader.iter_entity_chunks(
            data_model_id=data_model_id,
            job_id=job_id,
            entity_name=entity_name,
        ):
            rows_total += 1
            value = row.get(field_name)
            if value in (None, ""):
                missing_count += 1
            else:
                counts[str(value)] += 1

        return counts, rows_total, missing_count
