"""
FORGE Generation Core
Generation planning.

This module converts a validated FORGE specification into
a UI-independent generation plan.

No data is generated here.
"""

from __future__ import annotations

from dataclasses import dataclass

from .job import EntityGenerationProgress, GenerationJob
from .specification import SpecificationError


@dataclass(frozen=True)
class EntityGenerationPlan:
    """Generation requirements for one entity."""

    entity_name: str
    target_rows: int


@dataclass(frozen=True)
class GenerationPlan:
    """Generation requirements for a complete specification."""

    entities: tuple[EntityGenerationPlan, ...]

    @property
    def total_target_rows(self) -> int:
        """Return the total number of rows requested."""

        return sum(
            entity.target_rows
            for entity in self.entities
        )


def build_generation_plan(
    specification: dict,
) -> GenerationPlan:
    """
    Build a generation plan from a FORGE specification.

    This function only extracts generation requirements.
    Validation of the specification is handled separately.
    """

    entities = specification.get("entities")

    if not isinstance(entities, list):
        raise SpecificationError(
            "FORGE specification must contain an entities list."
        )

    plans: list[EntityGenerationPlan] = []

    for entity in entities:
        if not isinstance(entity, dict):
            raise SpecificationError(
                "Each FORGE entity must be an object."
            )

        entity_name = entity.get("name")

        if not isinstance(entity_name, str) or not entity_name:
            raise SpecificationError(
                "Each FORGE entity must have a non-empty name."
            )

        population = entity.get("population")

        if not isinstance(population, dict):
            raise SpecificationError(
                f"{entity_name}: population must be an object."
            )

        target_rows = population.get("count")

        if (
            not isinstance(target_rows, int)
            or isinstance(target_rows, bool)
            or target_rows < 0
        ):
            raise SpecificationError(
                f"{entity_name}: population.count must be "
                "a non-negative integer."
            )

        plans.append(
            EntityGenerationPlan(
                entity_name=entity_name,
                target_rows=target_rows,
            )
        )

    return GenerationPlan(
        entities=tuple(plans),
    )


def initialize_job_progress(
    job: GenerationJob,
    plan: GenerationPlan,
) -> GenerationJob:
    """
    Initialize entity-level progress from a generation plan.

    The supplied job is updated in place and returned for convenience.
    """

    job.entities = {
        entity_plan.entity_name: EntityGenerationProgress(
            entity_name=entity_plan.entity_name,
            target_rows=entity_plan.target_rows,
        )
        for entity_plan in plan.entities
    }

    return job
