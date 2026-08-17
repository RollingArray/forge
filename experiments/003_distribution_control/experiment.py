"""
FORGE - Experiment 003: Distribution-Controlled Generation
===========================================================

Purpose
-------
This experiment tests whether synthetic data can be generated with
explicit statistical distributions without access to real production
data.

The experiment builds on the metadata-driven generation established
in Experiment 001 and the field constraint concepts established in
Experiment 002.

The experiment introduces:

    - uniform categorical distributions
    - weighted categorical distributions
    - normal numeric distributions
    - bounded numeric distributions
    - population rates
    - statistical validation

No machine learning, deep learning, LLM, or real production data
is used.

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

Input
-----
The experiment specification is read from:

    experiments/003_distribution_control/specification.json

Output
------
The generated dataset is written to:

    experiments/003_distribution_control/output/generated_data.csv

Important
---------
The generated data is synthetic and does not represent any real
production dataset.
"""

from collections import Counter
from pathlib import Path
import json
import random
import statistics

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
    """
    Load the experiment specification from JSON.

    The specification is the source of truth for:

        - entity definition
        - field definition
        - generation behavior
        - distributions
        - population rates
        - record volume
        - random seed
    """

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
    """Generate a fixed-width identifier."""

    return str(index).zfill(length)


def generate_uniform(
    values: list[str],
) -> str:
    """Select a value using a uniform categorical distribution."""

    return random.choice(values)


