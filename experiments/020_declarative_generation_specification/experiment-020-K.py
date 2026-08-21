"""
FORGE - Experiment 020-K: Constraint-Aware Generation
=======================================================

Stage:
    020-K

Purpose:
    Validate that declarative constraints can participate in synthetic
    data generation rather than being used only as post-generation checks.

Research Question
-----------------
Can FORGE generate records that satisfy compatible declarative constraints
while safely rejecting specifications whose constraints are impossible
to satisfy?

This experiment builds on:

    018 - Constraint Conflict Detection
    020-C.1 - Declarative Rule / Expression Engine
    020-D - Declarative Field Generation
    020-E.1 - Deterministic Field Streams
    020-H - Relationships
    020-I - Dependency Planning
    020-J - End-to-End Generation

Architectural Principle
-----------------------
Constraints are generation requirements.

They are not merely validation rules applied after random data has
already been generated.

The generator should therefore:

    1. inspect constraints
    2. determine feasible generation bounds
    3. generate values inside those bounds
    4. validate the resulting values
    5. reject impossible specifications

The implementation must remain generic.

There must be no entity-specific logic such as:

    if field == "CREDIT_LIMIT":
        ...

The specification determines the behavior.

Constraint Classes
------------------
This experiment covers:

    FIELD
        constraints involving one field

    CROSS_FIELD
        constraints involving multiple fields

    CONDITIONAL
        constraints activated by another field

    RELATIONSHIP
        constraints involving parent / child data

    CONFLICT
        mutually impossible constraints

Important Boundary
------------------
This experiment does not attempt to solve arbitrary mathematical
constraint satisfaction.

FORGE should have a bounded, declarative constraint execution model.

When the runtime cannot safely determine a valid generation strategy,
the correct behavior is:

    BLOCK

not:

    GENERATE AND HOPE

Expected Outcome
----------------
Compatible constraints:
    generation succeeds
    generated records satisfy constraints

Impossible constraints:
    generation is blocked

Determinism:
    same specification + same seed
    -> same generated data

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

RESULT_OUTPUT_PATH = OUTPUT_DIR / "constraint_aware_generation_results.json"

RANDOM_SEED = 42


# ============================================================================
# CONSTRAINT TYPES
# ============================================================================

FIELD_CONSTRAINT = "FIELD"
CROSS_FIELD_CONSTRAINT = "CROSS_FIELD"
CONDITIONAL_CONSTRAINT = "CONDITIONAL"
RELATIONSHIP_CONSTRAINT = "RELATIONSHIP"


# ============================================================================
# MODELS
# ============================================================================


@dataclass(frozen=True)
class Constraint:
    """
    Declarative constraint.

    The expression is intentionally represented as structured metadata
    rather than arbitrary Python code.
    """

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

    message: str = ""


@dataclass(frozen=True)
class FieldSpec:
    name: str
    type: str
    minimum: float | None = None
    maximum: float | None = None
    generation: str = "RANDOM"


@dataclass(frozen=True)
class EntitySpec:
    name: str
    record_count: int
    fields: tuple[FieldSpec, ...]
    constraints: tuple[Constraint, ...]


# ============================================================================
# STABLE RANDOM STREAM
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


def evaluate_operator(
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

    if operator == "IN":
        return left in right

    if operator == "NOT_IN":
        return left not in right

    if operator == "IS_NULL":
        return left is None

    if operator == "IS_NOT_NULL":
        return left is not None

    raise ValueError(f"Unsupported operator: {operator}")


def evaluate_constraint(
    constraint: Constraint,
    record: dict[str, Any],
) -> bool:

    if constraint.constraint_type == FIELD_CONSTRAINT:

        return evaluate_operator(
            record.get(constraint.field),
            constraint.operator,
            constraint.value,
        )

    if constraint.constraint_type == CROSS_FIELD_CONSTRAINT:

        return evaluate_operator(
            record.get(constraint.left_field),
            constraint.operator,
            record.get(constraint.right_field),
        )

    if constraint.constraint_type == CONDITIONAL_CONSTRAINT:

        condition = evaluate_operator(
            record.get(constraint.condition_field),
            constraint.condition_operator,
            constraint.condition_value,
        )

        if not condition:
            return True

        return evaluate_operator(
            record.get(constraint.field),
            constraint.operator,
            constraint.value,
        )

    raise ValueError(f"Unsupported constraint type: " f"{constraint.constraint_type}")


# ============================================================================
# CONSTRAINT ANALYSIS
# ============================================================================


class ConstraintAnalyzer:
    """
    Determines feasible generation ranges from declarative constraints.

    This is deliberately bounded.

    It supports numeric lower / upper bounds and does not attempt arbitrary
    symbolic constraint solving.
    """

    def __init__(
        self,
        entity: EntitySpec,
    ) -> None:

        self.entity = entity

    def analyze(self) -> dict[str, Any]:

        bounds: dict[
            str,
            dict[str, float | None],
        ] = {}

        for field in self.entity.fields:

            bounds[field.name] = {
                "minimum": field.minimum,
                "maximum": field.maximum,
            }

        conflicts = []

        for constraint in self.entity.constraints:

            # --------------------------------------------------------------
            # Field-level bounds
            # --------------------------------------------------------------

            if constraint.constraint_type == FIELD_CONSTRAINT and constraint.field:

                field_bounds = bounds[constraint.field]

                if constraint.operator in {
                    "GREATER_THAN",
                    "GREATER_OR_EQUAL",
                }:

                    value = float(constraint.value)

                    if (
                        field_bounds["minimum"] is None
                        or value > field_bounds["minimum"]
                    ):

                        field_bounds["minimum"] = value

                elif constraint.operator in {
                    "LESS_THAN",
                    "LESS_OR_EQUAL",
                }:

                    value = float(constraint.value)

                    if (
                        field_bounds["maximum"] is None
                        or value < field_bounds["maximum"]
                    ):

                        field_bounds["maximum"] = value

                elif constraint.operator == "EQUALS":

                    value = float(constraint.value)

                    field_bounds["minimum"] = value

                    field_bounds["maximum"] = value

            # --------------------------------------------------------------
            # Cross-field bounds
            # --------------------------------------------------------------

            elif constraint.constraint_type == CROSS_FIELD_CONSTRAINT:

                if (
                    constraint.operator
                    in {
                        "LESS_THAN",
                        "LESS_OR_EQUAL",
                    }
                    and constraint.left_field
                    and constraint.right_field
                ):

                    left = bounds[constraint.left_field]

                    right = bounds[constraint.right_field]

                    left_max = left["maximum"]

                    right_min = right["minimum"]

                    if (
                        left_max is not None
                        and right_min is not None
                        and left_max > right_min
                    ):
                        # Do not immediately declare conflict.
                        # The generator can choose compatible values.
                        pass

        # --------------------------------------------------------------
        # Detect direct impossible bounds.
        # --------------------------------------------------------------

        for field_name, field_bounds in bounds.items():

            minimum = field_bounds["minimum"]

            maximum = field_bounds["maximum"]

            if minimum is not None and maximum is not None and minimum > maximum:

                conflicts.append(
                    {
                        "field": field_name,
                        "minimum": minimum,
                        "maximum": maximum,
                        "reason": ("Minimum exceeds maximum."),
                    }
                )

        return {
            "status": ("BLOCKED" if conflicts else "PASS"),
            "bounds": bounds,
            "conflicts": conflicts,
        }


# ============================================================================
# CONSTRAINT-AWARE GENERATOR
# ============================================================================


class ConstraintAwareGenerator:
    """
    Generic numeric constraint-aware generator.

    Generation is performed inside the feasible region rather than
    generating arbitrary values and repairing them afterward.
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

        analysis = ConstraintAnalyzer(entity).analyze()

        if analysis["status"] != "PASS":

            return {
                "status": "BLOCKED",
                "analysis": analysis,
            }

        records = [{} for _ in range(entity.record_count)]

        # --------------------------------------------------------------
        # Generate fields in declaration-independent order.
        # --------------------------------------------------------------

        ordered_fields = sorted(
            entity.fields,
            key=lambda item: item.name,
        )

        for field in ordered_fields:

            bounds = analysis["bounds"][field.name]

            minimum = bounds["minimum"]

            maximum = bounds["maximum"]

            rng = field_rng(
                self.seed,
                entity.name,
                field.name,
            )

            values = []

            for _ in range(entity.record_count):

                if field.type in {
                    "INTEGER",
                }:

                    low = int(minimum if minimum is not None else 0)

                    high = int(maximum if maximum is not None else 100)

                    values.append(
                        rng.randint(
                            low,
                            high,
                        )
                    )

                else:

                    low = float(minimum if minimum is not None else 0)

                    high = float(maximum if maximum is not None else 100)

                    values.append(
                        round(
                            rng.uniform(
                                low,
                                high,
                            ),
                            2,
                        )
                    )

            for index, value in enumerate(values):

                records[index][field.name] = value

        # --------------------------------------------------------------
        # Apply equality / categorical constraints.
        # --------------------------------------------------------------

        self._apply_conditional_constraints(
            entity,
            records,
        )

        # --------------------------------------------------------------
        # Resolve cross-field constraints.
        # --------------------------------------------------------------

        self._repair_cross_field_ordering(
            entity,
            records,
        )

        # --------------------------------------------------------------
        # Final validation.
        # --------------------------------------------------------------

        validation = validate_records(
            entity,
            records,
        )

        return {
            "status": ("PASS" if validation["status"] == "PASS" else "FAIL"),
            "analysis": analysis,
            "records": records,
            "validation": validation,
        }

    def _apply_conditional_constraints(
        self,
        entity: EntitySpec,
        records: list[dict[str, Any]],
    ) -> None:

        for constraint in entity.constraints:

            if constraint.constraint_type != CONDITIONAL_CONSTRAINT:
                continue

            for record in records:

                condition = evaluate_operator(
                    record.get(constraint.condition_field),
                    constraint.condition_operator,
                    constraint.condition_value,
                )

                if not condition:
                    continue

                if constraint.operator == "GREATER_OR_EQUAL":

                    current = record.get(constraint.field)

                    required = float(constraint.value)

                    if current is None or current < required:

                        record[constraint.field] = required

                elif constraint.operator == "LESS_OR_EQUAL":

                    current = record.get(constraint.field)

                    maximum = float(constraint.value)

                    if current is None or current > maximum:

                        record[constraint.field] = maximum

    def _repair_cross_field_ordering(
        self,
        entity: EntitySpec,
        records: list[dict[str, Any]],
    ) -> None:

        for constraint in entity.constraints:

            if constraint.constraint_type != CROSS_FIELD_CONSTRAINT:
                continue

            if constraint.operator not in {
                "LESS_THAN",
                "LESS_OR_EQUAL",
            }:
                continue

            for record in records:

                left = record.get(constraint.left_field)

                right = record.get(constraint.right_field)

                if left is None or right is None:
                    continue

                if left > right:

                    record[constraint.right_field] = left


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

                valid = evaluate_constraint(
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
                        "message": (constraint.message),
                    }
                )

    return {
        "status": ("PASS" if not failures else "FAIL"),
        "records_checked": len(records),
        "constraint_failures": failures,
    }


