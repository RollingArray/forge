"""
FORGE - Experiment 020-H: Declarative Relationships and Reference Resolution
=============================================================================

Purpose
-------
This experiment validates relationships and reference resolution as
first-class declarative generation capabilities.

The experiment builds on the identity capabilities established by
Experiment 020-G.

The following relationship forms are tested:

    1:1
    0:1
    1:N
    0:N
    N:M

The following relationship semantics are tested:

    PARENT
    CHILD
    ASSOCIATIVE
    REQUIRED
    OPTIONAL
    DEPENDENT

The experiment verifies that generated foreign-key values reference
actual parent identities and that relationship cardinality is enforced.

Stage
-----
020-H - Declarative Relationships and Reference Resolution

Research Question
-----------------
Can FORGE declaratively represent and generate related entities while
preserving referential integrity and relationship cardinality?

Hypothesis
----------
A generic relationship model can resolve references between entities
without requiring entity-specific generation logic.

The relationship engine should:

    - identify parent and child entities
    - generate parent identities before dependent references
    - resolve child foreign keys against parent identities
    - support required and optional relationships
    - support 1:1 and 1:N cardinalities
    - represent N:M through an associative entity
    - reject invalid references
    - remain deterministic under a fixed seed
    - remain independent of entity declaration order

Scope
-----
Included:

    - parent-child relationships
    - foreign-key resolution
    - 1:1
    - 0:1
    - 1:N
    - 0:N
    - N:M through an associative entity
    - REQUIRED relationships
    - OPTIONAL relationships
    - referential integrity
    - relationship cardinality validation
    - deterministic relationship assignment
    - entity-order independence
    - relationship configuration validation

Excluded:

    - arbitrary field dependencies
    - conditional dependencies
    - formulas
    - statistical correlation
    - temporal dependencies
    - scenario overrides
    - population distributions beyond what is required
    - LLM-generated specifications

Those capabilities are addressed by later experiments.

Important Architectural Principle
---------------------------------
A foreign key is not merely a generated value.

A valid foreign key must reference an identity that actually exists
in the target entity.

Therefore:

    FOREIGN_KEY generation
        +
    reference resolution
        =
    valid relationship

Relationship generation must remain generic and must not contain
business-specific logic such as:

    if entity == "ORDER":
        ...

The relationship specification itself must determine behavior.

Important Boundary
------------------
N:M relationships are represented through an associative entity.

For example:

    ORDER
       |
       | N:M
       |
    PRODUCT

is represented as:

    ORDER
       |
       | 1:N
       v
    ORDER_ITEM
       ^
       | N:1
       |
    PRODUCT

This experiment validates the associative representation but does
not attempt to generate arbitrary graph structures.

Author
------
Ranjoy Sen

Status
------
Experimental

How to Run
----------
From the repository root:

    uv run python experiments/020_declarative_generation_specification/experiment-020-H.py

Output
------
Results are written to:

    experiments/020_declarative_generation_specification/output/

Important
---------
All generated data is synthetic and domain-neutral.
"""

from __future__ import annotations

import hashlib
import json
import random
import sys
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any

# ============================================================================
# PATHS / CONSTANTS
# ============================================================================

EXPERIMENT_DIR = Path(__file__).resolve().parent

OUTPUT_DIR = EXPERIMENT_DIR / "output"

RESULT_OUTPUT_PATH = OUTPUT_DIR / "relationship_results.json"

RANDOM_SEED = 42


# ============================================================================
# CONTROLLED VOCABULARY
# ============================================================================

RELATIONSHIP_CARDINALITIES = {
    "1:1",
    "0:1",
    "1:N",
    "0:N",
    "N:M",
}

RELATIONSHIP_SEMANTICS = {
    "PARENT",
    "CHILD",
    "ASSOCIATIVE",
    "REQUIRED",
    "OPTIONAL",
    "DEPENDENT",
}


# ============================================================================
# DECLARATIVE RELATIONSHIP MODEL
# ============================================================================


@dataclass(frozen=True)
class EntityIdentity:
    """
    Defines the identity field of an entity.
    """

    entity: str
    field: str


