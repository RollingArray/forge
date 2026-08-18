"""
FORGE - Experiment 018: Constraint Conflict Detection
========================================================

Purpose
-------
This experiment tests whether FORGE can detect contradictory or
unsatisfiable constraints before attempting data generation.

The experiment builds on the constraint capabilities established by
Experiments 002 and 011 and the unified validation model established
by Experiment 017.

The following constraint forms are tested:

    - compatible numeric ranges
    - direct numeric conflicts
    - boundary conflicts
    - indirect cross-field conflicts
    - categorical conflicts
    - compatible categorical constraints
    - conditional conflicts
    - compatible conditional constraints

The experiment also tests whether conflict detection can act as a
generation guard, preventing generation when the specification is
known to be unsatisfiable.

No machine learning, LLM, or real production data is used.

Experiment
----------
018 - Constraint Conflict Detection

Key Question
------------
Can a generic constraint model identify common classes of contradictory
constraints before generation and prevent generation of an
unsatisfiable specification?

Author
------
Ranjoy Sen

Status
------
Experimental

How to Run
----------
From the repository root:

    uv run python experiments/018_constraint_conflict_detection/experiment.py

Output
------
Validation results are written to:

    experiments/018_constraint_conflict_detection/output/

Important
---------
The generated data is synthetic and does not represent any real
production dataset.
"""

from __future__ import annotations

import json
import random
from pathlib import Path
from typing import Any

# ============================================================
# Paths
# ============================================================

EXPERIMENT_DIR = Path(__file__).resolve().parent
SPECIFICATION_FILE = EXPERIMENT_DIR / "specification.json"
OUTPUT_DIR = EXPERIMENT_DIR / "output"
RESULTS_FILE = OUTPUT_DIR / "conflict_detection_results.json"


# ============================================================
# Constants
# ============================================================

COMPATIBLE = "COMPATIBLE"
CONFLICT = "CONFLICT"

SUPPORTED_TYPES = {
    "range",
    "cross_field",
    "categorical",
    "conditional",
}


# ============================================================
# Specification
# ============================================================


def load_specification() -> dict[str, Any]:
    """Load the experiment specification."""

    with SPECIFICATION_FILE.open(
        "r",
        encoding="utf-8",
    ) as file:
        return json.load(file)


# ============================================================
# Utility helpers
# ============================================================


def make_conflict(
    conflict_id: str,
    conflict_type: str,
    constraint_ids: list[str],
    reason: str,
    fields: list[str] | None = None,
) -> dict[str, Any]:
    """Create a normalized conflict record."""

    result = {
        "id": conflict_id,
        "type": conflict_type,
        "constraints": constraint_ids,
        "reason": reason,
    }

    if fields:
        result["fields"] = fields

    return result


def get_constraint_field(
    constraint: dict[str, Any],
) -> str | None:
    """Return the field associated with a constraint."""

    return constraint.get("field")


def normalize_operator(
    operator: str,
) -> str:
    """Normalize supported operators."""

    aliases = {
        "==": "=",
        "eq": "=",
        "gte": ">=",
        "lte": "<=",
        "gt": ">",
        "lt": "<",
    }

    return aliases.get(
        operator,
        operator,
    )


# ============================================================
# Numeric range analysis
# ============================================================


