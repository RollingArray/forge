"""
FORGE - Experiment 020-O: Declarative Scenario Generation
===========================================================

Stage:
    020-O

Purpose:
    Validate scenario-driven synthetic data generation.

Research question
-----------------
Can a single declarative FORGE specification produce controlled
dataset variants through scenario parameters, overrides, constraints,
and distributions without changing the underlying entity model?

Experiment focus
----------------
This experiment validates:

    SCENARIO
    SCENARIO_PARAMETER
    SCENARIO_OVERRIDE
    SCENARIO_CONSTRAINT
    SCENARIO_DISTRIBUTION

Core principle
--------------
A scenario changes generation behavior, not the semantic definition
of the underlying data model.

For example:

    NORMAL
        CUSTOMER_TYPE distribution:
            STANDARD 80%
            PREMIUM  20%

    PREMIUM_HEAVY
        CUSTOMER_TYPE distribution:
            STANDARD 40%
            PREMIUM  60%

The entity and field definitions remain unchanged.

Safety principles
-----------------
Scenario behavior must be:

    - Explicit
    - Deterministic
    - Reproducible
    - Validated
    - Isolated from the base specification
    - Free from implicit fallback

An invalid scenario must be rejected rather than silently falling
back to NORMAL.

Included
--------
    - Base scenario
    - Scenario parameters
    - Scenario overrides
    - Scenario-specific distributions
    - Scenario-specific constraints
    - Scenario composition
    - Scenario validation
    - Determinism
    - Seed sensitivity
    - Scenario isolation
    - Entity-order independence
    - Field-order independence

Excluded
--------
    - Statistical correlation
    - Empirical distributions
    - External data sources
    - LLM scenario interpretation
    - Production persistence
"""

from __future__ import annotations

import copy
import hashlib
import json
import random
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

# ============================================================================
# PATHS
# ============================================================================

EXPERIMENT_DIR = Path(__file__).resolve().parent

OUTPUT_DIR = EXPERIMENT_DIR / "output"

OUTPUT_PATH = OUTPUT_DIR / "scenario_generation_results.json"

MASTER_SEED = 42


# ============================================================================
# MODELS
# ============================================================================


@dataclass(frozen=True)
class FieldSpecification:
    name: str
    field_type: str
    strategy: str
    parameters: dict[str, Any]


@dataclass(frozen=True)
class EntitySpecification:
    name: str
    record_count: int
    fields: tuple[FieldSpecification, ...]


@dataclass(frozen=True)
class ScenarioParameter:
    name: str
    default: Any
    allowed_values: tuple[Any, ...] | None = None
    minimum: float | None = None
    maximum: float | None = None


@dataclass(frozen=True)
class ScenarioOverride:
    entity: str
    field: str
    parameter: str
    value: Any


@dataclass(frozen=True)
class ScenarioConstraint:
    entity: str
    field: str
    operator: str
    value: Any


@dataclass(frozen=True)
class ScenarioDistribution:
    entity: str
    field: str
    values: tuple[Any, ...]
    weights: tuple[float, ...]


@dataclass(frozen=True)
class Scenario:
    name: str
    parameters: tuple[ScenarioParameter, ...]
    overrides: tuple[ScenarioOverride, ...]
    constraints: tuple[ScenarioConstraint, ...]
    distributions: tuple[ScenarioDistribution, ...]


# ============================================================================
# DETERMINISTIC SEEDS
# ============================================================================


def stable_seed(
    seed: int,
    scenario: str,
    entity: str,
    field: str,
) -> int:

    material = (f"{seed}:" f"{scenario}:" f"{entity}:" f"{field}").encode("utf-8")

    digest = hashlib.sha256(material).digest()

    return int.from_bytes(
        digest[:8],
        byteorder="big",
        signed=False,
    )


def field_rng(
    seed: int,
    scenario: str,
    entity: str,
    field: str,
) -> random.Random:

    return random.Random(
        stable_seed(
            seed,
            scenario,
            entity,
            field,
        )
    )