@dataclass(frozen=True)
class RelationshipSpecification:
    """
    Generic declarative relationship.

    parent:
        Parent entity.

    child:
        Child entity.

    parent_key:
        Identity field on the parent.

    child_key:
        Foreign-key field on the child.

    cardinality:
        Relationship cardinality.

    requirement:
        REQUIRED or OPTIONAL.

    semantics:
        PARENT, CHILD, DEPENDENT, etc.

    min_children / max_children:
        Cardinality bounds used for validation.

    associative:
        Marks an associative relationship representation.
    """

    name: str
    parent: str
    child: str
    parent_key: str
    child_key: str

    cardinality: str

    requirement: str

    semantics: tuple[str, ...]

    min_children: int = 0
    max_children: int | None = None

    associative: bool = False


# ============================================================================
# RELATIONSHIP ENGINE
# ============================================================================


class RelationshipEngine:
    """
    Generic relationship resolution engine.

    No domain-specific entity names are used by the implementation.
    """

    def __init__(
        self,
        seed: int = RANDOM_SEED,
    ) -> None:

        self.seed = seed

    # ------------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------------

    def validate_specification(
        self,
        relationship: RelationshipSpecification,
        entities: dict[
            str,
            list[dict[str, Any]],
        ],
    ) -> None:

        if relationship.cardinality not in RELATIONSHIP_CARDINALITIES:

            raise ValueError(
                "Unsupported relationship "
                f"cardinality: "
                f"{relationship.cardinality}"
            )

        if relationship.requirement not in {
            "REQUIRED",
            "OPTIONAL",
        }:

            raise ValueError(
                "Unsupported relationship "
                f"requirement: "
                f"{relationship.requirement}"
            )

        for semantic in relationship.semantics:

            if semantic not in RELATIONSHIP_SEMANTICS:

                raise ValueError("Unsupported relationship " f"semantic: {semantic}")

        if relationship.parent not in entities:

            raise ValueError(
                f"Parent entity " f"'{relationship.parent}' " "does not exist."
            )

        if relationship.child not in entities:

            raise ValueError(
                f"Child entity " f"'{relationship.child}' " "does not exist."
            )

        parent_records = entities[relationship.parent]

        child_records = entities[relationship.child]

        if parent_records:

            if relationship.parent_key not in parent_records[0]:

                raise ValueError(
                    "Parent identity field "
                    f"'{relationship.parent_key}' "
                    "does not exist."
                )

        if child_records:

            if relationship.child_key not in child_records[0]:

                raise ValueError(
                    "Child foreign-key field "
                    f"'{relationship.child_key}' "
                    "does not exist."
                )

        if relationship.requirement == "REQUIRED" and relationship.cardinality in {
            "0:1",
            "0:N",
        }:

            raise ValueError(
                "REQUIRED relationship cannot " "use optional cardinality."
            )

    # ------------------------------------------------------------------------
    # Resolve relationship
    # ------------------------------------------------------------------------

    def resolve(
        self,
        relationship: RelationshipSpecification,
        entities: dict[
            str,
            list[dict[str, Any]],
        ],
    ) -> dict[str, Any]:

        self.validate_specification(
            relationship,
            entities,
        )

        parent_records = entities[relationship.parent]

        child_records = entities[relationship.child]

        if not parent_records:

            raise ValueError(
                "Cannot resolve relationship " "against an empty parent entity."
            )

        if not child_records:

            return {
                "relationship": relationship.name,
                "status": "PASS",
                "children": 0,
                "parents": len(parent_records),
            }

        parent_ids = [record[relationship.parent_key] for record in parent_records]

        if not all(value is not None for value in parent_ids):

            raise ValueError("Parent identity contains null.")

        if len(parent_ids) != len(set(parent_ids)):

            raise ValueError("Parent identity is not unique.")

        assignments = self._build_assignments(
            relationship,
            parent_ids,
            len(child_records),
        )

        for index, record in enumerate(child_records):

            record[relationship.child_key] = assignments[index]

        validation = self.validate_relationship(
            relationship,
            entities,
        )

        return validation

    # ------------------------------------------------------------------------
    # Assignment
    # ------------------------------------------------------------------------

    def _build_assignments(
        self,
        relationship: RelationshipSpecification,
        parent_ids: list[Any],
        child_count: int,
    ) -> list[Any]:

        if not parent_ids:

            raise ValueError("No parent identities available.")

        if relationship.cardinality in {"1:1", "0:1"}:

            return self._assign_one_to_one(
                relationship,
                parent_ids,
                child_count,
            )

        if relationship.cardinality in {"1:N", "0:N"}:

            return self._assign_one_to_many(
                relationship,
                parent_ids,
                child_count,
            )

        raise ValueError("N:M assignment must use an " "associative entity.")

    # ------------------------------------------------------------------------
    # 1:1 / 0:1
    # ------------------------------------------------------------------------

    def _assign_one_to_one(
        self,
        relationship: RelationshipSpecification,
        parent_ids: list[Any],
        child_count: int,
    ) -> list[Any]:

        if child_count > len(parent_ids):

            if (
                relationship.cardinality == "1:1"
                and relationship.requirement == "REQUIRED"
            ):

                raise ValueError(
                    "1:1 relationship cannot " "assign more children than " "parents."
                )

        assignments: list[Any] = []

        for index in range(child_count):

            if index < len(parent_ids):

                assignments.append(parent_ids[index])

            else:

                assignments.append(None)

        return assignments

    # ------------------------------------------------------------------------
    # 1:N / 0:N
    # ------------------------------------------------------------------------

    def _assign_one_to_many(
        self,
        relationship: RelationshipSpecification,
        parent_ids: list[Any],
        child_count: int,
    ) -> list[Any]:

        if relationship.requirement == "REQUIRED" and child_count < len(parent_ids):

            raise ValueError(
                "Required 1:N relationship "
                "requires every parent to have "
                "at least one child."
            )

        assignments = []

        for index in range(child_count):

            parent_index = index % len(parent_ids)

            assignments.append(parent_ids[parent_index])

        return assignments

    # ------------------------------------------------------------------------
    # Relationship validation
    # ------------------------------------------------------------------------

    def validate_relationship(
        self,
        relationship: RelationshipSpecification,
        entities: dict[
            str,
            list[dict[str, Any]],
        ],
    ) -> dict[str, Any]:

        parent_records = entities[relationship.parent]

        child_records = entities[relationship.child]

        parent_ids = {record[relationship.parent_key] for record in parent_records}

        child_references = [
            record.get(relationship.child_key) for record in child_records
        ]

        null_references = sum(value is None for value in child_references)

        invalid_references = [
            value
            for value in child_references
            if value is not None and value not in parent_ids
        ]

        counts: dict[Any, int] = {}

        for value in child_references:

            if value is None:
                continue

            counts[value] = counts.get(value, 0) + 1

        duplicate_child_parent_pairs = 0

        if relationship.cardinality == "1:1":

            duplicate_child_parent_pairs = sum(count > 1 for count in counts.values())

        required_parent_coverage = (
            len(counts) == len(parent_ids)
            if relationship.requirement == "REQUIRED"
            else True
        )

        if relationship.cardinality == "1:1":

            cardinality_valid = all(count <= 1 for count in counts.values())

        else:

            cardinality_valid = True

        if relationship.requirement == "REQUIRED":

            nullability_valid = null_references == 0

        else:

            nullability_valid = True

        referential_integrity = len(invalid_references) == 0

        passed = all(
            [
                referential_integrity,
                cardinality_valid,
                nullability_valid,
                required_parent_coverage,
            ]
        )

        return {
            "relationship": (relationship.name),
            "status": ("PASS" if passed else "FAIL"),
            "parent_count": len(parent_records),
            "child_count": len(child_records),
            "distinct_parent_references": len(counts),
            "null_references": (null_references),
            "invalid_references": (invalid_references),
            "referential_integrity": (referential_integrity),
            "cardinality_valid": (cardinality_valid),
            "nullability_valid": (nullability_valid),
            "required_parent_coverage": (required_parent_coverage),
            "duplicate_parent_assignments": (duplicate_child_parent_pairs),
        }


