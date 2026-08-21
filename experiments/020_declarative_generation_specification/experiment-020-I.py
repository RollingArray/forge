"""
FORGE - Experiment 020-I: Declarative Dependency Graph and Generation Planning
===============================================================================

Purpose
-------
This experiment validates dependency graph construction and deterministic
generation planning from declarative entity relationships.

The experiment builds on:

    020-G  Identity and Uniqueness
    020-H  Relationships and Reference Resolution

The objective is to move from individual relationship resolution to a
generic execution plan for an entire multi-entity specification.

Stage
-----
020-I - Declarative Dependency Graph and Generation Planning

Research Question
-----------------
Can FORGE derive a safe, deterministic generation order from declarative
relationships without depending on the order in which entities appear in
the specification?

Hypothesis
----------
A generic dependency graph can be constructed from relationship
declarations and converted into a deterministic topological generation
plan.

The planner should:

    - identify dependency edges
    - derive parent-before-child ordering
    - handle multiple dependencies
    - resolve transitive dependencies
    - preserve independent entities
    - support associative entities
    - remain independent of entity declaration order
    - detect dependency cycles
    - detect invalid references
    - detect self-dependencies
    - produce a deterministic plan

Generation itself is intentionally outside the primary scope.

Scope
-----
Included:

    - dependency graph construction
    - parent-to-child dependency edges
    - topological ordering
    - multiple parent dependencies
    - transitive dependencies
    - independent entities
    - associative entities
    - entity declaration-order independence
    - cycle detection
    - self-reference detection
    - disconnected graph components
    - deterministic planning
    - blocked planning for invalid specifications

Excluded:

    - actual record generation
    - statistical generation
    - distribution execution
    - field-level formulas
    - conditional field dependencies
    - temporal dependencies
    - correlation
    - scenario execution
    - LLM specification generation

Those capabilities belong to later experiments.

Important Architectural Principle
---------------------------------
The specification defines relationships.

The dependency planner derives execution order.

The user must not have to manually specify:

    generate CUSTOMER first
    then PRODUCT
    then ORDER
    then ORDER_ITEM

Instead, FORGE should derive the order from the dependency graph.

Example:

    CUSTOMER
       |
       v
     ORDER
       |
       v
   ORDER_ITEM
       ^
       |
    PRODUCT

A valid plan could therefore be:

    CUSTOMER
    PRODUCT
    ORDER
    ORDER_ITEM

CUSTOMER and PRODUCT are independent of each other and may therefore
occupy either relative position, provided both occur before ORDER_ITEM's
dependent entities.

Determinism
-----------
Where multiple valid topological orders exist, FORGE must choose a
deterministic order.

This prevents the execution plan from changing because of:

    - dictionary ordering
    - specification field ordering
    - incidental implementation details

Cycle Safety
------------
A dependency cycle must block generation.

For example:

    A -> B
    B -> C
    C -> A

must result in:

    PLAN = BLOCKED

The planner must never attempt to invent an execution order for a
cyclic dependency graph.

Self-Reference
--------------
Self-referencing relationships are treated as dependencies that require
special handling.

This experiment does not implement recursive generation.

Therefore:

    EMPLOYEE -> EMPLOYEE

must be identified explicitly and marked as deferred or blocked rather
than silently producing an invalid plan.

Author
------
Ranjoy Sen

Status
------
Experimental

How to Run
----------
From the repository root:

    uv run python experiments/020_declarative_generation_specification/experiment-020-I.py

Output
------
Results are written to:

    experiments/020_declarative_generation_specification/output/

Important
---------
All graph definitions are synthetic and domain-neutral.
"""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

# ============================================================================
# PATHS / CONSTANTS
# ============================================================================

EXPERIMENT_DIR = Path(__file__).resolve().parent

OUTPUT_DIR = EXPERIMENT_DIR / "output"

RESULT_OUTPUT_PATH = OUTPUT_DIR / "dependency_graph_results.json"


# ============================================================================
# CONTROLLED VOCABULARY
# ============================================================================

CARDINALITIES = {
    "1:1",
    "0:1",
    "1:N",
    "0:N",
    "N:M",
}

SEMANTICS = {
    "PARENT",
    "CHILD",
    "ASSOCIATIVE",
    "REQUIRED",
    "OPTIONAL",
    "DEPENDENT",
}


