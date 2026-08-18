"""
FORGE - Experiment 008: Domain vs Generation Strategy
======================================================

Purpose
-------
This experiment tests whether domain information and generation
strategy can be represented as separate concerns.

The experiment builds on the generation capabilities established in:

    Experiment 001 - Metadata-Only Generation
    Experiment 002 - Field Constraints
    Experiment 003 - Distribution-Controlled Generation
    Experiment 007 - Reproducible Generation

The experiment introduces an explicit domain definition and allows
multiple generation strategies to operate against the same domain.

The strategies tested are:

    - fixed
    - uniform
    - weighted
    - random

No machine learning, deep learning, LLM, or real production data
is used.

The objective is to determine whether:

    DOMAIN
        =
    What values are valid?

can be separated from:

    GENERATION STRATEGY
        =
    How should a value be selected?

Experiment
----------
008 - Domain vs Generation Strategy

Key Question
------------
Can the same domain be reused across multiple generation strategies
without redefining the domain itself?

Author
------
Ranjoy Sen

Status
------
Experimental

How to Run
----------
From the repository root:

    uv run python experiments/008_domain_vs_generation_strategy/experiment.py

Output
------
The generated dataset is written to:

    experiments/008_domain_vs_generation_strategy/output/generated_data.csv

The strategy results are written to:

    experiments/008_domain_vs_generation_strategy/output/strategy_results.json

Important
---------
The generated data is synthetic and does not represent any real
production dataset.
"""

from collections import Counter
from pathlib import Path
import json
import random

import pandas as pd

# --------------------------------------------------
# Experiment paths
# --------------------------------------------------

EXPERIMENT_DIR = Path(__file__).resolve().parent

SPECIFICATION_FILE = EXPERIMENT_DIR / "specification.json"

OUTPUT_DIR = EXPERIMENT_DIR / "output"

OUTPUT_FILE = OUTPUT_DIR / "generated_data.csv"

RESULTS_FILE = OUTPUT_DIR / "strategy_results.json"


# --------------------------------------------------
# Specification
# --------------------------------------------------


def load_specification() -> dict:
    """Load the experiment specification from JSON."""

    with SPECIFICATION_FILE.open(
        "r",
        encoding="utf-8",
    ) as file:
        return json.load(file)


# --------------------------------------------------
# Domain handling
# --------------------------------------------------


def get_domain(
    specification: dict,
    domain_name: str,
) -> list:
    """
    Retrieve a domain from the specification.

    A domain is intentionally treated as independent metadata.
    Generation strategies consume the domain but do not define it.
    """

    domains = specification.get(
        "domains",
        {},
    )

    if domain_name not in domains:
        raise ValueError(f"Domain not found: {domain_name}")

    domain = domains[domain_name]

    values = domain.get("values")

    if not values:
        raise ValueError(f"Domain '{domain_name}' must contain values.")

    if len(values) != len(set(values)):
        raise ValueError(f"Domain '{domain_name}' contains duplicate values.")

    return values


def validate_domain(
    values: list,
) -> None:
    """Validate the basic structure of a domain."""

    if not values:
        raise ValueError("Domain must contain at least one value.")

    if len(values) != len(set(values)):
        raise ValueError("Domain values must be unique.")


def validate_domain_membership(
    value,
    domain_values: list,
) -> bool:
    """Return whether a generated value belongs to the domain."""

    return value in domain_values


# --------------------------------------------------
# Generation strategies
# --------------------------------------------------


def generate_fixed(
    domain_values: list,
    generation: dict,
):
    """
    Generate a fixed value.

    The configured value must belong to the domain.
    """

    if "value" not in generation:
        raise ValueError("Fixed strategy requires a value.")

    value = generation["value"]

    if value not in domain_values:
        raise ValueError(f"Fixed value '{value}' is not part of the domain.")

    return value


def generate_uniform(
    domain_values: list,
):
    """Select a value with equal probability from the domain."""

    return random.choice(domain_values)


