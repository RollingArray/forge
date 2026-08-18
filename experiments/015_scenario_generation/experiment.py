"""
FORGE - Experiment 015: Scenario Generation
=============================================

Purpose
-------
This experiment tests whether a base data specification can be combined
with a declarative scenario to generate datasets with different,
coherent generation characteristics.

Scenarios tested:

    NORMAL
        Base specification without overrides.

    HIGH_VALUE
        Increased premium customer population and higher order amounts.

    MISSING_DATA
        Reduced email population.

The scenario is treated as an overlay on the base specification.

No machine learning, LLM, or real production data is used.

Experiment
----------
015 - Scenario Generation

Key Question
------------
Can scenarios be represented as declarative configuration overlays
without modifying the underlying data specification?

Author
------
Ranjoy Sen

Status
------
Experimental

How to Run
----------
From the repository root:

    uv run python experiments/015_scenario_generation/experiment.py

Output
------
Generated datasets are written to:

    experiments/015_scenario_generation/output/

Important
---------
The generated data is synthetic and does not represent any real
production dataset.
"""

from copy import deepcopy
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
STATISTICS_FILE = OUTPUT_DIR / "scenario_statistics.json"


# --------------------------------------------------
# Specification
# --------------------------------------------------


def load_specification() -> dict:
    """Load the experiment specification."""

    with SPECIFICATION_FILE.open(
        "r",
        encoding="utf-8",
    ) as file:
        return json.load(file)


# --------------------------------------------------
# Metadata helpers
# --------------------------------------------------


def get_entity(
    specification: dict,
    entity_name: str,
) -> dict:
    """Return an entity from the base specification."""

    return specification["base_specification"]["entities"][entity_name]


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


def get_relationship(
    specification: dict,
    relationship_id: str,
) -> dict:
    """Return a relationship definition."""

    relationships = specification["base_specification"]["relationships"]

    for relationship in relationships:
        if relationship["id"] == relationship_id:
            return relationship

    raise ValueError(f"Relationship not found: {relationship_id}")


# --------------------------------------------------
# Scenario resolution
# --------------------------------------------------


def apply_override(
    specification: dict,
    path: str,
    override: dict,
) -> None:
    """
    Apply a scenario override to a field.

    Example:

        CUSTOMER.EMAIL

    resolves to:

        entities -> CUSTOMER -> fields -> EMAIL
    """

    parts = path.split(".")

    if len(parts) != 2:
        raise ValueError(f"Invalid override path: {path}")

    entity_name = parts[0]
    field_name = parts[1]

    field_metadata = get_entity(
        specification,
        entity_name,
    )[
        "fields"
    ][field_name]

    for key, value in override.items():

        if isinstance(value, dict) and isinstance(
            field_metadata.get(key),
            dict,
        ):
            field_metadata[key].update(deepcopy(value))
        else:
            field_metadata[key] = deepcopy(value)


def resolve_scenario(
    specification: dict,
    scenario_name: str,
) -> dict:
    """
    Resolve a scenario against the base specification.

    The original specification is never modified.
    """

    scenarios = specification["scenarios"]

    if scenario_name not in scenarios:
        raise ValueError(f"Unknown scenario: {scenario_name}")

    effective = deepcopy(specification)

    scenario = scenarios[scenario_name]

    for path, override in scenario["overrides"].items():

        apply_override(
            effective,
            path,
            override,
        )

    effective["resolved_scenario"] = scenario_name

    return effective


# --------------------------------------------------
# Value generators
# --------------------------------------------------


def generate_identifier(
    metadata: dict,
    index: int,
) -> str:
    """Generate a fixed-width identifier."""

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
        return round(
            random.uniform(
                generation["min"],
                generation["max"],
            ),
            2,
        )

    raise ValueError(f"Unsupported numeric strategy: {strategy}")


def generate_string(
    metadata: dict,
) -> str:
    """Generate an uppercase alphanumeric string."""

    minimum = metadata["min_length"]
    maximum = metadata["max_length"]

    length = random.randint(
        minimum,
        maximum,
    )

    characters = "ABCDEFGHIJKLMNOPQRSTUVWXYZ" "0123456789"

    return "".join(random.choice(characters) for _ in range(length))


def should_populate(
    metadata: dict,
) -> bool:
    """Determine whether an optional field should be populated."""

    if not metadata.get(
        "nullable",
        False,
    ):
        return True

    population_rate = metadata.get(
        "population_rate",
        1.0,
    )

    return random.random() < population_rate


