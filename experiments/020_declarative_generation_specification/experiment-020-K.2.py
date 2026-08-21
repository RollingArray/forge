"""
FORGE - Experiment 020-K.2: Constraint-Driven Generation Planning
==================================================================

Stage:
    020-K.2

Purpose:
    Validate that cross-field declarative constraints can be translated
    into generation dependencies and executed through context-aware
    generation.

Research Question
-----------------
Can FORGE transform cross-field declarative constraints into a
generation plan that determines:

    1. which fields must be generated first
    2. which fields depend on earlier values
    3. the feasible range for dependent fields
    4. whether the specification is safely executable

The experiment specifically tests whether FORGE can generate valid
dependent values directly rather than generating arbitrary values
and repairing them afterward.

Architectural Principle
-----------------------
A cross-field constraint is not merely a validation rule.

For example:

    A <= B

must be capable of producing a generation relationship:

    A
    |
    +----> B

where B is generated using the already-generated value of A.

The intended execution model is:

    Specification
         |
         v
    Constraint Extraction
         |
         v
    Constraint Graph
         |
         v
    Generation Planning
         |
         v
    Context-Aware Generation
         |
         v
    Constraint Validation

The experiment explicitly rejects:

    Independent Generation
         |
         v
    Post-Generation Repair

Scope
-----
Included:

    - A <= B
    - A < B
    - A <= B <= C
    - chained dependencies
    - dependency ordering independent of field declaration order
    - dependent feasible ranges
    - deterministic generation
    - seed sensitivity
    - cyclic constraint detection
    - impossible dependency detection
    - final constraint validation

Excluded:

    - arbitrary symbolic mathematics
    - SAT / SMT solving
    - general optimization
    - statistical correlation
    - relationship-level generation
    - categorical conditional constraints

Important Boundary
------------------
The planner supports a bounded family of numeric ordering constraints.

If FORGE cannot safely derive a generation strategy, it must return:

    BLOCKED

rather than guessing.

Status:
    Experimental
"""

from __future__ import annotations

import hashlib
import json
import random
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

# ============================================================================
# PATHS
# ============================================================================

EXPERIMENT_DIR = Path(__file__).resolve().parent

OUTPUT_DIR = EXPERIMENT_DIR / "output"

RESULT_OUTPUT_PATH = OUTPUT_DIR / "constraint_driven_generation_results.json"

MASTER_SEED = 42


# ============================================================================
# CONSTANTS
# ============================================================================

LESS_THAN = "LESS_THAN"
LESS_OR_EQUAL = "LESS_OR_EQUAL"


# ============================================================================
# MODELS
# ============================================================================


@dataclass(frozen=True)
class FieldSpec:
    name: str
    minimum: float
    maximum: float
    type: str = "DECIMAL"


@dataclass(frozen=True)
class Constraint:
    constraint_id: str
    left_field: str
    right_field: str
    operator: str


@dataclass(frozen=True)
class EntitySpec:
    name: str
    record_count: int
    fields: tuple[FieldSpec, ...]
    constraints: tuple[Constraint, ...]


@dataclass
class GenerationStep:
    field: str
    dependencies: tuple[str, ...]
    minimum: float | None
    maximum: float | None
    strategy: str


# ============================================================================
# DETERMINISTIC STREAMS
# ============================================================================


def stable_seed(
    master_seed: int,
    entity: str,
    field: str,
) -> int:

    material = (f"{master_seed}:" f"{entity}:" f"{field}").encode("utf-8")

    digest = hashlib.sha256(material).digest()

    return int.from_bytes(
        digest[:8],
        byteorder="big",
        signed=False,
    )


def field_rng(
    master_seed: int,
    entity: str,
    field: str,
) -> random.Random:

    return random.Random(
        stable_seed(
            master_seed,
            entity,
            field,
        )
    )


# ============================================================================
# CONSTRAINT GRAPH
# ============================================================================


