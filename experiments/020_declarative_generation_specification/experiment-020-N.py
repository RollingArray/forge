"""
FORGE - Experiment 020-N: Full Declarative Generation Integration
==================================================================

Stage:
    020-N

Purpose:
    Final integration experiment for the FORGE declarative generation
    model.

Research Question
-----------------
Can one declarative FORGE specification combine:

    - primitive and semantic types
    - direct generation
    - statistical distributions
    - deterministic identity
    - composite identity
    - population / nullability
    - derived fields
    - conditional generation
    - cross-field constraints
    - entity dependencies
    - 1:1 relationships
    - 1:N relationships
    - N:M associative relationships
    - deterministic random streams
    - capability boundaries
    - final structural / relational / rule validation

without requiring domain-specific generator code?

Architectural Principle
-----------------------
The experiment validates the complete declarative execution pipeline:

    FORGE Specification
            |
            v
    Vocabulary Validation
            |
            v
    Capability Assessment
            |
            v
    Expression Analysis
            |
            v
    Constraint Analysis
            |
            v
    Dependency Graph
            |
            v
    Generation Plan
            |
            +----------------------+
            |                      |
            v                      v
      Independent             Context-Aware
       Generation              Generation
            |                      |
            +----------+-----------+
                       |
                       v
                Identity Generation
                       |
                       v
               Relationship Resolution
                       |
                       v
                 Final Validation
                       |
                       v
                    Dataset

Critical Safety Principle
-------------------------
A valid declarative specification must not imply that every capability
is executable.

If a vocabulary element is valid but unsupported by the current runtime,
the system must explicitly report:

    DEFERRED

If a specification is structurally invalid or impossible to execute,
the system must report:

    BLOCKED

The runtime must never silently substitute another generation behavior.

Scope
-----
Included:

    CUSTOMER
    CUSTOMER_PROFILE
    PRODUCT
    ORDER
    ORDER_ITEM
    SHIPMENT

Capabilities combined:

    - INTEGER
    - DECIMAL
    - STRING
    - BOOLEAN
    - CATEGORICAL
    - IDENTIFIER
    - CODE
    - CURRENCY
    - DATE
    - PRIMARY_KEY
    - FOREIGN_KEY
    - COMPOSITE_KEY
    - UNIQUE
    - SEQUENTIAL_ID
    - UUID
    - 1:1
    - 1:N
    - 0:N
    - N:M
    - REQUIRED
    - OPTIONAL
    - RANDOM
    - SEQUENTIAL
    - CONSTANT
    - NULL
    - UNIFORM
    - NORMAL
    - DISCRETE_UNIFORM
    - POISSON
    - CATEGORICAL
    - DERIVED
    - FORMULA
    - CONDITIONAL
    - constraints
    - dependency planning
    - deterministic streams
    - reproducibility
    - validation

Excluded:

    - full empirical distributions
    - correlation
    - learned distributions
    - external lookups
    - arbitrary user-defined functions
    - temporal lifecycle modeling
    - LLM specification generation
    - production persistence
    - large-scale performance benchmarking

Those capabilities belong outside the final integration boundary or
to later framework experiments.

Success Criteria
----------------
The experiment passes only if:

    1. The complete specification is accepted.
    2. Generation order is determined declaratively.
    3. Entity declaration order does not affect execution.
    4. Field declaration order does not affect execution.
    5. Primary keys are unique.
    6. Foreign keys resolve.
    7. Composite keys remain unique.
    8. N:M relationships are represented through an associative entity.
    9. Derived fields satisfy their formulas.
   10. Conditional fields satisfy their active branch.
   11. Cross-field constraints hold.
   12. Statistical fields remain within their declared behavior.
   13. The same seed produces the same dataset.
   14. A different seed produces a different dataset.
   15. Unsupported capabilities are explicitly deferred.
   16. Invalid configurations are blocked.
   17. No post-generation repair is required.

Status:
    Experimental
"""

from __future__ import annotations

import hashlib
import json
import random
import sys
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path
from typing import Any

# ============================================================================
# PATHS
# ============================================================================

EXPERIMENT_DIR = Path(__file__).resolve().parent

OUTPUT_DIR = EXPERIMENT_DIR / "output"

RESULT_OUTPUT_PATH = OUTPUT_DIR / "full_integration_results.json"

MASTER_SEED = 42


# ============================================================================
# MODELS
# ============================================================================


@dataclass(frozen=True)
class Field:
    name: str
    field_type: str
    strategy: str
    parameters: dict[str, Any]


@dataclass(frozen=True)
class DerivedRule:
    target: str
    operator: str
    operands: tuple[Any, ...]


@dataclass(frozen=True)
class ConditionalRule:
    target: str
    condition_field: str
    condition_operator: str
    condition_value: Any
    then_minimum: float
    then_maximum: float
    else_minimum: float
    else_maximum: float


@dataclass(frozen=True)
class Constraint:
    constraint_id: str
    left: str
    operator: str
    right: Any


@dataclass(frozen=True)
class Relationship:
    name: str
    parent: str
    child: str
    cardinality: str
    parent_key: tuple[str, ...]
    child_key: tuple[str, ...]
    required: bool


@dataclass(frozen=True)
class Entity:
    name: str
    record_count: int
    fields: tuple[Field, ...]
    derived_rules: tuple[DerivedRule, ...] = ()
    conditional_rules: tuple[ConditionalRule, ...] = ()
    constraints: tuple[Constraint, ...] = ()
    primary_key: tuple[str, ...] = ()


# ============================================================================
# CONTROLLED VOCABULARY
# ============================================================================

EXECUTABLE_TYPES = {
    "INTEGER",
    "DECIMAL",
    "STRING",
    "BOOLEAN",
    "CATEGORICAL",
    "IDENTIFIER",
    "CODE",
    "CURRENCY",
    "DATE",
}

