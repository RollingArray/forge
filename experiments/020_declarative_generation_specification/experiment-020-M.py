"""
FORGE - Experiment 020-M: Declarative Statistical Generation
==============================================================

Stage:
    020-M

Purpose:
    Validate declarative statistical generation as a first-class FORGE
    generation capability.

Research Question
-----------------
Can FORGE use a declarative statistical specification to generate values
according to the requested distribution while preserving:

    - explicit distribution parameters
    - deterministic generation
    - seed sensitivity
    - field-order independence
    - type compatibility
    - boundedness
    - categorical weighting
    - statistical validation
    - configuration safety

Architectural Principle
-----------------------
Distribution describes HOW a value should be generated.

It is not merely a validation property.

Example:

    AMOUNT
        type: DECIMAL
        strategy: RANDOM
        distribution: NORMAL
        parameters:
            mean: 500
            stddev: 100

The runtime should use the declared distribution directly.

It must not silently replace it with another distribution.

Execution model:

    Declarative Field Specification
                |
                v
       Distribution Analysis
                |
                v
       Parameter Validation
                |
                v
       Statistical Generator
                |
                v
          Field Values
                |
                v
       Statistical Validation

Supported statistical families in this experiment
--------------------------------------------------

    CONTINUOUS / BOUNDED
        UNIFORM
        NORMAL

    DISCRETE
        DISCRETE_UNIFORM
        POISSON

    CATEGORICAL
        CATEGORICAL

The complete FORGE vocabulary contains additional distributions.
Those remain valid vocabulary but are intentionally outside the
executable boundary of this experiment.

Important Boundary
------------------
A valid FORGE distribution does not automatically mean the current
runtime can execute it.

Unsupported but valid vocabulary must produce:

    DEFERRED

Invalid parameters must produce:

    BLOCKED

The runtime must never silently fall back to another distribution.

Scope
-----
Included:

    - UNIFORM
    - NORMAL
    - DISCRETE_UNIFORM
    - POISSON
    - CATEGORICAL
    - explicit distribution parameters
    - parameter validation
    - bounded generation
    - categorical weights
    - deterministic generation
    - seed sensitivity
    - field-order independence
    - statistical sanity checks
    - unsupported distribution boundary
    - invalid configuration blocking

Excluded:

    - LOGNORMAL
    - EXPONENTIAL
    - GAMMA
    - BETA
    - WEIBULL
    - TRIANGULAR
    - EMPIRICAL
    - TRUNCATED
    - MIXTURE
    - correlation
    - multivariate distributions
    - learned distributions

Those may be implemented after the statistical abstraction is proven.

Status:
    Experimental
"""

from __future__ import annotations

import hashlib
import json
import math
import random
import statistics
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

# ============================================================================
# PATHS
# ============================================================================

EXPERIMENT_DIR = Path(__file__).resolve().parent

OUTPUT_DIR = EXPERIMENT_DIR / "output"

RESULT_OUTPUT_PATH = OUTPUT_DIR / "statistical_generation_results.json"

MASTER_SEED = 42


# ============================================================================
# DISTRIBUTION VOCABULARY
# ============================================================================

EXECUTABLE_DISTRIBUTIONS = {
    "UNIFORM",
    "NORMAL",
    "DISCRETE_UNIFORM",
    "POISSON",
    "CATEGORICAL",
}

VALID_DEFERRED_DISTRIBUTIONS = {
    "LOGNORMAL",
    "EXPONENTIAL",
    "GAMMA",
    "BETA",
    "WEIBULL",
    "TRIANGULAR",
    "EMPIRICAL",
    "TRUNCATED",
    "MIXTURE",
}


# ============================================================================
# MODELS
# ============================================================================


@dataclass(frozen=True)
class DistributionSpec:
    name: str
    parameters: dict[str, Any]


@dataclass(frozen=True)
class StatisticalFieldSpec:
    name: str
    type: str
    distribution: DistributionSpec


# ============================================================================
# DETERMINISTIC STREAMS
# ============================================================================


def stable_seed(
    master_seed: int,
    field_name: str,
) -> int:

    material = (f"{master_seed}:" f"020-M:" f"{field_name}").encode("utf-8")

    digest = hashlib.sha256(material).digest()

    return int.from_bytes(
        digest[:8],
        byteorder="big",
        signed=False,
    )


def field_rng(
    master_seed: int,
    field_name: str,
) -> random.Random:

    return random.Random(
        stable_seed(
            master_seed,
            field_name,
        )
    )


