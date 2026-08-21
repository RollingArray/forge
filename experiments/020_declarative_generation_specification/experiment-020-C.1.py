"""
FORGE - Experiment 020-C.1: Expression Engine Validation Hardening
===================================================================

Purpose
-------
This experiment hardens and validates the declarative expression engine
established by Experiment 020-C.

Stage
-----
020-C.1 - Expression Engine Validation Hardening

This experiment does not introduce a new rule language.

Instead, it validates the behavior of the existing generic expression
engine under:

    - positive evaluations
    - negative evaluations
    - nested expressions
    - malformed expressions
    - missing references
    - arithmetic errors
    - unsupported but valid FORGE vocabulary
    - category-level result reporting

The experiment specifically establishes the distinction between:

    PASS
        The expression evaluated successfully and produced the
        expected result.

    FAIL
        The expression evaluated successfully but produced an
        unexpected result.

    ERROR
        The expression could not be evaluated because the expression
        or runtime context was invalid.

    DEFERRED
        The expression uses valid FORGE vocabulary that is intentionally
        not executable at the current stage.

Research Question
-----------------
Can the FORGE expression engine reliably distinguish successful
boolean outcomes, evaluation failures, malformed expressions, and
valid-but-deferred capabilities?

Hypothesis
----------
A generic declarative expression engine should:

    - correctly evaluate both True and False results
    - correctly evaluate nested expressions
    - reject malformed expressions explicitly
    - reject missing references explicitly
    - protect against invalid arithmetic operations
    - distinguish unsupported vocabulary from invalid vocabulary
    - preserve deterministic evaluation behavior
    - provide accurate category-level validation results

The hypothesis is supported if all expected behaviors are observed.

The hypothesis is rejected if the engine:

    - treats False as an evaluation failure
    - silently accepts malformed expressions
    - silently resolves missing references
    - executes deferred vocabulary
    - produces incorrect category-level reporting
    - produces nondeterministic results

No machine learning, LLM, or production data is used.

Experiment
----------
020-C.1 - Expression Engine Validation Hardening

Author
------
Ranjoy Sen

Status
------
Experimental

How to Run
----------
From the repository root:

    uv run python experiments/020_declarative_generation_specification/experiment-020-C.1.py

Output
------
    experiments/020_declarative_generation_specification/output/

Important
---------
The expression evaluator implementation is intentionally reused from
Experiment 020-C.

This stage validates the evaluator rather than creating a second
independent rule engine.
"""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

# ============================================================================
# LOAD 020-C IMPLEMENTATION
# ============================================================================

EXPERIMENT_DIR = Path(__file__).resolve().parent

OUTPUT_DIR = EXPERIMENT_DIR / "output"

RESULT_OUTPUT_PATH = OUTPUT_DIR / "rule_expression_validation_hardening.json"


# Import the existing evaluator from 020-C.
#
# The filename contains a hyphen, so normal Python import syntax cannot be
# used. We load the module directly from its path.
import importlib.util

ENGINE_PATH = EXPERIMENT_DIR / "experiment-020-C.py"


def load_expression_engine():
    spec = importlib.util.spec_from_file_location(
        "forge_experiment_020_c",
        ENGINE_PATH,
    )

    if spec is None or spec.loader is None:
        raise RuntimeError("Unable to load Experiment 020-C.")

    module = importlib.util.module_from_spec(spec)

    # Required for dataclasses and other runtime introspection
    # used by Experiment 020-C.
    sys.modules[spec.name] = module

    spec.loader.exec_module(module)

    return module


ENGINE = load_expression_engine()

ExpressionEvaluator = ENGINE.ExpressionEvaluator

EvaluationContext = ENGINE.EvaluationContext

UnsupportedOperatorError = ENGINE.UnsupportedOperatorError

InvalidExpressionError = ENGINE.InvalidExpressionError

EvaluationError = ENGINE.EvaluationError

RuleVocabulary = ENGINE.RuleVocabulary


# ============================================================================
# TEST MODEL
# ============================================================================


@dataclass
class HardeningTest:

    test_id: str
    category: str
    description: str
    expression: Any
    expected_behavior: str
    expected_value: Any = None


# ============================================================================
# TEST CONTEXTS
# ============================================================================


