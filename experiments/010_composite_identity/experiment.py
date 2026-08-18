"""
FORGE - Experiment 010: Composite Identity
===========================================

Purpose
-------
This experiment tests whether a composite identity should be treated
as a coordinated generation construct rather than as a collection of
independently generated fields.

The experiment builds on:

    Experiment 002 - Field Constraints
    Experiment 007 - Reproducible Generation
    Experiment 008 - Domain vs Generation Strategy
    Experiment 009 - Optionality and Population

The experiment compares two approaches:

    1. Independent generation
       Generate each identity component independently and then
       validate the resulting composite identity.

    2. Coordinated generation
       Generate the composite identity as a coordinated unit and
       assign its components to the corresponding fields.

The experiment specifically tests whether individual identity
components need to be unique or whether uniqueness belongs to the
combination of those components.

No machine learning, LLM, or real production data is used.

Experiment
----------
010 - Composite Identity

Key Question
------------
Should a composite identity be treated as a first-class generation
construct rather than as a collection of independently generated
fields?

Author
------
Ranjoy Sen

Status
------
Experimental

How to Run
----------
From the repository root:

    uv run python experiments/010_composite_identity/experiment.py

Output
------
The generated datasets are written to:

    experiments/010_composite_identity/output/independent_generation.csv

    experiments/010_composite_identity/output/coordinated_generation.csv

Identity validation results are written to:

    experiments/010_composite_identity/output/identity_statistics.json

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

INDEPENDENT_OUTPUT_FILE = OUTPUT_DIR / "independent_generation.csv"

COORDINATED_OUTPUT_FILE = OUTPUT_DIR / "coordinated_generation.csv"

STATISTICS_FILE = OUTPUT_DIR / "identity_statistics.json"


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


def get_field_metadata(
    specification: dict,
    field_name: str,
) -> dict:
    """Retrieve field metadata from the CUSTOMER_ACCOUNT entity."""

    return specification["entities"]["CUSTOMER_ACCOUNT"]["fields"][field_name]


def get_identity_fields(
    specification: dict,
) -> list[str]:
    """Retrieve the declared composite identity fields."""

    return specification["entities"]["CUSTOMER_ACCOUNT"]["identity"]["fields"]


def get_domain_values(
    specification: dict,
    field_name: str,
) -> list:
    """Retrieve categorical values for a field."""

    field_metadata = get_field_metadata(
        specification,
        field_name,
    )

    values = field_metadata.get("values")

    if not values:
        raise ValueError(f"Field '{field_name}' does not define a domain.")

    return values


# --------------------------------------------------
# Field generators
# --------------------------------------------------


def generate_categorical(
    values: list,
) -> str:
    """Generate a categorical value uniformly."""

    return random.choice(values)


def generate_identifier(
    length: int,
    prefix: str,
    value: int,
) -> str:
    """
    Generate a fixed-width identifier.

    The configured length represents the complete identifier length,
    including the prefix.

    Example:

        length = 6
        prefix = CUS
        value = 1

        result = CUS001
    """

    numeric_length = length - len(prefix)

    if numeric_length <= 0:
        raise ValueError("Identifier length must be greater " "than prefix length.")

    maximum_value = (10**numeric_length) - 1

    if not 0 <= value <= maximum_value:
        raise ValueError(
            f"Identifier value {value} exceeds " f"the configured identifier capacity."
        )

    return prefix + str(value).zfill(numeric_length)


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
# Identity handling
# --------------------------------------------------


def build_identity(
    record: dict,
    identity_fields: list[str],
) -> tuple:
    """
    Construct the composite identity from its declared components.
    """

    return tuple(record[field_name] for field_name in identity_fields)


def find_duplicate_identities(
    dataframe: pd.DataFrame,
    identity_fields: list[str],
) -> list[dict]:
    """Find duplicate composite identities."""

    identity_counts = (
        dataframe.groupby(
            identity_fields,
            dropna=False,
        )
        .size()
        .reset_index(name="count")
    )

    duplicates = identity_counts[identity_counts["count"] > 1]

    return duplicates.to_dict(orient="records")


def count_unique_identities(
    dataframe: pd.DataFrame,
    identity_fields: list[str],
) -> int:
    """Count unique composite identities."""

    return int(dataframe[identity_fields].drop_duplicates().shape[0])


# --------------------------------------------------
# Independent generation
# --------------------------------------------------


def generate_independent_dataset(
    specification: dict,
) -> pd.DataFrame:
    """
    Generate records by treating identity components independently.

    The CUSTOMER_NUMBER field is intentionally generated from a
    bounded identifier space with replacement.

    This creates the possibility of repeated CUSTOMER_NUMBER values,
    allowing the experiment to demonstrate that a repeated component
    does not necessarily imply a repeated composite identity.

    Composite uniqueness is validated only after all fields have been
    generated.
    """

    record_count = specification["generation"]["record_count"]

    company_values = get_domain_values(
        specification,
        "COMPANY_CODE",
    )

    account_type_values = get_domain_values(
        specification,
        "ACCOUNT_TYPE",
    )

    customer_number_metadata = get_field_metadata(
        specification,
        "CUSTOMER_NUMBER",
    )

    customer_number_length = customer_number_metadata["length"]

    customer_number_prefix = customer_number_metadata.get(
        "prefix",
        "",
    )

    numeric_length = customer_number_length - len(customer_number_prefix)

    customer_number_capacity = (10**numeric_length) - 1

    # Use a deliberately bounded identity component space.
    # This allows component reuse while keeping the experiment
    # independent of any real-world identifier semantics.
    customer_number_range = min(
        customer_number_capacity,
        100,
    )

    rows = []

    for _ in range(record_count):

        company_code = generate_categorical(company_values)

        customer_number_value = random.randint(
            1,
            customer_number_range,
        )

        customer_number = generate_identifier(
            length=customer_number_length,
            prefix=customer_number_prefix,
            value=customer_number_value,
        )

        account_type = generate_categorical(account_type_values)

        customer_name = generate_string(
            minimum=get_field_metadata(
                specification,
                "CUSTOMER_NAME",
            )["min_length"],
            maximum=get_field_metadata(
                specification,
                "CUSTOMER_NAME",
            )["max_length"],
        )

        rows.append(
            {
                "COMPANY_CODE": company_code,
                "CUSTOMER_NUMBER": customer_number,
                "ACCOUNT_TYPE": account_type,
                "CUSTOMER_NAME": customer_name,
            }
        )

    return pd.DataFrame(rows)


# --------------------------------------------------
# Coordinated generation
# --------------------------------------------------


def generate_identity_combinations(
    specification: dict,
) -> list[tuple]:
    """
    Build the available composite identity combinations.

    Each combination is treated as one identity rather than as
    independent field values.
    """

    company_values = get_domain_values(
        specification,
        "COMPANY_CODE",
    )

    account_type_values = get_domain_values(
        specification,
        "ACCOUNT_TYPE",
    )

    customer_number_metadata = get_field_metadata(
        specification,
        "CUSTOMER_NUMBER",
    )

    customer_number_length = customer_number_metadata["length"]

    customer_number_prefix = customer_number_metadata.get(
        "prefix",
        "",
    )

    numeric_length = customer_number_length - len(customer_number_prefix)

    customer_number_capacity = (10**numeric_length) - 1

    combinations = []

    for company_code in company_values:

        for customer_number_value in range(
            1,
            customer_number_capacity + 1,
        ):

            customer_number = generate_identifier(
                length=customer_number_length,
                prefix=customer_number_prefix,
                value=customer_number_value,
            )

            for account_type in account_type_values:

                combinations.append(
                    (
                        company_code,
                        customer_number,
                        account_type,
                    )
                )

    return combinations


def generate_coordinated_dataset(
    specification: dict,
) -> pd.DataFrame:
    """
    Generate records by treating the composite identity as a
    coordinated generation unit.

    The available identity combinations are generated first and then
    sampled without replacement.
    """

    record_count = specification["generation"]["record_count"]

    identity_fields = get_identity_fields(specification)

    combinations = generate_identity_combinations(specification)

    if record_count > len(combinations):
        raise ValueError(
            "Requested record count exceeds "
            "available composite identity combinations."
        )

    selected_combinations = random.sample(
        combinations,
        record_count,
    )

    customer_name_metadata = get_field_metadata(
        specification,
        "CUSTOMER_NAME",
    )

    rows = []

    for combination in selected_combinations:

        record = dict(
            zip(
                identity_fields,
                combination,
            )
        )

        record["CUSTOMER_NAME"] = generate_string(
            minimum=customer_name_metadata["min_length"],
            maximum=customer_name_metadata["max_length"],
        )

        rows.append(record)

    return pd.DataFrame(rows)


# --------------------------------------------------
# Component validation
# --------------------------------------------------


def validate_field_constraints(
    dataframe: pd.DataFrame,
    specification: dict,
) -> dict:
    """Validate basic field-level constraints."""

    fields = specification["entities"]["CUSTOMER_ACCOUNT"]["fields"]

    results = {}

    for (
        field_name,
        field_metadata,
    ) in fields.items():

        series = dataframe[field_name]

        non_null = series.dropna()

        field_type = field_metadata["type"]

        passed = True
        errors = []

        if not field_metadata.get(
            "nullable",
            False,
        ):

            if series.isna().any():
                passed = False
                errors.append("NULL value found in non-nullable field.")

        if field_type == "categorical":

            allowed_values = set(field_metadata["values"])

            invalid_values = [
                value for value in non_null if value not in allowed_values
            ]

            if invalid_values:
                passed = False
                errors.append("Value outside declared domain.")

        elif field_type == "identifier":

            expected_length = field_metadata["length"]

            invalid_lengths = [
                value for value in non_null if len(str(value)) != expected_length
            ]

            if invalid_lengths:
                passed = False
                errors.append("Invalid identifier length.")

            prefix = field_metadata.get(
                "prefix",
                "",
            )

            invalid_prefixes = [
                value for value in non_null if not str(value).startswith(prefix)
            ]

            if invalid_prefixes:
                passed = False
                errors.append("Invalid identifier prefix.")

        elif field_type == "string":

            minimum = field_metadata["min_length"]

            maximum = field_metadata["max_length"]

            invalid_lengths = [
                value
                for value in non_null
                if not (minimum <= len(str(value)) <= maximum)
            ]

            if invalid_lengths:
                passed = False
                errors.append("String length outside declared bounds.")

        results[field_name] = {
            "passed": passed,
            "errors": errors,
        }

    return results


# --------------------------------------------------
# Identity validation
# --------------------------------------------------


def validate_composite_identity(
    dataframe: pd.DataFrame,
    identity_fields: list[str],
) -> dict:
    """Validate uniqueness of the complete composite identity."""

    record_count = len(dataframe)

    unique_identity_count = count_unique_identities(
        dataframe,
        identity_fields,
    )

    duplicate_count = record_count - unique_identity_count

    duplicates = find_duplicate_identities(
        dataframe,
        identity_fields,
    )

    return {
        "identity_fields": identity_fields,
        "record_count": record_count,
        "unique_identity_count": (unique_identity_count),
        "duplicate_record_count": (duplicate_count),
        "duplicate_identity_count": len(duplicates),
        "duplicates": duplicates[:20],
        "passed": duplicate_count == 0,
    }


def validate_component_reuse(
    dataframe: pd.DataFrame,
    identity_fields: list[str],
) -> dict:
    """
    Demonstrate that individual identity components can repeat.

    This is an observation, not a failure condition.
    """

    results = {}

    for field_name in identity_fields:

        unique_count = dataframe[field_name].nunique()

        record_count = len(dataframe)

        results[field_name] = {
            "record_count": record_count,
            "unique_value_count": int(unique_count),
            "repeated_values_allowed": (unique_count < record_count),
        }

    return results


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
    """Run Experiment 010."""

    specification = load_specification()

    experiment_metadata = specification["experiment"]

    generation_metadata = specification["generation"]

    seed = generation_metadata["seed"]

    record_count = generation_metadata["record_count"]

    identity_fields = get_identity_fields(specification)

    random.seed(seed)

    print("=" * 70)
    print("FORGE - Experiment 010: " "Composite Identity")
    print("=" * 70)

    print(
        f"Experiment:   "
        f"{experiment_metadata['id']} - "
        f"{experiment_metadata['name']}"
    )

    print(f"Specification: " f"{SPECIFICATION_FILE}")

    print(f"Random seed:   {seed}")

    print(f"Record count:  {record_count}")

    print("\nComposite identity:")

    print("  " + " + ".join(identity_fields))

    # --------------------------------------------------
    # Independent generation
    # --------------------------------------------------

    print("\nApproach A: Independent generation")

    # Reset the seed so each approach starts from a known,
    # deterministic state.
    random.seed(seed)

    independent_dataframe = generate_independent_dataset(specification)

    independent_identity = validate_composite_identity(
        independent_dataframe,
        identity_fields,
    )

    independent_fields = validate_field_constraints(
        independent_dataframe,
        specification,
    )

    independent_reuse = validate_component_reuse(
        independent_dataframe,
        identity_fields,
    )

    print(f"  Records: " f"{len(independent_dataframe)}")

    print(
        f"  Unique composite identities: "
        f"{independent_identity['unique_identity_count']}"
    )

    print(
        f"  Duplicate composite identities: "
        f"{independent_identity['duplicate_identity_count']}"
    )

    print(
        f"  Result: "
        f"{'PASS' if independent_identity['passed'] else 'DUPLICATES DETECTED'}"
    )

    # --------------------------------------------------
    # Coordinated generation
    # --------------------------------------------------

    print("\nApproach B: Coordinated generation")

    random.seed(seed)

    coordinated_dataframe = generate_coordinated_dataset(specification)

    coordinated_identity = validate_composite_identity(
        coordinated_dataframe,
        identity_fields,
    )

    coordinated_fields = validate_field_constraints(
        coordinated_dataframe,
        specification,
    )

    coordinated_reuse = validate_component_reuse(
        coordinated_dataframe,
        identity_fields,
    )

    print(f"  Records: " f"{len(coordinated_dataframe)}")

    print(
        f"  Unique composite identities: "
        f"{coordinated_identity['unique_identity_count']}"
    )

    print(
        f"  Duplicate composite identities: "
        f"{coordinated_identity['duplicate_identity_count']}"
    )

    print(f"  Result: " f"{'PASS' if coordinated_identity['passed'] else 'FAIL'}")

    # --------------------------------------------------
    # Component reuse observation
    # --------------------------------------------------

    print("\nComponent reuse:")

    for (
        field_name,
        result,
    ) in coordinated_reuse.items():

        repeated = result["repeated_values_allowed"]

        print(
            f"  {field_name:<20} "
            f"unique={result['unique_value_count']:4d} "
            f"of {result['record_count']:4d} "
            f"-> "
            f"{'REUSED' if repeated else 'UNIQUE'}"
        )

    # --------------------------------------------------
    # Overall validation
    # --------------------------------------------------

    independent_field_passed = all(
        result["passed"] for result in independent_fields.values()
    )

    coordinated_field_passed = all(
        result["passed"] for result in coordinated_fields.values()
    )

    coordinated_passed = coordinated_identity["passed"] and coordinated_field_passed

    # The experiment itself passes when:
    #
    # 1. The composite identity is explicitly represented.
    # 2. Individual components can repeat.
    # 3. Coordinated generation produces unique identities.
    # 4. Field-level constraints remain valid.
    #
    # Independent generation is intentionally not required to pass
    # uniqueness. Duplicate detection is part of the experiment.

    component_reuse_observed = any(
        result["repeated_values_allowed"] for result in coordinated_reuse.values()
    )

    overall_result = (
        "PASS"
        if (
            coordinated_passed and independent_field_passed and component_reuse_observed
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
        coordinated_dataframe,
        COORDINATED_OUTPUT_FILE,
    )

    statistics = {
        "experiment": experiment_metadata,
        "generation": {
            "seed": seed,
            "record_count": record_count,
        },
        "identity": {
            "type": specification["entities"]["CUSTOMER_ACCOUNT"]["identity"]["type"],
            "fields": identity_fields,
        },
        "independent_generation": {
            "identity_validation": (independent_identity),
            "field_validation": (independent_fields),
            "component_reuse": (independent_reuse),
        },
        "coordinated_generation": {
            "identity_validation": (coordinated_identity),
            "field_validation": (coordinated_fields),
            "component_reuse": (coordinated_reuse),
        },
        "architectural_observation": {
            "identity_is_declared_separately": True,
            "individual_components_can_repeat": (component_reuse_observed),
            "coordinated_generation_preserves_composite_uniqueness": (
                coordinated_passed
            ),
            "independent_generation_requires_identity_validation": True,
        },
        "overall_result": overall_result,
    }

    save_statistics(statistics)

    # --------------------------------------------------
    # Output
    # --------------------------------------------------

    print("\nOutput:")

    print(f"  Independent: " f"{INDEPENDENT_OUTPUT_FILE}")

    print(f"  Coordinated: " f"{COORDINATED_OUTPUT_FILE}")

    print(f"  Statistics:  " f"{STATISTICS_FILE}")

    print("\nFirst 10 records: Independent")

    print(independent_dataframe.head(10).to_string(index=False))

    print("\nFirst 10 records: Coordinated")

    print(coordinated_dataframe.head(10).to_string(index=False))

    print("\nExperiment result:")

    print(
        f"  Independent field validation: "
        f"{'PASS' if independent_field_passed else 'FAIL'}"
    )

    print(
        f"  Coordinated identity: "
        f"{'PASS' if coordinated_identity['passed'] else 'FAIL'}"
    )

    print(
        f"  Component reuse observed: " f"{'YES' if component_reuse_observed else 'NO'}"
    )

    print(f"  Overall: " f"{overall_result}")

    print("\nExperiment completed successfully.")


# --------------------------------------------------
# Entry point
# --------------------------------------------------

if __name__ == "__main__":
    main()
