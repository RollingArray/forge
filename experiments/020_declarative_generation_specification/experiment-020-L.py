"""
FORGE - Experiment 020-L: Declarative Derived and Conditional Generation
========================================================================

Stage:
    020-L

Purpose:
    Validate declarative derived fields, formulas, conditional generation,
    dependency planning, and context-aware execution.

Research Question
-----------------
Can FORGE translate declarative DERIVED, FORMULA, and CONDITIONAL rules
into a deterministic generation plan and generate values directly from
their declared dependencies?

Architectural Principle
-----------------------
A declarative generation rule must influence execution.

Example:

    QUANTITY
        +
    UNIT_PRICE
        |
        v
    LINE_AMOUNT

LINE_AMOUNT must not be independently generated and subsequently repaired.

Likewise:

    CUSTOMER_TYPE == PREMIUM
                |
                v
          CREDIT_LIMIT >= 5000

The conditional rule must influence CREDIT_LIMIT generation.

Execution model:

    Specification
         |
         v
    Expression Analysis
         |
         v
    Dependency Extraction
         |
         v
    Generation Planning
         |
         v
    Context-Aware Generation
         |
         v
    Validation

Scope
-----
Included:

    - DERIVED fields
    - FORMULA fields
    - arithmetic expressions
    - field dependencies
    - multi-level derived dependencies
    - CONDITIONAL generation
    - conditional minimum / maximum
    - deterministic generation
    - field-order independence
    - cycle detection
    - impossible conditional configuration
    - final validation

Excluded:

    - arbitrary symbolic mathematics
    - statistical correlation
    - external lookup
    - relationship-level generation
    - aggregation across records
    - complex temporal logic
    - arbitrary user-defined functions

Important Boundary
------------------
The experiment supports a controlled subset of arithmetic and conditional
expressions.

If FORGE cannot safely determine a generation strategy, it must BLOCK
rather than silently generate an arbitrary value.

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

RESULT_OUTPUT_PATH = OUTPUT_DIR / "derived_conditional_generation_results.json"

MASTER_SEED = 42


# ============================================================================
# CONSTANTS
# ============================================================================

DERIVED = "DERIVED"
FORMULA = "FORMULA"
CONDITIONAL = "CONDITIONAL"

ADD = "ADD"
SUBTRACT = "SUBTRACT"
MULTIPLY = "MULTIPLY"
DIVIDE = "DIVIDE"

EQUALS = "EQUALS"
NOT_EQUALS = "NOT_EQUALS"
GREATER_THAN = "GREATER_THAN"
LESS_THAN = "LESS_THAN"
GREATER_OR_EQUAL = "GREATER_OR_EQUAL"
LESS_OR_EQUAL = "LESS_OR_EQUAL"


# ============================================================================
# MODELS
# ============================================================================


@dataclass(frozen=True)
class FieldSpec:
    name: str
    minimum: float | None = None
    maximum: float | None = None
    type: str = "DECIMAL"
    strategy: str = "RANDOM"


@dataclass(frozen=True)
class Formula:
    operator: str
    operands: tuple[Any, ...]


@dataclass(frozen=True)
class DerivedRule:
    target_field: str
    expression: Formula


@dataclass(frozen=True)
class ConditionalRule:
    target_field: str
    condition_field: str
    condition_operator: str
    condition_value: Any
    then_minimum: float | None = None
    then_maximum: float | None = None
    else_minimum: float | None = None
    else_maximum: float | None = None


@dataclass(frozen=True)
class EntitySpec:
    name: str
    record_count: int
    fields: tuple[FieldSpec, ...]
    derived_rules: tuple[DerivedRule, ...] = ()
    conditional_rules: tuple[ConditionalRule, ...] = ()


@dataclass
class GenerationStep:
    field: str
    strategy: str
    dependencies: tuple[str, ...]


# ============================================================================
# DETERMINISTIC RANDOM STREAMS
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
# EXPRESSION DEPENDENCY EXTRACTION
# ============================================================================


def expression_fields(
    expression: Any,
) -> set[str]:

    dependencies: set[str] = set()

    if isinstance(
        expression,
        str,
    ):

        dependencies.add(expression)

        return dependencies

    if isinstance(
        expression,
        Formula,
    ):

        for operand in expression.operands:

            dependencies.update(expression_fields(operand))

    return dependencies


# ============================================================================
# EXPRESSION EVALUATION
# ============================================================================


def evaluate_formula(
    expression: Any,
    context: dict[str, Any],
) -> Any:

    if isinstance(
        expression,
        (int, float),
    ):

        return expression

    if isinstance(
        expression,
        str,
    ):

        if expression not in context:

            raise ValueError(f"Unknown field reference: " f"{expression}")

        return context[expression]

    if not isinstance(
        expression,
        Formula,
    ):

        raise ValueError("Unsupported expression node")

    values = [
        evaluate_formula(
            operand,
            context,
        )
        for operand in expression.operands
    ]

    if expression.operator == ADD:

        return values[0] + values[1]

    if expression.operator == SUBTRACT:

        return values[0] - values[1]

    if expression.operator == MULTIPLY:

        return values[0] * values[1]

    if expression.operator == DIVIDE:

        if values[1] == 0:

            raise ValueError("Division by zero")

        return values[0] / values[1]

    raise ValueError(f"Unsupported formula operator: " f"{expression.operator}")


# ============================================================================
# CONDITIONAL EVALUATION
# ============================================================================


def evaluate_condition(
    value: Any,
    operator: str,
    expected: Any,
) -> bool:

    if operator == EQUALS:
        return value == expected

    if operator == NOT_EQUALS:
        return value != expected

    if operator == GREATER_THAN:
        return value > expected

    if operator == LESS_THAN:
        return value < expected

    if operator == GREATER_OR_EQUAL:
        return value >= expected

    if operator == LESS_OR_EQUAL:
        return value <= expected

    raise ValueError(f"Unsupported condition operator: " f"{operator}")


# ============================================================================
# DEPENDENCY GRAPH
# ============================================================================


class DerivedDependencyGraph:

    def __init__(
        self,
        entity: EntitySpec,
    ) -> None:

        self.entity = entity

        self.fields = {field.name for field in entity.fields}

        self.edges: dict[
            str,
            set[str],
        ] = {field: set() for field in self.fields}

        self.reverse_edges: dict[
            str,
            set[str],
        ] = {field: set() for field in self.fields}

        self.errors: list[dict[str, Any]] = []

        self._build()

    def _add_dependency(
        self,
        source: str,
        target: str,
        rule: str,
    ) -> None:

        if source not in self.fields:

            self.errors.append(
                {
                    "rule": rule,
                    "reason": (f"Unknown dependency field " f"{source}"),
                }
            )

            return

        if target not in self.fields:

            self.errors.append(
                {
                    "rule": rule,
                    "reason": (f"Unknown target field " f"{target}"),
                }
            )

            return

        if source == target:

            self.errors.append(
                {
                    "rule": rule,
                    "reason": ("Self dependency"),
                }
            )

            return

        self.edges[source].add(target)

        self.reverse_edges[target].add(source)

    def _build(self) -> None:

        for rule in self.entity.derived_rules:

            dependencies = expression_fields(rule.expression)

            for dependency in dependencies:

                self._add_dependency(
                    dependency,
                    rule.target_field,
                    f"DERIVED:{rule.target_field}",
                )

        for rule in self.entity.conditional_rules:

            self._add_dependency(
                rule.condition_field,
                rule.target_field,
                f"CONDITIONAL:{rule.target_field}",
            )

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

        return any(visit(node) for node in sorted(self.fields))

    def generation_order(
        self,
    ) -> list[str] | None:

        if self.errors:
            return None

        if self.detect_cycle():
            return None

        incoming = {node: len(self.reverse_edges[node]) for node in self.fields}

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

        if len(order) != len(self.fields):

            return None

        return order


# ============================================================================
# GENERATION PLANNER
# ============================================================================


class DerivedGenerationPlanner:

    def __init__(
        self,
        entity: EntitySpec,
    ) -> None:

        self.entity = entity

        self.fields = {field.name: field for field in entity.fields}

        self.derived = {rule.target_field: rule for rule in entity.derived_rules}

        self.conditional = {
            rule.target_field: rule for rule in entity.conditional_rules
        }

    def plan(self) -> dict[str, Any]:

        graph = DerivedDependencyGraph(self.entity)

        order = graph.generation_order()

        if order is None:

            return {
                "status": "BLOCKED",
                "reason": ("Invalid or cyclic " "generation dependency graph."),
                "errors": graph.errors,
            }

        steps = []

        for field_name in order:

            if field_name in self.derived:

                strategy = DERIVED

            elif field_name in self.conditional:

                strategy = CONDITIONAL

            else:

                strategy = "INDEPENDENT"

            dependencies = sorted(graph.reverse_edges[field_name])

            steps.append(
                GenerationStep(
                    field=field_name,
                    strategy=strategy,
                    dependencies=tuple(dependencies),
                )
            )

        return {
            "status": "PASS",
            "order": order,
            "steps": [
                {
                    "field": step.field,
                    "strategy": step.strategy,
                    "dependencies": list(step.dependencies),
                }
                for step in steps
            ],
        }


# ============================================================================
# GENERATOR
# ============================================================================


class DerivedConditionalGenerator:

    def __init__(
        self,
        seed: int,
    ) -> None:

        self.seed = seed

    def generate(
        self,
        entity: EntitySpec,
    ) -> dict[str, Any]:

        planner = DerivedGenerationPlanner(entity)

        plan = planner.plan()

        if plan["status"] != "PASS":

            return {
                "status": "BLOCKED",
                "plan": plan,
            }

        field_map = {field.name: field for field in entity.fields}

        derived_map = {rule.target_field: rule for rule in entity.derived_rules}

        conditional_map = {rule.target_field: rule for rule in entity.conditional_rules}

        records = [{} for _ in range(entity.record_count)]

        for field_name in plan["order"]:

            field = field_map[field_name]

            rng = field_rng(
                self.seed,
                entity.name,
                field_name,
            )

            for record in records:

                # ------------------------------------------------------
                # DERIVED
                # ------------------------------------------------------

                if field_name in derived_map:

                    rule = derived_map[field_name]

                    value = evaluate_formula(
                        rule.expression,
                        record,
                    )

                    record[field_name] = self._normalize(
                        value,
                        field,
                    )

                    continue

                # ------------------------------------------------------
                # CONDITIONAL
                # ------------------------------------------------------

                if field_name in conditional_map:

                    rule = conditional_map[field_name]

                    condition = evaluate_condition(
                        record[rule.condition_field],
                        rule.condition_operator,
                        rule.condition_value,
                    )

                    if condition:

                        minimum = rule.then_minimum

                        maximum = rule.then_maximum

                    else:

                        minimum = rule.else_minimum

                        maximum = rule.else_maximum

                    if minimum is None or maximum is None:

                        return {
                            "status": "BLOCKED",
                            "plan": plan,
                            "reason": (
                                f"Conditional field "
                                f"{field_name} has "
                                "no feasible range."
                            ),
                        }

                    if minimum > maximum:

                        return {
                            "status": "BLOCKED",
                            "plan": plan,
                            "reason": (
                                f"Conditional range " f"for {field_name} " "is invalid."
                            ),
                        }

                    value = rng.uniform(
                        minimum,
                        maximum,
                    )

                    record[field_name] = self._normalize(
                        value,
                        field,
                    )

                    continue

                # ------------------------------------------------------
                # INDEPENDENT
                # ------------------------------------------------------

                minimum = field.minimum

                maximum = field.maximum

                if minimum is None or maximum is None:

                    return {
                        "status": "BLOCKED",
                        "plan": plan,
                        "reason": (
                            f"Field " f"{field_name} has " "no generation range."
                        ),
                    }

                if minimum > maximum:

                    return {
                        "status": "BLOCKED",
                        "plan": plan,
                        "reason": (f"Invalid range " f"for {field_name}."),
                    }

                value = rng.uniform(
                    minimum,
                    maximum,
                )

                record[field_name] = self._normalize(
                    value,
                    field,
                )

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
    def _normalize(
        value: Any,
        field: FieldSpec,
    ) -> Any:

        if field.type == "INTEGER":

            return int(round(value))

        return round(
            float(value),
            2,
        )


# ============================================================================
# VALIDATION
# ============================================================================


def validate_records(
    entity: EntitySpec,
    records: list[dict[str, Any]],
) -> dict[str, Any]:

    failures = []

    derived_map = {rule.target_field: rule for rule in entity.derived_rules}

    conditional_map = {rule.target_field: rule for rule in entity.conditional_rules}

    for index, record in enumerate(records):

        # --------------------------------------------------------------
        # Derived validation
        # --------------------------------------------------------------

        for target, rule in derived_map.items():

            expected = evaluate_formula(
                rule.expression,
                record,
            )

            actual = record[target]

            if round(
                float(actual),
                6,
            ) != round(
                float(expected),
                6,
            ):

                failures.append(
                    {
                        "record": index,
                        "field": target,
                        "type": DERIVED,
                        "expected": expected,
                        "actual": actual,
                    }
                )

        # --------------------------------------------------------------
        # Conditional validation
        # --------------------------------------------------------------

        for target, rule in conditional_map.items():

            condition = evaluate_condition(
                record[rule.condition_field],
                rule.condition_operator,
                rule.condition_value,
            )

            if condition:

                minimum = rule.then_minimum

                maximum = rule.then_maximum

            else:

                minimum = rule.else_minimum

                maximum = rule.else_maximum

            value = record[target]

            if minimum is None or maximum is None or value < minimum or value > maximum:

                failures.append(
                    {
                        "record": index,
                        "field": target,
                        "type": CONDITIONAL,
                        "value": value,
                        "minimum": minimum,
                        "maximum": maximum,
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


def formula_entity() -> EntitySpec:

    return EntitySpec(
        name="ORDER",
        record_count=100,
        fields=(
            FieldSpec(
                name="QUANTITY",
                minimum=1,
                maximum=20,
                type="INTEGER",
            ),
            FieldSpec(
                name="UNIT_PRICE",
                minimum=100,
                maximum=1000,
            ),
            FieldSpec(
                name="LINE_AMOUNT",
                type="DECIMAL",
                strategy=FORMULA,
            ),
        ),
        derived_rules=(
            DerivedRule(
                target_field="LINE_AMOUNT",
                expression=Formula(
                    operator=MULTIPLY,
                    operands=(
                        "QUANTITY",
                        "UNIT_PRICE",
                    ),
                ),
            ),
        ),
    )


def multi_level_derived_entity() -> EntitySpec:

    return EntitySpec(
        name="ORDER_CALCULATION",
        record_count=100,
        fields=(
            FieldSpec(
                name="QUANTITY",
                minimum=1,
                maximum=20,
                type="INTEGER",
            ),
            FieldSpec(
                name="UNIT_PRICE",
                minimum=100,
                maximum=1000,
            ),
            FieldSpec(
                name="DISCOUNT",
                minimum=0,
                maximum=500,
            ),
            FieldSpec(
                name="SUBTOTAL",
                strategy=DERIVED,
            ),
            FieldSpec(
                name="NET_AMOUNT",
                strategy=FORMULA,
            ),
        ),
        derived_rules=(
            DerivedRule(
                target_field="SUBTOTAL",
                expression=Formula(
                    operator=MULTIPLY,
                    operands=(
                        "QUANTITY",
                        "UNIT_PRICE",
                    ),
                ),
            ),
            DerivedRule(
                target_field="NET_AMOUNT",
                expression=Formula(
                    operator=SUBTRACT,
                    operands=(
                        "SUBTOTAL",
                        "DISCOUNT",
                    ),
                ),
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
                minimum=0,
                maximum=1,
                type="INTEGER",
            ),
            FieldSpec(
                name="CREDIT_LIMIT",
                strategy=CONDITIONAL,
            ),
        ),
        conditional_rules=(
            ConditionalRule(
                target_field="CREDIT_LIMIT",
                condition_field="CUSTOMER_TYPE",
                condition_operator=EQUALS,
                condition_value=1,
                then_minimum=5000,
                then_maximum=10000,
                else_minimum=500,
                else_maximum=5000,
            ),
        ),
    )


def conditional_derived_entity() -> EntitySpec:

    return EntitySpec(
        name="SHIPMENT",
        record_count=100,
        fields=(
            FieldSpec(
                name="IS_SHIPPED",
                minimum=0,
                maximum=1,
                type="INTEGER",
            ),
            FieldSpec(
                name="DELIVERY_DAYS",
                minimum=1,
                maximum=10,
                type="INTEGER",
            ),
            FieldSpec(
                name="DELIVERY_DURATION",
                strategy=DERIVED,
            ),
        ),
        derived_rules=(
            DerivedRule(
                target_field="DELIVERY_DURATION",
                expression=Formula(
                    operator=MULTIPLY,
                    operands=(
                        "DELIVERY_DAYS",
                        24,
                    ),
                ),
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
                strategy=DERIVED,
            ),
        ),
        derived_rules=(
            DerivedRule(
                target_field="B",
                expression=Formula(
                    operator=ADD,
                    operands=(
                        "A",
                        10,
                    ),
                ),
            ),
            DerivedRule(
                target_field="A",
                expression=Formula(
                    operator=ADD,
                    operands=(
                        "B",
                        10,
                    ),
                ),
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


def test_formula_generation() -> dict[str, Any]:

    result = DerivedConditionalGenerator(MASTER_SEED).generate(formula_entity())

    passed = result["status"] == "PASS" and result["validation"]["status"] == "PASS"

    return {
        "status": ("PASS" if passed else "FAIL"),
        "plan": result.get("plan"),
    }


def test_multi_level_derivation() -> dict[str, Any]:

    result = DerivedConditionalGenerator(MASTER_SEED).generate(
        multi_level_derived_entity()
    )

    passed = (
        result["status"] == "PASS"
        and result["validation"]["status"] == "PASS"
        and all(
            record["NET_AMOUNT"]
            == round(
                record["SUBTOTAL"] - record["DISCOUNT"],
                2,
            )
            for record in result["records"]
        )
    )

    return {
        "status": ("PASS" if passed else "FAIL"),
        "plan": result.get("plan"),
    }


def test_conditional_generation() -> dict[str, Any]:

    result = DerivedConditionalGenerator(MASTER_SEED).generate(conditional_entity())

    passed = result["status"] == "PASS" and result["validation"]["status"] == "PASS"

    return {
        "status": ("PASS" if passed else "FAIL"),
        "validation": result.get("validation"),
    }


def test_conditional_branches() -> dict[str, Any]:

    result = DerivedConditionalGenerator(MASTER_SEED).generate(conditional_entity())

    if result["status"] != "PASS":
        return {"status": "FAIL"}

    valid = True

    for record in result["records"]:

        if record["CUSTOMER_TYPE"] == 1:

            valid &= 5000 <= record["CREDIT_LIMIT"] <= 10000

        else:

            valid &= 500 <= record["CREDIT_LIMIT"] <= 5000

    return {
        "status": ("PASS" if valid else "FAIL"),
    }


def test_dependency_order() -> dict[str, Any]:

    entity = multi_level_derived_entity()

    plan = DerivedGenerationPlanner(entity).plan()

    if plan["status"] != "PASS":

        return {
            "status": "FAIL",
            "plan": plan,
        }

    order = plan["order"]

    passed = (
        order.index("QUANTITY") < order.index("SUBTOTAL")
        and order.index("UNIT_PRICE") < order.index("SUBTOTAL")
        and order.index("SUBTOTAL") < order.index("NET_AMOUNT")
        and order.index("DISCOUNT") < order.index("NET_AMOUNT")
    )

    return {
        "status": ("PASS" if passed else "FAIL"),
        "order": order,
    }


def test_field_order_independence() -> dict[str, Any]:

    original = formula_entity()

    reversed_entity = EntitySpec(
        name=original.name,
        record_count=original.record_count,
        fields=tuple(reversed(original.fields)),
        derived_rules=tuple(reversed(original.derived_rules)),
    )

    first = DerivedConditionalGenerator(MASTER_SEED).generate(original)

    second = DerivedConditionalGenerator(MASTER_SEED).generate(reversed_entity)

    passed = first["records"] == second["records"]

    return {
        "status": ("PASS" if passed else "FAIL"),
        "identical": passed,
    }


def test_reproducibility() -> dict[str, Any]:

    entity = multi_level_derived_entity()

    first = DerivedConditionalGenerator(MASTER_SEED).generate(entity)

    second = DerivedConditionalGenerator(MASTER_SEED).generate(entity)

    passed = first["records"] == second["records"]

    return {
        "status": ("PASS" if passed else "FAIL"),
        "identical": passed,
    }


def test_seed_sensitivity() -> dict[str, Any]:

    entity = formula_entity()

    first = DerivedConditionalGenerator(42).generate(entity)

    second = DerivedConditionalGenerator(43).generate(entity)

    passed = first["records"] != second["records"]

    return {
        "status": ("PASS" if passed else "FAIL"),
        "different": passed,
    }


def test_cycle_blocking() -> dict[str, Any]:

    plan = DerivedGenerationPlanner(cyclic_entity()).plan()

    passed = plan["status"] == "BLOCKED"

    return {
        "status": ("PASS" if passed else "FAIL"),
        "reason": plan.get("reason"),
    }


def test_derived_value_not_random() -> dict[str, Any]:

    entity = formula_entity()

    result = DerivedConditionalGenerator(MASTER_SEED).generate(entity)

    if result["status"] != "PASS":

        return {"status": "FAIL"}

    passed = all(
        record["LINE_AMOUNT"]
        == round(
            record["QUANTITY"] * record["UNIT_PRICE"],
            2,
        )
        for record in result["records"]
    )

    return {
        "status": ("PASS" if passed else "FAIL"),
    }


def test_division_safety() -> dict[str, Any]:

    expression = Formula(
        operator=DIVIDE,
        operands=(
            100,
            0,
        ),
    )

    try:

        evaluate_formula(
            expression,
            {},
        )

    except ValueError:

        return {"status": "PASS"}

    return {"status": "FAIL"}


# ============================================================================
# MAIN
# ============================================================================


def main() -> int:

    print()

    print("=" * 70)

    print("FORGE - Experiment 020-L: " "Declarative Derived and Conditional Generation")

    print("=" * 70)

    print("Experiment:     " "020_declarative_generation_specification")

    print("Stage:          020-L")

    print("Purpose:        " "Derived, formula, and conditional generation")

    print(f"Random seed:    {MASTER_SEED}")

    print()

    print("Generation architecture:")

    print("  Specification")

    print("       ↓")

    print("  Expression analysis")

    print("       ↓")

    print("  Dependency extraction")

    print("       ↓")

    print("  Generation planning")

    print("       ↓")

    print("  Context-aware generation")

    print("       ↓")

    print("  Validation")

    print()

    tests = [
        run_test(
            "Formula generation",
            test_formula_generation,
        ),
        run_test(
            "Multi-level derivation",
            test_multi_level_derivation,
        ),
        run_test(
            "Conditional generation",
            test_conditional_generation,
        ),
        run_test(
            "Conditional branch semantics",
            test_conditional_branches,
        ),
        run_test(
            "Dependency planning",
            test_dependency_order,
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
            "Cycle blocking",
            test_cycle_blocking,
        ),
        run_test(
            "Derived values are deterministic",
            test_derived_value_not_random,
        ),
        run_test(
            "Division safety",
            test_division_safety,
        ),
    ]

    print("Derived / conditional generation validation:")

    for test in tests:

        print(f"  " f"{test['name']:<38}" f"{test['status']}")

    passed = sum(test["status"] == "PASS" for test in tests)

    total = len(tests)

    overall = passed == total

    print()

    print("Experiment result:")

    print(f"  Formula generation:          " f"{tests[0]['status']}")

    print(f"  Multi-level derivation:       " f"{tests[1]['status']}")

    print(f"  Conditional generation:      " f"{tests[2]['status']}")

    print(f"  Conditional branches:         " f"{tests[3]['status']}")

    print(f"  Dependency planning:          " f"{tests[4]['status']}")

    print(f"  Field-order independence:      " f"{tests[5]['status']}")

    print(f"  Reproducibility:               " f"{tests[6]['status']}")

    print(f"  Seed sensitivity:              " f"{tests[7]['status']}")

    print(f"  Cycle safety:                  " f"{tests[8]['status']}")

    print(f"  Derived-value determinism:     " f"{tests[9]['status']}")

    print(f"  Expression safety:             " f"{tests[10]['status']}")

    print(f"  Tests passed:                  " f"{passed}/{total}")

    print(f"  Overall:                       " f"{'PASS' if overall else 'FAIL'}")

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    output = {
        "experiment": ("020_declarative_generation_specification"),
        "stage": "020-L",
        "purpose": ("Declarative derived and " "conditional generation"),
        "seed": MASTER_SEED,
        "tests": tests,
        "tests_passed": passed,
        "tests_total": total,
        "architecture": {
            "expression_analysis": True,
            "dependency_extraction": True,
            "generation_planning": True,
            "derived_generation": True,
            "conditional_generation": True,
            "context_aware_generation": True,
            "post_generation_repair": False,
        },
        "architectural_conclusion": (
            "Derived and conditional rules can "
            "participate in generation planning "
            "and can be executed directly from "
            "declared dependencies and context."
        ),
        "boundary": (
            "The experiment intentionally supports "
            "a controlled arithmetic expression "
            "subset and simple conditional ranges."
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
