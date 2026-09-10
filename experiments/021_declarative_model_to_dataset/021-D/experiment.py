#!/usr/bin/env python3
"""
======================================================================
FORGE - Experiment 021-D: Declarative Derived & Conditional Model to Dataset
======================================================================

Stage:          021-D - Derived & Conditional Model to Dataset
Experiment:     021_declarative_model_to_dataset
Purpose:        Validate transformation of a domain-neutral declarative
                relational model containing derived and conditional field
                behavior into an actual synthetic relational dataset
Specification:  specification.json
Random seed:    Declared by specification

Research question:
  Can FORGE consume a declarative relational model containing relationships,
  constraints, derived fields, and conditional fields and produce an actual
  synthetic dataset without domain-specific generation code?

Hypothesis:
  Derived and conditional field behavior can be expressed entirely in the
  declarative specification, converted into field-level generation
  dependencies, planned in dependency order, and executed into a relational
  dataset whose final records conform to the declared behavior.

What this experiment adds:
  021-A established basic model-to-dataset generation.
  021-B introduced declarative relationships and referential integrity.
  021-C introduced constraint-aware generation.
  021-D introduces deterministic behavioral dependencies:

      base field
          |
          v
      derived field
          |
          v
      conditional field

  The important architectural question is not simply whether FORGE can
  calculate a value. It is whether the calculation and its dependency
  requirements can be discovered from the specification rather than being
  encoded into the generator.

Architecture:
    specification.json
           |
           v
    Specification Validation
           |
           v
    Relationship Discovery
           |
           v
    Constraint Discovery
           |
           v
    Field Dependency Discovery
           |
           v
    Dependency-Aware Generation Planning
           |
           v
    Base Field Generation
           |
           v
    Derived / Conditional Generation
           |
           v
    Relationship Resolution
           |
           v
    Independent Dataset Validation
           |
           v
    CSV Dataset

Design principles:
  - Specification over hard-coded business logic.
  - No entity-specific generation behavior.
  - No field-specific generation behavior.
  - Derived expressions are interpreted generically.
  - Conditional rules are interpreted generically.
  - Dependency order is discovered rather than assumed.
  - Field declaration order must not determine correctness.
  - Entity declaration order must not determine correctness.
  - Relationship-managed fields are not independently generated.
  - Constraints are respected during generation.
  - No hidden fallback behavior.
  - No silent constraint relaxation.
  - No post-generation repair.
  - Deterministic execution for the same specification and seed.
  - Stochastic base fields remain sensitive to seed changes.

Validation focus:
  - Declarative specification structure
  - Relationship configuration
  - Dependency discovery
  - Dependency planning
  - Derived-field correctness
  - Conditional-field correctness
  - Chained dependency correctness
  - Constraint preservation
  - Referential integrity
  - Identity uniqueness
  - Population counts
  - CSV output correctness
  - Reproducibility
  - Seed sensitivity
  - Entity-order independence
  - Field-order independence

Input:
    specification.json

Output:
    output/dataset/<ENTITY>.csv
    output/generation_manifest.json
    output/derived_conditional_generation_results.json

Important:
  This experiment intentionally does not introduce statistical
  relationships, scenarios, cross-entity derivations, or advanced
  provenance. Those remain separate concerns.

  The implementation must operate only on the declarative specification.
  Entity names and business field names appearing in specification.json
  must not be required by the generation engine.
======================================================================
"""

from __future__ import annotations

import ast
import copy
import csv
import hashlib
import json
import math
import operator
import random
import sys
from collections import defaultdict, deque
from pathlib import Path
from typing import Any

# ============================================================================
# EXPERIMENT CONFIGURATION
# ============================================================================

EXPERIMENT_ID = "021-D"
EXPERIMENT_NAME = "021_declarative_model_to_dataset"

EXPERIMENT_DIR = Path(__file__).resolve().parent
SPECIFICATION_FILE = EXPERIMENT_DIR / "specification.json"

OUTPUT_DIR = EXPERIMENT_DIR / "output"
DATASET_DIR = OUTPUT_DIR / "dataset"

RESULTS_FILE = OUTPUT_DIR / "derived_conditional_generation_results.json"

MANIFEST_FILE = OUTPUT_DIR / "generation_manifest.json"


# ============================================================================
# SUPPORTED DECLARATIVE VOCABULARY
# ============================================================================

SUPPORTED_FIELD_TYPES = {
    "IDENTIFIER",
    "STRING",
    "INTEGER",
    "DECIMAL",
    "CATEGORICAL",
    "BOOLEAN",
}

SUPPORTED_DISTRIBUTIONS = {
    "UNIFORM",
    "DISCRETE_UNIFORM",
    "CATEGORICAL",
}

SUPPORTED_STRATEGIES = {
    "SEQUENTIAL_ID",
    "DERIVED",
    "CONDITIONAL",
}

SUPPORTED_CONDITION_OPERATORS = {
    "EQUALS",
    "NOT_EQUALS",
    "GREATER_THAN",
    "GREATER_THAN_OR_EQUAL",
    "LESS_THAN",
    "LESS_THAN_OR_EQUAL",
    "IN",
    "NOT_IN",
}

SUPPORTED_CONSTRAINT_OPERATORS = {
    "EQUALS",
    "NOT_EQUALS",
    "GREATER_THAN",
    "GREATER_THAN_OR_EQUAL",
    "LESS_THAN",
    "LESS_THAN_OR_EQUAL",
    "IN",
    "NOT_IN",
}

SUPPORTED_RELATIONSHIP_TYPES = {
    "ONE_TO_MANY",
    "ONE_TO_ONE",
}


# ============================================================================
# SPECIFICATION LOADING
# ============================================================================


def load_specification() -> dict[str, Any]:
    if not SPECIFICATION_FILE.exists():
        raise FileNotFoundError(f"Specification not found: {SPECIFICATION_FILE}")

    with SPECIFICATION_FILE.open(
        "r",
        encoding="utf-8",
    ) as handle:
        specification = json.load(handle)

    if not isinstance(specification, dict):
        raise ValueError("Specification root must be a JSON object.")

    return specification


# ============================================================================
# GENERIC LOOKUP HELPERS
# ============================================================================


def get_entity_map(
    specification: dict[str, Any],
) -> dict[str, dict[str, Any]]:
    return {entity["name"]: entity for entity in specification["entities"]}


def get_field_map(
    specification: dict[str, Any],
) -> dict[str, dict[str, dict[str, Any]]]:
    return {
        entity["name"]: {field["name"]: field for field in entity["fields"]}
        for entity in specification["entities"]
    }


def get_relationship_managed_fields(
    specification: dict[str, Any],
) -> set[tuple[str, str]]:
    managed: set[tuple[str, str]] = set()

    for relationship in specification.get(
        "relationships",
        [],
    ):
        target = relationship["to"]

        managed.add(
            (
                target["entity"],
                target["field"],
            )
        )

    return managed


# ============================================================================
# EXPRESSION SUPPORT
# ============================================================================

BINARY_OPERATORS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
}

UNARY_OPERATORS = {
    ast.UAdd: operator.pos,
    ast.USub: operator.neg,
}


