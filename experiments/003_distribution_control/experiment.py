"""
FORGE - Experiment 003: Distribution-Controlled Generation
===========================================================

Purpose
-------
This experiment tests whether synthetic data can be generated with
explicit statistical distributions without access to real production
data.

The experiment introduces:

    - uniform categorical distributions
    - weighted categorical distributions
    - normal numeric distributions
    - bounded numeric distributions
    - population rates

No machine learning, LLM, or real production data is used.

The objective is to determine whether statistical behavior can be
declared explicitly as metadata and then enforced by the generator.

Experiment
----------
003 - Distribution-Controlled Generation

Key Question
------------
Can explicit statistical distributions produce synthetic data with
predictable statistical characteristics without learning from real data?

Author
------
Ranjoy Sen

Status
------
Experimental

How to Run
----------
From the repository root:

    uv run python experiments/003_distribution_control/experiment.py

Output
------
The generated dataset is written to:

    experiments/003_distribution_control/output/generated_data.csv

Important
---------
The generated data is synthetic and does not represent any real
production dataset.
"""

from pathlib import Path
from collections import Counter
import random
import statistics

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
VOLUME = 1000


# --------------------------------------------------
# Metadata
# --------------------------------------------------

METADATA = {
    "table": "CUSTOMER",
    "fields": {
        "CUSTOMER_ID": {
            "type": "identifier",
            "length": 10,
        },
        "COUNTRY_UNIFORM": {
            "type": "categorical",
            "values": ["US", "IN", "DE", "FR"],
            "distribution": "uniform",
        },
        "COUNTRY_WEIGHTED": {
            "type": "categorical",
            "values": ["US", "IN", "DE", "FR"],
            "distribution": "weighted",
            "weights": [0.50, 0.30, 0.15, 0.05],
        },
        "AGE": {
            "type": "integer",
            "distribution": "normal",
            "mean": 42,
            "std": 10,
            "min": 18,
            "max": 80,
        },
        "PHONE": {
            "type": "string",
            "length": 10,
            "population_rate": 0.70,
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
    """Generate a fixed-width identifier."""

    return str(index).zfill(length)


def generate_uniform(
    values: list[str],
) -> str:
    """Select values with equal probability."""

    return random.choice(values)


def generate_weighted(
    values: list[str],
    weights: list[float],
) -> str:
    """Select values according to explicit probabilities."""

    return random.choices(
        values,
        weights=weights,
        k=1,
    )[0]


def generate_normal(
    mean: float,
    std: float,
    minimum: int,
    maximum: int,
) -> int:
    """
    Generate a value from a normal distribution and constrain it
    to the declared bounds.
    """

    value = random.gauss(
        mean,
        std,
    )

    value = round(value)

    return max(
        minimum,
        min(maximum, value),
    )


def generate_phone(
    length: int,
) -> str:
    """Generate a synthetic numeric string."""

    return "".join(str(random.randint(0, 9)) for _ in range(length))


# --------------------------------------------------
# Population handling
# --------------------------------------------------


def should_populate(
    population_rate: float,
) -> bool:
    """Determine whether an optional field receives a value."""

    return random.random() < population_rate


# --------------------------------------------------
# Field generation
# --------------------------------------------------


def generate_value(
    field_metadata: dict,
    index: int,
):
    """Generate a value according to the field metadata."""

    field_type = field_metadata["type"]

    if field_type == "identifier":
        return generate_identifier(
            field_metadata["length"],
            index,
        )

    if field_type == "categorical":

        distribution = field_metadata.get(
            "distribution",
            "uniform",
        )

        if distribution == "uniform":
            return generate_uniform(field_metadata["values"])

        if distribution == "weighted":
            return generate_weighted(
                field_metadata["values"],
                field_metadata["weights"],
            )

        raise ValueError(f"Unsupported categorical distribution: " f"{distribution}")

    if field_type == "integer":

        distribution = field_metadata.get(
            "distribution",
            "uniform",
        )

        if distribution == "normal":
            return generate_normal(
                field_metadata["mean"],
                field_metadata["std"],
                field_metadata["min"],
                field_metadata["max"],
            )

        raise ValueError(f"Unsupported integer distribution: " f"{distribution}")

    if field_type == "string":
        return generate_phone(field_metadata["length"])

    raise ValueError(f"Unsupported field type: {field_type}")


# --------------------------------------------------
# Dataset generation
# --------------------------------------------------


def generate_dataset(
    metadata: dict,
    volume: int,
) -> pd.DataFrame:
    """Generate a statistically controlled dataset."""

    rows = []

    for index in range(1, volume + 1):

        row = {}

        for field_name, field_metadata in metadata["fields"].items():

            population_rate = field_metadata.get(
                "population_rate",
                1.0,
            )

            if population_rate < 1.0:

                if not should_populate(population_rate):
                    row[field_name] = None
                    continue

            row[field_name] = generate_value(
                field_metadata,
                index,
            )

        rows.append(row)

    return pd.DataFrame(rows)


# --------------------------------------------------
# Statistical validation
# --------------------------------------------------


def validate_uniform_distribution(
    series: pd.Series,
    expected_values: list[str],
) -> None:
    """Display observed frequencies for a uniform distribution."""

    counts = Counter(series.dropna())

    total = sum(counts.values())

    print("\nUniform distribution:")

    for value in expected_values:

        observed = counts.get(
            value,
            0,
        )

        percentage = observed / total

        print(f"  {value}: " f"{observed:4d} " f"({percentage:.2%})")


def validate_weighted_distribution(
    series: pd.Series,
    expected_values: list[str],
    expected_weights: list[float],
) -> None:
    """Display observed versus expected weighted frequencies."""

    counts = Counter(series.dropna())

    total = sum(counts.values())

    print("\nWeighted distribution:")

    for value, expected in zip(
        expected_values,
        expected_weights,
    ):

        observed = counts.get(
            value,
            0,
        )

        observed_rate = observed / total

        print(
            f"  {value}: " f"observed={observed_rate:.2%}, " f"expected={expected:.2%}"
        )


def validate_normal_distribution(
    series: pd.Series,
    expected_mean: float,
    expected_std: float,
) -> None:
    """Display observed versus expected normal distribution statistics."""

    values = series.dropna().tolist()

    observed_mean = statistics.mean(values)
    observed_std = statistics.stdev(values)

    print("\nNormal distribution:")

    print(f"  Mean: " f"observed={observed_mean:.2f}, " f"expected={expected_mean:.2f}")

    print(f"  Std : " f"observed={observed_std:.2f}, " f"expected={expected_std:.2f}")


def validate_population_rate(
    series: pd.Series,
    expected_rate: float,
) -> None:
    """Display observed versus expected population rate."""

    observed_rate = series.notna().mean()

    print("\nPopulation rate:")

    print(f"  Observed={observed_rate:.2%}, " f"Expected={expected_rate:.2%}")


# --------------------------------------------------
# Output
# --------------------------------------------------


def save_output(
    dataframe: pd.DataFrame,
) -> None:
    """Save generated data."""

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
    """Run Experiment 003."""

    random.seed(RANDOM_SEED)

    print("=" * 60)
    print("FORGE - Experiment 003")
    print("Distribution-Controlled Generation")
    print("=" * 60)

    print("\nGenerating synthetic data...")

    dataframe = generate_dataset(
        metadata=METADATA,
        volume=VOLUME,
    )

    print(f"  Records: {len(dataframe)}")

    validate_uniform_distribution(
        dataframe["COUNTRY_UNIFORM"],
        METADATA["fields"]["COUNTRY_UNIFORM"]["values"],
    )

    validate_weighted_distribution(
        dataframe["COUNTRY_WEIGHTED"],
        METADATA["fields"]["COUNTRY_WEIGHTED"]["values"],
        METADATA["fields"]["COUNTRY_WEIGHTED"]["weights"],
    )

    validate_normal_distribution(
        dataframe["AGE"],
        METADATA["fields"]["AGE"]["mean"],
        METADATA["fields"]["AGE"]["std"],
    )

    validate_population_rate(
        dataframe["PHONE"],
        METADATA["fields"]["PHONE"]["population_rate"],
    )

    save_output(dataframe)

    print("\nOutput:")
    print(f"  {OUTPUT_FILE}")

    print("\nFirst 20 records:")
    print(dataframe.head(20).to_string(index=False))

    print("\nExperiment completed successfully.")


# --------------------------------------------------
# Entry point
# --------------------------------------------------

if __name__ == "__main__":
    main()