# ============================================================================
# DECLARATIVE RELATIONSHIP
# ============================================================================


@dataclass(frozen=True)
class Relationship:
    """
    Minimal relationship representation required by the planner.

    The planner deliberately does not care about the business meaning
    of the entities.
    """

    name: str
    parent: str
    child: str

    parent_key: str
    child_key: str

    cardinality: str
    requirement: str

    semantics: tuple[str, ...] = ()

    associative: bool = False


# ============================================================================
# DEPENDENCY GRAPH
# ============================================================================


class DependencyGraph:
    """
    Generic directed dependency graph.

    Edge direction:

        parent -> child

    means:

        parent must be generated before child.
    """

    def __init__(
        self,
        entities: list[str],
    ) -> None:

        self.entities = set(entities)

        self.edges: dict[
            str,
            set[str],
        ] = {entity: set() for entity in entities}

        self.relationships: list[Relationship] = []

    # ------------------------------------------------------------------------
    # Add relationship
    # ------------------------------------------------------------------------

    def add_relationship(
        self,
        relationship: Relationship,
    ) -> None:

        self._validate_relationship(relationship)

        self.relationships.append(relationship)

        self.edges[relationship.parent].add(relationship.child)

    # ------------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------------

    def _validate_relationship(
        self,
        relationship: Relationship,
    ) -> None:

        if relationship.parent not in self.entities:

            raise ValueError(f"Unknown parent entity: " f"{relationship.parent}")

        if relationship.child not in self.entities:

            raise ValueError(f"Unknown child entity: " f"{relationship.child}")

        if relationship.cardinality not in CARDINALITIES:

            raise ValueError("Unsupported cardinality: " f"{relationship.cardinality}")

        if relationship.requirement not in {
            "REQUIRED",
            "OPTIONAL",
        }:

            raise ValueError("Unsupported requirement: " f"{relationship.requirement}")

        for semantic in relationship.semantics:

            if semantic not in SEMANTICS:

                raise ValueError("Unsupported relationship " f"semantic: {semantic}")

        if relationship.parent == relationship.child:

            raise ValueError(
                "Self-referencing dependency "
                f"detected for entity "
                f"'{relationship.parent}'."
            )

    # ------------------------------------------------------------------------
    # Edge list
    # ------------------------------------------------------------------------

    def edge_list(
        self,
    ) -> list[tuple[str, str]]:

        return sorted(
            (
                parent,
                child,
            )
            for parent, children in self.edges.items()
            for child in children
        )

    # ------------------------------------------------------------------------
    # Topological plan
    # ------------------------------------------------------------------------

    def topological_plan(
        self,
    ) -> list[str]:
        """
        Deterministic Kahn topological sort.

        Alphabetical ordering is used whenever multiple entities are
        simultaneously eligible for execution.
        """

        indegree: dict[
            str,
            int,
        ] = {entity: 0 for entity in self.entities}

        for parent, children in self.edges.items():

            for child in children:

                indegree[child] += 1

        ready = sorted(entity for entity, degree in indegree.items() if degree == 0)

        plan: list[str] = []

        while ready:

            current = ready.pop(0)

            plan.append(current)

            for child in sorted(self.edges[current]):

                indegree[child] -= 1

                if indegree[child] == 0:

                    ready.append(child)

            ready.sort()

        if len(plan) != len(self.entities):

            remaining = sorted(
                entity for entity, degree in indegree.items() if degree > 0
            )

            raise ValueError(
                "Dependency cycle detected. " f"Unresolved entities: " f"{remaining}"
            )

        return plan


# ============================================================================
# GENERIC PLANNER
# ============================================================================


class GenerationPlanner:
    """
    Converts declarative relationships into a generation plan.
    """

    def __init__(
        self,
        entities: list[str],
        relationships: list[Relationship],
    ) -> None:

        self.entities = list(entities)

        self.relationships = list(relationships)

    def build_graph(
        self,
    ) -> DependencyGraph:

        graph = DependencyGraph(self.entities)

        for relationship in self.relationships:

            graph.add_relationship(relationship)

        return graph

    def plan(
        self,
    ) -> dict[str, Any]:

        graph = self.build_graph()

        execution_order = graph.topological_plan()

        return {
            "status": "PASS",
            "entities": sorted(self.entities),
            "edges": graph.edge_list(),
            "execution_order": (execution_order),
        }