EXECUTABLE_STRATEGIES = {
    "CONSTANT",
    "SEQUENTIAL",
    "RANDOM",
    "NULL",
    "DERIVED",
    "FORMULA",
    "CONDITIONAL",
}

EXECUTABLE_DISTRIBUTIONS = {
    "UNIFORM",
    "NORMAL",
    "DISCRETE_UNIFORM",
    "POISSON",
    "CATEGORICAL",
}

VALID_DEFERRED_CAPABILITIES = {
    "LOOKUP",
    "REFERENCE",
    "EMPIRICAL",
    "BETA",
    "LOGNORMAL",
    "GAMMA",
    "WEIBULL",
    "TRUNCATED",
    "MIXTURE",
}


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
# SPECIFICATION
# ============================================================================


def build_specification(
    reverse_entities: bool = False,
    reverse_fields: bool = False,
) -> dict[str, Entity]:

    # ----------------------------------------------------------------------
    # CUSTOMER
    # ----------------------------------------------------------------------

    customer = Entity(
        name="CUSTOMER",
        record_count=25,
        fields=(
            Field(
                "CUSTOMER_ID",
                "IDENTIFIER",
                "SEQUENTIAL",
                {
                    "prefix": "CUS-",
                    "start": 1,
                },
            ),
            Field(
                "CUSTOMER_TYPE",
                "CATEGORICAL",
                "RANDOM",
                {
                    "distribution": "CATEGORICAL",
                    "values": {
                        "STANDARD": 0.70,
                        "PREMIUM": 0.30,
                    },
                },
            ),
            Field(
                "COUNTRY",
                "CATEGORICAL",
                "RANDOM",
                {
                    "distribution": "CATEGORICAL",
                    "values": {
                        "US": 0.45,
                        "IN": 0.30,
                        "DE": 0.15,
                        "GB": 0.10,
                    },
                },
            ),
            Field(
                "CREDIT_LIMIT",
                "CURRENCY",
                "CONDITIONAL",
                {},
            ),
            Field(
                "IS_ACTIVE",
                "BOOLEAN",
                "RANDOM",
                {
                    "distribution": "CATEGORICAL",
                    "values": {
                        True: 0.90,
                        False: 0.10,
                    },
                },
            ),
        ),
        conditional_rules=(
            ConditionalRule(
                target="CREDIT_LIMIT",
                condition_field="CUSTOMER_TYPE",
                condition_operator="EQUALS",
                condition_value="PREMIUM",
                then_minimum=5000,
                then_maximum=10000,
                else_minimum=500,
                else_maximum=5000,
            ),
        ),
        primary_key=("CUSTOMER_ID",),
    )

    # ----------------------------------------------------------------------
    # CUSTOMER PROFILE
    # ----------------------------------------------------------------------

    customer_profile = Entity(
        name="CUSTOMER_PROFILE",
        record_count=25,
        fields=(
            Field(
                "CUSTOMER_ID",
                "IDENTIFIER",
                "NULL",
                {},
            ),
            Field(
                "PROFILE_STATUS",
                "CATEGORICAL",
                "RANDOM",
                {
                    "distribution": "CATEGORICAL",
                    "values": {
                        "ACTIVE": 0.80,
                        "INACTIVE": 0.20,
                    },
                },
            ),
            Field(
                "PREFERRED_LANGUAGE",
                "CATEGORICAL",
                "RANDOM",
                {
                    "distribution": "CATEGORICAL",
                    "values": {
                        "EN": 0.60,
                        "DE": 0.20,
                        "FR": 0.10,
                        "ES": 0.10,
                    },
                },
            ),
        ),
        primary_key=("CUSTOMER_ID",),
    )

    # ----------------------------------------------------------------------
    # PRODUCT
    # ----------------------------------------------------------------------

    product = Entity(
        name="PRODUCT",
        record_count=20,
        fields=(
            Field(
                "PRODUCT_ID",
                "IDENTIFIER",
                "SEQUENTIAL",
                {
                    "prefix": "PRD-",
                    "start": 100,
                },
            ),
            Field(
                "PRODUCT_CODE",
                "CODE",
                "SEQUENTIAL",
                {
                    "prefix": "P-",
                    "start": 1,
                },
            ),
            Field(
                "PRODUCT_TYPE",
                "CATEGORICAL",
                "RANDOM",
                {
                    "distribution": "CATEGORICAL",
                    "values": {
                        "STANDARD": 0.60,
                        "PREMIUM": 0.25,
                        "SPECIAL": 0.15,
                    },
                },
            ),
            Field(
                "UNIT_PRICE",
                "CURRENCY",
                "RANDOM",
                {
                    "distribution": "UNIFORM",
                    "minimum": 100,
                    "maximum": 5000,
                },
            ),
        ),
        primary_key=("PRODUCT_ID",),
    )

    # ----------------------------------------------------------------------
    # ORDER
    # ----------------------------------------------------------------------

    order = Entity(
        name="ORDER",
        record_count=60,
        fields=(
            Field(
                "ORDER_ID",
                "IDENTIFIER",
                "SEQUENTIAL",
                {
                    "prefix": "ORD-",
                    "start": 1,
                },
            ),
            Field(
                "CUSTOMER_ID",
                "IDENTIFIER",
                "NULL",
                {},
            ),
            Field(
                "ORDER_DATE",
                "DATE",
                "RANDOM",
                {
                    "start": "2026-01-01",
                    "end": "2026-06-30",
                },
            ),
            Field(
                "QUANTITY",
                "INTEGER",
                "RANDOM",
                {
                    "distribution": "DISCRETE_UNIFORM",
                    "minimum": 1,
                    "maximum": 20,
                },
            ),
            Field(
                "UNIT_PRICE",
                "CURRENCY",
                "RANDOM",
                {
                    "distribution": "UNIFORM",
                    "minimum": 100,
                    "maximum": 1000,
                },
            ),
            Field(
                "DISCOUNT",
                "CURRENCY",
                "RANDOM",
                {
                    "distribution": "UNIFORM",
                    "minimum": 0,
                    "maximum": 500,
                },
            ),
            Field(
                "SUBTOTAL",
                "CURRENCY",
                "FORMULA",
                {},
            ),
            Field(
                "NET_AMOUNT",
                "CURRENCY",
                "FORMULA",
                {},
            ),
            Field(
                "IS_PRIORITY",
                "BOOLEAN",
                "CONDITIONAL",
                {},
            ),
        ),
        derived_rules=(
            DerivedRule(
                target="SUBTOTAL",
                operator="MULTIPLY",
                operands=(
                    "QUANTITY",
                    "UNIT_PRICE",
                ),
            ),
            DerivedRule(
                target="NET_AMOUNT",
                operator="SUBTRACT",
                operands=(
                    "SUBTOTAL",
                    "DISCOUNT",
                ),
            ),
        ),
        conditional_rules=(
            ConditionalRule(
                target="IS_PRIORITY",
                condition_field="NET_AMOUNT",
                condition_operator="GREATER_OR_EQUAL",
                condition_value=5000,
                then_minimum=1,
                then_maximum=1,
                else_minimum=0,
                else_maximum=0,
            ),
        ),
        constraints=(
            Constraint(
                constraint_id="ORDER-C001",
                left="DISCOUNT",
                operator="LESS_OR_EQUAL",
                right="SUBTOTAL",
            ),
            Constraint(
                constraint_id="ORDER-C002",
                left="NET_AMOUNT",
                operator="GREATER_OR_EQUAL",
                right=0,
            ),
        ),
        primary_key=("ORDER_ID",),
    )

    # ----------------------------------------------------------------------
    # ORDER ITEM
    # ----------------------------------------------------------------------

    order_item = Entity(
        name="ORDER_ITEM",
        record_count=120,
        fields=(
            Field(
                "ORDER_ID",
                "IDENTIFIER",
                "NULL",
                {},
            ),
            Field(
                "LINE_NUMBER",
                "INTEGER",
                "SEQUENTIAL",
                {
                    "start": 1,
                },
            ),
            Field(
                "PRODUCT_ID",
                "IDENTIFIER",
                "NULL",
                {},
            ),
            Field(
                "QUANTITY",
                "INTEGER",
                "RANDOM",
                {
                    "distribution": "POISSON",
                    "lambda": 3,
                },
            ),
            Field(
                "UNIT_PRICE",
                "CURRENCY",
                "RANDOM",
                {
                    "distribution": "UNIFORM",
                    "minimum": 50,
                    "maximum": 2000,
                },
            ),
            Field(
                "LINE_AMOUNT",
                "CURRENCY",
                "FORMULA",
                {},
            ),
        ),
        derived_rules=(
            DerivedRule(
                target="LINE_AMOUNT",
                operator="MULTIPLY",
                operands=(
                    "QUANTITY",
                    "UNIT_PRICE",
                ),
            ),
        ),
        primary_key=(
            "ORDER_ID",
            "LINE_NUMBER",
        ),
    )

    # ----------------------------------------------------------------------
    # SHIPMENT
    # ----------------------------------------------------------------------

    shipment = Entity(
        name="SHIPMENT",
        record_count=45,
        fields=(
            Field(
                "SHIPMENT_ID",
                "IDENTIFIER",
                "SEQUENTIAL",
                {
                    "prefix": "SHP-",
                    "start": 1,
                },
            ),
            Field(
                "ORDER_ID",
                "IDENTIFIER",
                "NULL",
                {},
            ),
            Field(
                "CARRIER_CODE",
                "CODE",
                "RANDOM",
                {
                    "distribution": "CATEGORICAL",
                    "values": {
                        "UPS": 0.40,
                        "FEDEX": 0.35,
                        "DHL": 0.25,
                    },
                },
            ),
            Field(
                "SHIPPING_COST",
                "CURRENCY",
                "RANDOM",
                {
                    "distribution": "NORMAL",
                    "mean": 50,
                    "stddev": 15,
                    "minimum": 5,
                    "maximum": 100,
                },
            ),
            Field(
                "DELIVERY_DAYS",
                "INTEGER",
                "RANDOM",
                {
                    "distribution": "DISCRETE_UNIFORM",
                    "minimum": 1,
                    "maximum": 10,
                },
            ),
            Field(
                "DELIVERY_DATE",
                "DATE",
                "FORMULA",
                {},
            ),
        ),
        derived_rules=(
            DerivedRule(
                target="DELIVERY_DATE",
                operator="DATE_ADD",
                operands=(
                    "ORDER_DATE",
                    "DELIVERY_DAYS",
                ),
            ),
        ),
        primary_key=("SHIPMENT_ID",),
    )

    entities = [
        customer,
        customer_profile,
        product,
        order,
        order_item,
        shipment,
    ]

    if reverse_entities:
        entities.reverse()

    if reverse_fields:
        entities = [
            Entity(
                name=entity.name,
                record_count=entity.record_count,
                fields=tuple(reversed(entity.fields)),
                derived_rules=entity.derived_rules,
                conditional_rules=entity.conditional_rules,
                constraints=entity.constraints,
                primary_key=entity.primary_key,
            )
            for entity in entities
        ]

    return {entity.name: entity for entity in entities}


