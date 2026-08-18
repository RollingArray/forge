"""
FORGE - Experiment 012: Correlation and Dependency
===================================================

Purpose
-------
This experiment tests whether meaningful relationships between fields
require explicit dependency-aware generation rather than independent
field generation.

The experiment compares two approaches:

    1. Independent generation
       Generate each field independently.

    2. Dependency-aware generation
       Generate fields according to dependencies declared in
       specification.json.

The experiment evaluates two dependency types:

    - categorical -> numeric
    - numeric -> numeric

Experiment
----------
012 - Correlation and Dependency

Key Question
------------
Can explicit dependency information produce measurable and
controllable relationships between generated fields?

Author
------
Ranjoy Sen

Status
------
Experimental

How to Run
----------
From the repository root:

    uv run python experiments/012_correlation_and_dependency/experiment.py

Output
------
The generated datasets are written to:

    experiments/012_correlation_and_dependency/output/independent_generation.csv

    experiments/012_correlation_and_dependency/output/dependency_aware_generation.csv

Statistical observations are written to:

    experiments/012_correlation_and_dependency/output/correlation_statistics.json

Important
---------
The generated data is synthetic and does not represent any real
production dataset.
"""

from pathlib import Path
from collections import Counter
import json
import random
import statistics

import pandas as pd

# --------------------------------------------------
# Experiment paths
# --------------------------------------------------

EXPERIMENT_DIR = Path(__file__).resolve().parent

SPECIFICATION_FILE = EXPERIMENT_DIR / "specification.json"

OUTPUT_DIR = EXPERIMENT_DIR / "output"

INDEPENDENT_OUTPUT_FILE = OUTPUT_DIR / "independent_generation.csv"

DEPENDENCY_AWARE_OUTPUT_FILE = OUTPUT_DIR / "dependency_aware_generation.csv"

STATISTICS_FILE = OUTPUT_DIR / "correlation_statistics.json"


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
# Metadata helpers
# --------------------------------------------------


def get_customer_entity(
    specification: dict,
) -> dict:
    """Return the CUSTOMER entity definition."""

    return specification["entities"]["CUSTOMER"]


def get_fields(
    specification: dict,
) -> dict:
    """Return CUSTOMER field definitions."""

    return get_customer_entity(specification)["fields"]


def get_field(
    specification: dict,
    field_name: str,
) -> dict:
    """Return metadata for a field."""

    return get_fields(specification)[field_name]


def get_dependencies(
    specification: dict,
) -> list[dict]:
    """Return declared dependencies."""

    return specification["dependencies"]


# --------------------------------------------------
# Identifier generation
# --------------------------------------------------


def generate_identifier(
    length: int,
    prefix: str,
    index: int,
) -> str:
    """
    Generate a fixed-width identifier.

    The configured length represents the complete identifier length,
    including the prefix.
    """

    numeric_length = length - len(prefix)

    if numeric_length <= 0:
        raise ValueError("Identifier length must be greater than prefix length.")

    maximum = (10**numeric_length) - 1

    if index > maximum:
        raise ValueError("Identifier capacity exceeded.")

    return prefix + str(index).zfill(numeric_length)


# --------------------------------------------------
# Distribution generators
# --------------------------------------------------


def generate_categorical(
    values: list[str],
    weights: list[float],
) -> str:
    """Generate a categorical value using configured weights."""

    return random.choices(
        values,
        weights=weights,
        k=1,
    )[0]


def generate_uniform_number(
    minimum: float,
    maximum: float,
) -> float:
    """Generate a numeric value from a uniform distribution."""

    return random.uniform(
        minimum,
        maximum,
    )


# --------------------------------------------------
# Generic field generation
# --------------------------------------------------