def extract_expression_dependencies(
    expression: str,
) -> set[str]:
    """
    Return field names referenced by a declarative arithmetic expression.

    Example:
        "UNIT_PRICE * QUANTITY"

    becomes:
        {"UNIT_PRICE", "QUANTITY"}
    """

    try:
        tree = ast.parse(
            expression,
            mode="eval",
        )
    except SyntaxError as exc:
        raise ValueError(f"Invalid derived expression: {expression}") from exc

    dependencies: set[str] = set()

    for node in ast.walk(tree):
        if isinstance(node, ast.Name):
            dependencies.add(node.id)

        elif isinstance(
            node,
            (
                ast.Call,
                ast.Attribute,
                ast.Subscript,
                ast.Lambda,
            ),
        ):
            raise ValueError(
                "Derived expressions may contain only "
                "field references and arithmetic operations."
            )

    return dependencies


def evaluate_expression(
    expression: str,
    record: dict[str, Any],
) -> Any:
    """
    Safely evaluate the restricted arithmetic expression vocabulary.

    Python eval() is intentionally not used.
    """

    try:
        tree = ast.parse(
            expression,
            mode="eval",
        )
    except SyntaxError as exc:
        raise ValueError(f"Invalid derived expression: {expression}") from exc

    def evaluate_node(node: ast.AST) -> Any:
        if isinstance(node, ast.Expression):
            return evaluate_node(node.body)

        if isinstance(node, ast.Constant):
            if isinstance(
                node.value,
                (int, float),
            ):
                return node.value

            raise ValueError(
                "Only numeric constants are supported " "inside derived expressions."
            )

        if isinstance(node, ast.Name):
            if node.id not in record:
                raise ValueError(
                    f"Derived expression references " f"unavailable field: {node.id}"
                )

            return record[node.id]

        if isinstance(node, ast.BinOp):
            operation_type = type(node.op)

            if operation_type not in BINARY_OPERATORS:
                raise ValueError(
                    f"Unsupported arithmetic operator: " f"{operation_type.__name__}"
                )

            left = evaluate_node(node.left)
            right = evaluate_node(node.right)

            return BINARY_OPERATORS[operation_type](
                left,
                right,
            )

        if isinstance(node, ast.UnaryOp):
            operation_type = type(node.op)

            if operation_type not in UNARY_OPERATORS:
                raise ValueError(
                    f"Unsupported unary operator: " f"{operation_type.__name__}"
                )

            value = evaluate_node(node.operand)

            return UNARY_OPERATORS[operation_type](value)

        raise ValueError(f"Unsupported expression element: " f"{type(node).__name__}")

    return evaluate_node(tree)


# ============================================================================
# CONDITION / CONSTRAINT OPERATORS
# ============================================================================


def evaluate_operator(
    left: Any,
    operator_name: str,
    right: Any,
) -> bool:
    if operator_name == "EQUALS":
        return left == right

    if operator_name == "NOT_EQUALS":
        return left != right

    if operator_name == "GREATER_THAN":
        return left > right

    if operator_name == "GREATER_THAN_OR_EQUAL":
        return left >= right

    if operator_name == "LESS_THAN":
        return left < right

    if operator_name == "LESS_THAN_OR_EQUAL":
        return left <= right

    if operator_name == "IN":
        return left in right

    if operator_name == "NOT_IN":
        return left not in right

    raise ValueError(f"Unsupported operator: {operator_name}")


# ============================================================================
# SPECIFICATION VALIDATION
# ============================================================================


