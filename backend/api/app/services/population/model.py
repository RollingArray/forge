"""
File: model.py
Purpose: Domain models for FORGE population planning.
"""

from dataclasses import dataclass
from enum import Enum


class PopulationMode(str, Enum):
    """How an entity population is specified."""

    EXPLICIT = "EXPLICIT"
    AUTO = "AUTO"


class PopulationStatus(str, Enum):
    """Current feasibility state of an entity population."""

    FEASIBLE = "FEASIBLE"
    INFEASIBLE = "INFEASIBLE"
    AUTO = "AUTO"
    UNRESOLVED = "UNRESOLVED"


@dataclass
class EntityPopulation:
    """Population request and resolution state for one entity."""

    entity: str
    mode: PopulationMode
    requested: int | None = None
    minimum_feasible: int | None = None
    resolved: int | None = None
    status: PopulationStatus = PopulationStatus.UNRESOLVED
    reason: str | None = None
    recommendation: str | None = None

    def __post_init__(self) -> None:
        if self.mode == PopulationMode.EXPLICIT:
            if self.requested is None:
                raise ValueError(
                    f"Explicit population for '{self.entity}' "
                    "requires a requested count."
                )

            if self.requested < 0:
                raise ValueError(
                    f"Population for '{self.entity}' cannot be negative."
                )

        if self.mode == PopulationMode.AUTO:
            if self.requested is not None:
                raise ValueError(
                    f"AUTO population for '{self.entity}' "
                    "cannot have a requested count."
                )

    @classmethod
    def explicit(
        cls,
        entity: str,
        count: int,
    ) -> "EntityPopulation":
        return cls(
            entity=entity,
            mode=PopulationMode.EXPLICIT,
            requested=count,
            resolved=count,
        )

    @classmethod
    def auto(
        cls,
        entity: str,
    ) -> "EntityPopulation":
        return cls(
            entity=entity,
            mode=PopulationMode.AUTO,
        )
