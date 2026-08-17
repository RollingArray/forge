"""
FORGE - Experiment 006: Distribution-Derived Relationship Allocation
=====================================================================

Purpose
-------
This experiment tests whether relationship allocation can be derived
automatically from a declared statistical distribution without
requiring explicit weights for individual parent records.

The experiment builds on the capabilities established in:

    Experiment 001 - Metadata-Only Generation
    Experiment 002 - Field Constraints
    Experiment 003 - Distribution-Controlled Generation
    Experiment 004 - Relationship-Aware Generation
    Experiment 005 - Relationship Distribution

The key difference from Experiment 005 is that individual parent
weights are NOT supplied in the specification.

Instead, the specification declares a distribution such as:

    power_law(alpha=1.5)

FORGE derives the parent-level allocation from that distribution.

No machine learning, deep learning, LLM, or real production data
is used.

Experiment
----------
006 - Distribution-Derived Relationship Allocation

Key Question
------------
Can relationship allocation be derived from statistical intent rather
than explicit parent-level weights?

Author
------
Ranjoy Sen

Status
------
Experimental

How to Run
----------
From the repository root:

    uv run python experiments/006_distribution_derived_relationship/experiment.py

Output
------
The generated datasets are written to:

    experiments/006_distribution_derived_relationship/output/CUSTOMER.csv
    experiments/006_distribution_derived_relationship/output/ORDER.csv

Relationship statistics are written to:

    experiments/006_distribution_derived_relationship/output/relationship_statistics.json

Important
---------
The generated data is synthetic and does not represent any real
production dataset.
"""

from collections import Counter
from pathlib import Path
import json
import math
import random
import statistics

import pandas as pd

# --------------------------------------------------
# Experiment paths
# --------------------------------------------------

EXPERIMENT_DIR = Path(__file__).resolve().parent
SPECIFICATION_FILE = EXPERIMENT_DIR / "specification.json"
OUTPUT_DIR = EXPERIMENT_DIR / "output"

RELATIONSHIP_STATISTICS_FILE = OUTPUT_DIR / "relationship_statistics.json"


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
    """Generate a categorical value using the declared distribution."""

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
            raise ValueError("Weighted categorical distribution requires weights.")

        if len(weights) != len(values):
            raise ValueError("Number of weights must match number of values.")

        return random.choices(
            values,
            weights=weights,
            k=1,
        )[0]

    raise ValueError(f"Unsupported categorical distribution: {distribution_type}")


def generate_integer(
    minimum: int,
    maximum: int,
    distribution: dict | None,
) -> int:
    """Generate an integer using the declared distribution."""

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

    raise ValueError(f"Unsupported integer distribution: {distribution_type}")


def generate_field_value(
    field_metadata: dict,
    index: int,
):
    """Generate a value from a field specification."""

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

    if field_type == "reference":
        return None

    raise ValueError(f"Unsupported field type: {field_type}")


# --------------------------------------------------
# Entity generation
# --------------------------------------------------


def generate_entity(
    entity_name: str,
    entity_metadata: dict,
) -> pd.DataFrame:
    """Generate an entity from its specification."""

    record_count = entity_metadata["record_count"]

    rows = []

    for index in range(
        1,
        record_count + 1,
    ):

        row = {}

        for field_name, field_metadata in entity_metadata["fields"].items():

            field_type = field_metadata["type"]

            if field_type == "reference":
                row[field_name] = None
                continue

            row[field_name] = generate_field_value(
                field_metadata=field_metadata,
                index=index,
            )

        rows.append(row)

    dataframe = pd.DataFrame(rows)

    print(f"Generated {record_count:4d} records for {entity_name}")

    return dataframe


# --------------------------------------------------
# Relationship distributions
# --------------------------------------------------


def derive_uniform_weights(
    parent_count: int,
) -> list[float]:
    """
    Derive equal allocation probability for every parent.
    """

    if parent_count <= 0:
        raise ValueError("Parent count must be greater than zero.")

    weight = 1.0 / parent_count

    return [weight] * parent_count


def derive_power_law_weights(
    parent_count: int,
    alpha: float,
) -> list[float]:
    """
    Derive normalized power-law weights from parent rank.

    Rank 1 receives the highest probability.

    Weight(rank) = 1 / rank^alpha

    The resulting weights are normalized so that their sum is 1.
    """

    if parent_count <= 0:
        raise ValueError("Parent count must be greater than zero.")

    if alpha <= 0:
        raise ValueError("Power-law alpha must be greater than zero.")

    raw_weights = [
        1.0
        / math.pow(
            rank,
            alpha,
        )
        for rank in range(
            1,
            parent_count + 1,
        )
    ]

    total = sum(raw_weights)

    return [weight / total for weight in raw_weights]