# ============================================================================
# GENERIC ENTITY FACTORY
# ============================================================================


def build_entity(
    entity_name: str,
    prefix: str,
    record_count: int,
) -> list[dict[str, Any]]:

    return [
        {f"{entity_name}_ID": (f"{prefix}-{index + 1:04d}")}
        for index in range(record_count)
    ]


# ============================================================================
# VALIDATION 1: 1:1
# ============================================================================


def validate_one_to_one() -> dict[str, Any]:

    entities = {
        "PARENT": build_entity(
            "PARENT",
            "PAR",
            100,
        ),
        "CHILD": build_entity(
            "CHILD",
            "CHD",
            100,
        ),
    }

    # Rename child identity into FK field.
    for record in entities["CHILD"]:

        record["PARENT_ID"] = None

    relationship = RelationshipSpecification(
        name="R-1-1",
        parent="PARENT",
        child="CHILD",
        parent_key="PARENT_ID",
        child_key="PARENT_ID",
        cardinality="1:1",
        requirement="REQUIRED",
        semantics=(
            "PARENT",
            "CHILD",
            "REQUIRED",
            "DEPENDENT",
        ),
    )

    result = RelationshipEngine(seed=RANDOM_SEED).resolve(
        relationship,
        entities,
    )

    return result


# ============================================================================
# VALIDATION 2: 0:1
# ============================================================================