class ConstraintGraph:
    """
    Directed graph representing generation dependencies.

    Edge:

        A -> B

    means:

        B depends on A

    because a constraint such as:

        A <= B

    requires B to be generated with knowledge of A.
    """

    def __init__(
        self,
        entity: EntitySpec,
    ) -> None:

        self.entity = entity

        self.nodes = {field.name for field in entity.fields}

        self.edges: dict[
            str,
            set[str],
        ] = {node: set() for node in self.nodes}

        self.reverse_edges: dict[
            str,
            set[str],
        ] = {node: set() for node in self.nodes}

        self.invalid_constraints: list[dict[str, Any]] = []

        self._build()

    def _build(self) -> None:

        for constraint in self.entity.constraints:

            if constraint.left_field not in self.nodes:

                self.invalid_constraints.append(
                    {
                        "constraint": (constraint.constraint_id),
                        "reason": ("Unknown left field"),
                    }
                )

                continue

            if constraint.right_field not in self.nodes:

                self.invalid_constraints.append(
                    {
                        "constraint": (constraint.constraint_id),
                        "reason": ("Unknown right field"),
                    }
                )

                continue

            if constraint.operator not in {
                LESS_THAN,
                LESS_OR_EQUAL,
            }:

                self.invalid_constraints.append(
                    {
                        "constraint": (constraint.constraint_id),
                        "reason": ("Unsupported ordering operator"),
                    }
                )

                continue

            if constraint.left_field == constraint.right_field:

                self.invalid_constraints.append(
                    {
                        "constraint": (constraint.constraint_id),
                        "reason": ("Self dependency"),
                    }
                )

                continue

            # A <= B means:
            #
            #     generate A first
            #     generate B using A
            #
            self.edges[constraint.left_field].add(constraint.right_field)

            self.reverse_edges[constraint.right_field].add(constraint.left_field)

    # ------------------------------------------------------------------
    # Cycle detection
    # ------------------------------------------------------------------

    def detect_cycle(self) -> bool:

        visiting: set[str] = set()
        visited: set[str] = set()

        def visit(
            node: str,
        ) -> bool:

            if node in visiting:
                return True

            if node in visited:
                return False

            visiting.add(node)

            for child in sorted(self.edges[node]):

                if visit(child):
                    return True

            visiting.remove(node)

            visited.add(node)

            return False

        return any(visit(node) for node in sorted(self.nodes))

    # ------------------------------------------------------------------
    # Topological generation order
    # ------------------------------------------------------------------

    def generation_order(
        self,
    ) -> list[str] | None:

        if self.invalid_constraints:
            return None

        if self.detect_cycle():
            return None

        incoming = {node: len(self.reverse_edges[node]) for node in self.nodes}

        ready = sorted(node for node, degree in incoming.items() if degree == 0)

        order: list[str] = []

        while ready:

            node = ready.pop(0)

            order.append(node)

            for child in sorted(self.edges[node]):

                incoming[child] -= 1

                if incoming[child] == 0:

                    ready.append(child)

                    ready.sort()

        if len(order) != len(self.nodes):

            return None

        return order


# ============================================================================
# GENERATION PLANNER
# ============================================================================


class ConstraintGenerationPlanner:
    """
    Converts a constraint graph into generation steps.

    The planner determines whether a field is:

        INDEPENDENT
        DEPENDENT
    """

    def __init__(
        self,
        entity: EntitySpec,
    ) -> None:

        self.entity = entity

        self.fields = {field.name: field for field in entity.fields}

        self.constraints = entity.constraints

    def plan(
        self,
    ) -> dict[str, Any]:

        graph = ConstraintGraph(self.entity)

        order = graph.generation_order()

        if order is None:

            return {
                "status": "BLOCKED",
                "reason": ("Generation dependency graph " "is invalid or cyclic."),
                "invalid_constraints": (graph.invalid_constraints),
            }

        steps: list[GenerationStep] = []

        for field_name in order:

            field = self.fields[field_name]

            dependencies = tuple(sorted(graph.reverse_edges[field_name]))

            strategy = "CONTEXT_AWARE" if dependencies else "INDEPENDENT"

            steps.append(
                GenerationStep(
                    field=field_name,
                    dependencies=dependencies,
                    minimum=field.minimum,
                    maximum=field.maximum,
                    strategy=strategy,
                )
            )

        return {
            "status": "PASS",
            "order": order,
            "steps": [
                {
                    "field": step.field,
                    "dependencies": (list(step.dependencies)),
                    "minimum": step.minimum,
                    "maximum": step.maximum,
                    "strategy": step.strategy,
                }
                for step in steps
            ],
            "edges": {
                node: sorted(children)
                for node, children in graph.edges.items()
                if children
            },
        }


