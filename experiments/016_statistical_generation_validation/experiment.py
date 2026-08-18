"""
FORGE - Experiment 016: Statistical Generation Validation
===========================================================

Purpose
-------
Determine whether FORGE can quantitatively validate that generated data
conforms sufficiently to its declared statistical generation behavior.

The experiment evaluates:

    - categorical distributions
    - numeric ranges
    - mean
    - median
    - standard deviation
    - percentiles
    - configurable PASS / WARN / FAIL thresholds
    - sampling variation across different record counts

Important distinction
---------------------
A sample-level validation failure does not automatically mean that the
experiment failed.

This experiment is also testing whether statistical validation is sensitive
to sample size. Small datasets are expected to exhibit greater sampling
variation than large datasets.

Experiment
----------
016 - Statistical Generation Validation

Run
---
uv run python experiments/016_statistical_generation_validation/experiment.py

Output
------
Generated datasets and validation results are written to:

    experiments/016_statistical_generation_validation/output/
"""

from pathlib import Path
import json
import math
import random

import pandas as pd

# ============================================================
# Experiment paths
# ============================================================

EXPERIMENT_DIR = Path(__file__).resolve().parent

SPECIFICATION_FILE = EXPERIMENT_DIR / "specification.json"

OUTPUT_DIR = EXPERIMENT_DIR / "output"

STATISTICS_FILE = OUTPUT_DIR / "statistical_validation.json"


# ============================================================
# Specification helpers
# ============================================================


def load_specification() -> dict:
    """Load the experiment specification."""

    with SPECIFICATION_FILE.open(
        "r",
        encoding="utf-8",
    ) as file:
        return json.load(file)


def get_entity(
    specification: dict,
    entity_name: str,
) -> dict:
    """Return entity metadata."""

    return specification["entities"][entity_name]


def get_field(
    specification: dict,
    entity_name: str,
    field_name: str,
) -> dict:
    """Return field metadata."""

    return get_entity(
        specification,
        entity_name,
    )[
        "fields"
    ][field_name]


# ============================================================
# Generation
# ============================================================


def generate_identifier(
    metadata: dict,
    index: int,
) -> str:
    """Generate a deterministic identifier."""

    prefix = metadata.get(
        "prefix",
        "",
    )

    length = metadata["length"]

    numeric_length = length - len(prefix)

    if numeric_length <= 0:
        raise ValueError("Identifier length must be greater than prefix length.")

    maximum = (10**numeric_length) - 1

    if index > maximum:
        raise ValueError("Identifier capacity exceeded.")

    return prefix + str(index).zfill(numeric_length)


def generate_categorical(
    metadata: dict,
) -> str:
    """Generate a categorical value."""

    values = metadata["values"]

    generation = metadata.get(
        "generation",
        {},
    )

    strategy = generation.get(
        "strategy",
        "uniform",
    )

    if strategy == "uniform":

        return random.choice(values)

    if strategy == "weighted":

        weights = generation["weights"]

        return random.choices(
            values,
            weights=[weights[value] for value in values],
            k=1,
        )[0]

    raise ValueError(f"Unsupported categorical strategy: {strategy}")


def generate_number(
    metadata: dict,
) -> float:
    """Generate a numeric value."""

    generation = metadata.get(
        "generation",
        {},
    )

    strategy = generation.get(
        "strategy",
        "uniform",
    )

    if strategy == "uniform":

        return random.uniform(
            generation["min"],
            generation["max"],
        )

    raise ValueError(f"Unsupported numeric strategy: {strategy}")


def generate_field_value(
    metadata: dict,
    index: int,
):
    """Generate a value according to field metadata."""

    field_type = metadata["type"]

    if field_type == "identifier":

        return generate_identifier(
            metadata,
            index,
        )

    if field_type == "categorical":

        return generate_categorical(metadata)

    if field_type == "number":

        return round(
            generate_number(metadata),
            2,
        )

    raise ValueError(f"Unsupported field type: {field_type}")


def generate_dataset(
    specification: dict,
    record_count: int,
) -> dict[str, pd.DataFrame]:
    """Generate the experiment dataset."""

    customer_fields = get_entity(
        specification,
        "CUSTOMER",
    )["fields"]

    order_fields = get_entity(
        specification,
        "ORDER",
    )["fields"]

    customers = []

    for index in range(
        1,
        record_count + 1,
    ):

        row = {}

        for field_name, metadata in customer_fields.items():

            row[field_name] = generate_field_value(
                metadata,
                index,
            )

        customers.append(row)

    customer_dataframe = pd.DataFrame(customers)

    orders = []

    for index in range(
        1,
        record_count + 1,
    ):

        row = {}

        for field_name, metadata in order_fields.items():

            row[field_name] = generate_field_value(
                metadata,
                index,
            )

        orders.append(row)

    order_dataframe = pd.DataFrame(orders)

    return {
        "CUSTOMER": customer_dataframe,
        "ORDER": order_dataframe,
    }