# ============================================================================
# BASE SPECIFICATION
# ============================================================================


def build_entities(
    reverse_entities: bool = False,
    reverse_fields: bool = False,
) -> dict[str, EntitySpecification]:

    customer = EntitySpecification(
        name="CUSTOMER",
        record_count=100,
        fields=(
            FieldSpecification(
                name="CUSTOMER_ID",
                field_type="IDENTIFIER",
                strategy="SEQUENTIAL",
                parameters={
                    "prefix": "CUS-",
                    "start": 1,
                },
            ),
            FieldSpecification(
                name="CUSTOMER_TYPE",
                field_type="CATEGORICAL",
                strategy="RANDOM",
                parameters={
                    "values": (
                        "STANDARD",
                        "PREMIUM",
                    ),
                },
            ),
            FieldSpecification(
                name="COUNTRY",
                field_type="CATEGORICAL",
                strategy="RANDOM",
                parameters={
                    "values": (
                        "US",
                        "IN",
                        "DE",
                    ),
                },
            ),
            FieldSpecification(
                name="CREDIT_LIMIT",
                field_type="DECIMAL",
                strategy="RANDOM",
                parameters={
                    "minimum": 1000.0,
                    "maximum": 10000.0,
                },
            ),
        ),
    )

    order = EntitySpecification(
        name="ORDER",
        record_count=200,
        fields=(
            FieldSpecification(
                name="ORDER_ID",
                field_type="IDENTIFIER",
                strategy="SEQUENTIAL",
                parameters={
                    "prefix": "ORD-",
                    "start": 1,
                },
            ),
            FieldSpecification(
                name="ORDER_VALUE",
                field_type="DECIMAL",
                strategy="RANDOM",
                parameters={
                    "minimum": 100.0,
                    "maximum": 5000.0,
                },
            ),
            FieldSpecification(
                name="IS_PRIORITY",
                field_type="BOOLEAN",
                strategy="RANDOM",
                parameters={
                    "probability_true": 0.20,
                },
            ),
        ),
    )

    entities = [
        customer,
        order,
    ]

    if reverse_entities:
        entities.reverse()

    if reverse_fields:

        entities = [
            EntitySpecification(
                name=entity.name,
                record_count=entity.record_count,
                fields=tuple(reversed(entity.fields)),
            )
            for entity in entities
        ]

    return {entity.name: entity for entity in entities}


# ============================================================================
# SCENARIOS
# ============================================================================


def build_scenarios() -> dict[str, Scenario]:

    normal = Scenario(
        name="NORMAL",
        parameters=(
            ScenarioParameter(
                name="premium_rate",
                default=0.20,
                minimum=0.0,
                maximum=1.0,
            ),
            ScenarioParameter(
                name="priority_rate",
                default=0.20,
                minimum=0.0,
                maximum=1.0,
            ),
        ),
        overrides=(),
        constraints=(),
        distributions=(
            ScenarioDistribution(
                entity="CUSTOMER",
                field="CUSTOMER_TYPE",
                values=(
                    "STANDARD",
                    "PREMIUM",
                ),
                weights=(
                    0.80,
                    0.20,
                ),
            ),
        ),
    )

    premium_heavy = Scenario(
        name="PREMIUM_HEAVY",
        parameters=(
            ScenarioParameter(
                name="premium_rate",
                default=0.60,
                minimum=0.0,
                maximum=1.0,
            ),
            ScenarioParameter(
                name="priority_rate",
                default=0.35,
                minimum=0.0,
                maximum=1.0,
            ),
        ),
        overrides=(
            ScenarioOverride(
                entity="CUSTOMER",
                field="CREDIT_LIMIT",
                parameter="minimum",
                value=5000.0,
            ),
        ),
        constraints=(
            ScenarioConstraint(
                entity="CUSTOMER",
                field="CREDIT_LIMIT",
                operator="GREATER_OR_EQUAL",
                value=5000.0,
            ),
        ),
        distributions=(
            ScenarioDistribution(
                entity="CUSTOMER",
                field="CUSTOMER_TYPE",
                values=(
                    "STANDARD",
                    "PREMIUM",
                ),
                weights=(
                    0.40,
                    0.60,
                ),
            ),
        ),
    )

    stress = Scenario(
        name="STRESS",
        parameters=(
            ScenarioParameter(
                name="premium_rate",
                default=0.50,
                minimum=0.0,
                maximum=1.0,
            ),
            ScenarioParameter(
                name="priority_rate",
                default=0.70,
                minimum=0.0,
                maximum=1.0,
            ),
        ),
        overrides=(
            ScenarioOverride(
                entity="ORDER",
                field="ORDER_VALUE",
                parameter="minimum",
                value=3000.0,
            ),
        ),
        constraints=(
            ScenarioConstraint(
                entity="ORDER",
                field="ORDER_VALUE",
                operator="GREATER_OR_EQUAL",
                value=3000.0,
            ),
        ),
        distributions=(
            ScenarioDistribution(
                entity="CUSTOMER",
                field="CUSTOMER_TYPE",
                values=(
                    "STANDARD",
                    "PREMIUM",
                ),
                weights=(
                    0.50,
                    0.50,
                ),
            ),
        ),
    )

    return {
        scenario.name: scenario
        for scenario in (
            normal,
            premium_heavy,
            stress,
        )
    }


