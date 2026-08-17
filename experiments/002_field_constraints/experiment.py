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

The experiment specification is externalized into specification.json.
The Python implementation acts as the generation and validation engine.

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

Specification
-------------
The experiment reads its configuration from:

    experiments/002_field_constraints/specification.json

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
import json
import random
import re

import pandas as pd

# --------------------------------------------------
# Experiment paths
# --------------------------------------------------

EXPERIMENT_DIR = Path(__file__).resolve().parent
SPECIFICATION_FILE = EXPERIMENT_DIR / "specification.json"
OUTPUT_DIR = EXPERIMENT_DIR / "output"
OUTPUT_FILE = OUTPUT_DIR / "generated_data.csv"


# --------------------------------------------------
# Specification loading
# --------------------------------------------------


def load_specification() -> dict:
    """Load the experiment specification from JSON."""

    if not SPECIFICATION_FILE.exists():
        raise FileNotFoundError(f"Specification file not found: {SPECIFICATION_FILE}")

    with SPECIFICATION_FILE.open(
        "r",
        encoding="utf-8",
    ) as file:
        return json.load(file)


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

    return random.randint(
        minimum,
        maximum,
    )


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
            result.append(
                chr(
                    random.randint(
                        ord("A"),
                        ord("Z"),
                    )
                )
            )

        else:
            result.append(character)

    return "".join(result)


def generate_string(
    minimum: int,
    maximum: int,
) -> str:
    """Generate an uppercase alphanumeric string."""

    length = random.randint(
        minimum,
        maximum,
    )

    characters = "ABCDEFGHIJKLMNOPQRSTUVWXYZ" "0123456789"

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
# Field generation
# --------------------------------------------------


def generate_value(
    field_metadata: dict,
    index: int,
):
    """Generate one value according to field metadata."""

    field_type = field_metadata["type"]

    if field_type == "identifier":

        return generate_identifier(
            length=field_metadata["length"],
            index=index,
        )

    if field_type == "categorical":

        return generate_categorical(
            values=field_metadata["values"],
        )

    if field_type == "integer":

        return generate_integer(
            minimum=field_metadata["min"],
            maximum=field_metadata["max"],
        )

    if field_type == "pattern":

        return generate_pattern(
            pattern=field_metadata["pattern"],
        )

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
    """Generate a synthetic dataset from the specification."""

    entity = specification["entity"]
    fields = entity["fields"]

    volume = specification["generation"]["volume"]

    rows = []

    for index in range(
        1,
        volume + 1,
    ):

        row = {}

        for field_name, field_metadata in fields.items():

            if field_metadata.get(
                "nullable",
                False,
            ):

                if not should_populate(field_metadata):
                    row[field_name] = None
                    continue

            row[field_name] = generate_value(
                field_metadata=field_metadata,
                index=index,
            )

        rows.append(row)

    return pd.DataFrame(rows)


# --------------------------------------------------
# Validation
# --------------------------------------------------


def validate_dataset(
    dataframe: pd.DataFrame,
    specification: dict,
) -> None:
    """
    Validate generated data against the declared constraints.

    Generation and validation are intentionally driven by the same
    specification.
    """

    fields = specification["entity"]["fields"]

    for field_name, field_metadata in fields.items():

        series = dataframe[field_name]

        non_null = series.dropna()

        field_type = field_metadata["type"]

        # ------------------------------------------
        # Identifier
        # ------------------------------------------

        if field_type == "identifier":

            expected_length = field_metadata["length"]

            assert all(len(str(value)) == expected_length for value in non_null)

        # ------------------------------------------
        # Categorical
        # ------------------------------------------

        elif field_type == "categorical":

            allowed_values = set(field_metadata["values"])

            assert set(non_null).issubset(allowed_values)

        # ------------------------------------------
        # Integer
        # ------------------------------------------

        elif field_type == "integer":

            minimum = field_metadata["min"]
            maximum = field_metadata["max"]

            assert non_null.between(
                minimum,
                maximum,
            ).all()

        # ------------------------------------------
        # Pattern
        # ------------------------------------------

        elif field_type == "pattern":

            pattern = field_metadata["pattern"]

            regex = (
                "^"
                + re.escape(pattern)
                .replace(
                    r"\#",
                    r"[0-9]",
                )
                .replace(
                    r"\A",
                    r"[A-Z]",
                )
                + "$"
            )

            assert all(
                re.match(
                    regex,
                    str(value),
                )
                for value in non_null
            )

        # ------------------------------------------
        # String
        # ------------------------------------------

        elif field_type == "string":

            minimum = field_metadata["min_length"]
            maximum = field_metadata["max_length"]

            assert all(minimum <= len(str(value)) <= maximum for value in non_null)

        else:

            raise ValueError(
                f"Unsupported field type during validation: " f"{field_type}"
            )


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

    specification = load_specification()

    random.seed(specification["generation"]["seed"])

    entity_name = specification["entity"]["name"]
    fields = specification["entity"]["fields"]
    volume = specification["generation"]["volume"]

    print("=" * 60)
    print("FORGE - Experiment 002")
    print("Field Constraints")
    print("=" * 60)

    print("\nSpecification:")
    print(f"  File    : {SPECIFICATION_FILE}")
    print(f"  Entity  : {entity_name}")
    print(f"  Fields  : {len(fields)}")
    print(f"  Records : {volume}")

    print("\nGenerating constrained synthetic data...")

    dataframe = generate_dataset(
        specification=specification,
    )

    print("Validating generated data...")

    validate_dataset(
        dataframe=dataframe,
        specification=specification,
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