def build_context() -> EvaluationContext:

    return EvaluationContext(
        record={
            "CUSTOMER_ID": "CUS001",
            "CUSTOMER_TYPE": "PREMIUM",
            "COUNTRY": "US",
            "AMOUNT": 7500.0,
            "CREDIT_LIMIT": 15000.0,
            "STATUS": "OPEN",
            "OPTIONAL_VALUE": None,
            "QUANTITY": 5,
            "UNIT_PRICE": 250.0,
            "SUBTOTAL": 1250.0,
            "DISCOUNT_AMOUNT": 150.0,
            "ORDER_ID": "1001",
            "EMAIL": "user@example.com",
            "CODE": "ABC123",
            "ORDER_DATE": date(
                2026,
                8,
                20,
            ),
            "DELIVERY_DATE": date(
                2026,
                8,
                25,
            ),
        }
    )


# ============================================================================
# EXPRESSION HELPERS
# ============================================================================


def field(
    name: str,
) -> dict[str, Any]:

    return {"field": name}


def value(
    data: Any,
) -> dict[str, Any]:

    return {"value": data}


def expression(
    operator: str,
    **kwargs: Any,
) -> dict[str, Any]:

    return {
        "operator": operator,
        **kwargs,
    }


# ============================================================================
# TEST SUITE
# ============================================================================