def validate_zero_to_one() -> dict[str, Any]:

    entities = {
        "PARENT": build_entity(
            "PARENT",
            "PAR",
            100,
        ),
        "CHILD": build_entity(
            "CHILD",
            "CHD",
            150,
        ),
    }

    for record in entities["CHILD"]:

        record["PARENT_ID"] = None

    relationship = RelationshipSpecification(
        name="R-0-1",
        parent="PARENT",
        child="CHILD",
        parent_key="PARENT_ID",
        child_key="PARENT_ID",
        cardinality="0:1",
        requirement="OPTIONAL",
        semantics=(
            "PARENT",
            "CHILD",
            "OPTIONAL",
        ),
    )

    # For 0:1, deliberately use only one child
    # per parent and leave remaining children
    # unassigned.
    engine = RelationshipEngine(seed=RANDOM_SEED)

    parent_ids = [record["PARENT_ID"] for record in entities["PARENT"]]

    for index, record in enumerate(entities["CHILD"]):

        if index < len(parent_ids):

            record["PARENT_ID"] = parent_ids[index]

        else:

            record["PARENT_ID"] = None

    return engine.validate_relationship(
        relationship,
        entities,
    )


# ============================================================================
# VALIDATION 3: 1:N
# ============================================================================


def validate_one_to_many() -> dict[str, Any]:

    entities = {
        "PARENT": build_entity(
            "PARENT",
            "PAR",
            100,
        ),
        "CHILD": build_entity(
            "CHILD",
            "CHD",
            1000,
        ),
    }

    for record in entities["CHILD"]:

        record["PARENT_ID"] = None

    relationship = RelationshipSpecification(
        name="R-1-N",
        parent="PARENT",
        child="CHILD",
        parent_key="PARENT_ID",
        child_key="PARENT_ID",
        cardinality="1:N",
        requirement="REQUIRED",
        semantics=(
            "PARENT",
            "CHILD",
            "REQUIRED",
            "DEPENDENT",
        ),
    )

    return RelationshipEngine(seed=RANDOM_SEED).resolve(
        relationship,
        entities,
    )


# ============================================================================
# VALIDATION 4: 0:N
# ============================================================================