# ============================================================================
# PARAMETER VALIDATION
# ============================================================================


class DistributionValidationError(ValueError):
    pass


def validate_distribution(
    specification: DistributionSpec,
) -> None:

    name = specification.name
    parameters = specification.parameters

    if (
        name not in EXECUTABLE_DISTRIBUTIONS
        and name not in VALID_DEFERRED_DISTRIBUTIONS
    ):

        raise DistributionValidationError(f"Unknown distribution: {name}")

    if name in VALID_DEFERRED_DISTRIBUTIONS:

        raise DistributionValidationError(
            f"Distribution '{name}' is valid " "FORGE vocabulary but deferred."
        )

    if name == "UNIFORM":

        require_parameters(
            parameters,
            {
                "minimum",
                "maximum",
            },
        )

        minimum = parameters["minimum"]

        maximum = parameters["maximum"]

        if minimum > maximum:

            raise DistributionValidationError("UNIFORM minimum cannot exceed maximum.")

    elif name == "NORMAL":

        require_parameters(
            parameters,
            {
                "mean",
                "stddev",
            },
        )

        if parameters["stddev"] <= 0:

            raise DistributionValidationError(
                "NORMAL stddev must be greater than zero."
            )

    elif name == "DISCRETE_UNIFORM":

        require_parameters(
            parameters,
            {
                "minimum",
                "maximum",
            },
        )

        minimum = parameters["minimum"]

        maximum = parameters["maximum"]

        if minimum > maximum:

            raise DistributionValidationError(
                "DISCRETE_UNIFORM minimum " "cannot exceed maximum."
            )

    elif name == "POISSON":

        require_parameters(
            parameters,
            {
                "lambda",
            },
        )

        if parameters["lambda"] <= 0:

            raise DistributionValidationError(
                "POISSON lambda must be greater than zero."
            )

    elif name == "CATEGORICAL":

        require_parameters(
            parameters,
            {
                "values",
            },
        )

        values = parameters["values"]

        if not isinstance(
            values,
            dict,
        ):

            raise DistributionValidationError("CATEGORICAL values must be a mapping.")

        if not values:

            raise DistributionValidationError("CATEGORICAL values cannot be empty.")

        total = sum(float(weight) for weight in values.values())

        if total <= 0:

            raise DistributionValidationError(
                "CATEGORICAL weights must sum to a positive value."
            )

        if any(float(weight) < 0 for weight in values.values()):

            raise DistributionValidationError("CATEGORICAL weights cannot be negative.")


def require_parameters(
    parameters: dict[str, Any],
    required: set[str],
) -> None:

    missing = required - set(parameters)

    if missing:

        raise DistributionValidationError(
            "Missing distribution parameters: " + ", ".join(sorted(missing))
        )


# ============================================================================
# STATISTICAL GENERATOR
# ============================================================================


class StatisticalGenerator:
    """
    Executes the supported declarative distributions.

    No distribution fallback is permitted.
    """

    def __init__(
        self,
        seed: int,
    ) -> None:

        self.seed = seed

    def generate(
        self,
        field: StatisticalFieldSpec,
        count: int,
    ) -> dict[str, Any]:

        distribution = field.distribution

        if distribution.name in VALID_DEFERRED_DISTRIBUTIONS:

            return {
                "status": "DEFERRED",
                "reason": (
                    f"Distribution "
                    f"'{distribution.name}' "
                    "is valid FORGE vocabulary "
                    "but not executable in 020-M."
                ),
            }

        try:

            validate_distribution(distribution)

        except DistributionValidationError as exc:

            if "deferred" in str(exc).lower():

                return {
                    "status": "DEFERRED",
                    "reason": str(exc),
                }

            return {
                "status": "BLOCKED",
                "reason": str(exc),
            }

        rng = field_rng(
            self.seed,
            field.name,
        )

        values = []

        name = distribution.name
        parameters = distribution.parameters

        for _ in range(count):

            if name == "UNIFORM":

                value = rng.uniform(
                    parameters["minimum"],
                    parameters["maximum"],
                )

            elif name == "NORMAL":

                value = rng.gauss(
                    parameters["mean"],
                    parameters["stddev"],
                )

            elif name == "DISCRETE_UNIFORM":

                value = rng.randint(
                    parameters["minimum"],
                    parameters["maximum"],
                )

            elif name == "POISSON":

                value = poisson(
                    rng,
                    parameters["lambda"],
                )

            elif name == "CATEGORICAL":

                value = weighted_choice(
                    rng,
                    parameters["values"],
                )

            else:

                return {
                    "status": "BLOCKED",
                    "reason": (f"No executor registered " f"for distribution {name}."),
                }

            values.append(value)

        return {
            "status": "PASS",
            "values": values,
            "distribution": name,
            "parameters": parameters,
        }


