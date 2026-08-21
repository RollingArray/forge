"""
FORGE - Experiment 020-Q: Declarative Multi-Field Statistical Relationships
============================================================================

Stage:
    020-Q

Purpose:
    Validate multi-field statistical relationship graphs, correlation
    feasibility, deterministic generation, and achieved-vs-target validation.

Research question
-----------------
Can FORGE interpret multiple declarative statistical relationships as a
coherent correlation graph, determine whether the requested relationships
are mathematically feasible, and generate a dataset that satisfies the
feasible relationships?

Core principle
--------------
Pairwise statistical relationships cannot always be considered independently.

For example:

    A <-> B = +0.80
    A <-> C = +0.80
    B <-> C = -0.80

may not represent a valid correlation matrix.

Therefore FORGE must distinguish:

    valid vocabulary
          from
    feasible statistical specification

Architecture
------------
    Declarative relationships
            ↓
    Relationship graph
            ↓
    Correlation matrix
            ↓
    Feasibility analysis
            ↓
       ┌──────────────┐
       │              │
    FEASIBLE       INFEASIBLE
       │              │
       ↓              ↓
    Generate         BLOCK
       ↓
    Validate achieved relationships

Included
--------
    - Multi-field correlation graph
    - Positive relationships
    - Negative relationships
    - Zero relationships
    - Pearson correlation
    - Correlation matrix construction
    - Symmetry validation
    - Unit diagonal validation
    - Positive-semidefinite feasibility
    - Compatible relationship generation
    - Impossible relationship blocking
    - Field-order independence
    - Reproducibility
    - Seed sensitivity
    - No hidden fallback
    - Achieved-vs-target validation

Excluded
--------
    - Cross-entity statistical relationships
    - Time-series relationships
    - Empirical distributions
    - Causal inference
    - Conditional correlation
    - Production optimization
"""

from __future__ import annotations

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

OUTPUT_PATH = OUTPUT_DIR / "multi_field_statistical_relationship_results.json"

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
    relationship: str
    target_correlation: float
    method: str
    tolerance: float


# ============================================================================
# VOCABULARY
# ============================================================================

SUPPORTED_RELATIONSHIPS = {
    "CORRELATION",
    "TARGET_CORRELATION",
}

SUPPORTED_DIRECTIONS = {
    "POSITIVE",
    "NEGATIVE",
}

SUPPORTED_METHODS = {
    "PEARSON",
    "SPEARMAN",
}


# ============================================================================
# TEST ENTITY
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
    "RETENTION_SCORE": NumericField(
        name="RETENTION_SCORE",
        minimum=0.0,
        maximum=100.0,
    ),
}


# ============================================================================
# DETERMINISTIC RANDOM STREAM
# ============================================================================


def stable_seed(
    seed: int,
    relationship_name: str,
) -> int:

    material = (f"{seed}:{relationship_name}").encode("utf-8")

    value = 0

    for byte in material:
        value = ((value * 131) + byte) & 0xFFFFFFFFFFFFFFFF

    return value


def relationship_rng(
    seed: int,
    relationship_name: str,
) -> random.Random:

    return random.Random(
        stable_seed(
            seed,
            relationship_name,
        )
    )


# ============================================================================
# CORRELATION
# ============================================================================


def pearson_correlation(
    x: list[float],
    y: list[float],
) -> float:

    if len(x) != len(y):
        raise ValueError("Correlation vectors must " "have equal length.")

    if len(x) < 2:
        raise ValueError("At least two observations " "are required.")

    x_mean = mean(x)
    y_mean = mean(y)

    numerator = sum(
        (xi - x_mean) * (yi - y_mean)
        for xi, yi in zip(
            x,
            y,
        )
    )

    denominator_x = math.sqrt(sum((xi - x_mean) ** 2 for xi in x))

    denominator_y = math.sqrt(sum((yi - y_mean) ** 2 for yi in y))

    denominator = denominator_x * denominator_y

    if math.isclose(
        denominator,
        0.0,
    ):
        raise ValueError("Correlation undefined for " "constant field.")

    return numerator / denominator


# ============================================================================
# MATRIX HELPERS
# ============================================================================


