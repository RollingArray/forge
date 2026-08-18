"""
FORGE - Experiment 009: Optionality and Population
===================================================

Purpose
-------
This experiment tests whether field nullability and population behavior
can be represented as separate concerns.

The experiment builds on:

    Experiment 002 - Field Constraints
    Experiment 003 - Distribution-Controlled Generation
    Experiment 008 - Domain vs Generation Strategy

The experiment introduces explicit population behavior:

    - always populated
    - rate-based population
    - zero population
    - full population
    - conditional population

The experiment intentionally separates:

    NULLABILITY
        Whether a field is allowed to contain NULL.

    POPULATION
        Whether a value should be generated.

    GENERATION
        What value should be generated.

No machine learning, LLM, or real production data is used.

Experiment
----------
009 - Optionality and Population

Key Question
------------
How should FORGE distinguish between field optionality,
population behavior, and value generation?

Author
------
Ranjoy Sen

Status
------
Experimental

How to Run
----------
From the repository root:

    uv run python experiments/009_optionality_and_population/experiment.py

Output
------
The generated dataset is written to:

    experiments/009_optionality_and_population/output/generated_data.csv

Population statistics are written to:

    experiments/009_optionality_and_population/output/population_statistics.json

Important
---------
The generated data is synthetic and does not represent any real
production dataset.
"""

from collections import Counter
from pathlib import Path
import json
import random
import string

import pandas as pd

# --------------------------------------------------
# Experiment paths
# --------------------------------------------------

EXPERIMENT_DIR = Path(__file__).resolve().parent

SPECIFICATION_FILE = EXPERIMENT_DIR / "specification.json"

OUTPUT_DIR = EXPERIMENT_DIR / "output"

OUTPUT_FILE = OUTPUT_DIR / "generated_data.csv"

STATISTICS_FILE = OUTPUT_DIR / "population_statistics.json"


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
    """Retrieve a domain from the specification."""

    domains = specification.get(
        "domains",
        {},
    )

    if domain_name not in domains:
        raise ValueError(f"Domain not found: {domain_name}")

    values = domains[domain_name].get("values")

    if not values:
        raise ValueError(f"Domain '{domain_name}' must contain values.")

    return values


# --------------------------------------------------
# Generation helpers
# --------------------------------------------------


def generate_identifier(
    length: int,
    prefix: str,
    index: int,
) -> str:
    """Generate a fixed-width identifier."""

    numeric_length = length - len(prefix)

    if numeric_length <= 0:
        raise ValueError("Identifier length must be greater " "than prefix length.")

    return prefix + str(index).zfill(numeric_length)


def generate_string(
    minimum: int,
    maximum: int,
) -> str:
    """Generate a synthetic alphanumeric string."""

    length = random.randint(
        minimum,
        maximum,
    )

    characters = string.ascii_uppercase + string.digits

    return "".join(random.choice(characters) for _ in range(length))


def generate_categorical(
    values: list,
) -> str:
    """Generate a categorical value uniformly from a domain."""

    return random.choice(values)


# --------------------------------------------------
# Population handling
# --------------------------------------------------


def evaluate_population(
    population: dict | None,
    row: dict,
) -> bool:
    """
    Determine whether a field should receive a value.

    Supported population types:

        rate
        conditional

    If no population configuration is supplied,
    the field is considered always populated.
    """

    if population is None:
        return True

    population_type = population.get("type")

    if population_type == "rate":

        rate = population.get("rate")

        if rate is None:
            raise ValueError("Population rate is required.")

        if not 0.0 <= rate <= 1.0:
            raise ValueError("Population rate must be between 0.0 and 1.0.")

        return random.random() < rate

    if population_type == "conditional":

        condition = population.get("condition")

        if condition is None:
            raise ValueError("Conditional population requires a condition.")

        return evaluate_condition(
            condition,
            row,
        )

    raise ValueError(f"Unsupported population type: " f"{population_type}")