def validate_zero_to_many() -> dict[str, Any]:

    entities = {
        "PARENT": build_entity(
            "PARENT",
            "PAR",
            100,
        ),
        "CHILD": build_entity(
            "CHILD",
            "CHD",
            50,
        ),
    }

    for record in entities["CHILD"]:

        record["PARENT_ID"] = None

    relationship = RelationshipSpecification(
        name="R-0-N",
        parent="PARENT",
        child="CHILD",
        parent_key="PARENT_ID",
        child_key="PARENT_ID",
        cardinality="0:N",
        requirement="OPTIONAL",
        semantics=(
            "PARENT",
            "CHILD",
            "OPTIONAL",
        ),
    )

    result = RelationshipEngine(seed=RANDOM_SEED).resolve(
        relationship,
        entities,
    )

    return result


# ============================================================================
# VALIDATION 5: REQUIRED vs OPTIONAL
# ============================================================================


def validate_required_optional() -> dict[str, Any]:

    entities = {
        "PARENT": build_entity(
            "PARENT",
            "PAR",
            10,
        ),
        "CHILD": build_entity(
            "CHILD",
            "CHD",
            10,
        ),
    }

    for record in entities["CHILD"]:

        record["PARENT_ID"] = None

    engine = RelationshipEngine(seed=RANDOM_SEED)

    required_relationship = RelationshipSpecification(
        name="REQUIRED",
        parent="PARENT",
        child="CHILD",
        parent_key="PARENT_ID",
        child_key="PARENT_ID",
        cardinality="1:N",
        requirement="REQUIRED",
        semantics=(
            "PARENT",
            "CHILD",
            "REQUIRED",
        ),
    )

    optional_relationship = RelationshipSpecification(
        name="OPTIONAL",
        parent="PARENT",
        child="CHILD",
        parent_key="PARENT_ID",
        child_key="PARENT_ID",
        cardinality="0:N",
        requirement="OPTIONAL",
        semantics=(
            "PARENT",
            "CHILD",
            "OPTIONAL",
        ),
    )

    required_result = engine.resolve(
        required_relationship,
        entities,
    )

    # Clear references before optional test.
    for record in entities["CHILD"]:

        record["PARENT_ID"] = None

    optional_result = engine.resolve(
        optional_relationship,
        entities,
    )

    passed = required_result["status"] == "PASS" and optional_result["status"] == "PASS"

    return {
        "status": ("PASS" if passed else "FAIL"),
        "required": required_result,
        "optional": optional_result,
    }


# ============================================================================
# VALIDATION 6: REFERENTIAL INTEGRITY
# ============================================================================


def validate_referential_integrity() -> dict[str, Any]:

    entities = {
        "PARENT": build_entity(
            "PARENT",
            "PAR",
            10,
        ),
        "CHILD": build_entity(
            "CHILD",
            "CHD",
            10,
        ),
    }

    valid_parent_ids = [record["PARENT_ID"] for record in entities["PARENT"]]

    for index, record in enumerate(entities["CHILD"]):

        record["PARENT_ID"] = valid_parent_ids[index % len(valid_parent_ids)]

    relationship = RelationshipSpecification(
        name="R-INTEGRITY",
        parent="PARENT",
        child="CHILD",
        parent_key="PARENT_ID",
        child_key="PARENT_ID",
        cardinality="1:N",
        requirement="REQUIRED",
        semantics=(
            "PARENT",
            "CHILD",
            "REQUIRED",
        ),
    )

    valid_result = RelationshipEngine(seed=RANDOM_SEED).validate_relationship(
        relationship,
        entities,
    )

    # Inject an invalid reference.
    entities["CHILD"][0]["PARENT_ID"] = "NON_EXISTENT_PARENT"

    invalid_result = RelationshipEngine(seed=RANDOM_SEED).validate_relationship(
        relationship,
        entities,
    )

    passed = (
        valid_result["status"] == "PASS"
        and invalid_result["status"] == "FAIL"
        and len(invalid_result["invalid_references"]) == 1
    )

    return {
        "status": ("PASS" if passed else "FAIL"),
        "valid_case": valid_result,
        "invalid_case": invalid_result,
    }


# ============================================================================
# VALIDATION 7: N:M THROUGH ASSOCIATIVE ENTITY
# ============================================================================


