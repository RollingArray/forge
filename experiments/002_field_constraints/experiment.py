"""
FORGE - Experiment 002: Field Constraints
=========================================

Purpose
-------
This experiment tests whether explicit field constraints can improve
the structural realism of synthetic data without access to real data.

The experiment extends Experiment 001 by introducing constraints such as:

    - fixed-width identifiers
    - numeric ranges
    - allowed categorical values
    - nullable fields
    - population rate
    - string length
    - pattern-based values

No machine learning, LLM, or statistical learning is used.

The objective is to understand how much structural realism can be
achieved through declarative constraints alone.

Experiment
----------
002 - Field Constraints

Key Question
------------
Can explicit field constraints produce synthetic values that better
represent the structural expectations of a real dataset?

Author
------
Ranjoy Sen

Status
------
Experimental

How to Run
----------
From the repository root:

    uv run python experiments/002_field_constraints/experiment.py

Output
------
The generated dataset is written to:

    experiments/002_field_constraints/output/generated_data.csv

Important
---------
The generated data is synthetic and does not represent any real
production dataset.
"""

from pathlib import Path
import random
import re

import pandas as pd

# --------------------------------------------------
# Experiment paths
# --------------------------------------------------

EXPERIMENT_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = EXPERIMENT_DIR / "output"
OUTPUT_FILE = OUTPUT_DIR / "generated_data.csv"


# --------------------------------------------------
# Experiment configuration
# --------------------------------------------------

RANDOM_SEED = 42
VOLUME = 30


# --------------------------------------------------
# Metadata
# --------------------------------------------------

METADATA = {
    "table": "CUSTOMER",
    "fields": {
        "CUSTOMER_ID": {
            "type": "identifier",
            "length": 10,
            "nullable": False,
        },
        "COUNTRY": {
            "type": "categorical",
            "values": ["US", "IN", "DE", "FR"],
            "nullable": False,
        },
        "AGE": {
            "type": "integer",
            "min": 18,
            "max": 80,
            "nullable": False,
        },
        "CUSTOMER_CODE": {
            "type": "pattern",
            "pattern": "CUS-#####",
            "nullable": False,
        },
        "PHONE": {
            "type": "string",
            "min_length": 10,
            "max_length": 10,
            "nullable": True,
            "population_rate": 0.80,
        },
    },
}


# --------------------------------------------------
# Value generators
# --------------------------------------------------


def generate_identifier(
    length: int,
    index: int,
) -> str:
    """Generate a fixed-width numeric identifier."""

    return str(index).zfill(length)


def generate_categorical(
    values: list[str],
) -> str:
    """Generate a value from an explicit domain."""

    return random.choice(values)


def generate_integer(
    minimum: int,
    maximum: int,
) -> int:
    """Generate an integer within the configured range."""

    return random.randint(minimum, maximum)


def generate_pattern(
    pattern: str,
) -> str:
    """
    Generate a simple pattern-based value.

    Supported syntax:

        # = numeric character
        A = uppercase alphabetic character
    """

    result = []

    for character in pattern:
        if character == "#":
            result.append(str(random.randint(0, 9)))

        elif character == "A":
            result.append(chr(random.randint(ord("A"), ord("Z"))))

        else:
            result.append(character)

    return "".join(result)


def generate_string(
    min_length: int,
    max_length: int,
) -> str:
    """Generate an uppercase alphanumeric string."""

    length = random.randint(
        min_length,
        max_length,
    )

    characters = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"

    return "".join(random.choice(characters) for _ in range(length))


# --------------------------------------------------
# Constraint handling
# --------------------------------------------------


def should_populate(
    field_metadata: dict,
) -> bool:
    """
    Determine whether an optional field should receive a value.

    population_rate represents the expected probability that the field
    is populated.
    """

    population_rate = field_metadata.get(
        "population_rate",
        1.0,
    )

    return random.random() < population_rate


# --------------------------------------------------
# Dataset generation
# --------------------------------------------------


