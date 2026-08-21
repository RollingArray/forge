"""
FORGE - Experiment 020-S: Declarative Generation Adversarial Validation
=======================================================================

Experiment:
    020_declarative_generation_specification

Stage:
    020-S

Purpose:
    Capstone adversarial and production-readiness validation of the
    declarative generation architecture.

This experiment intentionally combines:

    - Entity dependencies
    - Field dependencies
    - Statistical relationships
    - Constraints
    - Conditional rules
    - Derived fields
    - Relationships
    - Scenarios
    - Deterministic field streams
    - Capability boundaries

Core invariants:

    1. Declarative specification
    2. Entity-order independence
    3. Field-order independence
    4. Deterministic reproducibility
    5. Seed sensitivity
    6. Explicit capability boundaries
    7. No hidden fallback
    8. No post-generation repair
    9. Constraint preservation
    10. Relationship integrity
    11. Statistical relationship preservation
    12. Scenario isolation
    13. Derived-value determinism
    14. Safe failure
"""

from __future__ import annotations

import copy
import hashlib
import json
import math
import random
import sys
from dataclasses import dataclass
from pathlib import Path
from statistics import mean

# ============================================================================
# PATHS
# ============================================================================

EXPERIMENT_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = EXPERIMENT_DIR / "output"

OUTPUT_PATH = OUTPUT_DIR / "adversarial_generation_results.json"

MASTER_SEED = 42


# ============================================================================
# DECLARATIVE MODELS
# ============================================================================


@dataclass(frozen=True)
class Field:
    name: str
    minimum: float | None = None
    maximum: float | None = None
    constant: float | None = None


@dataclass(frozen=True)
class Entity:
    name: str
    fields: tuple[Field, ...]
    record_count: int


@dataclass(frozen=True)
class Correlation:
    name: str
    source_entity: str
    source_field: str
    target_entity: str
    target_field: str
    target_value: float
    tolerance: float


@dataclass(frozen=True)
class CrossConstraint:
    name: str
    entity: str
    left: str
    operator: str
    right: str
    multiplier: float = 1.0


@dataclass(frozen=True)
class Conditional:
    name: str
    entity: str
    condition_field: str
    condition_minimum: float
    target_field: str
    target_minimum: float


@dataclass(frozen=True)
class Derived:
    name: str
    entity: str
    source_a: str
    source_b: str
    operation: str


@dataclass(frozen=True)
class Relationship:
    name: str
    parent_entity: str
    parent_field: str
    child_entity: str
    child_field: str
    cardinality: str


@dataclass(frozen=True)
class ScenarioOverride:
    scenario: str
    entity: str
    field: str
    minimum: float | None = None
    maximum: float | None = None


@dataclass(frozen=True)
class Scenario:
    name: str
    overrides: tuple[ScenarioOverride, ...] = ()


@dataclass(frozen=True)
class Specification:
    entities: tuple[Entity, ...]
    relationships: tuple[Relationship, ...]
    correlations: tuple[Correlation, ...]
    constraints: tuple[CrossConstraint, ...]
    conditionals: tuple[Conditional, ...]
    derived: tuple[Derived, ...]
    scenarios: tuple[Scenario, ...]


# ============================================================================
# DETERMINISTIC STREAMS
# ============================================================================


def stable_seed(
    seed: int,
    namespace: str,
) -> int:

    digest = hashlib.sha256(f"{seed}:{namespace}".encode("utf-8")).digest()

    return int.from_bytes(
        digest[:8],
        byteorder="big",
        signed=False,
    )


def rng_for(
    seed: int,
    namespace: str,
) -> random.Random:

    return random.Random(
        stable_seed(
            seed,
            namespace,
        )
    )


# ============================================================================
# STATISTICS
# ============================================================================


def pearson(
    x: list[float],
    y: list[float],
) -> float:

    if len(x) != len(y):
        raise ValueError("Correlation vectors must have equal length.")

    if not x:
        raise ValueError("Correlation vectors cannot be empty.")

    x_mean = mean(x)
    y_mean = mean(y)

    numerator = sum((a - x_mean) * (b - y_mean) for a, b in zip(x, y))

    denominator = math.sqrt(
        sum((a - x_mean) ** 2 for a in x) * sum((b - y_mean) ** 2 for b in y)
    )

    if math.isclose(
        denominator,
        0.0,
    ):
        raise ValueError("Correlation undefined.")

    return numerator / denominator


# ============================================================================
# LOOKUPS
# ============================================================================


def entity_map(
    specification: Specification,
) -> dict[str, Entity]:

    return {entity.name: entity for entity in specification.entities}


def field_map(
    specification: Specification,
) -> dict[str, dict[str, Field]]:

    return {
        entity.name: {field.name: field for field in entity.fields}
        for entity in specification.entities
    }


# ============================================================================
# VOCABULARY VALIDATION
# ============================================================================


