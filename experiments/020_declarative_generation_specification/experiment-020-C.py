"""
FORGE - Experiment 020-C: Declarative Rule and Expression Engine
=================================================================

Purpose
-------
This experiment establishes the first executable rule and expression
engine for FORGE.

Stage
-----
020-C - Declarative Rule and Expression Engine

This stage extends the declarative foundation established by:

    020-A - Specification Foundation
    020-B - Generic Generation
    020-B.1 - Execution Capability Assessment

The objective is to prove that FORGE business rules can be represented
as declarative expressions and evaluated generically without embedding
business-specific logic inside the generation engine.

Core Architecture
-----------------

    Declarative Expression
             |
             v
       Expression Parser
             |
             v
       Expression Tree
             |
             v
       Generic Evaluator
             |
             v
          Result


The evaluator operates on a record/context and does not contain
customer-specific, order-specific, or domain-specific business logic.

Supported Rule Vocabulary
-------------------------

Comparison:

    EQUALS
    NOT_EQUALS
    GREATER_THAN
    LESS_THAN
    GREATER_OR_EQUAL
    LESS_OR_EQUAL
    BETWEEN

Membership:

    IN
    NOT_IN

Null:

    IS_NULL
    IS_NOT_NULL

Logic:

    AND
    OR
    NOT
    XOR
    IMPLIES

Conditional:

    IF
    THEN
    ELSE

Arithmetic:

    ADD
    SUBTRACT
    MULTIPLY
    DIVIDE
    MODULO
    ABS
    MIN
    MAX
    ROUND
    FLOOR
    CEILING

String:

    CONCAT
    LENGTH
    CONTAINS
    STARTS_WITH
    ENDS_WITH
    MATCH
    UPPER
    LOWER
    TRIM
    REPLACE

Date / Time:

    DATE_ADD
    DATE_SUBTRACT
    DATE_DIFF

Data Access:

    REFERENCE
    LOOKUP
    SAMPLE
    DERIVE

Only the expression operators required for this stage are executable.
The remaining vocabulary is recognized but explicitly deferred.

Research Question
-----------------
Can a generic expression evaluator execute FORGE declarative rules
without requiring rule-specific Python business logic?

Hypothesis
----------
A controlled expression model can represent and evaluate common
business constraints and derived values generically.

The hypothesis is supported if:

    - comparison expressions evaluate correctly
    - logical expressions compose correctly
    - conditional expressions evaluate correctly
    - arithmetic expressions evaluate correctly
    - string expressions evaluate correctly
    - nested expressions evaluate correctly
    - the same evaluator works across different entities
    - no business-specific operator implementation is required

The hypothesis is rejected if business rules require custom Python
logic for each individual rule.

No machine learning, LLM, or production data is used.

Experiment
----------
020-C - Declarative Rule and Expression Engine

Author
------
Ranjoy Sen

Status
------
Experimental

How to Run
----------
From the repository root:

    uv run python experiments/020_declarative_generation_specification/experiment_020_c.py

Output
------
    experiments/020_declarative_generation_specification/output/

Important
---------
This experiment intentionally focuses on the rule/expression execution
layer. Advanced statistical distributions, relationship generation,
reference resolution, lookup execution, provenance, and LLM-based
natural-language translation are addressed separately.
"""

from __future__ import annotations

import json
import math
import re
import sys
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

# ============================================================================
# PATHS
# ============================================================================

EXPERIMENT_DIR = Path(__file__).resolve().parent

OUTPUT_DIR = EXPERIMENT_DIR / "output"

RESULT_OUTPUT_PATH = OUTPUT_DIR / "rule_expression_results.json"


# ============================================================================
# EXCEPTIONS
# ============================================================================


class ForgeExpressionError(Exception):
    """Base exception for expression evaluation."""


class UnsupportedOperatorError(ForgeExpressionError):
    """Raised when an operator is not executable."""


class InvalidExpressionError(ForgeExpressionError):
    """Raised when an expression is malformed."""


class EvaluationError(ForgeExpressionError):
    """Raised when expression evaluation fails."""


# ============================================================================
# EXECUTABLE RULE VOCABULARY
# ============================================================================