# ============================================================================
# DISTRIBUTION IMPLEMENTATIONS
# ============================================================================


def poisson(
    rng: random.Random,
    lambda_value: float,
) -> int:
    """
    Knuth's algorithm.

    This is intentionally implemented here rather than relying on
    numpy/scipy so the experiment remains dependency-light and
    deterministic under the FORGE-controlled random stream.
    """

    limit = math.exp(-lambda_value)

    k = 0
    product = 1.0

    while product > limit:

        k += 1

        product *= rng.random()

    return k - 1


def weighted_choice(
    rng: random.Random,
    values: dict[str, float],
) -> str:

    total = sum(float(weight) for weight in values.values())

    threshold = rng.random() * total

    cumulative = 0.0

    for value, weight in values.items():

        cumulative += float(weight)

        if threshold < cumulative:

            return value

    # Floating-point safety.
    return next(reversed(values))


# ============================================================================
# STATISTICAL VALIDATION
# ============================================================================


def validate_uniform(
    values: list[float],
    minimum: float,
    maximum: float,
) -> bool:

    return all(minimum <= value <= maximum for value in values)


def validate_discrete_uniform(
    values: list[int],
    minimum: int,
    maximum: int,
) -> bool:

    return all(
        isinstance(
            value,
            int,
        )
        and minimum <= value <= maximum
        for value in values
    )


def validate_normal(
    values: list[float],
    mean: float,
    stddev: float,
) -> bool:

    observed_mean = statistics.mean(values)

    observed_stddev = statistics.stdev(values)

    mean_tolerance = max(
        stddev * 0.15,
        0.5,
    )

    stddev_tolerance = max(
        stddev * 0.20,
        0.5,
    )

    return (
        abs(observed_mean - mean) <= mean_tolerance
        and abs(observed_stddev - stddev) <= stddev_tolerance
    )


def validate_poisson(
    values: list[int],
    lambda_value: float,
) -> bool:

    observed_mean = statistics.mean(values)

    tolerance = max(
        lambda_value * 0.15,
        0.5,
    )

    return abs(observed_mean - lambda_value) <= tolerance


def validate_categorical(
    values: list[str],
    expected: dict[str, float],
) -> bool:

    total = len(values)

    observed = {key: values.count(key) / total for key in expected}

    expected_total = sum(float(weight) for weight in expected.values())

    tolerance = 0.08

    return all(
        abs(observed[key] - (float(weight) / expected_total)) <= tolerance
        for key, weight in expected.items()
    )


# ============================================================================
# TEST HELPERS
# ============================================================================


def run_test(
    name: str,
    function,
) -> dict[str, Any]:

    try:

        result = function()

        return {
            "name": name,
            **result,
        }

    except Exception as exc:

        return {
            "name": name,
            "status": "FAIL",
            "error": str(exc),
        }


# ============================================================================
# TESTS
# ============================================================================

SAMPLE_SIZE = 5000


def test_uniform() -> dict[str, Any]:

    field = StatisticalFieldSpec(
        name="AMOUNT",
        type="DECIMAL",
        distribution=DistributionSpec(
            name="UNIFORM",
            parameters={
                "minimum": 100,
                "maximum": 500,
            },
        ),
    )

    result = StatisticalGenerator(MASTER_SEED).generate(
        field,
        SAMPLE_SIZE,
    )

    passed = result["status"] == "PASS" and validate_uniform(
        result["values"],
        100,
        500,
    )

    return {
        "status": ("PASS" if passed else "FAIL"),
        "minimum": min(
            result.get(
                "values",
                [],
            )
        ),
        "maximum": max(
            result.get(
                "values",
                [],
            )
        ),
    }


def test_normal() -> dict[str, Any]:

    field = StatisticalFieldSpec(
        name="SCORE",
        type="DECIMAL",
        distribution=DistributionSpec(
            name="NORMAL",
            parameters={
                "mean": 500,
                "stddev": 100,
            },
        ),
    )

    result = StatisticalGenerator(MASTER_SEED).generate(
        field,
        SAMPLE_SIZE,
    )

    values = result.get(
        "values",
        [],
    )

    passed = result["status"] == "PASS" and validate_normal(
        values,
        500,
        100,
    )

    return {
        "status": ("PASS" if passed else "FAIL"),
        "observed_mean": (
            round(
                statistics.mean(values),
                2,
            )
            if values
            else None
        ),
        "observed_stddev": (
            round(
                statistics.stdev(values),
                2,
            )
            if len(values) > 1
            else None
        ),
    }