def generate_weighted(
    domain_values: list,
    generation: dict,
):
    """
    Select a value using explicitly supplied weights.

    The weights correspond positionally to the domain values.
    """

    weights = generation.get("weights")

    if weights is None:
        raise ValueError("Weighted strategy requires weights.")

    if len(weights) != len(domain_values):
        raise ValueError("Number of weights must match " "number of domain values.")

    if any(weight < 0 for weight in weights):
        raise ValueError("Weights cannot be negative.")

    if sum(weights) <= 0:
        raise ValueError("At least one weight must be greater than zero.")

    return random.choices(
        domain_values,
        weights=weights,
        k=1,
    )[0]


def generate_random(
    domain_values: list,
):
    """
    Select a value randomly from the domain.

    For this experiment, random selection is implemented using
    equal-probability sampling.

    The experiment intentionally investigates whether this should
    remain a distinct strategy or eventually be treated as an alias
    for uniform domain sampling.
    """

    return random.choice(domain_values)


# --------------------------------------------------
# Strategy dispatcher
# --------------------------------------------------


def generate_value(
    domain_values: list,
    generation: dict,
):
    """Generate a value using the configured strategy."""

    strategy = generation.get("strategy")

    if strategy == "fixed":

        return generate_fixed(
            domain_values,
            generation,
        )

    if strategy == "uniform":

        return generate_uniform(
            domain_values,
        )

    if strategy == "weighted":

        return generate_weighted(
            domain_values,
            generation,
        )

    if strategy == "random":

        return generate_random(
            domain_values,
        )

    raise ValueError(f"Unsupported generation strategy: {strategy}")


# --------------------------------------------------
# Entity generation
# --------------------------------------------------


def generate_identifier(
    length: int,
    prefix: str,
    index: int,
) -> str:
    """Generate a fixed-width identifier."""

    numeric_length = length - len(prefix)

    if numeric_length <= 0:
        raise ValueError("Identifier length must be greater than prefix length.")

    return prefix + str(index).zfill(numeric_length)


def generate_entity(
    specification: dict,
) -> pd.DataFrame:
    """Generate the CUSTOMER entity."""

    generation_metadata = specification["generation"]

    record_count = generation_metadata["record_count"]

    customer_metadata = specification["entities"]["CUSTOMER"]

    rows = []

    for index in range(
        1,
        record_count + 1,
    ):

        row = {}

        for (
            field_name,
            field_metadata,
        ) in customer_metadata["fields"].items():

            field_type = field_metadata["type"]

            if field_type == "identifier":

                row[field_name] = generate_identifier(
                    length=field_metadata["length"],
                    prefix=field_metadata.get(
                        "prefix",
                        "",
                    ),
                    index=index,
                )

                continue

            if field_type == "categorical":

                domain_name = field_metadata.get("domain")

                if not domain_name:
                    raise ValueError(
                        f"Categorical field '{field_name}' " "must reference a domain."
                    )

                domain_values = get_domain(
                    specification,
                    domain_name,
                )

                row[field_name] = generate_value(
                    domain_values=domain_values,
                    generation=field_metadata["generation"],
                )

                continue

            raise ValueError(f"Unsupported field type: {field_type}")

        rows.append(row)

    return pd.DataFrame(rows)


# --------------------------------------------------
# Validation
# --------------------------------------------------


def validate_fixed_strategy(
    dataframe: pd.DataFrame,
    field_name: str,
    expected_value,
) -> dict:
    """Validate fixed strategy output."""

    series = dataframe[field_name]

    passed = series.eq(expected_value).all()

    return {
        "strategy": "fixed",
        "field": field_name,
        "expected_value": expected_value,
        "observed_values": sorted(series.unique().tolist()),
        "passed": bool(passed),
    }


def validate_domain_membership_for_field(
    dataframe: pd.DataFrame,
    field_name: str,
    domain_values: list,
) -> dict:
    """Validate all generated values against the declared domain."""

    series = dataframe[field_name]

    invalid_values = [
        value
        for value in series
        if not validate_domain_membership(
            value,
            domain_values,
        )
    ]

    return {
        "field": field_name,
        "domain": domain_values,
        "invalid_count": len(invalid_values),
        "invalid_values": invalid_values,
        "passed": len(invalid_values) == 0,
    }


def calculate_distribution(
    dataframe: pd.DataFrame,
    field_name: str,
) -> dict:
    """Calculate observed value frequencies."""

    counts = Counter(dataframe[field_name])

    total = len(dataframe)

    distribution = {}

    for value in sorted(counts.keys()):
        distribution[value] = {
            "count": counts[value],
            "percentage": (counts[value] / total),
        }

    return distribution