def validate_specification(
    specification: dict[str, Any],
) -> list[str]:
    errors: list[str] = []

    required_top_level = {
        "version",
        "vocabulary_version",
        "model",
        "generation",
        "entities",
        "relationships",
        "constraints",
        "dependencies",
        "statistical_behavior",
        "scenarios",
    }

    missing = sorted(required_top_level - set(specification))

    if missing:
        errors.append(f"Missing top-level sections: {missing}")

    generation = specification.get("generation")

    if not isinstance(generation, dict):
        errors.append("generation must be an object.")
    elif not isinstance(
        generation.get("seed"),
        int,
    ):
        errors.append("generation.seed must be an integer.")

    entities = specification.get("entities")

    if not isinstance(entities, list) or not entities:
        errors.append("Specification must contain at least one entity.")
        return errors

    entity_names: set[str] = set()
    fields_by_entity: dict[str, set[str]] = {}

    for entity in entities:
        if not isinstance(entity, dict):
            errors.append("Each entity must be an object.")
            continue

        entity_name = entity.get("name")

        if not isinstance(entity_name, str) or not entity_name:
            errors.append("Every entity must have a non-empty name.")
            continue

        if entity_name in entity_names:
            errors.append(f"Duplicate entity: {entity_name}")

        entity_names.add(entity_name)

        population = entity.get("population")

        if not isinstance(population, dict):
            errors.append(f"{entity_name}: population must " f"be an object.")

        elif (
            not isinstance(
                population.get("count"),
                int,
            )
            or population["count"] < 0
        ):
            errors.append(
                f"{entity_name}: population.count " f"must be a non-negative integer."
            )

        fields = entity.get("fields")

        if not isinstance(fields, list) or not fields:
            errors.append(f"{entity_name}: entity must contain " f"at least one field.")
            continue

        field_names: set[str] = set()

        for field in fields:
            if not isinstance(field, dict):
                errors.append(f"{entity_name}: every field " f"must be an object.")
                continue

            field_name = field.get("name")
            field_type = field.get("type")

            if not isinstance(field_name, str) or not field_name:
                errors.append(
                    f"{entity_name}: field name must " f"be a non-empty string."
                )
                continue

            if field_name in field_names:
                errors.append(f"{entity_name}: duplicate field " f"{field_name}")

            field_names.add(field_name)

            if field_type not in SUPPORTED_FIELD_TYPES:
                errors.append(
                    f"{entity_name}.{field_name}: "
                    f"unsupported field type "
                    f"{field_type}"
                )

            generation_rule = field.get("generation")

            if generation_rule is None:
                continue

            if not isinstance(
                generation_rule,
                dict,
            ):
                errors.append(
                    f"{entity_name}.{field_name}: " f"generation must be an object."
                )
                continue

            strategy = generation_rule.get("strategy")

            distribution = generation_rule.get("distribution")

            if strategy is not None:
                if strategy not in SUPPORTED_STRATEGIES:
                    errors.append(
                        f"{entity_name}.{field_name}: "
                        f"unsupported generation "
                        f"strategy {strategy}"
                    )

            elif distribution is not None:
                if distribution not in SUPPORTED_DISTRIBUTIONS:
                    errors.append(
                        f"{entity_name}.{field_name}: "
                        f"unsupported distribution "
                        f"{distribution}"
                    )

            else:
                errors.append(
                    f"{entity_name}.{field_name}: "
                    f"generation must declare either "
                    f"strategy or distribution."
                )

        fields_by_entity[entity_name] = field_names

    # ------------------------------------------------------------------
    # Relationship validation
    # ------------------------------------------------------------------

    for relationship in specification.get(
        "relationships",
        [],
    ):
        if not isinstance(relationship, dict):
            errors.append("Each relationship must be an object.")
            continue

        relationship_name = relationship.get(
            "name",
            "<unnamed>",
        )

        relationship_type = relationship.get("type")

        if relationship_type not in SUPPORTED_RELATIONSHIP_TYPES:
            errors.append(
                f"Relationship {relationship_name}: "
                f"unsupported type "
                f"{relationship_type}"
            )

        for endpoint_name in ("from", "to"):
            endpoint = relationship.get(endpoint_name)

            if not isinstance(endpoint, dict):
                errors.append(
                    f"Relationship {relationship_name}: "
                    f"{endpoint_name} must be an object."
                )
                continue

            entity_name = endpoint.get("entity")
            field_name = endpoint.get("field")

            if entity_name not in entity_names:
                errors.append(
                    f"Relationship {relationship_name}: "
                    f"unknown entity {entity_name}"
                )
                continue

            if field_name not in fields_by_entity.get(
                entity_name,
                set(),
            ):
                errors.append(
                    f"Relationship {relationship_name}: "
                    f"unknown field "
                    f"{entity_name}.{field_name}"
                )

    relationship_managed = get_relationship_managed_fields(specification)

    # ------------------------------------------------------------------
    # Generation behavior validation
    # ------------------------------------------------------------------

    for entity in entities:
        entity_name = entity.get("name")

        if entity_name not in fields_by_entity:
            continue

        entity_fields = fields_by_entity[entity_name]

        for field in entity.get("fields", []):
            field_name = field.get("name")

            if not field_name:
                continue

            generation_rule = field.get("generation")

            managed_by_relationship = (
                entity_name,
                field_name,
            ) in relationship_managed

            if generation_rule is None and not managed_by_relationship:
                errors.append(
                    f"{entity_name}.{field_name}: "
                    f"no executable generation "
                    f"behavior declared."
                )
                continue

            if generation_rule is None:
                continue

            strategy = generation_rule.get("strategy")

            if strategy == "DERIVED":
                expression = generation_rule.get("expression")

                if not isinstance(expression, str) or not expression.strip():
                    errors.append(
                        f"{entity_name}.{field_name}: "
                        f"DERIVED strategy requires "
                        f"expression."
                    )
                    continue

                try:
                    dependencies = extract_expression_dependencies(expression)
                except ValueError as exc:
                    errors.append(f"{entity_name}.{field_name}: " f"{exc}")
                    continue

                unknown = dependencies - entity_fields

                if unknown:
                    errors.append(
                        f"{entity_name}.{field_name}: "
                        f"derived expression references "
                        f"unknown fields "
                        f"{sorted(unknown)}"
                    )

            if strategy == "CONDITIONAL":
                condition = generation_rule.get("condition")

                if not isinstance(
                    condition,
                    dict,
                ):
                    errors.append(
                        f"{entity_name}.{field_name}: "
                        f"CONDITIONAL strategy requires "
                        f"condition."
                    )
                    continue

                source_field = condition.get("field")

                condition_operator = condition.get("operator")

                if source_field not in entity_fields:
                    errors.append(
                        f"{entity_name}.{field_name}: "
                        f"conditional rule references "
                        f"unknown field "
                        f"{source_field}"
                    )

                if condition_operator not in SUPPORTED_CONDITION_OPERATORS:
                    errors.append(
                        f"{entity_name}.{field_name}: "
                        f"unsupported conditional "
                        f"operator "
                        f"{condition_operator}"
                    )

                if "when_true" not in generation_rule:
                    errors.append(
                        f"{entity_name}.{field_name}: "
                        f"CONDITIONAL strategy requires "
                        f"when_true."
                    )

                if "when_false" not in generation_rule:
                    errors.append(
                        f"{entity_name}.{field_name}: "
                        f"CONDITIONAL strategy requires "
                        f"when_false."
                    )

    # ------------------------------------------------------------------
    # Constraint validation
    # ------------------------------------------------------------------

    for constraint in specification.get(
        "constraints",
        [],
    ):
        if not isinstance(constraint, dict):
            errors.append("Each constraint must be an object.")
            continue

        constraint_name = constraint.get(
            "name",
            "<unnamed>",
        )

        entity_name = constraint.get("entity")
        field_name = constraint.get("field")
        constraint_operator = constraint.get("operator")

        if entity_name not in entity_names:
            errors.append(
                f"Constraint {constraint_name}: " f"unknown entity {entity_name}"
            )
            continue

        if field_name not in fields_by_entity.get(
            entity_name,
            set(),
        ):
            errors.append(
                f"Constraint {constraint_name}: "
                f"unknown field "
                f"{entity_name}.{field_name}"
            )

        if constraint_operator not in SUPPORTED_CONSTRAINT_OPERATORS:
            errors.append(
                f"Constraint {constraint_name}: "
                f"unsupported operator "
                f"{constraint_operator}"
            )

    # ------------------------------------------------------------------
    # Dependency declaration validation
    # ------------------------------------------------------------------

    for dependency in specification.get(
        "dependencies",
        [],
    ):
        if not isinstance(dependency, dict):
            errors.append("Each dependency must be an object.")
            continue

        dependency_name = dependency.get(
            "name",
            "<unnamed>",
        )

        target = dependency.get("target")
        sources = dependency.get("sources")

        if not isinstance(target, dict):
            errors.append(
                f"Dependency {dependency_name}: " f"target must be an object."
            )
            continue

        target_entity = target.get("entity")
        target_field = target.get("field")

        if target_entity not in entity_names:
            errors.append(
                f"Dependency {dependency_name}: "
                f"unknown target entity "
                f"{target_entity}"
            )

        elif target_field not in fields_by_entity.get(
            target_entity,
            set(),
        ):
            errors.append(
                f"Dependency {dependency_name}: "
                f"unknown target field "
                f"{target_entity}.{target_field}"
            )

        if not isinstance(sources, list):
            errors.append(f"Dependency {dependency_name}: " f"sources must be a list.")
            continue

        for source in sources:
            if not isinstance(source, dict):
                errors.append(
                    f"Dependency {dependency_name}: " f"source must be an object."
                )
                continue

            source_entity = source.get("entity")
            source_field = source.get("field")

            if source_entity not in entity_names:
                errors.append(
                    f"Dependency {dependency_name}: "
                    f"unknown source entity "
                    f"{source_entity}"
                )

            elif source_field not in fields_by_entity.get(
                source_entity,
                set(),
            ):
                errors.append(
                    f"Dependency {dependency_name}: "
                    f"unknown source field "
                    f"{source_entity}.{source_field}"
                )

    return errors


# ============================================================================
# FIELD DEPENDENCY DISCOVERY
# ============================================================================


def discover_field_dependencies(
    specification: dict[str, Any],
) -> dict[str, dict[str, set[str]]]:
    """
    Build same-entity field dependencies from executable field rules.

    The executable field declaration is the source of truth for field
    generation ordering. The top-level dependencies section remains useful
    as declarative model metadata and is validated independently.
    """

    result: dict[
        str,
        dict[str, set[str]],
    ] = {}

    relationship_managed = get_relationship_managed_fields(specification)

    for entity in specification["entities"]:
        entity_name = entity["name"]

        dependencies: dict[
            str,
            set[str],
        ] = {}

        for field in entity["fields"]:
            field_name = field["name"]

            if (
                entity_name,
                field_name,
            ) in relationship_managed:
                continue

            generation_rule = field.get(
                "generation",
                {},
            )

            strategy = generation_rule.get("strategy")

            if strategy == "DERIVED":
                dependencies[field_name] = extract_expression_dependencies(
                    generation_rule["expression"]
                )

            elif strategy == "CONDITIONAL":
                dependencies[field_name] = {generation_rule["condition"]["field"]}

            else:
                dependencies[field_name] = set()

        result[entity_name] = dependencies

    return result


# ============================================================================
# FIELD GENERATION PLANNING
# ============================================================================