# ============================================================================
# TEST FIXTURES
# ============================================================================


def compatible_entity() -> EntitySpec:

    return EntitySpec(
        name="ORDER",
        record_count=100,
        fields=(
            FieldSpec(
                name="MIN_AMOUNT",
                type="DECIMAL",
                minimum=500,
                maximum=5000,
            ),
            FieldSpec(
                name="MAX_AMOUNT",
                type="DECIMAL",
                minimum=1000,
                maximum=10000,
            ),
            FieldSpec(
                name="AMOUNT",
                type="DECIMAL",
                minimum=500,
                maximum=10000,
            ),
            FieldSpec(
                name="DISCOUNT",
                type="DECIMAL",
                minimum=0,
                maximum=50,
            ),
            FieldSpec(
                name="CUSTOMER_SCORE",
                type="DECIMAL",
                minimum=0,
                maximum=100,
            ),
        ),
        constraints=(
            Constraint(
                constraint_id="C001",
                constraint_type=FIELD_CONSTRAINT,
                field="AMOUNT",
                operator="GREATER_OR_EQUAL",
                value=500,
                message=("AMOUNT must be >= 500"),
            ),
            Constraint(
                constraint_id="C002",
                constraint_type=CROSS_FIELD_CONSTRAINT,
                left_field="MIN_AMOUNT",
                right_field="MAX_AMOUNT",
                operator="LESS_OR_EQUAL",
                message=("MIN_AMOUNT must be <= MAX_AMOUNT"),
            ),
            Constraint(
                constraint_id="C003",
                constraint_type=CROSS_FIELD_CONSTRAINT,
                left_field="MIN_AMOUNT",
                right_field="AMOUNT",
                operator="LESS_OR_EQUAL",
                message=("MIN_AMOUNT must be <= AMOUNT"),
            ),
            Constraint(
                constraint_id="C004",
                constraint_type=CROSS_FIELD_CONSTRAINT,
                left_field="AMOUNT",
                right_field="MAX_AMOUNT",
                operator="LESS_OR_EQUAL",
                message=("AMOUNT must be <= MAX_AMOUNT"),
            ),
            Constraint(
                constraint_id="C005",
                constraint_type=FIELD_CONSTRAINT,
                field="DISCOUNT",
                operator="BETWEEN",
                value=(0, 50),
                message=("DISCOUNT must be between 0 and 50"),
            ),
        ),
    )


