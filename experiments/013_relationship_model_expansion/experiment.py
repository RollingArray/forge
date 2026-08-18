"""
FORGE - Experiment 013: Relationship Model Expansion
======================================================

Purpose
-------
This experiment tests whether a generic relationship model can represent
and generate multiple relationship topologies while maintaining
referential integrity.

The experiment extends the relationship capabilities established by
Experiments 004, 005, and 006.

The following relationship forms are tested:

    - 1:1
    - 1:N
    - N:1 representation
    - N:M through an associative entity
    - optional relationships
    - multiple foreign keys to the same parent entity

No machine learning, LLM, or real production data is used.

Experiment
----------
013 - Relationship Model Expansion

Key Question
------------
Can a generic relationship model represent and generate multiple
relationship topologies without relationship-specific generation logic?

Author
------
Ranjoy Sen

Status
------
Experimental

How to Run
----------
From the repository root:

    uv run python experiments/013_relationship_model_expansion/experiment.py

Output
------
Generated datasets are written to:

    experiments/013_relationship_model_expansion/output/

Important
---------
The generated data is synthetic and does not represent any real
production dataset.
"""

from pathlib import Path
from collections import Counter
import json
import random

import pandas as pd

# --------------------------------------------------
# Experiment paths
# --------------------------------------------------

EXPERIMENT_DIR = Path(__file__).resolve().parent

SPECIFICATION_FILE = EXPERIMENT_DIR / "specification.json"

OUTPUT_DIR = EXPERIMENT_DIR / "output"

STATISTICS_FILE = OUTPUT_DIR / "relationship_statistics.json"


# --------------------------------------------------
# Specification
# --------------------------------------------------


def load_specification() -> dict:
    """Load the experiment specification."""

    with SPECIFICATION_FILE.open(
        "r",
        encoding="utf-8",
    ) as file:
        return json.load(file)


# --------------------------------------------------
# Metadata helpers
# --------------------------------------------------


def get_entity(
    specification: dict,
    entity_name: str,
) -> dict:
    """Return an entity definition."""

    return specification["entities"][entity_name]


def get_fields(
    specification: dict,
    entity_name: str,
) -> dict:
    """Return fields for an entity."""

    return get_entity(
        specification,
        entity_name,
    )["fields"]


def get_field(
    specification: dict,
    entity_name: str,
    field_name: str,
) -> dict:
    """Return field metadata."""

    return get_fields(
        specification,
        entity_name,
    )[field_name]


# --------------------------------------------------
# Value generation
# --------------------------------------------------


def generate_identifier(
    length: int,
    prefix: str,
    index: int,
) -> str:
    """
    Generate a fixed-width identifier.

    The configured length represents the complete identifier length,
    including the prefix.
    """

    numeric_length = length - len(prefix)

    if numeric_length <= 0:
        raise ValueError("Identifier length must be greater than prefix length.")

    maximum = (10**numeric_length) - 1

    if index > maximum:
        raise ValueError("Identifier capacity exceeded.")

    return prefix + str(index).zfill(numeric_length)


def generate_field_value(
    field_metadata: dict,
    index: int,
):
    """Generate a value according to field metadata."""

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

        values = field_metadata["values"]

        return random.choice(values)

    if field_type == "integer":

        return random.randint(
            field_metadata["min"],
            field_metadata["max"],
        )

    if field_type == "number":

        generation = field_metadata["generation"]

        strategy = generation.get(
            "strategy",
            "uniform",
        )

        if strategy == "uniform":

            return round(
                random.uniform(
                    generation["min"],
                    generation["max"],
                ),
                2,
            )

        raise ValueError("Unsupported number generation strategy: " f"{strategy}")

    raise ValueError(f"Unsupported field type: {field_type}")


# --------------------------------------------------
# Entity generation
# --------------------------------------------------


def generate_entity(
    specification: dict,
    entity_name: str,
) -> pd.DataFrame:
    """Generate an entity without resolving relationships."""

    entity = get_entity(
        specification,
        entity_name,
    )

    record_count = specification["generation"]["record_counts"][entity_name]

    rows = []

    for index in range(
        1,
        record_count + 1,
    ):

        row = {}

        for field_name, field_metadata in entity["fields"].items():

            row[field_name] = generate_field_value(
                field_metadata,
                index,
            )

        rows.append(row)

    return pd.DataFrame(rows)


# --------------------------------------------------
# Relationship helpers
# --------------------------------------------------


def get_relationships(
    specification: dict,
) -> list[dict]:
    """Return declared relationships."""

    return specification["relationships"]


def get_relationship(
    specification: dict,
    relationship_id: str,
) -> dict:
    """Return one relationship definition."""

    for relationship in get_relationships(specification):

        if relationship["id"] == relationship_id:

            return relationship

    raise ValueError(f"Relationship not found: {relationship_id}")