def build_tests() -> list[HardeningTest]:

    return [
        # ==================================================================
        # BOOLEAN TRUE / FALSE
        # ==================================================================
        HardeningTest(
            "BOOL-001",
            "Boolean Outcomes",
            "True comparison is accepted as PASS",
            expression(
                "GREATER_THAN",
                left=field("AMOUNT"),
                right=value(5000),
            ),
            "VALUE",
            True,
        ),
        HardeningTest(
            "BOOL-002",
            "Boolean Outcomes",
            "False comparison is accepted as PASS",
            expression(
                "GREATER_THAN",
                left=field("AMOUNT"),
                right=value(10000),
            ),
            "VALUE",
            False,
        ),
        HardeningTest(
            "BOOL-003",
            "Boolean Outcomes",
            "False membership result is accepted as PASS",
            expression(
                "IN",
                value=field("COUNTRY"),
                values=value(
                    [
                        "DE",
                        "FR",
                    ]
                ),
            ),
            "VALUE",
            False,
        ),
        # ==================================================================
        # BETWEEN
        # ==================================================================
        HardeningTest(
            "CMP-001",
            "Comparison",
            "BETWEEN returns True for value inside bounds",
            expression(
                "BETWEEN",
                value=field("AMOUNT"),
                min=value(5000),
                max=value(10000),
            ),
            "VALUE",
            True,
        ),
        HardeningTest(
            "CMP-002",
            "Comparison",
            "BETWEEN returns False for value outside bounds",
            expression(
                "BETWEEN",
                value=field("AMOUNT"),
                min=value(1000),
                max=value(5000),
            ),
            "VALUE",
            False,
        ),
        # ==================================================================
        # REGEX
        # ==================================================================
        HardeningTest(
            "STR-001",
            "String",
            "MATCH accepts a valid code",
            expression(
                "MATCH",
                value=field("CODE"),
                pattern=value(r"[A-Z]{3}[0-9]{3}"),
            ),
            "VALUE",
            True,
        ),
        HardeningTest(
            "STR-002",
            "String",
            "MATCH rejects an invalid code",
            expression(
                "MATCH",
                value=field("CODE"),
                pattern=value(r"[A-Z]{4}[0-9]{3}"),
            ),
            "VALUE",
            False,
        ),
        # ==================================================================
        # NESTED EXPRESSIONS
        # ==================================================================
        HardeningTest(
            "NEST-001",
            "Nested Expression",
            "Nested arithmetic comparison evaluates True",
            expression(
                "AND",
                operands=[
                    expression(
                        "EQUALS",
                        left=field("CUSTOMER_TYPE"),
                        right=value("PREMIUM"),
                    ),
                    expression(
                        "GREATER_THAN",
                        left=expression(
                            "MULTIPLY",
                            operands=[
                                field("QUANTITY"),
                                field("UNIT_PRICE"),
                            ],
                        ),
                        right=value(1000),
                    ),
                ],
            ),
            "VALUE",
            True,
        ),
        HardeningTest(
            "NEST-002",
            "Nested Expression",
            "Nested arithmetic comparison evaluates False",
            expression(
                "AND",
                operands=[
                    expression(
                        "EQUALS",
                        left=field("CUSTOMER_TYPE"),
                        right=value("STANDARD"),
                    ),
                    expression(
                        "GREATER_THAN",
                        left=expression(
                            "MULTIPLY",
                            operands=[
                                field("QUANTITY"),
                                field("UNIT_PRICE"),
                            ],
                        ),
                        right=value(1000),
                    ),
                ],
            ),
            "VALUE",
            False,
        ),
        # ==================================================================
        # CONDITIONAL
        # ==================================================================
        HardeningTest(
            "COND-001",
            "Conditional",
            "IF selects THEN branch",
            {
                "operator": "IF",
                "condition": expression(
                    "EQUALS",
                    left=field("CUSTOMER_TYPE"),
                    right=value("PREMIUM"),
                ),
                "then": value("HIGH"),
                "else": value("STANDARD"),
            },
            "VALUE",
            "HIGH",
        ),
        # ==================================================================
        # ERROR: MALFORMED
        # ==================================================================
        HardeningTest(
            "ERR-001",
            "Error Handling",
            "Missing operator is rejected",
            {
                "left": field("AMOUNT"),
                "right": value(100),
            },
            "INVALID_EXPRESSION",
        ),
        HardeningTest(
            "ERR-002",
            "Error Handling",
            "AND without operands is rejected",
            {"operator": "AND"},
            "INVALID_EXPRESSION",
        ),
        # ==================================================================
        # ERROR: MISSING REFERENCE
        # ==================================================================
        HardeningTest(
            "ERR-003",
            "Error Handling",
            "Unknown field reference is rejected",
            expression(
                "EQUALS",
                left=field("DOES_NOT_EXIST"),
                right=value(100),
            ),
            "EVALUATION_ERROR",
        ),
        # ==================================================================
        # ERROR: ARITHMETIC
        # ==================================================================
        HardeningTest(
            "ERR-004",
            "Error Handling",
            "Division by zero is rejected",
            expression(
                "DIVIDE",
                left=value(100),
                right=value(0),
            ),
            "EVALUATION_ERROR",
        ),
        # ==================================================================
        # DEFERRED VOCABULARY
        # ==================================================================
        HardeningTest(
            "DEF-001",
            "Capability Boundary",
            "Valid DERIVE vocabulary remains deferred",
            expression(
                "DERIVE",
                value=field("AMOUNT"),
            ),
            "DEFERRED",
        ),
        HardeningTest(
            "DEF-002",
            "Capability Boundary",
            "Valid REFERENCE vocabulary remains deferred",
            expression(
                "REFERENCE",
                value=field("CUSTOMER_ID"),
            ),
            "DEFERRED",
        ),
        # ==================================================================
        # UNKNOWN VOCABULARY
        # ==================================================================
        HardeningTest(
            "ERR-005",
            "Vocabulary Boundary",
            "Unknown operator is rejected",
            expression(
                "MAGIC_OPERATOR",
                value=value(100),
            ),
            "UNSUPPORTED_OPERATOR",
        ),
        # ==================================================================
        # DETERMINISM
        # ==================================================================
        HardeningTest(
            "DET-001",
            "Determinism",
            "Same expression produces same result",
            expression(
                "ADD",
                operands=[
                    value(100),
                    value(200),
                    value(300),
                ],
            ),
            "VALUE",
            600,
        ),
    ]


# ============================================================================
# TEST EXECUTION
# ============================================================================


