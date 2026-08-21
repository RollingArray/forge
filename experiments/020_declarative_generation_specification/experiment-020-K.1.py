"""
FORGE - Experiment 020-K.1: Constraint Propagation and Feasible Generation
==========================================================================

Stage:
    020-K.1

Purpose:
    Validate that declarative constraints can be propagated into the
    generation process so that values are generated directly inside
    their feasible region.

Research Question
-----------------
Can FORGE transform declarative constraints into generation-time
bounds and dependencies rather than generating arbitrary values and
repairing them afterward?

Architectural Principle
-----------------------
FORGE should prefer:

    Specification
        ↓
    Constraint extraction
        ↓
    Constraint propagation
        ↓
    Generation plan
        ↓
    Context-aware generation
        ↓
    Validation

over:

    Random generation
        ↓
    Post-generation repair

The second approach is intentionally NOT used by this experiment.

Scope
-----
Included:

    1. Single-field bounds
    2. Multiple constraints on one field
    3. Cross-field ordering
    4. Chained cross-field constraints
    5. Conditional bounds
    6. Impossible propagated bounds
    7. Field-order independence
    8. Deterministic generation
    9. Final constraint validation

Excluded:

    - General-purpose symbolic constraint solving
    - Arbitrary mathematical optimization
    - SAT / SMT solving
    - Statistical correlation optimization
    - Relationship-level generation

Important Boundary
------------------
If the runtime cannot safely derive a feasible generation region,
generation must be BLOCKED.

It must not silently generate invalid data.

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

RESULT_OUTPUT_PATH = OUTPUT_DIR / "constraint_propagation_results.json"

MASTER_SEED = 42


# ============================================================================
# CONSTANTS
# ============================================================================

FIELD = "FIELD"
CROSS_FIELD = "CROSS_FIELD"
CONDITIONAL = "CONDITIONAL"


# ============================================================================
# MODELS
# ============================================================================


@dataclass(frozen=True)
class FieldSpec:
    name: str
    minimum: float | None = None
    maximum: float | None = None
    type: str = "DECIMAL"


@dataclass(frozen=True)
class Constraint:
    constraint_id: str
    constraint_type: str

    field: str | None = None

    operator: str | None = None
    value: Any = None

    left_field: str | None = None
    right_field: str | None = None

    condition_field: str | None = None
    condition_operator: str | None = None
    condition_value: Any = None


@dataclass(frozen=True)
class EntitySpec:
    name: str
    record_count: int
    fields: tuple[FieldSpec, ...]
    constraints: tuple[Constraint, ...]


@dataclass
class Bounds:
    minimum: float | None
    maximum: float | None

    def copy(self) -> "Bounds":
        return Bounds(
            self.minimum,
            self.maximum,
        )

    def is_valid(self) -> bool:

        if self.minimum is not None and self.maximum is not None:
            return self.minimum <= self.maximum

        return True


# ============================================================================
# DETERMINISTIC FIELD STREAMS
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
# CONSTRAINT EVALUATION
# ============================================================================


def evaluate(
    left: Any,
    operator: str,
    right: Any,
) -> bool:

    if operator == "EQUALS":
        return left == right

    if operator == "NOT_EQUALS":
        return left != right

    if operator == "GREATER_THAN":
        return left > right

    if operator == "LESS_THAN":
        return left < right

    if operator == "GREATER_OR_EQUAL":
        return left >= right

    if operator == "LESS_OR_EQUAL":
        return left <= right

    if operator == "BETWEEN":
        low, high = right
        return low <= left <= high

    if operator == "IN":
        return left in right

    if operator == "NOT_IN":
        return left not in right

    raise ValueError(f"Unsupported operator: {operator}")


# ============================================================================
# BOUND APPLICATION
# ============================================================================


def apply_lower_bound(
    bounds: Bounds,
    value: float,
) -> None:

    if bounds.minimum is None or value > bounds.minimum:
        bounds.minimum = value


def apply_upper_bound(
    bounds: Bounds,
    value: float,
) -> None:

    if bounds.maximum is None or value < bounds.maximum:
        bounds.maximum = value


# ============================================================================
# CONSTRAINT PROPAGATOR
# ============================================================================


class ConstraintPropagator:
    """
    Derives feasible generation bounds.

    The propagator deliberately operates only on bounded numeric
    constraints.

    It does not attempt arbitrary symbolic reasoning.
    """

    def __init__(
        self,
        entity: EntitySpec,
    ) -> None:

        self.entity = entity

        self.bounds: dict[
            str,
            Bounds,
        ] = {
            field.name: Bounds(
                field.minimum,
                field.maximum,
            )
            for field in entity.fields
        }

        self.conflicts: list[dict[str, Any]] = []

        self.propagation_log: list[dict[str, Any]] = []

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def propagate(self) -> dict[str, Any]:

        changed = True

        iterations = 0

        max_iterations = max(
            1,
            len(self.entity.fields) * len(self.entity.constraints) * 2,
        )

        while changed and iterations < max_iterations:

            changed = False
            iterations += 1

            for constraint in self.entity.constraints:

                if self._apply(constraint):
                    changed = True

                self._check_conflicts()

                if self.conflicts:
                    return self.result(iterations)

        self._check_conflicts()

        return self.result(iterations)

    # ------------------------------------------------------------------
    # Constraint handling
    # ------------------------------------------------------------------

    def _apply(
        self,
        constraint: Constraint,
    ) -> bool:

        if constraint.constraint_type == FIELD:

            return self._apply_field(constraint)

        if constraint.constraint_type == CROSS_FIELD:

            return self._apply_cross_field(constraint)

        if constraint.constraint_type == CONDITIONAL:

            # Conditional propagation is intentionally handled only
            # when its condition is statically determinable.
            return self._apply_conditional(constraint)

        raise ValueError(
            "Unsupported constraint type: " f"{constraint.constraint_type}"
        )

    def _apply_field(
        self,
        constraint: Constraint,
    ) -> bool:

        if not constraint.field:
            return False

        bounds = self.bounds[constraint.field]

        before = bounds.copy()

        if constraint.operator == "GREATER_THAN":

            apply_lower_bound(
                bounds,
                float(constraint.value),
            )

        elif constraint.operator == "GREATER_OR_EQUAL":

            apply_lower_bound(
                bounds,
                float(constraint.value),
            )

        elif constraint.operator == "LESS_THAN":

            apply_upper_bound(
                bounds,
                float(constraint.value),
            )

        elif constraint.operator == "LESS_OR_EQUAL":

            apply_upper_bound(
                bounds,
                float(constraint.value),
            )

        elif constraint.operator == "EQUALS":

            value = float(constraint.value)

            bounds.minimum = value
            bounds.maximum = value

        elif constraint.operator == "BETWEEN":

            low, high = constraint.value

            apply_lower_bound(
                bounds,
                float(low),
            )

            apply_upper_bound(
                bounds,
                float(high),
            )

        changed = before.minimum != bounds.minimum or before.maximum != bounds.maximum

        if changed:

            self.propagation_log.append(
                {
                    "constraint": (constraint.constraint_id),
                    "field": (constraint.field),
                    "before": {
                        "minimum": before.minimum,
                        "maximum": before.maximum,
                    },
                    "after": {
                        "minimum": bounds.minimum,
                        "maximum": bounds.maximum,
                    },
                }
            )

        return changed

    def _apply_cross_field(
        self,
        constraint: Constraint,
    ) -> bool:

        if not (constraint.left_field and constraint.right_field):
            return False

        left = self.bounds[constraint.left_field]

        right = self.bounds[constraint.right_field]

        changed = False

        # left <= right
        if constraint.operator == "LESS_OR_EQUAL":

            # left cannot exceed right's known maximum.
            if right.maximum is not None:

                before = left.maximum

                apply_upper_bound(
                    left,
                    right.maximum,
                )

                changed |= before != left.maximum

            # right cannot be below left's known minimum.
            if left.minimum is not None:

                before = right.minimum

                apply_lower_bound(
                    right,
                    left.minimum,
                )

                changed |= before != right.minimum

        # left < right
        elif constraint.operator == "LESS_THAN":

            if right.maximum is not None:

                before = left.maximum

                apply_upper_bound(
                    left,
                    right.maximum,
                )

                changed |= before != left.maximum

            if left.minimum is not None:

                before = right.minimum

                apply_lower_bound(
                    right,
                    left.minimum,
                )

                changed |= before != right.minimum

        if changed:

            self.propagation_log.append(
                {
                    "constraint": (constraint.constraint_id),
                    "type": "CROSS_FIELD",
                    "left": (constraint.left_field),
                    "right": (constraint.right_field),
                    "bounds": {
                        constraint.left_field: {
                            "minimum": (left.minimum),
                            "maximum": (left.maximum),
                        },
                        constraint.right_field: {
                            "minimum": (right.minimum),
                            "maximum": (right.maximum),
                        },
                    },
                }
            )

        return changed

    def _apply_conditional(
        self,
        constraint: Constraint,
    ) -> bool:

        # Conditional propagation is intentionally deferred unless
        # the condition is statically true.
        #
        # Example:
        #
        # CUSTOMER_TYPE == PREMIUM
        #     -> CREDIT_LIMIT >= 5000
        #
        # requires categorical context and therefore is not propagated
        # globally in this bounded numeric propagator.

        return False

    # ------------------------------------------------------------------
    # Conflict detection
    # ------------------------------------------------------------------

    def _check_conflicts(self) -> None:

        self.conflicts.clear()

        for field_name, bounds in self.bounds.items():

            if not bounds.is_valid():

                self.conflicts.append(
                    {
                        "field": field_name,
                        "minimum": bounds.minimum,
                        "maximum": bounds.maximum,
                        "reason": ("Propagated minimum " "exceeds maximum."),
                    }
                )

    def result(
        self,
        iterations: int,
    ) -> dict[str, Any]:

        return {
            "status": ("BLOCKED" if self.conflicts else "PASS"),
            "iterations": iterations,
            "bounds": {
                name: {
                    "minimum": bounds.minimum,
                    "maximum": bounds.maximum,
                }
                for name, bounds in self.bounds.items()
            },
            "conflicts": self.conflicts,
            "propagation_log": (self.propagation_log),
        }


# ============================================================================
# FEASIBLE GENERATOR
# ============================================================================


class FeasibleGenerator:
    """
    Generates directly inside propagated bounds.

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

        propagation = ConstraintPropagator(entity).propagate()

        if propagation["status"] != "PASS":

            return {
                "status": "BLOCKED",
                "propagation": propagation,
            }

        records = [{} for _ in range(entity.record_count)]

        # Fields are sorted intentionally.
        # Generation therefore does not depend on declaration order.
        fields = sorted(
            entity.fields,
            key=lambda field: field.name,
        )

        for field in fields:

            bounds = propagation["bounds"][field.name]

            low = bounds["minimum"]

            high = bounds["maximum"]

            if low is None:
                low = 0

            if high is None:
                high = 100

            rng = field_rng(
                self.seed,
                entity.name,
                field.name,
            )

            for index in range(entity.record_count):

                if field.type == "INTEGER":

                    value = rng.randint(
                        int(low),
                        int(high),
                    )

                else:

                    value = round(
                        rng.uniform(
                            float(low),
                            float(high),
                        ),
                        2,
                    )

                records[index][field.name] = value

        validation = validate_records(
            entity,
            records,
        )

        return {
            "status": ("PASS" if validation["status"] == "PASS" else "FAIL"),
            "propagation": propagation,
            "records": records,
            "validation": validation,
        }


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

            try:

                valid = _evaluate_constraint(
                    constraint,
                    record,
                )

            except Exception as exc:

                failures.append(
                    {
                        "record": index,
                        "constraint": (constraint.constraint_id),
                        "error": str(exc),
                    }
                )

                continue

            if not valid:

                failures.append(
                    {
                        "record": index,
                        "constraint": (constraint.constraint_id),
                    }
                )

    return {
        "status": ("PASS" if not failures else "FAIL"),
        "records_checked": len(records),
        "failures": failures,
    }