def get_parent_values(
    dataframe: pd.DataFrame,
    field_name: str,
) -> list:
    """Return parent key values."""

    return dataframe[field_name].tolist()


# --------------------------------------------------
# Relationship assignment
# --------------------------------------------------


def assign_one_to_one(
    child_dataframe: pd.DataFrame,
    child_field: str,
    parent_dataframe: pd.DataFrame,
    parent_field: str,
) -> pd.DataFrame:
    """
    Assign each child to a unique parent.

    For this experiment, the 1:1 relationship is expected to have
    matching parent and child record counts.
    """

    parent_values = get_parent_values(
        parent_dataframe,
        parent_field,
    )

    if len(child_dataframe) > len(parent_values):
        raise ValueError(
            "Cannot generate 1:1 relationship: "
            "child record count exceeds parent record count."
        )

    child_dataframe = child_dataframe.copy()

    child_dataframe[child_field] = parent_values[: len(child_dataframe)]

    return child_dataframe


def assign_one_to_many(
    child_dataframe: pd.DataFrame,
    child_field: str,
    parent_dataframe: pd.DataFrame,
    parent_field: str,
) -> pd.DataFrame:
    """Assign child records to parent records allowing reuse."""

    parent_values = get_parent_values(
        parent_dataframe,
        parent_field,
    )

    if not parent_values:
        raise ValueError("Cannot generate relationship without parent records.")

    child_dataframe = child_dataframe.copy()

    child_dataframe[child_field] = [
        random.choice(parent_values) for _ in range(len(child_dataframe))
    ]

    return child_dataframe


def assign_optional_one_to_many(
    child_dataframe: pd.DataFrame,
    child_field: str,
    parent_dataframe: pd.DataFrame,
    parent_field: str,
    population_rate: float = 0.60,
) -> pd.DataFrame:
    """
    Assign optional parent references.

    A populated value always references an existing parent.
    """

    parent_values = get_parent_values(
        parent_dataframe,
        parent_field,
    )

    if not parent_values:
        raise ValueError("Cannot generate relationship without parent records.")

    child_dataframe = child_dataframe.copy()

    values = []

    for _ in range(len(child_dataframe)):

        if random.random() < population_rate:

            values.append(random.choice(parent_values))

        else:

            values.append(None)

    child_dataframe[child_field] = values

    return child_dataframe


# --------------------------------------------------
# Relationship generation
# --------------------------------------------------


def generate_relationship(
    specification: dict,
    relationship: dict,
    entities: dict[str, pd.DataFrame],
) -> None:
    """
    Apply a relationship definition to generated entities.

    Relationship behavior is selected from metadata rather than from
    entity-specific generation code.
    """

    parent_entity = relationship["parent_entity"]

    child_entity = relationship["child_entity"]

    parent_field = relationship["parent_field"]

    child_field = relationship["child_field"]

    cardinality = relationship["cardinality"]

    optional = relationship.get(
        "optional",
        False,
    )

    parent_dataframe = entities[parent_entity]

    child_dataframe = entities[child_entity]

    if cardinality == "1:1":

        entities[child_entity] = assign_one_to_one(
            child_dataframe,
            child_field,
            parent_dataframe,
            parent_field,
        )

        return

    if cardinality in (
        "1:N",
        "N:1",
    ):

        if optional:

            entities[child_entity] = assign_optional_one_to_many(
                child_dataframe,
                child_field,
                parent_dataframe,
                parent_field,
            )

        else:

            entities[child_entity] = assign_one_to_many(
                child_dataframe,
                child_field,
                parent_dataframe,
                parent_field,
            )

        return

    raise ValueError("Unsupported relationship cardinality: " f"{cardinality}")


# --------------------------------------------------
# Relationship validation
# --------------------------------------------------


def validate_referential_integrity(
    parent_dataframe: pd.DataFrame,
    parent_field: str,
    child_dataframe: pd.DataFrame,
    child_field: str,
    optional: bool,
) -> dict:
    """Validate foreign-key references."""

    parent_values = set(parent_dataframe[parent_field].tolist())

    child_values = child_dataframe[child_field]

    null_count = int(child_values.isna().sum())

    non_null_values = child_values.dropna()

    invalid_values = [value for value in non_null_values if value not in parent_values]

    optional_valid = optional or null_count == 0

    return {
        "parent_records": len(parent_dataframe),
        "child_records": len(child_dataframe),
        "invalid_references": len(invalid_values),
        "null_references": null_count,
        "optional": optional,
        "optional_validation": optional_valid,
        "passed": (len(invalid_values) == 0 and optional_valid),
    }


