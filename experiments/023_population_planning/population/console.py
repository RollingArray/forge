"""Console reporting for FORGE population planning."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .model import ForeignKeyDependency
from .planner import PopulationPlan, build_population_plan


def _format_population_value(value: int | None) -> str:
    """Format an optional population value for console output."""

    if value is None:
        return "-"

    return f"{value:,}"


def _format_population_row(
    entity: str,
    plan: PopulationPlan,
) -> str:
    """Format one population analysis table row."""

    population = plan.populations[entity]

    requested = _format_population_value(population.requested)

    minimum = _format_population_value(population.minimum_feasible)

    maximum = _format_population_value(plan.maximums.get(entity))

    resolved = _format_population_value(population.resolved)

    return (
        f"{entity:<20}"
        f"{requested:>15}"
        f"{minimum:>15}"
        f"{maximum:>15}"
        f"{resolved:>15}"
        f"  {population.status.value:<12}"
    )


def _format_population_analysis_details(
    plan: PopulationPlan,
) -> list[str]:
    """Format population reasons and recommendations."""

    lines: list[str] = []

    for entity in sorted(plan.populations):
        population = plan.populations[entity]

        if population.reason:
            lines.append(f"{entity}:")
            lines.append(f"  {population.reason}")

        if population.recommendation:
            lines.append(f"  Recommendation: {population.recommendation}")

    return lines


def format_population_analysis(plan: PopulationPlan) -> str:
    """Format a population plan as a human-readable analysis."""

    lines: list[str] = []

    lines.append("Population Analysis")
    lines.append("=" * 105)
    lines.append(
        f"{'Entity':<20}"
        f"{'Requested':>15}"
        f"{'Minimum':>15}"
        f"{'Maximum':>15}"
        f"{'Resolved':>15}"
        f"  {'Status':<12}"
    )
    lines.append("-" * 105)

    for entity in sorted(plan.populations):
        lines.append(
            _format_population_row(
                entity=entity,
                plan=plan,
            )
        )

    lines.append("")
    lines.append("Analysis")
    lines.append("-" * 105)
    lines.extend(_format_population_analysis_details(plan))

    return "\n".join(lines)


def print_population_analysis(plan: PopulationPlan) -> None:
    """Print a population plan to the console."""

    print(format_population_analysis(plan))


def population_plan_to_dict(
    plan: PopulationPlan,
) -> dict[str, Any]:
    """Convert a population plan into a JSON-serializable structure."""

    populations: dict[str, dict[str, Any]] = {}

    for entity, population in plan.populations.items():
        populations[entity] = {
            "mode": population.mode.value,
            "requested": population.requested,
            "minimum_feasible": population.minimum_feasible,
            "resolved": population.resolved,
            "status": population.status.value,
            "reason": population.reason,
            "recommendation": population.recommendation,
        }

    return {
        "populations": populations,
        "minimums": plan.minimums,
        "maximums": plan.maximums,
        "relationship_requirements": [
            {
                "entity": requirement.entity,
                "minimum": requirement.minimum,
                "relationship": requirement.relationship,
                "reason": requirement.reason,
            }
            for requirement in plan.relationship_requirements
        ],
        "capacity_requirements": [
            {
                "entity": requirement.entity,
                "minimum": requirement.minimum,
                "relationship": requirement.relationship,
                "reason": requirement.reason,
            }
            for requirement in plan.capacity_requirements
        ],
        "capacity_limits": [
            {
                "entity": limit.entity,
                "maximum": limit.maximum,
                "relationship": limit.relationship,
                "reason": limit.reason,
            }
            for limit in plan.capacity_limits
        ],
    }


def write_population_plan(
    plan: PopulationPlan,
    path: str | Path,
) -> Path:
    """Write the population plan as JSON."""

    output_path = Path(path)

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with output_path.open(
        "w",
        encoding="utf-8",
    ) as handle:
        json.dump(
            population_plan_to_dict(plan),
            handle,
            indent=2,
        )
        handle.write("\n")

    return output_path


def load_specification(
    path: str | Path,
) -> dict[str, Any]:
    """Load a FORGE specification JSON file."""

    specification_path = Path(path)

    with specification_path.open(
        "r",
        encoding="utf-8",
    ) as handle:
        return json.load(handle)


def build_population_inputs(
    specification: dict[str, Any],
) -> dict[str, int | str]:
    """Extract entity populations from a FORGE specification."""

    populations: dict[str, int | str] = {}

    for entity in specification.get("entities", []):
        name = entity["name"]
        population = entity.get("population", {})

        count = population.get("count")

        if count is None:
            populations[name] = "AUTO"
        else:
            populations[name] = count

    return populations


def build_entities_metadata(
    specification: dict[str, Any],
) -> dict[str, dict[str, Any]]:
    """Build the entity metadata required by capacity analysis."""

    entities: dict[str, dict[str, Any]] = {}

    for entity in specification.get("entities", []):
        entities[entity["name"]] = {
            "identity": entity.get("identity", {}).get("fields", [])
        }

    return entities


def build_relationships(
    specification: dict[str, Any],
) -> list[dict[str, Any]]:
    """Extract relationship definitions from a FORGE specification."""

    return list(specification.get("relationships", []))


def build_dependencies_by_entity(
    specification: dict[str, Any],
) -> dict[str, tuple[Any, ...]]:
    """Build FK dependencies required for population capacity analysis."""

    dependencies: dict[str, list[ForeignKeyDependency]] = {}

    for foreign_key in specification.get("foreign_keys", []):
        source = foreign_key["source"]
        target = foreign_key["target"]

        dependency = ForeignKeyDependency(
            foreign_key_name=foreign_key["name"],
            parent_entity=target["entity"],
            source_fields=tuple(source["fields"]),
            target_fields=tuple(target["fields"]),
        )

        dependencies.setdefault(
            source["entity"],
            [],
        ).append(dependency)

    return {
        entity: tuple(entity_dependencies)
        for entity, entity_dependencies in dependencies.items()
    }


def build_plan_from_specification(
    specification: dict[str, Any],
) -> PopulationPlan:
    """Build a population plan directly from a FORGE specification."""

    populations = build_population_inputs(specification)
    relationships = build_relationships(specification)
    entities = build_entities_metadata(specification)
    dependencies = build_dependencies_by_entity(specification)

    return build_population_plan(
        populations=populations,
        relationships=relationships,
        dependencies_by_entity=dependencies,
        entities=entities,
    )