# ============================================================================
# CONTEXT-AWARE GENERATOR
# ============================================================================


class ConstraintDrivenGenerator:
    """
    Generates fields according to the generation plan.

    Dependent fields are generated using the values already present
    in the current record.

    No post-generation repair is performed.
    """

    def __init__(
        self,
        seed: int,
    ) -> None:

        self.seed = seed

    def generate(
        self,
        entity: EntitySpec,
    ) -> dict[str, Any]:

        planner = ConstraintGenerationPlanner(entity)

        plan = planner.plan()

        if plan["status"] != "PASS":

            return {
                "status": "BLOCKED",
                "plan": plan,
            }

        field_map = {field.name: field for field in entity.fields}

        records = [{} for _ in range(entity.record_count)]

        for field_name in plan["order"]:

            field = field_map[field_name]

            dependencies = self._dependencies(
                entity,
                field_name,
            )

            for index, record in enumerate(records):

                rng = field_rng(
                    self.seed,
                    entity.name,
                    field_name,
                )

                minimum = field.minimum
                maximum = field.maximum

                # ------------------------------------------------------
                # Context-aware bounds
                # ------------------------------------------------------

                for dependency in dependencies:

                    dependency_value = record[dependency]

                    constraint = self._find_constraint(
                        entity,
                        dependency,
                        field_name,
                    )

                    if constraint is None:
                        continue

                    if constraint.operator == LESS_OR_EQUAL:

                        minimum = max(
                            minimum,
                            dependency_value,
                        )

                    elif constraint.operator == LESS_THAN:

                        minimum = max(
                            minimum,
                            dependency_value + self._epsilon(field),
                        )

                # ------------------------------------------------------
                # Feasibility check
                # ------------------------------------------------------

                if minimum > maximum:

                    return {
                        "status": "BLOCKED",
                        "plan": plan,
                        "reason": (
                            f"No feasible generation " f"range for {field_name}"
                        ),
                        "record_index": index,
                        "minimum": minimum,
                        "maximum": maximum,
                    }

                # ------------------------------------------------------
                # Direct feasible generation
                # ------------------------------------------------------

                if field.type == "INTEGER":

                    low = int(minimum)

                    high = int(maximum)

                    if low > high:

                        return {
                            "status": "BLOCKED",
                            "plan": plan,
                            "reason": ("Integer feasible " "range is empty."),
                            "field": field_name,
                        }

                    value = rng.randint(
                        low,
                        high,
                    )

                else:

                    value = round(
                        rng.uniform(
                            float(minimum),
                            float(maximum),
                        ),
                        2,
                    )

                record[field_name] = value

        validation = validate_records(
            entity,
            records,
        )

        return {
            "status": ("PASS" if validation["status"] == "PASS" else "FAIL"),
            "plan": plan,
            "records": records,
            "validation": validation,
        }

    @staticmethod
    def _epsilon(
        field: FieldSpec,
    ) -> float:

        if field.type == "INTEGER":
            return 1

        return 0.01

    @staticmethod
    def _dependencies(
        entity: EntitySpec,
        field_name: str,
    ) -> list[str]:

        dependencies = []

        for constraint in entity.constraints:

            if constraint.right_field == field_name:

                dependencies.append(constraint.left_field)

        return sorted(set(dependencies))

    @staticmethod
    def _find_constraint(
        entity: EntitySpec,
        left_field: str,
        right_field: str,
    ) -> Constraint | None:

        for constraint in entity.constraints:

            if (
                constraint.left_field == left_field
                and constraint.right_field == right_field
            ):

                return constraint

        return None


# ============================================================================
# VALIDATION
# ============================================================================


