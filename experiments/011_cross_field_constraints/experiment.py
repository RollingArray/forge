"""
FORGE - Experiment 011: Cross-Field Constraints
================================================

Purpose
-------
This experiment tests whether cross-field constraints require
dependency-aware generation rather than independent field generation.

The experiment compares two approaches:

    1. Independent generation
       Generate every field independently and validate the resulting
       record against cross-field constraints.

    2. Constraint-aware generation
       Generate fields according to the dependencies expressed by the
       declared cross-field constraints.

The experiment builds on:

    Experiment 002 - Field Constraints
    Experiment 007 - Reproducible Generation
    Experiment 008 - Domain vs Generation Strategy
    Experiment 009 - Optionality and Population
    Experiment 010 - Composite Identity

No machine learning, LLM, or real production data is used.

Experiment
----------
011 - Cross-Field Constraints

Key Question
------------
Can constraint-aware generation improve validity when the validity of
one field depends on another field?

Author
------
Ranjoy Sen

Status
------
Experimental

How to Run
----------
From the repository root:

    uv run python experiments/011_cross_field_constraints/experiment.py

Output
------
The generated datasets are written to:

    experiments/011_cross_field_constraints/output/independent_generation.csv

    experiments/011_cross_field_constraints/output/constraint_aware_generation.csv

Validation results are written to:

    experiments/011_cross_field_constraints/output/constraint_statistics.json

Important
---------
The generated data is synthetic and does not represent any real
production dataset.
"""

from datetime import date, timedelta
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

INDEPENDENT_OUTPUT_FILE = OUTPUT_DIR / "independent_generation.csv"

CONSTRAINT_AWARE_OUTPUT_FILE = OUTPUT_DIR / "constraint_aware_generation.csv"

STATISTICS_FILE = OUTPUT_DIR / "constraint_statistics.json"


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


def get_entity(
    specification: dict,
) -> dict:
    """Return the ORDER entity definition."""

    return specification["entities"]["ORDER"]


def get_field_metadata(
    specification: dict,
    field_name: str,
) -> dict:
    """Return metadata for a field."""

    return get_entity(specification)["fields"][field_name]


def get_constraints(
    specification: dict,
) -> list[dict]:
    """Return the declared cross-field constraints."""

    return get_entity(specification)["constraints"]


# --------------------------------------------------
# Basic field generators
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


def generate_uniform_number(
    minimum: float,
    maximum: float,
) -> float:
    """Generate a numeric value from a uniform distribution."""

    return random.uniform(
        minimum,
        maximum,
    )


def generate_date(
    minimum: date,
    maximum: date,
) -> str:
    """Generate a random date between two bounds."""

    delta = (maximum - minimum).days

    generated = minimum + timedelta(
        days=random.randint(
            0,
            delta,
        )
    )

    return generated.isoformat()


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


# --------------------------------------------------
# Generic field generation
# --------------------------------------------------


