"""
FORGE - Experiment 017: Unified Validation
============================================

Purpose
-------
This experiment tests whether multiple validation dimensions can be
evaluated through a common validation model while preserving the
specific semantics and evidence of each validation category.

The experiment builds on the validation capabilities established by
Experiments 002, 005, 006, 009, 011, 013, and 016.

The following validation dimensions are tested:

    - Structural validation
    - Referential / relationship validation
    - Cross-field constraint validation
    - Population validation
    - Statistical validation
    - Unified PASS / WARN / FAIL result
    - Category-level validation evidence
    - Multiple simultaneous validation failures

No machine learning, LLM, or real production data is used.

Experiment
----------
017 - Unified Validation

Key Question
------------
Can a generic validation model provide one coherent validation framework
across structural, relational, constraint, population, and statistical
validation without losing category-specific validation information?

Author
------
Ranjoy Sen

Status
------
Experimental

How to Run
----------
From the repository root:

    uv run python experiments/017_unified_validation/experiment.py

Output
------
Generated datasets and validation results are written to:

    experiments/017_unified_validation/output/

Important
---------
The generated data is synthetic and does not represent any real
production dataset.
"""

from pathlib import Path
from datetime import date, timedelta
import json
import random
import string

import pandas as pd

# ============================================================
# Paths
# ============================================================

EXPERIMENT_DIR = Path(__file__).resolve().parent

SPECIFICATION_FILE = EXPERIMENT_DIR / "specification.json"

OUTPUT_DIR = EXPERIMENT_DIR / "output"

STATISTICS_FILE = OUTPUT_DIR / "unified_validation.json"


# ============================================================
# Specification
# ============================================================


def load_specification() -> dict:
    """Load experiment specification."""

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
# Result helpers
# ============================================================


RESULT_PRECEDENCE = {
    "PASS": 0,
    "WARN": 1,
    "FAIL": 2,
}


def overall_result(
    results: list[str],
) -> str:
    """Derive overall result from category results."""

    if not results:
        return "PASS"

    return max(
        results,
        key=lambda result: RESULT_PRECEDENCE[result],
    )


def make_check(
    check_id: str,
    check_type: str,
    result: str,
    expected=None,
    observed=None,
    records_checked: int | None = None,
    violations: int = 0,
    message: str | None = None,
) -> dict:
    """Create a normalized validation check result."""

    return {
        "id": check_id,
        "type": check_type,
        "result": result,
        "expected": expected,
        "observed": observed,
        "records_checked": records_checked,
        "violations": violations,
        "message": message,
    }


def summarize_checks(
    checks: list[dict],
) -> str:
    """Derive category result from individual checks."""

    results = [check["result"] for check in checks]

    return overall_result(results)


# ============================================================
# Generation helpers
# ============================================================


def generate_identifier(
    prefix: str,
    index: int,
    width: int = 7,
) -> str:
    """Generate deterministic identifier."""

    return prefix + str(index).zfill(width)


def generate_random_string(
    length: int,
) -> str:
    """Generate random alphanumeric string."""

    alphabet = string.ascii_uppercase + string.digits

    return "".join(random.choice(alphabet) for _ in range(length))


def generate_date() -> str:
    """Generate a date within configured range."""

    start = date(
        2021,
        1,
        1,
    )

    end = date(
        2030,
        12,
        31,
    )

    days = (end - start).days

    generated = start + timedelta(
        days=random.randint(
            0,
            days,
        )
    )

    return generated.isoformat()


def generate_customer_dataset(
    specification: dict,
) -> pd.DataFrame:
    """Generate CUSTOMER entity."""

    record_count = specification["generation"]["record_counts"]["CUSTOMER"]

    rows = []

    for index in range(
        1,
        record_count + 1,
    ):

        country = random.choices(
            [
                "US",
                "IN",
                "DE",
                "FR",
            ],
            weights=[
                0.50,
                0.30,
                0.15,
                0.05,
            ],
            k=1,
        )[0]

        customer_type = random.choices(
            [
                "STANDARD",
                "PREMIUM",
            ],
            weights=[
                0.70,
                0.30,
            ],
            k=1,
        )[0]

        email = None

        if random.random() < 0.80:
            email = generate_random_string(20) + "@example.com"

        rows.append(
            {
                "CUSTOMER_ID": (
                    generate_identifier(
                        "CUS",
                        index,
                        7,
                    )
                ),
                "COUNTRY": country,
                "CUSTOMER_TYPE": customer_type,
                "EMAIL": email,
            }
        )

    return pd.DataFrame(rows)