class RuleVocabulary:
    """
    Complete FORGE rule vocabulary.

    The registry describes what the specification language can express.
    The executable set describes what this stage implements.
    """

    COMPLETE = {
        "EQUALS",
        "NOT_EQUALS",
        "GREATER_THAN",
        "LESS_THAN",
        "GREATER_OR_EQUAL",
        "LESS_OR_EQUAL",
        "BETWEEN",
        "IN",
        "NOT_IN",
        "IS_NULL",
        "IS_NOT_NULL",
        "AND",
        "OR",
        "NOT",
        "XOR",
        "IMPLIES",
        "IF",
        "THEN",
        "ELSE",
        "ADD",
        "SUBTRACT",
        "MULTIPLY",
        "DIVIDE",
        "MODULO",
        "ABS",
        "MIN",
        "MAX",
        "ROUND",
        "FLOOR",
        "CEILING",
        "CONCAT",
        "LENGTH",
        "CONTAINS",
        "STARTS_WITH",
        "ENDS_WITH",
        "MATCH",
        "UPPER",
        "LOWER",
        "TRIM",
        "REPLACE",
        "DATE_ADD",
        "DATE_SUBTRACT",
        "DATE_DIFF",
        "REFERENCE",
        "LOOKUP",
        "SAMPLE",
        "DERIVE",
    }

    EXECUTABLE = {
        "EQUALS",
        "NOT_EQUALS",
        "GREATER_THAN",
        "LESS_THAN",
        "GREATER_OR_EQUAL",
        "LESS_OR_EQUAL",
        "BETWEEN",
        "IN",
        "NOT_IN",
        "IS_NULL",
        "IS_NOT_NULL",
        "AND",
        "OR",
        "NOT",
        "XOR",
        "IMPLIES",
        "IF",
        "ADD",
        "SUBTRACT",
        "MULTIPLY",
        "DIVIDE",
        "MODULO",
        "ABS",
        "MIN",
        "MAX",
        "ROUND",
        "FLOOR",
        "CEILING",
        "CONCAT",
        "LENGTH",
        "CONTAINS",
        "STARTS_WITH",
        "ENDS_WITH",
        "MATCH",
        "UPPER",
        "LOWER",
        "TRIM",
        "REPLACE",
        "DATE_ADD",
        "DATE_SUBTRACT",
        "DATE_DIFF",
    }

    DEFERRED = COMPLETE - EXECUTABLE


# ============================================================================
# EXPRESSION CONTEXT
# ============================================================================


@dataclass
class EvaluationContext:
    """
    Runtime values available to an expression.

    The evaluator knows nothing about the business meaning of the
    fields. It simply resolves field references from this context.
    """

    record: dict[str, Any]

    variables: dict[str, Any] | None = None

    def resolve(
        self,
        reference: str,
    ) -> Any:

        if reference in self.record:
            return self.record[reference]

        if self.variables and (reference in self.variables):
            return self.variables[reference]

        raise EvaluationError(
            f"Reference '{reference}' " "not found in evaluation context."
        )


# ============================================================================
# VALUE RESOLUTION
# ============================================================================


class ValueResolver:
    """
    Resolves literals and declarative references.

    Examples:

        {"value": 100}

        {"field": "AMOUNT"}

        {"field": "CUSTOMER_TYPE"}
    """

    def resolve(
        self,
        expression: Any,
        context: EvaluationContext,
    ) -> Any:

        if not isinstance(
            expression,
            dict,
        ):
            return expression

        if "value" in expression:
            return expression["value"]

        if "field" in expression:

            return context.resolve(expression["field"])

        if "expression" in expression:

            return ExpressionEvaluator().evaluate(
                expression["expression"],
                context,
            )

        raise InvalidExpressionError(f"Unable to resolve expression: " f"{expression}")


# ============================================================================
# EXPRESSION EVALUATOR
# ============================================================================


