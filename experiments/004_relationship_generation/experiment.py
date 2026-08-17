"""
FORGE - Experiment 004: Relationship-Aware Generation
======================================================

Purpose
-------
This experiment tests whether synthetic datasets can preserve
relationships between entities when the relationships themselves
are explicitly defined in metadata.

The experiment builds directly on the capabilities established
in Experiments 001, 002 and 003.

Experiment 003 established:

    - metadata-driven generation
    - field constraints
    - categorical distributions
    - numeric distributions
    - population rates
    - deterministic generation

Experiment 004 adds:

    - multiple entities
    - parent-child relationships
    - reference fields
    - foreign-key generation
    - cardinality validation

No machine learning, deep learning, LLM, or real production data
is used.

Experiment
----------
004 - Relationship-Aware Generation

Key Question
------------
Can valid relationships between synthetic entities be generated
from explicit relationship metadata rather than learned from
real data?

Author
------
Ranjoy Sen

Status
------
Experimental

How to Run
----------
From the repository root:

    uv run python experiments/004_relationship_generation/experiment.py

Input
-----
The experiment specification is read from:

    experiments/004_relationship_generation/specification.json

Output
------
Generated datasets are written to:

    experiments/004_relationship_generation/output/

The following files are produced:

    CUSTOMER.csv
    ORDER.csv

Important
---------
The generated data is synthetic and does not represent any real
production dataset.
"""

from pathlib import Path
import json
import random

import pandas as pd

# --------------------------------------------------
# Experiment paths
# --------------------------------------------------

EXPERIMENT_DIR = Path(__file__).resolve().parent

SPECIFICATION_FILE = EXPERIMENT_DIR / "specification.json"

OUTPUT_DIR = EXPERIMENT_DIR / "output"


# --------------------------------------------------
# Specification loading
# --------------------------------------------------


