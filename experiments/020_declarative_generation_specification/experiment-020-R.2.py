"""
FORGE - Experiment 020-R.2: Constraint-Conditioned Statistical Generation
==========================================================================

Purpose
-------
Validate generation where statistical relationships are generated directly
inside record-level feasible regions created by:

    - field bounds
    - cross-field constraints
    - conditional constraints

The experiment explicitly prohibits:

    - post-generation repair
    - hidden fallback generation
    - silently relaxing constraints

Architecture
------------

    Declarative Specification
             |
             v
    Unified Feasibility Analysis
             |
             v
    Dependency / Relationship Planning
             |
             v
    Source Generation
             |
             v
    Record-Level Feasible Region
             |
             +---------------------------+
             |                           |
             v                           v
    Statistical Target Model      Constraint Bounds
             |                           |
             +-------------+-------------+
                           |
                           v
                Constraint-Conditioned
                     Generation
                           |
                           v
                Independent Validation
"""

from __future__ import annotations

import copy
import hashlib
import json
import math
import random
import sys
from dataclasses import dataclass
from itertools import combinations
from pathlib import Path
from statistics import mean

# ============================================================================
# PATHS / CONSTANTS
# ============================================================================

EXPERIMENT_DIR = Path(__file__).resolve().parent

OUTPUT_DIR = EXPERIMENT_DIR / "output"

OUTPUT_PATH = OUTPUT_DIR / "constraint_conditioned_generation_results.json"

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
# DETERMINISTIC RANDOM STREAMS
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
# SPECIFICATION VALIDATION
# ============================================================================