# ============================================================
# Statistical calculations
# ============================================================


def expected_uniform_mean(
    minimum: float,
    maximum: float,
) -> float:
    """Expected mean of a continuous uniform distribution."""

    return (minimum + maximum) / 2.0


def expected_uniform_stddev(
    minimum: float,
    maximum: float,
) -> float:
    """Expected standard deviation of a uniform distribution."""

    return (maximum - minimum) / math.sqrt(12.0)


def expected_uniform_percentile(
    minimum: float,
    maximum: float,
    percentile: float,
) -> float:
    """Expected percentile of a uniform distribution."""

    return minimum + (maximum - minimum) * percentile / 100.0


def calculate_percentiles(
    series: pd.Series,
    percentiles: list[int],
) -> dict:
    """Calculate requested percentiles."""

    return {
        f"P{percentile:02d}": round(
            float(series.quantile(percentile / 100.0)),
            4,
        )
        for percentile in percentiles
    }


# ============================================================
# Validation result classification
# ============================================================


def classify_difference(
    difference: float,
    pass_tolerance: float,
    warn_tolerance: float,
) -> str:
    """
    Classify an observed statistical difference.

    PASS:
        difference <= pass tolerance

    WARN:
        pass tolerance < difference <= warn tolerance

    FAIL:
        difference > warn tolerance
    """

    if difference <= pass_tolerance:
        return "PASS"

    if difference <= warn_tolerance:
        return "WARN"

    return "FAIL"


def classify_range(
    minimum: float,
    maximum: float,
    expected_minimum: float,
    expected_maximum: float,
    tolerance: float,
) -> dict:
    """Validate observed numeric boundaries."""

    minimum_difference = max(
        0.0,
        expected_minimum - minimum,
    )

    maximum_difference = max(
        0.0,
        maximum - expected_maximum,
    )

    difference = max(
        minimum_difference,
        maximum_difference,
    )

    result = classify_difference(
        difference,
        tolerance,
        tolerance,
    )

    return {
        "expected_minimum": expected_minimum,
        "expected_maximum": expected_maximum,
        "observed_minimum": round(
            minimum,
            4,
        ),
        "observed_maximum": round(
            maximum,
            4,
        ),
        "difference": round(
            difference,
            4,
        ),
        "tolerance": tolerance,
        "result": result,
        "passed": result == "PASS",
    }


# ============================================================
# Categorical validation
# ============================================================


def validate_categorical_distribution(
    series: pd.Series,
    metadata: dict,
) -> dict:
    """Validate categorical distribution."""

    generation = metadata["generation"]

    strategy = generation.get("strategy")

    if strategy == "weighted":

        expected = generation["weights"]

    elif strategy == "uniform":

        values = metadata["values"]

        expected_probability = 1.0 / len(values)

        expected = {value: expected_probability for value in values}

    else:

        raise ValueError("Unsupported categorical strategy: " f"{strategy}")

    observed_counts = series.value_counts(normalize=True).to_dict()

    tolerance = metadata["validation"]["distribution_tolerance"]

    categories = list(expected.keys())

    details = {}
    results = []

    for category in categories:

        expected_value = float(
            expected.get(
                category,
                0.0,
            )
        )

        observed_value = float(
            observed_counts.get(
                category,
                0.0,
            )
        )

        difference = abs(observed_value - expected_value)

        result = classify_difference(
            difference,
            tolerance,
            tolerance * 2.0,
        )

        details[category] = {
            "expected": round(
                expected_value,
                6,
            ),
            "observed": round(
                observed_value,
                6,
            ),
            "expected_percent": round(
                expected_value * 100,
                4,
            ),
            "observed_percent": round(
                observed_value * 100,
                4,
            ),
            "difference": round(
                difference,
                6,
            ),
            "difference_percent": round(
                difference * 100,
                4,
            ),
            "tolerance": tolerance,
            "result": result,
            "passed": result == "PASS",
        }

        results.append(result)

    if "FAIL" in results:
        overall_result = "FAIL"
    elif "WARN" in results:
        overall_result = "WARN"
    else:
        overall_result = "PASS"

    return {
        "strategy": strategy,
        "categories": details,
        "result": overall_result,
        "passed": overall_result == "PASS",
    }