def build_field_generation_plan(
    entity: dict[str, Any],
    dependencies: dict[str, set[str]],
    relationship_managed_fields: set[tuple[str, str]],
) -> list[str]:
    """
    Topologically order executable fields.

    Field declaration order in specification.json must not determine
    generation correctness.
    """

    entity_name = entity["name"]

    executable_fields = {
        field["name"]
        for field in entity["fields"]
        if (
            entity_name,
            field["name"],
        )
        not in relationship_managed_fields
    }

    indegree = {field_name: 0 for field_name in executable_fields}

    dependents: dict[
        str,
        set[str],
    ] = defaultdict(set)

    for target, sources in dependencies.items():
        if target not in executable_fields:
            continue

        for source in sources:
            if source not in executable_fields:
                raise ValueError(
                    f"{entity_name}.{target} depends "
                    f"on field {source}, but that field "
                    f"is not independently available "
                    f"during entity generation."
                )

            dependents[source].add(target)
            indegree[target] += 1

    # Sorting here makes the plan canonical and independent of
    # specification field declaration order.
    ready = deque(
        sorted(field_name for field_name, degree in indegree.items() if degree == 0)
    )

    plan: list[str] = []

    while ready:
        current = ready.popleft()
        plan.append(current)

        for dependent in sorted(dependents[current]):
            indegree[dependent] -= 1

            if indegree[dependent] == 0:
                ready.append(dependent)

    if len(plan) != len(executable_fields):
        unresolved = sorted(
            field_name for field_name, degree in indegree.items() if degree > 0
        )

        raise ValueError(
            f"Cyclic or unresolved field dependency "
            f"in entity {entity_name}: "
            f"{unresolved}"
        )

    return plan


def build_all_field_generation_plans(
    specification: dict[str, Any],
) -> dict[str, list[str]]:
    dependencies = discover_field_dependencies(specification)

    relationship_managed = get_relationship_managed_fields(specification)

    plans: dict[str, list[str]] = {}

    for entity in specification["entities"]:
        entity_name = entity["name"]

        plans[entity_name] = build_field_generation_plan(
            entity,
            dependencies[entity_name],
            relationship_managed,
        )

    return plans


# ============================================================================
# ENTITY GENERATION PLANNING
# ============================================================================


def build_entity_generation_plan(
    specification: dict[str, Any],
) -> list[str]:
    """
    Parent entities must be available before child relationships are resolved.
    """

    entity_names = {entity["name"] for entity in specification["entities"]}

    indegree = {name: 0 for name in entity_names}

    children: dict[
        str,
        set[str],
    ] = defaultdict(set)

    for relationship in specification.get(
        "relationships",
        [],
    ):
        parent = relationship["from"]["entity"]
        child = relationship["to"]["entity"]

        if child not in children[parent]:
            children[parent].add(child)
            indegree[child] += 1

    ready = deque(sorted(name for name, degree in indegree.items() if degree == 0))

    plan: list[str] = []

    while ready:
        current = ready.popleft()
        plan.append(current)

        for child in sorted(children[current]):
            indegree[child] -= 1

            if indegree[child] == 0:
                ready.append(child)

    if len(plan) != len(entity_names):
        unresolved = sorted(name for name, degree in indegree.items() if degree > 0)

        raise ValueError(f"Cyclic entity relationship dependency: " f"{unresolved}")

    return plan


# ============================================================================
# DETERMINISTIC RANDOM STREAMS
# ============================================================================


def derive_seed(
    master_seed: int,
    *components: str,
) -> int:
    material = "::".join(
        [
            str(master_seed),
            *components,
        ]
    )

    digest = hashlib.sha256(material.encode("utf-8")).digest()

    return int.from_bytes(
        digest[:8],
        byteorder="big",
        signed=False,
    )


def field_random(
    master_seed: int,
    entity_name: str,
    field_name: str,
    record_index: int,
) -> random.Random:
    return random.Random(
        derive_seed(
            master_seed,
            entity_name,
            field_name,
            str(record_index),
        )
    )


def relationship_random(
    master_seed: int,
    relationship_name: str,
    record_index: int,
) -> random.Random:
    return random.Random(
        derive_seed(
            master_seed,
            "RELATIONSHIP",
            relationship_name,
            str(record_index),
        )
    )


# ============================================================================
# CONSTRAINT HELPERS
# ============================================================================


def constraints_for_field(
    specification: dict[str, Any],
    entity_name: str,
    field_name: str,
) -> list[dict[str, Any]]:
    return [
        constraint
        for constraint in specification.get(
            "constraints",
            [],
        )
        if (
            constraint.get("entity") == entity_name
            and constraint.get("field") == field_name
        )
    ]


def numeric_feasible_range(
    minimum: float,
    maximum: float,
    constraints: list[dict[str, Any]],
    integer: bool,
) -> tuple[float, float]:
    lower = minimum
    upper = maximum

    for constraint in constraints:
        op = constraint["operator"]
        value = constraint["value"]

        if op == "GREATER_THAN":
            if integer:
                lower = max(
                    lower,
                    math.floor(value) + 1,
                )
            else:
                lower = max(
                    lower,
                    math.nextafter(
                        float(value),
                        math.inf,
                    ),
                )

        elif op == "GREATER_THAN_OR_EQUAL":
            lower = max(
                lower,
                value,
            )

        elif op == "LESS_THAN":
            if integer:
                upper = min(
                    upper,
                    math.ceil(value) - 1,
                )
            else:
                upper = min(
                    upper,
                    math.nextafter(
                        float(value),
                        -math.inf,
                    ),
                )

        elif op == "LESS_THAN_OR_EQUAL":
            upper = min(
                upper,
                value,
            )

    if lower > upper:
        raise ValueError(
            "Declared constraints create an " "empty feasible numeric range."
        )

    return lower, upper


# ============================================================================
# GENERIC FIELD GENERATION
# ============================================================================


def generate_sequential_identifier(
    generation_rule: dict[str, Any],
    record_index: int,
) -> str:
    parameters = generation_rule.get(
        "parameters",
        {},
    )

    prefix = parameters.get(
        "prefix",
        "",
    )

    start = parameters.get(
        "start",
        1,
    )

    return f"{prefix}{start + record_index}"


def generate_distribution_value(
    specification: dict[str, Any],
    entity_name: str,
    field: dict[str, Any],
    record_index: int,
) -> Any:
    field_name = field["name"]

    generation_rule = field["generation"]
    distribution = generation_rule["distribution"]

    parameters = generation_rule.get(
        "parameters",
        {},
    )

    rng = field_random(
        specification["generation"]["seed"],
        entity_name,
        field_name,
        record_index,
    )

    field_constraints = constraints_for_field(
        specification,
        entity_name,
        field_name,
    )

    if distribution == "UNIFORM":
        minimum = parameters["minimum"]
        maximum = parameters["maximum"]

        minimum, maximum = numeric_feasible_range(
            minimum,
            maximum,
            field_constraints,
            integer=False,
        )

        return rng.uniform(
            minimum,
            maximum,
        )

    if distribution == "DISCRETE_UNIFORM":
        minimum = parameters["minimum"]
        maximum = parameters["maximum"]

        minimum, maximum = numeric_feasible_range(
            minimum,
            maximum,
            field_constraints,
            integer=True,
        )

        return rng.randint(
            int(math.ceil(minimum)),
            int(math.floor(maximum)),
        )

    if distribution == "CATEGORICAL":
        values = parameters["values"]

        weights = parameters.get("weights")

        feasible_values = [
            value
            for value in values
            if all(
                evaluate_operator(
                    value,
                    constraint["operator"],
                    constraint["value"],
                )
                for constraint in field_constraints
            )
        ]

        if not feasible_values:
            raise ValueError(
                f"{entity_name}.{field_name}: "
                f"constraints remove every "
                f"categorical value."
            )

        if weights is None:
            return rng.choice(feasible_values)

        if len(weights) != len(values):
            raise ValueError(
                f"{entity_name}.{field_name}: "
                f"categorical weights must match "
                f"the number of values."
            )

        feasible_weights = [
            weights[index]
            for index, value in enumerate(values)
            if value in feasible_values
        ]

        return rng.choices(
            feasible_values,
            weights=feasible_weights,
            k=1,
        )[0]

    raise ValueError(f"Unsupported distribution: " f"{distribution}")