# ============================================================================
# SCENARIO VALIDATION
# ============================================================================


def validate_scenario(
    scenario: Scenario,
    entities: dict[str, EntitySpecification],
) -> None:

    entity_names = set(entities.keys())

    fields_by_entity = {
        entity.name: {field.name for field in entity.fields}
        for entity in entities.values()
    }

    # ------------------------------------------------------------------
    # Scenario parameter validation
    # ------------------------------------------------------------------

    for parameter in scenario.parameters:

        if (
            parameter.minimum is not None
            and parameter.maximum is not None
            and parameter.minimum > parameter.maximum
        ):
            raise ValueError(f"Invalid parameter range: " f"{parameter.name}")

        if parameter.minimum is not None and parameter.default < parameter.minimum:
            raise ValueError(
                f"Default value for " f"{parameter.name} is below minimum."
            )

        if parameter.maximum is not None and parameter.default > parameter.maximum:
            raise ValueError(
                f"Default value for " f"{parameter.name} is above maximum."
            )

        if (
            parameter.allowed_values
            and parameter.default not in parameter.allowed_values
        ):
            raise ValueError(f"Default value for " f"{parameter.name} is not allowed.")

    # ------------------------------------------------------------------
    # Scenario override validation
    # ------------------------------------------------------------------

    for override in scenario.overrides:

        if override.entity not in entity_names:
            raise ValueError(f"Unknown scenario entity: " f"{override.entity}")

        if override.field not in fields_by_entity[override.entity]:
            raise ValueError(
                f"Unknown scenario field: " f"{override.entity}." f"{override.field}"
            )

    # ------------------------------------------------------------------
    # Scenario constraint validation
    # ------------------------------------------------------------------

    for constraint in scenario.constraints:

        if constraint.entity not in entity_names:
            raise ValueError(f"Unknown constraint entity: " f"{constraint.entity}")

        if constraint.field not in fields_by_entity[constraint.entity]:
            raise ValueError(
                f"Unknown constraint field: "
                f"{constraint.entity}."
                f"{constraint.field}"
            )

    # ------------------------------------------------------------------
    # Scenario distribution validation
    # ------------------------------------------------------------------

    for distribution in scenario.distributions:

        if distribution.entity not in entity_names:
            raise ValueError(f"Unknown distribution entity: " f"{distribution.entity}")

        if distribution.field not in fields_by_entity[distribution.entity]:
            raise ValueError(
                f"Unknown distribution field: "
                f"{distribution.entity}."
                f"{distribution.field}"
            )

        if len(distribution.values) != len(distribution.weights):
            raise ValueError(
                "Distribution values and " "weights must have equal length."
            )

        if not distribution.weights:
            raise ValueError("Distribution must contain " "at least one value.")

        if any(weight < 0 for weight in distribution.weights):
            raise ValueError("Distribution weights cannot " "be negative.")

        if sum(distribution.weights) <= 0:
            raise ValueError("Distribution weights must " "sum to a positive value.")