def derive_relationship_weights(
    parent_count: int,
    distribution: dict,
) -> list[float]:
    """Derive parent allocation weights from distribution intent."""

    distribution_type = distribution["type"]

    parameters = distribution.get(
        "parameters",
        {},
    )

    if distribution_type == "uniform":

        return derive_uniform_weights(
            parent_count=parent_count,
        )

    if distribution_type == "power_law":

        alpha = parameters.get(
            "alpha",
            1.0,
        )

        return derive_power_law_weights(
            parent_count=parent_count,
            alpha=alpha,
        )

    raise ValueError(f"Unsupported relationship distribution: " f"{distribution_type}")


# --------------------------------------------------
# Relationship generation
# --------------------------------------------------


def generate_relationship(
    parent_dataframe: pd.DataFrame,
    child_dataframe: pd.DataFrame,
    relationship: dict,
) -> tuple[pd.DataFrame, list[float]]:
    """
    Generate child-to-parent references using derived weights.
    """

    parent_field = relationship["parent_field"]
    child_field = relationship["child_field"]

    distribution = relationship["distribution"]

    parent_values = parent_dataframe[parent_field].tolist()

    weights = derive_relationship_weights(
        parent_count=len(parent_values),
        distribution=distribution,
    )

    selected_parents = random.choices(
        parent_values,
        weights=weights,
        k=len(child_dataframe),
    )

    child_dataframe = child_dataframe.copy()

    child_dataframe[child_field] = selected_parents

    return (
        child_dataframe,
        weights,
    )


# --------------------------------------------------
# Relationship validation
# --------------------------------------------------


def validate_referential_integrity(
    parent_dataframe: pd.DataFrame,
    child_dataframe: pd.DataFrame,
    relationship: dict,
) -> int:
    """Return the number of invalid child references."""

    parent_field = relationship["parent_field"]
    child_field = relationship["child_field"]

    parent_values = set(parent_dataframe[parent_field])

    invalid_references = [
        value for value in child_dataframe[child_field] if value not in parent_values
    ]

    return len(invalid_references)


def validate_cardinality(
    parent_dataframe: pd.DataFrame,
    child_dataframe: pd.DataFrame,
    relationship: dict,
) -> None:
    """Validate the configured relationship cardinality."""

    cardinality = relationship["cardinality"]

    if cardinality != "1:N":
        raise ValueError(
            f"Experiment 006 supports 1:N only. " f"Received: {cardinality}"
        )

    parent_field = relationship["parent_field"]
    child_field = relationship["child_field"]

    parent_count = len(parent_dataframe)
    child_count = len(child_dataframe)

    if parent_count <= 0:
        raise ValueError("1:N relationship requires at least one parent.")

    if child_count < 0:
        raise ValueError("Child record count cannot be negative.")

    if parent_field not in parent_dataframe.columns:
        raise ValueError(f"Parent field not found: {parent_field}")

    if child_field not in child_dataframe.columns:
        raise ValueError(f"Child field not found: {child_field}")


# --------------------------------------------------
# Distribution validation
# --------------------------------------------------


def calculate_relationship_statistics(
    parent_dataframe: pd.DataFrame,
    child_dataframe: pd.DataFrame,
    relationship: dict,
    weights: list[float],
) -> dict:
    """Calculate derived and observed relationship statistics."""

    parent_field = relationship["parent_field"]
    child_field = relationship["child_field"]

    parent_values = parent_dataframe[parent_field].tolist()

    counts = Counter(child_dataframe[child_field])

    total_children = len(child_dataframe)

    allocation = []

    for rank, (
        parent_value,
        weight,
    ) in enumerate(
        zip(
            parent_values,
            weights,
        ),
        start=1,
    ):

        child_count = counts.get(
            parent_value,
            0,
        )

        if total_children > 0:
            observed_rate = child_count / total_children
        else:
            observed_rate = 0.0

        allocation.append(
            {
                "rank": rank,
                "parent": parent_value,
                "derived_weight": weight,
                "child_count": child_count,
                "observed_rate": observed_rate,
            }
        )

    child_counts = [item["child_count"] for item in allocation]

    if child_counts:

        minimum = min(child_counts)

        maximum = max(child_counts)

        mean = statistics.mean(child_counts)

        median = statistics.median(child_counts)

        zero_children = sum(count == 0 for count in child_counts)

    else:

        minimum = 0
        maximum = 0
        mean = 0
        median = 0
        zero_children = 0

    distribution = relationship["distribution"]

    return {
        "distribution": distribution,
        "parent_record_count": len(parent_dataframe),
        "child_record_count": len(child_dataframe),
        "minimum_children_per_parent": minimum,
        "maximum_children_per_parent": maximum,
        "mean_children_per_parent": mean,
        "median_children_per_parent": median,
        "parents_with_zero_children": zero_children,
        "allocation": allocation,
    }