def generate_field_value(
    specification: dict[str, Any],
    entity_name: str,
    field: dict[str, Any],
    record: dict[str, Any],
    record_index: int,
) -> Any:
    generation_rule = field["generation"]

    strategy = generation_rule.get("strategy")

    distribution = generation_rule.get("distribution")

    if strategy == "SEQUENTIAL_ID":
        return generate_sequential_identifier(
            generation_rule,
            record_index,
        )

    if strategy == "DERIVED":
        return evaluate_expression(
            generation_rule["expression"],
            record,
        )

    if strategy == "CONDITIONAL":
        condition = generation_rule["condition"]

        source_field = condition["field"]

        if source_field not in record:
            raise ValueError(
                f"{entity_name}.{field['name']}: "
                f"conditional source field "
                f"{source_field} is unavailable."
            )

        matched = evaluate_operator(
            record[source_field],
            condition["operator"],
            condition["value"],
        )

        if matched:
            return generation_rule["when_true"]

        return generation_rule["when_false"]

    if distribution is not None:
        return generate_distribution_value(
            specification,
            entity_name,
            field,
            record_index,
        )

    raise ValueError(
        f"No executable generation behavior "
        f"declared for "
        f"{entity_name}.{field['name']}."
    )


def normalize_record_field_order(
    specification: dict[str, Any],
    datasets: dict[
        str,
        list[dict[str, Any]],
    ],
) -> None:
    """
    Restore every generated record to the field order declared
    by specification.json.

    Relationship resolution may populate relationship-managed fields
    after normal field generation. This normalization ensures that the
    in-memory dataset follows the canonical schema defined by the
    specification.
    """

    entity_map = get_entity_map(specification)

    for entity_name, records in datasets.items():
        expected_fields = [field["name"] for field in entity_map[entity_name]["fields"]]

        for record in records:
            normalized = {
                field_name: record[field_name] for field_name in expected_fields
            }

            record.clear()
            record.update(normalized)


# ============================================================================
# ENTITY GENERATION
# ============================================================================


def generate_entity_records(
    specification: dict[str, Any],
    entity: dict[str, Any],
    field_plan: list[str],
) -> list[dict[str, Any]]:
    entity_name = entity["name"]

    fields = {field["name"]: field for field in entity["fields"]}

    record_count = entity["population"]["count"]

    records: list[dict[str, Any]] = []

    for record_index in range(record_count):
        generated: dict[
            str,
            Any,
        ] = {}

        for field_name in field_plan:
            field = fields[field_name]

            generated[field_name] = generate_field_value(
                specification,
                entity_name,
                field,
                generated,
                record_index,
            )

        # Restore specification field order in the final record.
        final_record: dict[
            str,
            Any,
        ] = {}

        for field in entity["fields"]:
            field_name = field["name"]

            if field_name in generated:
                final_record[field_name] = generated[field_name]

        records.append(final_record)

    return records


# ============================================================================
# RELATIONSHIP RESOLUTION
# ============================================================================


def resolve_relationships(
    specification: dict[str, Any],
    datasets: dict[
        str,
        list[dict[str, Any]],
    ],
) -> None:
    master_seed = specification["generation"]["seed"]

    for relationship in specification.get(
        "relationships",
        [],
    ):
        relationship_name = relationship["name"]

        relationship_type = relationship["type"]

        source = relationship["from"]
        target = relationship["to"]

        parent_records = datasets[source["entity"]]

        child_records = datasets[target["entity"]]

        parent_values = [record[source["field"]] for record in parent_records]

        if child_records and not parent_values:
            raise ValueError(
                f"Relationship "
                f"{relationship_name} cannot be "
                f"resolved because parent entity "
                f"{source['entity']} has no records."
            )

        if relationship_type == "ONE_TO_MANY":
            for record_index, record in enumerate(child_records):
                rng = relationship_random(
                    master_seed,
                    relationship_name,
                    record_index,
                )

                record[target["field"]] = rng.choice(parent_values)

        elif relationship_type == "ONE_TO_ONE":
            if len(child_records) > len(parent_values):
                raise ValueError(
                    f"Relationship "
                    f"{relationship_name}: "
                    f"ONE_TO_ONE target population "
                    f"exceeds source population."
                )

            ordered_parent_values = list(parent_values)

            rng = random.Random(
                derive_seed(
                    master_seed,
                    "RELATIONSHIP",
                    relationship_name,
                    "ONE_TO_ONE",
                )
            )

            rng.shuffle(ordered_parent_values)

            for record, value in zip(
                child_records,
                ordered_parent_values,
            ):
                record[target["field"]] = value

        else:
            raise ValueError(f"Unsupported relationship type: " f"{relationship_type}")


# ============================================================================
# COMPLETE DATASET GENERATION
# ============================================================================


def generate_dataset(
    specification: dict[str, Any],
) -> tuple[
    dict[str, list[dict[str, Any]]],
    list[str],
    dict[str, list[str]],
]:
    entity_map = get_entity_map(specification)

    entity_plan = build_entity_generation_plan(specification)

    field_plans = build_all_field_generation_plans(specification)

    datasets: dict[
        str,
        list[dict[str, Any]],
    ] = {}

    for entity_name in entity_plan:
        entity = entity_map[entity_name]

        datasets[entity_name] = generate_entity_records(
            specification,
            entity,
            field_plans[entity_name],
        )

    resolve_relationships(
        specification,
        datasets,
    )

    normalize_record_field_order(
        specification,
        datasets,
    )

    return (
        datasets,
        entity_plan,
        field_plans,
    )


# ============================================================================
# DATASET VALIDATION
# ============================================================================


def validate_population_counts(
    specification: dict[str, Any],
    datasets: dict[
        str,
        list[dict[str, Any]],
    ],
) -> bool:
    for entity in specification["entities"]:
        if (
            len(
                datasets.get(
                    entity["name"],
                    [],
                )
            )
            != entity["population"]["count"]
        ):
            return False

    return True


def validate_field_presence(
    specification: dict[str, Any],
    datasets: dict[
        str,
        list[dict[str, Any]],
    ],
) -> bool:
    for entity in specification["entities"]:
        expected_fields = [field["name"] for field in entity["fields"]]

        for record in datasets[entity["name"]]:
            if list(record.keys()) != expected_fields:
                return False

    return True


def validate_identity_uniqueness(
    specification: dict[str, Any],
    datasets: dict[
        str,
        list[dict[str, Any]],
    ],
) -> bool:
    for entity in specification["entities"]:
        entity_name = entity["name"]

        for field in entity["fields"]:
            if field["type"] != "IDENTIFIER":
                continue

            generation_rule = field.get(
                "generation",
                {},
            )

            if generation_rule.get("strategy") != "SEQUENTIAL_ID":
                continue

            values = [record[field["name"]] for record in datasets[entity_name]]

            if len(values) != len(set(values)):
                return False

    return True