def execute_test(
    test: HardeningTest,
    evaluator: ExpressionEvaluator,
    context: EvaluationContext,
) -> dict[str, Any]:

    try:

        actual = evaluator.evaluate(
            test.expression,
            context,
        )

        if test.expected_behavior == "VALUE":

            passed = actual == test.expected_value

            return {
                "test_id": test.test_id,
                "category": test.category,
                "description": test.description,
                "status": ("PASS" if passed else "FAIL"),
                "behavior": "VALUE",
                "expected": test.expected_value,
                "actual": actual,
                "error": None,
            }

        return {
            "test_id": test.test_id,
            "category": test.category,
            "description": test.description,
            "status": "FAIL",
            "behavior": "UNEXPECTED_EXECUTION",
            "expected": test.expected_behavior,
            "actual": actual,
            "error": (
                "Expression executed when " "an error/deferred result " "was expected."
            ),
        }

    except UnsupportedOperatorError as exc:

        expected = (
            test.expected_behavior == "DEFERRED"
            or test.expected_behavior == "UNSUPPORTED_OPERATOR"
        )

        return {
            "test_id": test.test_id,
            "category": test.category,
            "description": test.description,
            "status": ("PASS" if expected else "FAIL"),
            "behavior": (
                "DEFERRED"
                if (test.expected_behavior == "DEFERRED")
                else "UNSUPPORTED_OPERATOR"
            ),
            "expected": (test.expected_behavior),
            "actual": None,
            "error": str(exc),
        }

    except InvalidExpressionError as exc:

        expected = test.expected_behavior == "INVALID_EXPRESSION"

        return {
            "test_id": test.test_id,
            "category": test.category,
            "description": test.description,
            "status": ("PASS" if expected else "FAIL"),
            "behavior": "INVALID_EXPRESSION",
            "expected": (test.expected_behavior),
            "actual": None,
            "error": str(exc),
        }

    except EvaluationError as exc:

        expected = test.expected_behavior == "EVALUATION_ERROR"

        return {
            "test_id": test.test_id,
            "category": test.category,
            "description": test.description,
            "status": ("PASS" if expected else "FAIL"),
            "behavior": "EVALUATION_ERROR",
            "expected": (test.expected_behavior),
            "actual": None,
            "error": str(exc),
        }

    except Exception as exc:

        return {
            "test_id": test.test_id,
            "category": test.category,
            "description": test.description,
            "status": "FAIL",
            "behavior": "UNEXPECTED_ERROR",
            "expected": (test.expected_behavior),
            "actual": None,
            "error": (f"{type(exc).__name__}: " f"{exc}"),
        }


# ============================================================================
# CATEGORY SUMMARY
# ============================================================================


def build_category_summary(
    results: list[dict[str, Any]],
) -> dict[
    str,
    dict[str, Any],
]:

    categories: dict[
        str,
        dict[str, Any],
    ] = {}

    for result in results:

        category = result["category"]

        if category not in categories:

            categories[category] = {
                "total": 0,
                "passed": 0,
                "failed": 0,
                "status": "PASS",
            }

        categories[category]["total"] += 1

        if result["status"] == "PASS":

            categories[category]["passed"] += 1

        else:

            categories[category]["failed"] += 1

            categories[category]["status"] = "FAIL"

    return categories


# ============================================================================
# DETERMINISM TEST
# ============================================================================


def run_determinism_test() -> dict[
    str,
    Any,
]:

    evaluator = ExpressionEvaluator()

    context = build_context()

    test_expression = expression(
        "ADD",
        operands=[
            field("AMOUNT"),
            value(500),
            value(250),
        ],
    )

    first = evaluator.evaluate(
        test_expression,
        context,
    )

    second = evaluator.evaluate(
        test_expression,
        context,
    )

    passed = first == second

    return {
        "status": ("PASS" if passed else "FAIL"),
        "first_result": first,
        "second_result": second,
        "deterministic": passed,
    }


# ============================================================================
# OUTPUT
# ============================================================================