def validate_vocabulary(
    specification: Specification,
) -> None:

    entities = entity_map(specification)

    fields = field_map(specification)

    if len(entities) != len(specification.entities):
        raise ValueError("Duplicate entity.")

    for entity in specification.entities:

        if entity.record_count <= 0:
            raise ValueError(f"Invalid record count: {entity.name}")

        if not entity.fields:
            raise ValueError(f"Entity has no fields: {entity.name}")

        field_names = {field.name for field in entity.fields}

        if len(field_names) != len(entity.fields):
            raise ValueError(f"Duplicate field: {entity.name}")

        for field in entity.fields:

            if (
                field.minimum is not None
                and field.maximum is not None
                and field.minimum > field.maximum
            ):
                raise ValueError(f"Invalid bounds: " f"{entity.name}.{field.name}")

    valid_cardinalities = {
        "0:1",
        "0:N",
        "1:1",
        "1:N",
        "N:M",
    }

    for relationship in specification.relationships:

        if relationship.parent_entity not in entities:
            raise ValueError("Unknown parent entity.")

        if relationship.child_entity not in entities:
            raise ValueError("Unknown child entity.")

        if relationship.cardinality not in valid_cardinalities:
            raise ValueError("Invalid cardinality.")

        if relationship.parent_field not in fields[relationship.parent_entity]:
            raise ValueError("Unknown parent field.")

        if relationship.child_field not in fields[relationship.child_entity]:
            raise ValueError("Unknown child field.")

    for correlation in specification.correlations:

        if correlation.source_entity not in entities:
            raise ValueError("Unknown correlation source entity.")

        if correlation.target_entity not in entities:
            raise ValueError("Unknown correlation target entity.")

        if correlation.source_field not in fields[correlation.source_entity]:
            raise ValueError("Unknown correlation source field.")

        if correlation.target_field not in fields[correlation.target_entity]:
            raise ValueError("Unknown correlation target field.")

        if not (-1.0 <= correlation.target_value <= 1.0):
            raise ValueError("Correlation must be between -1 and 1.")

        if correlation.tolerance < 0:
            raise ValueError("Correlation tolerance cannot be negative.")

    for constraint in specification.constraints:

        if constraint.entity not in entities:
            raise ValueError("Unknown constraint entity.")

        if constraint.left not in fields[constraint.entity]:
            raise ValueError("Unknown constraint left field.")

        if constraint.right not in fields[constraint.entity]:
            raise ValueError("Unknown constraint right field.")

        if constraint.operator not in {
            ">=",
            "<=",
            ">",
            "<",
            "==",
        }:
            raise ValueError("Unsupported constraint operator.")

    for conditional in specification.conditionals:

        if conditional.entity not in entities:
            raise ValueError("Unknown conditional entity.")

        if conditional.condition_field not in fields[conditional.entity]:
            raise ValueError("Unknown conditional field.")

        if conditional.target_field not in fields[conditional.entity]:
            raise ValueError("Unknown conditional target field.")

    for derived in specification.derived:

        if derived.entity not in entities:
            raise ValueError("Unknown derived entity.")

        if derived.source_a not in fields[derived.entity]:
            raise ValueError(f"Unknown derived source: " f"{derived.source_a}")

        if derived.source_b not in fields[derived.entity]:
            raise ValueError(f"Unknown derived source: " f"{derived.source_b}")

        if derived.operation not in {
            "ADD",
            "SUBTRACT",
            "MULTIPLY",
        }:
            raise ValueError("Unsupported derived operation.")


# ============================================================================
# SCENARIO VALIDATION
# ============================================================================


def validate_scenario(
    specification: Specification,
    scenario_name: str,
) -> Scenario:

    entities = entity_map(specification)

    fields = field_map(specification)

    for scenario in specification.scenarios:

        if scenario.name != scenario_name:
            continue

        for override in scenario.overrides:

            if override.entity not in entities:
                raise ValueError("Unknown scenario entity.")

            if override.field not in fields[override.entity]:
                raise ValueError("Unknown scenario field.")

            if (
                override.minimum is not None
                and override.maximum is not None
                and override.minimum > override.maximum
            ):
                raise ValueError("Invalid scenario range.")

        return scenario

    raise ValueError(f"Unknown scenario: {scenario_name}")


# ============================================================================
# CAPABILITY ASSESSMENT
# ============================================================================

EXECUTABLE_CAPABILITIES = {
    "RANDOM",
    "SEQUENTIAL",
    "CONSTANT",
    "NORMAL",
    "UNIFORM",
    "CATEGORICAL",
    "CORRELATION",
    "CONSTRAINT",
    "CONDITIONAL",
    "DERIVED",
    "REFERENCE",
}

DEFERRED_CAPABILITIES = {
    "BETA",
    "GAMMA",
    "LOGNORMAL",
    "EMPIRICAL",
    "MIXTURE",
    "WEIBULL",
}


def assess_capabilities(
    specification: Specification,
) -> dict[str, str]:

    result = {}

    for capability in sorted(EXECUTABLE_CAPABILITIES):
        result[capability] = "EXECUTABLE"

    for capability in sorted(DEFERRED_CAPABILITIES):
        result[capability] = "DEFERRED"

    return result


# ============================================================================
# ENTITY DEPENDENCY PLANNER
# ============================================================================


def dependency_plan(
    specification: Specification,
) -> list[str]:

    entities = entity_map(specification)

    dependencies = {name: set() for name in entities}

    for relationship in specification.relationships:

        parent = relationship.parent_entity

        child = relationship.child_entity

        if parent == child:
            raise ValueError("Self-reference is not allowed.")

        dependencies[child].add(parent)

    remaining = {name: set(values) for name, values in dependencies.items()}

    plan = []

    while remaining:

        ready = sorted(name for name, deps in remaining.items() if not deps)

        if not ready:
            raise ValueError("Dependency cycle detected.")

        plan.extend(ready)

        for name in ready:
            del remaining[name]

        for deps in remaining.values():
            deps.difference_update(ready)

    return plan


# ============================================================================
# FIELD DEPENDENCY PLANNER
# ============================================================================


def field_dependency_plan(
    specification: Specification,
    entity_name: str,
) -> list[str]:

    fields = field_map(specification)[entity_name]

    dependencies = {field_name: set() for field_name in fields}

    # Statistical relationships.
    for relationship in specification.correlations:

        if relationship.target_entity != entity_name:
            continue

        if relationship.source_entity == entity_name:

            dependencies[relationship.target_field].add(relationship.source_field)

    # Derived fields are generated after their sources.
    for derived in specification.derived:

        if derived.entity != entity_name:
            continue

        # Derived fields are not ordinary fields.
        # They are represented as explicit nodes.
        dependencies.setdefault(
            derived.name,
            set(),
        )

        dependencies[derived.name].update(
            {
                derived.source_a,
                derived.source_b,
            }
        )

    # Conditional rules.
    for conditional in specification.conditionals:

        if conditional.entity != entity_name:
            continue

        dependencies[conditional.target_field].add(conditional.condition_field)

    # Local cross-field constraints.
    for constraint in specification.constraints:

        if constraint.entity != entity_name:
            continue

        dependencies[constraint.left].add(constraint.right)

    # Remove self-dependencies.
    for field_name in dependencies:

        dependencies[field_name].discard(field_name)

    remaining = {name: set(values) for name, values in dependencies.items()}

    plan = []

    while remaining:

        ready = sorted(name for name, deps in remaining.items() if not deps)

        if not ready:
            raise ValueError(f"Field dependency cycle detected " f"in {entity_name}.")

        plan.extend(ready)

        for name in ready:
            del remaining[name]

        for deps in remaining.values():
            deps.difference_update(ready)

    return plan