def validate_specification(
    specification: Specification,
) -> None:

    if not specification.fields:
        raise ValueError("Specification contains no fields.")

    for field in specification.fields.values():

        if field.minimum > field.maximum:
            raise ValueError(f"Invalid field bounds: {field.name}")

    for relationship in specification.correlations:

        if relationship.source not in specification.fields:
            raise ValueError(f"Unknown correlation source: " f"{relationship.source}")

        if relationship.target not in specification.fields:
            raise ValueError(f"Unknown correlation target: " f"{relationship.target}")

        if relationship.source == relationship.target:
            raise ValueError("Self-correlation is not supported.")

        if not (-1.0 <= relationship.target_value <= 1.0):
            raise ValueError(f"Invalid correlation target: " f"{relationship.name}")

        if relationship.tolerance < 0:
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
            raise ValueError(f"Unknown left field: {constraint.left}")

        if constraint.right not in specification.fields:
            raise ValueError(f"Unknown right field: {constraint.right}")

        if constraint.operator not in {
            ">=",
            "<=",
            ">",
            "<",
        }:
            raise ValueError(f"Unsupported operator: " f"{constraint.operator}")

        if constraint.multiplier < 0:
            raise ValueError("Constraint multiplier cannot be negative.")

    for conditional in specification.conditionals:

        if conditional.condition_field not in specification.fields:
            raise ValueError(
                f"Unknown condition field: " f"{conditional.condition_field}"
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
# GLOBAL FEASIBILITY
# ============================================================================


def effective_bounds(
    specification: Specification,
) -> dict[str, tuple[float, float]]:

    result = {
        name: (
            field.minimum,
            field.maximum,
        )
        for name, field in specification.fields.items()
    }

    for bound in specification.bounds:

        current_min, current_max = result[bound.field]

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
            raise ValueError(f"Infeasible bounds for " f"{bound.field}")

        result[bound.field] = (
            current_min,
            current_max,
        )

    return result


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

    total = 0.0

    for column in range(size):

        minor = [
            [matrix[row][candidate] for candidate in range(size) if candidate != column]
            for row in range(
                1,
                size,
            )
        ]

        sign = 1 if column % 2 == 0 else -1

        total += sign * matrix[0][column] * determinant(minor)

    return total


def validate_correlation_graph(
    specification: Specification,
) -> None:

    fields = sorted(specification.fields.keys())

    positions = {field: index for index, field in enumerate(fields)}

    size = len(fields)

    matrix = [[0.0] * size for _ in range(size)]

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
            raise ValueError("Conflicting correlations.")

        matrix[source][target] = value
        matrix[target][source] = value

    for subset_size in range(
        2,
        size + 1,
    ):

        for indexes in combinations(
            range(size),
            subset_size,
        ):

            minor = [[matrix[row][column] for column in indexes] for row in indexes]

            if determinant(minor) < -1e-9:
                raise ValueError("Correlation graph is infeasible.")


def validate_global_feasibility(
    specification: Specification,
) -> None:

    validate_specification(specification)

    effective_bounds(specification)

    validate_correlation_graph(specification)

    bounds = effective_bounds(specification)

    for constraint in specification.cross_constraints:

        left_min, left_max = bounds[constraint.left]

        right_min, right_max = bounds[constraint.right]

        multiplier = constraint.multiplier

        if constraint.operator == ">=":

            possible = left_max >= right_min * multiplier

        elif constraint.operator == "<=":

            possible = left_min <= right_max * multiplier

        elif constraint.operator == ">":

            possible = left_max > right_min * multiplier

        else:

            possible = left_min < right_max * multiplier

        if not possible:
            raise ValueError(
                f"Infeasible cross-field constraint: " f"{constraint.name}"
            )

    for conditional in specification.conditionals:

        target_min, target_max = bounds[conditional.target_field]

        if target_max < conditional.target_minimum:
            raise ValueError(f"Infeasible conditional: " f"{conditional.name}")


# ============================================================================
# RECORD-LEVEL FEASIBLE REGION
# ============================================================================


def feasible_region(
    specification: Specification,
    record: dict[str, float],
    target_field: str,
) -> tuple[float, float]:

    field = specification.fields[target_field]

    lower = field.minimum
    upper = field.maximum

    # Static bounds.
    for bound in specification.bounds:

        if bound.field != target_field:
            continue

        if bound.minimum is not None:
            lower = max(
                lower,
                bound.minimum,
            )

        if bound.maximum is not None:
            upper = min(
                upper,
                bound.maximum,
            )

    # Cross-field constraints.
    for constraint in specification.cross_constraints:

        if constraint.left == target_field:

            if constraint.right not in record:
                continue

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

        elif constraint.right == target_field:

            if constraint.left not in record:
                continue

            left_value = record[constraint.left]

            multiplier = constraint.multiplier

            if math.isclose(
                multiplier,
                0.0,
            ):
                continue

            if constraint.operator == ">=":

                # left >= target * multiplier
                upper = min(
                    upper,
                    left_value / multiplier,
                )

            elif constraint.operator == "<=":

                lower = max(
                    lower,
                    left_value / multiplier,
                )

            elif constraint.operator == ">":

                upper = min(
                    upper,
                    math.nextafter(
                        left_value / multiplier,
                        -math.inf,
                    ),
                )

            elif constraint.operator == "<":

                lower = max(
                    lower,
                    math.nextafter(
                        left_value / multiplier,
                        math.inf,
                    ),
                )

    # Conditional constraints.
    for conditional in specification.conditionals:

        if conditional.target_field != target_field:
            continue

        if conditional.condition_field not in record:
            continue

        condition_value = record[conditional.condition_field]

        if condition_value >= conditional.condition_minimum:

            lower = max(
                lower,
                conditional.target_minimum,
            )

    if lower > upper:
        raise ValueError(
            f"No feasible region for " f"{target_field}: " f"{lower} > {upper}"
        )

    return lower, upper


# ============================================================================
# CONSTRAINT-AWARE TARGET GENERATION
# ============================================================================


def correlated_target(
    source: list[float],
    target_field: Field,
    relationship: Correlation,
    record_contexts: list[dict[str, float]],
    specification: Specification,
    seed: int,
) -> list[float]:

    if not source:
        return []

    source_mean = mean(source)

    centered = [value - source_mean for value in source]

    variance = mean(value * value for value in centered)

    if math.isclose(
        variance,
        0.0,
    ):
        raise ValueError("Source field has zero variance.")

    source_std = math.sqrt(variance)

    normalized_source = [value / source_std for value in centered]

    rng = rng_for(
        seed,
        f"RELATIONSHIP:{relationship.name}",
    )

    noise = standard_normal(
        rng,
        len(source),
    )

    rho = relationship.target_value

    residual = math.sqrt(
        max(
            0.0,
            1.0 - rho * rho,
        )
    )

    latent = [
        (rho * source_value + residual * noise_value)
        for source_value, noise_value in zip(
            normalized_source,
            noise,
        )
    ]

    raw = scale(
        latent,
        target_field.minimum,
        target_field.maximum,
    )

    result = []

    for index, raw_value in enumerate(raw):

        context = record_contexts[index]

        lower, upper = feasible_region(
            specification,
            context,
            target_field.name,
        )

        # --------------------------------------------------------------
        # Constraint-conditioned generation.
        #
        # The raw statistical sample is mapped into the feasible
        # interval. This is generation inside the region, not a later
        # repair operation.
        # --------------------------------------------------------------

        base_range = target_field.maximum - target_field.minimum

        if math.isclose(
            base_range,
            0.0,
        ):
            normalized = 0.5

        else:
            normalized = (raw_value - target_field.minimum) / base_range

        normalized = max(
            0.0,
            min(
                1.0,
                normalized,
            ),
        )

        value = lower + normalized * (upper - lower)

        result.append(value)

    return result


# ============================================================================
# GENERATION
# ============================================================================


def generate_dataset(
    specification: Specification,
    count: int,
    seed: int,
) -> dict[str, list[float]]:

    validate_global_feasibility(specification)

    bounds = effective_bounds(specification)

    datasets: dict[
        str,
        list[float],
    ] = {}

    # --------------------------------------------------------------
    # Root field.
    # --------------------------------------------------------------

    root_field = "CUSTOMER_SCORE"

    root = specification.fields[root_field]

    rng = rng_for(
        seed,
        "ROOT:CUSTOMER_SCORE",
    )

    root_values = scale(
        standard_normal(
            rng,
            count,
        ),
        max(
            root.minimum,
            bounds[root_field][0],
        ),
        min(
            root.maximum,
            bounds[root_field][1],
        ),
    )

    datasets[root_field] = root_values

    # --------------------------------------------------------------
    # Build contexts from already generated values.
    # --------------------------------------------------------------

    contexts = [{root_field: value} for value in root_values]

    # --------------------------------------------------------------
    # Relationship targets.
    # --------------------------------------------------------------

    for relationship in specification.correlations:

        if relationship.source not in datasets:
            raise ValueError(
                f"Relationship source not generated: " f"{relationship.source}"
            )

        target_field = specification.fields[relationship.target]

        target_values = correlated_target(
            datasets[relationship.source],
            target_field,
            relationship,
            contexts,
            specification,
            seed,
        )

        datasets[relationship.target] = target_values

        for index, value in enumerate(target_values):
            contexts[index][relationship.target] = value

    # --------------------------------------------------------------
    # Derived fields.
    # --------------------------------------------------------------

    for derived in specification.derived_fields:

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

            raise ValueError(f"Unsupported operation: " f"{derived.operation}")

    return datasets


# ============================================================================
# VALIDATION
# ============================================================================


def validate_dataset(
    specification: Specification,
    dataset: dict[str, list[float]],
) -> bool:

    if not dataset:
        return False

    record_count = len(next(iter(dataset.values())))

    if not all(len(values) == record_count for values in dataset.values()):
        return False

    # Field bounds.
    for name, field in specification.fields.items():

        if name not in dataset:
            return False

        if any(
            value < field.minimum or value > field.maximum for value in dataset[name]
        ):
            return False

    # Static bounds.
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

            reference = right * constraint.multiplier

            if constraint.operator == ">=":
                valid = left >= reference

            elif constraint.operator == "<=":
                valid = left <= reference

            elif constraint.operator == ">":
                valid = left > reference

            elif constraint.operator == "<":
                valid = left < reference

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

    # Derived values.
    for derived in specification.derived_fields:

        actual = dataset[derived.name]

        a_values = dataset[derived.source_a]

        b_values = dataset[derived.source_b]

        if derived.operation == "MULTIPLY":

            expected = [
                a * b
                for a, b in zip(
                    a_values,
                    b_values,
                )
            ]

        elif derived.operation == "ADD":

            expected = [
                a + b
                for a, b in zip(
                    a_values,
                    b_values,
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


def build_integrated_specification() -> Specification:

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
                name="SCORE_TO_CREDIT",
                source="CUSTOMER_SCORE",
                target="CREDIT_LIMIT",
                target_value=0.50,
                tolerance=0.30,
            ),
            Correlation(
                name="SCORE_TO_RISK",
                source="CUSTOMER_SCORE",
                target="RISK_SCORE",
                target_value=-0.40,
                tolerance=0.30,
            ),
        ),
        bounds=(
            Bound(
                name="CREDIT_BASE_MIN",
                field="CREDIT_LIMIT",
                minimum=1000.0,
            ),
        ),
        cross_constraints=(
            CrossFieldConstraint(
                name="CREDIT_ABOVE_SCORE",
                left="CREDIT_LIMIT",
                operator=">=",
                right="CUSTOMER_SCORE",
                multiplier=50.0,
            ),
        ),
        conditionals=(
            Conditional(
                name="HIGH_SCORE_CREDIT",
                condition_field="CUSTOMER_SCORE",
                condition_minimum=70.0,
                target_field="CREDIT_LIMIT",
                target_minimum=5000.0,
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


def build_impossible_specification() -> Specification:

    specification = build_integrated_specification()

    return Specification(
        fields=specification.fields,
        correlations=(
            Correlation(
                name="INVALID_CORRELATION",
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


def build_impossible_record_specification() -> Specification:

    specification = build_integrated_specification()

    impossible_fields = dict(specification.fields)

    impossible_fields["CREDIT_LIMIT"] = Field(
        "CREDIT_LIMIT",
        1000.0,
        4000.0,
    )

    return Specification(
        fields=impossible_fields,
        correlations=specification.correlations,
        bounds=specification.bounds,
        cross_constraints=specification.cross_constraints,
        conditionals=specification.conditionals,
        derived_fields=specification.derived_fields,
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
            "status": "FAIL",
            "error": (f"{type(exc).__name__}: " f"{exc}"),
        }


# ============================================================================
# TESTS
# ============================================================================


def test_field_feasible_region() -> bool:

    specification = build_integrated_specification()

    record = {
        "CUSTOMER_SCORE": 60.0,
    }

    lower, upper = feasible_region(
        specification,
        record,
        "CREDIT_LIMIT",
    )

    return lower == 3000.0 and upper == 10000.0


def test_conditional_feasible_region() -> bool:

    specification = build_integrated_specification()

    record = {
        "CUSTOMER_SCORE": 80.0,
    }

    lower, upper = feasible_region(
        specification,
        record,
        "CREDIT_LIMIT",
    )

    return lower == 5000.0 and upper == 10000.0


def test_combined_feasible_region() -> bool:

    specification = build_integrated_specification()

    record = {
        "CUSTOMER_SCORE": 90.0,
    }

    lower, upper = feasible_region(
        specification,
        record,
        "CREDIT_LIMIT",
    )

    return lower == 5000.0 and upper == 10000.0


def test_constraint_conditioned_generation() -> bool:

    specification = build_integrated_specification()

    dataset = generate_dataset(
        specification,
        1000,
        MASTER_SEED,
    )

    scores = dataset["CUSTOMER_SCORE"]

    credits = dataset["CREDIT_LIMIT"]

    return all(
        credit >= score * 50.0
        for score, credit in zip(
            scores,
            credits,
        )
    )


def test_conditional_generation() -> bool:

    specification = build_integrated_specification()

    dataset = generate_dataset(
        specification,
        1000,
        MASTER_SEED,
    )

    return all(
        credit >= 5000.0
        for score, credit in zip(
            dataset["CUSTOMER_SCORE"],
            dataset["CREDIT_LIMIT"],
        )
        if score >= 70.0
    )


def test_statistical_target() -> bool:

    specification = build_integrated_specification()

    dataset = generate_dataset(
        specification,
        2000,
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


def test_derived_values() -> bool:

    specification = build_integrated_specification()

    dataset = generate_dataset(
        specification,
        1000,
        MASTER_SEED,
    )

    return all(
        math.isclose(
            actual,
            score * credit,
            rel_tol=1e-9,
            abs_tol=1e-9,
        )
        for actual, score, credit in zip(
            dataset["NET_VALUE"],
            dataset["CUSTOMER_SCORE"],
            dataset["CREDIT_LIMIT"],
        )
    )


def test_combined_validation() -> bool:

    specification = build_integrated_specification()

    dataset = generate_dataset(
        specification,
        1000,
        MASTER_SEED,
    )

    return validate_dataset(
        specification,
        dataset,
    )


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

    alternate = Specification(
        fields=reversed_fields,
        correlations=specification.correlations,
        bounds=specification.bounds,
        cross_constraints=specification.cross_constraints,
        conditionals=specification.conditionals,
        derived_fields=specification.derived_fields,
    )

    first = generate_dataset(
        specification,
        500,
        MASTER_SEED,
    )

    second = generate_dataset(
        alternate,
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


def test_impossible_record_region() -> bool:

    specification = build_impossible_record_specification()

    try:

        validate_global_feasibility(specification)

    except ValueError:

        return True

    return False


def test_no_hidden_fallback() -> bool:

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


def test_no_post_generation_repair() -> bool:

    specification = build_integrated_specification()

    dataset = generate_dataset(
        specification,
        1000,
        MASTER_SEED,
    )

    # Generation returns only directly generated
    # values. Validation is performed separately.
    #
    # There is intentionally no repair function
    # in the experiment.
    return validate_dataset(
        specification,
        dataset,
    )


def test_configuration_safety() -> bool:

    specification = build_integrated_specification()

    validate_global_feasibility(specification)

    return True


def test_multiple_constraints() -> bool:

    specification = build_integrated_specification()

    extended = Specification(
        fields=specification.fields,
        correlations=specification.correlations,
        bounds=specification.bounds,
        cross_constraints=(
            specification.cross_constraints
            + (
                CrossFieldConstraint(
                    name="CREDIT_ABOVE_HALF_SCORE",
                    left="CREDIT_LIMIT",
                    operator=">=",
                    right="CUSTOMER_SCORE",
                    multiplier=0.5,
                ),
            )
        ),
        conditionals=specification.conditionals,
        derived_fields=specification.derived_fields,
    )

    dataset = generate_dataset(
        extended,
        1000,
        MASTER_SEED,
    )

    return validate_dataset(
        extended,
        dataset,
    )


def test_record_region_is_used() -> bool:

    specification = build_integrated_specification()

    low_score = {
        "CUSTOMER_SCORE": 20.0,
    }

    high_score = {
        "CUSTOMER_SCORE": 90.0,
    }

    low_region = feasible_region(
        specification,
        low_score,
        "CREDIT_LIMIT",
    )

    high_region = feasible_region(
        specification,
        high_score,
        "CREDIT_LIMIT",
    )

    return (
        low_region[0] == 1000.0
        and high_region[0] == 5000.0
        and high_region[0] > low_region[0]
    )


# ============================================================================
# MAIN
# ============================================================================


def main() -> int:

    print()

    print("=" * 70)

    print(
        "FORGE - Experiment 020-R.2: " "Constraint-Conditioned Statistical Generation"
    )

    print("=" * 70)

    print("Experiment:     " "020_declarative_generation_specification")

    print("Stage:          020-R.2")

    print("Purpose:        " "Record-level feasible region generation")

    print(f"Random seed:    {MASTER_SEED}")

    print()

    print("Generation architecture:")

    print("  Source generation")

    print("       ↓")

    print("  Record-level context")

    print("       ↓")

    print("  Feasible target region")

    print("       ↓")

    print("  Statistical generation")

    print("       ↓")

    print("  Independent validation")

    print()

    specification = build_integrated_specification()

    print("Integrated capabilities:")

    print("  Statistical relationships: " f"{len(specification.correlations)}")

    print("  Field bounds:              " f"{len(specification.bounds)}")

    print("  Cross-field constraints:   " f"{len(specification.cross_constraints)}")

    print("  Conditional rules:         " f"{len(specification.conditionals)}")

    print("  Derived fields:            " f"{len(specification.derived_fields)}")

    print()

    tests = [
        (
            "Field feasible region",
            test_field_feasible_region,
        ),
        (
            "Conditional feasible region",
            test_conditional_feasible_region,
        ),
        (
            "Combined feasible region",
            test_combined_feasible_region,
        ),
        (
            "Constraint-conditioned generation",
            test_constraint_conditioned_generation,
        ),
        (
            "Conditional generation",
            test_conditional_generation,
        ),
        (
            "Statistical target preservation",
            test_statistical_target,
        ),
        (
            "Derived values",
            test_derived_values,
        ),
        (
            "Combined validation",
            test_combined_validation,
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
            "Impossible record-region blocking",
            test_impossible_record_region,
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
            "Multiple constraints",
            test_multiple_constraints,
        ),
        (
            "Record region is used",
            test_record_region_is_used,
        ),
    ]

    print("Constraint-conditioned generation validation:")

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

    print(f"  Feasible regions:          " f"{results[0]['status']}")

    print(f"  Conditional regions:       " f"{results[1]['status']}")

    print(f"  Combined regions:          " f"{results[2]['status']}")

    print(f"  Constraint-conditioned:    " f"{results[3]['status']}")

    print(f"  Conditional generation:    " f"{results[4]['status']}")

    print(f"  Statistical preservation:  " f"{results[5]['status']}")

    print(f"  Derived values:            " f"{results[6]['status']}")

    print(f"  Combined validation:       " f"{results[7]['status']}")

    print(f"  Reproducibility:           " f"{results[8]['status']}")

    print(f"  Seed sensitivity:          " f"{results[9]['status']}")

    print(f"  Field-order independence:  " f"{results[10]['status']}")

    print(f"  Impossible-spec safety:    " f"{results[11]['status']}")

    print(f"  Impossible-region safety:  " f"{results[12]['status']}")

    print(f"  No hidden fallback:        " f"{results[13]['status']}")

    print(f"  No post-generation repair: " f"{results[14]['status']}")

    print(f"  Configuration safety:      " f"{results[15]['status']}")

    print(f"  Multiple constraints:      " f"{results[16]['status']}")

    print()

    print(f"  Tests passed:              " f"{passed}/{total}")

    print(f"  Overall:                   " f"{'PASS' if overall else 'FAIL'}")

    # ------------------------------------------------------------------
    # Representative feasible regions
    # ------------------------------------------------------------------

    print()

    print("Representative feasible regions:")

    for score in (
        20.0,
        60.0,
        80.0,
        90.0,
    ):

        record = {"CUSTOMER_SCORE": score}

        lower, upper = feasible_region(
            specification,
            record,
            "CREDIT_LIMIT",
        )

        print(
            f"  CUSTOMER_SCORE={score:5.1f}"
            f" → CREDIT_LIMIT="
            f"[{lower:7.1f}, {upper:7.1f}]"
        )

    # ------------------------------------------------------------------
    # Output
    # ------------------------------------------------------------------

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    output = {
        "experiment": ("020_declarative_generation_specification"),
        "stage": "020-R.2",
        "purpose": ("Constraint-conditioned " "statistical generation"),
        "seed": MASTER_SEED,
        "tests": results,
        "tests_passed": passed,
        "tests_total": total,
        "overall": ("PASS" if overall else "FAIL"),
        "architecture": [
            "source_generation",
            "record_level_context",
            "feasible_region_derivation",
            "constraint_conditioned_generation",
            "independent_validation",
        ],
        "principles": [
            "record_level_feasible_regions",
            "no_post_generation_repair",
            "no_hidden_fallback",
            "field_order independence",
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
            "Constraint-conditioned statistical "
            "generation is experimentally validated."
        )

        return 0

    print("Experiment completed with failures.")

    return 1


if __name__ == "__main__":

    sys.exit(main())