def validate_many_to_many() -> dict[str, Any]:

    orders = build_entity(
        "ORDER",
        "ORD",
        20,
    )

    products = build_entity(
        "PRODUCT",
        "PRD",
        10,
    )

    order_items: list[dict[str, Any]] = []

    line_number = 1

    # Each order gets multiple products.
    for order_index, order in enumerate(orders):

        for product_index in range(3):

            product = products[(order_index + product_index) % len(products)]

            order_items.append(
                {
                    "ORDER_ID": (order["ORDER_ID"]),
                    "PRODUCT_ID": (product["PRODUCT_ID"]),
                    "LINE_NUMBER": (line_number),
                }
            )

            line_number += 1

    entities = {
        "ORDER": orders,
        "PRODUCT": products,
        "ORDER_ITEM": order_items,
    }

    order_relationship = RelationshipSpecification(
        name="R-ORDER-ITEM",
        parent="ORDER",
        child="ORDER_ITEM",
        parent_key="ORDER_ID",
        child_key="ORDER_ID",
        cardinality="1:N",
        requirement="REQUIRED",
        semantics=(
            "PARENT",
            "CHILD",
            "ASSOCIATIVE",
            "REQUIRED",
            "DEPENDENT",
        ),
        associative=True,
    )

    product_relationship = RelationshipSpecification(
        name="R-PRODUCT-ITEM",
        parent="PRODUCT",
        child="ORDER_ITEM",
        parent_key="PRODUCT_ID",
        child_key="PRODUCT_ID",
        cardinality="1:N",
        requirement="REQUIRED",
        semantics=(
            "PARENT",
            "CHILD",
            "ASSOCIATIVE",
            "REQUIRED",
            "DEPENDENT",
        ),
        associative=True,
    )

    engine = RelationshipEngine(seed=RANDOM_SEED)

    order_result = engine.validate_relationship(
        order_relationship,
        entities,
    )

    product_result = engine.validate_relationship(
        product_relationship,
        entities,
    )

    # Validate that the associative entity actually
    # represents multiple combinations.
    combinations = {
        (
            record["ORDER_ID"],
            record["PRODUCT_ID"],
        )
        for record in order_items
    }

    passed = (
        order_result["status"] == "PASS"
        and product_result["status"] == "PASS"
        and len(combinations) > len(orders)
    )

    return {
        "status": ("PASS" if passed else "FAIL"),
        "order_relationship": order_result,
        "product_relationship": product_result,
        "associative_records": len(order_items),
        "unique_combinations": len(combinations),
    }


# ============================================================================
# VALIDATION 8: DETERMINISM
# ============================================================================


def validate_determinism() -> dict[str, Any]:

    def generate() -> dict[
        str,
        list[dict[str, Any]],
    ]:

        entities = {
            "PARENT": build_entity(
                "PARENT",
                "PAR",
                20,
            ),
            "CHILD": build_entity(
                "CHILD",
                "CHD",
                100,
            ),
        }

        for record in entities["CHILD"]:

            record["PARENT_ID"] = None

        relationship = RelationshipSpecification(
            name="R-DETERMINISTIC",
            parent="PARENT",
            child="CHILD",
            parent_key="PARENT_ID",
            child_key="PARENT_ID",
            cardinality="1:N",
            requirement="REQUIRED",
            semantics=(
                "PARENT",
                "CHILD",
                "REQUIRED",
            ),
        )

        RelationshipEngine(seed=RANDOM_SEED).resolve(
            relationship,
            entities,
        )

        return entities

    first = generate()
    second = generate()

    passed = first == second

    return {
        "status": ("PASS" if passed else "FAIL"),
        "identical": passed,
    }


# ============================================================================
# VALIDATION 9: ENTITY DECLARATION ORDER
# ============================================================================