# ============================================================================
# SCENARIO MATERIALIZATION
# ============================================================================


def materialize_parameters(
    scenario: Scenario,
) -> dict[str, Any]:

    return {parameter.name: parameter.default for parameter in scenario.parameters}


def apply_overrides(
    field: FieldSpecification,
    scenario: Scenario,
) -> FieldSpecification:

    parameters = copy.deepcopy(field.parameters)

    for override in scenario.overrides:

        if override.field == field.name:

            parameters[override.parameter] = override.value

    return FieldSpecification(
        name=field.name,
        field_type=field.field_type,
        strategy=field.strategy,
        parameters=parameters,
    )


def find_distribution(
    entity: str,
    field: str,
    scenario: Scenario,
) -> ScenarioDistribution | None:

    matches = [
        distribution
        for distribution in scenario.distributions
        if (distribution.entity == entity and distribution.field == field)
    ]

    if len(matches) > 1:

        raise ValueError(f"Multiple distributions " f"defined for " f"{entity}.{field}")

    return matches[0] if matches else None


# ============================================================================
# FIELD GENERATION
# ============================================================================


def generate_field(
    entity: str,
    field: FieldSpecification,
    scenario: Scenario,
    seed: int,
) -> Any:

    rng = field_rng(
        seed,
        scenario.name,
        entity,
        field.name,
    )

    distribution = find_distribution(
        entity,
        field.name,
        scenario,
    )

    if field.strategy == "SEQUENTIAL":

        start = field.parameters.get(
            "start",
            1,
        )

        prefix = field.parameters.get(
            "prefix",
            "",
        )

        # The record index is injected separately.
        return (
            prefix,
            start,
        )

    if distribution is not None:

        return rng.choices(
            distribution.values,
            weights=distribution.weights,
            k=1,
        )[0]

    if field.strategy == "RANDOM":

        if field.field_type == "DECIMAL":

            return round(
                rng.uniform(
                    field.parameters["minimum"],
                    field.parameters["maximum"],
                ),
                2,
            )

        if field.field_type == "BOOLEAN":

            return rng.random() < field.parameters.get(
                "probability_true",
                0.5,
            )

        if field.field_type == "CATEGORICAL":

            values = field.parameters["values"]

            return rng.choice(values)

    raise ValueError(f"Unsupported field generation: " f"{entity}.{field.name}")


def build_scenario_distribution_values(
    entity: EntitySpecification,
    field: FieldSpecification,
    scenario: Scenario,
    seed: int,
) -> list[Any] | None:
    """
    Materialize a scenario distribution for the complete field population.

    The distribution is treated as a population-level property rather than
    an independent random choice for every record.

    The resulting values are deterministically shuffled using a field-specific
    scenario seed.
    """

    distribution = find_distribution(
        entity.name,
        field.name,
        scenario,
    )

    if distribution is None:
        return None

    record_count = entity.record_count

    total_weight = sum(distribution.weights)

    if total_weight <= 0:
        raise ValueError(
            f"Scenario distribution for "
            f"{entity.name}.{field.name} "
            f"has no positive weight."
        )

    # --------------------------------------------------------------
    # Calculate population allocation.
    #
    # Largest-remainder allocation is used so that:
    #
    #   STANDARD = 40%
    #   PREMIUM  = 60%
    #
    # over 100 records becomes exactly:
    #
    #   STANDARD = 40
    #   PREMIUM  = 60
    #
    # while still supporting arbitrary record counts.
    # --------------------------------------------------------------

    exact_counts = [
        (weight / total_weight) * record_count for weight in distribution.weights
    ]

    base_counts = [int(value) for value in exact_counts]

    remaining = record_count - sum(base_counts)

    remainders = sorted(
        range(len(exact_counts)),
        key=lambda index: (exact_counts[index] - base_counts[index]),
        reverse=True,
    )

    for index in remainders[:remaining]:
        base_counts[index] += 1

    # --------------------------------------------------------------
    # Materialize the population.
    # --------------------------------------------------------------

    values: list[Any] = []

    for value, count in zip(
        distribution.values,
        base_counts,
    ):
        values.extend([value] * count)

    if len(values) != record_count:
        raise RuntimeError(
            f"Scenario distribution allocation "
            f"failed for {entity.name}.{field.name}: "
            f"expected {record_count}, "
            f"generated {len(values)}."
        )

    # --------------------------------------------------------------
    # Deterministically shuffle the population.
    #
    # The allocation remains exact, while the assignment to records
    # remains seed-sensitive.
    # --------------------------------------------------------------

    rng = field_rng(
        seed,
        scenario.name,
        entity.name,
        field.name,
    )

    rng.shuffle(values)

    return values