def validate_distribution_shape(
    statistics_data: dict,
) -> None:
    """Print the derived and observed relationship distribution."""

    print("\nRelationship distribution:")

    allocation = statistics_data["allocation"]

    for item in allocation:

        print(
            f"  {item['parent']}: "
            f"observed={item['observed_rate']:.2%}, "
            f"derived={item['derived_weight']:.2%}"
        )


# --------------------------------------------------
# Output
# --------------------------------------------------


def save_entity(
    dataframe: pd.DataFrame,
    entity_name: str,
) -> Path:
    """Save an entity dataset."""

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    output_file = OUTPUT_DIR / f"{entity_name}.csv"

    dataframe.to_csv(
        output_file,
        index=False,
    )

    return output_file


def save_relationship_statistics(
    statistics_data: dict,
) -> Path:
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
            statistics_data,
            file,
            indent=2,
        )

    return RELATIONSHIP_STATISTICS_FILE


# --------------------------------------------------
# Experiment execution
# --------------------------------------------------


def main() -> None:
    """Run Experiment 006."""

    specification = load_specification()

    seed = specification["generation"]["seed"]

    random.seed(seed)

    print("=" * 70)
    print("FORGE - Experiment 006: " "Distribution-Derived Relationship Allocation")
    print("=" * 70)

    print(f"Specification: {SPECIFICATION_FILE}")

    print(f"Random seed:   {seed}")

    # --------------------------------------------------
    # Generate entities
    # --------------------------------------------------

    entities = {}

    for (
        entity_name,
        entity_metadata,
    ) in specification["entities"].items():

        entities[entity_name] = generate_entity(
            entity_name=entity_name,
            entity_metadata=entity_metadata,
        )

    # --------------------------------------------------
    # Generate relationships
    # --------------------------------------------------

    print("\nGenerating relationships...")

    relationship_statistics = []

    for relationship in specification["relationships"]:

        parent_entity = relationship["parent_entity"]

        child_entity = relationship["child_entity"]

        parent_dataframe = entities[parent_entity]

        child_dataframe = entities[child_entity]

        (
            child_dataframe,
            weights,
        ) = generate_relationship(
            parent_dataframe=parent_dataframe,
            child_dataframe=child_dataframe,
            relationship=relationship,
        )

        entities[child_entity] = child_dataframe

        invalid_references = validate_referential_integrity(
            parent_dataframe=parent_dataframe,
            child_dataframe=child_dataframe,
            relationship=relationship,
        )

        validate_cardinality(
            parent_dataframe=parent_dataframe,
            child_dataframe=child_dataframe,
            relationship=relationship,
        )

        statistics_data = calculate_relationship_statistics(
            parent_dataframe=parent_dataframe,
            child_dataframe=child_dataframe,
            relationship=relationship,
            weights=weights,
        )

        statistics_data["parent_entity"] = parent_entity

        statistics_data["child_entity"] = child_entity

        statistics_data["parent_field"] = relationship["parent_field"]

        statistics_data["child_field"] = relationship["child_field"]

        statistics_data["cardinality"] = relationship["cardinality"]

        statistics_data["invalid_references"] = invalid_references

        relationship_statistics.append(statistics_data)

        print("\nRelationship validation:")

        print(f"  {parent_entity}." f"{relationship['parent_field']}")

        print(f"      -> " f"{child_entity}." f"{relationship['child_field']}")

        print(f"  Cardinality: " f"{relationship['cardinality']}")

        print(f"  Parent records: " f"{len(parent_dataframe)}")

        print(f"  Child records: " f"{len(child_dataframe)}")

        print(f"  Invalid references: " f"{invalid_references}")

        result = "PASS" if invalid_references == 0 else "FAIL"

        print(f"  Result: {result}")

        validate_distribution_shape(statistics_data)

    # --------------------------------------------------
    # Save output
    # --------------------------------------------------

    output_files = []

    for (
        entity_name,
        dataframe,
    ) in entities.items():

        output_files.append(
            save_entity(
                dataframe=dataframe,
                entity_name=entity_name,
            )
        )

    statistics_output = {
        "experiment": 6,
        "distribution_intent": specification["relationships"],
        "relationships": relationship_statistics,
    }

    output_files.append(save_relationship_statistics(statistics_data=statistics_output))

    print("\nOutput:")

    for output_file in output_files:
        print(f"  {output_file}")

    # --------------------------------------------------
    # Preview
    # --------------------------------------------------

    for (
        entity_name,
        dataframe,
    ) in entities.items():

        print(f"\nFirst records: " f"{entity_name}")

        print(dataframe.head(10).to_string(index=False))

    print("\nExperiment completed successfully.")


# --------------------------------------------------
# Entry point
# --------------------------------------------------

if __name__ == "__main__":
    main()