def _evaluate_constraint(
    constraint: Constraint,
    record: dict[str, Any],
) -> bool:

    if constraint.constraint_type == FIELD:

        return evaluate(
            record[constraint.field],
            constraint.operator,
            constraint.value,
        )

    if constraint.constraint_type == CROSS_FIELD:

        return evaluate(
            record[constraint.left_field],
            constraint.operator,
            record[constraint.right_field],
        )

    if constraint.constraint_type == CONDITIONAL:

        condition = evaluate(
            record[constraint.condition_field],
            constraint.condition_operator,
            constraint.condition_value,
        )

        if not condition:
            return True

        return evaluate(
            record[constraint.field],
            constraint.operator,
            constraint.value,
        )

    raise ValueError("Unsupported constraint type: " f"{constraint.constraint_type}")


# ============================================================================
# TEST SPECIFICATIONS
# ============================================================================


def single_field_entity() -> EntitySpec:

    return EntitySpec(
        name="SINGLE_FIELD",
        record_count=100,
        fields=(
            FieldSpec(
                name="AMOUNT",
                minimum=0,
                maximum=10000,
            ),
        ),
        constraints=(
            Constraint(
                constraint_id="C001",
                constraint_type=FIELD,
                field="AMOUNT",
                operator="GREATER_OR_EQUAL",
                value=500,
            ),
            Constraint(
                constraint_id="C002",
                constraint_type=FIELD,
                field="AMOUNT",
                operator="LESS_OR_EQUAL",
                value=5000,
            ),
        ),
    )