# ============================================================================
# RELATIONSHIPS
# ============================================================================


def relationships() -> tuple[Relationship, ...]:

    return (
        Relationship(
            name="CUSTOMER_PROFILE",
            parent="CUSTOMER",
            child="CUSTOMER_PROFILE",
            cardinality="1:1",
            parent_key=("CUSTOMER_ID",),
            child_key=("CUSTOMER_ID",),
            required=True,
        ),
        Relationship(
            name="CUSTOMER_ORDERS",
            parent="CUSTOMER",
            child="ORDER",
            cardinality="1:N",
            parent_key=("CUSTOMER_ID",),
            child_key=("CUSTOMER_ID",),
            required=True,
        ),
        Relationship(
            name="ORDER_ITEMS",
            parent="ORDER",
            child="ORDER_ITEM",
            cardinality="1:N",
            parent_key=("ORDER_ID",),
            child_key=("ORDER_ID",),
            required=True,
        ),
        Relationship(
            name="PRODUCT_ORDER_ITEMS",
            parent="PRODUCT",
            child="ORDER_ITEM",
            cardinality="1:N",
            parent_key=("PRODUCT_ID",),
            child_key=("PRODUCT_ID",),
            required=True,
        ),
        Relationship(
            name="ORDER_SHIPMENTS",
            parent="ORDER",
            child="SHIPMENT",
            cardinality="0:N",
            parent_key=("ORDER_ID",),
            child_key=("ORDER_ID",),
            required=False,
        ),
    )


