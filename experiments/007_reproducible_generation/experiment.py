"""
FORGE - Experiment 007: Reproducible Generation
================================================

Purpose
-------
This experiment tests whether the same generation specification,
configuration, and random seed can produce an identical synthetic
dataset across repeated executions.

The experiment builds on the generation capabilities established in:

    Experiment 001 - Metadata-Only Generation
    Experiment 002 - Field Constraints
    Experiment 003 - Distribution-Controlled Generation

The experiment performs three primary tests:

    1. Same specification + same seed
       -> datasets should be identical.

    2. Same specification + different seed
       -> datasets should be different.

    3. Same specification + same seed across repeated executions
       -> datasets should remain identical.

No machine learning, deep learning, LLM, or real production data
is used.

Experiment
----------
007 - Reproducible Generation

Key Question
------------
Can FORGE guarantee reproducible synthetic data when the generation
specification, configuration, and random seed remain unchanged?

Author
------
Ranjoy Sen

Status
------
Experimental

How to Run
----------
From the repository root:

    uv run python experiments/007_reproducible_generation/experiment.py

Output
------
The generated datasets are written to:

    experiments/007_reproducible_generation/output/

The reproducibility results are written to:

    experiments/007_reproducible_generation/output/reproducibility_results.json

Important
---------
The generated data is synthetic and does not represent any real
production dataset.
"""

from pathlib import Path
import hashlib
import json
import random

import pandas as pd

# --------------------------------------------------
# Experiment paths
# --------------------------------------------------

EXPERIMENT_DIR = Path(__file__).resolve().parent

SPECIFICATION_FILE = EXPERIMENT_DIR / "specification.json"

OUTPUT_DIR = EXPERIMENT_DIR / "output"

RESULTS_FILE = OUTPUT_DIR / "reproducibility_results.json"


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
# Field generators
# --------------------------------------------------


def generate_identifier(
    length: int,
    prefix: str,
    index: int,
) -> str:
    """Generate a fixed-width identifier with a configurable prefix."""

    numeric_length = length - len(prefix)

    if numeric_length <= 0:
        raise ValueError("Identifier length must be greater than prefix length.")

    return prefix + str(index).zfill(numeric_length)


def generate_categorical(
    values: list[str],
    distribution: dict | None,
) -> str:
    """Generate a categorical value according to its distribution."""

    if not values:
        raise ValueError("Categorical field must define at least one value.")

    if not distribution:

        return random.choice(values)

    distribution_type = distribution.get(
        "type",
        "uniform",
    )

    if distribution_type == "uniform":

        return random.choice(values)

    if distribution_type == "weighted":

        weights = distribution.get("weights")

        if weights is None:
            raise ValueError("Weighted distribution requires weights.")

        if len(weights) != len(values):
            raise ValueError("Number of weights must match number of values.")

        return random.choices(
            values,
            weights=weights,
            k=1,
        )[0]

    raise ValueError("Unsupported categorical distribution: " f"{distribution_type}")


def generate_integer(
    minimum: int,
    maximum: int,
    distribution: dict | None,
) -> int:
    """Generate an integer according to its distribution."""

    if minimum > maximum:
        raise ValueError("Minimum value cannot be greater than maximum value.")

    distribution_type = (distribution or {}).get(
        "type",
        "uniform",
    )

    if distribution_type == "uniform":

        return random.randint(
            minimum,
            maximum,
        )

    raise ValueError("Unsupported integer distribution: " f"{distribution_type}")


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

            result.append(
                str(
                    random.randint(
                        0,
                        9,
                    )
                )
            )

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
# Population handling
# --------------------------------------------------


def should_populate(
    field_metadata: dict,
) -> bool:
    """Determine whether an optional field should be populated."""

    population_rate = field_metadata.get(
        "population_rate",
        1.0,
    )

    return random.random() < population_rate


# --------------------------------------------------
# Field generation
# --------------------------------------------------