def validate_referential_integrity(
    specification: dict[str, Any],
    datasets: dict[
        str,
        list[dict[str, Any]],
    ],
) -> bool:
    for relationship in specification.get(
        "relationships",
        [],
    ):
        source = relationship["from"]
        target = relationship["to"]

        valid_parent_values = {
            record[source["field"]] for record in datasets[source["entity"]]
        }

        for record in datasets[target["entity"]]:
            if record[target["field"]] not in valid_parent_values:
                return False

    return True


def validate_constraints(
    specification: dict[str, Any],
    datasets: dict[
        str,
        list[dict[str, Any]],
    ],
) -> bool:
    for constraint in specification.get(
        "constraints",
        [],
    ):
        entity_name = constraint["entity"]
        field_name = constraint["field"]

        for record in datasets[entity_name]:
            if not evaluate_operator(
                record[field_name],
                constraint["operator"],
                constraint["value"],
            ):
                return False

    return True


def validate_derived_fields(
    specification: dict[str, Any],
    datasets: dict[
        str,
        list[dict[str, Any]],
    ],
) -> bool:
    for entity in specification["entities"]:
        entity_name = entity["name"]

        for field in entity["fields"]:
            generation_rule = field.get(
                "generation",
                {},
            )

            if generation_rule.get("strategy") != "DERIVED":
                continue

            expression = generation_rule["expression"]

            for record in datasets[entity_name]:
                expected = evaluate_expression(
                    expression,
                    record,
                )

                actual = record[field["name"]]

                if isinstance(
                    expected,
                    float,
                ) or isinstance(
                    actual,
                    float,
                ):
                    if not math.isclose(
                        float(actual),
                        float(expected),
                        rel_tol=1e-12,
                        abs_tol=1e-12,
                    ):
                        return False

                elif actual != expected:
                    return False

    return True


def validate_conditional_fields(
    specification: dict[str, Any],
    datasets: dict[
        str,
        list[dict[str, Any]],
    ],
) -> bool:
    for entity in specification["entities"]:
        entity_name = entity["name"]

        for field in entity["fields"]:
            generation_rule = field.get(
                "generation",
                {},
            )

            if generation_rule.get("strategy") != "CONDITIONAL":
                continue

            condition = generation_rule["condition"]

            for record in datasets[entity_name]:
                matched = evaluate_operator(
                    record[condition["field"]],
                    condition["operator"],
                    condition["value"],
                )

                expected = (
                    generation_rule["when_true"]
                    if matched
                    else generation_rule["when_false"]
                )

                if record[field["name"]] != expected:
                    return False

    return True


def validate_chained_dependencies(
    specification: dict[str, Any],
    field_dependencies: dict[
        str,
        dict[str, set[str]],
    ],
) -> bool:
    """
    Confirm that at least one generated field depends on another
    non-base generated field.

    This makes the 021-D experiment prove an actual dependency chain
    rather than only independent one-hop transformations.
    """

    field_map = get_field_map(specification)

    for entity_name, dependency_map in field_dependencies.items():
        for target, sources in dependency_map.items():
            for source in sources:
                source_field = field_map[entity_name][source]

                source_strategy = source_field.get(
                    "generation",
                    {},
                ).get("strategy")

                if source_strategy in {
                    "DERIVED",
                    "CONDITIONAL",
                }:
                    return True

    return False


def validate_dataset(
    specification: dict[str, Any],
    datasets: dict[
        str,
        list[dict[str, Any]],
    ],
) -> dict[str, bool]:
    field_dependencies = discover_field_dependencies(specification)

    return {
        "dataset_structure": (
            set(datasets) == {entity["name"] for entity in specification["entities"]}
        ),
        "population_counts": (
            validate_population_counts(
                specification,
                datasets,
            )
        ),
        "field_presence": (
            validate_field_presence(
                specification,
                datasets,
            )
        ),
        "identity_uniqueness": (
            validate_identity_uniqueness(
                specification,
                datasets,
            )
        ),
        "referential_integrity": (
            validate_referential_integrity(
                specification,
                datasets,
            )
        ),
        "constraint_preservation": (
            validate_constraints(
                specification,
                datasets,
            )
        ),
        "derived_field_correctness": (
            validate_derived_fields(
                specification,
                datasets,
            )
        ),
        "conditional_field_correctness": (
            validate_conditional_fields(
                specification,
                datasets,
            )
        ),
        "chained_dependency_correctness": (
            validate_chained_dependencies(
                specification,
                field_dependencies,
            )
        ),
    }


# ============================================================================
# CSV OUTPUT
# ============================================================================


def write_csv_datasets(
    specification: dict[str, Any],
    datasets: dict[
        str,
        list[dict[str, Any]],
    ],
) -> list[Path]:
    DATASET_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    paths: list[Path] = []

    entity_map = get_entity_map(specification)

    for entity_name in sorted(datasets):
        records = datasets[entity_name]

        fieldnames = [field["name"] for field in entity_map[entity_name]["fields"]]

        path = DATASET_DIR / f"{entity_name}.csv"

        with path.open(
            "w",
            encoding="utf-8",
            newline="",
        ) as handle:
            writer = csv.DictWriter(
                handle,
                fieldnames=fieldnames,
            )

            writer.writeheader()
            writer.writerows(records)

        paths.append(path)

    return paths


def read_csv_datasets(
    specification: dict[str, Any],
    csv_paths: list[Path],
) -> dict[
    str,
    list[dict[str, str]],
]:
    """
    Read final CSV artifacts back from disk.

    This is intentionally separate from in-memory validation so that
    021-D validates the actual model-to-dataset boundary.
    """

    entity_names = {entity["name"] for entity in specification["entities"]}

    datasets: dict[
        str,
        list[dict[str, str]],
    ] = {}

    for path in csv_paths:
        entity_name = path.stem

        if entity_name not in entity_names:
            continue

        with path.open(
            "r",
            encoding="utf-8",
            newline="",
        ) as handle:
            datasets[entity_name] = list(csv.DictReader(handle))

    return datasets


def validate_csv_artifacts(
    specification: dict[str, Any],
    csv_paths: list[Path],
) -> bool:
    csv_datasets = read_csv_datasets(
        specification,
        csv_paths,
    )

    if set(csv_datasets) != {entity["name"] for entity in specification["entities"]}:
        return False

    for entity in specification["entities"]:
        entity_name = entity["name"]

        if len(csv_datasets[entity_name]) != entity["population"]["count"]:
            return False

        expected_fields = [field["name"] for field in entity["fields"]]

        for record in csv_datasets[entity_name]:
            if list(record.keys()) != expected_fields:
                return False

    return True


# ============================================================================
# MANIFEST / RESULTS
# ============================================================================