def test_discrete_uniform() -> dict[str, Any]:

    field = StatisticalFieldSpec(
        name="QUANTITY",
        type="INTEGER",
        distribution=DistributionSpec(
            name="DISCRETE_UNIFORM",
            parameters={
                "minimum": 1,
                "maximum": 10,
            },
        ),
    )

    result = StatisticalGenerator(MASTER_SEED).generate(
        field,
        SAMPLE_SIZE,
    )

    passed = result["status"] == "PASS" and validate_discrete_uniform(
        result["values"],
        1,
        10,
    )

    return {
        "status": ("PASS" if passed else "FAIL"),
        "unique_values": sorted(
            set(
                result.get(
                    "values",
                    [],
                )
            )
        ),
    }


def test_poisson() -> dict[str, Any]:

    field = StatisticalFieldSpec(
        name="EVENT_COUNT",
        type="INTEGER",
        distribution=DistributionSpec(
            name="POISSON",
            parameters={
                "lambda": 4,
            },
        ),
    )

    result = StatisticalGenerator(MASTER_SEED).generate(
        field,
        SAMPLE_SIZE,
    )

    values = result.get(
        "values",
        [],
    )

    passed = result["status"] == "PASS" and validate_poisson(
        values,
        4,
    )

    return {
        "status": ("PASS" if passed else "FAIL"),
        "observed_mean": (
            round(
                statistics.mean(values),
                3,
            )
            if values
            else None
        ),
    }


def test_categorical() -> dict[str, Any]:

    expected = {
        "NEW": 0.60,
        "ACTIVE": 0.30,
        "CLOSED": 0.10,
    }

    field = StatisticalFieldSpec(
        name="STATUS",
        type="CATEGORICAL",
        distribution=DistributionSpec(
            name="CATEGORICAL",
            parameters={
                "values": expected,
            },
        ),
    )

    result = StatisticalGenerator(MASTER_SEED).generate(
        field,
        SAMPLE_SIZE,
    )

    passed = result["status"] == "PASS" and validate_categorical(
        result["values"],
        expected,
    )

    frequencies = {
        key: round(
            result["values"].count(key) / len(result["values"]),
            3,
        )
        for key in expected
    }

    return {
        "status": ("PASS" if passed else "FAIL"),
        "observed_frequencies": frequencies,
    }


def test_parameter_validation() -> dict[str, Any]:

    invalid_specs = [
        DistributionSpec(
            name="UNIFORM",
            parameters={
                "minimum": 100,
                "maximum": 10,
            },
        ),
        DistributionSpec(
            name="NORMAL",
            parameters={
                "mean": 100,
                "stddev": 0,
            },
        ),
        DistributionSpec(
            name="POISSON",
            parameters={
                "lambda": 0,
            },
        ),
        DistributionSpec(
            name="CATEGORICAL",
            parameters={
                "values": {
                    "A": -1,
                    "B": 2,
                },
            },
        ),
    ]

    blocked = 0

    for specification in invalid_specs:

        field = StatisticalFieldSpec(
            name="INVALID",
            type="DECIMAL",
            distribution=specification,
        )

        result = StatisticalGenerator(MASTER_SEED).generate(
            field,
            10,
        )

        if result["status"] == "BLOCKED":

            blocked += 1

    passed = blocked == len(invalid_specs)

    return {
        "status": ("PASS" if passed else "FAIL"),
        "blocked": blocked,
        "expected": len(invalid_specs),
    }


def test_unsupported_distribution_boundary() -> dict[str, Any]:

    field = StatisticalFieldSpec(
        name="VALUE",
        type="DECIMAL",
        distribution=DistributionSpec(
            name="BETA",
            parameters={
                "alpha": 2,
                "beta": 5,
            },
        ),
    )

    result = StatisticalGenerator(MASTER_SEED).generate(
        field,
        100,
    )

    passed = result["status"] == "DEFERRED"

    return {
        "status": ("PASS" if passed else "FAIL"),
        "result": result,
    }