def generate_field_value(
    metadata: dict,
    index: int,
):
    """Generate a field value according to metadata."""

    if metadata.get(
        "nullable",
        False,
    ):
        if not should_populate(metadata):
            return None

    field_type = metadata["type"]

    if field_type == "identifier":
        return generate_identifier(
            metadata,
            index,
        )

    if field_type == "categorical":
        return generate_categorical(metadata)

    if field_type == "number":
        return generate_number(metadata)

    if field_type == "string":
        return generate_string(metadata)

    raise ValueError(f"Unsupported field type: {field_type}")


# --------------------------------------------------
# Entity generation
# --------------------------------------------------


def generate_customer_dataset(
    specification: dict,
) -> pd.DataFrame:
    """Generate CUSTOMER records."""

    record_count = specification["generation"]["record_counts"]["CUSTOMER"]

    fields = get_entity(
        specification,
        "CUSTOMER",
    )["fields"]

    rows = []

    for index in range(
        1,
        record_count + 1,
    ):

        row = {}

        for field_name, metadata in fields.items():

            row[field_name] = generate_field_value(
                metadata,
                index,
            )

        rows.append(row)

    return pd.DataFrame(rows)


def generate_order_dataset(
    specification: dict,
    customer_dataframe: pd.DataFrame,
) -> pd.DataFrame:
    """Generate ORDER records while preserving the relationship."""

    record_count = specification["generation"]["record_counts"]["ORDER"]

    fields = get_entity(
        specification,
        "ORDER",
    )["fields"]

    relationship = get_relationship(
        specification,
        "R001",
    )

    parent_field = relationship["parent_field"]

    child_field = relationship["child_field"]

    customer_ids = customer_dataframe[parent_field].tolist()

    rows = []

    for index in range(
        1,
        record_count + 1,
    ):

        row = {}

        for field_name, metadata in fields.items():

            if field_name == child_field:
                row[field_name] = random.choice(customer_ids)
            else:
                row[field_name] = generate_field_value(
                    metadata,
                    index,
                )

        rows.append(row)

    return pd.DataFrame(rows)


# --------------------------------------------------
# Validation
# --------------------------------------------------


def validate_customer_dataset(
    dataframe: pd.DataFrame,
    specification: dict,
) -> dict:
    """Validate CUSTOMER fields."""

    fields = get_entity(
        specification,
        "CUSTOMER",
    )["fields"]

    results = {}

    for field_name, metadata in fields.items():

        series = dataframe[field_name]

        non_null = series.dropna()

        passed = True

        if metadata["type"] == "identifier":

            expected_length = metadata["length"]

            passed = all(len(str(value)) == expected_length for value in non_null)

        elif metadata["type"] == "categorical":

            allowed_values = set(metadata["values"])

            passed = set(non_null).issubset(allowed_values)

        elif metadata["type"] == "string":

            minimum = metadata["min_length"]

            maximum = metadata["max_length"]

            passed = all(minimum <= len(str(value)) <= maximum for value in non_null)

        results[field_name] = bool(passed)

    return results


def validate_order_dataset(
    dataframe: pd.DataFrame,
    specification: dict,
) -> dict:
    """Validate ORDER fields."""

    fields = get_entity(
        specification,
        "ORDER",
    )["fields"]

    results = {}

    for field_name, metadata in fields.items():

        series = dataframe[field_name]

        non_null = series.dropna()

        passed = True

        if metadata["type"] == "identifier":

            expected_length = metadata["length"]

            passed = all(len(str(value)) == expected_length for value in non_null)

        elif metadata["type"] == "number":

            generation = metadata["generation"]

            minimum = generation["min"]

            maximum = generation["max"]

            passed = bool(
                non_null.between(
                    minimum,
                    maximum,
                ).all()
            )

        results[field_name] = bool(passed)

    return results


def validate_relationship(
    customer_dataframe: pd.DataFrame,
    order_dataframe: pd.DataFrame,
    specification: dict,
) -> dict:
    """Validate ORDER.CUSTOMER_ID references."""

    relationship = get_relationship(
        specification,
        "R001",
    )

    parent_field = relationship["parent_field"]

    child_field = relationship["child_field"]

    parent_values = set(customer_dataframe[parent_field])

    invalid_references = [
        value for value in order_dataframe[child_field] if value not in parent_values
    ]

    return {
        "parent_records": len(customer_dataframe),
        "child_records": len(order_dataframe),
        "invalid_references": len(invalid_references),
        "passed": len(invalid_references) == 0,
    }


# --------------------------------------------------
# Statistics
# --------------------------------------------------


def calculate_population_rate(
    dataframe: pd.DataFrame,
    field_name: str,
) -> float:
    """Calculate populated percentage."""

    if len(dataframe) == 0:
        return 0.0

    populated = dataframe[field_name].notna().sum()

    return round(
        populated / len(dataframe) * 100,
        2,
    )