def build_correlation_matrix(
    fields: list[str],
    relationships: list[StatisticalRelationship],
) -> list[list[float]]:

    index = {name: position for position, name in enumerate(fields)}

    size = len(fields)

    matrix = [[0.0 for _ in range(size)] for _ in range(size)]

    for position in range(size):
        matrix[position][position] = 1.0

    for relationship in relationships:

        source = index[relationship.source_field]

        target = index[relationship.target_field]

        value = relationship.target_correlation

        existing_forward = matrix[source][target]

        existing_reverse = matrix[target][source]

        if not math.isclose(
            existing_forward,
            0.0,
        ) and not math.isclose(
            existing_forward,
            value,
        ):
            raise ValueError(
                "Conflicting correlation "
                f"for {relationship.source_field} "
                f"<-> {relationship.target_field}"
            )

        if not math.isclose(
            existing_reverse,
            0.0,
        ) and not math.isclose(
            existing_reverse,
            value,
        ):
            raise ValueError(
                "Conflicting reverse correlation "
                f"for {relationship.target_field} "
                f"<-> {relationship.source_field}"
            )

        matrix[source][target] = value
        matrix[target][source] = value

    return matrix


def validate_matrix_shape(
    matrix: list[list[float]],
) -> bool:

    size = len(matrix)

    return all(len(row) == size for row in matrix)


def validate_matrix_symmetry(
    matrix: list[list[float]],
) -> bool:

    size = len(matrix)

    for i in range(size):

        for j in range(size):

            if not math.isclose(
                matrix[i][j],
                matrix[j][i],
                abs_tol=1e-10,
            ):
                return False

    return True


def validate_unit_diagonal(
    matrix: list[list[float]],
) -> bool:

    for index in range(len(matrix)):

        if not math.isclose(
            matrix[index][index],
            1.0,
            abs_tol=1e-10,
        ):
            return False

    return True


# ============================================================================
# POSITIVE SEMIDEFINITE CHECK
# ============================================================================
#
# We intentionally implement a small eigenvalue-free PSD check for this
# experiment using Sylvester-style principal minors for the small matrices
# under test.
#
# For a correlation matrix, all principal minors must be non-negative.
# ============================================================================


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

        minor = []

        for row in range(
            1,
            size,
        ):

            minor.append([matrix[row][c] for c in range(size) if c != column])

        sign = 1 if column % 2 == 0 else -1

        total += sign * matrix[0][column] * determinant(minor)

    return total


def principal_submatrix(
    matrix: list[list[float]],
    indices: list[int],
) -> list[list[float]]:

    return [[matrix[row][column] for column in indices] for row in indices]


def combinations(
    values: list[int],
    choose: int,
) -> list[list[int]]:

    if choose == 0:
        return [[]]

    if choose > len(values):
        return []

    result = []

    def build(
        start: int,
        current: list[int],
    ) -> None:

        if len(current) == choose:

            result.append(current.copy())

            return

        for index in range(
            start,
            len(values),
        ):

            current.append(values[index])

            build(
                index + 1,
                current,
            )

            current.pop()

    build(
        0,
        [],
    )

    return result


def is_positive_semidefinite(
    matrix: list[list[float]],
) -> bool:

    if not validate_matrix_shape(matrix):
        return False

    if not validate_matrix_symmetry(matrix):
        return False

    if not validate_unit_diagonal(matrix):
        return False

    size = len(matrix)

    indices = list(range(size))

    for dimension in range(
        1,
        size + 1,
    ):

        for subset in combinations(
            indices,
            dimension,
        ):

            minor = principal_submatrix(
                matrix,
                subset,
            )

            value = determinant(minor)

            if value < -1e-9:
                return False

    return True


# ============================================================================
# RELATIONSHIP VALIDATION
# ============================================================================


def validate_relationship(
    relationship: StatisticalRelationship,
    fields: dict[str, NumericField],
) -> None:

    if relationship.source_field not in fields:
        raise ValueError(f"Unknown source field: " f"{relationship.source_field}")

    if relationship.target_field not in fields:
        raise ValueError(f"Unknown target field: " f"{relationship.target_field}")

    if relationship.source_field == relationship.target_field:
        raise ValueError("A field cannot have a " "self-correlation relationship.")

    if relationship.relationship not in SUPPORTED_RELATIONSHIPS:
        raise ValueError(f"Unsupported relationship: " f"{relationship.relationship}")

    if relationship.method not in SUPPORTED_METHODS:
        raise ValueError(f"Unsupported method: " f"{relationship.method}")

    if not (-1.0 <= relationship.target_correlation <= 1.0):
        raise ValueError("Target correlation must " "be between -1 and 1.")

    if relationship.tolerance < 0:
        raise ValueError("Tolerance cannot be negative.")