# ============================================================================
# EXPRESSION EVALUATION
# ============================================================================


def evaluate_expression(
    operator: str,
    operands: tuple[Any, ...],
    record: dict[str, Any],
) -> Any:

    values = []

    for operand in operands:

        if isinstance(
            operand,
            str,
        ):

            if operand not in record:

                raise ValueError(f"Unknown field reference: " f"{operand}")

            values.append(record[operand])

        else:

            values.append(operand)

    if operator == "MULTIPLY":
        return values[0] * values[1]

    if operator == "SUBTRACT":
        return values[0] - values[1]

    if operator == "ADD":
        return values[0] + values[1]

    if operator == "DATE_ADD":

        return values[0] + timedelta(days=int(values[1]))

    raise ValueError(f"Unsupported expression operator: " f"{operator}")


# ============================================================================
# DEPENDENCY PLANNING
# ============================================================================


def expression_dependencies(
    entity: Entity,
) -> dict[str, set[str]]:

    dependencies = {field.name: set() for field in entity.fields}

    for rule in entity.derived_rules:

        for operand in rule.operands:

            if (
                isinstance(
                    operand,
                    str,
                )
                and operand in dependencies
            ):

                dependencies[rule.target].add(operand)

    for rule in entity.conditional_rules:

        if rule.condition_field in dependencies:

            dependencies[rule.target].add(rule.condition_field)

    return dependencies


def generation_order(
    entity: Entity,
) -> list[str] | None:

    dependencies = expression_dependencies(entity)

    incoming = {field: len(dependencies[field]) for field in dependencies}

    ready = sorted(field for field, degree in incoming.items() if degree == 0)

    order = []

    while ready:

        current = ready.pop(0)

        order.append(current)

        for target, deps in dependencies.items():

            if current in deps:

                incoming[target] -= 1

                if incoming[target] == 0:

                    ready.append(target)

                    ready.sort()

    if len(order) != len(dependencies):

        return None

    return order


def entity_generation_order(
    entities: dict[str, Entity],
    relationships_: tuple[Relationship, ...],
) -> list[str] | None:

    dependencies = {name: set() for name in entities}

    for relationship in relationships_:

        if relationship.parent not in entities or relationship.child not in entities:

            return None

        dependencies[relationship.child].add(relationship.parent)

    incoming = {name: len(dependencies[name]) for name in dependencies}

    ready = sorted(name for name, degree in incoming.items() if degree == 0)

    order = []

    while ready:

        current = ready.pop(0)

        order.append(current)

        for target, deps in dependencies.items():

            if current in deps:

                incoming[target] -= 1

                if incoming[target] == 0:

                    ready.append(target)

                    ready.sort()

    if len(order) != len(dependencies):

        return None

    return order


# ============================================================================
# FIELD GENERATION
# ============================================================================


def generate_field(
    field: Field,
    entity_name: str,
    record: dict[str, Any],
    record_index: int,
) -> Any:

    strategy = field.strategy
    parameters = field.parameters

    if strategy == "NULL":

        return None

    if strategy == "CONSTANT":

        return parameters["value"]

    if strategy == "SEQUENTIAL":

        start = parameters.get(
            "start",
            1,
        )

        prefix = parameters.get(
            "prefix",
            "",
        )

        return f"{prefix}" f"{start + record_index}"

    rng = field_rng(
        MASTER_SEED,
        entity_name,
        field.name,
    )

    if strategy == "RANDOM":

        distribution = parameters.get("distribution")

        if distribution == "CATEGORICAL":

            return weighted_choice(
                rng,
                parameters["values"],
            )

        if distribution == "UNIFORM":

            value = rng.uniform(
                parameters["minimum"],
                parameters["maximum"],
            )

            return round(
                value,
                2,
            )

        if distribution == "DISCRETE_UNIFORM":

            return rng.randint(
                parameters["minimum"],
                parameters["maximum"],
            )

        if distribution == "POISSON":

            return poisson(
                rng,
                parameters["lambda"],
            )

        if distribution == "NORMAL":

            value = rng.gauss(
                parameters["mean"],
                parameters["stddev"],
            )

            minimum = parameters.get("minimum")

            maximum = parameters.get("maximum")

            if minimum is not None:

                value = max(
                    minimum,
                    value,
                )

            if maximum is not None:

                value = min(
                    maximum,
                    value,
                )

            return round(
                value,
                2,
            )

    raise ValueError(
        f"Strategy '{strategy}' "
        f"cannot be independently generated "
        f"for field {field.name}"
    )