class ExpressionEvaluator:
    """
    Generic FORGE expression evaluator.

    The evaluator dispatches only on the controlled vocabulary operator.
    No domain-specific business logic is embedded here.
    """

    def __init__(self) -> None:

        self.resolver = ValueResolver()

    def evaluate(
        self,
        expression: dict[str, Any],
        context: EvaluationContext,
    ) -> Any:

        if not isinstance(
            expression,
            dict,
        ):
            raise InvalidExpressionError("Expression must be an object.")

        operator = expression.get("operator")

        if not operator:

            return self.resolver.resolve(
                expression,
                context,
            )

        if operator not in (RuleVocabulary.COMPLETE):
            raise UnsupportedOperatorError(f"Unknown operator: " f"{operator}")

        if operator not in (RuleVocabulary.EXECUTABLE):
            raise UnsupportedOperatorError(
                f"Operator '{operator}' "
                "is valid FORGE vocabulary "
                "but is not executable "
                "in 020-C."
            )

        method = getattr(
            self,
            f"_op_{operator.lower()}",
            None,
        )

        if method is None:
            raise UnsupportedOperatorError(
                f"Operator '{operator}' " "has no implementation."
            )

        return method(
            expression,
            context,
        )

    # ========================================================================
    # COMPARISON
    # ========================================================================

    def _op_equals(
        self,
        expression: dict[str, Any],
        context: EvaluationContext,
    ) -> bool:

        return self._operand(
            expression,
            "left",
            context,
        ) == self._operand(
            expression,
            "right",
            context,
        )

    def _op_not_equals(
        self,
        expression: dict[str, Any],
        context: EvaluationContext,
    ) -> bool:

        return self._operand(
            expression,
            "left",
            context,
        ) != self._operand(
            expression,
            "right",
            context,
        )

    def _op_greater_than(
        self,
        expression: dict[str, Any],
        context: EvaluationContext,
    ) -> bool:

        return self._operand(
            expression,
            "left",
            context,
        ) > self._operand(
            expression,
            "right",
            context,
        )

    def _op_less_than(
        self,
        expression: dict[str, Any],
        context: EvaluationContext,
    ) -> bool:

        return self._operand(
            expression,
            "left",
            context,
        ) < self._operand(
            expression,
            "right",
            context,
        )

    def _op_greater_or_equal(
        self,
        expression: dict[str, Any],
        context: EvaluationContext,
    ) -> bool:

        return self._operand(
            expression,
            "left",
            context,
        ) >= self._operand(
            expression,
            "right",
            context,
        )

    def _op_less_or_equal(
        self,
        expression: dict[str, Any],
        context: EvaluationContext,
    ) -> bool:

        return self._operand(
            expression,
            "left",
            context,
        ) <= self._operand(
            expression,
            "right",
            context,
        )

    def _op_between(
        self,
        expression: dict[str, Any],
        context: EvaluationContext,
    ) -> bool:

        value = self._operand(
            expression,
            "value",
            context,
        )

        minimum = self._operand(
            expression,
            "min",
            context,
        )

        maximum = self._operand(
            expression,
            "max",
            context,
        )

        return minimum <= value <= maximum

    # ========================================================================
    # MEMBERSHIP
    # ========================================================================

    def _op_in(
        self,
        expression: dict[str, Any],
        context: EvaluationContext,
    ) -> bool:

        value = self._operand(
            expression,
            "value",
            context,
        )

        values = self._operand(
            expression,
            "values",
            context,
        )

        return value in values

    def _op_not_in(
        self,
        expression: dict[str, Any],
        context: EvaluationContext,
    ) -> bool:

        value = self._operand(
            expression,
            "value",
            context,
        )

        values = self._operand(
            expression,
            "values",
            context,
        )

        return value not in values

    # ========================================================================
    # NULL
    # ========================================================================

    def _op_is_null(
        self,
        expression: dict[str, Any],
        context: EvaluationContext,
    ) -> bool:

        return (
            self._operand(
                expression,
                "value",
                context,
            )
            is None
        )

    def _op_is_not_null(
        self,
        expression: dict[str, Any],
        context: EvaluationContext,
    ) -> bool:

        return (
            self._operand(
                expression,
                "value",
                context,
            )
            is not None
        )

    # ========================================================================
    # LOGIC
    # ========================================================================

    def _op_and(
        self,
        expression: dict[str, Any],
        context: EvaluationContext,
    ) -> bool:

        operands = expression.get("operands")

        if not isinstance(
            operands,
            list,
        ):
            raise InvalidExpressionError("AND requires operands.")

        return all(
            bool(
                self.evaluate(
                    operand,
                    context,
                )
            )
            for operand in operands
        )

    def _op_or(
        self,
        expression: dict[str, Any],
        context: EvaluationContext,
    ) -> bool:

        operands = expression.get("operands")

        if not isinstance(
            operands,
            list,
        ):
            raise InvalidExpressionError("OR requires operands.")

        return any(
            bool(
                self.evaluate(
                    operand,
                    context,
                )
            )
            for operand in operands
        )

    def _op_not(
        self,
        expression: dict[str, Any],
        context: EvaluationContext,
    ) -> bool:

        return not bool(
            self._evaluate_operand(
                expression,
                "operand",
                context,
            )
        )

    def _op_xor(
        self,
        expression: dict[str, Any],
        context: EvaluationContext,
    ) -> bool:

        operands = expression.get("operands")

        if not isinstance(
            operands,
            list,
        ):

            raise InvalidExpressionError("XOR requires operands.")

        return (
            sum(
                bool(
                    self.evaluate(
                        operand,
                        context,
                    )
                )
                for operand in operands
            )
            == 1
        )

    def _op_implies(
        self,
        expression: dict[str, Any],
        context: EvaluationContext,
    ) -> bool:

        condition = bool(
            self._evaluate_operand(
                expression,
                "if",
                context,
            )
        )

        consequence = bool(
            self._evaluate_operand(
                expression,
                "then",
                context,
            )
        )

        return not condition or consequence

    # ========================================================================
    # CONDITIONAL
    # ========================================================================

    def _op_if(
        self,
        expression: dict[str, Any],
        context: EvaluationContext,
    ) -> Any:

        condition = bool(
            self._evaluate_operand(
                expression,
                "condition",
                context,
            )
        )

        if condition:

            return self._evaluate_operand(
                expression,
                "then",
                context,
            )

        return self._evaluate_operand(
            expression,
            "else",
            context,
        )

    # ========================================================================
    # ARITHMETIC
    # ========================================================================

    def _op_add(
        self,
        expression: dict[str, Any],
        context: EvaluationContext,
    ) -> Any:

        operands = self._operands(
            expression,
            context,
        )

        return sum(operands)

    def _op_subtract(
        self,
        expression: dict[str, Any],
        context: EvaluationContext,
    ) -> Any:

        left, right = self._binary(
            expression,
            context,
        )

        return left - right

    def _op_multiply(
        self,
        expression: dict[str, Any],
        context: EvaluationContext,
    ) -> Any:

        operands = self._operands(
            expression,
            context,
        )

        result = 1

        for operand in operands:
            result *= operand

        return result

    def _op_divide(
        self,
        expression: dict[str, Any],
        context: EvaluationContext,
    ) -> Any:

        left, right = self._binary(
            expression,
            context,
        )

        if right == 0:

            raise EvaluationError("Division by zero.")

        return left / right

    def _op_modulo(
        self,
        expression: dict[str, Any],
        context: EvaluationContext,
    ) -> Any:

        left, right = self._binary(
            expression,
            context,
        )

        return left % right

    def _op_abs(
        self,
        expression: dict[str, Any],
        context: EvaluationContext,
    ) -> Any:

        return abs(
            self._evaluate_operand(
                expression,
                "value",
                context,
            )
        )

    def _op_min(
        self,
        expression: dict[str, Any],
        context: EvaluationContext,
    ) -> Any:

        return min(
            self._operands(
                expression,
                context,
            )
        )

    def _op_max(
        self,
        expression: dict[str, Any],
        context: EvaluationContext,
    ) -> Any:

        return max(
            self._operands(
                expression,
                context,
            )
        )

    def _op_round(
        self,
        expression: dict[str, Any],
        context: EvaluationContext,
    ) -> Any:

        value = self._evaluate_operand(
            expression,
            "value",
            context,
        )

        digits = self._evaluate_operand(
            expression,
            "digits",
            context,
        )

        return round(
            value,
            digits,
        )

    def _op_floor(
        self,
        expression: dict[str, Any],
        context: EvaluationContext,
    ) -> int:

        return math.floor(
            self._evaluate_operand(
                expression,
                "value",
                context,
            )
        )

    def _op_ceiling(
        self,
        expression: dict[str, Any],
        context: EvaluationContext,
    ) -> int:

        return math.ceil(
            self._evaluate_operand(
                expression,
                "value",
                context,
            )
        )

    # ========================================================================
    # STRING
    # ========================================================================

    def _op_concat(
        self,
        expression: dict[str, Any],
        context: EvaluationContext,
    ) -> str:

        operands = self._operands(
            expression,
            context,
        )

        return "".join(str(value) for value in operands)

    def _op_length(
        self,
        expression: dict[str, Any],
        context: EvaluationContext,
    ) -> int:

        value = self._evaluate_operand(
            expression,
            "value",
            context,
        )

        return len(str(value))

    def _op_contains(
        self,
        expression: dict[str, Any],
        context: EvaluationContext,
    ) -> bool:

        value = str(
            self._evaluate_operand(
                expression,
                "value",
                context,
            )
        )

        search = str(
            self._evaluate_operand(
                expression,
                "search",
                context,
            )
        )

        return search in value

    def _op_starts_with(
        self,
        expression: dict[str, Any],
        context: EvaluationContext,
    ) -> bool:

        value = str(
            self._evaluate_operand(
                expression,
                "value",
                context,
            )
        )

        prefix = str(
            self._evaluate_operand(
                expression,
                "prefix",
                context,
            )
        )

        return value.startswith(prefix)

    def _op_ends_with(
        self,
        expression: dict[str, Any],
        context: EvaluationContext,
    ) -> bool:

        value = str(
            self._evaluate_operand(
                expression,
                "value",
                context,
            )
        )

        suffix = str(
            self._evaluate_operand(
                expression,
                "suffix",
                context,
            )
        )

        return value.endswith(suffix)

    def _op_match(
        self,
        expression: dict[str, Any],
        context: EvaluationContext,
    ) -> bool:

        value = str(
            self._evaluate_operand(
                expression,
                "value",
                context,
            )
        )

        pattern = str(
            self._evaluate_operand(
                expression,
                "pattern",
                context,
            )
        )

        return (
            re.fullmatch(
                pattern,
                value,
            )
            is not None
        )

    def _op_upper(
        self,
        expression: dict[str, Any],
        context: EvaluationContext,
    ) -> str:

        return str(
            self._evaluate_operand(
                expression,
                "value",
                context,
            )
        ).upper()

    def _op_lower(
        self,
        expression: dict[str, Any],
        context: EvaluationContext,
    ) -> str:

        return str(
            self._evaluate_operand(
                expression,
                "value",
                context,
            )
        ).lower()

    def _op_trim(
        self,
        expression: dict[str, Any],
        context: EvaluationContext,
    ) -> str:

        return str(
            self._evaluate_operand(
                expression,
                "value",
                context,
            )
        ).strip()

    def _op_replace(
        self,
        expression: dict[str, Any],
        context: EvaluationContext,
    ) -> str:

        value = str(
            self._evaluate_operand(
                expression,
                "value",
                context,
            )
        )

        old = str(
            self._evaluate_operand(
                expression,
                "old",
                context,
            )
        )

        new = str(
            self._evaluate_operand(
                expression,
                "new",
                context,
            )
        )

        return value.replace(
            old,
            new,
        )

    # ========================================================================
    # DATE / TIME
    # ========================================================================

    def _op_date_add(
        self,
        expression: dict[str, Any],
        context: EvaluationContext,
    ) -> Any:

        value = self._evaluate_operand(
            expression,
            "value",
            context,
        )

        days = int(
            self._evaluate_operand(
                expression,
                "days",
                context,
            )
        )

        parsed = self._parse_date(value)

        return parsed + timedelta(days=days)

    def _op_date_subtract(
        self,
        expression: dict[str, Any],
        context: EvaluationContext,
    ) -> Any:

        value = self._evaluate_operand(
            expression,
            "value",
            context,
        )

        days = int(
            self._evaluate_operand(
                expression,
                "days",
                context,
            )
        )

        parsed = self._parse_date(value)

        return parsed - timedelta(days=days)

    def _op_date_diff(
        self,
        expression: dict[str, Any],
        context: EvaluationContext,
    ) -> int:

        start = self._parse_date(
            self._evaluate_operand(
                expression,
                "start",
                context,
            )
        )

        end = self._parse_date(
            self._evaluate_operand(
                expression,
                "end",
                context,
            )
        )

        return (end - start).days

    # ========================================================================
    # HELPERS
    # ========================================================================

    def _operand(
        self,
        expression: dict[str, Any],
        key: str,
        context: EvaluationContext,
    ) -> Any:

        if key not in expression:

            raise InvalidExpressionError(f"Missing operand '{key}'.")

        return self._evaluate_operand(
            expression,
            key,
            context,
        )

    def _evaluate_operand(
        self,
        expression: dict[str, Any],
        key: str,
        context: EvaluationContext,
    ) -> Any:

        value = expression.get(key)

        if (
            isinstance(
                value,
                dict,
            )
            and "operator" in value
        ):

            return self.evaluate(
                value,
                context,
            )

        return self.resolver.resolve(
            value,
            context,
        )

    def _operands(
        self,
        expression: dict[str, Any],
        context: EvaluationContext,
    ) -> list[Any]:

        operands = expression.get("operands")

        if not isinstance(
            operands,
            list,
        ):

            raise InvalidExpressionError("Expression requires " "an operands list.")

        return [
            (
                self.evaluate(
                    operand,
                    context,
                )
                if isinstance(
                    operand,
                    dict,
                )
                and "operator" in operand
                else self.resolver.resolve(
                    operand,
                    context,
                )
            )
            for operand in operands
        ]

    def _binary(
        self,
        expression: dict[str, Any],
        context: EvaluationContext,
    ) -> tuple[Any, Any]:

        return (
            self._operand(
                expression,
                "left",
                context,
            ),
            self._operand(
                expression,
                "right",
                context,
            ),
        )

    @staticmethod
    def _parse_date(
        value: Any,
    ) -> date:

        if isinstance(
            value,
            datetime,
        ):
            return value.date()

        if isinstance(
            value,
            date,
        ):
            return value

        return date.fromisoformat(str(value))