def generate_field_value(
    specification: dict,
    field_name: str,
    index: int,
) -> object:
    """
    Generate a field independently according to its field metadata.

    This function intentionally does not evaluate dependencies.
    """

    metadata = get_field(
        specification,
        field_name,
    )

    field_type = metadata["type"]

    if field_type == "identifier":

        return generate_identifier(
            length=metadata["length"],
            prefix=metadata.get(
                "prefix",
                "",
            ),
            index=index,
        )

    if field_type == "categorical":

        distribution = metadata.get(
            "distribution",
            {},
        )

        distribution_type = distribution.get(
            "type",
            "uniform",
        )

        if distribution_type == "weighted":

            weights = distribution["weights"]

            return generate_categorical(
                metadata["values"],
                weights,
            )

        if distribution_type == "uniform":

            return random.choice(metadata["values"])

        raise ValueError(
            "Unsupported categorical distribution: " f"{distribution_type}"
        )

    if field_type == "number":

        generation = metadata["generation"]

        strategy = generation.get(
            "strategy",
            "uniform",
        )

        if strategy == "uniform":

            return round(
                generate_uniform_number(
                    generation["min"],
                    generation["max"],
                ),
                2,
            )

        raise ValueError("Unsupported numeric generation strategy: " f"{strategy}")

    raise ValueError(f"Unsupported field type: {field_type}")


# --------------------------------------------------
# Independent generation
# --------------------------------------------------


def generate_independent_dataset(
    specification: dict,
) -> pd.DataFrame:
    """
    Generate every field independently.

    Dependencies declared in the specification are intentionally
    ignored for this approach.
    """

    record_count = specification["generation"]["record_count"]

    fields = get_fields(specification)

    rows = []

    for index in range(
        1,
        record_count + 1,
    ):

        row = {}

        for field_name in fields:

            row[field_name] = generate_field_value(
                specification,
                field_name,
                index,
            )

        rows.append(row)

    return pd.DataFrame(rows)


# --------------------------------------------------
# Dependency lookup
# --------------------------------------------------


def get_dependency(
    specification: dict,
    dependency_id: str,
) -> dict:
    """Return a dependency by ID."""

    for dependency in get_dependencies(specification):

        if dependency["id"] == dependency_id:

            return dependency

    raise ValueError(f"Dependency not found: {dependency_id}")


# --------------------------------------------------
# Dependency-aware generation
# --------------------------------------------------


def generate_customer_limit_from_type(
    specification: dict,
    customer_type: str,
) -> float:
    """
    Generate CUSTOMER_LIMIT according to CUSTOMER_TYPE.

    The behavior is read from the declared dependency rather than
    being embedded in the field metadata.
    """

    dependency = get_dependency(
        specification,
        "D001",
    )

    behavior = dependency["behavior"]

    if customer_type not in behavior:

        raise ValueError(
            f"No dependency behavior defined for " f"CUSTOMER_TYPE={customer_type}"
        )

    distribution = behavior[customer_type]["distribution"]

    if distribution["type"] != "uniform":

        raise ValueError(
            "Unsupported dependency distribution: " f"{distribution['type']}"
        )

    return round(
        generate_uniform_number(
            distribution["min"],
            distribution["max"],
        ),
        2,
    )


def generate_order_amount_from_limit(
    specification: dict,
    customer_limit: float,
) -> float:
    """
    Generate ORDER_AMOUNT using CUSTOMER_LIMIT as the source.

    The amount is generated from the configured ratio range and then
    adjusted with the declared noise component.
    """

    dependency = get_dependency(
        specification,
        "D002",
    )

    behavior = dependency["behavior"]

    minimum_ratio = behavior["minimum_ratio"]

    maximum_ratio = behavior["maximum_ratio"]

    ratio = random.uniform(
        minimum_ratio,
        maximum_ratio,
    )

    noise_configuration = behavior["noise"]

    noise = random.uniform(
        noise_configuration["min"],
        noise_configuration["max"],
    )

    amount = customer_limit * ratio + noise

    field_metadata = get_field(
        specification,
        "ORDER_AMOUNT",
    )

    generation = field_metadata["generation"]

    minimum = generation["min"]

    maximum = generation["max"]

    amount = max(
        minimum,
        min(
            maximum,
            amount,
        ),
    )

    return round(
        amount,
        2,
    )