def evaluate_condition(
    condition: dict,
    row: dict,
) -> bool:
    """
    Evaluate a simple field condition.

    Supported operators:

        equals
        not_equals
    """

    field = condition.get("field")

    operator = condition.get("operator")

    expected_value = condition.get("value")

    if field not in row:
        raise ValueError(
            f"Condition references field " f"'{field}' before it has been generated."
        )

    actual_value = row[field]

    if operator == "equals":
        return actual_value == expected_value

    if operator == "not_equals":
        return actual_value != expected_value

    raise ValueError(f"Unsupported condition operator: " f"{operator}")


# --------------------------------------------------
# Field generation
# --------------------------------------------------


def generate_field_value(
    field_metadata: dict,
    specification: dict,
    index: int,
):
    """Generate a value according to field metadata."""

    field_type = field_metadata["type"]

    if field_type == "identifier":

        return generate_identifier(
            length=field_metadata["length"],
            prefix=field_metadata.get(
                "prefix",
                "",
            ),
            index=index,
        )

    if field_type == "categorical":

        domain_name = field_metadata.get("domain")

        if not domain_name:
            raise ValueError("Categorical field requires a domain.")

        domain_values = get_domain(
            specification,
            domain_name,
        )

        return generate_categorical(domain_values)

    if field_type == "string":

        return generate_string(
            minimum=field_metadata["min_length"],
            maximum=field_metadata["max_length"],
        )

    raise ValueError(f"Unsupported field type: {field_type}")


# --------------------------------------------------
# Dataset generation
# --------------------------------------------------


def generate_dataset(
    specification: dict,
) -> pd.DataFrame:
    """
    Generate the CUSTOMER dataset.

    Population is evaluated before value generation.

    This is intentional:

        Population decision
                ↓
          Generate value
                ↓
             Store value

    If the population decision is false, the generator is not called
    and the field receives NULL.
    """

    generation_metadata = specification["generation"]

    record_count = generation_metadata["record_count"]

    fields = specification["entities"]["CUSTOMER"]["fields"]

    rows = []

    for index in range(
        1,
        record_count + 1,
    ):

        row = {}

        for (
            field_name,
            field_metadata,
        ) in fields.items():

            nullable = field_metadata.get(
                "nullable",
                False,
            )

            population = field_metadata.get("population")

            should_populate = evaluate_population(
                population,
                row,
            )

            if not should_populate:

                if not nullable:
                    raise ValueError(
                        f"Field '{field_name}' "
                        "evaluated to NULL but "
                        "nullable=false."
                    )

                row[field_name] = None
                continue

            row[field_name] = generate_field_value(
                field_metadata=field_metadata,
                specification=specification,
                index=index,
            )

        rows.append(row)

    return pd.DataFrame(rows)


# --------------------------------------------------
# Validation
# --------------------------------------------------


def validate_nullability(
    dataframe: pd.DataFrame,
    specification: dict,
) -> dict:
    """
    Validate nullable and non-nullable fields.
    """

    fields = specification["entities"]["CUSTOMER"]["fields"]

    results = {}

    for (
        field_name,
        field_metadata,
    ) in fields.items():

        series = dataframe[field_name]

        null_count = int(series.isna().sum())

        nullable = field_metadata.get(
            "nullable",
            False,
        )

        passed = nullable or null_count == 0

        results[field_name] = {
            "nullable": nullable,
            "null_count": null_count,
            "passed": passed,
        }

    return results


def calculate_population_statistics(
    dataframe: pd.DataFrame,
    specification: dict,
) -> dict:
    """Calculate observed population behavior."""

    fields = specification["entities"]["CUSTOMER"]["fields"]

    results = {}

    for (
        field_name,
        field_metadata,
    ) in fields.items():

        series = dataframe[field_name]

        total = len(series)

        populated = int(series.notna().sum())

        null_count = int(series.isna().sum())

        observed_rate = populated / total if total else 0.0

        population = field_metadata.get("population")

        expected_rate = None
        population_type = "always"

        if population:

            population_type = population.get("type")

            if population_type == "rate":
                expected_rate = population.get("rate")

        results[field_name] = {
            "population_type": population_type,
            "expected_rate": expected_rate,
            "observed_rate": observed_rate,
            "populated_count": populated,
            "null_count": null_count,
            "total_count": total,
        }

    return results