# ============================================================================
# TEST CASE MODEL
# ============================================================================


@dataclass
class ExpressionTest:

    test_id: str
    category: str
    description: str
    expression: dict[str, Any]
    expected: Any


# ============================================================================
# TEST SUITE
# ============================================================================


def build_test_suite() -> list[ExpressionTest]:

    return [
        # ------------------------------------------------------------------
        # Comparison
        # ------------------------------------------------------------------
        ExpressionTest(
            "CMP-001",
            "Comparison",
            "Field equals literal",
            {
                "operator": "EQUALS",
                "left": {"field": "CUSTOMER_TYPE"},
                "right": {"value": "PREMIUM"},
            },
            True,
        ),
        ExpressionTest(
            "CMP-002",
            "Comparison",
            "Amount greater than threshold",
            {
                "operator": "GREATER_THAN",
                "left": {"field": "AMOUNT"},
                "right": {"value": 5000},
            },
            True,
        ),
        ExpressionTest(
            "CMP-003",
            "Comparison",
            "Amount between bounds",
            {
                "operator": "BETWEEN",
                "value": {"field": "AMOUNT"},
                "min": {"value": 1000},
                "max": {"value": 5000},
            },
            True,
        ),
        # ------------------------------------------------------------------
        # Membership
        # ------------------------------------------------------------------
        ExpressionTest(
            "MEM-001",
            "Membership",
            "Country is allowed",
            {
                "operator": "IN",
                "value": {"field": "COUNTRY"},
                "values": {
                    "value": [
                        "US",
                        "IN",
                        "DE",
                    ]
                },
            },
            True,
        ),
        ExpressionTest(
            "MEM-002",
            "Membership",
            "Status is not prohibited",
            {
                "operator": "NOT_IN",
                "value": {"field": "STATUS"},
                "values": {
                    "value": [
                        "CANCELLED",
                        "BLOCKED",
                    ]
                },
            },
            True,
        ),
        # ------------------------------------------------------------------
        # Null
        # ------------------------------------------------------------------
        ExpressionTest(
            "NULL-001",
            "Null",
            "Nullable field is null",
            {
                "operator": "IS_NULL",
                "value": {"field": "OPTIONAL_VALUE"},
            },
            True,
        ),
        ExpressionTest(
            "NULL-002",
            "Null",
            "Required field is not null",
            {
                "operator": "IS_NOT_NULL",
                "value": {"field": "CUSTOMER_ID"},
            },
            True,
        ),
        # ------------------------------------------------------------------
        # Logic
        # ------------------------------------------------------------------
        ExpressionTest(
            "LOG-001",
            "Logic",
            "Premium and high value",
            {
                "operator": "AND",
                "operands": [
                    {
                        "operator": "EQUALS",
                        "left": {"field": "CUSTOMER_TYPE"},
                        "right": {"value": "PREMIUM"},
                    },
                    {
                        "operator": "GREATER_THAN",
                        "left": {"field": "AMOUNT"},
                        "right": {"value": 5000},
                    },
                ],
            },
            True,
        ),
        ExpressionTest(
            "LOG-002",
            "Logic",
            "Premium or priority",
            {
                "operator": "OR",
                "operands": [
                    {
                        "operator": "EQUALS",
                        "left": {"field": "CUSTOMER_TYPE"},
                        "right": {"value": "PREMIUM"},
                    },
                    {
                        "operator": "EQUALS",
                        "left": {"field": "STATUS"},
                        "right": {"value": "PRIORITY"},
                    },
                ],
            },
            True,
        ),
        ExpressionTest(
            "LOG-003",
            "Logic",
            "Not cancelled",
            {
                "operator": "NOT",
                "operand": {
                    "operator": "EQUALS",
                    "left": {"field": "STATUS"},
                    "right": {"value": "CANCELLED"},
                },
            },
            True,
        ),
        ExpressionTest(
            "LOG-004",
            "Logic",
            "Premium implies high credit",
            {
                "operator": "IMPLIES",
                "if": {
                    "operator": "EQUALS",
                    "left": {"field": "CUSTOMER_TYPE"},
                    "right": {"value": "PREMIUM"},
                },
                "then": {
                    "operator": "GREATER_OR_EQUAL",
                    "left": {"field": "CREDIT_LIMIT"},
                    "right": {"value": 10000},
                },
            },
            True,
        ),
        # ------------------------------------------------------------------
        # Conditional
        # ------------------------------------------------------------------
        ExpressionTest(
            "COND-001",
            "Conditional",
            "Premium receives high credit limit",
            {
                "operator": "IF",
                "condition": {
                    "operator": "EQUALS",
                    "left": {"field": "CUSTOMER_TYPE"},
                    "right": {"value": "PREMIUM"},
                },
                "then": {"value": "HIGH"},
                "else": {"value": "STANDARD"},
            },
            "HIGH",
        ),
        # ------------------------------------------------------------------
        # Arithmetic
        # ------------------------------------------------------------------
        ExpressionTest(
            "ARITH-001",
            "Arithmetic",
            "Subtotal calculation",
            {
                "operator": "MULTIPLY",
                "operands": [
                    {"field": "QUANTITY"},
                    {"field": "UNIT_PRICE"},
                ],
            },
            50.0,
        ),
        ExpressionTest(
            "ARITH-002",
            "Arithmetic",
            "Net amount calculation",
            {
                "operator": "SUBTRACT",
                "left": {"field": "SUBTOTAL"},
                "right": {"field": "DISCOUNT_AMOUNT"},
            },
            850.0,
        ),
        ExpressionTest(
            "ARITH-003",
            "Arithmetic",
            "Rounded value",
            {
                "operator": "ROUND",
                "value": {"value": 123.4567},
                "digits": {"value": 2},
            },
            123.46,
        ),
        # ------------------------------------------------------------------
        # String
        # ------------------------------------------------------------------
        ExpressionTest(
            "STR-001",
            "String",
            "Construct order number",
            {
                "operator": "CONCAT",
                "operands": [
                    {"value": "ORD-"},
                    {"field": "ORDER_ID"},
                ],
            },
            "ORD-1001",
        ),
        ExpressionTest(
            "STR-002",
            "String",
            "Email contains domain",
            {
                "operator": "CONTAINS",
                "value": {"field": "EMAIL"},
                "search": {"value": "@example.com"},
            },
            True,
        ),
        ExpressionTest(
            "STR-003",
            "String",
            "Normalize code",
            {
                "operator": "UPPER",
                "value": {"field": "CODE"},
            },
            "ABC123",
        ),
        ExpressionTest(
            "STR-004",
            "String",
            "Regex validation",
            {
                "operator": "MATCH",
                "value": {"field": "CODE"},
                "pattern": {"value": r"[A-Z]{3}[0-9]{3}"},
            },
            True,
        ),
        # ------------------------------------------------------------------
        # Date
        # ------------------------------------------------------------------
        ExpressionTest(
            "DATE-001",
            "Date / Time",
            "Add delivery days",
            {
                "operator": "DATE_ADD",
                "value": {"field": "ORDER_DATE"},
                "days": {"value": 5},
            },
            date(
                2026,
                8,
                25,
            ),
        ),
        ExpressionTest(
            "DATE-002",
            "Date / Time",
            "Calculate delivery duration",
            {
                "operator": "DATE_DIFF",
                "start": {"field": "ORDER_DATE"},
                "end": {"field": "DELIVERY_DATE"},
            },
            5,
        ),
        # ------------------------------------------------------------------
        # Nested expression
        # ------------------------------------------------------------------
        ExpressionTest(
            "NEST-001",
            "Nested Expression",
            "Premium high-value rule",
            {
                "operator": "AND",
                "operands": [
                    {
                        "operator": "EQUALS",
                        "left": {"field": "CUSTOMER_TYPE"},
                        "right": {"value": "PREMIUM"},
                    },
                    {
                        "operator": "GREATER_THAN",
                        "left": {
                            "operator": "MULTIPLY",
                            "operands": [
                                {"field": "QUANTITY"},
                                {"field": "UNIT_PRICE"},
                            ],
                        },
                        "right": {"value": 1000},
                    },
                ],
            },
            True,
        ),
    ]