def generate_weighted(
    values: list[str],
    weights: list[float],
) -> str:
    """Select a value using an explicit weighted distribution."""

    if len(values) != len(weights):
        raise ValueError(
            "Number of categorical values must match " "number of weights."
        )

    if not weights:
        raise ValueError("Weighted distribution requires at least one weight.")

    if abs(sum(weights) - 1.0) > 0.000001:
        raise ValueError("Weighted distribution weights must sum to 1.0.")

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
    Generate an integer using a normal distribution.

    The generated value is constrained to the declared minimum
    and maximum.
    """

    value = random.gauss(
        mean,
        std,
    )

    value = round(value)

    return max(
        minimum,
        min(
            maximum,
            value,
        ),
    )


def generate_string(
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
    """
    Determine whether an optional field should be populated.
    """

    if not 0.0 <= population_rate <= 1.0:
        raise ValueError("Population rate must be between 0.0 and 1.0.")

    return random.random() < population_rate


# --------------------------------------------------
# Field generation
# --------------------------------------------------


def generate_value(
    field_metadata: dict,
    index: int,
):
    """
    Generate a field value according to its metadata.
    """

    field_type = field_metadata["type"]

    # --------------------------------------------------
    # Identifier
    # --------------------------------------------------

    if field_type == "identifier":

        return generate_identifier(
            length=field_metadata["length"],
            index=index,
        )

    # --------------------------------------------------
    # Categorical
    # --------------------------------------------------

    if field_type == "categorical":

        values = field_metadata["values"]

        distribution = field_metadata.get(
            "distribution",
            {
                "type": "uniform",
            },
        )

        distribution_type = distribution["type"]

        if distribution_type == "uniform":

            return generate_uniform(
                values,
            )

        if distribution_type == "weighted":

            return generate_weighted(
                values,
                distribution["weights"],
            )

        raise ValueError(
            "Unsupported categorical distribution: " f"{distribution_type}"
        )

    # --------------------------------------------------
    # Integer
    # --------------------------------------------------

    if field_type == "integer":

        distribution = field_metadata.get(
            "distribution",
            {
                "type": "uniform",
            },
        )

        distribution_type = distribution["type"]

        if distribution_type == "normal":

            return generate_normal(
                mean=distribution["mean"],
                std=distribution["std"],
                minimum=distribution["min"],
                maximum=distribution["max"],
            )

        raise ValueError("Unsupported integer distribution: " f"{distribution_type}")

    # --------------------------------------------------
    # String
    # --------------------------------------------------

    if field_type == "string":

        return generate_string(
            field_metadata["length"],
        )

    raise ValueError(f"Unsupported field type: {field_type}")


# --------------------------------------------------
# Dataset generation
# --------------------------------------------------


def generate_dataset(
    entity_metadata: dict,
    volume: int,
) -> pd.DataFrame:
    """
    Generate a dataset according to the entity specification.
    """

    rows = []

    fields = entity_metadata["fields"]

    for index in range(
        1,
        volume + 1,
    ):

        row = {}

        for field_name, field_metadata in fields.items():

            population_rate = field_metadata.get(
                "population_rate",
                1.0,
            )

            if population_rate < 1.0:

                if not should_populate(
                    population_rate,
                ):
                    row[field_name] = None
                    continue

            row[field_name] = generate_value(
                field_metadata=field_metadata,
                index=index,
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

    counts = Counter(
        series.dropna(),
    )

    total = sum(
        counts.values(),
    )

    print("\nUniform distribution:")

    for value in expected_values:

        observed = counts.get(
            value,
            0,
        )

        percentage = observed / total if total else 0

        print(f"  {value}: " f"{observed:4d} " f"({percentage:.2%})")


def validate_weighted_distribution(
    series: pd.Series,
    expected_values: list[str],
    expected_weights: list[float],
) -> None:
    """Display observed versus expected weighted frequencies."""

    counts = Counter(
        series.dropna(),
    )

    total = sum(
        counts.values(),
    )

    print("\nWeighted distribution:")

    for value, expected in zip(
        expected_values,
        expected_weights,
    ):

        observed = counts.get(
            value,
            0,
        )

        observed_rate = observed / total if total else 0

        print(
            f"  {value}: " f"observed={observed_rate:.2%}, " f"expected={expected:.2%}"
        )


def validate_normal_distribution(
    series: pd.Series,
    expected_mean: float,
    expected_std: float,
    minimum: int,
    maximum: int,
) -> None:
    """Display observed versus expected numeric statistics."""

    values = series.dropna().tolist()

    if not values:
        print("\nNormal distribution: no values generated.")
        return

    observed_mean = statistics.mean(values)

    observed_std = statistics.stdev(values) if len(values) > 1 else 0

    observed_min = min(values)

    observed_max = max(values)

    print("\nNormal distribution:")

    print(f"  Mean: " f"observed={observed_mean:.2f}, " f"expected={expected_mean:.2f}")

    print(f"  Std : " f"observed={observed_std:.2f}, " f"expected={expected_std:.2f}")

    print(f"  Min : " f"observed={observed_min}, " f"allowed={minimum}")

    print(f"  Max : " f"observed={observed_max}, " f"allowed={maximum}")


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
    """Save generated data to CSV."""

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

    specification = load_specification()

    generation_config = specification["generation"]

    random_seed = generation_config["seed"]

    volume = generation_config["record_count"]

    entity = specification["entity"]

    random.seed(
        random_seed,
    )

    print("=" * 70)
    print("FORGE - Experiment 003")
    print("Distribution-Controlled Generation")
    print("=" * 70)

    print(f"\nSpecification: " f"{SPECIFICATION_FILE}")

    print(f"Random seed:   " f"{random_seed}")

    print(f"Record count:  " f"{volume}")

    print(f"Entity:        " f"{entity['name']}")

    print("\nGenerating synthetic data...")

    dataframe = generate_dataset(
        entity_metadata=entity,
        volume=volume,
    )

    print(f"  Records generated: " f"{len(dataframe)}")

    fields = entity["fields"]

    # --------------------------------------------------
    # Validate uniform distribution
    # --------------------------------------------------

    uniform_field = fields["COUNTRY_UNIFORM"]

    validate_uniform_distribution(
        dataframe["COUNTRY_UNIFORM"],
        uniform_field["values"],
    )

    # --------------------------------------------------
    # Validate weighted distribution
    # --------------------------------------------------

    weighted_field = fields["COUNTRY_WEIGHTED"]

    weighted_distribution = weighted_field["distribution"]

    validate_weighted_distribution(
        dataframe["COUNTRY_WEIGHTED"],
        weighted_field["values"],
        weighted_distribution["weights"],
    )

    # --------------------------------------------------
    # Validate normal distribution
    # --------------------------------------------------

    age_field = fields["AGE"]

    age_distribution = age_field["distribution"]

    validate_normal_distribution(
        dataframe["AGE"],
        age_distribution["mean"],
        age_distribution["std"],
        age_distribution["min"],
        age_distribution["max"],
    )

    # --------------------------------------------------
    # Validate population rate
    # --------------------------------------------------

    phone_field = fields["PHONE"]

    validate_population_rate(
        dataframe["PHONE"],
        phone_field["population_rate"],
    )

    # --------------------------------------------------
    # Save output
    # --------------------------------------------------

    save_output(
        dataframe,
    )

    print("\nOutput:")
    print(f"  {OUTPUT_FILE}")

    print("\nFirst 20 records:")

    print(
        dataframe.head(20).to_string(
            index=False,
        )
    )

    print("\nExperiment completed successfully.")


# --------------------------------------------------
# Entry point
# --------------------------------------------------

if __name__ == "__main__":
    main()