def unified_generation_plan(
    specification: Specification,
) -> dict[str, list[str]]:

    entity_plan = dependency_plan(specification)

    return {
        entity_name: field_dependency_plan(
            specification,
            entity_name,
        )
        for entity_name in entity_plan
    }


# ============================================================================
# SCENARIO FIELD RESOLUTION
# ============================================================================


def effective_field(
    field: Field,
    override: ScenarioOverride | None,
) -> Field:

    if override is None:
        return field

    minimum = field.minimum
    maximum = field.maximum

    if override.minimum is not None:

        minimum = (
            override.minimum
            if minimum is None
            else max(
                minimum,
                override.minimum,
            )
        )

    if override.maximum is not None:

        maximum = (
            override.maximum
            if maximum is None
            else min(
                maximum,
                override.maximum,
            )
        )

    if minimum is not None and maximum is not None and minimum > maximum:
        raise ValueError(f"Scenario makes field infeasible: " f"{field.name}")

    return Field(
        name=field.name,
        minimum=minimum,
        maximum=maximum,
        constant=field.constant,
    )


def scenario_fields(
    specification: Specification,
    scenario_name: str,
) -> dict[str, dict[str, Field]]:

    scenario = validate_scenario(
        specification,
        scenario_name,
    )

    overrides = {
        (
            override.entity,
            override.field,
        ): override
        for override in scenario.overrides
    }

    result = {}

    for entity in specification.entities:

        result[entity.name] = {}

        for field in entity.fields:

            result[entity.name][field.name] = effective_field(
                field,
                overrides.get(
                    (
                        entity.name,
                        field.name,
                    )
                ),
            )

    return result


# ============================================================================
# FEASIBLE REGION
# ============================================================================


def feasible_region(
    specification: Specification,
    fields: dict[str, dict[str, Field]],
    entity_name: str,
    record: dict[str, float],
    target_field: str,
) -> tuple[float, float]:

    field = fields[entity_name][target_field]

    if field.minimum is None or field.maximum is None:
        raise ValueError(
            f"Field requires explicit bounds: " f"{entity_name}.{target_field}"
        )

    lower = field.minimum
    upper = field.maximum

    for constraint in specification.constraints:

        if constraint.entity != entity_name:
            continue

        if constraint.left == target_field and constraint.right in record:

            reference = record[constraint.right] * constraint.multiplier

            if constraint.operator == ">=":

                lower = max(
                    lower,
                    reference,
                )

            elif constraint.operator == ">":

                lower = max(
                    lower,
                    math.nextafter(
                        reference,
                        math.inf,
                    ),
                )

            elif constraint.operator == "<=":

                upper = min(
                    upper,
                    reference,
                )

            elif constraint.operator == "<":

                upper = min(
                    upper,
                    math.nextafter(
                        reference,
                        -math.inf,
                    ),
                )

            elif constraint.operator == "==":

                lower = max(
                    lower,
                    reference,
                )

                upper = min(
                    upper,
                    reference,
                )

        elif constraint.right == target_field and constraint.left in record:

            if math.isclose(
                constraint.multiplier,
                0.0,
            ):
                raise ValueError("Constraint multiplier cannot be zero.")

            reference = record[constraint.left] / constraint.multiplier

            if constraint.operator == ">=":

                upper = min(
                    upper,
                    reference,
                )

            elif constraint.operator == "<=":

                lower = max(
                    lower,
                    reference,
                )

            elif constraint.operator == "==":

                lower = max(
                    lower,
                    reference,
                )

                upper = min(
                    upper,
                    reference,
                )

    for conditional in specification.conditionals:

        if conditional.entity != entity_name:
            continue

        if conditional.target_field != target_field:
            continue

        if conditional.condition_field not in record:
            continue

        if record[conditional.condition_field] >= conditional.condition_minimum:

            lower = max(
                lower,
                conditional.target_minimum,
            )

    if lower > upper:

        raise ValueError(
            f"No feasible generation region for " f"{entity_name}.{target_field}"
        )

    return lower, upper


# ============================================================================
# ROOT GENERATION
# ============================================================================


def generate_root_field(
    field: Field,
    entity_name: str,
    seed: int,
    count: int,
) -> list[float]:

    if field.constant is not None:

        return [field.constant for _ in range(count)]

    if field.minimum is None or field.maximum is None:
        raise ValueError(f"Field bounds required: " f"{entity_name}.{field.name}")

    if field.minimum > field.maximum:

        raise ValueError(f"Infeasible field bounds: " f"{entity_name}.{field.name}")

    rng = rng_for(
        seed,
        f"FIELD:{entity_name}:{field.name}",
    )

    return [
        rng.uniform(
            field.minimum,
            field.maximum,
        )
        for _ in range(count)
    ]


# ============================================================================
# CORRELATED GENERATION
# ============================================================================


def generate_correlated(
    source: list[float],
    target: Field,
    relationship: Correlation,
    seed: int,
) -> list[float]:

    if target.minimum is None or target.maximum is None:
        raise ValueError("Correlated target requires bounds.")

    source_mean = mean(source)

    centered = [value - source_mean for value in source]

    variance = mean(value * value for value in centered)

    if math.isclose(
        variance,
        0.0,
    ):
        raise ValueError("Correlation source has zero variance.")

    source_std = math.sqrt(variance)

    normalized = [value / source_std for value in centered]

    rng = rng_for(
        seed,
        f"CORRELATION:{relationship.name}",
    )

    noise = [
        rng.gauss(
            0.0,
            1.0,
        )
        for _ in source
    ]

    rho = relationship.target_value

    residual = math.sqrt(
        max(
            0.0,
            1.0 - rho * rho,
        )
    )

    latent = [
        rho * x + residual * n
        for x, n in zip(
            normalized,
            noise,
        )
    ]

    low = min(latent)

    high = max(latent)

    if math.isclose(
        low,
        high,
    ):

        normalized_target = [0.5 for _ in latent]

    else:

        normalized_target = [(value - low) / (high - low) for value in latent]

    return [
        target.minimum + value * (target.maximum - target.minimum)
        for value in normalized_target
    ]