def generate_value(
    field_metadata: dict,
    index: int,
):
    """Generate one value according to field metadata."""

    field_type = field_metadata["type"]

    if field_type == "identifier":
        return generate_identifier(
            field_metadata["length"],
            index,
        )

    if field_type == "categorical":
        return generate_categorical(
            field_metadata["values"],
        )

    if field_type == "integer":
        return generate_integer(
            field_metadata["min"],
            field_metadata["max"],
        )

    if field_type == "pattern":
        return generate_pattern(
            field_metadata["pattern"],
        )

    if field_type == "string":
        return generate_string(
            field_metadata["min_length"],
            field_metadata["max_length"],
        )

    raise ValueError(f"Unsupported field type: {field_type}")


def generate_dataset(
    metadata: dict,
    volume: int,
) -> pd.DataFrame:
    """Generate a synthetic dataset from constrained metadata."""

    fields = metadata["fields"]

    rows = []

    for index in range(1, volume + 1):

        row = {}

        for field_name, field_metadata in fields.items():

            if field_metadata.get("nullable", False):

                if not should_populate(field_metadata):
                    row[field_name] = None
                    continue

            row[field_name] = generate_value(
                field_metadata,
                index,
            )

        rows.append(row)

    return pd.DataFrame(rows)


# --------------------------------------------------
# Validation
# --------------------------------------------------


def validate_dataset(
    dataframe: pd.DataFrame,
    metadata: dict,
) -> None:
    """
    Validate the generated dataset against the declared constraints.

    This is intentionally simple.

    The objective is to demonstrate that generation and validation can
    be driven by the same metadata.
    """

    for field_name, field_metadata in metadata["fields"].items():

        series = dataframe[field_name]

        non_null = series.dropna()

        field_type = field_metadata["type"]

        if field_type == "identifier":

            expected_length = field_metadata["length"]

            assert all(len(str(value)) == expected_length for value in non_null)

        elif field_type == "categorical":

            allowed_values = set(field_metadata["values"])

            assert set(non_null).issubset(allowed_values)

        elif field_type == "integer":

            minimum = field_metadata["min"]
            maximum = field_metadata["max"]

            assert non_null.between(
                minimum,
                maximum,
            ).all()

        elif field_type == "pattern":

            pattern = field_metadata["pattern"]

            regex = (
                "^"
                + re.escape(pattern).replace(r"\#", r"[0-9]").replace(r"\A", r"[A-Z]")
                + "$"
            )

            assert all(re.match(regex, str(value)) for value in non_null)

        elif field_type == "string":

            minimum = field_metadata["min_length"]
            maximum = field_metadata["max_length"]

            assert all(minimum <= len(str(value)) <= maximum for value in non_null)


# --------------------------------------------------
# Output
# --------------------------------------------------


def save_output(
    dataframe: pd.DataFrame,
) -> None:
    """Save the generated dataset."""

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    dataframe.to_csv(
        OUTPUT_FILE,
        index=False,
    )


# --------------------------------------------------
# Experiment execution
# --------------------------------------------------


def main() -> None:
    """Run Experiment 002."""

    random.seed(RANDOM_SEED)

    print("=" * 60)
    print("FORGE - Experiment 002")
    print("Field Constraints")
    print("=" * 60)

    print("\nMetadata:")
    print(f"  Table   : {METADATA['table']}")
    print(f"  Fields  : {len(METADATA['fields'])}")
    print(f"  Records : {VOLUME}")

    print("\nGenerating constrained synthetic data...")

    dataframe = generate_dataset(
        metadata=METADATA,
        volume=VOLUME,
    )

    print("Validating generated data...")

    validate_dataset(
        dataframe=dataframe,
        metadata=METADATA,
    )

    save_output(dataframe)

    print("\nValidation successful.")

    print(f"  Output : {OUTPUT_FILE}")

    print("\nGenerated data:")
    print(dataframe.to_string(index=False))

    print("\nExperiment completed successfully.")


# --------------------------------------------------
# Entry point
# --------------------------------------------------

if __name__ == "__main__":
    main()
