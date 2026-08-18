"""
FORGE - Experiment 014: Parent-Dependent Generation
====================================================

Purpose
-------
This experiment tests whether child-field generation can depend on an
attribute of the related parent entity.

The experiment compares:

    Approach A:
        Independent child generation

    Approach B:
        Parent-dependent child generation

Example:

    CUSTOMER.CUSTOMER_TYPE
            |
            v
    ORDER.AMOUNT

    STANDARD -> 100 - 2,000
    PREMIUM  -> 2,000 - 10,000

No machine learning, LLM, or real production data is used.

Experiment
----------
014 - Parent-Dependent Generation

Key Question
------------
Can a parent attribute provide generation context for a child field
through declarative metadata?

Author
------
Ranjoy Sen

Status
------
Experimental

How to Run
----------
From the repository root:

    uv run python experiments/014_parent_dependent_generation/experiment.py

Output
------
Generated datasets are written to:

    experiments/014_parent_dependent_generation/output/

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

CUSTOMER_OUTPUT_FILE = OUTPUT_DIR / "CUSTOMER.csv"
INDEPENDENT_OUTPUT_FILE = OUTPUT_DIR / "independent_generation.csv"
DEPENDENT_OUTPUT_FILE = OUTPUT_DIR / "parent_dependent_generation.csv"
STATISTICS_FILE = OUTPUT_DIR / "parent_dependency_statistics.json"


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


def get_field(
    specification: dict,
    entity_name: str,
    field_name: str,
) -> dict:
    """Return field metadata."""

    return get_entity(
        specification,
        entity_name,
    )[
        "fields"
    ][field_name]


def get_relationship(
    specification: dict,
    relationship_id: str,
) -> dict:
    """Return a relationship definition."""

    for relationship in specification["relationships"]:
        if relationship["id"] == relationship_id:
            return relationship

    raise ValueError(f"Relationship not found: {relationship_id}")


def get_dependency(
    specification: dict,
    dependency_id: str,
) -> dict:
    """Return a dependency definition."""

    for dependency in specification["dependencies"]:
        if dependency["id"] == dependency_id:
            return dependency

    raise ValueError(f"Dependency not found: {dependency_id}")


# --------------------------------------------------
# Value generation
# --------------------------------------------------


def generate_identifier(
    field_metadata: dict,
    index: int,
) -> str:
    """Generate a fixed-width identifier."""

    prefix = field_metadata.get(
        "prefix",
        "",
    )

    length = field_metadata["length"]

    numeric_length = length - len(prefix)

    if numeric_length <= 0:
        raise ValueError("Identifier length must be greater than prefix length.")

    maximum = (10**numeric_length) - 1

    if index > maximum:
        raise ValueError("Identifier capacity exceeded.")

    return prefix + str(index).zfill(numeric_length)


def generate_categorical(
    field_metadata: dict,
) -> str:
    """Generate a categorical value."""

    return random.choice(field_metadata["values"])


def generate_number(
    field_metadata: dict,
) -> float:
    """Generate a numeric value."""

    generation = field_metadata.get(
        "generation",
        {},
    )

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

    raise ValueError(f"Unsupported numeric generation strategy: {strategy}")


def generate_field_value(
    field_metadata: dict,
    index: int,
):
    """Generate a value according to field metadata."""

    field_type = field_metadata["type"]

    if field_type == "identifier":
        return generate_identifier(
            field_metadata,
            index,
        )

    if field_type == "categorical":
        return generate_categorical(
            field_metadata,
        )

    if field_type == "number":
        return generate_number(
            field_metadata,
        )

    raise ValueError(f"Unsupported field type: {field_type}")


# --------------------------------------------------
# Parent generation
# --------------------------------------------------


def generate_customer_dataset(
    specification: dict,
) -> pd.DataFrame:
    """Generate CUSTOMER records."""

    record_count = specification["generation"]["record_counts"]["CUSTOMER"]

    rows = []

    for index in range(
        1,
        record_count + 1,
    ):
        row = {}

        row["CUSTOMER_ID"] = generate_field_value(
            get_field(
                specification,
                "CUSTOMER",
                "CUSTOMER_ID",
            ),
            index,
        )

        row["CUSTOMER_TYPE"] = generate_field_value(
            get_field(
                specification,
                "CUSTOMER",
                "CUSTOMER_TYPE",
            ),
            index,
        )

        row["COUNTRY"] = generate_field_value(
            get_field(
                specification,
                "CUSTOMER",
                "COUNTRY",
            ),
            index,
        )

        rows.append(row)

    return pd.DataFrame(rows)


# --------------------------------------------------
# Parent context
# --------------------------------------------------


def build_parent_context(
    customer_dataframe: pd.DataFrame,
) -> dict[str, dict]:
    """
    Build an in-memory parent context.

    The complete parent record is retained so future experiments can
    use more than one parent attribute.
    """

    return {
        row["CUSTOMER_ID"]: row.to_dict() for _, row in customer_dataframe.iterrows()
    }


def select_parent(
    parent_context: dict[str, dict],
) -> dict:
    """Select one parent record."""

    parent_id = random.choice(list(parent_context.keys()))

    return parent_context[parent_id]


# --------------------------------------------------
# Independent generation
# --------------------------------------------------


def generate_independent_orders(
    specification: dict,
    customer_dataframe: pd.DataFrame,
) -> pd.DataFrame:
    """
    Generate orders independently of CUSTOMER_TYPE.

    The customer relationship is valid, but CUSTOMER_TYPE does not
    influence ORDER.AMOUNT.
    """

    record_count = specification["generation"]["record_counts"]["ORDER"]

    order_id_metadata = get_field(
        specification,
        "ORDER",
        "ORDER_ID",
    )

    amount_metadata = get_field(
        specification,
        "ORDER",
        "AMOUNT",
    )

    customer_ids = customer_dataframe["CUSTOMER_ID"].tolist()

    rows = []

    for index in range(
        1,
        record_count + 1,
    ):
        customer_id = random.choice(customer_ids)

        rows.append(
            {
                "ORDER_ID": generate_field_value(
                    order_id_metadata,
                    index,
                ),
                "CUSTOMER_ID": customer_id,
                "AMOUNT": generate_field_value(
                    amount_metadata,
                    index,
                ),
            }
        )

    return pd.DataFrame(rows)


# --------------------------------------------------
# Parent-dependent generation
# --------------------------------------------------


def get_parent_dependent_behavior(
    dependency: dict,
    parent_value,
) -> dict:
    """Resolve generation behavior for a parent attribute value."""

    behavior = dependency["behavior"]
    parent_key = str(parent_value)

    if parent_key not in behavior:
        raise ValueError(
            "No parent-dependent behavior declared for " f"value: {parent_value}"
        )

    return behavior[parent_key]


def generate_parent_dependent_number(
    behavior: dict,
) -> float:
    """Generate a number using resolved parent-dependent behavior."""

    distribution = behavior["distribution"]
    distribution_type = distribution["type"]

    if distribution_type == "uniform":
        return round(
            random.uniform(
                distribution["min"],
                distribution["max"],
            ),
            2,
        )

    raise ValueError(
        "Unsupported parent-dependent distribution: " f"{distribution_type}"
    )


def generate_parent_dependent_orders(
    specification: dict,
    customer_dataframe: pd.DataFrame,
) -> pd.DataFrame:
    """
    Generate orders using parent attributes as generation context.
    """

    record_count = specification["generation"]["record_counts"]["ORDER"]

    relationship = get_relationship(
        specification,
        "R001",
    )

    dependency = get_dependency(
        specification,
        "D001",
    )

    order_id_metadata = get_field(
        specification,
        "ORDER",
        "ORDER_ID",
    )

    parent_context = build_parent_context(customer_dataframe)

    rows = []

    for index in range(
        1,
        record_count + 1,
    ):
        parent = select_parent(parent_context)

        parent_id = parent[relationship["parent_field"]]

        parent_attribute = parent[dependency["parent_field"]]

        behavior = get_parent_dependent_behavior(
            dependency,
            parent_attribute,
        )

        amount = generate_parent_dependent_number(behavior)

        rows.append(
            {
                "ORDER_ID": generate_field_value(
                    order_id_metadata,
                    index,
                ),
                relationship["child_field"]: parent_id,
                dependency["child_field"]: amount,
            }
        )

    return pd.DataFrame(rows)


# --------------------------------------------------
# Field validation
# --------------------------------------------------


def validate_field_constraints(
    dataframe: pd.DataFrame,
    specification: dict,
) -> dict:
    """Validate ORDER field constraints."""

    results = {}

    for field_name in [
        "ORDER_ID",
        "CUSTOMER_ID",
        "AMOUNT",
    ]:
        metadata = get_field(
            specification,
            "ORDER",
            field_name,
        )

        series = dataframe[field_name]
        non_null = series.dropna()

        field_type = metadata["type"]
        passed = True

        if field_type == "identifier":
            expected_length = metadata["length"]

            passed = all(len(str(value)) == expected_length for value in non_null)

        elif field_type == "number":
            generation = metadata["generation"]

            minimum = generation["min"]
            maximum = generation["max"]

            passed = bool(
                non_null.between(
                    minimum,
                    maximum,
                ).all()
            )

        results[field_name] = {"passed": bool(passed)}

    return results


# --------------------------------------------------
# Relationship validation
# --------------------------------------------------


def validate_referential_integrity(
    customer_dataframe: pd.DataFrame,
    order_dataframe: pd.DataFrame,
) -> dict:
    """Validate ORDER.CUSTOMER_ID references."""

    parent_ids = set(customer_dataframe["CUSTOMER_ID"])

    invalid_values = [
        value for value in order_dataframe["CUSTOMER_ID"] if value not in parent_ids
    ]

    return {
        "parent_records": len(customer_dataframe),
        "child_records": len(order_dataframe),
        "invalid_references": len(invalid_values),
        "passed": len(invalid_values) == 0,
    }


# --------------------------------------------------
# Parent dependency validation
# --------------------------------------------------


def validate_parent_dependency(
    specification: dict,
    customer_dataframe: pd.DataFrame,
    order_dataframe: pd.DataFrame,
) -> dict:
    """
    Validate that each order amount respects the distribution
    declared for its parent's CUSTOMER_TYPE.
    """

    dependency = get_dependency(
        specification,
        "D001",
    )

    parent_lookup = customer_dataframe.set_index("CUSTOMER_ID")[
        "CUSTOMER_TYPE"
    ].to_dict()

    violations = []
    group_statistics = {}

    for parent_type, behavior in dependency["behavior"].items():

        distribution = behavior["distribution"]

        minimum = distribution["min"]
        maximum = distribution["max"]

        group = order_dataframe[
            order_dataframe["CUSTOMER_ID"].map(parent_lookup) == parent_type
        ]

        amounts = group["AMOUNT"]

        group_violations = amounts[(amounts < minimum) | (amounts > maximum)]

        violations.extend(group_violations.tolist())

        if len(amounts) > 0:
            group_statistics[parent_type] = {
                "records": len(amounts),
                "minimum": round(
                    float(amounts.min()),
                    2,
                ),
                "maximum": round(
                    float(amounts.max()),
                    2,
                ),
                "mean": round(
                    float(amounts.mean()),
                    2,
                ),
                "expected_minimum": minimum,
                "expected_maximum": maximum,
                "passed": len(group_violations) == 0,
            }
        else:
            group_statistics[parent_type] = {
                "records": 0,
                "minimum": None,
                "maximum": None,
                "mean": None,
                "expected_minimum": minimum,
                "expected_maximum": maximum,
                "passed": True,
            }

    return {
        "groups": group_statistics,
        "violations": len(violations),
        "passed": len(violations) == 0,
    }


# --------------------------------------------------
# Distribution statistics
# --------------------------------------------------


def calculate_group_statistics(
    customer_dataframe: pd.DataFrame,
    order_dataframe: pd.DataFrame,
) -> dict:
    """Calculate ORDER.AMOUNT statistics grouped by CUSTOMER_TYPE."""

    parent_lookup = customer_dataframe.set_index("CUSTOMER_ID")[
        "CUSTOMER_TYPE"
    ].to_dict()

    enriched = order_dataframe.copy()

    enriched["CUSTOMER_TYPE"] = enriched["CUSTOMER_ID"].map(parent_lookup)

    statistics = {}

    for customer_type, group in enriched.groupby("CUSTOMER_TYPE"):
        amounts = group["AMOUNT"]

        statistics[customer_type] = {
            "records": len(amounts),
            "mean": round(
                float(amounts.mean()),
                2,
            ),
            "median": round(
                float(amounts.median()),
                2,
            ),
            "minimum": round(
                float(amounts.min()),
                2,
            ),
            "maximum": round(
                float(amounts.max()),
                2,
            ),
        }

    return statistics


def calculate_group_mean_gap(
    statistics: dict,
) -> float:
    """Calculate the absolute difference between group means."""

    means = [value["mean"] for value in statistics.values() if value["records"] > 0]

    if len(means) < 2:
        return 0.0

    return round(
        abs(means[0] - means[1]),
        2,
    )


# --------------------------------------------------
# Output
# --------------------------------------------------


def save_outputs(
    customer_dataframe: pd.DataFrame,
    independent_dataframe: pd.DataFrame,
    dependent_dataframe: pd.DataFrame,
    statistics: dict,
) -> None:
    """Save generated datasets and statistics."""

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    customer_dataframe.to_csv(
        CUSTOMER_OUTPUT_FILE,
        index=False,
    )

    independent_dataframe.to_csv(
        INDEPENDENT_OUTPUT_FILE,
        index=False,
    )

    dependent_dataframe.to_csv(
        DEPENDENT_OUTPUT_FILE,
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
    """Run Experiment 014."""

    specification = load_specification()

    experiment = specification["experiment"]
    generation = specification["generation"]

    seed = generation["seed"]

    print("=" * 70)
    print("FORGE - Experiment 014: " "Parent-Dependent Generation")
    print("=" * 70)

    print(f"Experiment:   " f"{experiment['id']} - " f"{experiment['name']}")

    print(f"Specification: {SPECIFICATION_FILE}")

    print(f"Random seed:   {seed}")

    print(f"Record count:  " f"{generation['record_counts']['ORDER']}")

    # --------------------------------------------------
    # Parent generation
    # --------------------------------------------------

    print("\nGenerating parent entity...")

    random.seed(seed)

    customer_dataframe = generate_customer_dataset(specification)

    print(f"  Generated " f"{len(customer_dataframe)} " f"records for CUSTOMER")

    # --------------------------------------------------
    # Independent generation
    # --------------------------------------------------

    print("\nApproach A: Independent generation")

    random.seed(seed)

    independent_dataframe = generate_independent_orders(
        specification,
        customer_dataframe,
    )

    independent_field_validation = validate_field_constraints(
        independent_dataframe,
        specification,
    )

    independent_field_passed = all(
        result["passed"] for result in independent_field_validation.values()
    )

    independent_relationship_validation = validate_referential_integrity(
        customer_dataframe,
        independent_dataframe,
    )

    independent_statistics = calculate_group_statistics(
        customer_dataframe,
        independent_dataframe,
    )

    independent_mean_gap = calculate_group_mean_gap(independent_statistics)

    print(f"  Field validation: " f"{'PASS' if independent_field_passed else 'FAIL'}")

    print(
        f"  Relationship validation: "
        f"{'PASS' if independent_relationship_validation['passed'] else 'FAIL'}"
    )

    for parent_type, stats in independent_statistics.items():
        print(
            f"  {parent_type}: "
            f"mean={stats['mean']:.2f}, "
            f"median={stats['median']:.2f}"
        )

    print(f"  Group mean gap: " f"{independent_mean_gap:.2f}")

    # --------------------------------------------------
    # Parent-dependent generation
    # --------------------------------------------------

    print("\nApproach B: Parent-dependent generation")

    random.seed(seed)

    dependent_dataframe = generate_parent_dependent_orders(
        specification,
        customer_dataframe,
    )

    dependent_field_validation = validate_field_constraints(
        dependent_dataframe,
        specification,
    )

    dependent_field_passed = all(
        result["passed"] for result in dependent_field_validation.values()
    )

    dependent_relationship_validation = validate_referential_integrity(
        customer_dataframe,
        dependent_dataframe,
    )

    dependency_validation = validate_parent_dependency(
        specification,
        customer_dataframe,
        dependent_dataframe,
    )

    dependent_statistics = calculate_group_statistics(
        customer_dataframe,
        dependent_dataframe,
    )

    dependent_mean_gap = calculate_group_mean_gap(dependent_statistics)

    print(f"  Field validation: " f"{'PASS' if dependent_field_passed else 'FAIL'}")

    print(
        f"  Relationship validation: "
        f"{'PASS' if dependent_relationship_validation['passed'] else 'FAIL'}"
    )

    for parent_type, stats in dependent_statistics.items():
        print(
            f"  {parent_type}: "
            f"mean={stats['mean']:.2f}, "
            f"median={stats['median']:.2f}"
        )

    print(
        f"  Parent-dependent validation: "
        f"{'PASS' if dependency_validation['passed'] else 'FAIL'}"
    )

    print(f"  Group mean gap: " f"{dependent_mean_gap:.2f}")

    # --------------------------------------------------
    # Comparison
    # --------------------------------------------------

    mean_gap_change = round(
        dependent_mean_gap - independent_mean_gap,
        2,
    )

    overall_passed = (
        independent_field_passed
        and independent_relationship_validation["passed"]
        and dependent_field_passed
        and dependent_relationship_validation["passed"]
        and dependency_validation["passed"]
    )

    overall_result = "PASS" if overall_passed else "FAIL"

    statistics = {
        "experiment": experiment,
        "generation": generation,
        "independent": {
            "field_validation": independent_field_validation,
            "relationship_validation": (independent_relationship_validation),
            "group_statistics": independent_statistics,
            "group_mean_gap": independent_mean_gap,
        },
        "parent_dependent": {
            "field_validation": dependent_field_validation,
            "relationship_validation": (dependent_relationship_validation),
            "dependency_validation": dependency_validation,
            "group_statistics": dependent_statistics,
            "group_mean_gap": dependent_mean_gap,
        },
        "comparison": {
            "independent_group_mean_gap": (independent_mean_gap),
            "parent_dependent_group_mean_gap": (dependent_mean_gap),
            "group_mean_gap_change": (mean_gap_change),
        },
        "overall_result": overall_result,
    }

    # --------------------------------------------------
    # Save output
    # --------------------------------------------------

    save_outputs(
        customer_dataframe,
        independent_dataframe,
        dependent_dataframe,
        statistics,
    )

    # --------------------------------------------------
    # Output
    # --------------------------------------------------

    print("\nOutput:")

    print(f"  Customer: " f"{CUSTOMER_OUTPUT_FILE}")

    print(f"  Independent: " f"{INDEPENDENT_OUTPUT_FILE}")

    print(f"  Parent-dependent: " f"{DEPENDENT_OUTPUT_FILE}")

    print(f"  Statistics: " f"{STATISTICS_FILE}")

    print("\nFirst 10 records: Independent")

    print(independent_dataframe.head(10).to_string(index=False))

    print("\nFirst 10 records: Parent-dependent")

    print(dependent_dataframe.head(10).to_string(index=False))

    print("\nExperiment result:")

    print(
        f"  Independent field validation: "
        f"{'PASS' if independent_field_passed else 'FAIL'}"
    )

    print(
        f"  Parent-dependent field validation: "
        f"{'PASS' if dependent_field_passed else 'FAIL'}"
    )

    print(
        f"  Referential integrity: "
        f"{'PASS' if dependent_relationship_validation['passed'] else 'FAIL'}"
    )

    print(
        f"  Parent dependency: "
        f"{'PASS' if dependency_validation['passed'] else 'FAIL'}"
    )

    print(f"  Overall: {overall_result}")

    print("\nExperiment completed successfully.")


# --------------------------------------------------
# Entry point
# --------------------------------------------------

if __name__ == "__main__":
    main()