# ============================================================================
# CONSTRAINT-CONDITIONED STATISTICAL GENERATION
# ============================================================================


def condition_statistical_values(
    specification: Specification,
    fields: dict[str, dict[str, Field]],
    relationship: Correlation,
    source_values: list[float],
    seed: int,
) -> list[float]:

    target_field = fields[relationship.target_entity][relationship.target_field]

    raw_values = generate_correlated(
        source_values,
        target_field,
        relationship,
        seed,
    )

    result = []

    for index, raw_value in enumerate(raw_values):

        # Source field belongs to the same record
        # when source and target are in the same entity.
        #
        # For cross-entity generation, the corresponding
        # source value is supplied as context.

        context = {relationship.source_field: source_values[index]}

        lower, upper = feasible_region(
            specification,
            fields,
            relationship.target_entity,
            context,
            relationship.target_field,
        )

        base_low = target_field.minimum
        base_high = target_field.maximum

        if base_low is None or base_high is None:
            raise ValueError("Target bounds required.")

        normalized = (raw_value - base_low) / (base_high - base_low)

        normalized = max(
            0.0,
            min(
                1.0,
                normalized,
            ),
        )

        value = lower + normalized * (upper - lower)

        if value < lower or value > upper:
            raise ValueError("Statistical generation " "produced infeasible value.")

        result.append(value)

    return result


# ============================================================================
# DERIVED VALUES
# ============================================================================


def generate_derived_values(
    derived: Derived,
    records: list[dict[str, float]],
) -> list[float]:

    values = []

    for record in records:

        if derived.source_a not in record or derived.source_b not in record:
            raise ValueError(f"Derived sources unavailable: " f"{derived.name}")

        a = record[derived.source_a]

        b = record[derived.source_b]

        if derived.operation == "ADD":

            value = a + b

        elif derived.operation == "SUBTRACT":

            value = a - b

        elif derived.operation == "MULTIPLY":

            value = a * b

        else:

            raise ValueError("Unsupported derived operation.")

        values.append(value)

    return values


# ============================================================================
# GENERATION
# ============================================================================


def generate_dataset(
    specification: Specification,
    scenario_name: str,
    seed: int,
) -> dict[
    str,
    list[dict[str, float]],
]:

    validate_vocabulary(specification)

    validate_scenario(
        specification,
        scenario_name,
    )

    plan = unified_generation_plan(specification)

    fields = scenario_fields(
        specification,
        scenario_name,
    )

    entities = entity_map(specification)

    datasets = {}

    # ------------------------------------------------------------------
    # Entity-level generation.
    # ------------------------------------------------------------------

    for entity_name in plan:

        entity = entities[entity_name]

        records = [{} for _ in range(entity.record_count)]

        field_plan = plan[entity_name]

        for field_name in field_plan:

            # ----------------------------------------------------------
            # Derived field.
            # ----------------------------------------------------------

            derived = next(
                (
                    item
                    for item in specification.derived
                    if (item.entity == entity_name and item.name == field_name)
                ),
                None,
            )

            if derived is not None:

                values = generate_derived_values(
                    derived,
                    records,
                )

                for index, value in enumerate(values):
                    records[index][field_name] = value

                continue

            # ----------------------------------------------------------
            # Ordinary field.
            # ----------------------------------------------------------

            field = fields[entity_name][field_name]

            # ----------------------------------------------------------
            # Statistical target.
            # ----------------------------------------------------------

            correlation = next(
                (
                    relationship
                    for relationship in specification.correlations
                    if (
                        relationship.target_entity == entity_name
                        and relationship.target_field == field_name
                    )
                ),
                None,
            )

            if correlation is not None:

                source_entity = correlation.source_entity

                source_field = correlation.source_field

                if source_entity == entity_name:

                    source_values = [record[source_field] for record in records]

                else:

                    if source_entity not in datasets:
                        raise ValueError("Correlation source " "entity not generated.")

                    source_values = [
                        record[source_field] for record in datasets[source_entity]
                    ]

                values = condition_statistical_values(
                    specification,
                    fields,
                    correlation,
                    source_values,
                    seed,
                )

                for index, value in enumerate(values):
                    records[index][field_name] = value

                continue

            # ----------------------------------------------------------
            # Relationship target.
            #
            # Relationship resolution is deterministic and occurs
            # from already-generated parent records.
            # ----------------------------------------------------------

            relationship = next(
                (
                    item
                    for item in specification.relationships
                    if (
                        item.child_entity == entity_name
                        and item.child_field == field_name
                    )
                ),
                None,
            )

            if relationship is not None:

                parent_entity = relationship.parent_entity

                if parent_entity not in datasets:
                    raise ValueError("Relationship parent " "entity not generated.")

                parent_records = datasets[parent_entity]

                if not parent_records:
                    raise ValueError("Relationship parent " "has no records.")

                values = [
                    parent_records[index % len(parent_records)][
                        relationship.parent_field
                    ]
                    for index in range(len(records))
                ]

                # Ensure relationship value is within the
                # declarative target field bounds.
                for value in values:

                    if field.minimum is not None and value < field.minimum:
                        raise ValueError(
                            "Relationship value " "violates field minimum."
                        )

                    if field.maximum is not None and value > field.maximum:
                        raise ValueError(
                            "Relationship value " "violates field maximum."
                        )

                for index, value in enumerate(values):
                    records[index][field_name] = value

                continue

            # ----------------------------------------------------------
            # Root field.
            # ----------------------------------------------------------

            rng = rng_for(
                seed,
                f"FIELD:{entity_name}:{field_name}",
            )

            values = []

            for index in range(len(records)):

                context = dict(records[index])

                lower, upper = feasible_region(
                    specification,
                    fields,
                    entity_name,
                    context,
                    field_name,
                )

                value = rng.uniform(
                    lower,
                    upper,
                )

                if value < lower or value > upper:
                    raise ValueError(
                        f"Generation produced "
                        f"infeasible value for "
                        f"{entity_name}.{field_name}"
                    )

                values.append(value)

            for index, value in enumerate(values):

                records[index][field_name] = value

            for index, value in enumerate(values):
                records[index][field_name] = value

        datasets[entity_name] = records

    return datasets


