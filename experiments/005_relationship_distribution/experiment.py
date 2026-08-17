"""
FORGE - Experiment 005: Relationship Distribution
===================================================

Purpose
-------
This experiment tests whether synthetic data can maintain valid
parent-child relationships while controlling the statistical
distribution of child records across parent records.

The experiment builds directly on:

    Experiment 001
        Metadata-only generation

    Experiment 002
        Field constraints

    Experiment 003
        Distribution-controlled generation

    Experiment 004
        Relationship-aware generation

The experiment introduces:

    - relationship-level distributions
    - uniform child allocation
    - weighted child allocation
    - relationship distribution validation
    - referential integrity validation
    - relationship statistics

No machine learning, LLM, or real production data is used.

The objective is to determine whether relationship allocation can
be treated as an explicit generation characteristic.

Experiment
----------
005 - Relationship Distribution

Key Question
------------
Can synthetic data maintain referential integrity while also
following an explicitly declared statistical distribution for
child records across parent records?

Author
------
Ranjoy Sen

Status
------
Experimental

How to Run
----------
From the repository root:

    uv run python experiments/005_relationship_distribution/experiment.py

Output
------
Generated datasets are written to:

    experiments/005_relationship_distribution/output/CUSTOMER.csv
    experiments/005_relationship_distribution/output/ORDER.csv

Relationship statistics are written to:

    experiments/005_relationship_distribution/output/relationship_statistics.json

Important
---------
The generated data is synthetic and does not represent any real
production dataset.
"""

from __future__ import annotations

import json
import random
from collections import Counter
from pathlib import Path

import pandas as pd

# --------------------------------------------------
# Experiment paths
# --------------------------------------------------

EXPERIMENT_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = EXPERIMENT_DIR / "output"

SPECIFICATION_FILE = EXPERIMENT_DIR / "specification.json"

RELATIONSHIP_STATISTICS_FILE = OUTPUT_DIR / "relationship_statistics.json"


# --------------------------------------------------
# Specification handling
# --------------------------------------------------


def load_specification() -> dict:
    """
    Load the experiment specification.

    The specification is intentionally kept outside the generation
    code so that generation behavior can be changed without
    modifying the experiment implementation.
    """

    with SPECIFICATION_FILE.open(
        "r",
        encoding="utf-8",
    ) as file:
        return json.load(file)


# --------------------------------------------------
# Field generators
# --------------------------------------------------


def generate_identifier(
    prefix: str,
    length: int,
    index: int,
) -> str:
    """
    Generate a prefixed fixed-width identifier.

    Example:

        prefix = CUS
        length = 7

        CUS0000001
    """

    numeric_width = length

    return f"{prefix}{index:0{numeric_width}d}"


def generate_categorical(
    field_metadata: dict,
) -> str:
    """
    Generate a categorical value.

    Supports:

        - uniform distribution
        - weighted distribution
    """

    values = field_metadata["values"]

    distribution = field_metadata.get(
        "distribution",
        {},
    )

    distribution_type = distribution.get(
        "type",
        "uniform",
    )

    if distribution_type == "uniform":
        return random.choice(values)

    if distribution_type == "weighted":

        weights = distribution["weights"]

        return random.choices(
            values,
            weights=weights,
            k=1,
        )[0]

    raise ValueError(f"Unsupported categorical distribution: " f"{distribution_type}")


def generate_integer(
    field_metadata: dict,
) -> int:
    """
    Generate an integer according to the declared distribution.

    Experiment 005 currently supports a uniform bounded
    distribution. More distribution types can be added in
    subsequent experiments.
    """

    minimum = field_metadata["min"]
    maximum = field_metadata["max"]

    distribution = field_metadata.get(
        "distribution",
        {},
    )

    distribution_type = distribution.get(
        "type",
        "uniform",
    )

    if distribution_type == "uniform":

        return random.randint(
            minimum,
            maximum,
        )

    raise ValueError(f"Unsupported integer distribution: " f"{distribution_type}")


# --------------------------------------------------
# Field generation
# --------------------------------------------------


def generate_field_value(
    field_name: str,
    field_metadata: dict,
    index: int,
):
    """
    Generate a field value from its metadata.

    Reference fields are intentionally not generated here.

    They are populated later by the relationship-generation stage.
    """

    field_type = field_metadata["type"]

    if field_type == "identifier":

        return generate_identifier(
            prefix=field_metadata.get(
                "prefix",
                "",
            ),
            length=field_metadata["length"],
            index=index,
        )

    if field_type == "categorical":

        return generate_categorical(
            field_metadata,
        )

    if field_type == "integer":

        return generate_integer(
            field_metadata,
        )

    if field_type == "reference":

        return None

    raise ValueError(f"Unsupported field type for " f"{field_name}: {field_type}")


# --------------------------------------------------
# Entity generation
# --------------------------------------------------