def generate_dataset(
    entities: dict[str, EntitySpecification],
    scenario: Scenario,
    seed: int = MASTER_SEED,
) -> dict[
    str,
    list[dict[str, Any]],
]:

    validate_scenario(
        scenario,
        entities,
    )

    datasets = {}

    for entity_name in sorted(entities.keys()):

        entity = entities[entity_name]

        records = []

        # ----------------------------------------------------------
        # Materialize scenario distributions once per field.
        # ----------------------------------------------------------

        scenario_distributions: dict[
            str,
            list[Any],
        ] = {}

        for field in entity.fields:

            values = build_scenario_distribution_values(
                entity,
                field,
                scenario,
                seed,
            )

            if values is not None:
                scenario_distributions[field.name] = values

        # ----------------------------------------------------------
        # Generate records.
        # ----------------------------------------------------------

        for index in range(entity.record_count):

            record = {}

            for field in entity.fields:

                effective_field = apply_overrides(
                    field,
                    scenario,
                )

                # --------------------------------------------------
                # Scenario distribution has population-level
                # semantics and therefore takes precedence over the
                # normal per-record random generation path.
                # --------------------------------------------------

                if field.name in scenario_distributions:

                    value = scenario_distributions[field.name][index]

                else:

                    value = generate_field(
                        entity_name,
                        effective_field,
                        scenario,
                        seed,
                    )

                # --------------------------------------------------
                # Sequential generation
                # --------------------------------------------------

                if (
                    isinstance(
                        value,
                        tuple,
                    )
                    and effective_field.strategy == "SEQUENTIAL"
                ):

                    prefix, start = value

                    value = f"{prefix}" f"{start + index}"

                record[field.name] = value

            records.append(record)

        datasets[entity_name] = records

    validate_constraints(
        datasets,
        scenario,
    )

    return datasets


# ============================================================================
# CONSTRAINT VALIDATION
# ============================================================================


def validate_constraints(
    datasets: dict[
        str,
        list[dict[str, Any]],
    ],
    scenario: Scenario,
) -> None:

    for constraint in scenario.constraints:

        records = datasets[constraint.entity]

        for index, record in enumerate(records):

            value = record[constraint.field]

            if constraint.operator == "GREATER_OR_EQUAL":

                valid = value >= constraint.value

            elif constraint.operator == "EQUALS":

                valid = value == constraint.value

            elif constraint.operator == "LESS_OR_EQUAL":

                valid = value <= constraint.value

            else:

                raise ValueError(
                    "Unsupported scenario "
                    "constraint operator: "
                    f"{constraint.operator}"
                )

            if not valid:

                raise ValueError(
                    f"Scenario constraint "
                    f"failed for "
                    f"{constraint.entity}."
                    f"{constraint.field} "
                    f"record {index}"
                )


# ============================================================================
# SCENARIO METRICS
# ============================================================================