def validate_records(
    entity: EntitySpec,
    records: list[dict[str, Any]],
) -> dict[str, Any]:

    failures = []

    for index, record in enumerate(records):

        for constraint in entity.constraints:

            left = record[constraint.left_field]

            right = record[constraint.right_field]

            if constraint.operator == LESS_OR_EQUAL:

                valid = left <= right

            elif constraint.operator == LESS_THAN:

                valid = left < right

            else:

                valid = False

            if not valid:

                failures.append(
                    {
                        "record": index,
                        "constraint": (constraint.constraint_id),
                        "left": left,
                        "right": right,
                    }
                )

    return {
        "status": ("PASS" if not failures else "FAIL"),
        "records_checked": len(records),
        "failures": failures,
    }


# ============================================================================
# TEST FIXTURES
# ============================================================================


def simple_entity() -> EntitySpec:

    return EntitySpec(
        name="SIMPLE",
        record_count=100,
        fields=(
            FieldSpec(
                name="A",
                minimum=100,
                maximum=1000,
            ),
            FieldSpec(
                name="B",
                minimum=200,
                maximum=2000,
            ),
        ),
        constraints=(
            Constraint(
                constraint_id="C001",
                left_field="A",
                right_field="B",
                operator=LESS_OR_EQUAL,
            ),
        ),
    )


def chained_entity() -> EntitySpec:

    return EntitySpec(
        name="CHAINED",
        record_count=100,
        fields=(
            FieldSpec(
                name="A",
                minimum=100,
                maximum=1000,
            ),
            FieldSpec(
                name="B",
                minimum=200,
                maximum=2000,
            ),
            FieldSpec(
                name="C",
                minimum=300,
                maximum=3000,
            ),
        ),
        constraints=(
            Constraint(
                constraint_id="C010",
                left_field="A",
                right_field="B",
                operator=LESS_OR_EQUAL,
            ),
            Constraint(
                constraint_id="C011",
                left_field="B",
                right_field="C",
                operator=LESS_OR_EQUAL,
            ),
        ),
    )


def strict_chain_entity() -> EntitySpec:

    return EntitySpec(
        name="STRICT_CHAIN",
        record_count=100,
        fields=(
            FieldSpec(
                name="A",
                minimum=10,
                maximum=100,
                type="INTEGER",
            ),
            FieldSpec(
                name="B",
                minimum=20,
                maximum=200,
                type="INTEGER",
            ),
            FieldSpec(
                name="C",
                minimum=30,
                maximum=300,
                type="INTEGER",
            ),
        ),
        constraints=(
            Constraint(
                constraint_id="C020",
                left_field="A",
                right_field="B",
                operator=LESS_THAN,
            ),
            Constraint(
                constraint_id="C021",
                left_field="B",
                right_field="C",
                operator=LESS_THAN,
            ),
        ),
    )


def cyclic_entity() -> EntitySpec:

    return EntitySpec(
        name="CYCLIC",
        record_count=10,
        fields=(
            FieldSpec(
                name="A",
                minimum=0,
                maximum=100,
            ),
            FieldSpec(
                name="B",
                minimum=0,
                maximum=100,
            ),
        ),
        constraints=(
            Constraint(
                constraint_id="X001",
                left_field="A",
                right_field="B",
                operator=LESS_OR_EQUAL,
            ),
            Constraint(
                constraint_id="X002",
                left_field="B",
                right_field="A",
                operator=LESS_OR_EQUAL,
            ),
        ),
    )


def impossible_entity() -> EntitySpec:

    return EntitySpec(
        name="IMPOSSIBLE",
        record_count=10,
        fields=(
            FieldSpec(
                name="A",
                minimum=900,
                maximum=1000,
            ),
            FieldSpec(
                name="B",
                minimum=0,
                maximum=500,
            ),
        ),
        constraints=(
            Constraint(
                constraint_id="X010",
                left_field="A",
                right_field="B",
                operator=LESS_OR_EQUAL,
            ),
        ),
    )


# ============================================================================
# TEST HELPERS
# ============================================================================


def run_test(
    name: str,
    function,
) -> dict[str, Any]:

    try:

        result = function()

        return {
            "name": name,
            **result,
        }

    except Exception as exc:

        return {
            "name": name,
            "status": "FAIL",
            "error": str(exc),
        }


