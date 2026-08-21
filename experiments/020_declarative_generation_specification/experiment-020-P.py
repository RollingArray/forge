"""
FORGE - Experiment 020-P: Declarative Statistical Relationships
================================================================

Stage:
    020-P

Purpose:
    Validate declarative statistical relationship generation.

Research question
-----------------
Can FORGE generate fields with an explicitly declared statistical
relationship while preserving the requested field distributions,
determinism, seed sensitivity, and field-order independence?

Experiment focus
----------------
    CORRELATION
    TARGET_CORRELATION
    POSITIVE
    NEGATIVE
    PEARSON
    SPEARMAN

Core principle
--------------
A declared statistical relationship is a generation requirement,
not merely a post-generation validation metric.

Example:

    CUSTOMER_SCORE
          |
          | TARGET_CORRELATION
          | POSITIVE
          | PEARSON
          | target = 0.75
          v
    CREDIT_LIMIT

The generator should attempt to construct the relationship and
the validator should measure the achieved relationship.

Important distinction
---------------------
This experiment does NOT require exact correlation.

Statistical generation is probabilistic and finite-population
effects mean that:

    target correlation != observed correlation

The experiment therefore validates that the achieved relationship
falls within an explicitly declared tolerance.

Safety principles
-----------------
    - Correlation target must be explicit.
    - Correlation method must be explicit.
    - Direction must be explicit.
    - Invalid targets must be rejected.
    - Unsupported methods must be rejected.
    - No hidden independent-generation fallback.
    - Same seed must reproduce the same dataset.
    - Different seeds must produce a different realization.
    - Field declaration order must not affect results.

Included
--------
    - Independent relationship
    - Positive target correlation
    - Negative target correlation
    - Pearson correlation
    - Spearman correlation
    - Target tolerance
    - Parameter validation
    - Determinism
    - Seed sensitivity
    - Field-order independence
    - Relationship validation
    - Capability safety

Excluded
--------
    - Cross-entity statistical correlation
    - Empirical distributions
    - Mixture distributions
    - Time-series correlation
    - Causal inference
    - LLM interpretation
    - Production statistical optimization
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

OUTPUT_PATH = OUTPUT_DIR / "statistical_relationship_results.json"

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
# DETERMINISTIC RANDOM STREAM
# ============================================================================


def stable_seed(
    seed: int,
    relationship_name: str,
    field_name: str,
) -> int:

    material = (f"{seed}:" f"{relationship_name}:" f"{field_name}").encode("utf-8")

    digest = hashlib.sha256(material).digest()

    return int.from_bytes(
        digest[:8],
        byteorder="big",
        signed=False,
    )


def field_rng(
    seed: int,
    relationship_name: str,
    field_name: str,
) -> random.Random:

    return random.Random(
        stable_seed(
            seed,
            relationship_name,
            field_name,
        )
    )


# ============================================================================
# VALIDATION
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


def validate_relationship(
    relationship: StatisticalRelationship,
    fields: dict[str, NumericField],
) -> None:

    if relationship.source_field not in fields:
        raise ValueError(f"Unknown source field: " f"{relationship.source_field}")

    if relationship.target_field not in fields:
        raise ValueError(f"Unknown target field: " f"{relationship.target_field}")

    if relationship.source_field == relationship.target_field:
        raise ValueError("Statistical relationship " "cannot reference the same field.")

    if relationship.relationship not in SUPPORTED_RELATIONSHIPS:
        raise ValueError(
            f"Unsupported statistical " f"relationship: " f"{relationship.relationship}"
        )

    if relationship.relationship == "TARGET_CORRELATION" and not (
        -1.0 <= relationship.target_correlation <= 1.0
    ):
        raise ValueError("Target correlation must " "be between -1 and 1.")

    if relationship.relationship == "TARGET_CORRELATION" and relationship.tolerance < 0:
        raise ValueError("Correlation tolerance " "cannot be negative.")

    if relationship.method not in SUPPORTED_METHODS:
        raise ValueError(
            f"Unsupported correlation " f"method: " f"{relationship.method}"
        )

    if (
        relationship.relationship == "TARGET_CORRELATION"
        and relationship.target_correlation > 0
        and relationship.relationship == "TARGET_CORRELATION"
        and relationship.name.startswith("NEGATIVE")
    ):
        raise ValueError(
            "Negative relationship " "cannot request a positive " "target correlation."
        )


# ============================================================================
# NUMERIC TRANSFORMATION
# ============================================================================


def scale_to_range(
    values: list[float],
    minimum: float,
    maximum: float,
) -> list[float]:

    if not values:
        return []

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
# RANKING
# ============================================================================


def ranks(
    values: list[float],
) -> list[float]:

    ordered = sorted(
        range(len(values)),
        key=lambda index: (
            values[index],
            index,
        ),
    )

    result = [0.0] * len(values)

    for rank, index in enumerate(
        ordered,
        start=1,
    ):
        result[index] = float(rank)

    return result


# ============================================================================
# PEARSON
# ============================================================================


def pearson_correlation(
    x: list[float],
    y: list[float],
) -> float:

    if len(x) != len(y):
        raise ValueError("Correlation vectors " "must have equal length.")

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
        raise ValueError("Correlation is undefined " "for a constant field.")

    return numerator / denominator


# ============================================================================
# SPEARMAN
# ============================================================================


def spearman_correlation(
    x: list[float],
    y: list[float],
) -> float:

    return pearson_correlation(
        ranks(x),
        ranks(y),
    )


def calculate_correlation(
    x: list[float],
    y: list[float],
    method: str,
) -> float:

    if method == "PEARSON":
        return pearson_correlation(
            x,
            y,
        )

    if method == "SPEARMAN":
        return spearman_correlation(
            x,
            y,
        )

    raise ValueError(f"Unsupported correlation method: " f"{method}")


# ============================================================================
# CORRELATED GENERATION
# ============================================================================


def generate_standard_normal(
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


def generate_correlated_latent_values(
    source: list[float],
    target_correlation: float,
    rng: random.Random,
) -> list[float]:

    if not (-1.0 <= target_correlation <= 1.0):
        raise ValueError("Target correlation must " "be between -1 and 1.")

    independent = generate_standard_normal(
        rng,
        len(source),
    )

    source_mean = mean(source)

    centered_source = [value - source_mean for value in source]

    source_variance = mean(value * value for value in centered_source)

    if math.isclose(
        source_variance,
        0.0,
    ):
        raise ValueError("Source values have zero variance.")

    source_std = math.sqrt(source_variance)

    normalized_source = [value / source_std for value in centered_source]

    residual = math.sqrt(
        max(
            0.0,
            1.0 - (target_correlation**2),
        )
    )

    return [
        (target_correlation * source_value) + (residual * independent_value)
        for source_value, independent_value in zip(
            normalized_source,
            independent,
        )
    ]


def generate_related_fields(
    source_field: NumericField,
    target_field: NumericField,
    relationship: StatisticalRelationship,
    count: int,
    seed: int,
) -> tuple[
    list[float],
    list[float],
]:

    source_rng = field_rng(
        seed,
        relationship.name,
        source_field.name,
    )

    target_rng = field_rng(
        seed,
        relationship.name,
        target_field.name,
    )

    source_latent = generate_standard_normal(
        source_rng,
        count,
    )

    source_values = scale_to_range(
        source_latent,
        source_field.minimum,
        source_field.maximum,
    )

    target_latent = generate_correlated_latent_values(
        source_latent,
        relationship.target_correlation,
        target_rng,
    )

    target_values = scale_to_range(
        target_latent,
        target_field.minimum,
        target_field.maximum,
    )

    return (
        source_values,
        target_values,
    )


# ============================================================================
# TEST DATA
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
}


def positive_relationship() -> StatisticalRelationship:

    return StatisticalRelationship(
        name="POSITIVE_CREDIT",
        source_field="CUSTOMER_SCORE",
        target_field="CREDIT_LIMIT",
        relationship="TARGET_CORRELATION",
        target_correlation=0.75,
        method="PEARSON",
        tolerance=0.15,
    )


def negative_relationship() -> StatisticalRelationship:

    return StatisticalRelationship(
        name="NEGATIVE_RISK",
        source_field="CUSTOMER_SCORE",
        target_field="RISK_SCORE",
        relationship="TARGET_CORRELATION",
        target_correlation=-0.75,
        method="PEARSON",
        tolerance=0.15,
    )


def spearman_relationship() -> StatisticalRelationship:

    return StatisticalRelationship(
        name="SPEARMAN_SCORE_LIMIT",
        source_field="CUSTOMER_SCORE",
        target_field="CREDIT_LIMIT",
        relationship="TARGET_CORRELATION",
        target_correlation=0.75,
        method="SPEARMAN",
        tolerance=0.15,
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


def test_positive_pearson() -> bool:

    relationship = positive_relationship()

    validate_relationship(
        relationship,
        FIELDS,
    )

    source, target = generate_related_fields(
        FIELDS["CUSTOMER_SCORE"],
        FIELDS["CREDIT_LIMIT"],
        relationship,
        1000,
        MASTER_SEED,
    )

    observed = pearson_correlation(
        source,
        target,
    )

    return (
        observed > 0
        and abs(observed - relationship.target_correlation) <= relationship.tolerance
    )


def test_negative_pearson() -> bool:

    relationship = negative_relationship()

    validate_relationship(
        relationship,
        FIELDS,
    )

    source, target = generate_related_fields(
        FIELDS["CUSTOMER_SCORE"],
        FIELDS["RISK_SCORE"],
        relationship,
        1000,
        MASTER_SEED,
    )

    observed = pearson_correlation(
        source,
        target,
    )

    return (
        observed < 0
        and abs(observed - relationship.target_correlation) <= relationship.tolerance
    )


def test_spearman() -> bool:

    relationship = spearman_relationship()

    validate_relationship(
        relationship,
        FIELDS,
    )

    source, target = generate_related_fields(
        FIELDS["CUSTOMER_SCORE"],
        FIELDS["CREDIT_LIMIT"],
        relationship,
        1000,
        MASTER_SEED,
    )

    observed = spearman_correlation(
        source,
        target,
    )

    return (
        observed > 0
        and abs(observed - relationship.target_correlation) <= relationship.tolerance
    )


def test_independent_generation() -> bool:

    relationship = positive_relationship()

    source_rng = field_rng(
        MASTER_SEED,
        "INDEPENDENT",
        "CUSTOMER_SCORE",
    )

    target_rng = field_rng(
        MASTER_SEED,
        "INDEPENDENT",
        "CREDIT_LIMIT",
    )

    source = scale_to_range(
        generate_standard_normal(
            source_rng,
            1000,
        ),
        0.0,
        100.0,
    )

    target = scale_to_range(
        generate_standard_normal(
            target_rng,
            1000,
        ),
        1000.0,
        10000.0,
    )

    observed = pearson_correlation(
        source,
        target,
    )

    return abs(observed) < 0.15


def test_reproducibility() -> bool:

    relationship = positive_relationship()

    first = generate_related_fields(
        FIELDS["CUSTOMER_SCORE"],
        FIELDS["CREDIT_LIMIT"],
        relationship,
        1000,
        42,
    )

    second = generate_related_fields(
        FIELDS["CUSTOMER_SCORE"],
        FIELDS["CREDIT_LIMIT"],
        relationship,
        1000,
        42,
    )

    return first == second


def test_seed_sensitivity() -> bool:

    relationship = positive_relationship()

    first = generate_related_fields(
        FIELDS["CUSTOMER_SCORE"],
        FIELDS["CREDIT_LIMIT"],
        relationship,
        1000,
        42,
    )

    second = generate_related_fields(
        FIELDS["CUSTOMER_SCORE"],
        FIELDS["CREDIT_LIMIT"],
        relationship,
        1000,
        43,
    )

    return first != second


def test_field_order_independence() -> bool:

    relationship = positive_relationship()

    forward_fields = {
        "CUSTOMER_SCORE": FIELDS["CUSTOMER_SCORE"],
        "CREDIT_LIMIT": FIELDS["CREDIT_LIMIT"],
    }

    reverse_fields = {
        "CREDIT_LIMIT": FIELDS["CREDIT_LIMIT"],
        "CUSTOMER_SCORE": FIELDS["CUSTOMER_SCORE"],
    }

    first = generate_related_fields(
        forward_fields[relationship.source_field],
        forward_fields[relationship.target_field],
        relationship,
        1000,
        MASTER_SEED,
    )

    second = generate_related_fields(
        reverse_fields[relationship.source_field],
        reverse_fields[relationship.target_field],
        relationship,
        1000,
        MASTER_SEED,
    )

    return first == second


def test_relationship_direction() -> bool:

    relationship = positive_relationship()

    source, target = generate_related_fields(
        FIELDS["CUSTOMER_SCORE"],
        FIELDS["CREDIT_LIMIT"],
        relationship,
        1000,
        MASTER_SEED,
    )

    observed = pearson_correlation(
        source,
        target,
    )

    return observed > 0


def test_target_zero() -> bool:

    relationship = StatisticalRelationship(
        name="ZERO_CORRELATION",
        source_field="CUSTOMER_SCORE",
        target_field="CREDIT_LIMIT",
        relationship="TARGET_CORRELATION",
        target_correlation=0.0,
        method="PEARSON",
        tolerance=0.15,
    )

    validate_relationship(
        relationship,
        FIELDS,
    )

    source, target = generate_related_fields(
        FIELDS["CUSTOMER_SCORE"],
        FIELDS["CREDIT_LIMIT"],
        relationship,
        1000,
        MASTER_SEED,
    )

    observed = pearson_correlation(
        source,
        target,
    )

    return abs(observed) <= relationship.tolerance


def test_invalid_target() -> bool:

    relationship = StatisticalRelationship(
        name="INVALID_TARGET",
        source_field="CUSTOMER_SCORE",
        target_field="CREDIT_LIMIT",
        relationship="TARGET_CORRELATION",
        target_correlation=1.5,
        method="PEARSON",
        tolerance=0.15,
    )

    try:

        validate_relationship(
            relationship,
            FIELDS,
        )

    except ValueError:

        return True

    return False


def test_invalid_method() -> bool:

    relationship = StatisticalRelationship(
        name="INVALID_METHOD",
        source_field="CUSTOMER_SCORE",
        target_field="CREDIT_LIMIT",
        relationship="TARGET_CORRELATION",
        target_correlation=0.75,
        method="KENDALL",
        tolerance=0.15,
    )

    try:

        validate_relationship(
            relationship,
            FIELDS,
        )

    except ValueError:

        return True

    return False


def test_unknown_field() -> bool:

    relationship = StatisticalRelationship(
        name="UNKNOWN_FIELD",
        source_field="UNKNOWN",
        target_field="CREDIT_LIMIT",
        relationship="TARGET_CORRELATION",
        target_correlation=0.75,
        method="PEARSON",
        tolerance=0.15,
    )

    try:

        validate_relationship(
            relationship,
            FIELDS,
        )

    except ValueError:

        return True

    return False


def test_no_hidden_fallback() -> bool:

    relationship = StatisticalRelationship(
        name="UNSUPPORTED_RELATIONSHIP",
        source_field="CUSTOMER_SCORE",
        target_field="CREDIT_LIMIT",
        relationship="UNKNOWN_RELATIONSHIP",
        target_correlation=0.75,
        method="PEARSON",
        tolerance=0.15,
    )

    try:

        validate_relationship(
            relationship,
            FIELDS,
        )

    except ValueError:

        return True

    return False


def test_relationship_validation_integrity() -> bool:

    relationship = positive_relationship()

    source, target = generate_related_fields(
        FIELDS["CUSTOMER_SCORE"],
        FIELDS["CREDIT_LIMIT"],
        relationship,
        1000,
        MASTER_SEED,
    )

    observed = calculate_correlation(
        source,
        target,
        relationship.method,
    )

    return -1.0 <= observed <= 1.0


def test_different_target_changes_relationship() -> bool:

    low = StatisticalRelationship(
        name="LOW_TARGET",
        source_field="CUSTOMER_SCORE",
        target_field="CREDIT_LIMIT",
        relationship="TARGET_CORRELATION",
        target_correlation=0.25,
        method="PEARSON",
        tolerance=0.15,
    )

    high = StatisticalRelationship(
        name="HIGH_TARGET",
        source_field="CUSTOMER_SCORE",
        target_field="CREDIT_LIMIT",
        relationship="TARGET_CORRELATION",
        target_correlation=0.85,
        method="PEARSON",
        tolerance=0.15,
    )

    source_low, target_low = generate_related_fields(
        FIELDS["CUSTOMER_SCORE"],
        FIELDS["CREDIT_LIMIT"],
        low,
        1000,
        MASTER_SEED,
    )

    source_high, target_high = generate_related_fields(
        FIELDS["CUSTOMER_SCORE"],
        FIELDS["CREDIT_LIMIT"],
        high,
        1000,
        MASTER_SEED,
    )

    correlation_low = pearson_correlation(
        source_low,
        target_low,
    )

    correlation_high = pearson_correlation(
        source_high,
        target_high,
    )

    return correlation_high > correlation_low


# ============================================================================
# MAIN
# ============================================================================


def main() -> int:

    print()

    print("=" * 70)

    print("FORGE - Experiment 020-P: " "Declarative Statistical Relationships")

    print("=" * 70)

    print("Experiment:     " "020_declarative_generation_specification")

    print("Stage:          020-P")

    print("Purpose:        " "Declarative target correlation generation")

    print(f"Random seed:    {MASTER_SEED}")

    print()

    print("Statistical relationship architecture:")

    print("  Declarative relationship")

    print("       ↓")

    print("  Parameter validation")

    print("       ↓")

    print("  Correlated latent generation")

    print("       ↓")

    print("  Distribution transformation")

    print("       ↓")

    print("  Correlation validation")

    print()

    print("Controlled vocabulary:")

    print("  Relationships:")

    for value in sorted(SUPPORTED_RELATIONSHIPS):
        print(f"    {value}")

    print("  Directions:")

    for value in sorted(SUPPORTED_DIRECTIONS):
        print(f"    {value}")

    print("  Methods:")

    for value in sorted(SUPPORTED_METHODS):
        print(f"    {value}")

    print()

    tests = [
        (
            "Positive Pearson correlation",
            test_positive_pearson,
        ),
        (
            "Negative Pearson correlation",
            test_negative_pearson,
        ),
        (
            "Spearman correlation",
            test_spearman,
        ),
        (
            "Independent generation baseline",
            test_independent_generation,
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
            "Relationship direction",
            test_relationship_direction,
        ),
        (
            "Zero correlation",
            test_target_zero,
        ),
        (
            "Invalid target blocking",
            test_invalid_target,
        ),
        (
            "Invalid method blocking",
            test_invalid_method,
        ),
        (
            "Unknown field blocking",
            test_unknown_field,
        ),
        (
            "No hidden fallback",
            test_no_hidden_fallback,
        ),
        (
            "Correlation validation integrity",
            test_relationship_validation_integrity,
        ),
        (
            "Target sensitivity",
            test_different_target_changes_relationship,
        ),
    ]

    print("Statistical relationship validation:")

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
    # Representative statistics
    # ------------------------------------------------------------------

    positive = positive_relationship()

    negative = negative_relationship()

    source_positive, target_positive = generate_related_fields(
        FIELDS["CUSTOMER_SCORE"],
        FIELDS["CREDIT_LIMIT"],
        positive,
        1000,
        MASTER_SEED,
    )

    source_negative, target_negative = generate_related_fields(
        FIELDS["CUSTOMER_SCORE"],
        FIELDS["RISK_SCORE"],
        negative,
        1000,
        MASTER_SEED,
    )

    positive_observed = pearson_correlation(
        source_positive,
        target_positive,
    )

    negative_observed = pearson_correlation(
        source_negative,
        target_negative,
    )

    print("Observed statistical behavior:")

    print(f"  Positive target:          " f"{positive.target_correlation:+.2f}")

    print(f"  Positive observed:        " f"{positive_observed:+.3f}")

    print(f"  Negative target:          " f"{negative.target_correlation:+.2f}")

    print(f"  Negative observed:        " f"{negative_observed:+.3f}")

    print()

    print("Experiment result:")

    print(f"  Positive correlation:     " f"{results[0]['status']}")

    print(f"  Negative correlation:     " f"{results[1]['status']}")

    print(f"  Spearman:                 " f"{results[2]['status']}")

    print(f"  Independent baseline:     " f"{results[3]['status']}")

    print(f"  Reproducibility:          " f"{results[4]['status']}")

    print(f"  Seed sensitivity:         " f"{results[5]['status']}")

    print(f"  Field-order independence: " f"{results[6]['status']}")

    print(f"  Direction semantics:       " f"{results[7]['status']}")

    print(f"  Zero correlation:          " f"{results[8]['status']}")

    configuration_safety = (
        "PASS"
        if all(result["status"] == "PASS" for result in results[9:13])
        else "FAIL"
    )

    print(f"  Configuration safety:      " f"{configuration_safety}")

    print(f"  Target sensitivity:        " f"{results[14]['status']}")

    print()

    print(f"  Tests passed:              " f"{passed}/{total}")

    print(f"  Overall:                   " f"{'PASS' if overall else 'FAIL'}")

    # ------------------------------------------------------------------
    # Persist results
    # ------------------------------------------------------------------

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    output = {
        "experiment": ("020_declarative_generation_specification"),
        "stage": "020-P",
        "purpose": ("Declarative statistical " "relationship generation"),
        "seed": MASTER_SEED,
        "supported_relationships": sorted(SUPPORTED_RELATIONSHIPS),
        "supported_directions": sorted(SUPPORTED_DIRECTIONS),
        "supported_methods": sorted(SUPPORTED_METHODS),
        "observed_statistics": {
            "positive_target": positive.target_correlation,
            "positive_observed": positive_observed,
            "negative_target": negative.target_correlation,
            "negative_observed": negative_observed,
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
            "Declarative statistical " "relationships are " "experimentally validated."
        )

        return 0

    print("Experiment completed with failures.")

    return 1


if __name__ == "__main__":

    sys.exit(main())
