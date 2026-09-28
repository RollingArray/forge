"""
File: serializer.py
Purpose: Serialize a production population plan into the FORGE API contract.
"""

from typing import Any

from .planner import PopulationPlan


def population_plan_to_dict(plan: PopulationPlan) -> dict[str, Any]:
    """Serialize a population plan into a JSON-compatible structure."""

    return {
        "populations": {
            entity: {
                "mode": population.mode.value,
                "requested": population.requested,
                "minimum_feasible": population.minimum_feasible,
                "resolved": population.resolved,
                "status": population.status.value,
                "reason": population.reason,
                "recommendation": population.recommendation,
            }
            for entity, population in plan.populations.items()
        },
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