def validate_weighted_strategy(
    dataframe: pd.DataFrame,
    field_name: str,
    domain_values: list,
    weights: list[float],
) -> dict:
    """Report observed versus declared weighted distribution."""

    observed = calculate_distribution(
        dataframe,
        field_name,
    )

    expected = {}

    for value, weight in zip(
        domain_values,
        weights,
    ):
        expected[value] = weight

    comparison = {}

    for value in domain_values:

        observed_percentage = observed.get(
            value,
            {"percentage": 0.0},
        )["percentage"]

        comparison[value] = {
            "observed": observed_percentage,
            "expected": expected[value],
            "difference": (observed_percentage - expected[value]),
        }

    return {
        "strategy": "weighted",
        "field": field_name,
        "comparison": comparison,
    }


# --------------------------------------------------
# Output
# --------------------------------------------------


def save_dataset(
    dataframe: pd.DataFrame,
) -> Path:
    """Save generated data."""

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    dataframe.to_csv(
        OUTPUT_FILE,
        index=False,
    )

    return OUTPUT_FILE


def save_results(
    results: dict,
) -> Path:
    """Save strategy validation results."""

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    with RESULTS_FILE.open(
        "w",
        encoding="utf-8",
    ) as file:

        json.dump(
            results,
            file,
            indent=2,
        )

    return RESULTS_FILE


# --------------------------------------------------
# Experiment execution
# --------------------------------------------------