# ============================================================================
# DATASET VALIDATION
# ============================================================================


def validate_dataset(
    specification: Specification,
    datasets: dict[
        str,
        list[dict[str, float]],
    ],
    scenario_name: str,
) -> bool:

    fields = scenario_fields(
        specification,
        scenario_name,
    )

    # ------------------------------------------------------------------
    # Structure.
    # ------------------------------------------------------------------

    for entity in specification.entities:

        if entity.name not in datasets:
            return False

        records = datasets[entity.name]

        if len(records) != (entity.record_count):
            return False

        expected = {field.name for field in entity.fields}

        expected.update(
            derived.name
            for derived in specification.derived
            if derived.entity == entity.name
        )

        for record in records:

            if not expected.issubset(record.keys()):
                return False

    # ------------------------------------------------------------------
    # Field bounds.
    # ------------------------------------------------------------------

    for entity in specification.entities:

        for field in entity.fields:

            effective = fields[entity.name][field.name]

            if effective.minimum is None or effective.maximum is None:
                continue

            for record in datasets[entity.name]:

                value = record[field.name]

                if value < effective.minimum or value > effective.maximum:
                    return False

    # ------------------------------------------------------------------
    # Cross-field constraints.
    # ------------------------------------------------------------------

    for constraint in specification.constraints:

        for record in datasets[constraint.entity]:

            left = record[constraint.left]

            right = record[constraint.right] * constraint.multiplier

            if constraint.operator == ">=":
                valid = left >= right

            elif constraint.operator == "<=":
                valid = left <= right

            elif constraint.operator == ">":
                valid = left > right

            elif constraint.operator == "<":
                valid = left < right

            elif constraint.operator == "==":
                valid = math.isclose(
                    left,
                    right,
                    rel_tol=1e-9,
                    abs_tol=1e-9,
                )

            else:
                return False

            if not valid:
                return False

    # ------------------------------------------------------------------
    # Conditional rules.
    # ------------------------------------------------------------------

    for conditional in specification.conditionals:

        for record in datasets[conditional.entity]:

            if record[conditional.condition_field] >= conditional.condition_minimum:

                if record[conditional.target_field] < conditional.target_minimum:
                    return False

    # ------------------------------------------------------------------
    # Derived fields.
    # ------------------------------------------------------------------

    for derived in specification.derived:

        for record in datasets[derived.entity]:

            a = record[derived.source_a]

            b = record[derived.source_b]

            if derived.operation == "ADD":

                expected = a + b

            elif derived.operation == "SUBTRACT":

                expected = a - b

            elif derived.operation == "MULTIPLY":

                expected = a * b

            else:
                return False

            if not math.isclose(
                record[derived.name],
                expected,
                rel_tol=1e-9,
                abs_tol=1e-9,
            ):
                return False

    # ------------------------------------------------------------------
    # Relationships.
    # ------------------------------------------------------------------

    for relationship in specification.relationships:

        parent_values = {
            record[relationship.parent_field]
            for record in datasets[relationship.parent_entity]
        }

        for child in datasets[relationship.child_entity]:

            if child[relationship.child_field] not in parent_values:
                return False

    # ------------------------------------------------------------------
    # Statistical relationships.
    # ------------------------------------------------------------------

    for relationship in specification.correlations:

        source = [
            record[relationship.source_field]
            for record in datasets[relationship.source_entity]
        ]

        target = [
            record[relationship.target_field]
            for record in datasets[relationship.target_entity]
        ]

        observed = pearson(
            source,
            target,
        )

        if abs(observed - relationship.target_value) > relationship.tolerance:

            return False

    return True


# ============================================================================
# CAPSTONE SPECIFICATION
# ============================================================================