# ============================================================================
# HELPERS
# ============================================================================


def relationship(
    name: str,
    parent: str,
    child: str,
    cardinality: str = "1:N",
    requirement: str = "REQUIRED",
    associative: bool = False,
) -> Relationship:

    return Relationship(
        name=name,
        parent=parent,
        child=child,
        parent_key=f"{parent}_ID",
        child_key=f"{parent}_ID",
        cardinality=cardinality,
        requirement=requirement,
        semantics=(
            "PARENT",
            "CHILD",
            "REQUIRED" if requirement == "REQUIRED" else "OPTIONAL",
            "ASSOCIATIVE" if associative else "DEPENDENT",
        ),
        associative=associative,
    )


# ============================================================================
# TEST 1: SIMPLE DEPENDENCY
# ============================================================================


def test_simple_dependency() -> dict[str, Any]:

    planner = GenerationPlanner(
        entities=[
            "CUSTOMER",
            "ORDER",
        ],
        relationships=[
            relationship(
                "CUSTOMER_ORDER",
                "CUSTOMER",
                "ORDER",
            )
        ],
    )

    result = planner.plan()

    passed = result["execution_order"] == [
        "CUSTOMER",
        "ORDER",
    ]

    return {
        "status": ("PASS" if passed else "FAIL"),
        "plan": result,
    }


# ============================================================================
# TEST 2: MULTI-LEVEL DEPENDENCY
# ============================================================================


def test_transitive_dependency() -> dict[str, Any]:

    planner = GenerationPlanner(
        entities=[
            "CUSTOMER",
            "ORDER",
            "ORDER_ITEM",
        ],
        relationships=[
            relationship(
                "CUSTOMER_ORDER",
                "CUSTOMER",
                "ORDER",
            ),
            relationship(
                "ORDER_ITEM",
                "ORDER",
                "ORDER_ITEM",
            ),
        ],
    )

    result = planner.plan()

    order = result["execution_order"]

    passed = order.index("CUSTOMER") < order.index("ORDER") < order.index("ORDER_ITEM")

    return {
        "status": ("PASS" if passed else "FAIL"),
        "plan": result,
    }


# ============================================================================
# TEST 3: MULTIPLE PARENTS
# ============================================================================


def test_multiple_dependencies() -> dict[str, Any]:

    planner = GenerationPlanner(
        entities=[
            "CUSTOMER",
            "PRODUCT",
            "ORDER",
            "ORDER_ITEM",
        ],
        relationships=[
            relationship(
                "CUSTOMER_ORDER",
                "CUSTOMER",
                "ORDER",
            ),
            relationship(
                "ORDER_ITEM_ORDER",
                "ORDER",
                "ORDER_ITEM",
            ),
            relationship(
                "PRODUCT_ORDER_ITEM",
                "PRODUCT",
                "ORDER_ITEM",
            ),
        ],
    )

    result = planner.plan()

    order = result["execution_order"]

    passed = (
        order.index("CUSTOMER") < order.index("ORDER")
        and order.index("PRODUCT") < order.index("ORDER_ITEM")
        and order.index("ORDER") < order.index("ORDER_ITEM")
    )

    return {
        "status": ("PASS" if passed else "FAIL"),
        "plan": result,
    }


# ============================================================================
# TEST 4: INDEPENDENT ENTITIES
# ============================================================================


def test_independent_entities() -> dict[str, Any]:

    planner = GenerationPlanner(
        entities=[
            "CUSTOMER",
            "PRODUCT",
            "COUNTRY",
        ],
        relationships=[],
    )

    result = planner.plan()

    passed = result["execution_order"] == [
        "COUNTRY",
        "CUSTOMER",
        "PRODUCT",
    ]

    return {
        "status": ("PASS" if passed else "FAIL"),
        "plan": result,
    }


# ============================================================================
# TEST 5: ASSOCIATIVE ENTITY
# ============================================================================


def test_associative_entity() -> dict[str, Any]:

    planner = GenerationPlanner(
        entities=[
            "ORDER",
            "PRODUCT",
            "ORDER_ITEM",
        ],
        relationships=[
            relationship(
                "ORDER_ORDER_ITEM",
                "ORDER",
                "ORDER_ITEM",
                associative=True,
            ),
            relationship(
                "PRODUCT_ORDER_ITEM",
                "PRODUCT",
                "ORDER_ITEM",
                associative=True,
            ),
        ],
    )

    result = planner.plan()

    order = result["execution_order"]

    passed = order.index("ORDER") < order.index("ORDER_ITEM") and order.index(
        "PRODUCT"
    ) < order.index("ORDER_ITEM")

    return {
        "status": ("PASS" if passed else "FAIL"),
        "plan": result,
    }