def main() -> None:
    """Run Experiment 008."""

    specification = load_specification()

    experiment_metadata = specification["experiment"]

    generation_metadata = specification["generation"]

    seed = generation_metadata["seed"]

    record_count = generation_metadata["record_count"]

    country_domain = get_domain(
        specification,
        "COUNTRY",
    )

    validate_domain(country_domain)

    print("=" * 70)
    print("FORGE - Experiment 008: " "Domain vs Generation Strategy")
    print("=" * 70)

    print(
        f"Experiment:   "
        f"{experiment_metadata['id']} - "
        f"{experiment_metadata['name']}"
    )

    print(f"Specification: " f"{SPECIFICATION_FILE}")

    print(f"Random seed:   {seed}")

    print(f"Record count:  {record_count}")

    print("\nShared domain:")

    print(f"  COUNTRY: {country_domain}")

    print("\nGenerating data...")

    random.seed(seed)

    dataframe = generate_entity(specification)

    print(f"  Generated {len(dataframe)} " "records for CUSTOMER")

    # --------------------------------------------------
    # Domain validation
    # --------------------------------------------------

    print("\nDomain validation:")

    domain_results = {}

    strategy_fields = [
        "COUNTRY_FIXED",
        "COUNTRY_UNIFORM",
        "COUNTRY_WEIGHTED",
        "COUNTRY_RANDOM",
    ]

    for field_name in strategy_fields:

        result = validate_domain_membership_for_field(
            dataframe=dataframe,
            field_name=field_name,
            domain_values=country_domain,
        )

        domain_results[field_name] = result

        print(f"  {field_name:<20} " f"{'PASS' if result['passed'] else 'FAIL'}")

    # --------------------------------------------------
    # Fixed strategy
    # --------------------------------------------------

    fixed_generation = specification["entities"]["CUSTOMER"]["fields"]["COUNTRY_FIXED"][
        "generation"
    ]

    fixed_result = validate_fixed_strategy(
        dataframe=dataframe,
        field_name="COUNTRY_FIXED",
        expected_value=fixed_generation["value"],
    )

    print("\nFixed strategy:")

    print(f"  Expected value: " f"{fixed_result['expected_value']}")

    print(f"  Result:         " f"{'PASS' if fixed_result['passed'] else 'FAIL'}")

    # --------------------------------------------------
    # Uniform strategy
    # --------------------------------------------------

    uniform_distribution = calculate_distribution(
        dataframe,
        "COUNTRY_UNIFORM",
    )

    print("\nUniform strategy:")

    for value in country_domain:

        observed = uniform_distribution.get(
            value,
            {"percentage": 0.0},
        )["percentage"]

        print(f"  {value}: " f"{observed:.2%}")

    # --------------------------------------------------
    # Weighted strategy
    # --------------------------------------------------

    weighted_generation = specification["entities"]["CUSTOMER"]["fields"][
        "COUNTRY_WEIGHTED"
    ]["generation"]

    weighted_result = validate_weighted_strategy(
        dataframe=dataframe,
        field_name="COUNTRY_WEIGHTED",
        domain_values=country_domain,
        weights=weighted_generation["weights"],
    )

    print("\nWeighted strategy:")

    for (
        value,
        comparison,
    ) in weighted_result["comparison"].items():

        print(
            f"  {value}: "
            f"observed="
            f"{comparison['observed']:.2%}, "
            f"expected="
            f"{comparison['expected']:.2%}"
        )

    # --------------------------------------------------
    # Random strategy
    # --------------------------------------------------

    random_distribution = calculate_distribution(
        dataframe,
        "COUNTRY_RANDOM",
    )

    print("\nRandom strategy:")

    for value in country_domain:

        observed = random_distribution.get(
            value,
            {"percentage": 0.0},
        )["percentage"]

        print(f"  {value}: " f"{observed:.2%}")

    # --------------------------------------------------
    # Strategy comparison
    # --------------------------------------------------

    uniform_values = set(dataframe["COUNTRY_UNIFORM"])

    random_values = set(dataframe["COUNTRY_RANDOM"])

    same_domain = uniform_values.issubset(
        set(country_domain)
    ) and random_values.issubset(set(country_domain))

    strategy_comparison = {
        "fixed": {
            "field": "COUNTRY_FIXED",
            "domain": "COUNTRY",
            "strategy": "fixed",
            "passed": fixed_result["passed"],
        },
        "uniform": {
            "field": "COUNTRY_UNIFORM",
            "domain": "COUNTRY",
            "strategy": "uniform",
            "passed": domain_results["COUNTRY_UNIFORM"]["passed"],
        },
        "weighted": {
            "field": "COUNTRY_WEIGHTED",
            "domain": "COUNTRY",
            "strategy": "weighted",
            "passed": domain_results["COUNTRY_WEIGHTED"]["passed"],
        },
        "random": {
            "field": "COUNTRY_RANDOM",
            "domain": "COUNTRY",
            "strategy": "random",
            "passed": domain_results["COUNTRY_RANDOM"]["passed"],
        },
    }

    all_domain_checks_passed = all(
        result["passed"] for result in domain_results.values()
    )

    overall_result = (
        "PASS"
        if (all_domain_checks_passed and fixed_result["passed"] and same_domain)
        else "FAIL"
    )

    results = {
        "experiment": experiment_metadata,
        "generation": {
            "seed": seed,
            "record_count": record_count,
        },
        "domain": {
            "name": "COUNTRY",
            "type": "categorical",
            "values": country_domain,
        },
        "strategies": strategy_comparison,
        "observed_distributions": {
            "COUNTRY_UNIFORM": uniform_distribution,
            "COUNTRY_WEIGHTED": weighted_result["comparison"],
            "COUNTRY_RANDOM": random_distribution,
        },
        "domain_validation": domain_results,
        "fixed_validation": fixed_result,
        "architectural_observation": {
            "same_domain_reused": True,
            "domain_changed_between_strategies": False,
            "strategy_changes_generation_behavior": True,
        },
        "overall_result": overall_result,
    }

    # --------------------------------------------------
    # Output
    # --------------------------------------------------

    output_file = save_dataset(dataframe)

    results_file = save_results(results)

    print("\nOutput:")

    print(f"  Dataset: " f"{output_file}")

    print(f"  Results: " f"{results_file}")

    print("\nFirst 20 records:")

    print(dataframe.head(20).to_string(index=False))

    print("\nExperiment result:")

    print(f"  Domain validation: " f"{'PASS' if all_domain_checks_passed else 'FAIL'}")

    print(f"  Fixed strategy:     " f"{'PASS' if fixed_result['passed'] else 'FAIL'}")

    print(f"  Overall result:     " f"{overall_result}")

    print("\nExperiment completed successfully.")


# --------------------------------------------------
# Entry point
# --------------------------------------------------

if __name__ == "__main__":
    main()