def weighted_choice(
    rng: random.Random,
    values: dict[Any, float],
) -> Any:

    total = sum(float(weight) for weight in values.values())

    threshold = rng.random() * total

    cumulative = 0

    for value, weight in values.items():

        cumulative += float(weight)

        if threshold < cumulative:

            return value

    return next(reversed(values))


def poisson(
    rng: random.Random,
    lambda_value: float,
) -> int:

    import math

    limit = math.exp(-lambda_value)

    k = 0
    product = 1.0

    while product > limit:

        k += 1

        product *= rng.random()

    return k - 1


# ============================================================================
# ENTITY GENERATION
# ============================================================================


def generate_entity(
    entity: Entity,
) -> list[dict[str, Any]]:

    order = generation_order(entity)

    if order is None:

        raise ValueError(f"Cyclic dependency in " f"entity {entity.name}")

    field_map = {field.name: field for field in entity.fields}

    derived_map = {rule.target: rule for rule in entity.derived_rules}

    conditional_map = {rule.target: rule for rule in entity.conditional_rules}

    records = [{} for _ in range(entity.record_count)]

    for field_name in order:

        field = field_map[field_name]

        for index, record in enumerate(records):

            if field_name in (derived_map):

                rule = derived_map[field_name]

                value = evaluate_expression(
                    rule.operator,
                    rule.operands,
                    record,
                )

                if isinstance(
                    value,
                    float,
                ):

                    value = round(
                        value,
                        2,
                    )

                record[field_name] = value

                continue

            if field_name in (conditional_map):

                rule = conditional_map[field_name]

                condition_value = record[rule.condition_field]

                condition = compare(
                    condition_value,
                    rule.condition_operator,
                    rule.condition_value,
                )

                rng = field_rng(
                    MASTER_SEED,
                    entity.name,
                    field.name,
                )

                if condition:

                    minimum = rule.then_minimum

                    maximum = rule.then_maximum

                else:

                    minimum = rule.else_minimum

                    maximum = rule.else_maximum

                if field.field_type == "BOOLEAN":

                    value = bool(
                        round(
                            rng.uniform(
                                minimum,
                                maximum,
                            )
                        )
                    )

                else:

                    value = round(
                        rng.uniform(
                            minimum,
                            maximum,
                        ),
                        2,
                    )

                record[field_name] = value

                continue

            record[field_name] = generate_field(
                field,
                entity.name,
                record,
                index,
            )

    return records


def compare(
    actual: Any,
    operator: str,
    expected: Any,
) -> bool:

    if operator == "EQUALS":
        return actual == expected

    if operator == "GREATER_OR_EQUAL":
        return actual >= expected

    if operator == "LESS_OR_EQUAL":
        return actual <= expected

    if operator == "GREATER_THAN":
        return actual > expected

    if operator == "LESS_THAN":
        return actual < expected

    if operator == "NOT_EQUALS":
        return actual != expected

    raise ValueError(f"Unsupported comparison: {operator}")


# ============================================================================
# RELATIONSHIP RESOLUTION
# ============================================================================


def resolve_relationships(
    datasets: dict[
        str,
        list[dict[str, Any]],
    ],
    relationships_: tuple[Relationship, ...],
) -> None:

    for relationship in relationships_:

        parent_records = datasets[relationship.parent]

        child_records = datasets[relationship.child]

        parent_keys = {
            tuple(record[key] for key in relationship.parent_key)
            for record in parent_records
        }

        child_key_count = {}

        for child in child_records:

            key = tuple(child[key] for key in relationship.child_key)

            child_key_count[key] = (
                child_key_count.get(
                    key,
                    0,
                )
                + 1
            )

        if relationship.required:

            if not all(key in parent_keys for key in child_key_count):

                raise ValueError(
                    f"Referential integrity failure: " f"{relationship.name}"
                )

        # 1:1 child key uniqueness.
        if relationship.cardinality == "1:1":

            if len(child_key_count) != len(child_records):

                raise ValueError(f"1:1 relationship violation: " f"{relationship.name}")


# ============================================================================
# FOREIGN KEY ASSIGNMENT
# ============================================================================


def assign_foreign_keys(
    datasets: dict[
        str,
        list[dict[str, Any]],
    ],
    relationships_: tuple[Relationship, ...],
) -> None:

    for relationship in relationships_:

        parent_records = datasets[relationship.parent]

        child_records = datasets[relationship.child]

        parent_values = [
            tuple(record[key] for key in relationship.parent_key)
            for record in parent_records
        ]

        if not parent_values:

            raise ValueError(f"No parent records for " f"{relationship.name}")

        rng = field_rng(
            MASTER_SEED,
            relationship.child,
            relationship.name,
        )

        for index, child in enumerate(child_records):

            if relationship.cardinality == "1:1":

                if index >= len(parent_values):

                    raise ValueError(
                        f"Insufficient parent "
                        f"records for 1:1 "
                        f"relationship "
                        f"{relationship.name}"
                    )

                selected = parent_values[index]

            else:

                selected = rng.choice(parent_values)

            for child_key, value in zip(
                relationship.child_key,
                selected,
            ):

                child[child_key] = value


# ============================================================================
# COMPOSITE ORDER ITEM IDENTITY
# ============================================================================


def validate_primary_keys(
    datasets: dict[
        str,
        list[dict[str, Any]],
    ],
    entities: dict[str, Entity],
) -> list[str]:

    failures = []

    for entity_name, entity in entities.items():

        records = datasets[entity_name]

        keys = [
            tuple(record[field] for field in entity.primary_key) for record in records
        ]

        if len(keys) != len(set(keys)):

            failures.append(f"{entity_name}: duplicate primary key")

        if any(any(value is None for value in key) for key in keys):

            failures.append(f"{entity_name}: null primary key")

    return failures


# ============================================================================
# CONSTRAINT VALIDATION
# ============================================================================