def save_results(
    results: list[dict[str, Any]],
    category_summary: dict[
        str,
        dict[str, Any],
    ],
    determinism: dict[
        str,
        Any,
    ],
) -> None:

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    total = len(results)

    passed = sum(result["status"] == "PASS" for result in results)

    failed = total - passed

    payload = {
        "experiment": ("020_declarative_generation_specification"),
        "stage": "020-C.1",
        "purpose": ("Expression engine " "validation hardening"),
        "classification": {
            "PASS": ("Expected result " "was produced."),
            "FAIL": ("Evaluation completed " "but produced an " "unexpected result."),
            "ERROR": ("Expression could not " "be evaluated."),
            "DEFERRED": (
                "Valid FORGE vocabulary " "is not executable " "at this stage."
            ),
        },
        "vocabulary": {
            "registered": len(RuleVocabulary.COMPLETE),
            "executable": len(RuleVocabulary.EXECUTABLE),
            "deferred": len(RuleVocabulary.DEFERRED),
        },
        "summary": {
            "total": total,
            "passed": passed,
            "failed": failed,
            "overall": ("PASS" if failed == 0 else "FAIL"),
        },
        "category_summary": (category_summary),
        "determinism": (determinism),
        "tests": results,
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


# ============================================================================
# REPORTING
# ============================================================================


def print_header() -> None:

    print()
    print("=" * 70)

    print("FORGE - Experiment 020-C.1: " "Expression Engine Validation Hardening")

    print("=" * 70)

    print("Experiment:     " "020_declarative_generation_specification")

    print("Stage:          020-C.1")

    print(
        "Purpose:        "
        "Validate expression outcomes, errors, "
        "and capability boundaries"
    )

    print()


def print_results(
    results: list[dict[str, Any]],
) -> None:

    print("Expression hardening validation:")

    current_category = None

    for result in results:

        category = result["category"]

        if category != current_category:

            current_category = category

            print()
            print(f"  {category}")

        print(
            f"    "
            f"{result['test_id']:<12}"
            f"{result['status']:<8}"
            f"{result['description']}"
        )

        if result["status"] == "FAIL":

            print(f"      Expected: " f"{result['expected']}")

            print(f"      Actual:   " f"{result['actual']}")

            print(f"      Error:    " f"{result['error']}")

    print()


def print_category_summary(
    summary: dict[
        str,
        dict[str, Any],
    ],
) -> None:

    print("Category validation:")

    for category, result in summary.items():

        print(
            f"  {category:<24}"
            f"{result['passed']}/"
            f"{result['total']} "
            f"{result['status']}"
        )

    print()


# ============================================================================
# MAIN
# ============================================================================


def main() -> int:

    print_header()

    print("Engine vocabulary:")

    print(f"  Registered operators: " f"{len(RuleVocabulary.COMPLETE)}")

    print(f"  Executable operators: " f"{len(RuleVocabulary.EXECUTABLE)}")

    print(f"  Deferred operators:   " f"{len(RuleVocabulary.DEFERRED)}")

    print()

    evaluator = ExpressionEvaluator()

    context = build_context()

    results = []

    for test in build_tests():

        results.append(
            execute_test(
                test,
                evaluator,
                context,
            )
        )

    print_results(results)

    category_summary = build_category_summary(results)

    print_category_summary(category_summary)

    determinism = run_determinism_test()

    print("Determinism validation:")

    print(f"  Same expression / same context: " f"{determinism['status']}")

    print(f"  First result:  " f"{determinism['first_result']}")

    print(f"  Second result: " f"{determinism['second_result']}")

    print()

    total = len(results)

    passed = sum(result["status"] == "PASS" for result in results)

    failed = total - passed

    overall = failed == 0 and determinism["status"] == "PASS"

    save_results(
        results,
        category_summary,
        determinism,
    )

    print("Experiment result:")

    print(f"  Tests passed: " f"{passed}/{total}")

    print(f"  Tests failed: " f"{failed}/{total}")

    print(
        f"  Boolean outcome handling: "
        f"{'PASS' if category_summary.get('Boolean Outcomes', {}).get('status') == 'PASS' else 'FAIL'}"
    )

    print(
        f"  Nested expressions: "
        f"{'PASS' if category_summary.get('Nested Expression', {}).get('status') == 'PASS' else 'FAIL'}"
    )

    print(
        f"  Error handling: "
        f"{'PASS' if category_summary.get('Error Handling', {}).get('status') == 'PASS' else 'FAIL'}"
    )

    print(
        f"  Capability boundary: "
        f"{'PASS' if category_summary.get('Capability Boundary', {}).get('status') == 'PASS' else 'FAIL'}"
    )

    print(
        f"  Vocabulary boundary: "
        f"{'PASS' if category_summary.get('Vocabulary Boundary', {}).get('status') == 'PASS' else 'FAIL'}"
    )

    print(f"  Determinism: " f"{determinism['status']}")

    print(f"  Overall: " f"{'PASS' if overall else 'FAIL'}")

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