def test_unknown_distribution_boundary() -> dict[str, Any]:

    field = StatisticalFieldSpec(
        name="VALUE",
        type="DECIMAL",
        distribution=DistributionSpec(
            name="MADE_UP_DISTRIBUTION",
            parameters={},
        ),
    )

    result = StatisticalGenerator(MASTER_SEED).generate(
        field,
        100,
    )

    passed = result["status"] == "BLOCKED"

    return {
        "status": ("PASS" if passed else "FAIL"),
        "reason": result.get("reason"),
    }


def test_reproducibility() -> dict[str, Any]:

    field = StatisticalFieldSpec(
        name="AMOUNT",
        type="DECIMAL",
        distribution=DistributionSpec(
            name="NORMAL",
            parameters={
                "mean": 500,
                "stddev": 100,
            },
        ),
    )

    first = StatisticalGenerator(42).generate(
        field,
        1000,
    )

    second = StatisticalGenerator(42).generate(
        field,
        1000,
    )

    passed = first["values"] == second["values"]

    return {
        "status": ("PASS" if passed else "FAIL"),
        "identical": passed,
    }


def test_seed_sensitivity() -> dict[str, Any]:

    field = StatisticalFieldSpec(
        name="AMOUNT",
        type="DECIMAL",
        distribution=DistributionSpec(
            name="NORMAL",
            parameters={
                "mean": 500,
                "stddev": 100,
            },
        ),
    )

    first = StatisticalGenerator(42).generate(
        field,
        1000,
    )

    second = StatisticalGenerator(43).generate(
        field,
        1000,
    )

    passed = first["values"] != second["values"]

    return {
        "status": ("PASS" if passed else "FAIL"),
        "different": passed,
    }


def test_field_order_independence() -> dict[str, Any]:

    fields_a = [
        StatisticalFieldSpec(
            name="AMOUNT",
            type="DECIMAL",
            distribution=DistributionSpec(
                name="UNIFORM",
                parameters={
                    "minimum": 0,
                    "maximum": 100,
                },
            ),
        ),
        StatisticalFieldSpec(
            name="SCORE",
            type="DECIMAL",
            distribution=DistributionSpec(
                name="NORMAL",
                parameters={
                    "mean": 50,
                    "stddev": 10,
                },
            ),
        ),
    ]

    fields_b = list(reversed(fields_a))

    generator = StatisticalGenerator(MASTER_SEED)

    first = {
        field.name: generator.generate(
            field,
            100,
        )["values"]
        for field in fields_a
    }

    second = {
        field.name: generator.generate(
            field,
            100,
        )["values"]
        for field in fields_b
    }

    passed = first == second

    return {
        "status": ("PASS" if passed else "FAIL"),
        "identical": passed,
    }


def test_no_hidden_distribution_fallback() -> dict[str, Any]:

    field = StatisticalFieldSpec(
        name="VALUE",
        type="DECIMAL",
        distribution=DistributionSpec(
            name="BETA",
            parameters={
                "alpha": 2,
                "beta": 5,
            },
        ),
    )

    result = StatisticalGenerator(MASTER_SEED).generate(
        field,
        100,
    )

    passed = result["status"] == "DEFERRED" and "values" not in result

    return {
        "status": ("PASS" if passed else "FAIL"),
    }


def test_parameter_explicitness() -> dict[str, Any]:

    field = StatisticalFieldSpec(
        name="AMOUNT",
        type="DECIMAL",
        distribution=DistributionSpec(
            name="UNIFORM",
            parameters={
                "minimum": 100,
                "maximum": 200,
            },
        ),
    )

    result = StatisticalGenerator(MASTER_SEED).generate(
        field,
        100,
    )

    passed = result["status"] == "PASS" and result["parameters"] == {
        "minimum": 100,
        "maximum": 200,
    }

    return {
        "status": ("PASS" if passed else "FAIL"),
        "parameters": result.get("parameters"),
    }


# ============================================================================
# MAIN
# ============================================================================