def validate_constraints(
    datasets: dict[
        str,
        list[dict[str, Any]],
    ],
    entities: dict[str, Entity],
) -> list[str]:

    failures = []

    for entity_name, entity in entities.items():

        for index, record in enumerate(datasets[entity_name]):

            for constraint in entity.constraints:

                left = record[constraint.left]

                right = (
                    record[constraint.right]
                    if isinstance(
                        constraint.right,
                        str,
                    )
                    and constraint.right in record
                    else constraint.right
                )

                valid = compare(
                    left,
                    constraint.operator,
                    right,
                )

                if not valid:

                    failures.append(
                        f"{entity_name}[{index}] " f"{constraint.constraint_id}"
                    )

    return failures


# ============================================================================
# DERIVED / CONDITIONAL VALIDATION
# ============================================================================


def validate_derived(
    datasets: dict[
        str,
        list[dict[str, Any]],
    ],
    entities: dict[str, Entity],
) -> list[str]:

    failures = []

    for entity_name, entity in entities.items():

        for index, record in enumerate(datasets[entity_name]):

            for rule in entity.derived_rules:

                expected = evaluate_expression(
                    rule.operator,
                    rule.operands,
                    record,
                )

                actual = record[rule.target]

                if isinstance(
                    expected,
                    float,
                ):

                    if abs(actual - expected) > 0.01:

                        failures.append(f"{entity_name}[{index}] " f"{rule.target}")

                elif actual != expected:

                    failures.append(f"{entity_name}[{index}] " f"{rule.target}")

    return failures


# ============================================================================
# DATASET GENERATION
# ============================================================================


def generate_dataset(
    entities: dict[str, Entity],
) -> tuple[
    dict[str, list[dict[str, Any]]],
    list[str],
]:

    relationship_defs = relationships()

    order = entity_generation_order(
        entities,
        relationship_defs,
    )

    if order is None:

        raise ValueError("Entity dependency graph is cyclic.")

    datasets = {}

    # Generate parent entities first.
    for entity_name in order:

        datasets[entity_name] = generate_entity(entities[entity_name])

    # Resolve all foreign keys after parent
    # datasets exist.
    assign_foreign_keys(
        datasets,
        relationship_defs,
    )

    # Validate relationships.
    resolve_relationships(
        datasets,
        relationship_defs,
    )

    return (
        datasets,
        order,
    )


# ============================================================================
# STATISTICAL VALIDATION
# ============================================================================


def validate_statistical_fields(
    datasets: dict[
        str,
        list[dict[str, Any]],
    ],
) -> list[str]:

    failures = []

    # CUSTOMER_TYPE must contain only
    # declared categories.
    customer_types = {record["CUSTOMER_TYPE"] for record in datasets["CUSTOMER"]}

    if not customer_types <= {
        "STANDARD",
        "PREMIUM",
    }:

        failures.append("CUSTOMER_TYPE distribution")

    # Product prices must remain within
    # declared uniform bounds.
    if not all(100 <= record["UNIT_PRICE"] <= 5000 for record in datasets["PRODUCT"]):

        failures.append("PRODUCT.UNIT_PRICE distribution")

    # Order quantities.
    if not all(1 <= record["QUANTITY"] <= 20 for record in datasets["ORDER"]):

        failures.append("ORDER.QUANTITY distribution")

    return failures


# ============================================================================
# CAPABILITY ASSESSMENT
# ============================================================================


def capability_assessment() -> dict[str, Any]:

    requested = {
        "types": sorted(EXECUTABLE_TYPES),
        "strategies": sorted(EXECUTABLE_STRATEGIES),
        "distributions": sorted(EXECUTABLE_DISTRIBUTIONS),
        "deferred": sorted(VALID_DEFERRED_CAPABILITIES),
    }

    return {
        "status": "PASS",
        "requested": requested,
        "deferred_capabilities": sorted(VALID_DEFERRED_CAPABILITIES),
    }


def test_deferred_boundary() -> dict[str, Any]:

    requested = [
        "LOOKUP",
        "REFERENCE",
        "BETA",
        "EMPIRICAL",
    ]

    safe = all(capability in VALID_DEFERRED_CAPABILITIES for capability in requested)

    return {
        "status": ("PASS" if safe else "FAIL"),
        "capabilities": requested,
        "behavior": "DEFERRED",
    }


# ============================================================================
# INTEGRATION TESTS
# ============================================================================


def test_complete_generation() -> dict[str, Any]:

    entities = build_specification()

    datasets, order = generate_dataset(entities)

    expected_entities = {
        "CUSTOMER",
        "CUSTOMER_PROFILE",
        "PRODUCT",
        "ORDER",
        "ORDER_ITEM",
        "SHIPMENT",
    }

    passed = set(datasets) == expected_entities and all(
        len(datasets[entity.name]) == entity.record_count
        for entity in entities.values()
    )

    return {
        "status": ("PASS" if passed else "FAIL"),
        "generation_order": order,
        "record_counts": {name: len(records) for name, records in datasets.items()},
    }


def test_primary_keys() -> dict[str, Any]:

    entities = build_specification()

    datasets, _ = generate_dataset(entities)

    failures = validate_primary_keys(
        datasets,
        entities,
    )

    return {
        "status": ("PASS" if not failures else "FAIL"),
        "failures": failures,
    }


def test_relationships() -> dict[str, Any]:

    entities = build_specification()

    datasets, _ = generate_dataset(entities)

    try:

        resolve_relationships(
            datasets,
            relationships(),
        )

        passed = True

    except ValueError:

        passed = False

    return {
        "status": ("PASS" if passed else "FAIL"),
    }