def validate_relationship_graph(
    fields: dict[str, NumericField],
    relationships: list[StatisticalRelationship],
) -> list[list[float]]:

    for relationship in relationships:

        validate_relationship(
            relationship,
            fields,
        )

    field_names = sorted(fields.keys())

    matrix = build_correlation_matrix(
        field_names,
        relationships,
    )

    if not is_positive_semidefinite(matrix):
        raise ValueError(
            "Statistical relationship graph " "is mathematically infeasible."
        )

    return matrix


# ============================================================================
# GENERATION
# ============================================================================


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


def cholesky(
    matrix: list[list[float]],
) -> list[list[float]]:

    size = len(matrix)

    result = [[0.0 for _ in range(size)] for _ in range(size)]

    for i in range(size):

        for j in range(i + 1):

            value = matrix[i][j]

            for k in range(j):

                value -= result[i][k] * result[j][k]

            if i == j:

                if value < -1e-9:
                    raise ValueError(
                        "Correlation matrix " "is not positive " "semidefinite."
                    )

                result[i][j] = math.sqrt(
                    max(
                        0.0,
                        value,
                    )
                )

            else:

                if math.isclose(
                    result[j][j],
                    0.0,
                ):
                    result[i][j] = 0.0

                else:

                    result[i][j] = value / result[j][j]

    return result


def generate_multivariate_standard_normal(
    matrix: list[list[float]],
    count: int,
    seed: int,
) -> list[list[float]]:

    lower = cholesky(matrix)

    rng = random.Random(
        stable_seed(
            seed,
            "MULTIVARIATE",
        )
    )

    size = len(matrix)

    output = [[] for _ in range(size)]

    for _ in range(count):

        independent = standard_normal(
            rng,
            size,
        )

        correlated = []

        for row in range(size):

            value = sum(
                lower[row][column] * independent[column] for column in range(row + 1)
            )

            correlated.append(value)

        for index, value in enumerate(correlated):

            output[index].append(value)

    return output