def generate_order_dataset(
    specification: dict,
    customer_dataframe: pd.DataFrame,
) -> pd.DataFrame:
    """Generate ORDER entity."""

    record_count = specification["generation"]["record_counts"]["ORDER"]

    customer_ids = customer_dataframe["CUSTOMER_ID"].tolist()

    rows = []

    for index in range(
        1,
        record_count + 1,
    ):

        start_date = generate_date()

        start = date.fromisoformat(start_date)

        end = start + timedelta(
            days=random.randint(
                0,
                3650,
            )
        )

        end_date = end.isoformat()

        minimum = round(
            random.uniform(
                100.0,
                3000.0,
            ),
            2,
        )

        maximum = round(
            random.uniform(
                minimum,
                5000.0,
            ),
            2,
        )

        amount = round(
            random.uniform(
                minimum,
                maximum,
            ),
            2,
        )

        rows.append(
            {
                "ORDER_ID": (
                    generate_identifier(
                        "ORD",
                        index,
                        7,
                    )
                ),
                "CUSTOMER_ID": (random.choice(customer_ids)),
                "START_DATE": start_date,
                "END_DATE": end_date,
                "MIN_AMOUNT": minimum,
                "MAX_AMOUNT": maximum,
                "ORDER_AMOUNT": amount,
            }
        )

    return pd.DataFrame(rows)


def generate_dataset(
    specification: dict,
) -> dict[str, pd.DataFrame]:
    """Generate complete valid dataset."""

    customer_dataframe = generate_customer_dataset(specification)

    order_dataframe = generate_order_dataset(
        specification,
        customer_dataframe,
    )

    return {
        "CUSTOMER": customer_dataframe,
        "ORDER": order_dataframe,
    }


# ============================================================
# Structural validation
# ============================================================


def validate_structural(
    specification: dict,
    datasets: dict[str, pd.DataFrame],
) -> dict:
    """Validate dataset structure."""

    checks = []

    for entity_name in [
        "CUSTOMER",
        "ORDER",
    ]:

        entity = get_entity(
            specification,
            entity_name,
        )

        if entity_name not in datasets:

            checks.append(
                make_check(
                    f"S-{entity_name}-001",
                    "structural",
                    "FAIL",
                    expected="entity_exists",
                    observed="missing",
                    message=(f"Entity {entity_name} is missing."),
                )
            )

            continue

        dataframe = datasets[entity_name]

        checks.append(
            make_check(
                f"S-{entity_name}-001",
                "structural",
                "PASS",
                expected="entity_exists",
                observed="present",
                records_checked=len(dataframe),
            )
        )

        expected_fields = list(entity["fields"].keys())

        missing_fields = [
            field for field in expected_fields if field not in dataframe.columns
        ]

        field_result = "FAIL" if missing_fields else "PASS"

        checks.append(
            make_check(
                f"S-{entity_name}-002",
                "structural",
                field_result,
                expected=expected_fields,
                observed=list(dataframe.columns),
                records_checked=len(dataframe),
                violations=len(missing_fields),
                message=(
                    "Missing fields: " + ", ".join(missing_fields)
                    if missing_fields
                    else None
                ),
            )
        )

        primary_key = entity["primary_key"]

        for field_name in primary_key:

            if field_name not in dataframe.columns:
                continue

            null_count = int(dataframe[field_name].isna().sum())

            duplicate_count = int(dataframe[field_name].duplicated().sum())

            null_result = "PASS" if null_count == 0 else "FAIL"

            duplicate_result = "PASS" if duplicate_count == 0 else "FAIL"

            checks.append(
                make_check(
                    f"S-{entity_name}-PK-{field_name}-NULL",
                    "structural",
                    null_result,
                    expected="no_nulls",
                    observed=null_count,
                    records_checked=len(dataframe),
                    violations=null_count,
                )
            )

            checks.append(
                make_check(
                    f"S-{entity_name}-PK-{field_name}-UNIQUE",
                    "structural",
                    duplicate_result,
                    expected="unique",
                    observed=(len(dataframe) - duplicate_count),
                    records_checked=len(dataframe),
                    violations=duplicate_count,
                )
            )

    category_result = summarize_checks(checks)

    return {
        "result": category_result,
        "checks": checks,
    }