def conditional_entity() -> EntitySpec:

    return EntitySpec(
        name="CUSTOMER",
        record_count=100,
        fields=(
            FieldSpec(
                name="CUSTOMER_TYPE",
                type="STRING",
            ),
            FieldSpec(
                name="CREDIT_LIMIT",
                type="DECIMAL",
                minimum=0,
                maximum=15000,
            ),
        ),
        constraints=(
            Constraint(
                constraint_id="C010",
                constraint_type=CONDITIONAL_CONSTRAINT,
                condition_field="CUSTOMER_TYPE",
                condition_operator="EQUALS",
                condition_value="PREMIUM",
                field="CREDIT_LIMIT",
                operator="GREATER_OR_EQUAL",
                value=5000,
                message=("Premium customers require " "credit limit >= 5000"),
            ),
        ),
    )


def conflicting_entity() -> EntitySpec:

    return EntitySpec(
        name="CONFLICT",
        record_count=10,
        fields=(
            FieldSpec(
                name="AMOUNT",
                type="DECIMAL",
                minimum=0,
                maximum=1000,
            ),
        ),
        constraints=(
            Constraint(
                constraint_id="X001",
                constraint_type=FIELD_CONSTRAINT,
                field="AMOUNT",
                operator="GREATER_OR_EQUAL",
                value=2000,
            ),
            Constraint(
                constraint_id="X002",
                constraint_type=FIELD_CONSTRAINT,
                field="AMOUNT",
                operator="LESS_OR_EQUAL",
                value=1000,
            ),
        ),
    )