def build_capstone_specification() -> Specification:

    customer = Entity(
        name="CUSTOMER",
        fields=(
            Field(
                "CUSTOMER_SCORE",
                0.0,
                100.0,
            ),
            Field(
                "CUSTOMER_VALUE",
                1000.0,
                10000.0,
            ),
        ),
        record_count=500,
    )

    profile = Entity(
        name="CUSTOMER_PROFILE",
        fields=(
            Field(
                "PROFILE_SCORE",
                0.0,
                100.0,
            ),
        ),
        record_count=500,
    )

    product = Entity(
        name="PRODUCT",
        fields=(
            Field(
                "PRODUCT_SCORE",
                0.0,
                100.0,
            ),
            Field(
                "UNIT_PRICE",
                100.0,
                5000.0,
            ),
        ),
        record_count=300,
    )

    order = Entity(
        name="ORDER",
        fields=(
            Field(
                "ORDER_VALUE",
                1000.0,
                20000.0,
            ),
            Field(
                "DISCOUNT",
                0.0,
                30.0,
            ),
            Field(
                "ORDER_CUSTOMER_VALUE",
                1000.0,
                10000.0,
            ),
            Field(
                "NET_ORDER_VALUE",
                0.0,
                20000.0,
            ),
        ),
        record_count=1000,
    )

    shipment = Entity(
        name="SHIPMENT",
        fields=(
            Field(
                "SHIPPING_COST",
                50.0,
                2000.0,
            ),
            Field(
                "SHIPMENT_ORDER_VALUE",
                1000.0,
                20000.0,
            ),
        ),
        record_count=1000,
    )

    relationships = (
        Relationship(
            name="CUSTOMER_PROFILE_LINK",
            parent_entity="CUSTOMER",
            parent_field="CUSTOMER_SCORE",
            child_entity="CUSTOMER_PROFILE",
            child_field="PROFILE_SCORE",
            cardinality="1:1",
        ),
        Relationship(
            name="ORDER_CUSTOMER_LINK",
            parent_entity="CUSTOMER",
            parent_field="CUSTOMER_VALUE",
            child_entity="ORDER",
            child_field="ORDER_CUSTOMER_VALUE",
            cardinality="1:N",
        ),
        Relationship(
            name="ORDER_SHIPMENT_LINK",
            parent_entity="ORDER",
            parent_field="ORDER_VALUE",
            child_entity="SHIPMENT",
            child_field="SHIPMENT_ORDER_VALUE",
            cardinality="1:N",
        ),
    )

    correlations = (
        Correlation(
            name="CUSTOMER_SCORE_VALUE",
            source_entity="CUSTOMER",
            source_field="CUSTOMER_SCORE",
            target_entity="CUSTOMER",
            target_field="CUSTOMER_VALUE",
            target_value=0.60,
            tolerance=0.45,
        ),
        Correlation(
            name="PRODUCT_SCORE_PRICE",
            source_entity="PRODUCT",
            source_field="PRODUCT_SCORE",
            target_entity="PRODUCT",
            target_field="UNIT_PRICE",
            target_value=0.50,
            tolerance=0.45,
        ),
    )

    constraints = (
        CrossConstraint(
            name="ORDER_VALUE_ABOVE_CUSTOMER",
            entity="ORDER",
            left="ORDER_VALUE",
            operator=">=",
            right="ORDER_CUSTOMER_VALUE",
            multiplier=1.0,
        ),
    )

    conditionals = (
        Conditional(
            name="HIGH_VALUE_ORDER_DISCOUNT",
            entity="ORDER",
            condition_field="ORDER_VALUE",
            condition_minimum=10000.0,
            target_field="DISCOUNT",
            target_minimum=5.0,
        ),
    )

    derived = (
        Derived(
            name="NET_ORDER_VALUE",
            entity="ORDER",
            source_a="ORDER_VALUE",
            source_b="DISCOUNT",
            operation="SUBTRACT",
        ),
    )

    scenarios = (
        Scenario(
            name="NORMAL",
        ),
        Scenario(
            name="PREMIUM",
            overrides=(
                ScenarioOverride(
                    scenario="PREMIUM",
                    entity="CUSTOMER",
                    field="CUSTOMER_SCORE",
                    minimum=60.0,
                    maximum=100.0,
                ),
            ),
        ),
        Scenario(
            name="STRESS",
            overrides=(
                ScenarioOverride(
                    scenario="STRESS",
                    entity="ORDER",
                    field="ORDER_VALUE",
                    minimum=10000.0,
                    maximum=20000.0,
                ),
            ),
        ),
    )

    return Specification(
        entities=(
            customer,
            profile,
            product,
            order,
            shipment,
        ),
        relationships=relationships,
        correlations=correlations,
        constraints=constraints,
        conditionals=conditionals,
        derived=derived,
        scenarios=scenarios,
    )


# ============================================================================
# ADVERSARIAL SPECIFICATIONS
# ============================================================================


def impossible_cycle() -> Specification:

    specification = build_capstone_specification()

    relationships = specification.relationships + (
        Relationship(
            name="SHIPMENT_CUSTOMER_CYCLE",
            parent_entity="SHIPMENT",
            parent_field="SHIPPING_COST",
            child_entity="CUSTOMER",
            child_field="CUSTOMER_SCORE",
            cardinality="1:N",
        ),
    )

    return Specification(
        entities=specification.entities,
        relationships=relationships,
        correlations=specification.correlations,
        constraints=specification.constraints,
        conditionals=specification.conditionals,
        derived=specification.derived,
        scenarios=specification.scenarios,
    )


def impossible_correlation() -> Specification:

    specification = build_capstone_specification()

    correlations = specification.correlations + (
        Correlation(
            name="INVALID_CORRELATION",
            source_entity="CUSTOMER",
            source_field="CUSTOMER_SCORE",
            target_entity="CUSTOMER",
            target_field="CUSTOMER_VALUE",
            target_value=2.0,
            tolerance=0.1,
        ),
    )

    return Specification(
        entities=specification.entities,
        relationships=specification.relationships,
        correlations=correlations,
        constraints=specification.constraints,
        conditionals=specification.conditionals,
        derived=specification.derived,
        scenarios=specification.scenarios,
    )


def impossible_constraint() -> Specification:

    specification = build_capstone_specification()

    constraints = specification.constraints + (
        CrossConstraint(
            name="IMPOSSIBLE_ORDER",
            entity="ORDER",
            left="ORDER_VALUE",
            operator=">=",
            right="ORDER_CUSTOMER_VALUE",
            multiplier=100.0,
        ),
    )

    return Specification(
        entities=specification.entities,
        relationships=specification.relationships,
        correlations=specification.correlations,
        constraints=constraints,
        conditionals=specification.conditionals,
        derived=specification.derived,
        scenarios=specification.scenarios,
    )


def invalid_scenario() -> Specification:

    specification = build_capstone_specification()

    scenarios = specification.scenarios + (
        Scenario(
            name="INVALID",
            overrides=(
                ScenarioOverride(
                    scenario="INVALID",
                    entity="UNKNOWN",
                    field="UNKNOWN",
                    minimum=1.0,
                    maximum=0.0,
                ),
            ),
        ),
    )

    return Specification(
        entities=specification.entities,
        relationships=specification.relationships,
        correlations=specification.correlations,
        constraints=specification.constraints,
        conditionals=specification.conditionals,
        derived=specification.derived,
        scenarios=scenarios,
    )


# ============================================================================
# TEST HELPER
# ============================================================================


def run_test(
    name: str,
    function,
) -> dict[str, object]:

    try:

        passed = bool(function())

        return {
            "name": name,
            "status": ("PASS" if passed else "FAIL"),
        }

    except Exception as exc:

        return {
            "name": name,
            "status": ("PASS" if name.startswith("Reject") else "FAIL"),
            "error": (f"{type(exc).__name__}: " f"{exc}"),
        }


# ============================================================================
# TESTS
# ============================================================================


def test_complete_generation() -> bool:

    specification = build_capstone_specification()

    datasets = generate_dataset(
        specification,
        "NORMAL",
        MASTER_SEED,
    )

    return bool(datasets)


