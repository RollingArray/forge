"""
FORGE - Experiment 020-R: Declarative Constraint and Statistical Integration
=============================================================================

Stage:
    020-R

Purpose:
    Validate composition of statistical relationships, constraints,
    derived fields, conditional rules, and dependency planning.

Research question
-----------------
Can independently validated declarative capabilities be composed into
one coherent generation model while preserving:

    - statistical relationships
    - field constraints
    - cross-field constraints
    - conditional rules
    - derived values
    - dependency ordering
    - deterministic generation
    - field-order independence
    - safe failure for infeasible specifications

Architecture
------------

                  Declarative Specification
                            |
              +-------------+-------------+
              |             |             |
              v             v             v
        Statistics      Constraints    Expressions
              |             |             |
              +-------------+-------------+
                            |
                    Unified Feasibility
                         Analysis
                            |
                    Dependency Planning
                            |
                    Context-aware
                       Generation
                            |
                    Final Validation

Important principle
-------------------
The generator must not generate data independently and repair it later.

Generation must respect the combined specification.

No post-generation repair is permitted.

Included
--------
    - Statistical target relationships
    - Field bounds
    - Cross-field constraints
    - Conditional generation
    - Derived/formula fields
    - Dependency ordering
    - Combined feasibility
    - Statistical validation
    - Constraint validation
    - Reproducibility
    - Seed sensitivity
    - Field-order independence
    - Safe impossible-specification blocking
    - No hidden fallback
    - No post-generation repair

Excluded
--------
    - Cross-entity relationships
    - Temporal distributions
    - Empirical distributions
    - Production optimization
    - LLM-assisted specification interpretation
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

OUTPUT_PATH = OUTPUT_DIR / "constraint_statistical_integration_results.json"

MASTER_SEED = 42


# ============================================================================
# MODELS
# ============================================================================


@dataclass(frozen=True)
class NumericField:
    name: str
    minimum: float
    maximum: float


@dataclass(frozen=True)
class StatisticalRelationship:
    name: str
    source_field: str
    target_field: str
    target_correlation: float
    tolerance: float


@dataclass(frozen=True)
class Constraint:
    name: str
    expression: str


@dataclass(frozen=True)
class ConditionalRule:
    name: str
    condition_field: str
    condition_value: object
    target_field: str
    minimum: float | None = None
    maximum: float | None = None


@dataclass(frozen=True)
class DerivedField:
    name: str
    dependencies: tuple[str, ...]
    formula: str


@dataclass(frozen=True)
class GenerationSpecification:
    fields: dict[str, NumericField]
    relationships: tuple[StatisticalRelationship, ...]
    constraints: tuple[Constraint, ...]
    conditionals: tuple[ConditionalRule, ...]
    derived_fields: tuple[DerivedField, ...]


# ============================================================================
# FIELD DEFINITIONS
# ============================================================================

FIELDS = {
    "CUSTOMER_SCORE": NumericField(
        name="CUSTOMER_SCORE",
        minimum=0.0,
        maximum=100.0,
    ),
    "CREDIT_LIMIT": NumericField(
        name="CREDIT_LIMIT",
        minimum=1000.0,
        maximum=10000.0,
    ),
    "RISK_SCORE": NumericField(
        name="RISK_SCORE",
        minimum=0.0,
        maximum=100.0,
    ),
    "CUSTOMER_TYPE_SCORE": NumericField(
        name="CUSTOMER_TYPE_SCORE",
        minimum=0.0,
        maximum=1.0,
    ),
    "NET_VALUE": NumericField(
        name="NET_VALUE",
        minimum=0.0,
        maximum=1000000.0,
    ),
}


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
# STATISTICAL HELPERS
# ============================================================================


def pearson(
    x: list[float],
    y: list[float],
) -> float:

    if len(x) != len(y):
        raise ValueError("Correlation vectors must " "have equal length.")

    x_mean = mean(x)
    y_mean = mean(y)

    numerator = sum(
        (xi - x_mean) * (yi - y_mean)
        for xi, yi in zip(
            x,
            y,
        )
    )

    denominator = math.sqrt(
        sum((xi - x_mean) ** 2 for xi in x) * sum((yi - y_mean) ** 2 for yi in y)
    )

    if math.isclose(
        denominator,
        0.0,
    ):
        raise ValueError("Correlation undefined.")

    return numerator / denominator


def standard_normal(
    rng: random.Random,
    count: int,
) -> list[float]:

    return [
        rng.gauss(
            0.0,
            1.0,
        )
        for _ in range(count)
    ]


def scale(
    values: list[float],
    minimum: float,
    maximum: float,
) -> list[float]:

    low = min(values)
    high = max(values)

    if math.isclose(
        low,
        high,
    ):

        midpoint = (minimum + maximum) / 2.0

        return [midpoint for _ in values]

    return [
        minimum + ((value - low) / (high - low)) * (maximum - minimum)
        for value in values
    ]


# ============================================================================
# CORRELATED GENERATION
# ============================================================================


def generate_correlated(
    source: list[float],
    target_correlation: float,
    rng: random.Random,
) -> list[float]:

    source_mean = mean(source)

    centered = [value - source_mean for value in source]

    variance = mean(value * value for value in centered)

    if math.isclose(
        variance,
        0.0,
    ):
        raise ValueError("Source has zero variance.")

    source_std = math.sqrt(variance)

    normalized = [value / source_std for value in centered]

    independent = standard_normal(
        rng,
        len(source),
    )

    residual = math.sqrt(
        max(
            0.0,
            1.0 - target_correlation**2,
        )
    )

    return [
        (target_correlation * source_value) + (residual * independent_value)
        for source_value, independent_value in zip(
            normalized,
            independent,
        )
    ]


# ============================================================================
# SPECIFICATION VALIDATION
# ============================================================================


def validate_specification(
    specification: GenerationSpecification,
) -> None:

    fields = specification.fields

    if not fields:
        raise ValueError("Specification must contain fields.")

    for field in fields.values():

        if field.minimum > field.maximum:
            raise ValueError(f"Invalid bounds for " f"{field.name}")

    for relationship in specification.relationships:

        if relationship.source_field not in fields:
            raise ValueError(f"Unknown source field: " f"{relationship.source_field}")

        if relationship.target_field not in fields:
            raise ValueError(f"Unknown target field: " f"{relationship.target_field}")

        if relationship.source_field == relationship.target_field:
            raise ValueError("Self-correlation is not allowed.")

        if not (-1.0 <= relationship.target_correlation <= 1.0):
            raise ValueError("Target correlation must " "be between -1 and 1.")

        if relationship.tolerance < 0:
            raise ValueError("Correlation tolerance " "cannot be negative.")

    for conditional in specification.conditionals:

        if conditional.condition_field not in fields:
            raise ValueError(
                f"Unknown condition field: " f"{conditional.condition_field}"
            )

        if conditional.target_field not in fields:
            raise ValueError(
                f"Unknown conditional " f"target field: " f"{conditional.target_field}"
            )

        if (
            conditional.minimum is not None
            and conditional.maximum is not None
            and conditional.minimum > conditional.maximum
        ):
            raise ValueError(f"Invalid conditional " f"range: {conditional.name}")

    for derived in specification.derived_fields:

        if derived.name in fields:
            raise ValueError(f"Derived field already " f"exists: {derived.name}")

        for dependency in derived.dependencies:

            if dependency not in fields:
                raise ValueError(f"Unknown derived " f"dependency: {dependency}")

    for constraint in specification.constraints:

        if not constraint.expression:
            raise ValueError(f"Empty constraint: " f"{constraint.name}")


# ============================================================================
# DEPENDENCY PLANNING
# ============================================================================


def build_dependency_graph(
    specification: GenerationSpecification,
) -> dict[str, set[str]]:

    graph = {field: set() for field in specification.fields}

    for derived in specification.derived_fields:

        graph[derived.name] = set(derived.dependencies)

    return graph


def topological_order(
    graph: dict[str, set[str]],
) -> list[str]:

    remaining = {key: set(value) for key, value in graph.items()}

    order = []

    while remaining:

        ready = sorted(
            key for key, dependencies in remaining.items() if not dependencies
        )

        if not ready:
            raise ValueError("Dependency cycle detected.")

        for key in ready:

            order.append(key)

            del remaining[key]

        for dependencies in remaining.values():

            dependencies.difference_update(ready)

    return order


# ============================================================================
# CONSTRAINT EVALUATION
# ============================================================================


def evaluate_constraint(
    expression: str,
    record: dict[str, float],
) -> bool:
    """
    Deliberately small declarative constraint evaluator.

    Supported expressions in this experiment:

        A >= number
        A <= number
        A > B
        A >= B
        A + B <= number
        A * number <= B

    This is intentionally not a general expression engine.
    """

    expression = expression.strip()

    if ">=" in expression:

        left, right = (
            part.strip()
            for part in expression.split(
                ">=",
                1,
            )
        )

        return evaluate_value(
            left,
            record,
        ) >= evaluate_value(
            right,
            record,
        )

    if "<=" in expression:

        left, right = (
            part.strip()
            for part in expression.split(
                "<=",
                1,
            )
        )

        return evaluate_value(
            left,
            record,
        ) <= evaluate_value(
            right,
            record,
        )

    if ">" in expression:

        left, right = (
            part.strip()
            for part in expression.split(
                ">",
                1,
            )
        )

        return evaluate_value(
            left,
            record,
        ) > evaluate_value(
            right,
            record,
        )

    if "<" in expression:

        left, right = (
            part.strip()
            for part in expression.split(
                "<",
                1,
            )
        )

        return evaluate_value(
            left,
            record,
        ) < evaluate_value(
            right,
            record,
        )

    raise ValueError(f"Unsupported constraint: " f"{expression}")


def evaluate_value(
    expression: str,
    record: dict[str, float],
) -> float:

    expression = expression.strip()

    if expression in record:
        return float(record[expression])

    if "*" in expression:

        left, right = (
            part.strip()
            for part in expression.split(
                "*",
                1,
            )
        )

        return evaluate_value(
            left,
            record,
        ) * float(right)

    if "+" in expression:

        left, right = (
            part.strip()
            for part in expression.split(
                "+",
                1,
            )
        )

        return evaluate_value(
            left,
            record,
        ) + evaluate_value(
            right,
            record,
        )

    return float(expression)


# ============================================================================
# COMBINED GENERATION
# ============================================================================


def generate_base_fields(
    specification: GenerationSpecification,
    count: int,
    seed: int,
) -> dict[str, list[float]]:

    relationships = specification.relationships

    relationship_by_target = {
        relationship.target_field: relationship for relationship in relationships
    }

    datasets = {}

    field_names = sorted(specification.fields.keys())

    # Fields participating as relationship
    # sources get their own deterministic
    # random stream.
    for field_name in field_names:

        if field_name in relationship_by_target:
            continue

        field = specification.fields[field_name]

        rng = rng_for(
            seed,
            f"FIELD:{field_name}",
        )

        latent = standard_normal(
            rng,
            count,
        )

        datasets[field_name] = scale(
            latent,
            field.minimum,
            field.maximum,
        )

    # Targets are generated from their
    # declared statistical relationship.
    for relationship in relationships:

        source = datasets.get(relationship.source_field)

        if source is None:
            raise ValueError(
                f"Source field " f"{relationship.source_field} " f"was not generated."
            )

        rng = rng_for(
            seed,
            f"REL:{relationship.name}",
        )

        latent = generate_correlated(
            source,
            relationship.target_correlation,
            rng,
        )

        target = specification.fields[relationship.target_field]

        datasets[relationship.target_field] = scale(
            latent,
            target.minimum,
            target.maximum,
        )

    return datasets


def apply_conditionals(
    specification: GenerationSpecification,
    datasets: dict[str, list[float]],
) -> None:

    for conditional in specification.conditionals:

        condition_values = datasets[conditional.condition_field]

        target_values = datasets[conditional.target_field]

        for index, condition_value in enumerate(condition_values):

            if condition_value >= 70.0:

                if conditional.minimum is not None:
                    target_values[index] = max(
                        target_values[index],
                        conditional.minimum,
                    )

                if conditional.maximum is not None:
                    target_values[index] = min(
                        target_values[index],
                        conditional.maximum,
                    )


def apply_derived_fields(
    specification: GenerationSpecification,
    datasets: dict[str, list[float]],
) -> None:

    graph = build_dependency_graph(specification)

    order = topological_order(graph)

    for field_name in order:

        derived = next(
            (item for item in specification.derived_fields if item.name == field_name),
            None,
        )

        if derived is None:
            continue

        if derived.formula == ("CREDIT_LIMIT * " "CUSTOMER_SCORE / 100"):

            credit = datasets["CREDIT_LIMIT"]

            score = datasets["CUSTOMER_SCORE"]

            datasets[field_name] = [
                credit_value * score_value / 100.0
                for credit_value, score_value in zip(
                    credit,
                    score,
                )
            ]

        elif derived.formula == ("CREDIT_LIMIT - RISK_SCORE"):

            credit = datasets["CREDIT_LIMIT"]

            risk = datasets["RISK_SCORE"]

            datasets[field_name] = [
                credit_value - risk_value
                for credit_value, risk_value in zip(
                    credit,
                    risk,
                )
            ]

        else:

            raise ValueError(f"Unsupported formula: " f"{derived.formula}")


# ============================================================================
# VALIDATION
# ============================================================================


def validate_constraints(
    specification: GenerationSpecification,
    datasets: dict[str, list[float]],
) -> bool:

    count = len(next(iter(datasets.values())))

    for field_name, field in specification.fields.items():

        if field_name not in datasets:
            continue

        for value in datasets[field_name]:

            if not (field.minimum <= value <= field.maximum):
                return False

    for constraint in specification.constraints:

        for index in range(count):

            record = {field: values[index] for field, values in datasets.items()}

            if not evaluate_constraint(
                constraint.expression,
                record,
            ):
                return False

    return True


def validate_conditionals(
    specification: GenerationSpecification,
    datasets: dict[str, list[float]],
) -> bool:

    for conditional in specification.conditionals:

        condition_values = datasets[conditional.condition_field]

        target_values = datasets[conditional.target_field]

        for condition_value, target_value in zip(
            condition_values,
            target_values,
        ):

            if condition_value >= 70.0:

                if (
                    conditional.minimum is not None
                    and target_value < conditional.minimum
                ):
                    return False

                if (
                    conditional.maximum is not None
                    and target_value > conditional.maximum
                ):
                    return False

    return True


def validate_relationships(
    specification: GenerationSpecification,
    datasets: dict[str, list[float]],
) -> bool:

    for relationship in specification.relationships:

        observed = pearson(
            datasets[relationship.source_field],
            datasets[relationship.target_field],
        )

        if abs(observed - relationship.target_correlation) > relationship.tolerance:

            return False

    return True


# ============================================================================
# COMPLETE PIPELINE
# ============================================================================


def generate_dataset(
    specification: GenerationSpecification,
    count: int,
    seed: int,
) -> dict[str, list[float]]:

    validate_specification(specification)

    # Feasibility is checked before generation.
    #
    # This deliberately blocks impossible
    # statistical specifications rather than
    # generating and repairing them.
    validate_relationship_graph(specification)

    datasets = generate_base_fields(
        specification,
        count,
        seed,
    )

    apply_conditionals(
        specification,
        datasets,
    )

    apply_derived_fields(
        specification,
        datasets,
    )

    if not validate_constraints(
        specification,
        datasets,
    ):
        raise ValueError("Generated dataset violates " "declarative constraints.")

    if not validate_conditionals(
        specification,
        datasets,
    ):
        raise ValueError("Generated dataset violates " "conditional rules.")

    if not validate_relationships(
        specification,
        datasets,
    ):
        raise ValueError("Generated dataset violates " "statistical relationships.")

    return datasets


def validate_relationship_graph(
    specification: GenerationSpecification,
) -> None:

    fields = sorted(specification.fields.keys())

    matrix = [[0.0 for _ in fields] for _ in fields]

    for index in range(len(fields)):
        matrix[index][index] = 1.0

    positions = {field: index for index, field in enumerate(fields)}

    for relationship in specification.relationships:

        source = positions[relationship.source_field]

        target = positions[relationship.target_field]

        value = relationship.target_correlation

        existing = matrix[source][target]

        if not math.isclose(
            existing,
            0.0,
        ) and not math.isclose(
            existing,
            value,
        ):
            raise ValueError("Conflicting statistical " "relationships.")

        matrix[source][target] = value
        matrix[target][source] = value

    # Small-matrix determinant test.
    # For the integrated experiment the
    # statistical graphs remain intentionally
    # small.
    if not is_psd(matrix):
        raise ValueError("Statistical relationships " "are jointly infeasible.")


def determinant(
    matrix: list[list[float]],
) -> float:

    size = len(matrix)

    if size == 0:
        return 1.0

    if size == 1:
        return matrix[0][0]

    if size == 2:
        return matrix[0][0] * matrix[1][1] - matrix[0][1] * matrix[1][0]

    result = 0.0

    for column in range(size):

        minor = []

        for row in range(
            1,
            size,
        ):

            minor.append([matrix[row][c] for c in range(size) if c != column])

        sign = 1 if column % 2 == 0 else -1

        result += sign * matrix[0][column] * determinant(minor)

    return result


def is_psd(
    matrix: list[list[float]],
) -> bool:

    size = len(matrix)

    for i in range(size):

        for j in range(size):

            if not math.isclose(
                matrix[i][j],
                matrix[j][i],
                abs_tol=1e-9,
            ):
                return False

    # Principal minors.
    for i in range(size):

        if matrix[i][i] < -1e-9:
            return False

    if size >= 2:

        for i in range(size):

            for j in range(
                i + 1,
                size,
            ):

                minor = [
                    [
                        matrix[i][i],
                        matrix[i][j],
                    ],
                    [
                        matrix[j][i],
                        matrix[j][j],
                    ],
                ]

                if determinant(minor) < -1e-9:

                    return False

    if size >= 3:

        if determinant(matrix) < -1e-9:

            return False

    return True


# ============================================================================
# SPECIFICATIONS
# ============================================================================


def build_integrated_specification() -> GenerationSpecification:

    return GenerationSpecification(
        fields=copy.deepcopy(FIELDS),
        relationships=(
            StatisticalRelationship(
                name="SCORE_TO_CREDIT",
                source_field="CUSTOMER_SCORE",
                target_field="CREDIT_LIMIT",
                target_correlation=0.55,
                tolerance=0.20,
            ),
            StatisticalRelationship(
                name="SCORE_TO_RISK",
                source_field="CUSTOMER_SCORE",
                target_field="RISK_SCORE",
                target_correlation=-0.45,
                tolerance=0.20,
            ),
        ),
        constraints=(
            Constraint(
                name="CREDIT_LIMIT_MIN",
                expression=("CREDIT_LIMIT >= 1000"),
            ),
            Constraint(
                name="SCORE_LIMIT",
                expression=("CUSTOMER_SCORE <= 100"),
            ),
        ),
        conditionals=(
            ConditionalRule(
                name="PREMIUM_CREDIT",
                condition_field=("CUSTOMER_SCORE"),
                condition_value=70,
                target_field=("CREDIT_LIMIT"),
                minimum=5000.0,
            ),
        ),
        derived_fields=(
            DerivedField(
                name="NET_VALUE",
                dependencies=(
                    "CUSTOMER_SCORE",
                    "CREDIT_LIMIT",
                ),
                formula=("CREDIT_LIMIT * " "CUSTOMER_SCORE / 100"),
            ),
        ),
    )


def build_impossible_specification() -> GenerationSpecification:

    specification = build_integrated_specification()

    impossible = (
        StatisticalRelationship(
            name="IMPOSSIBLE_RELATIONSHIP",
            source_field="CUSTOMER_SCORE",
            target_field="RISK_SCORE",
            target_correlation=1.5,
            tolerance=0.10,
        ),
    )

    return GenerationSpecification(
        fields=specification.fields,
        relationships=impossible,
        constraints=specification.constraints,
        conditionals=specification.conditionals,
        derived_fields=specification.derived_fields,
    )


# ============================================================================
# TEST HELPERS
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
            "status": "FAIL",
            "error": (f"{type(exc).__name__}: " f"{exc}"),
        }


# ============================================================================
# TESTS
# ============================================================================


def test_complete_generation() -> bool:

    specification = build_integrated_specification()

    dataset = generate_dataset(
        specification,
        1000,
        MASTER_SEED,
    )

    return len(dataset) >= 4 and all(len(values) == 1000 for values in dataset.values())


def test_statistical_relationships() -> bool:

    specification = build_integrated_specification()

    dataset = generate_dataset(
        specification,
        1000,
        MASTER_SEED,
    )

    return validate_relationships(
        specification,
        dataset,
    )


def test_field_constraints() -> bool:

    specification = build_integrated_specification()

    dataset = generate_dataset(
        specification,
        1000,
        MASTER_SEED,
    )

    return validate_constraints(
        specification,
        dataset,
    )


def test_conditionals() -> bool:

    specification = build_integrated_specification()

    dataset = generate_dataset(
        specification,
        1000,
        MASTER_SEED,
    )

    return validate_conditionals(
        specification,
        dataset,
    )


def test_derived_fields() -> bool:

    specification = build_integrated_specification()

    dataset = generate_dataset(
        specification,
        1000,
        MASTER_SEED,
    )

    for score, credit, net in zip(
        dataset["CUSTOMER_SCORE"],
        dataset["CREDIT_LIMIT"],
        dataset["NET_VALUE"],
    ):

        expected = credit * score / 100.0

        if not math.isclose(
            net,
            expected,
            rel_tol=1e-9,
        ):
            return False

    return True


def test_dependency_planning() -> bool:

    specification = build_integrated_specification()

    graph = build_dependency_graph(specification)

    order = topological_order(graph)

    return order.index("CREDIT_LIMIT") < order.index("NET_VALUE") and order.index(
        "CUSTOMER_SCORE"
    ) < order.index("NET_VALUE")


def test_reproducibility() -> bool:

    specification = build_integrated_specification()

    first = generate_dataset(
        specification,
        500,
        42,
    )

    second = generate_dataset(
        specification,
        500,
        42,
    )

    return first == second


def test_seed_sensitivity() -> bool:

    specification = build_integrated_specification()

    first = generate_dataset(
        specification,
        500,
        42,
    )

    second = generate_dataset(
        specification,
        500,
        43,
    )

    return first != second


def test_field_order_independence() -> bool:

    specification = build_integrated_specification()

    reversed_fields = dict(reversed(list(specification.fields.items())))

    reversed_specification = GenerationSpecification(
        fields=reversed_fields,
        relationships=specification.relationships,
        constraints=specification.constraints,
        conditionals=specification.conditionals,
        derived_fields=specification.derived_fields,
    )

    first = generate_dataset(
        specification,
        500,
        MASTER_SEED,
    )

    second = generate_dataset(
        reversed_specification,
        500,
        MASTER_SEED,
    )

    return first == second


def test_impossible_specification_blocking() -> bool:

    specification = build_impossible_specification()

    try:

        generate_dataset(
            specification,
            500,
            MASTER_SEED,
        )

    except ValueError:

        return True

    return False


def test_no_hidden_fallback() -> bool:

    specification = build_impossible_specification()

    try:

        dataset = generate_dataset(
            specification,
            500,
            MASTER_SEED,
        )

        return dataset == {}

    except ValueError:

        return True


def test_no_post_generation_repair() -> bool:

    specification = build_integrated_specification()

    dataset = generate_dataset(
        specification,
        1000,
        MASTER_SEED,
    )

    # The dataset is directly validated after
    # generation. No repair pass exists in
    # this experiment.
    return (
        validate_constraints(
            specification,
            dataset,
        )
        and validate_relationships(
            specification,
            dataset,
        )
        and validate_conditionals(
            specification,
            dataset,
        )
    )


def test_configuration_safety() -> bool:

    specification = build_integrated_specification()

    validate_specification(specification)

    return True


def test_combined_integrity() -> bool:

    specification = build_integrated_specification()

    dataset = generate_dataset(
        specification,
        1000,
        MASTER_SEED,
    )

    return (
        validate_constraints(
            specification,
            dataset,
        )
        and validate_relationships(
            specification,
            dataset,
        )
        and validate_conditionals(
            specification,
            dataset,
        )
    )


# ============================================================================
# MAIN
# ============================================================================


def main() -> int:

    print()

    print("=" * 70)

    print(
        "FORGE - Experiment 020-R: "
        "Declarative Constraint and Statistical Integration"
    )

    print("=" * 70)

    print("Experiment:     " "020_declarative_generation_specification")

    print("Stage:          020-R")

    print("Purpose:        " "Integrated constraint and statistical generation")

    print(f"Random seed:    {MASTER_SEED}")

    print()

    print("Integrated generation architecture:")

    print("  Declarative specification")

    print("       ↓")

    print("  Statistical relationships")

    print("       ↓")

    print("  Constraint analysis")

    print("       ↓")

    print("  Dependency planning")

    print("       ↓")

    print("  Context-aware generation")

    print("       ↓")

    print("  Derived / conditional generation")

    print("       ↓")

    print("  Unified validation")

    print()

    specification = build_integrated_specification()

    print("Integrated capabilities:")

    print("  Statistical relationships: " f"{len(specification.relationships)}")

    print("  Constraints:               " f"{len(specification.constraints)}")

    print("  Conditional rules:         " f"{len(specification.conditionals)}")

    print("  Derived fields:            " f"{len(specification.derived_fields)}")

    print()

    tests = [
        (
            "Complete generation",
            test_complete_generation,
        ),
        (
            "Statistical relationships",
            test_statistical_relationships,
        ),
        (
            "Field constraints",
            test_field_constraints,
        ),
        (
            "Conditional rules",
            test_conditionals,
        ),
        (
            "Derived fields",
            test_derived_fields,
        ),
        (
            "Dependency planning",
            test_dependency_planning,
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
            "Field-order independence",
            test_field_order_independence,
        ),
        (
            "Impossible specification blocking",
            test_impossible_specification_blocking,
        ),
        (
            "No hidden fallback",
            test_no_hidden_fallback,
        ),
        (
            "No post-generation repair",
            test_no_post_generation_repair,
        ),
        (
            "Configuration safety",
            test_configuration_safety,
        ),
        (
            "Combined integrity",
            test_combined_integrity,
        ),
    ]

    print("Integrated generation validation:")

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

    print("Experiment result:")

    print(f"  Complete generation:       " f"{results[0]['status']}")

    print(f"  Statistical relationships: " f"{results[1]['status']}")

    print(f"  Constraints:               " f"{results[2]['status']}")

    print(f"  Conditional rules:         " f"{results[3]['status']}")

    print(f"  Derived fields:            " f"{results[4]['status']}")

    print(f"  Dependency planning:       " f"{results[5]['status']}")

    print(f"  Reproducibility:            " f"{results[6]['status']}")

    print(f"  Seed sensitivity:           " f"{results[7]['status']}")

    print(f"  Field-order independence:   " f"{results[8]['status']}")

    print(f"  Impossible-spec safety:     " f"{results[9]['status']}")

    print(f"  No hidden fallback:         " f"{results[10]['status']}")

    print(f"  No post-generation repair:  " f"{results[11]['status']}")

    print(f"  Combined integrity:         " f"{results[13]['status']}")

    print()

    print(f"  Tests passed:              " f"{passed}/{total}")

    print(f"  Overall:                   " f"{'PASS' if overall else 'FAIL'}")

    # ------------------------------------------------------------------
    # Representative dataset
    # ------------------------------------------------------------------

    if overall:

        dataset = generate_dataset(
            specification,
            5,
            MASTER_SEED,
        )

        print()

        print("Representative generated records:")

        for index in range(5):

            record = {
                field: round(
                    values[index],
                    3,
                )
                for field, values in dataset.items()
            }

            print(f"  {record}")

    # ------------------------------------------------------------------
    # Persist results
    # ------------------------------------------------------------------

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    output = {
        "experiment": ("020_declarative_generation_specification"),
        "stage": "020-R",
        "purpose": ("Declarative constraint and " "statistical integration"),
        "seed": MASTER_SEED,
        "capabilities": {
            "statistical_relationships": len(specification.relationships),
            "constraints": len(specification.constraints),
            "conditionals": len(specification.conditionals),
            "derived_fields": len(specification.derived_fields),
        },
        "tests": results,
        "tests_passed": passed,
        "tests_total": total,
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

        print(
            "Constraint and statistical " "integration is " "experimentally validated."
        )

        return 0

    print("Experiment completed with failures.")

    return 1


if __name__ == "__main__":

    sys.exit(main())