def summarize_dataset(
    datasets: dict[
        str,
        list[dict[str, Any]],
    ],
) -> dict[str, Any]:

    customer_records = datasets["CUSTOMER"]

    premium_count = sum(
        record["CUSTOMER_TYPE"] == "PREMIUM" for record in customer_records
    )

    premium_rate = premium_count / len(customer_records)

    order_records = datasets["ORDER"]

    high_value_count = sum(record["ORDER_VALUE"] >= 3000 for record in order_records)

    high_value_rate = high_value_count / len(order_records)

    return {
        "customer_count": len(customer_records),
        "premium_count": premium_count,
        "premium_rate": premium_rate,
        "order_count": len(order_records),
        "orders_at_or_above_3000": high_value_count,
        "orders_at_or_above_3000_rate": high_value_rate,
    }


# ============================================================================
# TEST HELPERS
# ============================================================================


def run_test(
    name: str,
    function,
) -> dict[str, Any]:

    try:

        passed = bool(function())

        return {
            "name": name,
            "status": ("PASS" if passed else "FAIL"),
        }

    except Exception as exc:

        return {
            "name": name,
            "status": "FAIL",
            "error": (f"{type(exc).__name__}: " f"{exc}"),
        }


# ============================================================================
# TESTS
# ============================================================================


def test_base_scenario() -> bool:

    entities = build_entities()

    scenarios = build_scenarios()

    dataset = generate_dataset(
        entities,
        scenarios["NORMAL"],
    )

    return len(dataset["CUSTOMER"]) == 100 and len(dataset["ORDER"]) == 200


def test_scenario_parameter_behavior() -> bool:

    scenarios = build_scenarios()

    normal = materialize_parameters(scenarios["NORMAL"])

    premium_heavy = materialize_parameters(scenarios["PREMIUM_HEAVY"])

    return normal["premium_rate"] != premium_heavy["premium_rate"]


def test_distribution_override() -> bool:

    entities = build_entities()

    scenarios = build_scenarios()

    normal = generate_dataset(
        entities,
        scenarios["NORMAL"],
    )

    premium_heavy = generate_dataset(
        entities,
        scenarios["PREMIUM_HEAVY"],
    )

    normal_rate = summarize_dataset(normal)["premium_rate"]

    premium_heavy_rate = summarize_dataset(premium_heavy)["premium_rate"]

    return premium_heavy_rate > normal_rate


def test_parameter_override() -> bool:

    entities = build_entities()

    scenarios = build_scenarios()

    dataset = generate_dataset(
        entities,
        scenarios["PREMIUM_HEAVY"],
    )

    return all(record["CREDIT_LIMIT"] >= 5000 for record in dataset["CUSTOMER"])


def test_scenario_constraint() -> bool:

    entities = build_entities()

    scenarios = build_scenarios()

    dataset = generate_dataset(
        entities,
        scenarios["STRESS"],
    )

    return all(record["ORDER_VALUE"] >= 3000 for record in dataset["ORDER"])


def test_scenario_isolation() -> bool:

    entities = build_entities()

    scenarios = build_scenarios()

    normal = generate_dataset(
        entities,
        scenarios["NORMAL"],
    )

    premium_heavy = generate_dataset(
        entities,
        scenarios["PREMIUM_HEAVY"],
    )

    normal_again = generate_dataset(
        entities,
        scenarios["NORMAL"],
    )

    return normal == normal_again and normal != premium_heavy


def test_reproducibility() -> bool:

    entities = build_entities()

    scenarios = build_scenarios()

    first = generate_dataset(
        entities,
        scenarios["STRESS"],
        seed=42,
    )

    second = generate_dataset(
        entities,
        scenarios["STRESS"],
        seed=42,
    )

    return first == second


def test_seed_sensitivity() -> bool:

    entities = build_entities()

    scenarios = build_scenarios()

    first = generate_dataset(
        entities,
        scenarios["STRESS"],
        seed=42,
    )

    second = generate_dataset(
        entities,
        scenarios["STRESS"],
        seed=43,
    )

    return first != second