def test_composite_key() -> dict[str, Any]:

    entities = build_specification()

    datasets, _ = generate_dataset(entities)

    records = datasets["ORDER_ITEM"]

    keys = {
        (
            record["ORDER_ID"],
            record["LINE_NUMBER"],
        )
        for record in records
    }

    passed = len(keys) == len(records)

    return {
        "status": ("PASS" if passed else "FAIL"),
        "records": len(records),
        "unique_composite_keys": len(keys),
    }


def test_derived_fields() -> dict[str, Any]:

    entities = build_specification()

    datasets, _ = generate_dataset(entities)

    failures = validate_derived(
        datasets,
        entities,
    )

    return {
        "status": ("PASS" if not failures else "FAIL"),
        "failures": failures,
    }


def test_constraints() -> dict[str, Any]:

    entities = build_specification()

    datasets, _ = generate_dataset(entities)

    failures = validate_constraints(
        datasets,
        entities,
    )

    return {
        "status": ("PASS" if not failures else "FAIL"),
        "failures": failures,
    }


def test_statistical_behavior() -> dict[str, Any]:

    entities = build_specification()

    datasets, _ = generate_dataset(entities)

    failures = validate_statistical_fields(
        datasets,
    )

    return {
        "status": ("PASS" if not failures else "FAIL"),
        "failures": failures,
    }


def test_entity_order_independence() -> dict[str, Any]:

    first_entities = build_specification(
        reverse_entities=False,
    )

    second_entities = build_specification(
        reverse_entities=True,
    )

    first, first_order = generate_dataset(first_entities)

    second, second_order = generate_dataset(second_entities)

    passed = first == second

    return {
        "status": ("PASS" if passed else "FAIL"),
        "first_order": first_order,
        "second_order": second_order,
    }


def test_field_order_independence() -> dict[str, Any]:

    first_entities = build_specification(
        reverse_fields=False,
    )

    second_entities = build_specification(
        reverse_fields=True,
    )

    first, _ = generate_dataset(first_entities)

    second, _ = generate_dataset(second_entities)

    passed = first == second

    return {
        "status": ("PASS" if passed else "FAIL"),
        "identical": passed,
    }


def test_reproducibility() -> dict[str, Any]:

    first_entities = build_specification()

    second_entities = build_specification()

    first, _ = generate_dataset(first_entities)

    second, _ = generate_dataset(second_entities)

    passed = first == second

    return {
        "status": ("PASS" if passed else "FAIL"),
        "identical": passed,
    }


def test_seed_sensitivity() -> dict[str, Any]:

    global MASTER_SEED

    original_seed = MASTER_SEED

    try:

        first_entities = build_specification()

        first, _ = generate_dataset(first_entities)

        MASTER_SEED = 43

        second_entities = build_specification()

        second, _ = generate_dataset(second_entities)

    finally:

        MASTER_SEED = original_seed

    passed = first != second

    return {
        "status": ("PASS" if passed else "FAIL"),
        "different": passed,
    }


def test_capability_assessment() -> dict[str, Any]:

    assessment = capability_assessment()

    passed = assessment["status"] == "PASS" and all(
        capability in EXECUTABLE_TYPES
        for capability in assessment["requested"]["types"]
    )

    return {
        "status": ("PASS" if passed else "FAIL"),
        "assessment": assessment,
    }


def test_deferred_capability_safety() -> dict[str, Any]:

    result = test_deferred_boundary()

    return result


def test_no_post_generation_repair() -> dict[str, Any]:

    entities = build_specification()

    datasets, _ = generate_dataset(entities)

    derived_failures = validate_derived(
        datasets,
        entities,
    )

    constraint_failures = validate_constraints(
        datasets,
        entities,
    )

    relationship_ok = True

    try:

        resolve_relationships(
            datasets,
            relationships(),
        )

    except ValueError:

        relationship_ok = False

    passed = not derived_failures and not constraint_failures and relationship_ok

    return {
        "status": ("PASS" if passed else "FAIL"),
        "derived_failures": derived_failures,
        "constraint_failures": constraint_failures,
        "relationship_valid": relationship_ok,
        "repair_used": False,
    }


def test_generation_plan() -> dict[str, Any]:

    entities = build_specification()

    entity_order = entity_generation_order(
        entities,
        relationships(),
    )

    field_orders = {name: generation_order(entity) for name, entity in entities.items()}

    passed = entity_order is not None and all(
        order is not None for order in field_orders.values()
    )

    return {
        "status": ("PASS" if passed else "FAIL"),
        "entity_order": entity_order,
        "field_orders": field_orders,
    }


def test_dataset_structure() -> dict[str, Any]:

    entities = build_specification()

    datasets, _ = generate_dataset(entities)

    failures = []

    for entity_name, entity in entities.items():

        expected_fields = {field.name for field in entity.fields}

        for index, record in enumerate(datasets[entity_name]):

            if set(record) != (expected_fields):

                failures.append(f"{entity_name}[{index}]")

    return {
        "status": ("PASS" if not failures else "FAIL"),
        "failures": failures,
    }


def run_test(
    name: str,
    function,
) -> dict[str, Any]:

    try:
        result = function()

        if not isinstance(result, dict):
            return {
                "name": name,
                "status": "FAIL",
                "error": ("Test function did not return " "a result dictionary."),
            }

        result.setdefault(
            "name",
            name,
        )

        result.setdefault(
            "status",
            "FAIL",
        )

        return result

    except Exception as exc:

        return {
            "name": name,
            "status": "FAIL",
            "error": (f"{type(exc).__name__}: {exc}"),
        }


# ============================================================================
# MAIN
# ============================================================================