# ============================================================================
# SAMPLE CONTEXTS
# ============================================================================


def build_contexts() -> dict[
    str,
    EvaluationContext,
]:

    return {
        "ORDER_PREMIUM": EvaluationContext(
            record={
                "CUSTOMER_ID": "CUS001",
                "CUSTOMER_TYPE": "PREMIUM",
                "COUNTRY": "US",
                "AMOUNT": 7500,
                "CREDIT_LIMIT": 15000,
                "STATUS": "OPEN",
                "OPTIONAL_VALUE": None,
                "QUANTITY": 5,
                "UNIT_PRICE": 10.0,
                "SUBTOTAL": 1000.0,
                "DISCOUNT_AMOUNT": 150.0,
                "ORDER_ID": "1001",
                "EMAIL": "user@example.com",
                "CODE": "abc123",
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
        ),
    }


# ============================================================================
# TEST EXECUTION
# ============================================================================


def run_tests() -> list[dict[str, Any]]:

    evaluator = ExpressionEvaluator()

    contexts = build_contexts()

    results: list[dict[str, Any]] = []

    for test in build_test_suite():

        context = contexts["ORDER_PREMIUM"]

        try:

            actual = evaluator.evaluate(
                test.expression,
                context,
            )

            passed = actual == test.expected

            results.append(
                {
                    "test_id": test.test_id,
                    "category": test.category,
                    "description": (test.description),
                    "status": ("PASS" if passed else "FAIL"),
                    "expected": serialize(test.expected),
                    "actual": serialize(actual),
                    "error": None,
                }
            )

        except Exception as exc:

            results.append(
                {
                    "test_id": test.test_id,
                    "category": test.category,
                    "description": (test.description),
                    "status": "FAIL",
                    "expected": serialize(test.expected),
                    "actual": None,
                    "error": (f"{type(exc).__name__}: " f"{exc}"),
                }
            )

    return results


# ============================================================================
# DEFERRED OPERATOR TEST
# ============================================================================


def test_deferred_operator() -> dict[
    str,
    Any,
]:

    evaluator = ExpressionEvaluator()

    context = build_contexts()["ORDER_PREMIUM"]

    expression = {
        "operator": "DERIVE",
        "value": {"field": "AMOUNT"},
    }

    try:

        evaluator.evaluate(
            expression,
            context,
        )

    except UnsupportedOperatorError as exc:

        return {
            "operator": "DERIVE",
            "status": "PASS",
            "behavior": "DEFERRED",
            "message": str(exc),
        }

    except Exception as exc:

        return {
            "operator": "DERIVE",
            "status": "FAIL",
            "behavior": "UNEXPECTED_ERROR",
            "message": str(exc),
        }

    return {
        "operator": "DERIVE",
        "status": "FAIL",
        "behavior": "EXECUTED",
        "message": ("Deferred operator unexpectedly " "executed."),
    }


# ============================================================================
# SERIALIZATION
# ============================================================================


def serialize(
    value: Any,
) -> Any:

    if isinstance(
        value,
        (
            datetime,
            date,
        ),
    ):

        return value.isoformat()

    return value


def save_results(
    results: list[dict[str, Any]],
    deferred_result: dict[
        str,
        Any,
    ],
) -> None:

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    passed = sum(result["status"] == "PASS" for result in results)

    failed = len(results) - passed

    payload = {
        "experiment": ("020_declarative_generation_specification"),
        "stage": "020-C",
        "description": ("Declarative Rule and " "Expression Engine"),
        "vocabulary": {
            "complete": sorted(RuleVocabulary.COMPLETE),
            "executable": sorted(RuleVocabulary.EXECUTABLE),
            "deferred": sorted(RuleVocabulary.DEFERRED),
        },
        "test_summary": {
            "total": len(results),
            "passed": passed,
            "failed": failed,
            "overall": ("PASS" if failed == 0 else "FAIL"),
        },
        "tests": results,
        "deferred_operator_test": (deferred_result),
    }

    with RESULT_OUTPUT_PATH.open(
        "w",
        encoding="utf-8",
    ) as file:

        json.dump(
            payload,
            file,
            indent=2,
        )


# ============================================================================
# REPORTING
# ============================================================================


def print_header() -> None:

    print()
    print("=" * 70)

    print("FORGE - Experiment 020-C: " "Declarative Rule and Expression Engine")

    print("=" * 70)

    print("Experiment:     " "020_declarative_generation_specification")

    print("Stage:          020-C")

    print("Purpose:        " "Generic declarative expression evaluation")

    print()


def print_vocabulary() -> None:

    print("Rule vocabulary:")

    print(f"  Total registered: " f"{len(RuleVocabulary.COMPLETE)}")

    print(f"  Executable:       " f"{len(RuleVocabulary.EXECUTABLE)}")

    print(f"  Deferred:         " f"{len(RuleVocabulary.DEFERRED)}")

    print()

    print("Executable operators:")

    print("  " + ", ".join(sorted(RuleVocabulary.EXECUTABLE)))

    print()


def print_results(
    results: list[dict[str, Any]],
) -> None:

    print("Expression validation:")

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

            if result["error"]:

                print(f"      Error:    " f"{result['error']}")

    print()


# ============================================================================
# MAIN
# ============================================================================


def main() -> int:

    print_header()

    print_vocabulary()

    try:

        results = run_tests()

        print_results(results)

        deferred_result = test_deferred_operator()

        print("Capability boundary validation:")

        print(f"  Deferred operator handling: " f"{deferred_result['status']}")

        print(f"  DERIVE behavior: " f"{deferred_result['behavior']}")

        print()

        save_results(
            results,
            deferred_result,
        )

        passed = sum(result["status"] == "PASS" for result in results)

        failed = len(results) - passed

        all_passed = failed == 0 and deferred_result["status"] == "PASS"

        print("Rule engine assessment:")

        print(f"  Comparison operators: " f"{'PASS' if all_passed else 'FAIL'}")

        print(f"  Membership operators: " f"{'PASS' if all_passed else 'FAIL'}")

        print(f"  Null operators: " f"{'PASS' if all_passed else 'FAIL'}")

        print(f"  Logical composition: " f"{'PASS' if all_passed else 'FAIL'}")

        print(f"  Conditional evaluation: " f"{'PASS' if all_passed else 'FAIL'}")

        print(f"  Arithmetic expressions: " f"{'PASS' if all_passed else 'FAIL'}")

        print(f"  String expressions: " f"{'PASS' if all_passed else 'FAIL'}")

        print(f"  Date expressions: " f"{'PASS' if all_passed else 'FAIL'}")

        print(f"  Nested expressions: " f"{'PASS' if all_passed else 'FAIL'}")

        print(f"  Deferred capability handling: " f"{'PASS' if all_passed else 'FAIL'}")

        print()

        print("Experiment result:")

        print(f"  Tests passed: " f"{passed}/{len(results)}")

        print(f"  Tests failed: " f"{failed}/{len(results)}")

        print(f"  Overall: " f"{'PASS' if all_passed else 'FAIL'}")

        print()

        print("Output:")

        print(f"  Results: " f"{RESULT_OUTPUT_PATH}")

        print()

        if all_passed:

            print("Experiment completed successfully.")

            return 0

        print("Experiment completed with failures.")

        return 1

    except ForgeExpressionError as exc:

        print()

        print("Experiment result:")

        print("  Overall: FAIL")

        print(f"ERROR: {exc}")

        return 1


if __name__ == "__main__":
    sys.exit(main())