# ============================================================
# Relational validation
# ============================================================


def validate_relationships(
    specification: dict,
    datasets: dict[str, pd.DataFrame],
) -> dict:
    """Validate declared relationships."""

    checks = []

    for relationship in specification["relationships"]:

        parent_entity, parent_field = relationship["parent"].split(".")

        child_entity, child_field = relationship["child"].split(".")

        parent_dataframe = datasets[parent_entity]

        child_dataframe = datasets[child_entity]

        parent_values = set(parent_dataframe[parent_field].dropna())

        invalid_references = ~child_dataframe[child_field].isin(parent_values)

        invalid_count = int(invalid_references.sum())

        result = "PASS" if invalid_count == 0 else "FAIL"

        checks.append(
            make_check(
                relationship["id"],
                "relational",
                result,
                expected=(
                    f"all {child_entity}."
                    f"{child_field} values reference "
                    f"{parent_entity}."
                    f"{parent_field}"
                ),
                observed=(f"{invalid_count} invalid references"),
                records_checked=len(child_dataframe),
                violations=invalid_count,
            )
        )

    return {
        "result": summarize_checks(checks),
        "checks": checks,
    }


# ============================================================
# Constraint validation
# ============================================================


def validate_constraints(
    specification: dict,
    datasets: dict[str, pd.DataFrame],
) -> dict:
    """Validate cross-field constraints."""

    checks = []

    dataframe = datasets["ORDER"]

    for constraint in specification["constraints"]:

        constraint_id = constraint["id"]

        expression = constraint["expression"]

        if constraint_id == "C001":

            violations = dataframe["START_DATE"] > dataframe["END_DATE"]

        elif constraint_id == "C002":

            violations = dataframe["MIN_AMOUNT"] > dataframe["MAX_AMOUNT"]

        elif constraint_id == "C003":

            violations = (dataframe["ORDER_AMOUNT"] < dataframe["MIN_AMOUNT"]) | (
                dataframe["ORDER_AMOUNT"] > dataframe["MAX_AMOUNT"]
            )

        else:
            raise ValueError(f"Unsupported constraint: " f"{constraint_id}")

        violation_count = int(violations.sum())

        result = "PASS" if violation_count == 0 else "FAIL"

        checks.append(
            make_check(
                constraint_id,
                "constraint",
                result,
                expected=expression,
                observed=(f"{violation_count} violations"),
                records_checked=len(dataframe),
                violations=violation_count,
            )
        )

    return {
        "result": summarize_checks(checks),
        "checks": checks,
    }


# ============================================================
# Population validation
# ============================================================


def validate_population(
    specification: dict,
    datasets: dict[str, pd.DataFrame],
) -> dict:
    """Validate optional field population."""

    checks = []

    dataframe = datasets["CUSTOMER"]

    field_name = "EMAIL"

    metadata = get_field(
        specification,
        "CUSTOMER",
        field_name,
    )

    population = metadata["population"]

    expected_rate = float(population["expected_rate"])

    tolerance = float(population["tolerance"])

    observed_rate = float(dataframe[field_name].notna().mean())

    difference = abs(observed_rate - expected_rate)

    result = (
        "PASS"
        if difference <= tolerance
        else "WARN" if difference <= tolerance * 2 else "FAIL"
    )

    checks.append(
        make_check(
            "P001",
            "population",
            result,
            expected=expected_rate,
            observed=round(
                observed_rate,
                4,
            ),
            records_checked=len(dataframe),
            violations=0,
            message=(f"Difference={difference:.4f}, " f"tolerance={tolerance:.4f}"),
        )
    )

    return {
        "result": summarize_checks(checks),
        "checks": checks,
    }