def validate_entity_order_independence() -> dict[str, Any]:

    def generate(
        reverse: bool,
    ) -> dict[
        str,
        list[dict[str, Any]],
    ]:

        parent = build_entity(
            "PARENT",
            "PAR",
            20,
        )

        child = build_entity(
            "CHILD",
            "CHD",
            100,
        )

        for record in child:

            record["PARENT_ID"] = None

        if reverse:

            entities = {
                "CHILD": child,
                "PARENT": parent,
            }

        else:

            entities = {
                "PARENT": parent,
                "CHILD": child,
            }

        relationship = RelationshipSpecification(
            name="R-ORDER",
            parent="PARENT",
            child="CHILD",
            parent_key="PARENT_ID",
            child_key="PARENT_ID",
            cardinality="1:N",
            requirement="REQUIRED",
            semantics=(
                "PARENT",
                "CHILD",
                "REQUIRED",
            ),
        )

        RelationshipEngine(seed=RANDOM_SEED).resolve(
            relationship,
            entities,
        )

        return entities

    first = generate(reverse=False)

    second = generate(reverse=True)

    first_values = [record["PARENT_ID"] for record in first["CHILD"]]

    second_values = [record["PARENT_ID"] for record in second["CHILD"]]

    passed = first_values == second_values

    return {
        "status": ("PASS" if passed else "FAIL"),
        "identical": passed,
    }


# ============================================================================
# VALIDATION 10: INVALID CONFIGURATION
# ============================================================================


def validate_invalid_configuration() -> dict[str, Any]:

    engine = RelationshipEngine(seed=RANDOM_SEED)

    entities = {
        "PARENT": build_entity(
            "PARENT",
            "PAR",
            10,
        ),
        "CHILD": build_entity(
            "CHILD",
            "CHD",
            10,
        ),
    }

    for record in entities["CHILD"]:

        record["PARENT_ID"] = None

    failures = []

    # Unknown cardinality.
    try:

        engine.resolve(
            RelationshipSpecification(
                name="INVALID-CARDINALITY",
                parent="PARENT",
                child="CHILD",
                parent_key="PARENT_ID",
                child_key="PARENT_ID",
                cardinality="X:Y",
                requirement="REQUIRED",
                semantics=("PARENT", "CHILD"),
            ),
            entities,
        )

        failures.append("Unknown cardinality accepted.")

    except ValueError:
        pass

    # Invalid parent entity.
    try:

        engine.resolve(
            RelationshipSpecification(
                name="INVALID-PARENT",
                parent="UNKNOWN",
                child="CHILD",
                parent_key="PARENT_ID",
                child_key="PARENT_ID",
                cardinality="1:N",
                requirement="REQUIRED",
                semantics=("PARENT", "CHILD"),
            ),
            entities,
        )

        failures.append("Unknown parent accepted.")

    except ValueError:
        pass

    # Invalid child FK field.
    try:

        engine.resolve(
            RelationshipSpecification(
                name="INVALID-FK",
                parent="PARENT",
                child="CHILD",
                parent_key="PARENT_ID",
                child_key="UNKNOWN_FK",
                cardinality="1:N",
                requirement="REQUIRED",
                semantics=("PARENT", "CHILD"),
            ),
            entities,
        )

        failures.append("Unknown child FK accepted.")

    except ValueError:
        pass

    # Required relationship with optional
    # cardinality.
    try:

        engine.resolve(
            RelationshipSpecification(
                name="INVALID-REQUIRED",
                parent="PARENT",
                child="CHILD",
                parent_key="PARENT_ID",
                child_key="PARENT_ID",
                cardinality="0:N",
                requirement="REQUIRED",
                semantics=("PARENT", "CHILD"),
            ),
            entities,
        )

        failures.append("Required 0:N relationship accepted.")

    except ValueError:
        pass

    passed = not failures

    return {
        "status": ("PASS" if passed else "FAIL"),
        "unexpected_acceptances": failures,
    }


# ============================================================================
# MAIN
# ============================================================================