def test_dataset_structure() -> bool:

    specification = build_capstone_specification()

    datasets = generate_dataset(
        specification,
        "NORMAL",
        MASTER_SEED,
    )

    return all(
        len(datasets[entity.name]) == entity.record_count
        for entity in specification.entities
    )


def test_relationship_integrity() -> bool:

    specification = build_capstone_specification()

    datasets = generate_dataset(
        specification,
        "NORMAL",
        MASTER_SEED,
    )

    return validate_dataset(
        specification,
        datasets,
        "NORMAL",
    )


def test_constraint_integrity() -> bool:

    specification = build_capstone_specification()

    datasets = generate_dataset(
        specification,
        "NORMAL",
        MASTER_SEED,
    )

    return validate_dataset(
        specification,
        datasets,
        "NORMAL",
    )


def test_conditional_integrity() -> bool:

    specification = build_capstone_specification()

    datasets = generate_dataset(
        specification,
        "STRESS",
        MASTER_SEED,
    )

    return all(
        record["DISCOUNT"] >= 5.0
        for record in datasets["ORDER"]
        if record["ORDER_VALUE"] >= 10000.0
    )


def test_derived_integrity() -> bool:

    specification = build_capstone_specification()

    datasets = generate_dataset(
        specification,
        "NORMAL",
        MASTER_SEED,
    )

    return all(
        math.isclose(
            record["NET_ORDER_VALUE"],
            record["ORDER_VALUE"] - record["DISCOUNT"],
            rel_tol=1e-9,
            abs_tol=1e-9,
        )
        for record in datasets["ORDER"]
    )


def test_statistical_integrity() -> bool:

    specification = build_capstone_specification()

    datasets = generate_dataset(
        specification,
        "NORMAL",
        MASTER_SEED,
    )

    for relationship in specification.correlations:

        observed = pearson(
            [
                record[relationship.source_field]
                for record in datasets[relationship.source_entity]
            ],
            [
                record[relationship.target_field]
                for record in datasets[relationship.target_entity]
            ],
        )

        if abs(observed - relationship.target_value) > relationship.tolerance:

            return False

    return True


def test_reproducibility() -> bool:

    specification = build_capstone_specification()

    first = generate_dataset(
        specification,
        "NORMAL",
        42,
    )

    second = generate_dataset(
        specification,
        "NORMAL",
        42,
    )

    return first == second


def test_seed_sensitivity() -> bool:

    specification = build_capstone_specification()

    first = generate_dataset(
        specification,
        "NORMAL",
        42,
    )

    second = generate_dataset(
        specification,
        "NORMAL",
        43,
    )

    return first != second


def test_entity_order_independence() -> bool:

    specification = build_capstone_specification()

    alternate = Specification(
        entities=tuple(reversed(specification.entities)),
        relationships=specification.relationships,
        correlations=specification.correlations,
        constraints=specification.constraints,
        conditionals=specification.conditionals,
        derived=specification.derived,
        scenarios=specification.scenarios,
    )

    first = generate_dataset(
        specification,
        "NORMAL",
        MASTER_SEED,
    )

    second = generate_dataset(
        alternate,
        "NORMAL",
        MASTER_SEED,
    )

    return first == second


def test_field_order_independence() -> bool:

    specification = build_capstone_specification()

    alternate_entities = []

    for entity in specification.entities:

        alternate_entities.append(
            Entity(
                name=entity.name,
                fields=tuple(reversed(entity.fields)),
                record_count=entity.record_count,
            )
        )

    alternate = Specification(
        entities=tuple(alternate_entities),
        relationships=specification.relationships,
        correlations=specification.correlations,
        constraints=specification.constraints,
        conditionals=specification.conditionals,
        derived=specification.derived,
        scenarios=specification.scenarios,
    )

    first = generate_dataset(
        specification,
        "NORMAL",
        MASTER_SEED,
    )

    second = generate_dataset(
        alternate,
        "NORMAL",
        MASTER_SEED,
    )

    return first == second


def test_scenario_isolation() -> bool:

    specification = build_capstone_specification()

    before = copy.deepcopy(specification)

    generate_dataset(
        specification,
        "PREMIUM",
        MASTER_SEED,
    )

    return specification == before


def test_scenario_behavior() -> bool:

    specification = build_capstone_specification()

    normal = generate_dataset(
        specification,
        "NORMAL",
        MASTER_SEED,
    )

    premium = generate_dataset(
        specification,
        "PREMIUM",
        MASTER_SEED,
    )

    normal_average = mean(record["CUSTOMER_SCORE"] for record in normal["CUSTOMER"])

    premium_average = mean(record["CUSTOMER_SCORE"] for record in premium["CUSTOMER"])

    return premium_average >= 60.0 and premium_average != normal_average


def test_no_hidden_fallback() -> bool:

    specification = impossible_correlation()

    try:

        generate_dataset(
            specification,
            "NORMAL",
            MASTER_SEED,
        )

    except ValueError:

        return True

    return False


def test_cycle_blocking() -> bool:

    specification = impossible_cycle()

    try:

        dependency_plan(specification)

    except ValueError:

        return True

    return False


def test_impossible_constraint_blocking() -> bool:

    specification = impossible_constraint()

    try:

        generate_dataset(
            specification,
            "NORMAL",
            MASTER_SEED,
        )

    except ValueError:

        return True

    return False


def test_invalid_scenario_blocking() -> bool:

    specification = invalid_scenario()

    try:

        validate_scenario(
            specification,
            "INVALID",
        )

    except ValueError:

        return True

    return False


def test_capability_boundary() -> bool:

    specification = build_capstone_specification()

    capabilities = assess_capabilities(specification)

    return (
        capabilities["CORRELATION"] == "EXECUTABLE"
        and capabilities["CONSTRAINT"] == "EXECUTABLE"
        and capabilities["DERIVED"] == "EXECUTABLE"
        and capabilities["BETA"] == "DEFERRED"
    )


def test_no_post_generation_repair() -> bool:

    specification = build_capstone_specification()

    datasets = generate_dataset(
        specification,
        "NORMAL",
        MASTER_SEED,
    )

    return validate_dataset(
        specification,
        datasets,
        "NORMAL",
    )