# ============================================================
# Statistical validation
# ============================================================


def validate_statistical(
    specification: dict,
    datasets: dict[str, pd.DataFrame],
) -> dict:
    """Validate selected statistical characteristics."""

    checks = []

    customer_dataframe = datasets["CUSTOMER"]

    order_dataframe = datasets["ORDER"]

    # --------------------------------------------------------
    # COUNTRY distribution
    # --------------------------------------------------------

    country_metadata = get_field(
        specification,
        "CUSTOMER",
        "COUNTRY",
    )

    expected_weights = country_metadata["generation"]["weights"]

    tolerance = country_metadata["validation"]["distribution_tolerance"]

    observed = customer_dataframe["COUNTRY"].value_counts(normalize=True).to_dict()

    for country, expected in expected_weights.items():

        observed_value = float(
            observed.get(
                country,
                0.0,
            )
        )

        difference = abs(observed_value - expected)

        result = (
            "PASS"
            if difference <= tolerance
            else "WARN" if difference <= tolerance * 2 else "FAIL"
        )

        checks.append(
            make_check(
                f"STAT-COUNTRY-{country}",
                "statistical",
                result,
                expected=expected,
                observed=round(
                    observed_value,
                    4,
                ),
                records_checked=len(customer_dataframe),
                message=(f"Difference={difference:.4f}, " f"tolerance={tolerance:.4f}"),
            )
        )

    # --------------------------------------------------------
    # ORDER amount mean
    # --------------------------------------------------------

    amount_metadata = get_field(
        specification,
        "ORDER",
        "ORDER_AMOUNT",
    )

    generation = amount_metadata["generation"]

    expected_mean = (float(generation["min"]) + float(generation["max"])) / 2.0

    observed_mean = float(order_dataframe["ORDER_AMOUNT"].mean())

    numeric_validation = specification["validation"]["statistical"]["numeric"]

    mean_tolerance = float(numeric_validation["mean_tolerance"])

    mean_difference = abs(observed_mean - expected_mean)

    mean_result = (
        "PASS"
        if mean_difference <= mean_tolerance
        else "WARN" if mean_difference <= mean_tolerance * 2 else "FAIL"
    )

    checks.append(
        make_check(
            "STAT-ORDER-AMOUNT-MEAN",
            "statistical",
            mean_result,
            expected=round(
                expected_mean,
                4,
            ),
            observed=round(
                observed_mean,
                4,
            ),
            records_checked=len(order_dataframe),
            message=(
                f"Difference={mean_difference:.4f}, " f"tolerance={mean_tolerance:.4f}"
            ),
        )
    )

    return {
        "result": summarize_checks(checks),
        "checks": checks,
    }


# ============================================================
# Unified validation
# ============================================================


def validate_dataset(
    specification: dict,
    datasets: dict[str, pd.DataFrame],
) -> dict:
    """Run all validation categories."""

    structural = validate_structural(
        specification,
        datasets,
    )

    relational = validate_relationships(
        specification,
        datasets,
    )

    constraints = validate_constraints(
        specification,
        datasets,
    )

    population = validate_population(
        specification,
        datasets,
    )

    statistical = validate_statistical(
        specification,
        datasets,
    )

    categories = {
        "structural": structural,
        "relational": relational,
        "constraints": constraints,
        "population": population,
        "statistical": statistical,
    }

    category_results = [category["result"] for category in categories.values()]

    return {
        "categories": categories,
        "overall_result": overall_result(category_results),
    }


# ============================================================
# Controlled invalid dataset
# ============================================================