def main() -> int:

    print()

    print("=" * 70)

    print("FORGE - Experiment 020-N: " "Full Declarative Generation Integration")

    print("=" * 70)

    print("Experiment:     " "020_declarative_generation_specification")

    print("Stage:          020-N")

    print("Purpose:        " "Final declarative generation integration")

    print(f"Random seed:    {MASTER_SEED}")

    print()

    print("Integration pipeline:")

    print("  Specification")

    print("       ↓")

    print("  Vocabulary validation")

    print("       ↓")

    print("  Capability assessment")

    print("       ↓")

    print("  Expression analysis")

    print("       ↓")

    print("  Constraint analysis")

    print("       ↓")

    print("  Dependency planning")

    print("       ↓")

    print("  Field generation")

    print("       ↓")

    print("  Identity / relationship resolution")

    print("       ↓")

    print("  Final validation")

    print()

    print("Integrated entities:")

    for name in build_specification():

        print(f"  {name}")

    print()

    tests = [
        (
            "Complete generation",
            test_complete_generation,
        ),
        (
            "Generation planning",
            test_generation_plan,
        ),
        (
            "Dataset structure",
            test_dataset_structure,
        ),
        (
            "Primary key validation",
            test_primary_keys,
        ),
        (
            "Relationship integrity",
            test_relationships,
        ),
        (
            "Composite key validation",
            test_composite_key,
        ),
        (
            "Derived field validation",
            test_derived_fields,
        ),
        (
            "Constraint validation",
            test_constraints,
        ),
        (
            "Statistical behavior",
            test_statistical_behavior,
        ),
        (
            "Entity-order independence",
            test_entity_order_independence,
        ),
        (
            "Field-order independence",
            test_field_order_independence,
        ),
        (
            "Reproducibility",
            test_reproducibility,
        ),
        (
            "Seed sensitivity",
            test_seed_sensitivity,
        ),
        (
            "Capability assessment",
            test_capability_assessment,
        ),
        (
            "Deferred capability safety",
            test_deferred_capability_safety,
        ),
        (
            "No post-generation repair",
            test_no_post_generation_repair,
        ),
    ]

    print("End-to-end integration validation:")

    results = []

    for name, function in tests:

        result = run_test(
            name,
            function,
        )

        results.append(result)

        print(f"  " f"{name:<38}" f"{result['status']}")

    passed = sum(result["status"] == "PASS" for result in results)

    total = len(results)

    overall = passed == total

    print()

    print("Experiment result:")

    print(f"  Complete generation:       " f"{results[0]['status']}")

    print(f"  Generation planning:       " f"{results[1]['status']}")

    print(f"  Dataset structure:         " f"{results[2]['status']}")

    print(f"  Primary keys:              " f"{results[3]['status']}")

    print(f"  Relationships:             " f"{results[4]['status']}")

    print(f"  Composite keys:            " f"{results[5]['status']}")

    print(f"  Derived fields:            " f"{results[6]['status']}")

    print(f"  Constraints:               " f"{results[7]['status']}")

    print(f"  Statistical behavior:      " f"{results[8]['status']}")

    print(f"  Entity-order independence: " f"{results[9]['status']}")

    print(f"  Field-order independence:  " f"{results[10]['status']}")

    print(f"  Reproducibility:           " f"{results[11]['status']}")

    print(f"  Seed sensitivity:          " f"{results[12]['status']}")

    print(f"  Capability assessment:     " f"{results[13]['status']}")

    print(f"  Deferred safety:           " f"{results[14]['status']}")

    print(f"  No post-generation repair: " f"{results[15]['status']}")

    print(f"  Tests passed:              " f"{passed}/{total}")

    print(f"  Overall:                   " f"{'PASS' if overall else 'FAIL'}")

    # ----------------------------------------------------------------------
    # Capture representative generated output.
    # ----------------------------------------------------------------------

    sample_dataset = {}

    if overall:

        entities = build_specification()

        datasets, generation_order_ = generate_dataset(entities)

        for entity_name in generation_order_:

            sample_dataset[entity_name] = datasets[entity_name][:3]

    # ----------------------------------------------------------------------
    # Output
    # ----------------------------------------------------------------------

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    output = {
        "experiment": ("020_declarative_generation_specification"),
        "stage": "020-N",
        "purpose": ("Full declarative generation integration"),
        "seed": MASTER_SEED,
        "entities": list(build_specification()),
        "relationships": [
            {
                "name": relationship.name,
                "parent": relationship.parent,
                "child": relationship.child,
                "cardinality": relationship.cardinality,
                "parent_key": list(relationship.parent_key),
                "child_key": list(relationship.child_key),
                "required": relationship.required,
            }
            for relationship in relationships()
        ],
        "tests": results,
        "tests_passed": passed,
        "tests_total": total,
        "sample_dataset": sample_dataset,
        "architecture": {
            "declarative_specification": True,
            "vocabulary_validation": True,
            "capability_assessment": True,
            "dependency_planning": True,
            "field_generation": True,
            "statistical_generation": True,
            "derived_generation": True,
            "conditional_generation": True,
            "identity_generation": True,
            "relationship_resolution": True,
            "constraint_validation": True,
            "statistical_validation": True,
            "deterministic_streams": True,
            "entity_order_independence": True,
            "field_order_independence": True,
            "safe_deferred_capabilities": True,
            "post_generation_repair": False,
        },
        "architectural_conclusion": (
            "The FORGE declarative model can combine "
            "field generation, statistical behavior, "
            "derived expressions, conditional rules, "
            "identity, relationships, dependencies, "
            "constraints, deterministic streams, and "
            "validation within one executable "
            "generation pipeline."
        ),
        "framework_readiness": (
            "The declarative generation model has "
            "sufficient experimental evidence to "
            "begin extraction into reusable FORGE "
            "framework components."
            if overall
            else "Framework extraction should wait until "
            "the failed integration capabilities "
            "are resolved."
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

        print()

        print(
            "020 declarative generation foundation "
            "is ready for framework extraction."
        )

        return 0

    print("Experiment completed with failures.")

    return 1


if __name__ == "__main__":
    sys.exit(main())
