
from dataclasses import asdict
from typing import Any

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

        entities = {
            entity["name"]: entity
            for entity in specification.get("entities", [])
        }

        plan = build_population_plan(
            populations=populations,
            relationships=specification.get("relationships", []),
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

        entities = {
            entity["name"]: entity
            for entity in specification.get("entities", [])
        }

        plan = build_population_plan(
            populations=populations,
            relationships=specification.get("relationships", []),
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
        result["feasible"] = (
            all(
                population["status"] == "FEASIBLE"
                for population in result["populations"].values()
            )
            and allocation.feasible_target
        )

        return result