# ============================================================================
# TEST 6: OPTIONAL RELATIONSHIP
# ============================================================================


def test_optional_dependency() -> dict[str, Any]:

    planner = GenerationPlanner(
        entities=[
            "ORDER",
            "SHIPMENT",
        ],
        relationships=[
            relationship(
                "ORDER_SHIPMENT",
                "ORDER",
                "SHIPMENT",
                cardinality="0:1",
                requirement="OPTIONAL",
            )
        ],
    )

    result = planner.plan()

    order = result["execution_order"]

    passed = order.index("ORDER") < order.index("SHIPMENT")

    return {
        "status": ("PASS" if passed else "FAIL"),
        "plan": result,
    }


# ============================================================================
# TEST 7: ENTITY DECLARATION ORDER
# ============================================================================


def test_entity_order_independence() -> dict[str, Any]:

    relationships = [
        relationship(
            "CUSTOMER_ORDER",
            "CUSTOMER",
            "ORDER",
        ),
        relationship(
            "ORDER_ITEM_ORDER",
            "ORDER",
            "ORDER_ITEM",
        ),
        relationship(
            "PRODUCT_ORDER_ITEM",
            "PRODUCT",
            "ORDER_ITEM",
        ),
    ]

    planner_a = GenerationPlanner(
        entities=[
            "CUSTOMER",
            "PRODUCT",
            "ORDER",
            "ORDER_ITEM",
        ],
        relationships=relationships,
    )

    planner_b = GenerationPlanner(
        entities=[
            "ORDER_ITEM",
            "ORDER",
            "PRODUCT",
            "CUSTOMER",
        ],
        relationships=relationships,
    )

    plan_a = planner_a.plan()
    plan_b = planner_b.plan()

    passed = plan_a["execution_order"] == plan_b["execution_order"]

    return {
        "status": ("PASS" if passed else "FAIL"),
        "plan_a": plan_a,
        "plan_b": plan_b,
    }


# ============================================================================
# TEST 8: DETERMINISM
# ============================================================================


def test_determinism() -> dict[str, Any]:

    relationships = [
        relationship(
            "CUSTOMER_ORDER",
            "CUSTOMER",
            "ORDER",
        ),
        relationship(
            "ORDER_ITEM_ORDER",
            "ORDER",
            "ORDER_ITEM",
        ),
        relationship(
            "PRODUCT_ORDER_ITEM",
            "PRODUCT",
            "ORDER_ITEM",
        ),
    ]

    first = GenerationPlanner(
        entities=[
            "CUSTOMER",
            "PRODUCT",
            "ORDER",
            "ORDER_ITEM",
        ],
        relationships=relationships,
    ).plan()

    second = GenerationPlanner(
        entities=[
            "CUSTOMER",
            "PRODUCT",
            "ORDER",
            "ORDER_ITEM",
        ],
        relationships=relationships,
    ).plan()

    passed = first["execution_order"] == second["execution_order"]

    return {
        "status": ("PASS" if passed else "FAIL"),
        "first": first["execution_order"],
        "second": second["execution_order"],
    }


# ============================================================================
# TEST 9: CYCLE DETECTION
# ============================================================================


def test_cycle_detection() -> dict[str, Any]:

    planner = GenerationPlanner(
        entities=[
            "A",
            "B",
            "C",
        ],
        relationships=[
            relationship(
                "A_B",
                "A",
                "B",
            ),
            relationship(
                "B_C",
                "B",
                "C",
            ),
            relationship(
                "C_A",
                "C",
                "A",
            ),
        ],
    )

    try:

        planner.plan()

        passed = False

        error = "Cycle was not detected."

    except ValueError as exc:

        passed = "cycle" in str(exc).lower()

        error = str(exc)

    return {
        "status": ("PASS" if passed else "FAIL"),
        "error": error,
    }


# ============================================================================
# TEST 10: SELF REFERENCE
# ============================================================================