def load_specification() -> dict:
    """
    Load the experiment specification.

    The specification is the source of truth for:

        - entities
        - fields
        - field generation
        - relationships
        - cardinality
        - record volume
        - random seed
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
    length: int,
    index: int,
    prefix: str = "",
) -> str:
    """Generate a fixed-width identifier with an optional prefix."""

    numeric_length = length - len(prefix)

    if numeric_length <= 0:
        raise ValueError("Identifier length must be greater than prefix length.")

    return f"{prefix}{str(index).zfill(numeric_length)}"


def generate_uniform(
    values: list[str],
) -> str:
    """Generate a value using a uniform distribution."""

    return random.choice(values)


def generate_integer(
    minimum: int,
    maximum: int,
) -> int:
    """Generate an integer within the declared bounds."""

    return random.randint(
        minimum,
        maximum,
    )


def generate_categorical(
    field_metadata: dict,
) -> str:
    """
    Generate a categorical value according to the declared
    distribution.
    """

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

        weights = distribution["weights"]

        if len(values) != len(weights):
            raise ValueError(
                "Number of categorical values must match " "number of weights."
            )

        if abs(sum(weights) - 1.0) > 0.000001:
            raise ValueError("Weighted distribution weights must sum to 1.0.")

        return random.choices(
            values,
            weights=weights,
            k=1,
        )[0]

    raise ValueError("Unsupported categorical distribution: " f"{distribution_type}")


def generate_string(
    length: int,
) -> str:
    """Generate a synthetic alphanumeric string."""

    characters = "ABCDEFGHIJKLMNOPQRSTUVWXYZ" "abcdefghijklmnopqrstuvwxyz" "0123456789"

    return "".join(random.choice(characters) for _ in range(length))


# --------------------------------------------------
# Field generation
# --------------------------------------------------


def generate_field_value(
    field_metadata: dict,
    index: int,
):
    """
    Generate a field value using the same basic generation
    principles established in Experiment 003.

    Reference fields are intentionally excluded here.

    They are resolved later by the relationship engine.
    """

    field_type = field_metadata["type"]

    # --------------------------------------------------
    # Identifier
    # --------------------------------------------------

    if field_type == "identifier":

        return generate_identifier(
            length=field_metadata["length"],
            index=index,
            prefix=field_metadata.get("prefix", ""),
        )

    # --------------------------------------------------
    # Categorical
    # --------------------------------------------------

    if field_type == "categorical":

        return generate_categorical(
            field_metadata,
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

        if distribution_type == "uniform":

            return generate_integer(
                minimum=distribution["min"],
                maximum=distribution["max"],
            )

        raise ValueError("Unsupported integer distribution: " f"{distribution_type}")

    # --------------------------------------------------
    # String
    # --------------------------------------------------

    if field_type == "string":

        return generate_string(
            length=field_metadata["length"],
        )

    # --------------------------------------------------
    # Reference
    # --------------------------------------------------

    if field_type == "reference":

        # Reference values cannot be generated independently.
        #
        # They are populated by the relationship engine after
        # the parent entity has been generated.

        return None

    raise ValueError(f"Unsupported field type: {field_type}")


# --------------------------------------------------
# Entity generation
# --------------------------------------------------


def generate_entity(
    entity_name: str,
    entity_metadata: dict,
) -> list[dict]:
    """
    Generate an entity using its field metadata.

    Reference fields remain unresolved until relationships
    are processed.
    """

    records = []

    record_count = entity_metadata["record_count"]

    fields = entity_metadata["fields"]

    for index in range(
        1,
        record_count + 1,
    ):

        record = {}

        for field_name, field_metadata in fields.items():

            # Reference fields are populated later.
            if field_metadata["type"] == "reference":
                record[field_name] = None
                continue

            record[field_name] = generate_field_value(
                field_metadata=field_metadata,
                index=index,
            )

        records.append(record)

    print(f"Generated {record_count:4d} records " f"for {entity_name}")

    return records


# --------------------------------------------------
# Relationship generation
# --------------------------------------------------


def generate_one_to_many_relationship(
    parent_records: list[dict],
    parent_field: str,
    child_records: list[dict],
    child_field: str,
) -> None:
    """
    Generate a 1:N relationship.

    Every child receives a valid parent reference.

    Parent records may therefore have:

        - zero children
        - one child
        - multiple children

    The relationship is valid as long as every child reference
    points to an existing parent.
    """

    parent_values = [record[parent_field] for record in parent_records]

    if not parent_values:
        raise ValueError(
            "Cannot generate relationship because "
            "the parent entity contains no records."
        )

    for child_record in child_records:

        child_record[child_field] = random.choice(parent_values)


def generate_relationship(
    relationship: dict,
    entities: dict[str, list[dict]],
) -> None:
    """
    Generate a relationship defined in the specification.
    """

    parent_entity = relationship["parent_entity"]

    child_entity = relationship["child_entity"]

    parent_records = entities[parent_entity]

    child_records = entities[child_entity]

    cardinality = relationship["cardinality"]

    if cardinality == "1:N":

        generate_one_to_many_relationship(
            parent_records=parent_records,
            parent_field=relationship["parent_field"],
            child_records=child_records,
            child_field=relationship["child_field"],
        )

        return

    raise ValueError("Unsupported relationship cardinality: " f"{cardinality}")


# --------------------------------------------------
# Relationship validation
# --------------------------------------------------


def validate_relationship(
    relationship: dict,
    entities: dict[str, list[dict]],
) -> None:
    """
    Validate that every child reference points to an
    existing parent record.
    """

    parent_records = entities[relationship["parent_entity"]]

    child_records = entities[relationship["child_entity"]]

    parent_field = relationship["parent_field"]

    child_field = relationship["child_field"]

    parent_values = {record[parent_field] for record in parent_records}

    invalid_references = [
        record[child_field]
        for record in child_records
        if record[child_field] not in parent_values
    ]

    if invalid_references:

        raise ValueError(
            f"Relationship validation failed. "
            f"Found {len(invalid_references)} "
            f"invalid references."
        )

    print("\nRelationship validation:")

    print(f"  {relationship['parent_entity']}." f"{parent_field}")

    print(f"      -> " f"{relationship['child_entity']}." f"{child_field}")

    print(f"  Cardinality: " f"{relationship['cardinality']}")

    print(f"  Parent records: " f"{len(parent_records)}")

    print(f"  Child records: " f"{len(child_records)}")

    print("  Invalid references: 0")

    print("  Result: PASS")


# --------------------------------------------------
# Output
# --------------------------------------------------


def save_entity(
    entity_name: str,
    records: list[dict],
) -> None:
    """Save generated entity records to CSV."""

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    output_file = OUTPUT_DIR / f"{entity_name}.csv"

    dataframe = pd.DataFrame(
        records,
    )

    dataframe.to_csv(
        output_file,
        index=False,
    )

    print(f"  {output_file}")


# --------------------------------------------------
# Experiment execution
# --------------------------------------------------


def main() -> None:
    """Run Experiment 004."""

    specification = load_specification()

    generation_config = specification["generation"]

    random_seed = generation_config["seed"]

    random.seed(
        random_seed,
    )

    print("=" * 70)
    print("FORGE - Experiment 004: " "Relationship-Aware Generation")
    print("=" * 70)

    print(f"Specification: " f"{SPECIFICATION_FILE}")

    print(f"Random seed:   " f"{random_seed}")

    # --------------------------------------------------
    # Generate entities
    # --------------------------------------------------

    entities = {}

    entity_specifications = specification["entities"]

    for entity_name, entity_metadata in entity_specifications.items():

        entities[entity_name] = generate_entity(
            entity_name=entity_name,
            entity_metadata=entity_metadata,
        )

    # --------------------------------------------------
    # Generate relationships
    # --------------------------------------------------

    print("\nGenerating relationships...")

    for relationship in specification["relationships"]:

        generate_relationship(
            relationship=relationship,
            entities=entities,
        )

    # --------------------------------------------------
    # Validate relationships
    # --------------------------------------------------

    for relationship in specification["relationships"]:

        validate_relationship(
            relationship=relationship,
            entities=entities,
        )

    # --------------------------------------------------
    # Save outputs
    # --------------------------------------------------

    print("\nOutput:")

    for entity_name, records in entities.items():

        save_entity(
            entity_name=entity_name,
            records=records,
        )

    # --------------------------------------------------
    # Preview
    # --------------------------------------------------

    for entity_name, records in entities.items():

        print(f"\nFirst records: {entity_name}")

        dataframe = pd.DataFrame(
            records,
        )

        print(
            dataframe.head(10).to_string(
                index=False,
            )
        )

    print("\nExperiment completed successfully.")


# --------------------------------------------------
# Entry point
# --------------------------------------------------

if __name__ == "__main__":
    main()