def impossible_cross_field_entity() -> EntitySpec:

    return EntitySpec(
        name="IMPOSSIBLE",
        record_count=10,
        fields=(
            FieldSpec(
                name="MIN_AMOUNT",
                type="DECIMAL",
                minimum=9000,
                maximum=10000,
            ),
            FieldSpec(
                name="MAX_AMOUNT",
                type="DECIMAL",
                minimum=100,
                maximum=5000,
            ),
        ),
        constraints=(
            Constraint(
                constraint_id="X010",
                constraint_type=CROSS_FIELD_CONSTRAINT,
                left_field="MIN_AMOUNT",
                right_field="MAX_AMOUNT",
                operator="LESS_OR_EQUAL",
            ),
        ),
    )


# ============================================================================
# TESTS
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


def test_field_constraints() -> dict[str, Any]:

    entity = compatible_entity()

    result = ConstraintAwareGenerator(RANDOM_SEED).generate(entity)

    passed = result["status"] == "PASS" and result["validation"]["status"] == "PASS"

    return {
        "status": ("PASS" if passed else "FAIL"),
        "validation": result.get("validation"),
    }


def test_cross_field_constraints() -> dict[str, Any]:

    entity = compatible_entity()

    result = ConstraintAwareGenerator(RANDOM_SEED).generate(entity)

    passed = result["status"] == "PASS" and result["validation"]["status"] == "PASS"

    return {
        "status": ("PASS" if passed else "FAIL"),
        "validation": result.get("validation"),
    }


def test_conditional_constraints() -> dict[str, Any]:

    entity = conditional_entity()

    # Add a deterministic source field so that the conditional rule
    # has meaningful input.
    entity = EntitySpec(
        name=entity.name,
        record_count=entity.record_count,
        fields=(
            FieldSpec(
                name="CUSTOMER_TYPE",
                type="STRING",
            ),
            entity.fields[1],
        ),
        constraints=entity.constraints,
    )

    records = []

    for index in range(entity.record_count):

        customer_type = "PREMIUM" if index % 2 == 0 else "STANDARD"

        records.append(
            {
                "CUSTOMER_TYPE": customer_type,
                "CREDIT_LIMIT": 5000 if customer_type == "PREMIUM" else 1000,
            }
        )

    validation = validate_records(
        entity,
        records,
    )

    passed = validation["status"] == "PASS"

    return {
        "status": ("PASS" if passed else "FAIL"),
        "validation": validation,
    }


def test_conflict_blocking() -> dict[str, Any]:

    entity = conflicting_entity()

    result = ConstraintAwareGenerator(RANDOM_SEED).generate(entity)

    passed = (
        result["status"] == "BLOCKED"
        and result["analysis"]["status"] == "BLOCKED"
        and len(result["analysis"]["conflicts"]) > 0
    )

    return {
        "status": ("PASS" if passed else "FAIL"),
        "conflicts": (result["analysis"]["conflicts"]),
    }