def test_self_reference() -> dict[str, Any]:

    planner = GenerationPlanner(
        entities=[
            "EMPLOYEE",
        ],
        relationships=[
            relationship(
                "EMPLOYEE_MANAGER",
                "EMPLOYEE",
                "EMPLOYEE",
            )
        ],
    )

    try:

        planner.plan()

        passed = False

        error = "Self-reference was not blocked."

    except ValueError as exc:

        passed = "self" in str(exc).lower()

        error = str(exc)

    return {
        "status": ("PASS" if passed else "FAIL"),
        "error": error,
    }


# ============================================================================
# TEST 11: UNKNOWN ENTITY
# ============================================================================


def test_unknown_entity() -> dict[str, Any]:

    planner = GenerationPlanner(
        entities=[
            "CUSTOMER",
            "ORDER",
        ],
        relationships=[
            relationship(
                "UNKNOWN_ORDER",
                "UNKNOWN",
                "ORDER",
            )
        ],
    )

    try:

        planner.plan()

        passed = False

        error = "Unknown entity was not blocked."

    except ValueError as exc:

        passed = "unknown" in str(exc).lower()

        error = str(exc)

    return {
        "status": ("PASS" if passed else "FAIL"),
        "error": error,
    }


# ============================================================================
# TEST 12: INVALID CARDINALITY
# ============================================================================


def test_invalid_cardinality() -> dict[str, Any]:

    planner = GenerationPlanner(
        entities=[
            "CUSTOMER",
            "ORDER",
        ],
        relationships=[
            relationship(
                "INVALID",
                "CUSTOMER",
                "ORDER",
                cardinality="X:Y",
            )
        ],
    )

    try:

        planner.plan()

        passed = False

        error = "Invalid cardinality " "was not blocked."

    except ValueError as exc:

        passed = "cardinality" in str(exc).lower()

        error = str(exc)

    return {
        "status": ("PASS" if passed else "FAIL"),
        "error": error,
    }


# ============================================================================
# TEST 13: DISCONNECTED COMPONENTS
# ============================================================================


def test_disconnected_components() -> dict[str, Any]:

    planner = GenerationPlanner(
        entities=[
            "CUSTOMER",
            "ORDER",
            "PRODUCT",
            "SUPPLIER",
        ],
        relationships=[
            relationship(
                "CUSTOMER_ORDER",
                "CUSTOMER",
                "ORDER",
            ),
            relationship(
                "SUPPLIER_PRODUCT",
                "SUPPLIER",
                "PRODUCT",
            ),
        ],
    )

    result = planner.plan()

    order = result["execution_order"]

    passed = order.index("CUSTOMER") < order.index("ORDER") and order.index(
        "SUPPLIER"
    ) < order.index("PRODUCT")

    return {
        "status": ("PASS" if passed else "FAIL"),
        "plan": result,
    }


# ============================================================================
# TEST 14: FULL END-TO-END GRAPH
# ============================================================================


def test_full_graph() -> dict[str, Any]:

    entities = [
        "CUSTOMER",
        "CUSTOMER_PROFILE",
        "PRODUCT",
        "ORDER",
        "ORDER_ITEM",
        "SHIPMENT",
    ]

    relationships = [
        relationship(
            "CUSTOMER_PROFILE",
            "CUSTOMER",
            "CUSTOMER_PROFILE",
            cardinality="0:1",
            requirement="OPTIONAL",
        ),
        relationship(
            "CUSTOMER_ORDER",
            "CUSTOMER",
            "ORDER",
        ),
        relationship(
            "ORDER_ITEM_ORDER",
            "ORDER",
            "ORDER_ITEM",
            associative=True,
        ),
        relationship(
            "PRODUCT_ORDER_ITEM",
            "PRODUCT",
            "ORDER_ITEM",
            associative=True,
        ),
        relationship(
            "ORDER_SHIPMENT",
            "ORDER",
            "SHIPMENT",
            cardinality="0:1",
            requirement="OPTIONAL",
        ),
    ]

    planner = GenerationPlanner(
        entities=entities,
        relationships=relationships,
    )

    result = planner.plan()

    order = result["execution_order"]

    passed = (
        order.index("CUSTOMER") < order.index("CUSTOMER_PROFILE")
        and order.index("CUSTOMER") < order.index("ORDER")
        and order.index("PRODUCT") < order.index("ORDER_ITEM")
        and order.index("ORDER") < order.index("ORDER_ITEM")
        and order.index("ORDER") < order.index("SHIPMENT")
    )

    return {
        "status": ("PASS" if passed else "FAIL"),
        "plan": result,
    }