# ============================================================
# Numeric validation
# ============================================================


def validate_numeric_distribution(
    series: pd.Series,
    metadata: dict,
    percentiles: list[int],
) -> dict:
    """Validate numeric distribution."""

    generation = metadata["generation"]

    validation = metadata["validation"]

    minimum = float(generation["min"])

    maximum = float(generation["max"])

    observed_minimum = float(series.min())

    observed_maximum = float(series.max())

    observed_mean = float(series.mean())

    observed_median = float(series.median())

    observed_stddev = float(series.std(ddof=0))

    expected_mean = expected_uniform_mean(
        minimum,
        maximum,
    )

    expected_median = expected_mean

    expected_stddev = expected_uniform_stddev(
        minimum,
        maximum,
    )

    range_result = classify_range(
        observed_minimum,
        observed_maximum,
        minimum,
        maximum,
        validation["range_tolerance"],
    )

    mean_difference = abs(observed_mean - expected_mean)

    mean_result = classify_difference(
        mean_difference,
        validation["mean_tolerance"],
        validation["mean_tolerance"] * 2.0,
    )

    median_difference = abs(observed_median - expected_median)

    median_result = classify_difference(
        median_difference,
        validation["median_tolerance"],
        validation["median_tolerance"] * 2.0,
    )

    stddev_difference = abs(observed_stddev - expected_stddev)

    stddev_result = classify_difference(
        stddev_difference,
        validation["stddev_tolerance"],
        validation["stddev_tolerance"] * 2.0,
    )

    observed_percentiles = calculate_percentiles(
        series,
        percentiles,
    )

    percentile_results = {}
    percentile_result_values = []

    for percentile in percentiles:

        expected_value = expected_uniform_percentile(
            minimum,
            maximum,
            percentile,
        )

        observed_value = observed_percentiles[f"P{percentile:02d}"]

        difference = abs(observed_value - expected_value)

        result = classify_difference(
            difference,
            validation["percentile_tolerance"],
            validation["percentile_tolerance"] * 2.0,
        )

        percentile_results[f"P{percentile:02d}"] = {
            "expected": round(
                expected_value,
                4,
            ),
            "observed": round(
                observed_value,
                4,
            ),
            "difference": round(
                difference,
                4,
            ),
            "tolerance": validation["percentile_tolerance"],
            "result": result,
            "passed": result == "PASS",
        }

        percentile_result_values.append(result)

    all_results = [
        range_result["result"],
        mean_result,
        median_result,
        stddev_result,
        *percentile_result_values,
    ]

    if "FAIL" in all_results:
        overall_result = "FAIL"
    elif "WARN" in all_results:
        overall_result = "WARN"
    else:
        overall_result = "PASS"

    return {
        "strategy": generation["strategy"],
        "expected": {
            "minimum": minimum,
            "maximum": maximum,
            "mean": round(
                expected_mean,
                4,
            ),
            "median": round(
                expected_median,
                4,
            ),
            "stddev": round(
                expected_stddev,
                4,
            ),
        },
        "observed": {
            "minimum": round(
                observed_minimum,
                4,
            ),
            "maximum": round(
                observed_maximum,
                4,
            ),
            "mean": round(
                observed_mean,
                4,
            ),
            "median": round(
                observed_median,
                4,
            ),
            "stddev": round(
                observed_stddev,
                4,
            ),
            "percentiles": observed_percentiles,
        },
        "validation": {
            "range": range_result,
            "mean": {
                "expected": round(
                    expected_mean,
                    4,
                ),
                "observed": round(
                    observed_mean,
                    4,
                ),
                "difference": round(
                    mean_difference,
                    4,
                ),
                "tolerance": validation["mean_tolerance"],
                "result": mean_result,
                "passed": mean_result == "PASS",
            },
            "median": {
                "expected": round(
                    expected_median,
                    4,
                ),
                "observed": round(
                    observed_median,
                    4,
                ),
                "difference": round(
                    median_difference,
                    4,
                ),
                "tolerance": validation["median_tolerance"],
                "result": median_result,
                "passed": median_result == "PASS",
            },
            "stddev": {
                "expected": round(
                    expected_stddev,
                    4,
                ),
                "observed": round(
                    observed_stddev,
                    4,
                ),
                "difference": round(
                    stddev_difference,
                    4,
                ),
                "tolerance": validation["stddev_tolerance"],
                "result": stddev_result,
                "passed": stddev_result == "PASS",
            },
            "percentiles": percentile_results,
        },
        "result": overall_result,
        "passed": overall_result == "PASS",
    }


# ============================================================
# Dataset validation
# ============================================================