def create_invalid_dataset(
    valid_datasets: dict[str, pd.DataFrame],
) -> dict[str, pd.DataFrame]:
    """
    Create a controlled invalid dataset.

    Violations introduced:

        - duplicate CUSTOMER primary key
        - invalid ORDER foreign key
        - invalid START_DATE / END_DATE
        - invalid MIN_AMOUNT / MAX_AMOUNT
        - invalid ORDER_AMOUNT range
        - population deviation
        - statistical deviation
    """

    customers = valid_datasets["CUSTOMER"].copy()

    orders = valid_datasets["ORDER"].copy()

    # --------------------------------------------------------
    # Structural violation
    # --------------------------------------------------------

    if len(customers) >= 2:

        customers.loc[1, "CUSTOMER_ID"] = customers.loc[0, "CUSTOMER_ID"]

    # --------------------------------------------------------
    # Population deviation
    # --------------------------------------------------------

    customers["EMAIL"] = None

    # --------------------------------------------------------
    # Relational violation
    # --------------------------------------------------------

    orders.loc[0, "CUSTOMER_ID"] = "CUS9999999"

    # --------------------------------------------------------
    # Constraint C001 violation
    # --------------------------------------------------------

    orders.loc[1, "START_DATE"] = "2030-12-31"

    orders.loc[1, "END_DATE"] = "2021-01-01"

    # --------------------------------------------------------
    # Constraint C002 violation
    # --------------------------------------------------------

    orders.loc[2, "MIN_AMOUNT"] = 4500.0

    orders.loc[2, "MAX_AMOUNT"] = 1000.0

    # --------------------------------------------------------
    # Constraint C003 violation
    # --------------------------------------------------------

    orders.loc[3, "MIN_AMOUNT"] = 1000.0

    orders.loc[3, "MAX_AMOUNT"] = 2000.0

    orders.loc[3, "ORDER_AMOUNT"] = 4500.0

    # --------------------------------------------------------
    # Statistical deviation
    #
    # Shift all amounts toward a high-value range.
    # --------------------------------------------------------

    orders["ORDER_AMOUNT"] = orders["ORDER_AMOUNT"].clip(
        lower=4500.0,
        upper=5000.0,
    )

    return {
        "CUSTOMER": customers,
        "ORDER": orders,
    }


# ============================================================
# Output helpers
# ============================================================


def save_dataset(
    datasets: dict[str, pd.DataFrame],
    directory_name: str,
) -> Path:
    """Save dataset entities."""

    directory = OUTPUT_DIR / directory_name

    directory.mkdir(
        parents=True,
        exist_ok=True,
    )

    for (
        entity_name,
        dataframe,
    ) in datasets.items():

        dataframe.to_csv(
            directory / f"{entity_name}.csv",
            index=False,
        )

    return directory


def save_json(
    path: Path,
    value: dict,
) -> None:
    """Save JSON output."""

    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with path.open(
        "w",
        encoding="utf-8",
    ) as file:

        json.dump(
            value,
            file,
            indent=2,
            default=str,
        )


# ============================================================
# Console reporting
# ============================================================


def print_validation_summary(
    validation: dict,
) -> None:
    """Print unified validation summary."""

    print("\nValidation summary:")

    for (
        category_name,
        category,
    ) in validation["categories"].items():

        print(f"  {category_name.capitalize():<15}" f"{category['result']}")

        for check in category["checks"]:

            print(f"    {check['id']:<30}" f"{check['result']}")

    print(f"\n  Overall: " f"{validation['overall_result']}")


# ============================================================
# Main
# ============================================================