def validate_one_to_one(
    parent_dataframe: pd.DataFrame,
    parent_field: str,
    child_dataframe: pd.DataFrame,
    child_field: str,
) -> dict:
    """Validate uniqueness required by a 1:1 relationship."""

    counts = Counter(child_dataframe[child_field].dropna())

    duplicate_assignments = sum(1 for count in counts.values() if count > 1)

    return {
        "unique_parent_references": len(counts),
        "duplicate_parent_assignments": (duplicate_assignments),
        "passed": (duplicate_assignments == 0),
    }


def validate_relationship(
    relationship: dict,
    entities: dict[str, pd.DataFrame],
) -> dict:
    """Validate a relationship according to its metadata."""

    parent_entity = relationship["parent_entity"]

    child_entity = relationship["child_entity"]

    parent_field = relationship["parent_field"]

    child_field = relationship["child_field"]

    cardinality = relationship["cardinality"]

    optional = relationship.get(
        "optional",
        False,
    )

    parent_dataframe = entities[parent_entity]

    child_dataframe = entities[child_entity]

    result = validate_referential_integrity(
        parent_dataframe,
        parent_field,
        child_dataframe,
        child_field,
        optional,
    )

    result["relationship_id"] = relationship["id"]

    result["parent_entity"] = parent_entity

    result["child_entity"] = child_entity

    result["parent_field"] = parent_field

    result["child_field"] = child_field

    result["cardinality"] = cardinality

    if cardinality == "1:1":

        uniqueness = validate_one_to_one(
            parent_dataframe,
            parent_field,
            child_dataframe,
            child_field,
        )

        result["unique_parent_references"] = uniqueness["unique_parent_references"]

        result["duplicate_parent_assignments"] = uniqueness[
            "duplicate_parent_assignments"
        ]

        result["cardinality_validation"] = uniqueness["passed"]

    else:

        result["cardinality_validation"] = True

    result["passed"] = result["passed"] and result["cardinality_validation"]

    return result


# --------------------------------------------------
# Relationship statistics
# --------------------------------------------------


def relationship_statistics(
    relationship: dict,
    child_dataframe: pd.DataFrame,
) -> dict:
    """Calculate relationship-level statistics."""

    child_field = relationship["child_field"]

    values = child_dataframe[child_field]

    counts = Counter(values.dropna())

    statistics = {
        "relationship_id": relationship["id"],
        "cardinality": relationship["cardinality"],
        "optional": relationship.get(
            "optional",
            False,
        ),
        "child_records": len(child_dataframe),
        "null_references": int(values.isna().sum()),
        "unique_parent_references": len(counts),
    }

    if counts:

        statistics["minimum_children_per_parent"] = min(counts.values())

        statistics["maximum_children_per_parent"] = max(counts.values())

        statistics["average_children_per_parent"] = round(
            sum(counts.values()) / len(counts),
            2,
        )

    else:

        statistics["minimum_children_per_parent"] = 0

        statistics["maximum_children_per_parent"] = 0

        statistics["average_children_per_parent"] = 0

    return statistics


# --------------------------------------------------
# N:M validation
# --------------------------------------------------


def validate_many_to_many(
    order_dataframe: pd.DataFrame,
    product_dataframe: pd.DataFrame,
    order_item_dataframe: pd.DataFrame,
) -> dict:
    """
    Validate the many-to-many relationship represented through
    ORDER_ITEM.

    ORDER -> ORDER_ITEM -> PRODUCT
    """

    order_ids = set(order_dataframe["ORDER_ID"])

    product_ids = set(product_dataframe["PRODUCT_ID"])

    invalid_order_references = [
        value for value in order_item_dataframe["ORDER_ID"] if value not in order_ids
    ]

    invalid_product_references = [
        value
        for value in order_item_dataframe["PRODUCT_ID"]
        if value not in product_ids
    ]

    order_product_pairs = order_item_dataframe[
        [
            "ORDER_ID",
            "PRODUCT_ID",
        ]
    ].drop_duplicates()

    return {
        "order_item_records": len(order_item_dataframe),
        "unique_order_product_pairs": len(order_product_pairs),
        "invalid_order_references": len(invalid_order_references),
        "invalid_product_references": len(invalid_product_references),
        "passed": (
            len(invalid_order_references) == 0 and len(invalid_product_references) == 0
        ),
    }


# --------------------------------------------------
# Output
# --------------------------------------------------