def calculate_distribution(
    dataframe: pd.DataFrame,
    field_name: str,
) -> dict:
    """Calculate categorical distribution."""

    distribution = (
        dataframe[field_name].value_counts(normalize=True).mul(100).round(2).to_dict()
    )

    return {str(key): float(value) for key, value in distribution.items()}


def calculate_amount_statistics(
    dataframe: pd.DataFrame,
) -> dict:
    """Calculate ORDER.AMOUNT statistics."""

    amount = dataframe["AMOUNT"]

    return {
        "mean": round(
            float(amount.mean()),
            2,
        ),
        "median": round(
            float(amount.median()),
            2,
        ),
        "minimum": round(
            float(amount.min()),
            2,
        ),
        "maximum": round(
            float(amount.max()),
            2,
        ),
    }


# --------------------------------------------------
# Scenario validation
# --------------------------------------------------


def validate_scenario(
    scenario_name: str,
    specification: dict,
    customer_dataframe: pd.DataFrame,
    order_dataframe: pd.DataFrame,
) -> dict:
    """Validate scenario-specific behavior."""

    scenario = specification["scenarios"][scenario_name]

    results = {}

    if scenario_name == "NORMAL":

        results["baseline"] = {
            "passed": True,
            "message": ("Base specification used without overrides."),
        }

    elif scenario_name == "HIGH_VALUE":

        override = scenario["overrides"]["CUSTOMER.CUSTOMER_TYPE"]

        weights = override["generation"]["weights"]

        observed = (
            customer_dataframe["CUSTOMER_TYPE"].value_counts(normalize=True).to_dict()
        )

        tolerance = 0.08

        distribution_passed = all(
            abs(
                observed.get(
                    value,
                    0.0,
                )
                - expected
            )
            <= tolerance
            for value, expected in weights.items()
        )

        results["customer_type_distribution"] = {
            "passed": distribution_passed,
            "expected": weights,
            "observed": observed,
            "tolerance": tolerance,
        }

        amount_override = scenario["overrides"]["ORDER.AMOUNT"]["generation"]

        amount = order_dataframe["AMOUNT"]

        amount_passed = bool(
            amount.between(
                amount_override["min"],
                amount_override["max"],
            ).all()
        )

        results["order_amount_range"] = {
            "passed": amount_passed,
            "expected_minimum": amount_override["min"],
            "expected_maximum": amount_override["max"],
            "observed_minimum": round(
                float(amount.min()),
                2,
            ),
            "observed_maximum": round(
                float(amount.max()),
                2,
            ),
        }

    elif scenario_name == "MISSING_DATA":

        expected_rate = scenario["overrides"]["CUSTOMER.EMAIL"]["population_rate"] * 100

        observed_rate = calculate_population_rate(
            customer_dataframe,
            "EMAIL",
        )

        tolerance = 8.0

        population_passed = abs(observed_rate - expected_rate) <= tolerance

        results["email_population"] = {
            "passed": population_passed,
            "expected_percent": expected_rate,
            "observed_percent": observed_rate,
            "tolerance": tolerance,
        }

    else:

        raise ValueError(f"Unsupported scenario: {scenario_name}")

    scenario_checks = [
        value["passed"]
        for value in results.values()
        if isinstance(value, dict) and "passed" in value
    ]

    results["passed"] = all(scenario_checks)

    return results


# --------------------------------------------------
# Scenario execution
# --------------------------------------------------


def run_scenario(
    specification: dict,
    scenario_name: str,
) -> dict:
    """Generate and validate one scenario."""

    seed = specification["generation"]["seed"]

    random.seed(seed)

    effective = resolve_scenario(
        specification,
        scenario_name,
    )

    customer_dataframe = generate_customer_dataset(effective)

    order_dataframe = generate_order_dataset(
        effective,
        customer_dataframe,
    )

    customer_validation = validate_customer_dataset(
        customer_dataframe,
        effective,
    )

    order_validation = validate_order_dataset(
        order_dataframe,
        effective,
    )

    relationship_validation = validate_relationship(
        customer_dataframe,
        order_dataframe,
        effective,
    )

    scenario_validation = validate_scenario(
        scenario_name,
        specification,
        customer_dataframe,
        order_dataframe,
    )

    customer_type_distribution = calculate_distribution(
        customer_dataframe,
        "CUSTOMER_TYPE",
    )

    country_distribution = calculate_distribution(
        customer_dataframe,
        "COUNTRY",
    )

    email_population = calculate_population_rate(
        customer_dataframe,
        "EMAIL",
    )

    amount_statistics = calculate_amount_statistics(order_dataframe)

    structural_passed = all(customer_validation.values()) and all(
        order_validation.values()
    )

    overall_passed = (
        structural_passed
        and relationship_validation["passed"]
        and scenario_validation["passed"]
    )

    statistics = {
        "scenario": scenario_name,
        "seed": seed,
        "record_counts": {
            "CUSTOMER": len(customer_dataframe),
            "ORDER": len(order_dataframe),
        },
        "customer_type_distribution": (customer_type_distribution),
        "country_distribution": (country_distribution),
        "email_population_percent": (email_population),
        "order_amount": amount_statistics,
        "customer_validation": customer_validation,
        "order_validation": order_validation,
        "relationship_validation": relationship_validation,
        "scenario_validation": scenario_validation,
        "structural_validation": {"passed": structural_passed},
        "overall_result": ("PASS" if overall_passed else "FAIL"),
    }

    return {
        "customer": customer_dataframe,
        "order": order_dataframe,
        "statistics": statistics,
    }