def write_manifest(
    specification: dict[str, Any],
    datasets: dict[
        str,
        list[dict[str, Any]],
    ],
    entity_plan: list[str],
    field_plans: dict[str, list[str]],
    csv_paths: list[Path],
) -> Path:
    derived_fields: list[str] = []
    conditional_fields: list[str] = []

    for entity in specification["entities"]:
        for field in entity["fields"]:
            strategy = field.get(
                "generation",
                {},
            ).get("strategy")

            qualified = f"{entity['name']}." f"{field['name']}"

            if strategy == "DERIVED":
                derived_fields.append(qualified)

            elif strategy == "CONDITIONAL":
                conditional_fields.append(qualified)

    manifest = {
        "experiment": EXPERIMENT_NAME,
        "stage": EXPERIMENT_ID,
        "specification": (SPECIFICATION_FILE.name),
        "model": specification["model"]["name"],
        "seed": specification["generation"]["seed"],
        "scenario": specification["generation"].get("scenario"),
        "generation_mode": "declarative",
        "domain_specific_generation_code": False,
        "entities": {name: len(records) for name, records in datasets.items()},
        "total_records": sum(len(records) for records in datasets.values()),
        "relationships": len(
            specification.get(
                "relationships",
                [],
            )
        ),
        "constraints": len(
            specification.get(
                "constraints",
                [],
            )
        ),
        "derived_fields": sorted(derived_fields),
        "conditional_fields": sorted(conditional_fields),
        "entity_generation_plan": (entity_plan),
        "field_generation_plans": (field_plans),
        "dataset_files": [str(path) for path in csv_paths],
    }

    with MANIFEST_FILE.open(
        "w",
        encoding="utf-8",
    ) as handle:
        json.dump(
            manifest,
            handle,
            indent=2,
        )

    return MANIFEST_FILE


# ============================================================================
# ORDER-INDEPENDENCE TEST HELPERS
# ============================================================================


def reorder_entities(
    specification: dict[str, Any],
) -> dict[str, Any]:
    alternate = copy.deepcopy(specification)

    alternate["entities"] = list(reversed(alternate["entities"]))

    return alternate


def reorder_fields(
    specification: dict[str, Any],
) -> dict[str, Any]:
    alternate = copy.deepcopy(specification)

    for entity in alternate["entities"]:
        entity["fields"] = list(reversed(entity["fields"]))

    return alternate


def canonical_dataset(
    datasets: dict[
        str,
        list[dict[str, Any]],
    ],
) -> dict[
    str,
    list[dict[str, Any]],
]:
    """
    Canonicalize record key order so field declaration order does not
    affect equality checks.
    """

    result: dict[
        str,
        list[dict[str, Any]],
    ] = {}

    for entity_name in sorted(datasets):
        result[entity_name] = [
            {key: record[key] for key in sorted(record)}
            for record in datasets[entity_name]
        ]

    return result


# ============================================================================
# EXPERIMENT EXECUTION
# ============================================================================