# ============================================================================
# TESTS
# ============================================================================


def test_simple_dependency() -> dict[str, Any]:

    entity = simple_entity()

    plan = ConstraintGenerationPlanner(entity).plan()

    passed = (
        plan["status"] == "PASS"
        and plan["order"].index("A") < plan["order"].index("B")
        and "A"
        in next(step["dependencies"] for step in plan["steps"] if step["field"] == "B")
    )

    return {
        "status": ("PASS" if passed else "FAIL"),
        "plan": plan,
    }


def test_simple_generation() -> dict[str, Any]:

    result = ConstraintDrivenGenerator(MASTER_SEED).generate(simple_entity())

    passed = (
        result["status"] == "PASS"
        and result["validation"]["status"] == "PASS"
        and all(record["A"] <= record["B"] for record in result["records"])
    )

    return {
        "status": ("PASS" if passed else "FAIL"),
        "validation": result.get("validation"),
    }


def test_chained_dependency() -> dict[str, Any]:

    result = ConstraintDrivenGenerator(MASTER_SEED).generate(chained_entity())

    passed = (
        result["status"] == "PASS"
        and result["validation"]["status"] == "PASS"
        and all(
            record["A"] <= record["B"] <= record["C"] for record in result["records"]
        )
    )

    return {
        "status": ("PASS" if passed else "FAIL"),
        "order": result.get(
            "plan",
            {},
        ).get("order"),
    }


def test_strict_chain() -> dict[str, Any]:

    result = ConstraintDrivenGenerator(MASTER_SEED).generate(strict_chain_entity())

    passed = (
        result["status"] == "PASS"
        and result["validation"]["status"] == "PASS"
        and all(record["A"] < record["B"] < record["C"] for record in result["records"])
    )

    return {
        "status": ("PASS" if passed else "FAIL"),
        "validation": result.get("validation"),
    }


def test_cycle_blocking() -> dict[str, Any]:

    plan = ConstraintGenerationPlanner(cyclic_entity()).plan()

    passed = plan["status"] == "BLOCKED"

    return {
        "status": ("PASS" if passed else "FAIL"),
        "reason": plan.get("reason"),
    }


def test_impossible_generation() -> dict[str, Any]:

    result = ConstraintDrivenGenerator(MASTER_SEED).generate(impossible_entity())

    # The planner itself is valid, but once A is generated there is no
    # feasible B range. Generation must therefore block safely.
    passed = result["status"] == "BLOCKED"

    return {
        "status": ("PASS" if passed else "FAIL"),
        "reason": result.get("reason"),
    }


def test_field_order_independence() -> dict[str, Any]:

    original = chained_entity()

    reversed_entity = EntitySpec(
        name=original.name,
        record_count=original.record_count,
        fields=tuple(reversed(original.fields)),
        constraints=tuple(reversed(original.constraints)),
    )

    first = ConstraintDrivenGenerator(MASTER_SEED).generate(original)

    second = ConstraintDrivenGenerator(MASTER_SEED).generate(reversed_entity)

    passed = first["records"] == second["records"]

    return {
        "status": ("PASS" if passed else "FAIL"),
        "identical": passed,
    }


def test_reproducibility() -> dict[str, Any]:

    entity = chained_entity()

    first = ConstraintDrivenGenerator(MASTER_SEED).generate(entity)

    second = ConstraintDrivenGenerator(MASTER_SEED).generate(entity)

    passed = first["records"] == second["records"]

    return {
        "status": ("PASS" if passed else "FAIL"),
        "identical": passed,
    }


def test_seed_sensitivity() -> dict[str, Any]:

    entity = chained_entity()

    first = ConstraintDrivenGenerator(42).generate(entity)

    second = ConstraintDrivenGenerator(43).generate(entity)

    passed = first["records"] != second["records"]

    return {
        "status": ("PASS" if passed else "FAIL"),
        "different": passed,
    }