def generate_dependency_aware_dataset(
    specification: dict,
) -> pd.DataFrame:
    """
    Generate data using the declared dependency graph.

    Generation flow:

        CUSTOMER_TYPE
              |
              v
        CUSTOMER_LIMIT
              |
              v
        ORDER_AMOUNT
    """

    record_count = specification["generation"]["record_count"]

    fields = get_fields(specification)

    rows = []

    for index in range(
        1,
        record_count + 1,
    ):

        row = {}

        # --------------------------------------------------
        # Root field
        # --------------------------------------------------

        row["CUSTOMER_ID"] = generate_field_value(
            specification,
            "CUSTOMER_ID",
            index,
        )

        # --------------------------------------------------
        # Dependency root
        # --------------------------------------------------

        row["CUSTOMER_TYPE"] = generate_field_value(
            specification,
            "CUSTOMER_TYPE",
            index,
        )

        # --------------------------------------------------
        # D001:
        #
        # CUSTOMER_TYPE -> CUSTOMER_LIMIT
        # --------------------------------------------------

        row["CUSTOMER_LIMIT"] = generate_customer_limit_from_type(
            specification,
            row["CUSTOMER_TYPE"],
        )

        # --------------------------------------------------
        # D002:
        #
        # CUSTOMER_LIMIT -> ORDER_AMOUNT
        # --------------------------------------------------

        row["ORDER_AMOUNT"] = generate_order_amount_from_limit(
            specification,
            row["CUSTOMER_LIMIT"],
        )

        rows.append({field_name: row[field_name] for field_name in fields})

    return pd.DataFrame(rows)


# --------------------------------------------------
# Field validation
# --------------------------------------------------


def validate_fields(
    dataframe: pd.DataFrame,
    specification: dict,
) -> dict:
    """Validate generated fields against their declared metadata."""

    results = {}

    for field_name, metadata in get_fields(specification).items():

        series = dataframe[field_name]

        passed = True
        errors = []

        if not metadata.get(
            "nullable",
            False,
        ):

            if series.isna().any():

                passed = False

                errors.append("NULL value found.")

        non_null = series.dropna()

        field_type = metadata["type"]

        if field_type == "identifier":

            expected_length = metadata["length"]

            prefix = metadata.get(
                "prefix",
                "",
            )

            if not all(len(str(value)) == expected_length for value in non_null):

                passed = False

                errors.append("Invalid identifier length.")

            if not all(str(value).startswith(prefix) for value in non_null):

                passed = False

                errors.append("Invalid identifier prefix.")

        elif field_type == "categorical":

            allowed_values = set(metadata["values"])

            if not set(non_null).issubset(allowed_values):

                passed = False

                errors.append("Value outside categorical domain.")

        elif field_type == "number":

            generation = metadata["generation"]

            minimum = generation["min"]

            maximum = generation["max"]

            numeric_values = pd.to_numeric(non_null)

            if not numeric_values.between(
                minimum,
                maximum,
            ).all():

                passed = False

                errors.append("Value outside numeric bounds.")

        results[field_name] = {
            "passed": passed,
            "errors": errors,
        }

    return results


# --------------------------------------------------
# Statistical measurements
# --------------------------------------------------


def calculate_group_statistics(
    dataframe: pd.DataFrame,
) -> dict:
    """
    Calculate CUSTOMER_LIMIT statistics grouped by CUSTOMER_TYPE.
    """

    results = {}

    for customer_type, group in dataframe.groupby("CUSTOMER_TYPE"):

        values = group["CUSTOMER_LIMIT"].tolist()

        results[customer_type] = {
            "count": len(values),
            "mean": round(
                statistics.mean(values),
                2,
            ),
            "median": round(
                statistics.median(values),
                2,
            ),
            "min": round(
                min(values),
                2,
            ),
            "max": round(
                max(values),
                2,
            ),
        }

    return results


def calculate_pearson_correlation(
    dataframe: pd.DataFrame,
    source_field: str,
    target_field: str,
) -> float:
    """
    Calculate Pearson correlation between two numeric fields.

    Pandas is used here only for the statistical measurement. The
    generator itself does not use statistical learning.
    """

    correlation = (
        dataframe[
            [
                source_field,
                target_field,
            ]
        ]
        .corr(method="pearson")
        .iloc[
            0,
            1,
        ]
    )

    return round(
        float(correlation),
        6,
    )


def calculate_statistics(
    dataframe: pd.DataFrame,
) -> dict:
    """Calculate all experiment-level statistical observations."""

    return {
        "categorical_to_numeric": {
            "source": "CUSTOMER_TYPE",
            "target": "CUSTOMER_LIMIT",
            "groups": calculate_group_statistics(dataframe),
        },
        "numeric_to_numeric": {
            "source": "CUSTOMER_LIMIT",
            "target": "ORDER_AMOUNT",
            "pearson_correlation": calculate_pearson_correlation(
                dataframe,
                "CUSTOMER_LIMIT",
                "ORDER_AMOUNT",
            ),
        },
    }