def generate_field_value(
    field_metadata: dict,
    index: int,
):
    """Generate one field value from metadata."""

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

        return generate_categorical(
            values=field_metadata["values"],
            distribution=field_metadata.get("distribution"),
        )

    if field_type == "integer":

        return generate_integer(
            minimum=field_metadata["min"],
            maximum=field_metadata["max"],
            distribution=field_metadata.get("distribution"),
        )

    if field_type == "pattern":

        return generate_pattern(pattern=field_metadata["pattern"])

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
    """Generate a dataset using the supplied specification."""

    generation = specification["generation"]

    record_count = generation["record_count"]

    entities = specification["entities"]

    if len(entities) != 1:
        raise ValueError("Experiment 007 expects exactly one entity.")

    entity_name = next(iter(entities))

    entity_metadata = entities[entity_name]

    rows = []

    for index in range(
        1,
        record_count + 1,
    ):

        row = {}

        for (
            field_name,
            field_metadata,
        ) in entity_metadata["fields"].items():

            nullable = field_metadata.get(
                "nullable",
                False,
            )

            if nullable:

                if not should_populate(field_metadata):

                    row[field_name] = None

                    continue

            row[field_name] = generate_field_value(
                field_metadata=field_metadata,
                index=index,
            )

        rows.append(row)

    return pd.DataFrame(rows)


# --------------------------------------------------
# Dataset comparison
# --------------------------------------------------


def dataframe_to_bytes(
    dataframe: pd.DataFrame,
) -> bytes:
    """
    Convert a dataframe into a deterministic CSV byte representation.

    The same column order, row order, and CSV formatting are used for
    every comparison.
    """

    csv_data = dataframe.to_csv(
        index=False,
        lineterminator="\n",
    )

    return csv_data.encode("utf-8")


def calculate_hash(
    dataframe: pd.DataFrame,
) -> str:
    """Calculate a SHA-256 hash of the generated dataset."""

    return hashlib.sha256(dataframe_to_bytes(dataframe)).hexdigest()


def datasets_equal(
    first: pd.DataFrame,
    second: pd.DataFrame,
) -> bool:
    """Compare two datasets for exact equality."""

    return first.equals(second)


def datasets_byte_equal(
    first: pd.DataFrame,
    second: pd.DataFrame,
) -> bool:
    """Compare deterministic CSV representations byte-for-byte."""

    return dataframe_to_bytes(first) == dataframe_to_bytes(second)


# --------------------------------------------------
# Validation
# --------------------------------------------------


def validate_dataset(
    dataframe: pd.DataFrame,
    specification: dict,
) -> None:
    """
    Validate the generated dataset against the declared constraints.

    The validation intentionally focuses on the structural constraints
    needed for this experiment.
    """

    generation = specification["generation"]

    expected_record_count = generation["record_count"]

    if len(dataframe) != expected_record_count:
        raise AssertionError("Generated record count does not match specification.")

    entities = specification["entities"]

    entity_name = next(iter(entities))

    fields = entities[entity_name]["fields"]

    for (
        field_name,
        field_metadata,
    ) in fields.items():

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

            for value in non_null:

                generated = str(value)

                if len(generated) != len(pattern):
                    raise AssertionError(
                        f"Pattern length violation " f"for {field_name}."
                    )

                for (
                    generated_character,
                    pattern_character,
                ) in zip(
                    generated,
                    pattern,
                ):

                    if pattern_character == "#":

                        assert generated_character.isdigit()

                    elif pattern_character == "A":

                        assert (
                            generated_character.isalpha()
                            and generated_character.isupper()
                        )

                    else:

                        assert generated_character == pattern_character

        elif field_type == "string":

            minimum = field_metadata["min_length"]

            maximum = field_metadata["max_length"]

            assert all(minimum <= len(str(value)) <= maximum for value in non_null)

        else:

            raise ValueError(f"Unsupported validation type: {field_type}")


# --------------------------------------------------
# Output
# --------------------------------------------------


def save_dataset(
    dataframe: pd.DataFrame,
    filename: str,
) -> Path:
    """Save a generated dataset."""

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    output_file = OUTPUT_DIR / filename

    dataframe.to_csv(
        output_file,
        index=False,
    )

    return output_file


def save_results(
    results: dict,
) -> Path:
    """Save reproducibility results."""

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    with RESULTS_FILE.open(
        "w",
        encoding="utf-8",
    ) as file:

        json.dump(
            results,
            file,
            indent=2,
        )

    return RESULTS_FILE


# --------------------------------------------------
# Generation execution
# --------------------------------------------------


def generate_with_seed(
    specification: dict,
    seed: int,
) -> pd.DataFrame:
    """
    Generate a dataset after explicitly resetting the global
    random state.

    Resetting the random state is intentional for this experiment.
    It allows repeated executions to start from exactly the same
    random state.
    """

    random.seed(seed)

    return generate_dataset(specification)


# --------------------------------------------------
# Experiment execution
# --------------------------------------------------


