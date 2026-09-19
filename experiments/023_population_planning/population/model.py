"""Data structures used by the FORGE population planner."""

from dataclasses import dataclass
from enum import Enum
from typing import Optional


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


@dataclass(frozen=True)
class ForeignKeyDependency:
    """Foreign-key relationship required for population capacity analysis."""

    foreign_key_name: str
    parent_entity: str
    source_fields: tuple[str, ...]
    target_fields: tuple[str, ...]


@dataclass
class EntityPopulation:
    """Population request and resolution state for one entity."""

    entity: str

    mode: PopulationMode

    requested: Optional[int] = None

    minimum_feasible: Optional[int] = None

    resolved: Optional[int] = None

    status: PopulationStatus = PopulationStatus.UNRESOLVED

    reason: Optional[str] = None

    recommendation: Optional[str] = None

    def __post_init__(self) -> None:
        """Validate basic population semantics."""

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
        """Create an explicit user-requested population."""

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
        """Create an AUTO population request."""

        return cls(
            entity=entity,
            mode=PopulationMode.AUTO,
        )