def validate_boundary_rates(
    dataframe: pd.DataFrame,
    specification: dict,
) -> dict:
    """Validate explicit zero and full population boundaries."""

    fields = specification["entities"]["CUSTOMER"]["fields"]

    results = {}

    for (
        field_name,
        field_metadata,
    ) in fields.items():

        population = field_metadata.get("population")

        if not population:
            continue

        if population.get("type") != "rate":
            continue

        rate = population.get("rate")

        series = dataframe[field_name]

        if rate == 0.0:

            passed = bool(series.isna().all())

        elif rate == 1.0:

            passed = bool(series.notna().all())

        else:
            continue

        results[field_name] = {
            "configured_rate": rate,
            "passed": passed,
        }

    return results


def validate_conditional_population(
    dataframe: pd.DataFrame,
    specification: dict,
) -> dict:
    """
    Validate conditional population behavior.

    Currently the specification contains TAX_ID with:

        COUNTRY == US
            -> populated

        COUNTRY != US
            -> null
    """

    fields = specification["entities"]["CUSTOMER"]["fields"]

    results = {}

    for (
        field_name,
        field_metadata,
    ) in fields.items():

        population = field_metadata.get("population")

        if not population:
            continue

        if population.get("type") != "conditional":
            continue

        condition = population["condition"]

        condition_field = condition["field"]

        condition_operator = condition["operator"]

        condition_value = condition["value"]

        populated_when_condition_true = True
        null_when_condition_false = True

        for _, row in dataframe.iterrows():

            actual_value = row[condition_field]

            if condition_operator == "equals":

                condition_result = actual_value == condition_value

            elif condition_operator == "not_equals":

                condition_result = actual_value != condition_value

            else:
                raise ValueError(
                    f"Unsupported condition operator: " f"{condition_operator}"
                )

            field_is_populated = pd.notna(row[field_name])

            if condition_result:

                if not field_is_populated:
                    populated_when_condition_true = False

            else:

                if field_is_populated:
                    null_when_condition_false = False

        passed = populated_when_condition_true and null_when_condition_false

        results[field_name] = {
            "condition": condition,
            "populated_when_condition_true": (populated_when_condition_true),
            "null_when_condition_false": (null_when_condition_false),
            "passed": passed,
        }

    return results


# --------------------------------------------------
# Output
# --------------------------------------------------


def save_dataset(
    dataframe: pd.DataFrame,
) -> Path:
    """Save generated dataset."""

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    dataframe.to_csv(
        OUTPUT_FILE,
        index=False,
    )

    return OUTPUT_FILE


def save_statistics(
    statistics: dict,
) -> Path:
    """Save population statistics."""

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

    return STATISTICS_FILE


# --------------------------------------------------
# Experiment execution
# --------------------------------------------------