def run_experiment() -> int:
    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    DATASET_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    print("=" * 70)
    print(
        "FORGE - Experiment 021-D: "
        "Declarative Derived & Conditional Model to Dataset"
    )
    print("=" * 70)

    print("Experiment:     " "021_declarative_model_to_dataset")
    print("Stage:          " "021-D")
    print(
        "Purpose:        " "Derived & conditional relational model " "to actual dataset"
    )

    try:
        specification = load_specification()

        print(f"Random seed:    " f"{specification['generation']['seed']}")

        print()
        print("Model-to-dataset architecture:")
        print("  Declarative specification")
        print("       ↓")
        print("  Specification validation")
        print("       ↓")
        print("  Relationship / constraint discovery")
        print("       ↓")
        print("  Field dependency discovery")
        print("       ↓")
        print("  Dependency-aware generation planning")
        print("       ↓")
        print("  Base + derived + conditional generation")
        print("       ↓")
        print("  Relationship resolution")
        print("       ↓")
        print("  Independent dataset validation")
        print("       ↓")
        print("  CSV datasets")

        print()
        print("Specification:")
        print(f"  Model:          " f"{specification['model']['name']}")
        print(f"  Version:        " f"{specification['version']}")
        print(f"  Vocabulary:     " f"{specification['vocabulary_version']}")
        print(f"  Seed:           " f"{specification['generation']['seed']}")
        print(f"  Scenario:       " f"{specification['generation'].get('scenario')}")
        print(f"  Entities:       " f"{len(specification['entities'])}")
        print(f"  Relationships:  " f"{len(specification.get('relationships', []))}")
        print(f"  Constraints:    " f"{len(specification.get('constraints', []))}")
        print(f"  Dependencies:   " f"{len(specification.get('dependencies', []))}")

        # ==============================================================
        # SPECIFICATION VALIDATION
        # ==============================================================

        specification_errors = validate_specification(specification)

        specification_valid = not specification_errors

        print()
        print("Specification validation:")
        print(
            f"  Declarative structure              "
            f"{'PASS' if specification_valid else 'FAIL'}"
        )

        if specification_errors:
            for error in specification_errors:
                print(f"    ERROR: {error}")

            results = {
                "experiment": (EXPERIMENT_NAME),
                "stage": EXPERIMENT_ID,
                "overall": "FAIL",
                "specification_valid": False,
                "errors": (specification_errors),
            }

            with RESULTS_FILE.open(
                "w",
                encoding="utf-8",
            ) as handle:
                json.dump(
                    results,
                    handle,
                    indent=2,
                )

            print()
            print("Experiment completed with failures.")

            return 1

        # ==============================================================
        # DISCOVERY
        # ==============================================================

        relationship_managed = get_relationship_managed_fields(specification)

        field_dependencies = discover_field_dependencies(specification)

        entity_plan = build_entity_generation_plan(specification)

        field_plans = build_all_field_generation_plans(specification)

        print()
        print("Declarative relationships:")

        for relationship in specification.get(
            "relationships",
            [],
        ):
            source = relationship["from"]
            target = relationship["to"]

            print(
                f"  {source['entity']}."
                f"{source['field']}"
                f"  →  "
                f"{target['entity']}."
                f"{target['field']}"
                f"  [{relationship['type']}]"
            )

        print()
        print("Relationship-managed fields:")

        for entity_name, field_name in sorted(relationship_managed):
            print(f"  {entity_name}.{field_name}")

        print()
        print("Derived / conditional fields:")

        for entity in specification["entities"]:
            for field in entity["fields"]:
                strategy = field.get(
                    "generation",
                    {},
                ).get("strategy")

                if strategy in {
                    "DERIVED",
                    "CONDITIONAL",
                }:
                    print(f"  {entity['name']}." f"{field['name']}" f"  [{strategy}]")

        print()
        print("Discovered field dependencies:")

        for entity_name in sorted(field_dependencies):
            for target in sorted(field_dependencies[entity_name]):
                sources = field_dependencies[entity_name][target]

                if not sources:
                    continue

                print(
                    f"  {entity_name}.{target}"
                    f"  <-  "
                    f"{', '.join(sorted(sources))}"
                )

        print()
        print("Generation plan:")
        print("  Entity order: " + " -> ".join(entity_plan))

        for entity_name in entity_plan:
            print(f"  {entity_name} fields: " + " -> ".join(field_plans[entity_name]))

        # ==============================================================
        # GENERATION
        # ==============================================================

        print()
        print("Generating relational dataset...")

        (
            datasets,
            generated_entity_plan,
            generated_field_plans,
        ) = generate_dataset(specification)

        print()
        print("Generated dataset:")

        total_records = 0

        for entity_name in sorted(datasets):
            records = datasets[entity_name]

            total_records += len(records)

            print(f"  {entity_name}: " f"{len(records)} records")

            if records:
                print(f"    Sample: " f"{records[0]}")

        # ==============================================================
        # DATASET VALIDATION
        # ==============================================================

        validation = validate_dataset(
            specification,
            datasets,
        )

        print()
        print("Dataset validation:")

        for name, passed in validation.items():
            label = name.replace("_", " ").title()

            print(f"  {label:<38}" f"{'PASS' if passed else 'FAIL'}")

        dataset_valid = all(validation.values())

        # ==============================================================
        # CSV ARTIFACT VALIDATION
        # ==============================================================

        csv_paths = write_csv_datasets(
            specification,
            datasets,
        )

        csv_valid = validate_csv_artifacts(
            specification,
            csv_paths,
        )

        print()
        print("CSV artifact validation:")
        print(
            f"  Final CSV structure                  "
            f"{'PASS' if csv_valid else 'FAIL'}"
        )

        # ==============================================================
        # REPRODUCIBILITY
        # ==============================================================

        (
            repeat_dataset,
            _,
            _,
        ) = generate_dataset(specification)

        reproducibility = canonical_dataset(repeat_dataset) == canonical_dataset(
            datasets
        )

        print()
        print("Reproducibility validation:")
        print(
            f"  Same specification + same seed       "
            f"{'PASS' if reproducibility else 'FAIL'}"
        )

        # ==============================================================
        # SEED SENSITIVITY
        # ==============================================================

        alternate_seed_spec = copy.deepcopy(specification)

        alternate_seed_spec["generation"]["seed"] += 1

        (
            alternate_seed_dataset,
            _,
            _,
        ) = generate_dataset(alternate_seed_spec)

        seed_sensitive = canonical_dataset(alternate_seed_dataset) != canonical_dataset(
            datasets
        )

        print()
        print("Seed sensitivity validation:")
        print(
            f"  Different seed changes stochastic data "
            f"{'PASS' if seed_sensitive else 'FAIL'}"
        )

        # ==============================================================
        # ENTITY ORDER INDEPENDENCE
        # ==============================================================

        entity_reordered_spec = reorder_entities(specification)

        (
            entity_reordered_dataset,
            _,
            _,
        ) = generate_dataset(entity_reordered_spec)

        entity_order_independent = canonical_dataset(
            entity_reordered_dataset
        ) == canonical_dataset(datasets)

        print()
        print("Entity-order validation:")
        print(
            f"  Entity declaration order does not "
            f"change results "
            f"{'PASS' if entity_order_independent else 'FAIL'}"
        )

        # ==============================================================
        # FIELD ORDER INDEPENDENCE
        # ==============================================================

        field_reordered_spec = reorder_fields(specification)

        (
            field_reordered_dataset,
            _,
            _,
        ) = generate_dataset(field_reordered_spec)

        field_order_independent = canonical_dataset(
            field_reordered_dataset
        ) == canonical_dataset(datasets)

        print()
        print("Field-order validation:")
        print(
            f"  Field declaration order does not "
            f"change results "
            f"{'PASS' if field_order_independent else 'FAIL'}"
        )

        # ==============================================================
        # MANIFEST
        # ==============================================================

        manifest_path = write_manifest(
            specification,
            datasets,
            generated_entity_plan,
            generated_field_plans,
            csv_paths,
        )

        # ==============================================================
        # FINAL RESULT
        # ==============================================================

        overall = (
            specification_valid
            and dataset_valid
            and csv_valid
            and reproducibility
            and seed_sensitive
            and entity_order_independent
            and field_order_independent
        )

        results = {
            "experiment": (EXPERIMENT_NAME),
            "stage": EXPERIMENT_ID,
            "purpose": (
                "Declarative derived and " "conditional relational model " "to dataset"
            ),
            "overall": ("PASS" if overall else "FAIL"),
            "specification_valid": (specification_valid),
            "dataset_validation": (validation),
            "csv_artifact_validation": (csv_valid),
            "reproducibility": (reproducibility),
            "seed_sensitivity": (seed_sensitive),
            "entity_order_independence": (entity_order_independent),
            "field_order_independence": (field_order_independent),
            "relationships": len(
                specification.get(
                    "relationships",
                    [],
                )
            ),
            "relationship_managed_fields": (len(relationship_managed)),
            "constraints": len(
                specification.get(
                    "constraints",
                    [],
                )
            ),
            "dependencies": len(
                specification.get(
                    "dependencies",
                    [],
                )
            ),
            "entities": {name: len(records) for name, records in datasets.items()},
            "total_records": (total_records),
            "domain_specific_generation_code": (False),
            "entity_generation_plan": (generated_entity_plan),
            "field_generation_plans": (generated_field_plans),
            "artifacts": {
                "dataset_csv": [str(path) for path in csv_paths],
                "generation_manifest": (str(manifest_path)),
            },
        }

        with RESULTS_FILE.open(
            "w",
            encoding="utf-8",
        ) as handle:
            json.dump(
                results,
                handle,
                indent=2,
            )

        print()
        print("Experiment result:")
        print(
            f"  Specification validity:       "
            f"{'PASS' if specification_valid else 'FAIL'}"
        )
        print(
            f"  Relational generation:        " f"{'PASS' if dataset_valid else 'FAIL'}"
        )
        print(
            f"  Derived-field correctness:    "
            f"{'PASS' if validation['derived_field_correctness'] else 'FAIL'}"
        )
        print(
            f"  Conditional correctness:      "
            f"{'PASS' if validation['conditional_field_correctness'] else 'FAIL'}"
        )
        print(
            f"  Chained dependencies:         "
            f"{'PASS' if validation['chained_dependency_correctness'] else 'FAIL'}"
        )
        print(
            f"  Constraint preservation:      "
            f"{'PASS' if validation['constraint_preservation'] else 'FAIL'}"
        )
        print(
            f"  Referential integrity:        "
            f"{'PASS' if validation['referential_integrity'] else 'FAIL'}"
        )
        print(f"  CSV artifact validation:      " f"{'PASS' if csv_valid else 'FAIL'}")
        print(
            f"  Reproducibility:              "
            f"{'PASS' if reproducibility else 'FAIL'}"
        )
        print(
            f"  Seed sensitivity:             "
            f"{'PASS' if seed_sensitive else 'FAIL'}"
        )
        print(
            f"  Entity-order independence:    "
            f"{'PASS' if entity_order_independent else 'FAIL'}"
        )
        print(
            f"  Field-order independence:     "
            f"{'PASS' if field_order_independent else 'FAIL'}"
        )
        print(
            f"  Relationships:                "
            f"{len(specification.get('relationships', []))}"
        )
        print(f"  Relationship-managed fields:  " f"{len(relationship_managed)}")
        print(
            f"  Constraints:                  "
            f"{len(specification.get('constraints', []))}"
        )
        print(
            f"  Dependencies:                 "
            f"{len(specification.get('dependencies', []))}"
        )
        print(f"  Total records:                " f"{total_records}")
        print(f"  Overall:                      " f"{'PASS' if overall else 'FAIL'}")

        print()
        print("Output:")

        for path in csv_paths:
            print(f"  Dataset:     {path}")

        print(f"  Manifest:    {manifest_path}")
        print(f"  Results:     {RESULTS_FILE}")

        if overall:
            print()
            print("Experiment completed successfully.")
            print(
                "Declarative derived and conditional "
                "model-to-dataset generation is "
                "experimentally validated."
            )
            return 0

        print()
        print("Experiment completed with failures.")

        return 1

    except Exception as exc:
        print()
        print(f"ERROR: " f"{type(exc).__name__}: " f"{exc}")

        results = {
            "experiment": (EXPERIMENT_NAME),
            "stage": EXPERIMENT_ID,
            "overall": "FAIL",
            "error": (f"{type(exc).__name__}: " f"{exc}"),
        }

        with RESULTS_FILE.open(
            "w",
            encoding="utf-8",
        ) as handle:
            json.dump(
                results,
                handle,
                indent=2,
            )

        return 1


if __name__ == "__main__":
    sys.exit(run_experiment())