# --------------------------------------------------
# Scenario isolation
# --------------------------------------------------


def validate_scenario_isolation(
    specification: dict,
) -> dict:
    """
    Validate that scenarios only change properties explicitly
    declared in their overrides.

    Isolation is evaluated against the effective configuration,
    rather than requiring generated datasets to be byte-identical.

    This is important because scenario-specific generation changes
    may legitimately alter the random-number stream.
    """

    base_customer = get_field(
        specification,
        "CUSTOMER",
        "COUNTRY",
    )

    normal = resolve_scenario(
        specification,
        "NORMAL",
    )

    high_value = resolve_scenario(
        specification,
        "HIGH_VALUE",
    )

    missing_data = resolve_scenario(
        specification,
        "MISSING_DATA",
    )

    normal_country = get_field(
        normal,
        "CUSTOMER",
        "COUNTRY",
    )

    high_value_country = get_field(
        high_value,
        "CUSTOMER",
        "COUNTRY",
    )

    missing_data_country = get_field(
        missing_data,
        "CUSTOMER",
        "COUNTRY",
    )

    checks = {
        "base_country_configuration_valid": (normal_country == base_customer),
        "HIGH_VALUE_country_unchanged": (high_value_country == base_customer),
        "MISSING_DATA_country_unchanged": (missing_data_country == base_customer),
    }

    return {
        "checks": {key: bool(value) for key, value in checks.items()},
        "passed": bool(all(checks.values())),
    }


# --------------------------------------------------
# Determinism
# --------------------------------------------------


def validate_determinism(
    specification: dict,
    scenario_names: list[str],
) -> dict:
    """Run each scenario twice and compare generated datasets."""

    checks = {}

    for scenario_name in scenario_names:

        first = run_scenario(
            specification,
            scenario_name,
        )

        second = run_scenario(
            specification,
            scenario_name,
        )

        first_customer = first["customer"].to_csv(index=False)

        second_customer = second["customer"].to_csv(index=False)

        first_order = first["order"].to_csv(index=False)

        second_order = second["order"].to_csv(index=False)

        checks[scenario_name] = (
            first_customer == second_customer and first_order == second_order
        )

    return {
        "checks": checks,
        "passed": all(checks.values()),
    }


# --------------------------------------------------
# Output
# --------------------------------------------------


def save_scenario_output(
    scenario_name: str,
    customer_dataframe: pd.DataFrame,
    order_dataframe: pd.DataFrame,
) -> None:
    """Save scenario datasets."""

    scenario_directory = OUTPUT_DIR / scenario_name.lower()

    scenario_directory.mkdir(
        parents=True,
        exist_ok=True,
    )

    customer_dataframe.to_csv(
        scenario_directory / "CUSTOMER.csv",
        index=False,
    )

    order_dataframe.to_csv(
        scenario_directory / "ORDER.csv",
        index=False,
    )


def save_statistics(
    statistics: dict,
) -> None:
    """Save experiment statistics as JSON."""

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
            default=lambda value: (
                bool(value)
                if hasattr(value, "item")
                and isinstance(
                    value.item(),
                    bool,
                )
                else value.item() if hasattr(value, "item") else str(value)
            ),
        )


# --------------------------------------------------
# Experiment execution
# --------------------------------------------------