def main() -> None:
    """Run Experiment 009."""

    specification = load_specification()

    experiment_metadata = specification["experiment"]

    generation_metadata = specification["generation"]

    seed = generation_metadata["seed"]

    record_count = generation_metadata["record_count"]

    random.seed(seed)

    print("=" * 70)
    print("FORGE - Experiment 009: " "Optionality and Population")
    print("=" * 70)

    print(
        f"Experiment:   "
        f"{experiment_metadata['id']} - "
        f"{experiment_metadata['name']}"
    )

    print(f"Specification: " f"{SPECIFICATION_FILE}")

    print(f"Random seed:   {seed}")

    print(f"Record count:  {record_count}")

    print("\nGenerating dataset...")

    dataframe = generate_dataset(specification)

    print(f"  Generated {len(dataframe)} " "records for CUSTOMER")

    # --------------------------------------------------
    # Validation
    # --------------------------------------------------

    nullability_results = validate_nullability(
        dataframe,
        specification,
    )

    population_statistics = calculate_population_statistics(
        dataframe,
        specification,
    )

    boundary_results = validate_boundary_rates(
        dataframe,
        specification,
    )

    conditional_results = validate_conditional_population(
        dataframe,
        specification,
    )

    # --------------------------------------------------
    # Display population statistics
    # --------------------------------------------------

    print("\nPopulation statistics:")

    for (
        field_name,
        result,
    ) in population_statistics.items():

        expected = result["expected_rate"]

        observed = result["observed_rate"]

        if expected is not None:

            print(
                f"  {field_name:<25} "
                f"observed={observed:.2%}, "
                f"expected={expected:.2%}"
            )

        else:

            print(
                f"  {field_name:<25} " f"observed={observed:.2%}, " f"expected=always"
            )

    # --------------------------------------------------
    # Nullability validation
    # --------------------------------------------------

    print("\nNullability validation:")

    nullability_passed = True

    for (
        field_name,
        result,
    ) in nullability_results.items():

        passed = result["passed"]

        nullability_passed = nullability_passed and passed

        print(f"  {field_name:<25} " f"{'PASS' if passed else 'FAIL'}")

    # --------------------------------------------------
    # Boundary validation
    # --------------------------------------------------

    print("\nPopulation boundary validation:")

    boundary_passed = True

    for (
        field_name,
        result,
    ) in boundary_results.items():

        passed = result["passed"]

        boundary_passed = boundary_passed and passed

        print(
            f"  {field_name:<25} "
            f"rate={result['configured_rate']:.1f} "
            f"{'PASS' if passed else 'FAIL'}"
        )

    # --------------------------------------------------
    # Conditional validation
    # --------------------------------------------------

    print("\nConditional population validation:")

    conditional_passed = True

    for (
        field_name,
        result,
    ) in conditional_results.items():

        passed = result["passed"]

        conditional_passed = conditional_passed and passed

        condition = result["condition"]

        print(
            f"  {field_name:<25} "
            f"{condition['field']} "
            f"{condition['operator']} "
            f"{condition['value']} "
            f"-> "
            f"{'PASS' if passed else 'FAIL'}"
        )

    # --------------------------------------------------
    # Overall result
    # --------------------------------------------------

    overall_result = (
        "PASS"
        if (nullability_passed and boundary_passed and conditional_passed)
        else "FAIL"
    )

    # --------------------------------------------------
    # Results
    # --------------------------------------------------

    statistics = {
        "experiment": experiment_metadata,
        "generation": {
            "seed": seed,
            "record_count": record_count,
        },
        "population": population_statistics,
        "validation": {
            "nullability": nullability_results,
            "boundary": boundary_results,
            "conditional": conditional_results,
        },
        "architectural_observation": {
            "nullability_separated_from_population": True,
            "population_separated_from_generation": True,
            "conditional_population_supported": (len(conditional_results) > 0),
        },
        "overall_result": overall_result,
    }

    # --------------------------------------------------
    # Output
    # --------------------------------------------------

    output_file = save_dataset(dataframe)

    statistics_file = save_statistics(statistics)

    print("\nOutput:")

    print(f"  Dataset: " f"{output_file}")

    print(f"  Statistics: " f"{statistics_file}")

    print("\nFirst 20 records:")

    print(dataframe.head(20).to_string(index=False))

    print("\nExperiment result:")

    print(f"  Nullability: " f"{'PASS' if nullability_passed else 'FAIL'}")

    print(f"  Boundaries:   " f"{'PASS' if boundary_passed else 'FAIL'}")

    print(f"  Conditional:  " f"{'PASS' if conditional_passed else 'FAIL'}")

    print(f"  Overall:      " f"{overall_result}")

    print("\nExperiment completed successfully.")


# --------------------------------------------------
# Entry point
# --------------------------------------------------

if __name__ == "__main__":
    main()