def generate_entity(
    entity_name: str,
    entity_metadata: dict,
) -> list[dict]:
    """
    Generate an entity from its specification.

    Relationship fields are not populated during this stage.
    """

    record_count = entity_metadata["record_count"]
    fields = entity_metadata["fields"]

    records = []

    for index in range(
        1,
        record_count + 1,
    ):

        record = {}

        for field_name, field_metadata in fields.items():

            if field_metadata["type"] == "reference":
                continue

            record[field_name] = generate_field_value(
                field_name=field_name,
                field_metadata=field_metadata,
                index=index,
            )

        records.append(record)

    return records


# --------------------------------------------------
# Relationship distribution
# --------------------------------------------------


def normalize_weights(
    parent_values: list[str],
    weights: dict[str, float],
) -> list[float]:
    """
    Convert parent-specific weights into an ordered list.

    The order follows the generated parent records.
    """

    ordered_weights = []

    for parent_value in parent_values:

        if parent_value not in weights:
            raise ValueError(
                "Relationship distribution does not "
                f"contain a weight for parent "
                f"{parent_value}"
            )

        ordered_weights.append(weights[parent_value])

    total = sum(ordered_weights)

    if total <= 0:
        raise ValueError("Relationship weights must have " "a positive total.")

    return ordered_weights


def allocate_uniform(
    parent_values: list[str],
    child_count: int,
) -> list[str]:
    """
    Allocate child records uniformly across parents.

    Every child receives a randomly selected parent with equal
    probability.
    """

    return random.choices(
        parent_values,
        k=child_count,
    )


def allocate_weighted(
    parent_values: list[str],
    child_count: int,
    weights: dict[str, float],
) -> list[str]:
    """
    Allocate child records according to explicit parent weights.
    """

    ordered_weights = normalize_weights(
        parent_values=parent_values,
        weights=weights,
    )

    return random.choices(
        parent_values,
        weights=ordered_weights,
        k=child_count,
    )


def generate_relationship(
    relationship: dict,
    parent_records: list[dict],
    child_records: list[dict],
) -> None:
    """
    Populate the child reference field according to the declared
    relationship distribution.
    """

    parent_field = relationship["parent_field"]
    child_field = relationship["child_field"]

    parent_values = [record[parent_field] for record in parent_records]

    distribution = relationship.get(
        "distribution",
        {},
    )

    distribution_type = distribution.get(
        "type",
        "uniform",
    )

    child_count = len(child_records)

    if distribution_type == "uniform":

        allocated_values = allocate_uniform(
            parent_values=parent_values,
            child_count=child_count,
        )

    elif distribution_type == "weighted":

        allocated_values = allocate_weighted(
            parent_values=parent_values,
            child_count=child_count,
            weights=distribution["weights"],
        )

    else:

        raise ValueError(
            "Unsupported relationship distribution: " f"{distribution_type}"
        )

    for record, parent_value in zip(
        child_records,
        allocated_values,
    ):

        record[child_field] = parent_value


# --------------------------------------------------
# Relationship validation
# --------------------------------------------------


def validate_referential_integrity(
    relationship: dict,
    parent_records: list[dict],
    child_records: list[dict],
) -> int:
    """
    Validate that every child reference points to an existing parent.

    Returns the number of invalid references.
    """

    parent_field = relationship["parent_field"]
    child_field = relationship["child_field"]

    parent_values = {record[parent_field] for record in parent_records}

    invalid_references = 0

    for record in child_records:

        child_value = record.get(child_field)

        if child_value not in parent_values:
            invalid_references += 1

    return invalid_references


# --------------------------------------------------
# Relationship statistics
# --------------------------------------------------


def calculate_relationship_statistics(
    relationship: dict,
    parent_records: list[dict],
    child_records: list[dict],
) -> dict:
    """
    Calculate observed child-record distribution across parents.
    """

    parent_field = relationship["parent_field"]
    child_field = relationship["child_field"]

    parent_values = [record[parent_field] for record in parent_records]

    child_counts = Counter(record[child_field] for record in child_records)

    counts = {
        parent_value: child_counts.get(
            parent_value,
            0,
        )
        for parent_value in parent_values
    }

    total_children = len(child_records)
    total_parents = len(parent_records)

    minimum = min(counts.values())
    maximum = max(counts.values())

    mean = total_children / total_parents if total_parents else 0

    observed_distribution = {}

    for parent_value, count in counts.items():

        if total_children:

            observed_distribution[parent_value] = count / total_children

        else:

            observed_distribution[parent_value] = 0.0

    return {
        "parent_entity": relationship["parent_entity"],
        "parent_field": parent_field,
        "child_entity": relationship["child_entity"],
        "child_field": child_field,
        "cardinality": relationship["cardinality"],
        "distribution_type": relationship.get(
            "distribution",
            {},
        ).get(
            "type",
            "uniform",
        ),
        "parent_record_count": total_parents,
        "child_record_count": total_children,
        "minimum_children_per_parent": minimum,
        "maximum_children_per_parent": maximum,
        "mean_children_per_parent": mean,
        "parents_with_zero_children": sum(1 for count in counts.values() if count == 0),
        "observed_child_counts": counts,
        "observed_distribution": observed_distribution,
    }