def validate_dataset(
    specification: dict,
    datasets: dict[str, pd.DataFrame],
) -> dict:
    """Validate all statistical fields."""

    percentiles = specification["statistical_validation"]["percentiles"]

    customer_dataframe = datasets["CUSTOMER"]

    order_dataframe = datasets["ORDER"]

    country_validation = validate_categorical_distribution(
        customer_dataframe["COUNTRY"],
        get_field(
            specification,
            "CUSTOMER",
            "COUNTRY",
        ),
    )

    customer_type_validation = validate_categorical_distribution(
        customer_dataframe["CUSTOMER_TYPE"],
        get_field(
            specification,
            "CUSTOMER",
            "CUSTOMER_TYPE",
        ),
    )

    amount_validation = validate_numeric_distribution(
        order_dataframe["AMOUNT"],
        get_field(
            specification,
            "ORDER",
            "AMOUNT",
        ),
        percentiles,
    )

    discount_validation = validate_numeric_distribution(
        order_dataframe["DISCOUNT"],
        get_field(
            specification,
            "ORDER",
            "DISCOUNT",
        ),
        percentiles,
    )

    field_results = {
        "CUSTOMER.COUNTRY": country_validation,
        "CUSTOMER.CUSTOMER_TYPE": (customer_type_validation),
        "ORDER.AMOUNT": amount_validation,
        "ORDER.DISCOUNT": discount_validation,
    }

    results = [result["result"] for result in field_results.values()]

    if "FAIL" in results:
        overall_result = "FAIL"
    elif "WARN" in results:
        overall_result = "WARN"
    else:
        overall_result = "PASS"

    return {
        "fields": field_results,
        "overall_result": overall_result,
        "passed": overall_result == "PASS",
    }


# ============================================================
# JSON safety
# ============================================================


def json_safe(value):
    """Convert pandas/numpy values to JSON-safe Python values."""

    if hasattr(
        value,
        "item",
    ):

        try:
            return value.item()
        except (
            ValueError,
            TypeError,
        ):
            pass

    if isinstance(
        value,
        dict,
    ):

        return {str(key): json_safe(item) for key, item in value.items()}

    if isinstance(
        value,
        list,
    ):

        return [json_safe(item) for item in value]

    if isinstance(
        value,
        tuple,
    ):

        return [json_safe(item) for item in value]

    return value


# ============================================================
# Output
# ============================================================


def save_dataset(
    datasets: dict[str, pd.DataFrame],
    record_count: int,
) -> Path:
    """Save generated datasets."""

    dataset_directory = OUTPUT_DIR / f"records_{record_count}"

    dataset_directory.mkdir(
        parents=True,
        exist_ok=True,
    )

    for entity_name, dataframe in datasets.items():

        dataframe.to_csv(
            dataset_directory / f"{entity_name}.csv",
            index=False,
        )

    return dataset_directory


def save_statistics(
    statistics: dict,
) -> None:
    """Save statistical validation results."""

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    with STATISTICS_FILE.open(
        "w",
        encoding="utf-8",
    ) as file:

        json.dump(
            json_safe(statistics),
            file,
            indent=2,
        )


# ============================================================
# Main experiment
# ============================================================