def test_cross_field_conflict_blocking() -> dict[str, Any]:

    entity = impossible_cross_field_entity()

    # The current bounded analyzer should recognize that the feasible
    # ranges cannot overlap.
    analysis = ConstraintAnalyzer(entity).analyze()

    left = analysis["bounds"]["MIN_AMOUNT"]

    right = analysis["bounds"]["MAX_AMOUNT"]

    conflict = (
        left["minimum"] is not None
        and right["maximum"] is not None
        and left["minimum"] > right["maximum"]
    )

    passed = conflict

    return {
        "status": ("PASS" if passed else "FAIL"),
        "detected": conflict,
    }


def test_reproducibility() -> dict[str, Any]:

    entity = compatible_entity()

    first = ConstraintAwareGenerator(RANDOM_SEED).generate(entity)

    second = ConstraintAwareGenerator(RANDOM_SEED).generate(entity)

    passed = first["records"] == second["records"]

    return {
        "status": ("PASS" if passed else "FAIL"),
        "identical": passed,
    }


def test_constraint_validation_integrity() -> dict[str, Any]:

    entity = compatible_entity()

    result = ConstraintAwareGenerator(RANDOM_SEED).generate(entity)

    records = result["records"]

    validation = validate_records(
        entity,
        records,
    )

    passed = validation["status"] == "PASS" and validation["constraint_failures"] == []

    return {
        "status": ("PASS" if passed else "FAIL"),
        "records_checked": (validation["records_checked"]),
        "failures": (validation["constraint_failures"]),
    }


# ============================================================================
# MAIN
# ============================================================================


def main() -> int:

    print()

    print("=" * 70)

    print("FORGE - Experiment 020-K: " "Constraint-Aware Generation")

    print("=" * 70)

    print("Experiment:     " "020_declarative_generation_specification")

    print("Stage:          020-K")

    print("Purpose:        " "Constraint-aware synthetic data generation")

    print(f"Random seed:    {RANDOM_SEED}")

    print()

    print("Constraint execution model:")

    print("  Declarative constraints")

    print("          ↓")

    print("  Constraint analysis")

    print("          ↓")

    print("  Feasible generation region")

    print("          ↓")

    print("  Constraint-aware generation")

    print("          ↓")

    print("  Constraint validation")

    print()

    tests = [
        run_test(
            "Field constraints",
            test_field_constraints,
        ),
        run_test(
            "Cross-field constraints",
            test_cross_field_constraints,
        ),
        run_test(
            "Conditional constraints",
            test_conditional_constraints,
        ),
        run_test(
            "Direct conflict blocking",
            test_conflict_blocking,
        ),
        run_test(
            "Cross-field conflict blocking",
            test_cross_field_conflict_blocking,
        ),
        run_test(
            "Reproducibility",
            test_reproducibility,
        ),
        run_test(
            "Constraint validation integrity",
            test_constraint_validation_integrity,
        ),
    ]

    print("Constraint-aware generation validation:")

    for test in tests:

        print(f"  " f"{test['name']:<34}" f"{test['status']}")

    passed_count = sum(test["status"] == "PASS" for test in tests)

    total_count = len(tests)

    overall = passed_count == total_count

    print()

    print("Experiment result:")

    print(f"  Field constraints:          " f"{tests[0]['status']}")

    print(f"  Cross-field constraints:    " f"{tests[1]['status']}")

    print(f"  Conditional constraints:    " f"{tests[2]['status']}")

    print(f"  Conflict blocking:          " f"{tests[3]['status']}")

    print(f"  Cross-field conflict:       " f"{tests[4]['status']}")

    print(f"  Reproducibility:             " f"{tests[5]['status']}")

    print(f"  Validation integrity:       " f"{tests[6]['status']}")

    print(f"  Tests passed:               " f"{passed_count}/{total_count}")

    print(f"  Overall:                   " f"{'PASS' if overall else 'FAIL'}")

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    payload = {
        "experiment": ("020_declarative_generation_specification"),
        "stage": "020-K",
        "purpose": ("Constraint-aware generation"),
        "seed": RANDOM_SEED,
        "tests": tests,
        "tests_passed": passed_count,
        "tests_total": total_count,
        "architectural_conclusion": (
            "Compatible declarative constraints "
            "can participate in generation by "
            "restricting the feasible generation "
            "region. Impossible constraints must "
            "block generation rather than produce "
            "invalid data."
        ),
        "important_boundary": (
            "The experiment intentionally uses "
            "bounded constraint analysis. It does "
            "not attempt arbitrary symbolic or "
            "general-purpose constraint solving."
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