def analyze_numeric_ranges(
    constraints: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """
    Detect contradictory lower and upper bounds for fields.

    Supported forms:

        field >= value
        field >  value
        field <= value
        field <  value
        field =  value
    """

    conflicts = []

    by_field: dict[str, list[dict[str, Any]]] = {}

    for constraint in constraints:

        if constraint.get("type") != "range":
            continue

        field = get_constraint_field(constraint)

        if not field:
            continue

        by_field.setdefault(
            field,
            [],
        ).append(constraint)

    for field, field_constraints in by_field.items():

        lower_bounds = []
        upper_bounds = []
        equalities = []

        for constraint in field_constraints:

            operator = normalize_operator(constraint["operator"])

            value = constraint["value"]

            if operator in {">", ">="}:

                lower_bounds.append(
                    (
                        value,
                        operator,
                        constraint,
                    )
                )

            elif operator in {"<", "<="}:

                upper_bounds.append(
                    (
                        value,
                        operator,
                        constraint,
                    )
                )

            elif operator == "=":

                equalities.append(
                    (
                        value,
                        constraint,
                    )
                )

        # ----------------------------------------------------
        # Lower bound > upper bound
        # ----------------------------------------------------

        for (
            lower_value,
            lower_operator,
            lower_constraint,
        ) in lower_bounds:

            for (
                upper_value,
                upper_operator,
                upper_constraint,
            ) in upper_bounds:

                impossible = lower_value > upper_value

                impossible_boundary = lower_value == upper_value and (
                    lower_operator == ">" or upper_operator == "<"
                )

                if impossible or impossible_boundary:

                    conflicts.append(
                        make_conflict(
                            conflict_id=(
                                f"X-{field}-"
                                f"{lower_constraint['id']}-"
                                f"{upper_constraint['id']}"
                            ),
                            conflict_type="numeric_range",
                            constraint_ids=[
                                lower_constraint["id"],
                                upper_constraint["id"],
                            ],
                            fields=[field],
                            reason=(
                                f"{field} has incompatible "
                                f"bounds: "
                                f"{lower_operator} "
                                f"{lower_value} and "
                                f"{upper_operator} "
                                f"{upper_value}"
                            ),
                        )
                    )

        # ----------------------------------------------------
        # Multiple equalities
        # ----------------------------------------------------

        equality_values = {value for value, _ in equalities}

        if len(equality_values) > 1:

            conflicts.append(
                make_conflict(
                    conflict_id=(f"X-{field}-EQUALITY"),
                    conflict_type="numeric_range",
                    constraint_ids=[constraint["id"] for _, constraint in equalities],
                    fields=[field],
                    reason=(
                        f"{field} is required to equal "
                        f"multiple different values: "
                        f"{sorted(equality_values)}"
                    ),
                )
            )

        # ----------------------------------------------------
        # Equality against bounds
        # ----------------------------------------------------

        for (
            equality_value,
            equality_constraint,
        ) in equalities:

            for (
                lower_value,
                lower_operator,
                lower_constraint,
            ) in lower_bounds:

                invalid = equality_value < lower_value or (
                    equality_value == lower_value and lower_operator == ">"
                )

                if invalid:

                    conflicts.append(
                        make_conflict(
                            conflict_id=(
                                f"X-{field}-"
                                f"{equality_constraint['id']}-"
                                f"{lower_constraint['id']}"
                            ),
                            conflict_type="numeric_range",
                            constraint_ids=[
                                equality_constraint["id"],
                                lower_constraint["id"],
                            ],
                            fields=[field],
                            reason=(
                                f"{field} must equal "
                                f"{equality_value} but "
                                f"must also satisfy "
                                f"{lower_operator} "
                                f"{lower_value}"
                            ),
                        )
                    )

            for (
                upper_value,
                upper_operator,
                upper_constraint,
            ) in upper_bounds:

                invalid = equality_value > upper_value or (
                    equality_value == upper_value and upper_operator == "<"
                )

                if invalid:

                    conflicts.append(
                        make_conflict(
                            conflict_id=(
                                f"X-{field}-"
                                f"{equality_constraint['id']}-"
                                f"{upper_constraint['id']}"
                            ),
                            conflict_type="numeric_range",
                            constraint_ids=[
                                equality_constraint["id"],
                                upper_constraint["id"],
                            ],
                            fields=[field],
                            reason=(
                                f"{field} must equal "
                                f"{equality_value} but "
                                f"must also satisfy "
                                f"{upper_operator} "
                                f"{upper_value}"
                            ),
                        )
                    )

    return conflicts


# ============================================================
# Categorical analysis
# ============================================================


def analyze_categorical_constraints(
    constraints: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Detect contradictory categorical equality constraints."""

    conflicts = []

    by_field: dict[str, list[dict[str, Any]]] = {}

    for constraint in constraints:

        if constraint.get("type") != "categorical":
            continue

        field = constraint.get("field")

        if field:
            by_field.setdefault(
                field,
                [],
            ).append(constraint)

    for field, field_constraints in by_field.items():

        equality_constraints = [
            constraint
            for constraint in field_constraints
            if normalize_operator(
                constraint.get(
                    "operator",
                    "",
                )
            )
            == "="
        ]

        values = {constraint.get("value") for constraint in equality_constraints}

        if len(values) > 1:

            conflicts.append(
                make_conflict(
                    conflict_id=(f"X-{field}-" f"CATEGORICAL"),
                    conflict_type="categorical",
                    constraint_ids=[
                        constraint["id"] for constraint in equality_constraints
                    ],
                    fields=[field],
                    reason=(
                        f"{field} is required to equal "
                        f"multiple categorical values: "
                        f"{sorted(values)}"
                    ),
                )
            )

    return conflicts


# ============================================================
# Cross-field analysis
# ============================================================


def analyze_cross_field_constraints(
    constraints: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """
    Detect common contradictions between cross-field inequalities
    and explicit field bounds.

    Supported pattern:

        A <= B
        A >= X
        B <= Y

    Conflict exists when X > Y.
    """

    conflicts = []

    cross_field_constraints = [
        constraint
        for constraint in constraints
        if constraint.get("type") == "cross_field"
    ]

    range_constraints = [
        constraint for constraint in constraints if constraint.get("type") == "range"
    ]

    for cross_constraint in cross_field_constraints:

        left = cross_constraint.get("left")

        right = cross_constraint.get("right")

        operator = normalize_operator(
            cross_constraint.get(
                "operator",
                "",
            )
        )

        if operator != "<=":
            continue

        left_lower_bounds = [
            constraint
            for constraint in range_constraints
            if constraint.get("field") == left
            and normalize_operator(
                constraint.get(
                    "operator",
                    "",
                )
            )
            in {">", ">="}
        ]

        right_upper_bounds = [
            constraint
            for constraint in range_constraints
            if constraint.get("field") == right
            and normalize_operator(
                constraint.get(
                    "operator",
                    "",
                )
            )
            in {"<", "<="}
        ]

        for left_constraint in left_lower_bounds:

            for right_constraint in right_upper_bounds:

                left_value = left_constraint["value"]

                right_value = right_constraint["value"]

                if left_value > right_value:

                    conflicts.append(
                        make_conflict(
                            conflict_id=(f"X-CROSS-" f"{cross_constraint['id']}"),
                            conflict_type="cross_field",
                            constraint_ids=[
                                cross_constraint["id"],
                                left_constraint["id"],
                                right_constraint["id"],
                            ],
                            fields=[
                                left,
                                right,
                            ],
                            reason=(
                                f"{left} must be <= {right}, "
                                f"but {left} >= {left_value} "
                                f"and {right} <= {right_value}"
                            ),
                        )
                    )

    return conflicts


# ============================================================
# Conditional analysis
# ============================================================


def analyze_conditional_constraints(
    constraints: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """
    Detect contradictory conditional constraints.

    Supported pattern:

        IF A = X THEN B >= Y
        IF A = X THEN B <= Z

    Conflict exists when Y > Z.
    """

    conflicts = []

    conditional_constraints = [
        constraint
        for constraint in constraints
        if constraint.get("type") == "conditional"
    ]

    groups: dict[
        tuple[str, str, Any, str],
        list[dict[str, Any]],
    ] = {}

    for constraint in conditional_constraints:

        when = constraint.get(
            "when",
            {},
        )

        then = constraint.get(
            "then",
            {},
        )

        when_field = when.get("field")

        when_operator = normalize_operator(
            when.get(
                "operator",
                "",
            )
        )

        when_value = when.get("value")

        then_field = then.get("field")

        if not all(
            [
                when_field,
                when_operator,
                then_field,
            ]
        ):
            continue

        key = (
            when_field,
            when_operator,
            when_value,
            then_field,
        )

        groups.setdefault(
            key,
            [],
        ).append(constraint)

    for (
        condition,
        grouped_constraints,
    ) in groups.items():

        lower_bounds = []
        upper_bounds = []
        equalities = []

        for constraint in grouped_constraints:

            then = constraint["then"]

            operator = normalize_operator(
                then.get(
                    "operator",
                    "",
                )
            )

            value = then.get("value")

            if operator in {
                ">",
                ">=",
            }:

                lower_bounds.append(
                    (
                        value,
                        operator,
                        constraint,
                    )
                )

            elif operator in {
                "<",
                "<=",
            }:

                upper_bounds.append(
                    (
                        value,
                        operator,
                        constraint,
                    )
                )

            elif operator == "=":

                equalities.append(
                    (
                        value,
                        constraint,
                    )
                )

        for (
            lower_value,
            lower_operator,
            lower_constraint,
        ) in lower_bounds:

            for (
                upper_value,
                upper_operator,
                upper_constraint,
            ) in upper_bounds:

                impossible = lower_value > upper_value

                impossible_boundary = lower_value == upper_value and (
                    lower_operator == ">" or upper_operator == "<"
                )

                if impossible or impossible_boundary:

                    condition_text = (
                        f"{condition[0]} " f"{condition[1]} " f"{condition[2]}"
                    )

                    conflicts.append(
                        make_conflict(
                            conflict_id=(
                                f"X-CONDITIONAL-"
                                f"{lower_constraint['id']}-"
                                f"{upper_constraint['id']}"
                            ),
                            conflict_type="conditional",
                            constraint_ids=[
                                lower_constraint["id"],
                                upper_constraint["id"],
                            ],
                            fields=[
                                condition[0],
                                condition[3],
                            ],
                            reason=(
                                f"When {condition_text}, "
                                f"{condition[3]} must satisfy "
                                f"{lower_operator} "
                                f"{lower_value} and "
                                f"{upper_operator} "
                                f"{upper_value}"
                            ),
                        )
                    )

        equality_values = {value for value, _ in equalities}

        if len(equality_values) > 1:

            conflicts.append(
                make_conflict(
                    conflict_id=("X-CONDITIONAL-EQUALITY-" + condition[3]),
                    conflict_type="conditional",
                    constraint_ids=[constraint["id"] for _, constraint in equalities],
                    fields=[
                        condition[0],
                        condition[3],
                    ],
                    reason=(
                        f"Under the same condition, "
                        f"{condition[3]} must equal "
                        f"multiple different values: "
                        f"{sorted(equality_values)}"
                    ),
                )
            )

    return conflicts


# ============================================================
# Constraint analyzer
# ============================================================


def detect_conflicts(
    constraints: list[dict[str, Any]],
) -> dict[str, Any]:
    """Analyze a constraint set for supported conflicts."""

    conflicts = []

    unsupported_types = sorted(
        {
            constraint.get("type")
            for constraint in constraints
            if constraint.get("type") not in SUPPORTED_TYPES
        }
    )

    conflicts.extend(analyze_numeric_ranges(constraints))

    conflicts.extend(analyze_categorical_constraints(constraints))

    conflicts.extend(analyze_cross_field_constraints(constraints))

    conflicts.extend(analyze_conditional_constraints(constraints))

    return {
        "result": (CONFLICT if conflicts else COMPATIBLE),
        "constraints_checked": len(constraints),
        "conflicts_detected": len(conflicts),
        "conflicts": conflicts,
        "unsupported_types": (unsupported_types),
        "generation_allowed": not bool(conflicts),
    }


# ============================================================
# Generation guard
# ============================================================


def generation_guard(
    analysis: dict[str, Any],
) -> bool:
    """
    Determine whether generation may proceed.

    Generation is allowed only when no supported conflicts exist.
    """

    return analysis["result"] == COMPATIBLE and not analysis["unsupported_types"]


# ============================================================
# Minimal demonstration generation
# ============================================================


def generate_sample_records(
    specification: dict[str, Any],
    count: int = 10,
) -> list[dict[str, Any]]:
    """
    Generate a minimal demonstration dataset.

    This function is deliberately simple. The experiment is testing
    specification-level conflict detection, not generation fidelity.
    """

    random.seed(specification["generation"]["seed"])

    records = []

    for index in range(
        1,
        count + 1,
    ):

        records.append(
            {
                "ORDER_ID": (f"ORD{index:07d}"),
                "MIN_AMOUNT": round(
                    random.uniform(
                        100,
                        1000,
                    ),
                    2,
                ),
                "MAX_AMOUNT": round(
                    random.uniform(
                        1000,
                        5000,
                    ),
                    2,
                ),
                "ORDER_AMOUNT": round(
                    random.uniform(
                        100,
                        5000,
                    ),
                    2,
                ),
                "CUSTOMER_TYPE": random.choice(
                    [
                        "STANDARD",
                        "PREMIUM",
                    ]
                ),
                "DISCOUNT": round(
                    random.uniform(
                        0,
                        30,
                    ),
                    2,
                ),
            }
        )

    return records


# ============================================================
# Constraint-set validation
# ============================================================


def validate_constraint_sets(
    specification: dict[str, Any],
) -> list[dict[str, Any]]:
    """Evaluate every declared constraint set."""

    results = []

    for constraint_set in specification["constraint_sets"]:

        analysis = detect_conflicts(constraint_set["constraints"])

        expected = constraint_set["expected_result"]

        actual = analysis["result"]

        classification_pass = actual == expected

        guard_result = generation_guard(analysis)

        expected_generation_allowed = expected == COMPATIBLE

        generation_guard_pass = guard_result == expected_generation_allowed

        results.append(
            {
                "id": constraint_set["id"],
                "name": constraint_set["name"],
                "expected_result": expected,
                "actual_result": actual,
                "classification_pass": (classification_pass),
                "generation_allowed": (guard_result),
                "expected_generation_allowed": (expected_generation_allowed),
                "generation_guard_pass": (generation_guard_pass),
                "constraints_checked": (analysis["constraints_checked"]),
                "conflicts_detected": (analysis["conflicts_detected"]),
                "conflicts": analysis["conflicts"],
                "unsupported_types": (analysis["unsupported_types"]),
            }
        )

    return results


# ============================================================
# Summary
# ============================================================


def build_summary(
    results: list[dict[str, Any]],
) -> dict[str, Any]:
    """Build experiment-level summary."""

    total = len(results)

    classification_passes = sum(result["classification_pass"] for result in results)

    guard_passes = sum(result["generation_guard_pass"] for result in results)

    compatible_sets = sum(result["actual_result"] == COMPATIBLE for result in results)

    conflicting_sets = sum(result["actual_result"] == CONFLICT for result in results)

    all_classifications_pass = classification_passes == total

    all_guards_pass = guard_passes == total

    expected_compatible_count = sum(
        result["expected_result"] == COMPATIBLE for result in results
    )

    expected_conflict_count = sum(
        result["expected_result"] == CONFLICT for result in results
    )

    expected_counts_match = (
        compatible_sets == expected_compatible_count
        and conflicting_sets == expected_conflict_count
    )

    overall_pass = all(
        [
            all_classifications_pass,
            all_guards_pass,
            expected_counts_match,
        ]
    )

    return {
        "constraint_sets": total,
        "classification_passes": (classification_passes),
        "generation_guard_passes": (guard_passes),
        "compatible_sets_detected": (compatible_sets),
        "conflicting_sets_detected": (conflicting_sets),
        "expected_compatible_sets": (expected_compatible_count),
        "expected_conflicting_sets": (expected_conflict_count),
        "classification_validation": ("PASS" if all_classifications_pass else "FAIL"),
        "generation_guard_validation": ("PASS" if all_guards_pass else "FAIL"),
        "coverage_validation": ("PASS" if expected_counts_match else "FAIL"),
        "overall_result": ("PASS" if overall_pass else "FAIL"),
    }


# ============================================================
# Output
# ============================================================


def save_results(
    specification: dict[str, Any],
    results: list[dict[str, Any]],
    summary: dict[str, Any],
) -> None:
    """Persist experiment results."""

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    output = {
        "experiment": specification["experiment"],
        "generation": specification["generation"],
        "results": results,
        "summary": summary,
    }

    with RESULTS_FILE.open(
        "w",
        encoding="utf-8",
    ) as file:

        json.dump(
            output,
            file,
            indent=2,
            default=str,
        )


# ============================================================
# Console reporting
# ============================================================


def print_constraint_result(
    result: dict[str, Any],
) -> None:
    """Print one constraint-set result."""

    status = "PASS" if result["classification_pass"] else "FAIL"

    print(f"\n  {result['id']}: " f"{result['name']}")

    print(f"    Expected: " f"{result['expected_result']}")

    print(f"    Detected: " f"{result['actual_result']}")

    print(f"    Conflicts: " f"{result['conflicts_detected']}")

    print(
        f"    Generation allowed: " f"{'YES' if result['generation_allowed'] else 'NO'}"
    )

    print(f"    Classification: " f"{status}")

    if result["conflicts"]:

        for conflict in result["conflicts"]:

            print(f"      {conflict['id']}: " f"{conflict['reason']}")


# ============================================================
# Main
# ============================================================


def main() -> None:
    """Run Experiment 018."""

    specification = load_specification()

    experiment = specification["experiment"]

    seed = specification["generation"]["seed"]

    random.seed(seed)

    print("=" * 70)
    print("FORGE - Experiment 018: " "Constraint Conflict Detection")
    print("=" * 70)

    print(f"Experiment:   " f"{experiment['id']} - " f"{experiment['name']}")

    print(f"Specification: " f"{SPECIFICATION_FILE}")

    print(f"Random seed:   " f"{seed}")

    print("\nConstraint conflict analysis:")

    results = validate_constraint_sets(specification)

    for result in results:
        print_constraint_result(result)

    summary = build_summary(results)

    save_results(
        specification,
        results,
        summary,
    )

    # --------------------------------------------------------
    # Demonstration of generation guard
    # --------------------------------------------------------

    compatible_results = [
        result for result in results if result["expected_result"] == COMPATIBLE
    ]

    conflicting_results = [
        result for result in results if result["expected_result"] == CONFLICT
    ]

    compatible_generation_allowed = all(
        result["generation_allowed"] for result in compatible_results
    )

    conflicting_generation_blocked = all(
        not result["generation_allowed"] for result in conflicting_results
    )

    generation_guard_pass = (
        compatible_generation_allowed and conflicting_generation_blocked
    )

    # --------------------------------------------------------
    # Demonstration generation
    # --------------------------------------------------------

    sample_records = []

    if compatible_results:

        sample_records = generate_sample_records(
            specification,
            count=10,
        )

    sample_generation_pass = len(sample_records) == 10

    # --------------------------------------------------------
    # Final experiment result
    # --------------------------------------------------------

    overall_pass = all(
        [
            summary["overall_result"] == "PASS",
            generation_guard_pass,
            sample_generation_pass,
        ]
    )

    print("\n" + "-" * 70)

    print("Conflict detection validation")

    print(f"  Constraint classification: " f"{summary['classification_validation']}")

    print(f"  Generation guard: " f"{'PASS' if generation_guard_pass else 'FAIL'}")

    print(
        f"  Compatible specifications: "
        f"{'PASS' if compatible_generation_allowed else 'FAIL'}"
    )

    print(
        f"  Conflicting specifications blocked: "
        f"{'PASS' if conflicting_generation_blocked else 'FAIL'}"
    )

    print(f"  Sample generation: " f"{'PASS' if sample_generation_pass else 'FAIL'}")

    print(f"  Overall: " f"{'PASS' if overall_pass else 'FAIL'}")

    print("\nOutput:")

    print(f"  Results: " f"{RESULTS_FILE}")

    if sample_records:

        print("\nSample records generated from a " "compatible specification:")

        for record in sample_records:
            print(f"  {record}")

    print("\nExperiment completed successfully.")


# ============================================================
# Entry point
# ============================================================


if __name__ == "__main__":
    main()