# ============================================================================
# MAIN
# ============================================================================


def main() -> int:

    print()

    print("=" * 70)

    print(
        "FORGE - Experiment 020-I: "
        "Declarative Dependency Graph and Generation Planning"
    )

    print("=" * 70)

    print("Experiment:     " "020_declarative_generation_specification")

    print("Stage:          020-I")

    print("Purpose:        " "Declarative dependency graph and generation planning")

    print()

    print("Graph semantics:")

    print("  Edge direction: parent -> child")

    print("  Meaning: parent must be generated " "before child")

    print()

    tests = {
        "simple_dependency": (test_simple_dependency()),
        "transitive_dependency": (test_transitive_dependency()),
        "multiple_dependencies": (test_multiple_dependencies()),
        "independent_entities": (test_independent_entities()),
        "associative_entity": (test_associative_entity()),
        "optional_dependency": (test_optional_dependency()),
        "entity_order_independence": (test_entity_order_independence()),
        "determinism": (test_determinism()),
        "cycle_detection": (test_cycle_detection()),
        "self_reference": (test_self_reference()),
        "unknown_entity": (test_unknown_entity()),
        "invalid_cardinality": (test_invalid_cardinality()),
        "disconnected_components": (test_disconnected_components()),
        "full_graph": (test_full_graph()),
    }

    labels = {
        "simple_dependency": "Simple dependency",
        "transitive_dependency": "Transitive dependency",
        "multiple_dependencies": "Multiple dependencies",
        "independent_entities": "Independent entities",
        "associative_entity": "Associative entity",
        "optional_dependency": "Optional dependency",
        "entity_order_independence": "Entity-order independence",
        "determinism": "Deterministic planning",
        "cycle_detection": "Cycle detection",
        "self_reference": "Self-reference safety",
        "unknown_entity": "Unknown entity safety",
        "invalid_cardinality": "Cardinality validation",
        "disconnected_components": "Disconnected components",
        "full_graph": "Full end-to-end graph",
    }

    print("Dependency graph validation:")

    for key, result in tests.items():

        print(f"  " f"{labels[key]:<34}" f"{result['status']}")

    print()

    passed_count = sum(result["status"] == "PASS" for result in tests.values())

    total_count = len(tests)

    overall = passed_count == total_count

    print("Experiment result:")

    print(
        f"  Dependency graph:          "
        f"{'PASS' if all(tests[key]['status'] == 'PASS' for key in ['simple_dependency', 'transitive_dependency', 'multiple_dependencies']) else 'FAIL'}"
    )

    print(
        f"  Topological planning:      "
        f"{'PASS' if tests['full_graph']['status'] == 'PASS' else 'FAIL'}"
    )

    print(f"  Determinism:               " f"{tests['determinism']['status']}")

    print(
        f"  Entity-order independence: "
        f"{tests['entity_order_independence']['status']}"
    )

    print(f"  Cycle safety:              " f"{tests['cycle_detection']['status']}")

    print(f"  Self-reference safety:     " f"{tests['self_reference']['status']}")

    print(
        f"  Configuration safety:      "
        f"{'PASS' if all(tests[key]['status'] == 'PASS' for key in ['unknown_entity', 'invalid_cardinality']) else 'FAIL'}"
    )

    print(f"  Tests passed:              " f"{passed_count}/{total_count}")

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
        "stage": "020-I",
        "purpose": ("Declarative dependency graph " "and generation planning"),
        "edge_semantics": ("parent -> child"),
        "tests": tests,
        "tests_passed": passed_count,
        "tests_total": total_count,
        "architectural_conclusion": (
            "FORGE can derive a deterministic "
            "generation order from declarative "
            "entity relationships. Parent "
            "entities are planned before "
            "dependent entities. Independent "
            "entities remain valid graph "
            "components. Cyclic and invalid "
            "dependencies are rejected rather "
            "than silently producing an unsafe "
            "generation plan."
        ),
        "important_boundary": (
            "This experiment produces an "
            "execution plan but does not "
            "execute record generation. "
            "Actual execution orchestration "
            "will be addressed after the "
            "dependency model is established."
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