# --------------------------------------------------
# Distribution validation
# --------------------------------------------------


def validate_relationship_distribution(
    relationship: dict,
    statistics: dict,
) -> None:
    """
    Compare the observed relationship distribution against
    the declared distribution.
    """

    distribution = relationship.get(
        "distribution",
        {},
    )

    distribution_type = distribution.get(
        "type",
        "uniform",
    )

    observed = statistics["observed_distribution"]

    print("\nRelationship distribution:")

    if distribution_type == "uniform":

        expected = 1.0 / len(observed) if observed else 0.0

        for parent, observed_rate in observed.items():

            print(
                f"  {parent}: "
                f"observed={observed_rate:.2%}, "
                f"expected={expected:.2%}"
            )

        return

    if distribution_type == "weighted":

        expected_weights = distribution["weights"]

        for parent, observed_rate in observed.items():

            expected = expected_weights[parent]

            print(
                f"  {parent}: "
                f"observed={observed_rate:.2%}, "
                f"expected={expected:.2%}"
            )

        return

    raise ValueError("Unsupported relationship distribution: " f"{distribution_type}")


# --------------------------------------------------
# Output
# --------------------------------------------------


def save_entity(
    entity_name: str,
    records: list[dict],
) -> Path:
    """Save an entity dataset as CSV."""

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    output_file = OUTPUT_DIR / f"{entity_name}.csv"

    dataframe = pd.DataFrame(records)

    dataframe.to_csv(
        output_file,
        index=False,
    )

    return output_file


def save_relationship_statistics(
    statistics: dict,
) -> None:
    """Save relationship statistics as JSON."""

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    with RELATIONSHIP_STATISTICS_FILE.open(
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
    """Run Experiment 005."""

    specification = load_specification()

    seed = specification["generation"]["seed"]

    random.seed(seed)

    print("=" * 70)
    print("FORGE - Experiment 005: " "Relationship Distribution")
    print("=" * 70)

    print(f"Specification: {SPECIFICATION_FILE}")

    print(f"Random seed:   {seed}")

    # --------------------------------------------------
    # Generate entities
    # --------------------------------------------------

    entities: dict[str, list[dict]] = {}

    for entity_name, entity_metadata in specification["entities"].items():

        records = generate_entity(
            entity_name=entity_name,
            entity_metadata=entity_metadata,
        )

        entities[entity_name] = records

        print(f"Generated " f"{len(records):4d} records for " f"{entity_name}")

    # --------------------------------------------------
    # Generate relationships
    # --------------------------------------------------

    print("\nGenerating relationships...")

    relationship_statistics = []

    for relationship in specification["relationships"]:

        parent_entity = relationship["parent_entity"]

        child_entity = relationship["child_entity"]

        parent_records = entities[parent_entity]

        child_records = entities[child_entity]

        generate_relationship(
            relationship=relationship,
            parent_records=parent_records,
            child_records=child_records,
        )

        # --------------------------------------------------
        # Validate referential integrity
        # --------------------------------------------------

        invalid_references = validate_referential_integrity(
            relationship=relationship,
            parent_records=parent_records,
            child_records=child_records,
        )

        # --------------------------------------------------
        # Calculate relationship statistics
        # --------------------------------------------------

        statistics = calculate_relationship_statistics(
            relationship=relationship,
            parent_records=parent_records,
            child_records=child_records,
        )

        statistics["invalid_references"] = invalid_references

        relationship_statistics.append(statistics)

        print("\nRelationship validation:")

        print(f"  " f"{parent_entity}." f"{relationship['parent_field']}")

        print("      -> " f"{child_entity}." f"{relationship['child_field']}")

        print(f"  Cardinality: " f"{relationship['cardinality']}")

        print(f"  Parent records: " f"{len(parent_records)}")

        print(f"  Child records: " f"{len(child_records)}")

        print(f"  Invalid references: " f"{invalid_references}")

        result = "PASS" if invalid_references == 0 else "FAIL"

        print(f"  Result: {result}")

        validate_relationship_distribution(
            relationship=relationship,
            statistics=statistics,
        )

    # --------------------------------------------------
    # Save outputs
    # --------------------------------------------------

    output_files = []

    for entity_name, records in entities.items():

        output_files.append(
            save_entity(
                entity_name=entity_name,
                records=records,
            )
        )

    relationship_output = {
        "experiment": "005",
        "name": "Relationship Distribution",
        "seed": seed,
        "relationships": relationship_statistics,
    }

    save_relationship_statistics(relationship_output)

    # --------------------------------------------------
    # Display output
    # --------------------------------------------------

    print("\nOutput:")

    for output_file in output_files:

        print(f"  {output_file}")

    print(f"  {RELATIONSHIP_STATISTICS_FILE}")

    for entity_name, records in entities.items():

        dataframe = pd.DataFrame(records)

        print(f"\nFirst records: " f"{entity_name}")

        print(dataframe.head(10).to_string(index=False))

    print("\nExperiment completed successfully.")


# --------------------------------------------------
# Entry point
# --------------------------------------------------

if __name__ == "__main__":
    main()