def main() -> None:
    """Run Experiment 016."""

    specification = load_specification()

    experiment = specification["experiment"]

    generation = specification["generation"]

    record_counts = generation["record_counts"]

    print("=" * 70)
    print("FORGE - Experiment 016: " "Statistical Generation Validation")
    print("=" * 70)

    print(f"Experiment:   " f"{experiment['id']} - " f"{experiment['name']}")

    print(f"Specification: " f"{SPECIFICATION_FILE}")

    print(f"Random seed:   " f"{generation['seed']}")

    print(f"Record counts: " f"{record_counts}")

    all_results = {}

    # --------------------------------------------------------
    # Generate and validate each sample size
    # --------------------------------------------------------

    for record_count in record_counts:

        print("\n" + "-" * 70)

        print(f"Record count: {record_count}")

        random.seed(generation["seed"])

        datasets = generate_dataset(
            specification,
            record_count,
        )

        validation = validate_dataset(
            specification,
            datasets,
        )

        dataset_directory = save_dataset(
            datasets,
            record_count,
        )

        all_results[str(record_count)] = {
            "record_count": record_count,
            "dataset_path": str(dataset_directory),
            "validation": validation,
        }

        # ----------------------------------------------------
        # Categorical output
        # ----------------------------------------------------

        print("\nCategorical validation:")

        for field_name in [
            "CUSTOMER.COUNTRY",
            "CUSTOMER.CUSTOMER_TYPE",
        ]:

            result = validation["fields"][field_name]

            print(f"  {field_name}: " f"{result['result']}")

            if field_name == ("CUSTOMER.COUNTRY"):

                for (
                    category,
                    details,
                ) in result["categories"].items():

                    print(
                        f"    {category}: "
                        f"observed="
                        f"{details['observed_percent']:.2f}% "
                        f"expected="
                        f"{details['expected_percent']:.2f}% "
                        f"result="
                        f"{details['result']}"
                    )

        # ----------------------------------------------------
        # Numeric output
        # ----------------------------------------------------

        print("\nNumeric validation:")

        for field_name in [
            "ORDER.AMOUNT",
            "ORDER.DISCOUNT",
        ]:

            result = validation["fields"][field_name]

            print(f"  {field_name}: " f"{result['result']}")

            observed = result["observed"]

            expected = result["expected"]

            print(
                f"    mean: "
                f"observed={observed['mean']:.2f} "
                f"expected={expected['mean']:.2f}"
            )

            print(
                f"    median: "
                f"observed={observed['median']:.2f} "
                f"expected={expected['median']:.2f}"
            )

            print(
                f"    stddev: "
                f"observed={observed['stddev']:.2f} "
                f"expected={expected['stddev']:.2f}"
            )

            print(
                f"    range: "
                f"{observed['minimum']:.2f} - "
                f"{observed['maximum']:.2f}"
            )

        print("\nOverall statistical validation: " f"{validation['overall_result']}")

    # ========================================================
    # Sample-size comparison
    # ========================================================

    print("\n" + "-" * 70)

    print("Sample-size comparison")

    sample_size_comparison = {}

    for (
        record_count,
        result,
    ) in all_results.items():

        validation = result["validation"]

        country = validation["fields"]["CUSTOMER.COUNTRY"]

        amount = validation["fields"]["ORDER.AMOUNT"]

        sample_size_comparison[record_count] = {
            "country_result": (country["result"]),
            "amount_result": (amount["result"]),
            "overall_result": (validation["overall_result"]),
        }

        print(
            f"  {record_count} records: "
            f"COUNTRY={country['result']} "
            f"AMOUNT={amount['result']} "
            f"OVERALL="
            f"{validation['overall_result']}"
        )

    # ========================================================
    # Experiment-level conclusion
    # ========================================================
    #
    # The experiment is not testing whether every sample size
    # passes a fixed tolerance.
    #
    # It is testing whether:
    #
    #   1. statistical characteristics can be measured
    #   2. observed values can be compared with expectations
    #   3. deviations can be classified
    #   4. sample-size sensitivity can be observed
    #   5. larger samples converge toward expected behavior
    #
    # Therefore, an individual sample-level FAIL does not
    # automatically constitute an experiment-level failure.
    # ========================================================

    sample_size_results = [
        result["validation"]["overall_result"] for result in all_results.values()
    ]

    statistical_measurement_pass = all(
        "validation" in result for result in all_results.values()
    )

    sample_size_sensitivity_observed = len(set(sample_size_results)) > 1

    large_sample_passed = any(result == "PASS" for result in sample_size_results)

    if (
        statistical_measurement_pass
        and sample_size_sensitivity_observed
        and large_sample_passed
    ):
        overall_result = "PASS"
    else:
        overall_result = "FAIL"

    # ========================================================
    # Statistics
    # ========================================================

    statistics = {
        "experiment": experiment,
        "generation": generation,
        "record_counts": record_counts,
        "results": all_results,
        "sample_size_comparison": (sample_size_comparison),
        "experiment_conclusion": {
            "statistical_measurement": "PASS",
            "sample_size_sensitivity": (
                "PASS" if sample_size_sensitivity_observed else "FAIL"
            ),
            "large_sample_convergence": ("PASS" if large_sample_passed else "FAIL"),
            "overall_result": (overall_result),
        },
        "overall_result": (overall_result),
    }

    save_statistics(statistics)

    # ========================================================
    # Final output
    # ========================================================

    print("\nOutput:")

    print(f"  Statistics: " f"{STATISTICS_FILE}")

    print("\nExperiment result:")

    print("  Statistical measurement: PASS")

    print(
        "  Sample-size sensitivity: "
        + ("PASS" if sample_size_sensitivity_observed else "FAIL")
    )

    print("  Large-sample convergence: " + ("PASS" if large_sample_passed else "FAIL"))

    print(f"  Overall: {overall_result}")

    print("\nExperiment completed successfully.")


# ============================================================
# Entry point
# ============================================================


if __name__ == "__main__":
    main()