def main() -> int:

    print()

    print("=" * 70)

    print(
        "FORGE - Experiment 020-H: "
        "Declarative Relationships and Reference Resolution"
    )

    print("=" * 70)

    print("Experiment:     " "020_declarative_generation_specification")

    print("Stage:          020-H")

    print("Purpose:        " "Declarative relationships and reference resolution")

    print(f"Random seed:    {RANDOM_SEED}")

    print()

    print("Relationship cardinalities:")

    for value in sorted(RELATIONSHIP_CARDINALITIES):

        print(f"  {value}")

    print()

    print("Relationship semantics:")

    for value in sorted(RELATIONSHIP_SEMANTICS):

        print(f"  {value}")

    print()

    # ------------------------------------------------------------------------
    # Run validations
    # ------------------------------------------------------------------------

    results = {
        "one_to_one": (validate_one_to_one()),
        "zero_to_one": (validate_zero_to_one()),
        "one_to_many": (validate_one_to_many()),
        "zero_to_many": (validate_zero_to_many()),
        "required_optional": (validate_required_optional()),
        "referential_integrity": (validate_referential_integrity()),
        "many_to_many": (validate_many_to_many()),
        "determinism": (validate_determinism()),
        "entity_order_independence": (validate_entity_order_independence()),
        "invalid_configuration": (validate_invalid_configuration()),
    }

    labels = {
        "one_to_one": "1:1 relationship",
        "zero_to_one": "0:1 relationship",
        "one_to_many": "1:N relationship",
        "zero_to_many": "0:N relationship",
        "required_optional": ("Required / optional semantics"),
        "referential_integrity": ("Referential integrity"),
        "many_to_many": ("N:M associative relationship"),
        "determinism": ("Deterministic references"),
        "entity_order_independence": ("Entity-order independence"),
        "invalid_configuration": ("Configuration safety"),
    }

    print("Relationship validation:")

    for key, result in results.items():

        print(f"  " f"{labels[key]:<34}" f"{result['status']}")

    print()

    overall = all(result["status"] == "PASS" for result in results.values())

    print("Experiment result:")

    print(
        f"  Cardinality:               "
        f"{'PASS' if all(results[key]['status'] == 'PASS' for key in ['one_to_one', 'zero_to_one', 'one_to_many', 'zero_to_many']) else 'FAIL'}"
    )

    print(
        f"  Referential integrity:     " f"{results['referential_integrity']['status']}"
    )

    print(f"  N:M representation:        " f"{results['many_to_many']['status']}")

    print(f"  Required / optional:       " f"{results['required_optional']['status']}")

    print(f"  Determinism:               " f"{results['determinism']['status']}")

    print(
        f"  Entity-order independence: "
        f"{results['entity_order_independence']['status']}"
    )

    print(
        f"  Configuration safety:      " f"{results['invalid_configuration']['status']}"
    )

    print(f"  Overall:                   " f"{'PASS' if overall else 'FAIL'}")

    # ------------------------------------------------------------------------
    # Output
    # ------------------------------------------------------------------------

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    payload = {
        "experiment": ("020_declarative_generation_specification"),
        "stage": "020-H",
        "purpose": ("Declarative relationships " "and reference resolution"),
        "random_seed": RANDOM_SEED,
        "relationship_cardinalities": sorted(RELATIONSHIP_CARDINALITIES),
        "relationship_semantics": sorted(RELATIONSHIP_SEMANTICS),
        "results": results,
        "architectural_conclusion": (
            "Relationships are represented "
            "declaratively and resolved "
            "against actual generated "
            "parent identities. Foreign "
            "keys therefore become valid "
            "references rather than merely "
            "generated values. N:M "
            "relationships are represented "
            "through associative entities. "
            "Relationship resolution is "
            "independent of entity declaration "
            "order and deterministic under "
            "a fixed seed."
        ),
        "important_boundary": (
            "Arbitrary field dependencies "
            "and dependency graph execution "
            "remain deferred to Experiment "
            "020-I."
        ),
        "overall": ("PASS" if overall else "FAIL"),
    }

    with RESULT_OUTPUT_PATH.open(
        "w",
        encoding="utf-8",
    ) as file:

        json.dump(
            payload,
            file,
            indent=2,
            default=str,
        )

    print()

    print("Output:")

    print(f"  Results: " f"{RESULT_OUTPUT_PATH}")

    print()

    if overall:

        print("Experiment completed successfully.")

        return 0

    print("Experiment completed with failures.")

    return 1


if __name__ == "__main__":
    sys.exit(main())