def main() -> None:
    """Run Experiment 007."""

    specification = load_specification()

    seed_a = specification["generation"]["seed"]

    different_seed = specification["generation"].get(
        "different_seed",
        99,
    )

    repeat_count = specification["generation"].get(
        "repeat_count",
        3,
    )

    print("=" * 70)
    print("FORGE - Experiment 007: " "Reproducible Generation")
    print("=" * 70)

    print(f"Specification: {SPECIFICATION_FILE}")

    print(f"Primary seed:  {seed_a}")

    print(f"Other seed:    {different_seed}")

    print(f"Repeat count:  {repeat_count}")

    # --------------------------------------------------
    # Test 1: Same seed
    # --------------------------------------------------

    print("\nTest 1: Same seed")

    datasets_same_seed = []

    for run_number in range(
        1,
        repeat_count + 1,
    ):

        dataframe = generate_with_seed(
            specification=specification,
            seed=seed_a,
        )

        validate_dataset(
            dataframe=dataframe,
            specification=specification,
        )

        datasets_same_seed.append(dataframe)

        filename = f"dataset_seed_" f"{seed_a}_run_" f"{run_number}.csv"

        output_file = save_dataset(
            dataframe=dataframe,
            filename=filename,
        )

        print(f"  Run {run_number}: " f"{output_file}")

    first_dataset = datasets_same_seed[0]

    same_seed_results = []

    for index in range(
        1,
        len(datasets_same_seed),
    ):

        current_dataset = datasets_same_seed[index]

        same_seed_results.append(
            {
                "run_a": 1,
                "run_b": index + 1,
                "dataset_identical": datasets_equal(
                    first_dataset,
                    current_dataset,
                ),
                "byte_identical": datasets_byte_equal(
                    first_dataset,
                    current_dataset,
                ),
                "hash_a": calculate_hash(first_dataset),
                "hash_b": calculate_hash(current_dataset),
            }
        )

    same_seed_pass = all(
        result["dataset_identical"] and result["byte_identical"]
        for result in same_seed_results
    )

    print(f"  Dataset equality: " f"{'PASS' if same_seed_pass else 'FAIL'}")

    print(f"  Byte equality:    " f"{'PASS' if same_seed_pass else 'FAIL'}")

    # --------------------------------------------------
    # Test 2: Different seed
    # --------------------------------------------------

    print("\nTest 2: Different seed")

    different_seed_dataset = generate_with_seed(
        specification=specification,
        seed=different_seed,
    )

    validate_dataset(
        dataframe=different_seed_dataset,
        specification=specification,
    )

    different_seed_file = save_dataset(
        dataframe=different_seed_dataset,
        filename=(f"dataset_seed_" f"{different_seed}.csv"),
    )

    different_seed_identical = datasets_equal(
        first_dataset,
        different_seed_dataset,
    )

    different_seed_byte_identical = datasets_byte_equal(
        first_dataset,
        different_seed_dataset,
    )

    different_seed_pass = (
        not different_seed_identical and not different_seed_byte_identical
    )

    print(
        f"  Dataset equality: " f"{'PASS' if not different_seed_identical else 'FAIL'}"
    )

    print(
        f"  Byte equality:    "
        f"{'PASS' if not different_seed_byte_identical else 'FAIL'}"
    )

    print(f"  Output:           " f"{different_seed_file}")

    # --------------------------------------------------
    # Results
    # --------------------------------------------------

    results = {
        "experiment": 7,
        "primary_seed": seed_a,
        "different_seed": different_seed,
        "repeat_count": repeat_count,
        "same_seed": {
            "tests": same_seed_results,
            "passed": same_seed_pass,
        },
        "different_seed": {
            "datasets_identical": (different_seed_identical),
            "byte_identical": (different_seed_byte_identical),
            "passed": different_seed_pass,
        },
        "dataset_hash": {
            "primary": calculate_hash(first_dataset),
            "different_seed": calculate_hash(different_seed_dataset),
        },
        "overall_result": (
            "PASS" if same_seed_pass and different_seed_pass else "FAIL"
        ),
    }

    results_file = save_results(results)

    # --------------------------------------------------
    # Output summary
    # --------------------------------------------------

    print("\nReproducibility summary:")

    print(f"  Same seed:       " f"{'PASS' if same_seed_pass else 'FAIL'}")

    print(f"  Different seed:  " f"{'PASS' if different_seed_pass else 'FAIL'}")

    print(f"  Overall result:  " f"{results['overall_result']}")

    print(f"\nResults:")

    print(f"  {results_file}")

    print("\nFirst 10 records:")

    print(first_dataset.head(10).to_string(index=False))

    print("\nExperiment completed successfully.")


# --------------------------------------------------
# Entry point
# --------------------------------------------------

if __name__ == "__main__":
    main()