def test_no_repair() -> dict[str, Any]:

    entity = chained_entity()

    result = ConstraintDrivenGenerator(MASTER_SEED).generate(entity)

    # We validate that dependent values were generated from context.
    # For every record, B must have been generated after A and C after B.
    order = result["plan"]["order"]

    records = result["records"]

    passed = order.index("A") < order.index("B") < order.index("C") and all(
        record["A"] <= record["B"] <= record["C"] for record in records
    )

    return {
        "status": ("PASS" if passed else "FAIL"),
        "generation_order": order,
    }


# ============================================================================
# MAIN
# ============================================================================


def main() -> int:

    print()

    print("=" * 70)

    print("FORGE - Experiment 020-K.2: " "Constraint-Driven Generation Planning")

    print("=" * 70)

    print("Experiment:     " "020_declarative_generation_specification")

    print("Stage:          020-K.2")

    print("Purpose:        " "Constraint-driven generation planning")

    print(f"Random seed:    {MASTER_SEED}")

    print()

    print("Generation architecture:")

    print("  Specification")

    print("       ↓")

    print("  Constraint extraction")

    print("       ↓")

    print("  Constraint graph")

    print("       ↓")

    print("  Generation planning")

    print("       ↓")

    print("  Context-aware generation")

    print("       ↓")

    print("  Constraint validation")

    print()

    tests = [
        run_test(
            "Simple dependency planning",
            test_simple_dependency,
        ),
        run_test(
            "Simple constraint generation",
            test_simple_generation,
        ),
        run_test(
            "Chained dependency generation",
            test_chained_dependency,
        ),
        run_test(
            "Strict ordering generation",
            test_strict_chain,
        ),
        run_test(
            "Cycle blocking",
            test_cycle_blocking,
        ),
        run_test(
            "Impossible generation blocking",
            test_impossible_generation,
        ),
        run_test(
            "Field-order independence",
            test_field_order_independence,
        ),
        run_test(
            "Reproducibility",
            test_reproducibility,
        ),
        run_test(
            "Seed sensitivity",
            test_seed_sensitivity,
        ),
        run_test(
            "No post-generation repair",
            test_no_repair,
        ),
    ]

    print("Constraint-driven generation validation:")

    for test in tests:

        print(f"  " f"{test['name']:<38}" f"{test['status']}")

    passed = sum(test["status"] == "PASS" for test in tests)

    total = len(tests)

    overall = passed == total

    print()

    print("Experiment result:")

    print(f"  Dependency planning:          " f"{tests[0]['status']}")

    print(f"  Simple generation:            " f"{tests[1]['status']}")

    print(f"  Chained generation:           " f"{tests[2]['status']}")

    print(f"  Strict ordering:              " f"{tests[3]['status']}")

    print(f"  Cycle safety:                 " f"{tests[4]['status']}")

    print(f"  Impossible constraints:       " f"{tests[5]['status']}")

    print(f"  Field-order independence:      " f"{tests[6]['status']}")

    print(f"  Reproducibility:               " f"{tests[7]['status']}")

    print(f"  Seed sensitivity:              " f"{tests[8]['status']}")

    print(f"  No post-generation repair:     " f"{tests[9]['status']}")

    print(f"  Tests passed:                  " f"{passed}/{total}")

    print(f"  Overall:                       " f"{'PASS' if overall else 'FAIL'}")

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    output = {
        "experiment": ("020_declarative_generation_specification"),
        "stage": "020-K.2",
        "purpose": ("Constraint-driven generation planning"),
        "seed": MASTER_SEED,
        "tests": tests,
        "tests_passed": passed,
        "tests_total": total,
        "architecture": {
            "constraint_graph": True,
            "generation_planning": True,
            "context_aware_generation": True,
            "post_generation_repair": False,
            "bounded_ordering_constraints": True,
        },
        "architectural_conclusion": (
            "Cross-field declarative constraints "
            "can be represented as generation "
            "dependencies. Dependent fields can "
            "then be generated directly from the "
            "already-generated context."
        ),
        "boundary": (
            "The experiment intentionally supports "
            "bounded numeric ordering constraints "
            "and does not attempt arbitrary "
            "constraint solving."
        ),
        "overall": ("PASS" if overall else "FAIL"),
    }

    with RESULT_OUTPUT_PATH.open(
        "w",
        encoding="utf-8",
    ) as file:

        json.dump(
            output,
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
