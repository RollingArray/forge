
from dataclasses import asdict
from typing import Any

from app.services.population.adapter import (
    build_dependencies_by_entity,
    build_entities_metadata,
)
from app.services.population.allocator import allocate_population_target
from app.services.population.planner import build_population_plan
from app.services.specification_service import SpecificationService


class PopulationService:
    def __init__(
        self,
        specification_service: SpecificationService | None = None,
    ) -> None:
        self.specification_service = (
            specification_service
            if specification_service is not None
            else SpecificationService()
        )

    def get_population_plan(
        self,
        data_model_id: str,
    ) -> dict[str, Any] | None:
        specification = self.specification_service.get_specification(
            data_model_id
        )

        if specification is None:
            return None

        populations = {
            entity["name"]: entity.get("population") or {}
            for entity in specification.get("entities", [])
        }

        entities = build_entities_metadata(specification)
        dependencies = build_dependencies_by_entity(specification)

        plan = build_population_plan(
            populations=populations,
            relationships=specification.get("relationships", []),
            dependencies_by_entity=dependencies,
            entities=entities,
        )

        result = asdict(plan)

        for entity_name, population in result["populations"].items():
            population["scaling"] = (
                populations[entity_name].get("scaling", "SCALABLE")
            )

        return result

    def build_candidate_plan(
        self,
        data_model_id: str,
        target: int,
        driver: str,
    ) -> dict[str, Any] | None:
        specification = self.specification_service.get_specification(
            data_model_id
        )

        if specification is None:
            return None

        allocation = allocate_population_target(
            specification=specification,
            target=target,
            driver=driver,
        )

        populations = {
            entity["name"]: {
                **(entity.get("population") or {}),
                "count": allocation.populations[entity["name"]],
            }
            for entity in specification.get("entities", [])
        }

        entities = build_entities_metadata(specification)
        dependencies = build_dependencies_by_entity(specification)

        plan = build_population_plan(
            populations=populations,
            relationships=specification.get("relationships", []),
            dependencies_by_entity=dependencies,
            entities=entities,
        )

        result = asdict(plan)

        for entity_name, population in result["populations"].items():
            population["scaling"] = (
                populations[entity_name].get("scaling", "SCALABLE")
            )

        result["target"] = allocation.target
        result["driver"] = allocation.driver
        result["fixed_total"] = allocation.fixed_total
        result["unaffected_total"] = allocation.unaffected_total
        result["scalable_total"] = allocation.scalable_total
        result["allocated_total"] = allocation.allocated_total
        result["affected_entities"] = list(allocation.affected_entities)
        result["target_feasible"] = allocation.feasible_target
        result["target_reason"] = allocation.reason
        result["allocation_status"] = allocation.status
        result["allocation_diagnostics"] = list(allocation.diagnostics)
        result["feasible"] = (
            allocation.status == "FEASIBLE"
            and allocation.feasible_target
            and allocation.allocated_total == allocation.target
            and all(
                population["status"] == "FEASIBLE"
                for population in result["populations"].values()
            )
        )

        return result