def test_entity_order_independence() -> bool:

    first_entities = build_entities(
        reverse_entities=False,
    )

    second_entities = build_entities(
        reverse_entities=True,
    )

    scenarios = build_scenarios()

    first = generate_dataset(
        first_entities,
        scenarios["PREMIUM_HEAVY"],
    )

    second = generate_dataset(
        second_entities,
        scenarios["PREMIUM_HEAVY"],
    )

    return first == second


def test_field_order_independence() -> bool:

    first_entities = build_entities(
        reverse_fields=False,
    )

    second_entities = build_entities(
        reverse_fields=True,
    )

    scenarios = build_scenarios()

    first = generate_dataset(
        first_entities,
        scenarios["PREMIUM_HEAVY"],
    )

    second = generate_dataset(
        second_entities,
        scenarios["PREMIUM_HEAVY"],
    )

    return first == second


def test_invalid_scenario_is_blocked() -> bool:

    entities = build_entities()

    invalid = Scenario(
        name="INVALID",
        parameters=(),
        overrides=(
            ScenarioOverride(
                entity="DOES_NOT_EXIST",
                field="CUSTOMER_TYPE",
                parameter="minimum",
                value=1,
            ),
        ),
        constraints=(),
        distributions=(),
    )

    try:

        generate_dataset(
            entities,
            invalid,
        )

    except ValueError:

        return True

    return False


def test_invalid_distribution_is_blocked() -> bool:

    entities = build_entities()

    invalid = Scenario(
        name="INVALID_DISTRIBUTION",
        parameters=(),
        overrides=(),
        constraints=(),
        distributions=(
            ScenarioDistribution(
                entity="CUSTOMER",
                field="CUSTOMER_TYPE",
                values=(
                    "STANDARD",
                    "PREMIUM",
                ),
                weights=(
                    -1.0,
                    1.0,
                ),
            ),
        ),
    )

    try:

        generate_dataset(
            entities,
            invalid,
        )

    except ValueError:

        return True

    return False


def test_no_base_spec_mutation() -> bool:

    entities = build_entities()

    original = copy.deepcopy(entities)

    scenarios = build_scenarios()

    generate_dataset(
        entities,
        scenarios["PREMIUM_HEAVY"],
    )

    return entities == original


def test_scenario_parameter_validation() -> bool:

    entities = build_entities()

    invalid = Scenario(
        name="INVALID_PARAMETER",
        parameters=(
            ScenarioParameter(
                name="bad_rate",
                default=2.0,
                minimum=0.0,
                maximum=1.0,
            ),
        ),
        overrides=(),
        constraints=(),
        distributions=(),
    )

    try:

        generate_dataset(
            entities,
            invalid,
        )

    except ValueError:

        return True

    return False


# ============================================================================
# MAIN
# ============================================================================