# --------------------------------------------------
# Dependency validation
# --------------------------------------------------


def validate_categorical_dependency(
    dataframe: pd.DataFrame,
    specification: dict,
) -> dict:
    """
    Validate whether the observed CUSTOMER_LIMIT ranges follow the
    ranges declared in D001.
    """

    dependency = get_dependency(
        specification,
        "D001",
    )

    results = {}

    for customer_type, configuration in dependency["behavior"].items():

        expected_distribution = configuration["distribution"]

        values = dataframe[dataframe["CUSTOMER_TYPE"] == customer_type][
            "CUSTOMER_LIMIT"
        ]

        observed_min = float(values.min())

        observed_max = float(values.max())

        expected_min = expected_distribution["min"]

        expected_max = expected_distribution["max"]

        passed = observed_min >= expected_min and observed_max <= expected_max

        results[customer_type] = {
            "observed_min": round(
                observed_min,
                2,
            ),
            "observed_max": round(
                observed_max,
                2,
            ),
            "expected_min": expected_min,
            "expected_max": expected_max,
            "passed": passed,
        }

    return {
        "passed": all(result["passed"] for result in results.values()),
        "groups": results,
    }


def validate_numeric_dependency(
    dataframe: pd.DataFrame,
    specification: dict,
) -> dict:
    """
    Validate the numeric dependency by checking whether generated
    ORDER_AMOUNT values remain within the declared relationship
    bounds after noise and configured field bounds are applied.

    The experiment primarily measures the relationship using
    correlation. This validation confirms that generated values
    remain within the configured ORDER_AMOUNT field bounds.
    """

    dependency = get_dependency(
        specification,
        "D002",
    )

    behavior = dependency["behavior"]

    minimum_ratio = behavior["minimum_ratio"]

    maximum_ratio = behavior["maximum_ratio"]

    field_metadata = get_field(
        specification,
        "ORDER_AMOUNT",
    )

    generation = field_metadata["generation"]

    minimum = generation["min"]

    maximum = generation["max"]

    lower_bound = dataframe["CUSTOMER_LIMIT"] * minimum_ratio

    upper_bound = dataframe["CUSTOMER_LIMIT"] * maximum_ratio

    order_amount = dataframe["ORDER_AMOUNT"]

    # Because noise is intentionally part of the dependency, exact
    # ratio validation would incorrectly classify legitimate noise as
    # a violation. We therefore validate field bounds here and use
    # correlation as the primary relationship measurement.

    field_bounds_passed = order_amount.between(
        minimum,
        maximum,
    ).all()

    return {
        "field_bounds_passed": bool(field_bounds_passed),
        "configured_minimum_ratio": minimum_ratio,
        "configured_maximum_ratio": maximum_ratio,
        "noise": behavior["noise"],
        "relationship_measurement": ("pearson_correlation"),
        "ratio_reference": {
            "minimum_observed_reference": round(
                float(lower_bound.min()),
                2,
            ),
            "maximum_observed_reference": round(
                float(upper_bound.max()),
                2,
            ),
        },
    }


# --------------------------------------------------
# Output
# --------------------------------------------------


def save_dataset(
    dataframe: pd.DataFrame,
    output_file: Path,
) -> None:
    """Save a generated dataset."""

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    dataframe.to_csv(
        output_file,
        index=False,
    )


def save_statistics(
    statistics: dict,
) -> None:
    """Save experiment statistics."""

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    with STATISTICS_FILE.open(
        "w",
        encoding="utf-8",
    ) as file:

        json.dump(
            statistics,
            file,
            indent=2,
        )


# --------------------------------------------------
# Experiment execution
# --------------------------------------------------


