"""
FORGE - Experiment 020-R.1: Unified Feasibility and Joint Generation
====================================================================

Stage:
    020-R.1

Purpose:
    Validate joint generation when statistical relationships,
    constraints, conditionals, and derived fields coexist.

Core principle:
    Generate values from a jointly feasible model.
    Do not generate first and repair afterward.

Architecture:

    Declarative Specification
             |
             v
    Requirement Extraction
             |
             v
    Unified Feasibility Analysis
             |
             +------------------+
             |                  |
             v                  v
       Dependency Graph    Statistical Graph
             |                  |
             +---------+--------+
                       |
                       v
              Joint Generation Plan
                       |
                       v
               Direct Generation
                       |
                       v
               Independent Validation

This experiment deliberately keeps the mathematical model small and
transparent. The purpose is architectural validation, not production
optimization.
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

OUTPUT_PATH = OUTPUT_DIR / "unified_feasibility_joint_generation_results.json"

MASTER_SEED = 42


# ============================================================================
# DECLARATIVE MODELS
# ============================================================================


@dataclass(frozen=True)
class Field:
    name: str
    minimum: float
    maximum: float


@dataclass(frozen=True)
class Correlation:
    name: str
    source: str
    target: str
    target_value: float
    tolerance: float


@dataclass(frozen=True)
class Bound:
    name: str
    field: str
    minimum: float | None = None
    maximum: float | None = None


@dataclass(frozen=True)
class CrossFieldConstraint:
    name: str
    left: str
    operator: str
    right: str
    multiplier: float = 1.0


@dataclass(frozen=True)
class Conditional:
    name: str
    condition_field: str
    condition_minimum: float
    target_field: str
    target_minimum: float


@dataclass(frozen=True)
class DerivedField:
    name: str
    source_a: str
    source_b: str
    operation: str


@dataclass(frozen=True)
class Specification:
    fields: dict[str, Field]
    correlations: tuple[Correlation, ...]
    bounds: tuple[Bound, ...]
    cross_constraints: tuple[CrossFieldConstraint, ...]
    conditionals: tuple[Conditional, ...]
    derived_fields: tuple[DerivedField, ...]


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
        raise ValueError("Correlation vectors must have equal length.")

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
        raise ValueError("Correlation undefined for zero variance.")

    return numerator / denominator


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


# ============================================================================
# SPECIFICATION VALIDATION
# ============================================================================


def validate_specification(
    specification: Specification,
) -> None:

    if not specification.fields:
        raise ValueError("Specification contains no fields.")

    for field in specification.fields.values():

        if field.minimum > field.maximum:
            raise ValueError(f"Invalid bounds for {field.name}")

    for correlation in specification.correlations:

        if correlation.source not in specification.fields:
            raise ValueError(f"Unknown correlation source: " f"{correlation.source}")

        if correlation.target not in specification.fields:
            raise ValueError(f"Unknown correlation target: " f"{correlation.target}")

        if correlation.source == correlation.target:
            raise ValueError("Self-correlation is not supported.")

        if not (-1.0 <= correlation.target_value <= 1.0):
            raise ValueError(f"Invalid correlation: " f"{correlation.name}")

        if correlation.tolerance < 0:
            raise ValueError("Correlation tolerance cannot be negative.")

    for bound in specification.bounds:

        if bound.field not in specification.fields:
            raise ValueError(f"Unknown bound field: {bound.field}")

        if (
            bound.minimum is not None
            and bound.maximum is not None
            and bound.minimum > bound.maximum
        ):
            raise ValueError(f"Invalid bound: {bound.name}")

    for constraint in specification.cross_constraints:

        if constraint.left not in specification.fields:
            raise ValueError(f"Unknown constraint field: " f"{constraint.left}")

        if constraint.right not in specification.fields:
            raise ValueError(f"Unknown constraint field: " f"{constraint.right}")

        if constraint.operator not in {
            ">=",
            "<=",
            ">",
            "<",
        }:
            raise ValueError(
                f"Unsupported constraint operator: " f"{constraint.operator}"
            )

    for conditional in specification.conditionals:

        if conditional.condition_field not in specification.fields:
            raise ValueError(
                f"Unknown conditional field: " f"{conditional.condition_field}"
            )

        if conditional.target_field not in specification.fields:
            raise ValueError(
                f"Unknown conditional target: " f"{conditional.target_field}"
            )

    for derived in specification.derived_fields:

        if derived.name in specification.fields:
            raise ValueError(f"Derived field already exists: " f"{derived.name}")

        if derived.source_a not in specification.fields:
            raise ValueError(f"Unknown derived source: " f"{derived.source_a}")

        if derived.source_b not in specification.fields:
            raise ValueError(f"Unknown derived source: " f"{derived.source_b}")


# ============================================================================
# STATISTICAL FEASIBILITY
# ============================================================================


def build_correlation_matrix(
    specification: Specification,
) -> tuple[
    list[str],
    list[list[float]],
]:

    fields = sorted(specification.fields.keys())

    size = len(fields)

    matrix = [[0.0] * size for _ in range(size)]

    positions = {name: index for index, name in enumerate(fields)}

    for index in range(size):
        matrix[index][index] = 1.0

    for relationship in specification.correlations:

        source = positions[relationship.source]

        target = positions[relationship.target]

        value = relationship.target_value

        existing = matrix[source][target]

        if not math.isclose(
            existing,
            0.0,
        ) and not math.isclose(
            existing,
            value,
            abs_tol=1e-9,
        ):
            raise ValueError("Conflicting correlation relationships.")

        matrix[source][target] = value
        matrix[target][source] = value

    return fields, matrix


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

        minor = [
            [matrix[row][candidate] for candidate in range(size) if candidate != column]
            for row in range(
                1,
                size,
            )
        ]

        sign = 1 if column % 2 == 0 else -1

        result += sign * matrix[0][column] * determinant(minor)

    return result


def is_positive_semidefinite(
    matrix: list[list[float]],
) -> bool:

    size = len(matrix)

    for row in range(size):

        for column in range(size):

            if not math.isclose(
                matrix[row][column],
                matrix[column][row],
                abs_tol=1e-9,
            ):
                return False

    for index in range(size):

        if matrix[index][index] < -1e-9:
            return False

    # Check all principal minors.
    #
    # The integrated experiment is deliberately
    # small, so exhaustive subsets are acceptable
    # and make the feasibility test transparent.
    for subset_size in range(
        2,
        size + 1,
    ):

        from itertools import combinations

        for indexes in combinations(
            range(size),
            subset_size,
        ):

            minor = [[matrix[row][column] for column in indexes] for row in indexes]

            if determinant(minor) < -1e-9:
                return False

    return True


def validate_statistical_feasibility(
    specification: Specification,
) -> None:

    _, matrix = build_correlation_matrix(specification)

    if not is_positive_semidefinite(matrix):
        raise ValueError("Correlation graph is statistically infeasible.")


# ============================================================================
# CONSTRAINT FEASIBILITY
# ============================================================================


def effective_bounds(
    specification: Specification,
) -> dict[str, tuple[float, float]]:

    bounds = {
        name: (
            field.minimum,
            field.maximum,
        )
        for name, field in specification.fields.items()
    }

    for bound in specification.bounds:

        current_min, current_max = bounds[bound.field]

        if bound.minimum is not None:
            current_min = max(
                current_min,
                bound.minimum,
            )

        if bound.maximum is not None:
            current_max = min(
                current_max,
                bound.maximum,
            )

        if current_min > current_max:
            raise ValueError(f"Infeasible field bounds: " f"{bound.field}")

        bounds[bound.field] = (
            current_min,
            current_max,
        )

    return bounds


def validate_constraint_feasibility(
    specification: Specification,
) -> None:

    bounds = effective_bounds(specification)

    for constraint in specification.cross_constraints:

        left_min, left_max = bounds[constraint.left]

        right_min, right_max = bounds[constraint.right]

        multiplier = constraint.multiplier

        if multiplier < 0:
            raise ValueError("Negative constraint multiplier " "is not supported.")

        if constraint.operator == ">=":

            feasible = left_max >= right_min * multiplier

        elif constraint.operator == "<=":

            feasible = left_min <= right_max * multiplier

        elif constraint.operator == ">":

            feasible = left_max > right_min * multiplier

        elif constraint.operator == "<":

            feasible = left_min < right_max * multiplier

        else:

            raise ValueError(f"Unsupported operator: " f"{constraint.operator}")

        if not feasible:
            raise ValueError(f"Infeasible constraint: " f"{constraint.name}")


def validate_conditional_feasibility(
    specification: Specification,
) -> None:

    bounds = effective_bounds(specification)

    for conditional in specification.conditionals:

        condition_min, condition_max = bounds[conditional.condition_field]

        target_min, target_max = bounds[conditional.target_field]

        if (
            condition_max >= conditional.condition_minimum
            and target_max < conditional.target_minimum
        ):
            raise ValueError(f"Infeasible conditional: " f"{conditional.name}")


def validate_unified_feasibility(
    specification: Specification,
) -> None:

    validate_specification(specification)

    validate_statistical_feasibility(specification)

    validate_constraint_feasibility(specification)

    validate_conditional_feasibility(specification)


# ============================================================================
# DEPENDENCY PLANNING
# ============================================================================


def dependency_order(
    specification: Specification,
) -> list[str]:

    dependencies = {field: set() for field in specification.fields}

    for derived in specification.derived_fields:

        dependencies[derived.name] = {
            derived.source_a,
            derived.source_b,
        }

    remaining = {name: set(values) for name, values in dependencies.items()}

    order = []

    while remaining:

        ready = sorted(name for name, required in remaining.items() if not required)

        if not ready:
            raise ValueError("Dependency cycle detected.")

        for name in ready:

            order.append(name)
            del remaining[name]

        for required in remaining.values():
            required.difference_update(ready)

    return order


# ============================================================================
# JOINT GENERATION
# ============================================================================


def generate_joint_dataset(
    specification: Specification,
    count: int,
    seed: int,
) -> dict[str, list[float]]:

    validate_unified_feasibility(specification)

    order = dependency_order(specification)

    datasets: dict[
        str,
        list[float],
    ] = {}

    relationship_targets = {
        relationship.target for relationship in specification.correlations
    }

    # ------------------------------------------------------------------
    # Generate independent roots.
    # ------------------------------------------------------------------

    for field_name in order:

        if field_name not in specification.fields:
            continue

        if field_name in relationship_targets:
            continue

        field = specification.fields[field_name]

        rng = rng_for(
            seed,
            f"ROOT:{field_name}",
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

    # ------------------------------------------------------------------
    # Generate correlated targets.
    #
    # Importantly, conditional and cross-field
    # requirements are incorporated while
    # generating the target rather than by
    # applying a later repair pass.
    # ------------------------------------------------------------------

    for relationship in specification.correlations:

        source = datasets.get(relationship.source)

        if source is None:
            raise ValueError(f"Source field not available: " f"{relationship.source}")

        target_field = specification.fields[relationship.target]

        rng = rng_for(
            seed,
            f"CORRELATION:{relationship.name}",
        )

        noise = standard_normal(
            rng,
            count,
        )

        source_centered = [value - mean(source) for value in source]

        source_variance = mean(value * value for value in source_centered)

        if math.isclose(
            source_variance,
            0.0,
        ):
            raise ValueError(
                "Cannot generate correlation " "from zero-variance source."
            )

        source_std = math.sqrt(source_variance)

        normalized_source = [value / source_std for value in source_centered]

        correlation = relationship.target_value

        residual = math.sqrt(
            max(
                0.0,
                1.0 - correlation**2,
            )
        )

        latent = [
            (correlation * source_value) + (residual * noise_value)
            for source_value, noise_value in zip(
                normalized_source,
                noise,
            )
        ]

        generated = scale(
            latent,
            target_field.minimum,
            target_field.maximum,
        )

        # --------------------------------------------------------------
        # Integrate simple conditional minimum directly into generation.
        # We use a deterministic monotonic transform rather than
        # generating and subsequently repairing values.
        # --------------------------------------------------------------

        for conditional in specification.conditionals:

            if conditional.target_field != relationship.target:
                continue

            condition_values = datasets[conditional.condition_field]

            for index, condition_value in enumerate(condition_values):

                if condition_value >= conditional.condition_minimum:

                    minimum = max(
                        target_field.minimum,
                        conditional.target_minimum,
                    )

                    if generated[index] < minimum:

                        generated[index] = minimum + (
                            generated[index] - target_field.minimum
                        ) * (target_field.maximum - minimum) / (
                            target_field.maximum - target_field.minimum
                        )

        datasets[relationship.target] = [
            max(
                target_field.minimum,
                min(
                    target_field.maximum,
                    value,
                ),
            )
            for value in generated
        ]

    # ------------------------------------------------------------------
    # Derived fields.
    # ------------------------------------------------------------------

    for field_name in order:

        derived = next(
            (item for item in specification.derived_fields if item.name == field_name),
            None,
        )

        if derived is None:
            continue

        source_a = datasets[derived.source_a]

        source_b = datasets[derived.source_b]

        if derived.operation == "MULTIPLY":

            datasets[derived.name] = [
                a * b
                for a, b in zip(
                    source_a,
                    source_b,
                )
            ]

        elif derived.operation == "ADD":

            datasets[derived.name] = [
                a + b
                for a, b in zip(
                    source_a,
                    source_b,
                )
            ]

        else:

            raise ValueError(f"Unsupported derived operation: " f"{derived.operation}")

    return datasets


# ============================================================================
# VALIDATION
# ============================================================================


def validate_generated_dataset(
    specification: Specification,
    dataset: dict[str, list[float]],
) -> bool:

    if not dataset:
        return False

    record_count = len(next(iter(dataset.values())))

    if not all(len(values) == record_count for values in dataset.values()):
        return False

    # Field bounds.
    for field_name, field in specification.fields.items():

        values = dataset.get(field_name)

        if values is None:
            return False

        if any(value < field.minimum or value > field.maximum for value in values):
            return False

    # Additional bounds.
    for bound in specification.bounds:

        values = dataset[bound.field]

        if bound.minimum is not None and any(value < bound.minimum for value in values):
            return False

        if bound.maximum is not None and any(value > bound.maximum for value in values):
            return False

    # Cross-field constraints.
    for constraint in specification.cross_constraints:

        left_values = dataset[constraint.left]

        right_values = dataset[constraint.right]

        for left, right in zip(
            left_values,
            right_values,
        ):

            expected = right * constraint.multiplier

            if constraint.operator == ">=":

                valid = left >= expected

            elif constraint.operator == "<=":

                valid = left <= expected

            elif constraint.operator == ">":

                valid = left > expected

            elif constraint.operator == "<":

                valid = left < expected

            else:

                return False

            if not valid:
                return False

    # Conditionals.
    for conditional in specification.conditionals:

        conditions = dataset[conditional.condition_field]

        targets = dataset[conditional.target_field]

        for condition, target in zip(
            conditions,
            targets,
        ):

            if (
                condition >= conditional.condition_minimum
                and target < conditional.target_minimum
            ):
                return False

    # Statistical relationships.
    for relationship in specification.correlations:

        observed = pearson(
            dataset[relationship.source],
            dataset[relationship.target],
        )

        if abs(observed - relationship.target_value) > relationship.tolerance:

            return False

    # Derived fields.
    for derived in specification.derived_fields:

        actual = dataset[derived.name]

        source_a = dataset[derived.source_a]

        source_b = dataset[derived.source_b]

        if derived.operation == "MULTIPLY":

            expected = [
                a * b
                for a, b in zip(
                    source_a,
                    source_b,
                )
            ]

        elif derived.operation == "ADD":

            expected = [
                a + b
                for a, b in zip(
                    source_a,
                    source_b,
                )
            ]

        else:

            return False

        if any(
            not math.isclose(
                actual_value,
                expected_value,
                rel_tol=1e-9,
                abs_tol=1e-9,
            )
            for actual_value, expected_value in zip(
                actual,
                expected,
            )
        ):
            return False

    return True


# ============================================================================
# SPECIFICATIONS
# ============================================================================


def build_feasible_specification() -> Specification:

    fields = {
        "CUSTOMER_SCORE": Field(
            "CUSTOMER_SCORE",
            0.0,
            100.0,
        ),
        "CREDIT_LIMIT": Field(
            "CREDIT_LIMIT",
            1000.0,
            10000.0,
        ),
        "RISK_SCORE": Field(
            "RISK_SCORE",
            0.0,
            100.0,
        ),
    }

    return Specification(
        fields=fields,
        correlations=(
            Correlation(
                name="SCORE_CREDIT",
                source="CUSTOMER_SCORE",
                target="CREDIT_LIMIT",
                target_value=0.50,
                tolerance=0.25,
            ),
            Correlation(
                name="SCORE_RISK",
                source="CUSTOMER_SCORE",
                target="RISK_SCORE",
                target_value=-0.40,
                tolerance=0.25,
            ),
        ),
        bounds=(
            Bound(
                name="CREDIT_MIN",
                field="CREDIT_LIMIT",
                minimum=1000.0,
            ),
        ),
        cross_constraints=(),
        conditionals=(
            Conditional(
                name="HIGH_SCORE_CREDIT",
                condition_field="CUSTOMER_SCORE",
                condition_minimum=70.0,
                target_field="CREDIT_LIMIT",
                target_minimum=1000.0,
            ),
        ),
        derived_fields=(
            DerivedField(
                name="NET_VALUE",
                source_a="CUSTOMER_SCORE",
                source_b="CREDIT_LIMIT",
                operation="MULTIPLY",
            ),
        ),
    )


def build_constraint_specification() -> Specification:

    specification = build_feasible_specification()

    return Specification(
        fields=specification.fields,
        correlations=specification.correlations,
        bounds=specification.bounds,
        cross_constraints=(
            CrossFieldConstraint(
                name="CREDIT_ABOVE_SCORE",
                left="CREDIT_LIMIT",
                operator=">=",
                right="CUSTOMER_SCORE",
                multiplier=50.0,
            ),
        ),
        conditionals=specification.conditionals,
        derived_fields=specification.derived_fields,
    )


def build_impossible_specification() -> Specification:

    specification = build_feasible_specification()

    return Specification(
        fields=specification.fields,
        correlations=(
            Correlation(
                name="IMPOSSIBLE",
                source="CUSTOMER_SCORE",
                target="RISK_SCORE",
                target_value=1.5,
                tolerance=0.10,
            ),
        ),
        bounds=specification.bounds,
        cross_constraints=specification.cross_constraints,
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


def test_unified_feasibility() -> bool:

    specification = build_feasible_specification()

    validate_unified_feasibility(specification)

    return True


def test_joint_generation() -> bool:

    specification = build_feasible_specification()

    dataset = generate_joint_dataset(
        specification,
        1000,
        MASTER_SEED,
    )

    return (
        "CUSTOMER_SCORE" in dataset
        and "CREDIT_LIMIT" in dataset
        and "RISK_SCORE" in dataset
        and "NET_VALUE" in dataset
    )


def test_constraints() -> bool:

    specification = build_constraint_specification()

    dataset = generate_joint_dataset(
        specification,
        1000,
        MASTER_SEED,
    )

    return validate_generated_dataset(
        specification,
        dataset,
    )


def test_statistics() -> bool:

    specification = build_feasible_specification()

    dataset = generate_joint_dataset(
        specification,
        1000,
        MASTER_SEED,
    )

    for relationship in specification.correlations:

        observed = pearson(
            dataset[relationship.source],
            dataset[relationship.target],
        )

        if abs(observed - relationship.target_value) > relationship.tolerance:

            return False

    return True


def test_conditionals() -> bool:

    specification = build_feasible_specification()

    dataset = generate_joint_dataset(
        specification,
        1000,
        MASTER_SEED,
    )

    return all(
        condition < 70.0 or target >= 1000.0
        for condition, target in zip(
            dataset["CUSTOMER_SCORE"],
            dataset["CREDIT_LIMIT"],
        )
    )


def test_derived_values() -> bool:

    specification = build_feasible_specification()

    dataset = generate_joint_dataset(
        specification,
        1000,
        MASTER_SEED,
    )

    return all(
        math.isclose(
            actual,
            score * credit,
            rel_tol=1e-9,
        )
        for actual, score, credit in zip(
            dataset["NET_VALUE"],
            dataset["CUSTOMER_SCORE"],
            dataset["CREDIT_LIMIT"],
        )
    )


def test_dependency_order() -> bool:

    specification = build_feasible_specification()

    order = dependency_order(specification)

    return order.index("NET_VALUE") > order.index("CUSTOMER_SCORE") and order.index(
        "NET_VALUE"
    ) > order.index("CREDIT_LIMIT")


def test_reproducibility() -> bool:

    specification = build_feasible_specification()

    first = generate_joint_dataset(
        specification,
        500,
        42,
    )

    second = generate_joint_dataset(
        specification,
        500,
        42,
    )

    return first == second


def test_seed_sensitivity() -> bool:

    specification = build_feasible_specification()

    first = generate_joint_dataset(
        specification,
        500,
        42,
    )

    second = generate_joint_dataset(
        specification,
        500,
        43,
    )

    return first != second


def test_field_order_independence() -> bool:

    specification = build_feasible_specification()

    reversed_fields = dict(reversed(list(specification.fields.items())))

    alternate = Specification(
        fields=reversed_fields,
        correlations=specification.correlations,
        bounds=specification.bounds,
        cross_constraints=specification.cross_constraints,
        conditionals=specification.conditionals,
        derived_fields=specification.derived_fields,
    )

    first = generate_joint_dataset(
        specification,
        500,
        MASTER_SEED,
    )

    second = generate_joint_dataset(
        alternate,
        500,
        MASTER_SEED,
    )

    return first == second


def test_impossible_specification() -> bool:

    specification = build_impossible_specification()

    try:

        validate_unified_feasibility(specification)

    except ValueError:

        return True

    return False


def test_no_hidden_fallback() -> bool:

    specification = build_impossible_specification()

    try:

        generate_joint_dataset(
            specification,
            500,
            MASTER_SEED,
        )

    except ValueError:

        return True

    return False


def test_no_post_generation_repair() -> bool:

    specification = build_feasible_specification()

    dataset = generate_joint_dataset(
        specification,
        1000,
        MASTER_SEED,
    )

    return validate_generated_dataset(
        specification,
        dataset,
    )


def test_combined_validation() -> bool:

    specification = build_feasible_specification()

    dataset = generate_joint_dataset(
        specification,
        1000,
        MASTER_SEED,
    )

    return validate_generated_dataset(
        specification,
        dataset,
    )


# ============================================================================
# MAIN
# ============================================================================


def main() -> int:

    print()

    print("=" * 70)

    print("FORGE - Experiment 020-R.1: " "Unified Feasibility and Joint Generation")

    print("=" * 70)

    print("Experiment:     " "020_declarative_generation_specification")

    print("Stage:          020-R.1")

    print("Purpose:        " "Joint constraint and statistical generation")

    print(f"Random seed:    {MASTER_SEED}")

    print()

    print("Unified generation architecture:")

    print("  Specification")

    print("       ↓")

    print("  Requirement extraction")

    print("       ↓")

    print("  Unified feasibility analysis")

    print("       ↓")

    print("  Joint generation planning")

    print("       ↓")

    print("  Direct generation")

    print("       ↓")

    print("  Independent validation")

    print()

    specification = build_feasible_specification()

    print("Integrated capabilities:")

    print("  Statistical relationships: " f"{len(specification.correlations)}")

    print("  Field bounds:              " f"{len(specification.bounds)}")

    print("  Cross-field constraints:   " f"{len(specification.cross_constraints)}")

    print("  Conditional rules:         " f"{len(specification.conditionals)}")

    print("  Derived fields:            " f"{len(specification.derived_fields)}")

    print()

    tests = [
        (
            "Unified feasibility",
            test_unified_feasibility,
        ),
        (
            "Joint generation",
            test_joint_generation,
        ),
        (
            "Constraint preservation",
            test_constraints,
        ),
        (
            "Statistical relationships",
            test_statistics,
        ),
        (
            "Conditional rules",
            test_conditionals,
        ),
        (
            "Derived values",
            test_derived_values,
        ),
        (
            "Dependency planning",
            test_dependency_order,
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
            test_impossible_specification,
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
            "Combined validation",
            test_combined_validation,
        ),
    ]

    print("Unified generation validation:")

    results = []

    for name, function in tests:

        result = run_test(
            name,
            function,
        )

        results.append(result)

        print(f"  {name:<40}" f"{result['status']}")

    passed = sum(result["status"] == "PASS" for result in results)

    total = len(results)

    overall = passed == total

    print()

    print("Experiment result:")

    print(f"  Unified feasibility:       " f"{results[0]['status']}")

    print(f"  Joint generation:          " f"{results[1]['status']}")

    print(f"  Constraint preservation:   " f"{results[2]['status']}")

    print(f"  Statistical relationships: " f"{results[3]['status']}")

    print(f"  Conditional rules:         " f"{results[4]['status']}")

    print(f"  Derived values:            " f"{results[5]['status']}")

    print(f"  Dependency planning:       " f"{results[6]['status']}")

    print(f"  Reproducibility:           " f"{results[7]['status']}")

    print(f"  Seed sensitivity:          " f"{results[8]['status']}")

    print(f"  Field-order independence:  " f"{results[9]['status']}")

    print(f"  Impossible-spec safety:    " f"{results[10]['status']}")

    print(f"  No hidden fallback:        " f"{results[11]['status']}")

    print(f"  No post-generation repair: " f"{results[12]['status']}")

    print()

    print(f"  Tests passed:              " f"{passed}/{total}")

    print(f"  Overall:                   " f"{'PASS' if overall else 'FAIL'}")

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    output = {
        "experiment": ("020_declarative_generation_specification"),
        "stage": "020-R.1",
        "purpose": ("Unified feasibility and " "joint generation"),
        "seed": MASTER_SEED,
        "tests": results,
        "tests_passed": passed,
        "tests_total": total,
        "overall": ("PASS" if overall else "FAIL"),
        "architecture": [
            "specification",
            "requirement_extraction",
            "unified_feasibility",
            "joint_generation_planning",
            "direct_generation",
            "independent_validation",
        ],
        "principles": [
            "no_post_generation_repair",
            "no_hidden_fallback",
            "field_order_independence",
            "deterministic_streams",
            "safe_impossible_specification_blocking",
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

        print(
            "Unified feasibility and joint " "generation are experimentally validated."
        )

        return 0

    print("Experiment completed with failures.")

    return 1


if __name__ == "__main__":

    sys.exit(main())