def save_outputs(
    entities: dict[str, pd.DataFrame],
    statistics: dict,
) -> None:
    """Save generated datasets and relationship statistics."""

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    for entity_name, dataframe in entities.items():

        dataframe.to_csv(
            OUTPUT_DIR / f"{entity_name}.csv",
            index=False,
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
    """Run Experiment 013."""

    specification = load_specification()

    experiment = specification["experiment"]

    generation = specification["generation"]

    seed = generation["seed"]

    random.seed(seed)

    print("=" * 70)
    print("FORGE - Experiment 013: " "Relationship Model Expansion")
    print("=" * 70)

    print(f"Experiment:   " f"{experiment['id']} - " f"{experiment['name']}")

    print(f"Specification: " f"{SPECIFICATION_FILE}")

    print(f"Random seed:   {seed}")

    print("\nGenerating entities...")

    entities = {}

    for entity_name in specification["entities"]:

        entities[entity_name] = generate_entity(
            specification,
            entity_name,
        )

        print(
            f"  Generated "
            f"{len(entities[entity_name]):4d} "
            f"records for "
            f"{entity_name}"
        )

    # --------------------------------------------------
    # Relationship generation
    # --------------------------------------------------

    print("\nGenerating relationships...")

    for relationship in get_relationships(specification):

        print(
            f"  {relationship['id']}: "
            f"{relationship['parent_entity']}."
            f"{relationship['parent_field']}"
            f" -> "
            f"{relationship['child_entity']}."
            f"{relationship['child_field']}"
            f" ({relationship['cardinality']})"
        )

        generate_relationship(
            specification,
            relationship,
            entities,
        )

    # --------------------------------------------------
    # Relationship validation
    # --------------------------------------------------

    print("\nRelationship validation:")

    relationship_results = []

    for relationship in get_relationships(specification):

        result = validate_relationship(
            relationship,
            entities,
        )

        relationship_results.append(result)

        print(
            f"\n  {relationship['id']} "
            f"{relationship['parent_entity']}."
            f"{relationship['parent_field']}"
        )

        print(
            f"      -> "
            f"{relationship['child_entity']}."
            f"{relationship['child_field']}"
        )

        print(f"  Cardinality: " f"{relationship['cardinality']}")

        if relationship.get(
            "optional",
            False,
        ):

            print("  Optional: true")

        print(f"  Parent records: " f"{result['parent_records']}")

        print(f"  Child records: " f"{result['child_records']}")

        print(f"  Invalid references: " f"{result['invalid_references']}")

        if relationship["cardinality"] == "1:1":

            print(
                f"  Duplicate parent assignments: "
                f"{result['duplicate_parent_assignments']}"
            )

        if relationship.get(
            "optional",
            False,
        ):

            print(f"  Null references: " f"{result['null_references']}")

        print(f"  Result: " f"{'PASS' if result['passed'] else 'FAIL'}")

    # --------------------------------------------------
    # N:M validation
    # --------------------------------------------------

    print("\nMany-to-many validation:")

    many_to_many_result = validate_many_to_many(
        entities["ORDER"],
        entities["PRODUCT"],
        entities["ORDER_ITEM"],
    )

    print(f"  ORDER -> ORDER_ITEM -> PRODUCT")

    print(f"  Order-item records: " f"{many_to_many_result['order_item_records']}")

    print(
        f"  Unique order-product pairs: "
        f"{many_to_many_result['unique_order_product_pairs']}"
    )

    print(
        f"  Invalid order references: "
        f"{many_to_many_result['invalid_order_references']}"
    )

    print(
        f"  Invalid product references: "
        f"{many_to_many_result['invalid_product_references']}"
    )

    print(f"  Result: " f"{'PASS' if many_to_many_result['passed'] else 'FAIL'}")

    # --------------------------------------------------
    # Relationship statistics
    # --------------------------------------------------

    statistics = []

    for relationship in get_relationships(specification):

        statistics.append(
            relationship_statistics(
                relationship,
                entities[relationship["child_entity"]],
            )
        )

    all_relationships_passed = all(result["passed"] for result in relationship_results)

    overall_result = (
        "PASS"
        if (all_relationships_passed and many_to_many_result["passed"])
        else "FAIL"
    )

    # --------------------------------------------------
    # Save output
    # --------------------------------------------------

    output_statistics = {
        "experiment": experiment,
        "generation": generation,
        "relationships": statistics,
        "many_to_many": many_to_many_result,
        "validation": relationship_results,
        "overall_result": overall_result,
    }

    save_outputs(
        entities,
        output_statistics,
    )

    # --------------------------------------------------
    # Output
    # --------------------------------------------------

    print("\nOutput:")

    for entity_name in entities:

        print(f"  {OUTPUT_DIR / f'{entity_name}.csv'}")

    print(f"  {STATISTICS_FILE}")

    print("\nFirst records:")

    for entity_name in entities:

        print(f"\n{entity_name}")

        print(entities[entity_name].head(5).to_string(index=False))

    print("\nExperiment result:")

    print(
        f"  Relationship validation: "
        f"{'PASS' if all_relationships_passed else 'FAIL'}"
    )

    print(
        f"  Many-to-many validation: "
        f"{'PASS' if many_to_many_result['passed'] else 'FAIL'}"
    )

    print(f"  Overall: {overall_result}")

    print("\nExperiment completed successfully.")


# --------------------------------------------------
# Entry point
# --------------------------------------------------

if __name__ == "__main__":
    main()