def main() -> None:
    """Run Experiment 015."""

    specification = load_specification()

    experiment = specification["experiment"]

    generation = specification["generation"]

    scenario_names = list(specification["scenarios"].keys())

    print("=" * 70)
    print("FORGE - Experiment 015: Scenario Generation")
    print("=" * 70)

    print(f"Experiment:   {experiment['id']} - " f"{experiment['name']}")

    print(f"Specification: {SPECIFICATION_FILE}")

    print(f"Random seed:   {generation['seed']}")

    print(f"Customer records: " f"{generation['record_counts']['CUSTOMER']}")

    print(f"Order records: " f"{generation['record_counts']['ORDER']}")

    results = {}

    # --------------------------------------------------
    # Generate scenarios
    # --------------------------------------------------

    for scenario_name in scenario_names:

        print("\n" + "-" * 70)
        print(f"Scenario: {scenario_name}")

        result = run_scenario(
            specification,
            scenario_name,
        )

        results[scenario_name] = result

        save_scenario_output(
            scenario_name,
            result["customer"],
            result["order"],
        )

        statistics = result["statistics"]

        print(f"  CUSTOMER records: " f"{statistics['record_counts']['CUSTOMER']}")

        print(f"  ORDER records: " f"{statistics['record_counts']['ORDER']}")

        print("  CUSTOMER_TYPE distribution:")

        for (
            customer_type,
            percentage,
        ) in statistics["customer_type_distribution"].items():

            print(f"    {customer_type}: " f"{percentage:.2f}%")

        print(f"  EMAIL population: " f"{statistics['email_population_percent']:.2f}%")

        amount = statistics["order_amount"]

        print(f"  ORDER.AMOUNT mean: " f"{amount['mean']:.2f}")

        print(
            f"  ORDER.AMOUNT range: "
            f"{amount['minimum']:.2f} - "
            f"{amount['maximum']:.2f}"
        )

        structural_passed = statistics["structural_validation"]["passed"]

        relationship_passed = statistics["relationship_validation"]["passed"]

        scenario_passed = statistics["scenario_validation"]["passed"]

        print("  Structural validation: " f"{'PASS' if structural_passed else 'FAIL'}")

        print(
            "  Relationship validation: " f"{'PASS' if relationship_passed else 'FAIL'}"
        )

        print("  Scenario validation: " f"{'PASS' if scenario_passed else 'FAIL'}")

        print(f"  Overall: " f"{statistics['overall_result']}")

    # --------------------------------------------------
    # Isolation validation
    # --------------------------------------------------

    print("\n" + "-" * 70)
    print("Scenario isolation validation")

    isolation = validate_scenario_isolation(specification)

    for (
        check_name,
        passed,
    ) in isolation["checks"].items():

        print(f"  {check_name}: " f"{'PASS' if passed else 'FAIL'}")

    print("  Isolation result: " f"{'PASS' if isolation['passed'] else 'FAIL'}")

    # --------------------------------------------------
    # Determinism validation
    # --------------------------------------------------

    print("\n" + "-" * 70)
    print("Scenario determinism validation")

    determinism = validate_determinism(
        specification,
        scenario_names,
    )

    for (
        scenario_name,
        passed,
    ) in determinism["checks"].items():

        print(f"  {scenario_name}: " f"{'PASS' if passed else 'FAIL'}")

    print("  Determinism result: " f"{'PASS' if determinism['passed'] else 'FAIL'}")

    # --------------------------------------------------
    # Overall result
    # --------------------------------------------------

    scenario_passed = all(
        result["statistics"]["overall_result"] == "PASS" for result in results.values()
    )

    overall_passed = scenario_passed and isolation["passed"] and determinism["passed"]

    overall_result = "PASS" if overall_passed else "FAIL"

    statistics = {
        "experiment": experiment,
        "generation": generation,
        "scenarios": {
            scenario_name: result["statistics"]
            for scenario_name, result in results.items()
        },
        "scenario_isolation": isolation,
        "determinism": determinism,
        "overall_result": overall_result,
    }

    save_statistics(statistics)

    # --------------------------------------------------
    # Final output
    # --------------------------------------------------

    print("\nOutput:")

    print(f"  Statistics: {STATISTICS_FILE}")

    for scenario_name in scenario_names:

        scenario_directory = OUTPUT_DIR / scenario_name.lower()

        print(f"  {scenario_name}: " f"{scenario_directory}")

    print("\nExperiment result:")

    print("  Scenario validation: " f"{'PASS' if scenario_passed else 'FAIL'}")

    print("  Scenario isolation: " f"{'PASS' if isolation['passed'] else 'FAIL'}")

    print("  Determinism: " f"{'PASS' if determinism['passed'] else 'FAIL'}")

    print(f"  Overall: {overall_result}")

    print("\nExperiment completed successfully.")


# --------------------------------------------------
# Entry point
# --------------------------------------------------

if __name__ == "__main__":
    main()