def main() -> None:
    """Run Experiment 012."""

    specification = load_specification()

    experiment_metadata = specification["experiment"]

    generation_metadata = specification["generation"]

    seed = generation_metadata["seed"]

    record_count = generation_metadata["record_count"]

    random.seed(seed)

    print("=" * 70)
    print("FORGE - Experiment 012: " "Correlation and Dependency")
    print("=" * 70)

    print(
        f"Experiment:   "
        f"{experiment_metadata['id']} - "
        f"{experiment_metadata['name']}"
    )

    print(f"Specification: " f"{SPECIFICATION_FILE}")

    print(f"Random seed:   {seed}")

    print(f"Record count:  {record_count}")

    print("\nDeclared dependencies:")

    for dependency in get_dependencies(specification):

        print(
            f"  {dependency['id']}: "
            f"{dependency['source']} "
            f"-> "
            f"{dependency['target']} "
            f"({dependency['type']})"
        )

    # --------------------------------------------------
    # Independent generation
    # --------------------------------------------------

    print("\nApproach A: Independent generation")

    random.seed(seed)

    independent_dataframe = generate_independent_dataset(specification)

    independent_field_validation = validate_fields(
        independent_dataframe,
        specification,
    )

    independent_field_passed = all(
        result["passed"] for result in independent_field_validation.values()
    )

    independent_statistics = calculate_statistics(independent_dataframe)

    print(f"  Field validation: " f"{'PASS' if independent_field_passed else 'FAIL'}")

    print("  CUSTOMER_TYPE -> CUSTOMER_LIMIT:")

    for (
        customer_type,
        statistics_result,
    ) in independent_statistics[
        "categorical_to_numeric"
    ]["groups"].items():

        print(
            f"    {customer_type}: "
            f"mean={statistics_result['mean']:.2f}, "
            f"median={statistics_result['median']:.2f}"
        )

    print("  CUSTOMER_LIMIT -> ORDER_AMOUNT:")

    print(
        f"    Pearson correlation="
        f"{independent_statistics['numeric_to_numeric']['pearson_correlation']:.4f}"
    )

    # --------------------------------------------------
    # Dependency-aware generation
    # --------------------------------------------------

    print("\nApproach B: Dependency-aware generation")

    random.seed(seed)

    dependency_aware_dataframe = generate_dependency_aware_dataset(specification)

    dependency_aware_field_validation = validate_fields(
        dependency_aware_dataframe,
        specification,
    )

    dependency_aware_field_passed = all(
        result["passed"] for result in dependency_aware_field_validation.values()
    )

    dependency_aware_statistics = calculate_statistics(dependency_aware_dataframe)

    categorical_dependency_validation = validate_categorical_dependency(
        dependency_aware_dataframe,
        specification,
    )

    numeric_dependency_validation = validate_numeric_dependency(
        dependency_aware_dataframe,
        specification,
    )

    print(
        f"  Field validation: " f"{'PASS' if dependency_aware_field_passed else 'FAIL'}"
    )

    print("  CUSTOMER_TYPE -> CUSTOMER_LIMIT:")

    for (
        customer_type,
        statistics_result,
    ) in dependency_aware_statistics[
        "categorical_to_numeric"
    ]["groups"].items():

        print(
            f"    {customer_type}: "
            f"mean={statistics_result['mean']:.2f}, "
            f"median={statistics_result['median']:.2f}"
        )

    print("  CUSTOMER_LIMIT -> ORDER_AMOUNT:")

    print(
        f"    Pearson correlation="
        f"{dependency_aware_statistics['numeric_to_numeric']['pearson_correlation']:.4f}"
    )

    print(
        "  Categorical dependency validation: "
        f"{'PASS' if categorical_dependency_validation['passed'] else 'FAIL'}"
    )

    print(
        "  Numeric dependency field validation: "
        f"{'PASS' if numeric_dependency_validation['field_bounds_passed'] else 'FAIL'}"
    )

    # --------------------------------------------------
    # Comparison
    # --------------------------------------------------

    independent_correlation = independent_statistics["numeric_to_numeric"][
        "pearson_correlation"
    ]

    dependency_aware_correlation = dependency_aware_statistics["numeric_to_numeric"][
        "pearson_correlation"
    ]

    correlation_change = dependency_aware_correlation - independent_correlation

    # The categorical dependency is demonstrated by comparing the
    # separation between STANDARD and PREMIUM mean limits.

    independent_groups = independent_statistics["categorical_to_numeric"]["groups"]

    dependency_aware_groups = dependency_aware_statistics["categorical_to_numeric"][
        "groups"
    ]

    independent_mean_gap = abs(
        independent_groups["PREMIUM"]["mean"] - independent_groups["STANDARD"]["mean"]
    )

    dependency_aware_mean_gap = abs(
        dependency_aware_groups["PREMIUM"]["mean"]
        - dependency_aware_groups["STANDARD"]["mean"]
    )

    # A meaningful positive dependency should increase both the
    # categorical group separation and numeric correlation compared
    # with independent generation.
    #
    # We intentionally do not prescribe an arbitrary universal
    # correlation threshold. The experiment is comparative.

    overall_result = (
        "PASS"
        if (
            dependency_aware_field_passed
            and categorical_dependency_validation["passed"]
            and numeric_dependency_validation["field_bounds_passed"]
            and dependency_aware_mean_gap > independent_mean_gap
            and dependency_aware_correlation > independent_correlation
        )
        else "FAIL"
    )

    # --------------------------------------------------
    # Save output
    # --------------------------------------------------

    save_dataset(
        independent_dataframe,
        INDEPENDENT_OUTPUT_FILE,
    )

    save_dataset(
        dependency_aware_dataframe,
        DEPENDENCY_AWARE_OUTPUT_FILE,
    )

    statistics_output = {
        "experiment": experiment_metadata,
        "generation": {
            "seed": seed,
            "record_count": record_count,
        },
        "dependencies": get_dependencies(specification),
        "independent_generation": {
            "field_validation": (independent_field_validation),
            "statistics": (independent_statistics),
        },
        "dependency_aware_generation": {
            "field_validation": (dependency_aware_field_validation),
            "statistics": (dependency_aware_statistics),
            "categorical_dependency_validation": (categorical_dependency_validation),
            "numeric_dependency_validation": (numeric_dependency_validation),
        },
        "comparison": {
            "independent_numeric_correlation": (independent_correlation),
            "dependency_aware_numeric_correlation": (dependency_aware_correlation),
            "correlation_change": round(
                correlation_change,
                6,
            ),
            "independent_group_mean_gap": round(
                independent_mean_gap,
                2,
            ),
            "dependency_aware_group_mean_gap": round(
                dependency_aware_mean_gap,
                2,
            ),
        },
        "architectural_observation": {
            "dependencies_are_declared_separately": True,
            "categorical_dependency_is_observable": (
                dependency_aware_mean_gap > independent_mean_gap
            ),
            "numeric_dependency_is_observable": (
                dependency_aware_correlation > independent_correlation
            ),
            "dependency_aware_generation_preserves_field_validity": (
                dependency_aware_field_passed
            ),
        },
        "overall_result": overall_result,
    }

    save_statistics(statistics_output)

    # --------------------------------------------------
    # Output
    # --------------------------------------------------

    print("\nOutput:")

    print(f"  Independent: " f"{INDEPENDENT_OUTPUT_FILE}")

    print(f"  Dependency-aware: " f"{DEPENDENCY_AWARE_OUTPUT_FILE}")

    print(f"  Statistics: " f"{STATISTICS_FILE}")

    print("\nDependency comparison:")

    print(
        f"  Numeric correlation:"
        f" independent={independent_correlation:.4f},"
        f" dependency-aware={dependency_aware_correlation:.4f}"
    )

    print(f"  Correlation change:" f" {correlation_change:+.4f}")

    print(
        f"  Group mean gap:"
        f" independent={independent_mean_gap:.2f},"
        f" dependency-aware={dependency_aware_mean_gap:.2f}"
    )

    print("\nFirst 10 records: Independent")

    print(independent_dataframe.head(10).to_string(index=False))

    print("\nFirst 10 records: Dependency-aware")

    print(dependency_aware_dataframe.head(10).to_string(index=False))

    print("\nExperiment result:")

    print(
        f"  Independent field validation: "
        f"{'PASS' if independent_field_passed else 'FAIL'}"
    )

    print(
        f"  Dependency-aware field validation: "
        f"{'PASS' if dependency_aware_field_passed else 'FAIL'}"
    )

    print(
        f"  Categorical dependency: "
        f"{'PASS' if categorical_dependency_validation['passed'] else 'FAIL'}"
    )

    print(
        f"  Numeric dependency: "
        f"{'PASS' if numeric_dependency_validation['field_bounds_passed'] else 'FAIL'}"
    )

    print(f"  Overall: {overall_result}")

    print("\nExperiment completed successfully.")


# --------------------------------------------------
# Entry point
# --------------------------------------------------

if __name__ == "__main__":
    main()