def main() -> int:

    print()

    print("=" * 70)

    print("FORGE - Experiment 020-M: " "Declarative Statistical Generation")

    print("=" * 70)

    print("Experiment:     " "020_declarative_generation_specification")

    print("Stage:          020-M")

    print("Purpose:        " "Declarative statistical generation")

    print(f"Random seed:    {MASTER_SEED}")

    print()

    print("Statistical generation architecture:")

    print("  Declarative field specification")

    print("       ↓")

    print("  Distribution analysis")

    print("       ↓")

    print("  Parameter validation")

    print("       ↓")

    print("  Statistical generator")

    print("       ↓")

    print("  Statistical validation")

    print()

    print("Executable distributions:")

    for distribution in sorted(EXECUTABLE_DISTRIBUTIONS):

        print(f"  {distribution}")

    print()

    print("Deferred distributions:")

    for distribution in sorted(VALID_DEFERRED_DISTRIBUTIONS):

        print(f"  {distribution}")

    print()

    tests = [
        run_test(
            "UNIFORM generation",
            test_uniform,
        ),
        run_test(
            "NORMAL generation",
            test_normal,
        ),
        run_test(
            "DISCRETE_UNIFORM generation",
            test_discrete_uniform,
        ),
        run_test(
            "POISSON generation",
            test_poisson,
        ),
        run_test(
            "CATEGORICAL generation",
            test_categorical,
        ),
        run_test(
            "Parameter validation",
            test_parameter_validation,
        ),
        run_test(
            "Unsupported distribution boundary",
            test_unsupported_distribution_boundary,
        ),
        run_test(
            "Unknown distribution boundary",
            test_unknown_distribution_boundary,
        ),
        run_test(
            "Reproducibility",
            test_reproducibility,
        ),
        run_test(
            "Seed sensitivity",
            test_seed_sensitivity,
        ),
        run_test(
            "Field-order independence",
            test_field_order_independence,
        ),
        run_test(
            "No hidden distribution fallback",
            test_no_hidden_distribution_fallback,
        ),
        run_test(
            "Parameter explicitness",
            test_parameter_explicitness,
        ),
    ]

    print("Statistical generation validation:")

    for test in tests:

        print(f"  " f"{test['name']:<42}" f"{test['status']}")

    passed = sum(test["status"] == "PASS" for test in tests)

    total = len(tests)

    overall = passed == total

    print()

    print("Experiment result:")

    print(f"  Uniform generation:             " f"{tests[0]['status']}")

    print(f"  Normal generation:              " f"{tests[1]['status']}")

    print(f"  Discrete uniform generation:    " f"{tests[2]['status']}")

    print(f"  Poisson generation:             " f"{tests[3]['status']}")

    print(f"  Categorical generation:         " f"{tests[4]['status']}")

    print(f"  Parameter validation:            " f"{tests[5]['status']}")

    print(f"  Deferred capability boundary:    " f"{tests[6]['status']}")

    print(f"  Unknown vocabulary safety:       " f"{tests[7]['status']}")

    print(f"  Reproducibility:                 " f"{tests[8]['status']}")

    print(f"  Seed sensitivity:                " f"{tests[9]['status']}")

    print(f"  Field-order independence:         " f"{tests[10]['status']}")

    print(f"  No hidden fallback:              " f"{tests[11]['status']}")

    print(f"  Parameter explicitness:          " f"{tests[12]['status']}")

    print(f"  Tests passed:                    " f"{passed}/{total}")

    print(f"  Overall:                         " f"{'PASS' if overall else 'FAIL'}")

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    output = {
        "experiment": ("020_declarative_generation_specification"),
        "stage": "020-M",
        "purpose": ("Declarative statistical generation"),
        "seed": MASTER_SEED,
        "sample_size": SAMPLE_SIZE,
        "executable_distributions": sorted(EXECUTABLE_DISTRIBUTIONS),
        "deferred_distributions": sorted(VALID_DEFERRED_DISTRIBUTIONS),
        "tests": tests,
        "tests_passed": passed,
        "tests_total": total,
        "architecture": {
            "distribution_as_first_class_capability": True,
            "explicit_parameters": True,
            "parameter_validation": True,
            "deterministic_field_streams": True,
            "statistical_validation": True,
            "safe_deferred_capabilities": True,
            "hidden_distribution_fallback": False,
        },
        "architectural_conclusion": (
            "Declarative distributions can be treated "
            "as first-class generation strategies "
            "with explicit parameters, deterministic "
            "execution, statistical validation, and "
            "safe capability boundaries."
        ),
        "boundary": (
            "Only five representative statistical "
            "distributions are executable in 020-M. "
            "The remaining valid FORGE vocabulary "
            "is explicitly deferred."
        ),
        "overall": ("PASS" if overall else "FAIL"),
    }

    with RESULT_OUTPUT_PATH.open(
        "w",
        encoding="utf-8",
    ) as file:

        json.dump(
            output,
            file,
            indent=2,
            default=str,
        )

    print()

    print("Output:")

    print(f"  Results: " f"{RESULT_OUTPUT_PATH}")

    print()

    if overall:

        print("Experiment completed successfully.")

        return 0

    print("Experiment completed with failures.")

    return 1


if __name__ == "__main__":
    sys.exit(main())