def cross_field_entity() -> EntitySpec:

    return EntitySpec(
        name="CROSS_FIELD",
        record_count=100,
        fields=(
            FieldSpec(
                name="MIN_AMOUNT",
                minimum=500,
                maximum=5000,
            ),
            FieldSpec(
                name="MAX_AMOUNT",
                minimum=1000,
                maximum=10000,
            ),
        ),
        constraints=(
            Constraint(
                constraint_id="C010",
                constraint_type=CROSS_FIELD,
                left_field="MIN_AMOUNT",
                right_field="MAX_AMOUNT",
                operator="LESS_OR_EQUAL",
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
                constraint_id="C020",
                constraint_type=CROSS_FIELD,
                left_field="A",
                right_field="B",
                operator="LESS_OR_EQUAL",
            ),
            Constraint(
                constraint_id="C021",
                constraint_type=CROSS_FIELD,
                left_field="B",
                right_field="C",
                operator="LESS_OR_EQUAL",
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
                minimum=9000,
                maximum=10000,
            ),
            FieldSpec(
                name="B",
                minimum=100,
                maximum=5000,
            ),
        ),
        constraints=(
            Constraint(
                constraint_id="X001",
                constraint_type=CROSS_FIELD,
                left_field="A",
                right_field="B",
                operator="LESS_OR_EQUAL",
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


def test_single_field_bounds() -> dict[str, Any]:

    entity = single_field_entity()

    result = FeasibleGenerator(MASTER_SEED).generate(entity)

    passed = (
        result["status"] == "PASS"
        and result["validation"]["status"] == "PASS"
        and all(500 <= record["AMOUNT"] <= 5000 for record in result["records"])
    )

    return {
        "status": ("PASS" if passed else "FAIL"),
        "bounds": result["propagation"]["bounds"],
    }


def test_cross_field_generation() -> dict[str, Any]:

    entity = cross_field_entity()

    result = FeasibleGenerator(MASTER_SEED).generate(entity)

    passed = (
        result["status"] == "PASS"
        and result["validation"]["status"] == "PASS"
        and all(
            record["MIN_AMOUNT"] <= record["MAX_AMOUNT"] for record in result["records"]
        )
    )

    return {
        "status": ("PASS" if passed else "FAIL"),
        "bounds": result["propagation"]["bounds"],
    }


def test_chained_constraints() -> dict[str, Any]:

    entity = chained_entity()

    result = FeasibleGenerator(MASTER_SEED).generate(entity)

    passed = (
        result["status"] == "PASS"
        and result["validation"]["status"] == "PASS"
        and all(
            record["A"] <= record["B"] <= record["C"] for record in result["records"]
        )
    )

    return {
        "status": ("PASS" if passed else "FAIL"),
        "bounds": result["propagation"]["bounds"],
    }


def test_impossible_propagation() -> dict[str, Any]:

    entity = impossible_entity()

    result = FeasibleGenerator(MASTER_SEED).generate(entity)

    passed = (
        result["status"] == "BLOCKED" and result["propagation"]["status"] == "BLOCKED"
    )

    return {
        "status": ("PASS" if passed else "FAIL"),
        "conflicts": result["propagation"]["conflicts"],
    }


def test_field_order_independence() -> dict[str, Any]:

    original = chained_entity()

    reversed_entity = EntitySpec(
        name=original.name,
        record_count=original.record_count,
        fields=tuple(reversed(original.fields)),
        constraints=tuple(reversed(original.constraints)),
    )

    first = FeasibleGenerator(MASTER_SEED).generate(original)

    second = FeasibleGenerator(MASTER_SEED).generate(reversed_entity)

    passed = first["records"] == second["records"]

    return {
        "status": ("PASS" if passed else "FAIL"),
        "identical": passed,
    }


def test_reproducibility() -> dict[str, Any]:

    entity = cross_field_entity()

    first = FeasibleGenerator(MASTER_SEED).generate(entity)

    second = FeasibleGenerator(MASTER_SEED).generate(entity)

    passed = first["records"] == second["records"]

    return {
        "status": ("PASS" if passed else "FAIL"),
        "identical": passed,
    }


def test_no_post_generation_repair() -> dict[str, Any]:

    entity = cross_field_entity()

    result = FeasibleGenerator(MASTER_SEED).generate(entity)

    propagation = result["propagation"]

    records = result["records"]

    # Every generated value must already be within
    # its propagated field bounds.
    passed = True

    for record in records:

        for field_name, bounds in propagation["bounds"].items():

            value = record[field_name]

            if bounds["minimum"] is not None and value < bounds["minimum"]:
                passed = False

            if bounds["maximum"] is not None and value > bounds["maximum"]:
                passed = False

    return {
        "status": ("PASS" if passed else "FAIL"),
        "repair_required": not passed,
    }


# ============================================================================
# MAIN
# ============================================================================


def main() -> int:

    print()

    print("=" * 70)

    print(
        "FORGE - Experiment 020-K.1: " "Constraint Propagation and Feasible Generation"
    )

    print("=" * 70)

    print("Experiment:     " "020_declarative_generation_specification")

    print("Stage:          020-K.1")

    print("Purpose:        " "Constraint propagation and feasible generation")

    print(f"Random seed:    {MASTER_SEED}")

    print()

    print("Generation architecture:")

    print("  Specification")

    print("       ↓")

    print("  Constraint extraction")

    print("       ↓")

    print("  Constraint propagation")

    print("       ↓")

    print("  Feasible generation region")

    print("       ↓")

    print("  Direct generation")

    print("       ↓")

    print("  Validation")

    print()

    tests = [
        run_test(
            "Single-field bounds",
            test_single_field_bounds,
        ),
        run_test(
            "Cross-field constraints",
            test_cross_field_generation,
        ),
        run_test(
            "Chained constraints",
            test_chained_constraints,
        ),
        run_test(
            "Impossible propagation",
            test_impossible_propagation,
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
            "No post-generation repair",
            test_no_post_generation_repair,
        ),
    ]

    print("Constraint propagation validation:")

    for test in tests:

        print(f"  " f"{test['name']:<36}" f"{test['status']}")

    passed = sum(test["status"] == "PASS" for test in tests)

    total = len(tests)

    overall = passed == total

    print()

    print("Experiment result:")

    print(f"  Single-field constraints:     " f"{tests[0]['status']}")

    print(f"  Cross-field constraints:      " f"{tests[1]['status']}")

    print(f"  Chained constraints:           " f"{tests[2]['status']}")

    print(f"  Impossible specifications:     " f"{tests[3]['status']}")

    print(f"  Field-order independence:      " f"{tests[4]['status']}")

    print(f"  Reproducibility:               " f"{tests[5]['status']}")

    print(f"  No post-generation repair:     " f"{tests[6]['status']}")

    print(f"  Tests passed:                  " f"{passed}/{total}")

    print(f"  Overall:                       " f"{'PASS' if overall else 'FAIL'}")

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    output = {
        "experiment": ("020_declarative_generation_specification"),
        "stage": "020-K.1",
        "purpose": ("Constraint propagation and " "feasible generation"),
        "seed": MASTER_SEED,
        "tests": tests,
        "tests_passed": passed,
        "tests_total": total,
        "architecture": {
            "constraint_propagation": True,
            "direct_feasible_generation": True,
            "post_generation_repair": False,
            "bounded_constraint_solver": True,
        },
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