def generate_field_value(
    specification: dict,
    field_name: str,
    index: int,
) -> object:
    """
    Generate one field according to its own metadata.

    This function intentionally knows nothing about cross-field
    constraints.
    """

    metadata = get_field_metadata(
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

    if field_type == "date":

        minimum = date.fromisoformat(metadata["generation"]["min"])

        maximum = date.fromisoformat(metadata["generation"]["max"])

        return generate_date(
            minimum,
            maximum,
        )

    if field_type == "number":

        return round(
            generate_uniform_number(
                metadata["generation"]["min"],
                metadata["generation"]["max"],
            ),
            2,
        )

    if field_type == "string":

        return generate_string(
            minimum=metadata["min_length"],
            maximum=metadata["max_length"],
        )

    raise ValueError(f"Unsupported field type: {field_type}")


# --------------------------------------------------
# Independent generation
# --------------------------------------------------


def generate_independent_dataset(
    specification: dict,
) -> pd.DataFrame:
    """
    Generate every field independently.

    No cross-field relationship is considered during generation.
    """

    record_count = specification["generation"]["record_count"]

    fields = get_entity(specification)["fields"]

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
# Constraint-aware generation
# --------------------------------------------------


def generate_constraint_aware_dataset(
    specification: dict,
) -> pd.DataFrame:
    """
    Generate records while respecting the declared cross-field
    constraints.

    The dependency logic is derived from the specification.

    Supported relationships in this experiment:

        A <= B

        MIN <= VALUE <= MAX

    The generator does not embed these relationships inside the
    individual field definitions.
    """

    record_count = specification["generation"]["record_count"]

    fields = get_entity(specification)["fields"]

    rows = []

    for index in range(
        1,
        record_count + 1,
    ):

        row = {}

        # --------------------------------------------------
        # Generate fields that have no dependency on another
        # field first.
        # --------------------------------------------------

        independent_fields = [
            "ORDER_ID",
            "START_DATE",
            "MIN_AMOUNT",
        ]

        for field_name in independent_fields:

            row[field_name] = generate_field_value(
                specification,
                field_name,
                index,
            )

        # --------------------------------------------------
        # START_DATE <= END_DATE
        # --------------------------------------------------

        start_date = date.fromisoformat(row["START_DATE"])

        end_date_metadata = get_field_metadata(
            specification,
            "END_DATE",
        )

        end_date_maximum = date.fromisoformat(end_date_metadata["generation"]["max"])

        if start_date > end_date_maximum:
            raise ValueError(
                "Constraint-aware generation cannot satisfy "
                "START_DATE <= END_DATE within END_DATE bounds."
            )

        end_date = start_date + timedelta(
            days=random.randint(
                0,
                (end_date_maximum - start_date).days,
            )
        )

        row["END_DATE"] = end_date.isoformat()

        # --------------------------------------------------
        # MIN_AMOUNT <= MAX_AMOUNT
        # --------------------------------------------------

        min_amount = float(row["MIN_AMOUNT"])

        max_amount_metadata = get_field_metadata(
            specification,
            "MAX_AMOUNT",
        )

        max_amount_limit = float(max_amount_metadata["generation"]["max"])

        if min_amount > max_amount_limit:
            raise ValueError(
                "Constraint-aware generation cannot satisfy "
                "MIN_AMOUNT <= MAX_AMOUNT within MAX_AMOUNT bounds."
            )

        max_amount = round(
            random.uniform(
                min_amount,
                max_amount_limit,
            ),
            2,
        )

        row["MAX_AMOUNT"] = max_amount

        # --------------------------------------------------
        # MIN_AMOUNT <= ORDER_AMOUNT <= MAX_AMOUNT
        # --------------------------------------------------

        order_amount = round(
            random.uniform(
                float(row["MIN_AMOUNT"]),
                float(row["MAX_AMOUNT"]),
            ),
            2,
        )

        row["ORDER_AMOUNT"] = order_amount

        # --------------------------------------------------
        # CUSTOMER_NAME
        # --------------------------------------------------

        row["CUSTOMER_NAME"] = generate_field_value(
            specification,
            "CUSTOMER_NAME",
            index,
        )

        # --------------------------------------------------
        # Preserve specification field order.
        # --------------------------------------------------

        rows.append({field_name: row[field_name] for field_name in fields})

    return pd.DataFrame(rows)


# --------------------------------------------------
# Field-level validation
# --------------------------------------------------


def validate_field_constraints(
    dataframe: pd.DataFrame,
    specification: dict,
) -> dict:
    """Validate individual field constraints."""

    fields = get_entity(specification)["fields"]

    results = {}

    for (
        field_name,
        metadata,
    ) in fields.items():

        series = dataframe[field_name]

        non_null = series.dropna()

        passed = True
        errors = []

        if not metadata.get(
            "nullable",
            False,
        ):

            if series.isna().any():
                passed = False
                errors.append("NULL value found.")

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

        elif field_type == "date":

            minimum = date.fromisoformat(metadata["generation"]["min"])

            maximum = date.fromisoformat(metadata["generation"]["max"])

            for value in non_null:

                parsed = date.fromisoformat(str(value))

                if not (minimum <= parsed <= maximum):
                    passed = False
                    errors.append("Date outside configured bounds.")
                    break

        elif field_type == "number":

            minimum = metadata["generation"]["min"]

            maximum = metadata["generation"]["max"]

            numeric_values = pd.to_numeric(non_null)

            if not numeric_values.between(
                minimum,
                maximum,
            ).all():

                passed = False
                errors.append("Number outside configured bounds.")

        elif field_type == "string":

            minimum = metadata["min_length"]

            maximum = metadata["max_length"]

            if not all(minimum <= len(str(value)) <= maximum for value in non_null):

                passed = False
                errors.append("String length outside configured bounds.")

        results[field_name] = {
            "passed": passed,
            "errors": errors,
        }

    return results


# --------------------------------------------------
# Cross-field validation
# --------------------------------------------------


def validate_comparison_constraint(
    dataframe: pd.DataFrame,
    constraint: dict,
) -> dict:
    """Validate a comparison constraint."""

    left_field = constraint["left"]

    right_field = constraint["right"]

    operator = constraint["operator"]

    violations = []

    for index, row in dataframe.iterrows():

        left = row[left_field]

        right = row[right_field]

        if operator == "less_than_or_equal":

            valid = left <= right

        else:
            raise ValueError(f"Unsupported comparison operator: {operator}")

        if not valid:

            violations.append(
                {
                    "record": int(index + 1),
                    "left_field": left_field,
                    "left_value": left,
                    "operator": operator,
                    "right_field": right_field,
                    "right_value": right,
                }
            )

    return {
        "constraint_id": constraint["id"],
        "type": constraint["type"],
        "passed": len(violations) == 0,
        "violation_count": len(violations),
        "violations": violations[:20],
    }


def validate_range_constraint(
    dataframe: pd.DataFrame,
    constraint: dict,
) -> dict:
    """Validate a field against minimum and maximum fields."""

    field = constraint["field"]

    minimum_field = constraint["minimum_field"]

    maximum_field = constraint["maximum_field"]

    violations = []

    for index, row in dataframe.iterrows():

        value = float(row[field])

        minimum = float(row[minimum_field])

        maximum = float(row[maximum_field])

        if not (minimum <= value <= maximum):

            violations.append(
                {
                    "record": int(index + 1),
                    "field": field,
                    "value": value,
                    "minimum_field": minimum_field,
                    "minimum": minimum,
                    "maximum_field": maximum_field,
                    "maximum": maximum,
                }
            )

    return {
        "constraint_id": constraint["id"],
        "type": constraint["type"],
        "passed": len(violations) == 0,
        "violation_count": len(violations),
        "violations": violations[:20],
    }


def validate_cross_field_constraints(
    dataframe: pd.DataFrame,
    specification: dict,
) -> dict:
    """Validate all declared cross-field constraints."""

    results = []

    for constraint in get_constraints(specification):

        constraint_type = constraint["type"]

        if constraint_type == "comparison":

            result = validate_comparison_constraint(
                dataframe,
                constraint,
            )

        elif constraint_type == "range":

            result = validate_range_constraint(
                dataframe,
                constraint,
            )

        else:

            raise ValueError(f"Unsupported constraint type: " f"{constraint_type}")

        results.append(result)

    total_violations = sum(result["violation_count"] for result in results)

    return {
        "constraints": results,
        "total_violation_count": (total_violations),
        "passed": all(result["passed"] for result in results),
    }


# --------------------------------------------------
# Dependency observation
# --------------------------------------------------


def derive_dependencies(
    specification: dict,
) -> list[dict]:
    """
    Derive a simple dependency representation from the declared
    constraints.

    This is intentionally small and experiment-specific. It is not
    intended to be the final FORGE constraint engine.
    """

    dependencies = []

    for constraint in get_constraints(specification):

        if constraint["type"] == "comparison":

            dependencies.append(
                {
                    "constraint_id": constraint["id"],
                    "source": constraint["left"],
                    "dependent": constraint["right"],
                    "relationship": constraint["operator"],
                }
            )

        elif constraint["type"] == "range":

            dependencies.append(
                {
                    "constraint_id": constraint["id"],
                    "source": [
                        constraint["minimum_field"],
                        constraint["maximum_field"],
                    ],
                    "dependent": constraint["field"],
                    "relationship": "bounded_by",
                }
            )

    return dependencies


# --------------------------------------------------
# Output
# --------------------------------------------------


def save_dataset(
    dataframe: pd.DataFrame,
    output_file: Path,
) -> None:
    """Save generated dataset."""

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
    """Run Experiment 011."""

    specification = load_specification()

    experiment_metadata = specification["experiment"]

    generation_metadata = specification["generation"]

    seed = generation_metadata["seed"]

    record_count = generation_metadata["record_count"]

    random.seed(seed)

    print("=" * 70)
    print("FORGE - Experiment 011: " "Cross-Field Constraints")
    print("=" * 70)

    print(
        f"Experiment:   "
        f"{experiment_metadata['id']} - "
        f"{experiment_metadata['name']}"
    )

    print(f"Specification: " f"{SPECIFICATION_FILE}")

    print(f"Random seed:   {seed}")

    print(f"Record count:  {record_count}")

    print("\nDeclared cross-field constraints:")

    for constraint in get_constraints(specification):

        if constraint["type"] == "comparison":

            print(
                f"  {constraint['id']}: "
                f"{constraint['left']} "
                f"<= "
                f"{constraint['right']}"
            )

        elif constraint["type"] == "range":

            print(
                f"  {constraint['id']}: "
                f"{constraint['minimum_field']} "
                f"<= "
                f"{constraint['field']} "
                f"<= "
                f"{constraint['maximum_field']}"
            )

    dependencies = derive_dependencies(specification)

    print("\nDerived generation dependencies:")

    for dependency in dependencies:

        print(
            f"  {dependency['constraint_id']}: "
            f"{dependency['source']} "
            f"-> "
            f"{dependency['dependent']}"
        )

    # --------------------------------------------------
    # Approach A
    # --------------------------------------------------

    print("\nApproach A: Independent generation")

    random.seed(seed)

    independent_dataframe = generate_independent_dataset(specification)

    independent_field_validation = validate_field_constraints(
        independent_dataframe,
        specification,
    )

    independent_cross_field_validation = validate_cross_field_constraints(
        independent_dataframe,
        specification,
    )

    independent_field_passed = all(
        result["passed"] for result in independent_field_validation.values()
    )

    print(f"  Field validation: " f"{'PASS' if independent_field_passed else 'FAIL'}")

    print(
        f"  Cross-field validation: "
        f"{'PASS' if independent_cross_field_validation['passed'] else 'FAIL'}"
    )

    print(
        f"  Violations: "
        f"{independent_cross_field_validation['total_violation_count']}"
    )

    # --------------------------------------------------
    # Approach B
    # --------------------------------------------------

    print("\nApproach B: Constraint-aware generation")

    random.seed(seed)

    constraint_aware_dataframe = generate_constraint_aware_dataset(specification)

    constraint_aware_field_validation = validate_field_constraints(
        constraint_aware_dataframe,
        specification,
    )

    constraint_aware_cross_field_validation = validate_cross_field_constraints(
        constraint_aware_dataframe,
        specification,
    )

    constraint_aware_field_passed = all(
        result["passed"] for result in constraint_aware_field_validation.values()
    )

    print(
        f"  Field validation: " f"{'PASS' if constraint_aware_field_passed else 'FAIL'}"
    )

    print(
        f"  Cross-field validation: "
        f"{'PASS' if constraint_aware_cross_field_validation['passed'] else 'FAIL'}"
    )

    print(
        f"  Violations: "
        f"{constraint_aware_cross_field_validation['total_violation_count']}"
    )

    # --------------------------------------------------
    # Improvement
    # --------------------------------------------------

    independent_violations = independent_cross_field_validation["total_violation_count"]

    constraint_aware_violations = constraint_aware_cross_field_validation[
        "total_violation_count"
    ]

    if independent_violations > 0:

        violation_reduction = (
            independent_violations - constraint_aware_violations
        ) / independent_violations

    else:

        violation_reduction = 0.0

    # --------------------------------------------------
    # Overall experiment result
    # --------------------------------------------------

    # The experiment succeeds when:
    #
    # 1. Independent generation demonstrates the distinction
    #    between field-level and cross-field validity.
    # 2. Constraint-aware generation preserves field validity.
    # 3. Constraint-aware generation satisfies all declared
    #    cross-field constraints.
    #
    # If independent generation happens to produce zero violations,
    # the experiment is still valid, but the contrast is weaker.

    overall_result = (
        "PASS"
        if (
            constraint_aware_field_passed
            and constraint_aware_cross_field_validation["passed"]
            and (independent_violations >= constraint_aware_violations)
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
        constraint_aware_dataframe,
        CONSTRAINT_AWARE_OUTPUT_FILE,
    )

    statistics = {
        "experiment": experiment_metadata,
        "generation": {
            "seed": seed,
            "record_count": record_count,
        },
        "constraints": get_constraints(specification),
        "derived_dependencies": dependencies,
        "independent_generation": {
            "field_validation": (independent_field_validation),
            "cross_field_validation": (independent_cross_field_validation),
        },
        "constraint_aware_generation": {
            "field_validation": (constraint_aware_field_validation),
            "cross_field_validation": (constraint_aware_cross_field_validation),
        },
        "comparison": {
            "independent_violation_count": (independent_violations),
            "constraint_aware_violation_count": (constraint_aware_violations),
            "violation_reduction": (
                round(
                    violation_reduction,
                    4,
                )
            ),
        },
        "architectural_observation": {
            "cross_field_constraints_are_declared_separately": True,
            "generation_dependencies_can_be_derived": True,
            "constraint_aware_generation_preserves_validity": (
                constraint_aware_field_passed
                and constraint_aware_cross_field_validation["passed"]
            ),
        },
        "overall_result": overall_result,
    }

    save_statistics(statistics)

    # --------------------------------------------------
    # Output
    # --------------------------------------------------

    print("\nOutput:")

    print(f"  Independent: " f"{INDEPENDENT_OUTPUT_FILE}")

    print(f"  Constraint-aware: " f"{CONSTRAINT_AWARE_OUTPUT_FILE}")

    print(f"  Statistics: " f"{STATISTICS_FILE}")

    print("\nFirst 10 records: Independent")

    print(independent_dataframe.head(10).to_string(index=False))

    print("\nFirst 10 records: Constraint-aware")

    print(constraint_aware_dataframe.head(10).to_string(index=False))

    print("\nExperiment result:")

    print(f"  Independent violations: " f"{independent_violations}")

    print(f"  Constraint-aware violations: " f"{constraint_aware_violations}")

    print(f"  Violation reduction: " f"{violation_reduction:.2%}")

    print(f"  Overall: " f"{overall_result}")

    print("\nExperiment completed successfully.")


# --------------------------------------------------
# Entry point
# --------------------------------------------------

if __name__ == "__main__":
    main()
