"""
FORGE - Experiment 001: Metadata-Only Generation
=================================================

Purpose
-------
This experiment tests whether a small declarative metadata specification
is sufficient to generate a basic synthetic dataset without access to
real production data.

The experiment deliberately avoids machine learning, LLMs, and statistical
learning. The objective is to understand what can be achieved using
explicit metadata and deterministic generation rules alone.

This is an experiment, not production FORGE code.

Experiment
----------
001 - Metadata-Only Generation

Key Question
------------
Can a generic generator produce structurally valid synthetic data from
metadata alone?

Author
------
Ranjoy Sen

Status
------
Experimental

How to Run
----------
From the repository root:

    uv run python experiments/001_metadata_only/experiment.py

Output
------
The generated dataset is written to:

    experiments/001_metadata_only/output/generated_data.csv

The output directory is created automatically if it does not exist.

Important
---------
The generated data is synthetic and does not represent any real
production dataset.
"""

from pathlib import Path

import pandas as pd

# --------------------------------------------------
# Experiment paths
# --------------------------------------------------

EXPERIMENT_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = EXPERIMENT_DIR / "output"
OUTPUT_FILE = OUTPUT_DIR / "generated_data.csv"


# --------------------------------------------------
# Experiment metadata
# --------------------------------------------------

METADATA = {
    "table": "CUSTOMER",
    "fields": {
        "CUSTOMER_ID": {
            "type": "identifier",
            "length": 8,
        },
        "COUNTRY": {
            "type": "categorical",
            "values": ["US", "IN", "DE", "FR"],
        },
        "AGE": {
            "type": "integer",
            "min": 18,
            "max": 80,
        },
        "ACTIVE": {
            "type": "boolean",
        },
    },
}


# --------------------------------------------------
# Generation functions
# --------------------------------------------------


def generate_identifier(length: int, index: int) -> str:
    """Generate a fixed-width synthetic identifier."""
    return str(index).zfill(length)


def generate_dataset(metadata: dict, volume: int = 20) -> pd.DataFrame:
    """
    Generate a synthetic dataset from declarative metadata.

    No real data is used by this experiment.
    """

    fields = metadata["fields"]
    rows = []

    for index in range(1, volume + 1):
        row = {}

        for field_name, field_metadata in fields.items():
            field_type = field_metadata["type"]

            if field_type == "identifier":
                row[field_name] = generate_identifier(
                    field_metadata["length"],
                    index,
                )

            elif field_type == "categorical":
                values = field_metadata["values"]
                row[field_name] = values[(index - 1) % len(values)]

            elif field_type == "integer":
                minimum = field_metadata["min"]
                maximum = field_metadata["max"]

                value_range = maximum - minimum + 1
                row[field_name] = minimum + ((index - 1) % value_range)

            elif field_type == "boolean":
                row[field_name] = index % 2 == 1

            else:
                raise ValueError(f"Unsupported field type: {field_type}")

        rows.append(row)

    return pd.DataFrame(rows)


# --------------------------------------------------
# Output
# --------------------------------------------------


def save_output(dataframe: pd.DataFrame) -> None:
    """Save the generated dataset to the experiment output directory."""

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    dataframe.to_csv(
        OUTPUT_FILE,
        index=False,
    )


# --------------------------------------------------
# Experiment execution
# --------------------------------------------------


def main() -> None:
    """Run Experiment 001."""

    print("=" * 60)
    print("FORGE - Experiment 001")
    print("Metadata-Only Generation")
    print("=" * 60)

    print("\nMetadata:")
    print(f"  Table   : {METADATA['table']}")
    print(f"  Fields  : {len(METADATA['fields'])}")

    print("\nGenerating synthetic data...")

    dataframe = generate_dataset(
        metadata=METADATA,
        volume=20,
    )

    save_output(dataframe)

    print(f"  Records : {len(dataframe)}")
    print(f"  Output  : {OUTPUT_FILE}")

    print("\nGenerated data:")
    print(dataframe.to_string(index=False))

    print("\nExperiment completed successfully.")


# --------------------------------------------------
# Entry point
# --------------------------------------------------

if __name__ == "__main__":
    main()