def scale_to_range(
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


def generate_dataset(
    fields: dict[str, NumericField],
    relationships: list[StatisticalRelationship],
    count: int,
    seed: int,
) -> dict[str, list[float]]:

    matrix = validate_relationship_graph(
        fields,
        relationships,
    )

    field_names = sorted(fields.keys())

    generated = generate_multivariate_standard_normal(
        matrix,
        count,
        seed,
    )

    datasets = {}

    for index, field_name in enumerate(field_names):

        field = fields[field_name]

        datasets[field_name] = scale_to_range(
            generated[index],
            field.minimum,
            field.maximum,
        )

    return datasets


# ============================================================================
# RELATIONSHIP TEST SPECIFICATIONS
# ============================================================================


def compatible_relationships() -> list[StatisticalRelationship]:

    return [
        StatisticalRelationship(
            name="SCORE_TO_CREDIT",
            source_field="CUSTOMER_SCORE",
            target_field="CREDIT_LIMIT",
            relationship="TARGET_CORRELATION",
            target_correlation=0.75,
            method="PEARSON",
            tolerance=0.15,
        ),
        StatisticalRelationship(
            name="SCORE_TO_RISK",
            source_field="CUSTOMER_SCORE",
            target_field="RISK_SCORE",
            relationship="TARGET_CORRELATION",
            target_correlation=-0.60,
            method="PEARSON",
            tolerance=0.15,
        ),
    ]


def three_field_relationships() -> list[StatisticalRelationship]:

    return [
        StatisticalRelationship(
            name="SCORE_TO_CREDIT",
            source_field="CUSTOMER_SCORE",
            target_field="CREDIT_LIMIT",
            relationship="TARGET_CORRELATION",
            target_correlation=0.60,
            method="PEARSON",
            tolerance=0.18,
        ),
        StatisticalRelationship(
            name="SCORE_TO_RISK",
            source_field="CUSTOMER_SCORE",
            target_field="RISK_SCORE",
            relationship="TARGET_CORRELATION",
            target_correlation=-0.50,
            method="PEARSON",
            tolerance=0.18,
        ),
        StatisticalRelationship(
            name="SCORE_TO_RETENTION",
            source_field="CUSTOMER_SCORE",
            target_field="RETENTION_SCORE",
            relationship="TARGET_CORRELATION",
            target_correlation=0.50,
            method="PEARSON",
            tolerance=0.18,
        ),
    ]


def impossible_relationships() -> list[StatisticalRelationship]:

    return [
        StatisticalRelationship(
            name="A_TO_B",
            source_field="CUSTOMER_SCORE",
            target_field="CREDIT_LIMIT",
            relationship="TARGET_CORRELATION",
            target_correlation=0.90,
            method="PEARSON",
            tolerance=0.10,
        ),
        StatisticalRelationship(
            name="A_TO_C",
            source_field="CUSTOMER_SCORE",
            target_field="RISK_SCORE",
            relationship="TARGET_CORRELATION",
            target_correlation=0.90,
            method="PEARSON",
            tolerance=0.10,
        ),
        StatisticalRelationship(
            name="B_TO_C",
            source_field="CREDIT_LIMIT",
            target_field="RISK_SCORE",
            relationship="TARGET_CORRELATION",
            target_correlation=-0.90,
            method="PEARSON",
            tolerance=0.10,
        ),
    ]


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


def test_matrix_symmetry() -> bool:

    relationships = compatible_relationships()

    matrix = validate_relationship_graph(
        FIELDS,
        relationships,
    )

    return validate_matrix_symmetry(matrix) and validate_unit_diagonal(matrix)


def test_compatible_graph() -> bool:

    relationships = compatible_relationships()

    matrix = validate_relationship_graph(
        FIELDS,
        relationships,
    )

    return is_positive_semidefinite(matrix)


def test_three_field_generation() -> bool:

    fields = {
        "CUSTOMER_SCORE": FIELDS["CUSTOMER_SCORE"],
        "CREDIT_LIMIT": FIELDS["CREDIT_LIMIT"],
        "RISK_SCORE": FIELDS["RISK_SCORE"],
        "RETENTION_SCORE": FIELDS["RETENTION_SCORE"],
    }

    relationships = three_field_relationships()

    dataset = generate_dataset(
        fields,
        relationships,
        2000,
        MASTER_SEED,
    )

    score = dataset["CUSTOMER_SCORE"]

    credit = dataset["CREDIT_LIMIT"]

    risk = dataset["RISK_SCORE"]

    retention = dataset["RETENTION_SCORE"]

    score_credit = pearson_correlation(
        score,
        credit,
    )

    score_risk = pearson_correlation(
        score,
        risk,
    )

    score_retention = pearson_correlation(
        score,
        retention,
    )

    return (
        abs(score_credit - 0.60) <= 0.18
        and abs(score_risk + 0.50) <= 0.18
        and abs(score_retention - 0.50) <= 0.18
    )


def test_shared_source_relationships() -> bool:

    relationships = three_field_relationships()

    matrix = validate_relationship_graph(
        FIELDS,
        relationships,
    )

    # CUSTOMER_SCORE has three declared
    # relationships and must remain a valid
    # common source.
    score_index = sorted(FIELDS.keys()).index("CUSTOMER_SCORE")

    return matrix[score_index][score_index] == 1.0


def test_impossible_graph_blocking() -> bool:

    relationships = impossible_relationships()

    try:

        validate_relationship_graph(
            FIELDS,
            relationships,
        )

    except ValueError:

        return True

    return False


def test_field_order_independence() -> bool:

    relationships = compatible_relationships()

    fields_forward = {
        "CUSTOMER_SCORE": FIELDS["CUSTOMER_SCORE"],
        "CREDIT_LIMIT": FIELDS["CREDIT_LIMIT"],
        "RISK_SCORE": FIELDS["RISK_SCORE"],
        "RETENTION_SCORE": FIELDS["RETENTION_SCORE"],
    }

    fields_reverse = {
        "RETENTION_SCORE": FIELDS["RETENTION_SCORE"],
        "RISK_SCORE": FIELDS["RISK_SCORE"],
        "CREDIT_LIMIT": FIELDS["CREDIT_LIMIT"],
        "CUSTOMER_SCORE": FIELDS["CUSTOMER_SCORE"],
    }

    first = generate_dataset(
        fields_forward,
        relationships,
        500,
        MASTER_SEED,
    )

    second = generate_dataset(
        fields_reverse,
        relationships,
        500,
        MASTER_SEED,
    )

    return first == second


def test_reproducibility() -> bool:

    relationships = compatible_relationships()

    first = generate_dataset(
        FIELDS,
        relationships,
        500,
        MASTER_SEED,
    )

    second = generate_dataset(
        FIELDS,
        relationships,
        500,
        MASTER_SEED,
    )

    return first == second


def test_seed_sensitivity() -> bool:

    relationships = compatible_relationships()

    first = generate_dataset(
        FIELDS,
        relationships,
        500,
        42,
    )

    second = generate_dataset(
        FIELDS,
        relationships,
        500,
        43,
    )

    return first != second


def test_no_hidden_fallback() -> bool:

    relationships = impossible_relationships()

    try:

        generate_dataset(
            FIELDS,
            relationships,
            500,
            MASTER_SEED,
        )

    except ValueError:

        return True

    return False


def test_unknown_field_blocking() -> bool:

    relationship = StatisticalRelationship(
        name="UNKNOWN",
        source_field="CUSTOMER_SCORE",
        target_field="UNKNOWN_FIELD",
        relationship="TARGET_CORRELATION",
        target_correlation=0.50,
        method="PEARSON",
        tolerance=0.15,
    )

    try:

        validate_relationship_graph(
            FIELDS,
            [relationship],
        )

    except ValueError:

        return True

    return False


def test_duplicate_conflict_blocking() -> bool:

    relationships = [
        StatisticalRelationship(
            name="RELATIONSHIP_A",
            source_field="CUSTOMER_SCORE",
            target_field="CREDIT_LIMIT",
            relationship="TARGET_CORRELATION",
            target_correlation=0.50,
            method="PEARSON",
            tolerance=0.15,
        ),
        StatisticalRelationship(
            name="RELATIONSHIP_B",
            source_field="CUSTOMER_SCORE",
            target_field="CREDIT_LIMIT",
            relationship="TARGET_CORRELATION",
            target_correlation=0.80,
            method="PEARSON",
            tolerance=0.15,
        ),
    ]

    try:

        validate_relationship_graph(
            FIELDS,
            relationships,
        )

    except ValueError:

        return True

    return False


def test_matrix_positive_semidefinite() -> bool:

    relationships = compatible_relationships()

    matrix = validate_relationship_graph(
        FIELDS,
        relationships,
    )

    return is_positive_semidefinite(matrix)


def test_relationship_count() -> bool:

    relationships = three_field_relationships()

    return len(relationships) == 3


def test_achieved_relationship_validation() -> bool:

    relationships = three_field_relationships()

    dataset = generate_dataset(
        FIELDS,
        relationships,
        2000,
        MASTER_SEED,
    )

    checks = []

    for relationship in relationships:

        observed = pearson_correlation(
            dataset[relationship.source_field],
            dataset[relationship.target_field],
        )

        checks.append(
            abs(observed - relationship.target_correlation) <= relationship.tolerance
        )

    return all(checks)


def test_relationship_direction() -> bool:

    relationships = three_field_relationships()

    dataset = generate_dataset(
        FIELDS,
        relationships,
        2000,
        MASTER_SEED,
    )

    score = dataset["CUSTOMER_SCORE"]

    credit = dataset["CREDIT_LIMIT"]

    risk = dataset["RISK_SCORE"]

    retention = dataset["RETENTION_SCORE"]

    return (
        pearson_correlation(
            score,
            credit,
        )
        > 0
        and pearson_correlation(
            score,
            risk,
        )
        < 0
        and pearson_correlation(
            score,
            retention,
        )
        > 0
    )


def test_zero_relationship() -> bool:

    relationships = [
        StatisticalRelationship(
            name="ZERO_RELATIONSHIP",
            source_field="CUSTOMER_SCORE",
            target_field="CREDIT_LIMIT",
            relationship="TARGET_CORRELATION",
            target_correlation=0.0,
            method="PEARSON",
            tolerance=0.15,
        ),
    ]

    dataset = generate_dataset(
        FIELDS,
        relationships,
        2000,
        MASTER_SEED,
    )

    observed = pearson_correlation(
        dataset["CUSTOMER_SCORE"],
        dataset["CREDIT_LIMIT"],
    )

    return abs(observed) <= 0.15


# ============================================================================
# MAIN
# ============================================================================


def main() -> int:

    print()

    print("=" * 70)

    print(
        "FORGE - Experiment 020-Q: " "Declarative Multi-Field Statistical Relationships"
    )

    print("=" * 70)

    print("Experiment:     " "020_declarative_generation_specification")

    print("Stage:          020-Q")

    print("Purpose:        " "Multi-field statistical relationship graphs")

    print(f"Random seed:    {MASTER_SEED}")

    print()

    print("Statistical relationship graph:")

    print("  Declarative relationships")

    print("       ↓")

    print("  Correlation graph")

    print("       ↓")

    print("  Correlation matrix")

    print("       ↓")

    print("  Feasibility analysis")

    print("       ↓")

    print("  Multivariate generation")

    print("       ↓")

    print("  Achieved relationship validation")

    print()

    print("Controlled vocabulary:")

    print("  Relationships:")

    for value in sorted(SUPPORTED_RELATIONSHIPS):
        print(f"    {value}")

    print("  Methods:")

    for value in sorted(SUPPORTED_METHODS):
        print(f"    {value}")

    print()

    tests = [
        (
            "Correlation matrix symmetry",
            test_matrix_symmetry,
        ),
        (
            "Compatible graph feasibility",
            test_compatible_graph,
        ),
        (
            "Three-field generation",
            test_three_field_generation,
        ),
        (
            "Shared-source relationships",
            test_shared_source_relationships,
        ),
        (
            "Impossible graph blocking",
            test_impossible_graph_blocking,
        ),
        (
            "Field-order independence",
            test_field_order_independence,
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
            "No hidden fallback",
            test_no_hidden_fallback,
        ),
        (
            "Unknown field blocking",
            test_unknown_field_blocking,
        ),
        (
            "Duplicate conflict blocking",
            test_duplicate_conflict_blocking,
        ),
        (
            "Positive-semidefinite validation",
            test_matrix_positive_semidefinite,
        ),
        (
            "Relationship count",
            test_relationship_count,
        ),
        (
            "Achieved relationship validation",
            test_achieved_relationship_validation,
        ),
        (
            "Relationship direction",
            test_relationship_direction,
        ),
        (
            "Zero relationship",
            test_zero_relationship,
        ),
    ]

    print("Multi-field statistical relationship validation:")

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

    # ------------------------------------------------------------------
    # Representative correlation matrix
    # ------------------------------------------------------------------

    compatible = compatible_relationships()

    matrix_fields = sorted(FIELDS.keys())

    matrix = build_correlation_matrix(
        matrix_fields,
        compatible,
    )

    print("Correlation matrix:")

    print("  Fields:")

    print("    " + " ".join(f"{field:>18}" for field in matrix_fields))

    for field, row in zip(
        matrix_fields,
        matrix,
    ):

        print(f"    {field:<18}" + " ".join(f"{value:>18.3f}" for value in row))

    print()

    print("Correlation matrix feasibility:")

    print(
        f"  Positive semidefinite: "
        f"{'PASS' if is_positive_semidefinite(matrix) else 'FAIL'}"
    )

    print()

    print("Experiment result:")

    print(f"  Matrix symmetry:          " f"{results[0]['status']}")

    print(f"  Graph feasibility:        " f"{results[1]['status']}")

    print(f"  Multi-field generation:   " f"{results[2]['status']}")

    print(f"  Impossible graph safety:  " f"{results[4]['status']}")

    print(f"  Reproducibility:          " f"{results[6]['status']}")

    print(f"  Seed sensitivity:         " f"{results[7]['status']}")

    print(f"  Relationship validation:  " f"{results[13]['status']}")

    configuration_safety = (
        "PASS"
        if all(result["status"] == "PASS" for result in results[8:12])
        else "FAIL"
    )

    print(f"  Configuration safety:     " f"{configuration_safety}")

    print()

    print(f"  Tests passed:              " f"{passed}/{total}")

    print(f"  Overall:                   " f"{'PASS' if overall else 'FAIL'}")

    # ------------------------------------------------------------------
    # Persist
    # ------------------------------------------------------------------

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    output = {
        "experiment": ("020_declarative_generation_specification"),
        "stage": "020-Q",
        "purpose": ("Declarative multi-field " "statistical relationships"),
        "seed": MASTER_SEED,
        "fields": matrix_fields,
        "relationships": [
            {
                "name": relationship.name,
                "source_field": relationship.source_field,
                "target_field": relationship.target_field,
                "target_correlation": relationship.target_correlation,
                "method": relationship.method,
                "tolerance": relationship.tolerance,
            }
            for relationship in compatible
        ],
        "correlation_matrix": matrix,
        "matrix_positive_semidefinite": is_positive_semidefinite(matrix),
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
            "Multi-field statistical " "relationships are " "experimentally validated."
        )

        return 0

    print("Experiment completed with failures.")

    return 1


if __name__ == "__main__":

    sys.exit(main())