def main() -> int:

    print()

    print("=" * 70)

    print("FORGE - Experiment 020-O: " "Declarative Scenario Generation")

    print("=" * 70)

    print("Experiment:     " "020_declarative_generation_specification")

    print("Stage:          020-O")

    print("Purpose:        " "Scenario-driven synthetic data generation")

    print(f"Random seed:    {MASTER_SEED}")

    print()

    print("Scenario model:")

    print("  Base Specification")

    print("        ↓")

    print("  Scenario Parameters")

    print("        ↓")

    print("  Scenario Overrides")

    print("        ↓")

    print("  Scenario Distribution")

    print("        ↓")

    print("  Scenario Constraints")

    print("        ↓")

    print("  Generated Dataset")

    print()

    scenarios = build_scenarios()

    print("Available scenarios:")

    for scenario in scenarios:

        print(f"  {scenario}")

    print()

    tests = [
        (
            "Base scenario",
            test_base_scenario,
        ),
        (
            "Scenario parameter behavior",
            test_scenario_parameter_behavior,
        ),
        (
            "Scenario distribution override",
            test_distribution_override,
        ),
        (
            "Scenario parameter override",
            test_parameter_override,
        ),
        (
            "Scenario constraint",
            test_scenario_constraint,
        ),
        (
            "Scenario isolation",
            test_scenario_isolation,
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
            "Invalid scenario blocking",
            test_invalid_scenario_is_blocked,
        ),
        (
            "Invalid distribution blocking",
            test_invalid_distribution_is_blocked,
        ),
        (
            "Base specification immutability",
            test_no_base_spec_mutation,
        ),
        (
            "Scenario parameter validation",
            test_scenario_parameter_validation,
        ),
    ]

    print("Scenario generation validation:")

    results = []

    for name, function in tests:

        result = run_test(
            name,
            function,
        )

        results.append(result)

        print(f"  " f"{name:<40}" f"{result['status']}")

    passed = sum(result["status"] == "PASS" for result in results)

    total = len(results)

    overall = passed == total

    print()

    print("Scenario comparison:")

    entities = build_entities()

    normal_dataset = generate_dataset(
        entities,
        scenarios["NORMAL"],
    )

    premium_dataset = generate_dataset(
        entities,
        scenarios["PREMIUM_HEAVY"],
    )

    stress_dataset = generate_dataset(
        entities,
        scenarios["STRESS"],
    )

    normal_summary = summarize_dataset(normal_dataset)

    premium_summary = summarize_dataset(premium_dataset)

    stress_summary = summarize_dataset(stress_dataset)

    print("  NORMAL:")

    print(f"    Premium rate: " f"{normal_summary['premium_rate']:.2%}")

    print("  PREMIUM_HEAVY:")

    print(f"    Premium rate: " f"{premium_summary['premium_rate']:.2%}")

    print("  STRESS:")

    print(
        f"    Orders >= 3000: " f"{stress_summary['orders_at_or_above_3000_rate']:.2%}"
    )

    print()

    print("Experiment result:")

    print(f"  Base scenario:             " f"{results[0]['status']}")

    print(f"  Parameters:                " f"{results[1]['status']}")

    print(f"  Distributions:             " f"{results[2]['status']}")

    print(f"  Overrides:                 " f"{results[3]['status']}")

    print(f"  Constraints:               " f"{results[4]['status']}")

    print(f"  Scenario isolation:        " f"{results[5]['status']}")

    print(f"  Reproducibility:           " f"{results[6]['status']}")

    print(f"  Seed sensitivity:          " f"{results[7]['status']}")

    print(f"  Entity-order independence: " f"{results[8]['status']}")

    print(f"  Field-order independence:  " f"{results[9]['status']}")

    configuration_safety = (
        "PASS" if all(result["status"] == "PASS" for result in results[10:]) else "FAIL"
    )

    print(f"  Configuration safety:      " f"{configuration_safety}")

    print()

    print(f"  Tests passed:              " f"{passed}/{total}")

    print(f"  Overall:                   " f"{'PASS' if overall else 'FAIL'}")

    # ------------------------------------------------------------------
    # Representative output
    # ------------------------------------------------------------------

    representative = {
        "NORMAL": normal_summary,
        "PREMIUM_HEAVY": premium_summary,
        "STRESS": stress_summary,
    }

    # ------------------------------------------------------------------
    # Persist
    # ------------------------------------------------------------------

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    output = {
        "experiment": ("020_declarative_generation_specification"),
        "stage": "020-O",
        "purpose": ("Declarative scenario generation"),
        "seed": MASTER_SEED,
        "scenarios": list(scenarios.keys()),
        "tests": results,
        "tests_passed": passed,
        "tests_total": total,
        "scenario_summaries": representative,
        "architectural_conclusion": (
            "FORGE can generate controlled "
            "scenario-specific datasets from a "
            "shared declarative specification."
            if overall
            else "Scenario generation still has " "unresolved execution boundaries."
        ),
        "overall": ("PASS" if overall else "FAIL"),
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

        print("Scenario-driven generation is " "experimentally validated.")

        return 0

    print("Experiment completed with failures.")

    return 1


if __name__ == "__main__":

    sys.exit(main())