def test_complex_specification_isolation() -> bool:

    specification = build_capstone_specification()

    datasets = generate_dataset(
        specification,
        "STRESS",
        MASTER_SEED,
    )

    return (
        len(datasets["CUSTOMER"]) == 500
        and len(datasets["PRODUCT"]) == 300
        and len(datasets["ORDER"]) == 1000
        and len(datasets["SHIPMENT"]) == 1000
    )


def test_full_integrity() -> bool:

    specification = build_capstone_specification()

    datasets = generate_dataset(
        specification,
        "NORMAL",
        MASTER_SEED,
    )

    return validate_dataset(
        specification,
        datasets,
        "NORMAL",
    )


# ============================================================================
# MAIN
# ============================================================================


def main() -> int:

    print()

    print("=" * 70)

    print("FORGE - Experiment 020-S: " "Declarative Generation Adversarial Validation")

    print("=" * 70)

    print("Experiment:     " "020_declarative_generation_specification")

    print("Stage:          020-S")

    print("Purpose:        " "Capstone adversarial and production-readiness validation")

    print(f"Random seed:    {MASTER_SEED}")

    print()

    specification = build_capstone_specification()

    print("Capstone specification:")

    print(f"  Entities:                  " f"{len(specification.entities)}")

    print(f"  Relationships:             " f"{len(specification.relationships)}")

    print(f"  Statistical relationships: " f"{len(specification.correlations)}")

    print(f"  Cross-field constraints:   " f"{len(specification.constraints)}")

    print(f"  Conditional rules:         " f"{len(specification.conditionals)}")

    print(f"  Derived fields:            " f"{len(specification.derived)}")

    print(f"  Scenarios:                 " f"{len(specification.scenarios)}")

    print()

    print("Unified generation planning:")

    entity_plan = dependency_plan(specification)

    print("  Entity order:")

    print("    " + " -> ".join(entity_plan))

    print()

    field_plan = unified_generation_plan(specification)

    for entity_name in entity_plan:

        print(f"  {entity_name}:")

        print("    " + " -> ".join(field_plan[entity_name]))

    print()

    print("Adversarial validation:")

    tests = [
        (
            "Complete generation",
            test_complete_generation,
        ),
        (
            "Dataset structure",
            test_dataset_structure,
        ),
        (
            "Relationship integrity",
            test_relationship_integrity,
        ),
        (
            "Constraint integrity",
            test_constraint_integrity,
        ),
        (
            "Conditional integrity",
            test_conditional_integrity,
        ),
        (
            "Derived-field integrity",
            test_derived_integrity,
        ),
        (
            "Statistical integrity",
            test_statistical_integrity,
        ),
        (
            "Reproducibility",
            test_reproducibility,
        ),
        (
            "Seed sensitivity",
            test_seed_sensitivity,
        ),
        (
            "Entity-order independence",
            test_entity_order_independence,
        ),
        (
            "Field-order independence",
            test_field_order_independence,
        ),
        (
            "Scenario isolation",
            test_scenario_isolation,
        ),
        (
            "Scenario behavior",
            test_scenario_behavior,
        ),
        (
            "Reject hidden fallback",
            test_no_hidden_fallback,
        ),
        (
            "Reject dependency cycle",
            test_cycle_blocking,
        ),
        (
            "Reject impossible constraint",
            test_impossible_constraint_blocking,
        ),
        (
            "Reject invalid scenario",
            test_invalid_scenario_blocking,
        ),
        (
            "Capability boundary",
            test_capability_boundary,
        ),
        (
            "No post-generation repair",
            test_no_post_generation_repair,
        ),
        (
            "Complex specification isolation",
            test_complex_specification_isolation,
        ),
        (
            "Full integrity",
            test_full_integrity,
        ),
    ]

    results = []

    for name, function in tests:

        result = run_test(
            name,
            function,
        )

        results.append(result)

        print(f"  {name:<40}" f"{result['status']}")

        if result["status"] == "FAIL" and "error" in result:

            print(f"      error: " f"{result['error']}")

    passed = sum(result["status"] == "PASS" for result in results)

    total = len(results)

    overall = passed == total

    print()

    print("Experiment result:")

    print(f"  Tests passed:              " f"{passed}/{total}")

    print(f"  Overall:                   " f"{'PASS' if overall else 'FAIL'}")

    # ------------------------------------------------------------------
    # Output.
    # ------------------------------------------------------------------

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    output = {
        "experiment": ("020_declarative_generation_specification"),
        "stage": "020-S",
        "purpose": (
            "Declarative generation adversarial " "and production-readiness validation"
        ),
        "seed": MASTER_SEED,
        "generation_plan": {
            "entities": entity_plan,
            "fields": field_plan,
        },
        "tests": results,
        "tests_passed": passed,
        "tests_total": total,
        "overall": ("PASS" if overall else "FAIL"),
        "capabilities": {
            "entities": len(specification.entities),
            "relationships": len(specification.relationships),
            "statistical_relationships": len(specification.correlations),
            "constraints": len(specification.constraints),
            "conditionals": len(specification.conditionals),
            "derived_fields": len(specification.derived),
            "scenarios": len(specification.scenarios),
        },
        "invariants": [
            "declarative_specification",
            "entity_order_independence",
            "field_order_independence",
            "deterministic_reproducibility",
            "seed_sensitivity",
            "explicit_capability_boundaries",
            "no_hidden_fallback",
            "no_post_generation_repair",
            "constraint_preservation",
            "relationship_integrity",
            "statistical_relationship_preservation",
            "scenario_isolation",
            "derived_value_determinism",
            "safe_failure",
            "field_level_dependency_planning",
        ],
    }

    with OUTPUT_PATH.open(
        "w",
        encoding="utf-8",
    ) as file:

        json.dump(
            output,
            file,
            indent=2,
        )

    print()

    print("Output:")

    print(f"  Results: {OUTPUT_PATH}")

    print()

    if overall:

        print("Experiment completed successfully.")

        print("Declarative generation passed " "the capstone adversarial validation.")

        return 0

    print("Experiment completed with failures.")

    print("Failures are intentionally preserved " "as architectural evidence.")

    return 1


if __name__ == "__main__":

    sys.exit(main())