def main() -> None:
    """Run Experiment 017."""

    specification = load_specification()

    experiment = specification["experiment"]

    generation = specification["generation"]

    seed = generation["seed"]

    random.seed(seed)

    print("=" * 70)
    print("FORGE - Experiment 017: Unified Validation")
    print("=" * 70)

    print(f"Experiment:   " f"{experiment['id']} - " f"{experiment['name']}")

    print(f"Specification: " f"{SPECIFICATION_FILE}")

    print(f"Random seed:   " f"{seed}")

    print("\nGenerating valid dataset...")

    valid_dataset = generate_dataset(specification)

    print(f"  CUSTOMER records: " f"{len(valid_dataset['CUSTOMER'])}")

    print(f"  ORDER records: " f"{len(valid_dataset['ORDER'])}")

    print("\nValid dataset validation:")

    valid_validation = validate_dataset(
        specification,
        valid_dataset,
    )

    print_validation_summary(valid_validation)

    print("\nCreating controlled invalid dataset...")

    invalid_dataset = create_invalid_dataset(valid_dataset)

    print("\nInvalid dataset validation:")

    invalid_validation = validate_dataset(
        specification,
        invalid_dataset,
    )

    print_validation_summary(invalid_validation)

    # ========================================================
    # Validation model assessment
    # ========================================================

    valid_expected = specification["test_cases"]["valid_dataset"]["expected_result"]

    invalid_expected = specification["test_cases"]["invalid_dataset"]["expected_result"]

    valid_result_pass = valid_validation["overall_result"] == valid_expected

    invalid_result_pass = invalid_validation["overall_result"] == invalid_expected

    categories_present = set(valid_validation["categories"].keys()) == {
        "structural",
        "relational",
        "constraints",
        "population",
        "statistical",
    }

    multiple_failures = sum(
        1
        for category in invalid_validation["categories"].values()
        if category["result"] == "FAIL"
    )

    multiple_failures_detected = multiple_failures >= 2

    category_evidence_present = all(
        isinstance(
            category["checks"],
            list,
        )
        and len(category["checks"]) > 0
        for category in invalid_validation["categories"].values()
    )

    unified_validation_pass = all(
        [
            valid_result_pass,
            invalid_result_pass,
            categories_present,
            multiple_failures_detected,
            category_evidence_present,
        ]
    )

    # ========================================================
    # Save outputs
    # ========================================================

    valid_output = save_dataset(
        valid_dataset,
        "valid",
    )

    invalid_output = save_dataset(
        invalid_dataset,
        "invalid",
    )

    results = {
        "experiment": experiment,
        "generation": generation,
        "valid_dataset": {
            "output": str(valid_output),
            "validation": valid_validation,
            "expected_result": valid_expected,
            "result_matches_expectation": (valid_result_pass),
        },
        "invalid_dataset": {
            "output": str(invalid_output),
            "validation": invalid_validation,
            "expected_result": invalid_expected,
            "result_matches_expectation": (invalid_result_pass),
        },
        "unified_model_assessment": {
            "categories_present": (categories_present),
            "multiple_failures_detected": (multiple_failures_detected),
            "category_evidence_present": (category_evidence_present),
            "multiple_failed_categories": (multiple_failures),
            "overall_result": ("PASS" if unified_validation_pass else "FAIL"),
        },
    }

    save_json(
        STATISTICS_FILE,
        results,
    )

    # ========================================================
    # Final output
    # ========================================================

    print("\n" + "-" * 70)

    print("Unified validation assessment")

    print(
        "  Valid dataset expected result: " + ("PASS" if valid_result_pass else "FAIL")
    )

    print(
        "  Invalid dataset expected result: "
        + ("PASS" if invalid_result_pass else "FAIL")
    )

    print(
        "  All validation categories represented: "
        + ("PASS" if categories_present else "FAIL")
    )

    print(
        "  Multiple failures detected: "
        + ("PASS" if multiple_failures_detected else "FAIL")
    )

    print(
        "  Category evidence preserved: "
        + ("PASS" if category_evidence_present else "FAIL")
    )

    print(f"  Overall: " f"{'PASS' if unified_validation_pass else 'FAIL'}")

    print("\nOutput:")

    print(f"  Valid dataset:   " f"{valid_output}")

    print(f"  Invalid dataset: " f"{invalid_output}")

    print(f"  Statistics:      " f"{STATISTICS_FILE}")

    print("\nExperiment completed successfully.")


# ============================================================
# Entry point
# ============================================================


if __name__ == "__main__":
    main()
