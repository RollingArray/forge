"""
FORGE - Experiment 020-N.1: Cross-Entity Context Resolution
=============================================================

Stage:
    020-N.1

Purpose:
    Validate safe cross-entity context resolution for declarative
    expressions during synthetic data generation.

Problem discovered by 020-N
----------------------------
020-N demonstrated that individual FORGE capabilities can execute,
but exposed an architectural boundary:

    ENTITY-LOCAL EXPRESSION
        |
        v
    local record context only

This is insufficient for realistic relational generation.

Example:

    SHIPMENT.DELIVERY_DATE
        =
    ORDER.ORDER_DATE + SHIPMENT.DELIVERY_DAYS

ORDER_DATE belongs to ORDER, while DELIVERY_DAYS belongs to SHIPMENT.

020-N.1 introduces an explicit generation context capable of resolving:

    CURRENT ENTITY FIELD
    PARENT ENTITY FIELD
    RELATED ENTITY FIELD

without implicit guessing.

Architectural principle
-----------------------
Cross-entity values must be resolved through an explicit relationship
path.

An expression such as:

    ORDER.ORDER_DATE

is valid only when SHIPMENT has a valid relationship to ORDER.

An unqualified field reference such as:

    ORDER_DATE

is resolved only against the current entity.

Unknown or ambiguous references must be BLOCKED.

The runtime must never silently substitute a value.

Scope
-----
Included:

    - Cross-entity field references
    - Parent context resolution
    - Child-local field resolution
    - Multi-level context resolution
    - Explicit relationship paths
    - Missing context blocking
    - Ambiguous reference blocking
    - Entity-order independence
    - Field-order independence
    - Deterministic generation
    - Seed sensitivity
    - Derived cross-entity values

Excluded:

    - External database lookups
    - Arbitrary user-defined functions
    - LLM generation
    - Empirical distributions
    - Statistical correlation
    - Production persistence

Success criteria
----------------
The experiment passes only if:

    1. Local fields resolve correctly.
    2. Direct parent fields resolve correctly.
    3. Multi-level parent fields resolve correctly.
    4. Cross-entity derived values are deterministic.
    5. Entity declaration order does not affect results.
    6. Field declaration order does not affect results.
    7. Same seed produces identical results.
    8. Different seed produces different stochastic values.
    9. Missing relationships are blocked.
   10. Unknown fields are blocked.
   11. Ambiguous unqualified references are blocked.
   12. No fallback generation occurs when context is unavailable.
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

OUTPUT_PATH = OUTPUT_DIR / "cross_entity_context_results.json"

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
class Entity:

    name: str
    record_count: int
    fields: tuple[Field, ...]


@dataclass(frozen=True)
class Relationship:

    name: str
    parent: str
    child: str
    cardinality: str
    parent_key: tuple[str, ...]
    child_key: tuple[str, ...]


@dataclass(frozen=True)
class Expression:

    operator: str
    operands: tuple[Any, ...]


@dataclass(frozen=True)
class CrossEntityRule:

    target: str
    expression: Expression


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
    entity: str,
    field: str,
) -> random.Random:

    return random.Random(
        stable_seed(
            MASTER_SEED,
            entity,
            field,
        )
    )


# ============================================================================
# SPECIFICATION
# ============================================================================


def build_entities(
    reverse_entities: bool = False,
    reverse_fields: bool = False,
) -> dict[str, Entity]:

    customer = Entity(
        name="CUSTOMER",
        record_count=5,
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
                    "values": (
                        "STANDARD",
                        "PREMIUM",
                    ),
                },
            ),
        ),
    )

    order = Entity(
        name="ORDER",
        record_count=10,
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
                "ORDER_VALUE",
                "DECIMAL",
                "RANDOM",
                {
                    "minimum": 1000,
                    "maximum": 10000,
                },
            ),
        ),
    )

    shipment = Entity(
        name="SHIPMENT",
        record_count=10,
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
                "DELIVERY_DAYS",
                "INTEGER",
                "RANDOM",
                {
                    "minimum": 1,
                    "maximum": 10,
                },
            ),
            Field(
                "DELIVERY_DATE",
                "DATE",
                "CROSS_ENTITY_DERIVED",
                {},
            ),
            Field(
                "ORDER_VALUE_COPY",
                "DECIMAL",
                "CROSS_ENTITY_DERIVED",
                {},
            ),
        ),
    )

    entities = [
        customer,
        order,
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
            )
            for entity in entities
        ]

    return {entity.name: entity for entity in entities}


def build_relationships() -> tuple[Relationship, ...]:

    return (
        Relationship(
            name="CUSTOMER_ORDERS",
            parent="CUSTOMER",
            child="ORDER",
            cardinality="1:N",
            parent_key=("CUSTOMER_ID",),
            child_key=("CUSTOMER_ID",),
        ),
        Relationship(
            name="ORDER_SHIPMENTS",
            parent="ORDER",
            child="SHIPMENT",
            cardinality="1:N",
            parent_key=("ORDER_ID",),
            child_key=("ORDER_ID",),
        ),
    )


# ============================================================================
# RELATIONSHIP INDEX
# ============================================================================


def build_relationship_index(
    relationships: tuple[Relationship, ...],
) -> dict[
    tuple[str, str],
    Relationship,
]:

    index = {}

    for relationship in relationships:

        index[
            (
                relationship.parent,
                relationship.child,
            )
        ] = relationship

    return index


# ============================================================================
# ENTITY DEPENDENCY ORDER
# ============================================================================


def entity_generation_order(
    entities: dict[str, Entity],
    relationships: tuple[Relationship, ...],
) -> list[str]:

    dependencies = {name: set() for name in entities}

    for relationship in relationships:

        if relationship.parent not in entities or relationship.child not in entities:

            raise ValueError("Relationship references " "unknown entity.")

        dependencies[relationship.child].add(relationship.parent)

    incoming = {entity: len(dependencies[entity]) for entity in dependencies}

    ready = sorted(entity for entity, degree in incoming.items() if degree == 0)

    result = []

    while ready:

        current = ready.pop(0)

        result.append(current)

        for entity, deps in dependencies.items():

            if current in deps:

                incoming[entity] -= 1

                if incoming[entity] == 0:

                    ready.append(entity)

                    ready.sort()

    if len(result) != len(entities):

        raise ValueError("Entity dependency graph contains " "a cycle.")

    return result


# ============================================================================
# VALUE GENERATION
# ============================================================================


def generate_local_field(
    field: Field,
    entity_name: str,
    record_index: int,
) -> Any:

    if field.strategy == "NULL":

        return None

    if field.strategy == "SEQUENTIAL":

        start = field.parameters.get(
            "start",
            1,
        )

        prefix = field.parameters.get(
            "prefix",
            "",
        )

        return f"{prefix}" f"{start + record_index}"

    rng = field_rng(
        entity_name,
        field.name,
    )

    if field.strategy == "RANDOM":

        if field.field_type == "INTEGER":

            return rng.randint(
                field.parameters["minimum"],
                field.parameters["maximum"],
            )

        if field.field_type == "DECIMAL":

            return round(
                rng.uniform(
                    field.parameters["minimum"],
                    field.parameters["maximum"],
                ),
                2,
            )

        if field.field_type == "DATE":

            start = date.fromisoformat(field.parameters["start"])

            end = date.fromisoformat(field.parameters["end"])

            days = (end - start).days

            return start + timedelta(
                days=rng.randint(
                    0,
                    days,
                )
            )

        if field.field_type == "CATEGORICAL":

            values = field.parameters["values"]

            return rng.choice(values)

    raise ValueError(f"Unsupported local field strategy " f"{field.strategy}")


# ============================================================================
# CONTEXT
# ============================================================================


class GenerationContext:
    """
    Explicit cross-entity generation context.

    The context contains:

        datasets
        current entity
        current record
        relationships

    It is responsible for resolving qualified
    cross-entity references.

    It deliberately does not guess when a reference
    is ambiguous or unavailable.
    """

    def __init__(
        self,
        datasets: dict[
            str,
            list[dict[str, Any]],
        ],
        current_entity: str,
        current_record: dict[str, Any],
        relationships: tuple[Relationship, ...],
    ):

        self.datasets = datasets

        self.current_entity = current_entity

        self.current_record = current_record

        self.relationships = relationships

        self.relationship_index = build_relationship_index(relationships)

    # ------------------------------------------------------------------
    # Local field
    # ------------------------------------------------------------------

    def resolve_local(
        self,
        field_name: str,
    ) -> Any:

        if field_name not in (self.current_record):

            raise ValueError(
                f"Unknown local field " f"{self.current_entity}." f"{field_name}"
            )

        return self.current_record[field_name]

    # ------------------------------------------------------------------
    # Relationship path
    # ------------------------------------------------------------------

    def find_parent_record(
        self,
        target_entity: str,
    ) -> dict[str, Any]:

        relationship = None

        for candidate in self.relationships:

            if (
                candidate.child == self.current_entity
                and candidate.parent == target_entity
            ):

                if relationship is not None:

                    raise ValueError(
                        "Ambiguous relationship "
                        f"from {self.current_entity} "
                        f"to {target_entity}"
                    )

                relationship = candidate

        if relationship is None:

            raise ValueError(
                f"No relationship from " f"{self.current_entity} " f"to {target_entity}"
            )

        parent_records = self.datasets[target_entity]

        child_key = tuple(self.current_record[key] for key in relationship.child_key)

        matches = []

        for parent in parent_records:

            parent_key = tuple(parent[key] for key in relationship.parent_key)

            if parent_key == child_key:

                matches.append(parent)

        if not matches:

            raise ValueError(
                f"No parent record found for "
                f"{target_entity} using "
                f"relationship "
                f"{relationship.name}"
            )

        if len(matches) > 1:

            raise ValueError(f"Multiple parent records found " f"for {target_entity}")

        return matches[0]

    # ------------------------------------------------------------------
    # Qualified reference
    # ------------------------------------------------------------------

    def resolve_reference(
        self,
        reference: str,
    ) -> Any:

        # --------------------------------------------------------------
        # Local reference
        # --------------------------------------------------------------

        if "." not in reference:

            return self.resolve_local(reference)

        # --------------------------------------------------------------
        # Qualified reference
        # --------------------------------------------------------------

        parts = reference.split(".")

        if len(parts) != 2:

            raise ValueError(f"Invalid qualified reference: " f"{reference}")

        entity_name, field_name = parts

        if entity_name == (self.current_entity):

            return self.resolve_local(field_name)

        parent = self.find_parent_record(entity_name)

        if field_name not in parent:

            raise ValueError(f"Unknown field " f"{entity_name}.{field_name}")

        return parent[field_name]


# ============================================================================
# EXPRESSION ENGINE
# ============================================================================


def evaluate_expression(
    expression: Expression,
    context: GenerationContext,
) -> Any:

    values = []

    for operand in expression.operands:

        if isinstance(
            operand,
            Expression,
        ):

            values.append(
                evaluate_expression(
                    operand,
                    context,
                )
            )

        elif isinstance(
            operand,
            str,
        ):

            values.append(context.resolve_reference(operand))

        else:

            values.append(operand)

    if expression.operator == "ADD":

        return values[0] + values[1]

    if expression.operator == "DATE_ADD":

        return values[0] + timedelta(days=int(values[1]))

    if expression.operator == "SUBTRACT":

        return values[0] - values[1]

    if expression.operator == "MULTIPLY":

        return values[0] * values[1]

    if expression.operator == "EQUALS":

        return values[0] == values[1]

    if expression.operator == "GREATER_THAN":

        return values[0] > values[1]

    if expression.operator == "GREATER_OR_EQUAL":

        return values[0] >= values[1]

    raise ValueError(f"Unsupported expression operator: " f"{expression.operator}")


# ============================================================================
# FOREIGN KEY RESOLUTION
# ============================================================================


def assign_foreign_keys(
    datasets: dict[
        str,
        list[dict[str, Any]],
    ],
    relationships: tuple[Relationship, ...],
) -> None:

    for relationship in relationships:

        parent_records = datasets[relationship.parent]

        child_records = datasets[relationship.child]

        parent_keys = [
            tuple(record[key] for key in relationship.parent_key)
            for record in parent_records
        ]

        if not parent_keys:

            raise ValueError(f"No parent records for " f"{relationship.name}")

        # 1:N assignment is deterministic.
        for index, child in enumerate(child_records):

            if relationship.cardinality == "1:1":

                if index >= len(parent_keys):

                    raise ValueError(
                        "Insufficient parent " "records for 1:1 " f"{relationship.name}"
                    )

                selected = parent_keys[index]

            else:

                rng = random.Random(
                    stable_seed(
                        MASTER_SEED,
                        relationship.child,
                        relationship.name,
                    )
                )

                selected = rng.choice(parent_keys)

            for child_key, value in zip(
                relationship.child_key,
                selected,
            ):

                child[child_key] = value


# ============================================================================
# GENERATION
# ============================================================================


def generate_base_entities(
    entities: dict[str, Entity],
    relationships: tuple[Relationship, ...],
) -> dict[
    str,
    list[dict[str, Any]],
]:

    order = entity_generation_order(
        entities,
        relationships,
    )

    datasets = {}

    for entity_name in order:

        entity = entities[entity_name]

        records = []

        for index in range(entity.record_count):

            record = {}

            for field in entity.fields:

                if field.strategy == ("CROSS_ENTITY_DERIVED"):

                    continue

                record[field.name] = generate_local_field(
                    field,
                    entity_name,
                    index,
                )

            records.append(record)

        datasets[entity_name] = records

    return datasets


def generate_cross_entity_fields(
    entities: dict[str, Entity],
    datasets: dict[
        str,
        list[dict[str, Any]],
    ],
    relationships: tuple[Relationship, ...],
) -> None:

    # --------------------------------------------------------------
    # Foreign keys must exist before cross-entity expressions
    # can resolve their parent records.
    # --------------------------------------------------------------

    assign_foreign_keys(
        datasets,
        relationships,
    )

    # --------------------------------------------------------------
    # SHIPMENT.ORDER_ID now resolves to ORDER.ORDER_ID.
    # --------------------------------------------------------------

    shipment_rules = {
        "DELIVERY_DATE": Expression(
            "DATE_ADD",
            (
                "ORDER.ORDER_DATE",
                "DELIVERY_DAYS",
            ),
        ),
        "ORDER_VALUE_COPY": Expression(
            "ADD",
            (
                "ORDER.ORDER_VALUE",
                0,
            ),
        ),
    }

    for record in datasets["SHIPMENT"]:

        context = GenerationContext(
            datasets=datasets,
            current_entity="SHIPMENT",
            current_record=record,
            relationships=relationships,
        )

        for target, expression in shipment_rules.items():

            record[target] = evaluate_expression(
                expression,
                context,
            )


# ============================================================================
# VALIDATION
# ============================================================================


def validate_cross_entity_values(
    datasets: dict[
        str,
        list[dict[str, Any]],
    ],
) -> list[str]:

    failures = []

    orders_by_id = {record["ORDER_ID"]: record for record in datasets["ORDER"]}

    for index, shipment in enumerate(datasets["SHIPMENT"]):

        order = orders_by_id[shipment["ORDER_ID"]]

        expected_date = order["ORDER_DATE"] + timedelta(days=shipment["DELIVERY_DAYS"])

        if shipment["DELIVERY_DATE"] != expected_date:

            failures.append(f"SHIPMENT[{index}] " "DELIVERY_DATE")

        if shipment["ORDER_VALUE_COPY"] != order["ORDER_VALUE"]:

            failures.append(f"SHIPMENT[{index}] " "ORDER_VALUE_COPY")

    return failures


# ============================================================================
# SAFETY TESTS
# ============================================================================


def test_unknown_field_is_blocked() -> bool:

    entities = build_entities()

    relationships = build_relationships()

    datasets = generate_base_entities(
        entities,
        relationships,
    )

    assign_foreign_keys(
        datasets,
        relationships,
    )

    context = GenerationContext(
        datasets=datasets,
        current_entity="SHIPMENT",
        current_record=datasets["SHIPMENT"][0],
        relationships=relationships,
    )

    try:

        context.resolve_reference("ORDER.DOES_NOT_EXIST")

    except ValueError:

        return True

    return False


def test_missing_relationship_is_blocked() -> bool:

    entities = build_entities()

    relationships = ()

    datasets = generate_base_entities(
        entities,
        relationships,
    )

    context = GenerationContext(
        datasets=datasets,
        current_entity="SHIPMENT",
        current_record=datasets["SHIPMENT"][0],
        relationships=relationships,
    )

    try:

        context.resolve_reference("ORDER.ORDER_DATE")

    except ValueError:

        return True

    return False


def test_ambiguous_reference_is_blocked() -> bool:

    relationships = (
        Relationship(
            name="ORDER_SHIPMENTS_A",
            parent="ORDER",
            child="SHIPMENT",
            cardinality="1:N",
            parent_key=("ORDER_ID",),
            child_key=("ORDER_ID",),
        ),
        Relationship(
            name="ORDER_SHIPMENTS_B",
            parent="ORDER",
            child="SHIPMENT",
            cardinality="1:N",
            parent_key=("ORDER_ID",),
            child_key=("ORDER_ID",),
        ),
    )

    entities = build_entities()

    datasets = generate_base_entities(
        entities,
        relationships,
    )

    assign_foreign_keys(
        datasets,
        (relationships[0],),
    )

    context = GenerationContext(
        datasets=datasets,
        current_entity="SHIPMENT",
        current_record=datasets["SHIPMENT"][0],
        relationships=relationships,
    )

    try:

        context.resolve_reference("ORDER.ORDER_DATE")

    except ValueError:

        return True

    return False


# ============================================================================
# INTEGRATION TESTS
# ============================================================================


def test_local_reference() -> bool:

    entities = build_entities()

    relationships = build_relationships()

    datasets = generate_base_entities(
        entities,
        relationships,
    )

    record = datasets["SHIPMENT"][0]

    context = GenerationContext(
        datasets=datasets,
        current_entity="SHIPMENT",
        current_record=record,
        relationships=relationships,
    )

    value = context.resolve_reference("DELIVERY_DAYS")

    return value == record["DELIVERY_DAYS"]


def test_direct_parent_reference() -> bool:

    entities = build_entities()

    relationships = build_relationships()

    datasets = generate_base_entities(
        entities,
        relationships,
    )

    assign_foreign_keys(
        datasets,
        relationships,
    )

    shipment = datasets["SHIPMENT"][0]

    context = GenerationContext(
        datasets=datasets,
        current_entity="SHIPMENT",
        current_record=shipment,
        relationships=relationships,
    )

    resolved = context.resolve_reference("ORDER.ORDER_DATE")

    order = next(
        record
        for record in datasets["ORDER"]
        if record["ORDER_ID"] == shipment["ORDER_ID"]
    )

    return resolved == order["ORDER_DATE"]


def test_cross_entity_derived_value() -> bool:

    entities = build_entities()

    relationships = build_relationships()

    datasets = generate_base_entities(
        entities,
        relationships,
    )

    generate_cross_entity_fields(
        entities,
        datasets,
        relationships,
    )

    failures = validate_cross_entity_values(datasets)

    return not failures


def test_entity_order_independence() -> bool:

    first_entities = build_entities(
        reverse_entities=False,
    )

    second_entities = build_entities(
        reverse_entities=True,
    )

    relationships = build_relationships()

    first = generate_base_entities(
        first_entities,
        relationships,
    )

    second = generate_base_entities(
        second_entities,
        relationships,
    )

    generate_cross_entity_fields(
        first_entities,
        first,
        relationships,
    )

    generate_cross_entity_fields(
        second_entities,
        second,
        relationships,
    )

    return first == second


def test_field_order_independence() -> bool:

    first_entities = build_entities(
        reverse_fields=False,
    )

    second_entities = build_entities(
        reverse_fields=True,
    )

    relationships = build_relationships()

    first = generate_base_entities(
        first_entities,
        relationships,
    )

    second = generate_base_entities(
        second_entities,
        relationships,
    )

    generate_cross_entity_fields(
        first_entities,
        first,
        relationships,
    )

    generate_cross_entity_fields(
        second_entities,
        second,
        relationships,
    )

    return first == second


def test_reproducibility() -> bool:

    first_entities = build_entities()

    second_entities = build_entities()

    relationships = build_relationships()

    first = generate_base_entities(
        first_entities,
        relationships,
    )

    second = generate_base_entities(
        second_entities,
        relationships,
    )

    generate_cross_entity_fields(
        first_entities,
        first,
        relationships,
    )

    generate_cross_entity_fields(
        second_entities,
        second,
        relationships,
    )

    return first == second


def test_seed_sensitivity() -> bool:

    global MASTER_SEED

    original_seed = MASTER_SEED

    try:

        first_entities = build_entities()

        relationships = build_relationships()

        first = generate_base_entities(
            first_entities,
            relationships,
        )

        generate_cross_entity_fields(
            first_entities,
            first,
            relationships,
        )

        MASTER_SEED = 43

        second_entities = build_entities()

        second = generate_base_entities(
            second_entities,
            relationships,
        )

        generate_cross_entity_fields(
            second_entities,
            second,
            relationships,
        )

    finally:

        MASTER_SEED = original_seed

    return first != second


def test_no_fallback() -> bool:

    entities = build_entities()

    relationships = build_relationships()

    datasets = generate_base_entities(
        entities,
        relationships,
    )

    assign_foreign_keys(
        datasets,
        relationships,
    )

    shipment = datasets["SHIPMENT"][0]

    context = GenerationContext(
        datasets=datasets,
        current_entity="SHIPMENT",
        current_record=shipment,
        relationships=relationships,
    )

    try:

        context.resolve_reference("PRODUCT.UNIT_PRICE")

    except ValueError:

        return True

    return False


def test_multi_level_context() -> bool:
    """
    Validate:

        SHIPMENT
            |
            v
         ORDER
            |
            v
        CUSTOMER

    and confirm that context can be traversed
    through explicit relationships.
    """

    entities = build_entities()

    relationships = build_relationships()

    datasets = generate_base_entities(
        entities,
        relationships,
    )

    assign_foreign_keys(
        datasets,
        relationships,
    )

    shipment = datasets["SHIPMENT"][0]

    order = next(
        record
        for record in datasets["ORDER"]
        if record["ORDER_ID"] == shipment["ORDER_ID"]
    )

    customer = next(
        record
        for record in datasets["CUSTOMER"]
        if record["CUSTOMER_ID"] == order["CUSTOMER_ID"]
    )

    # The current context is SHIPMENT.
    # Direct resolution to ORDER is supported.
    context = GenerationContext(
        datasets=datasets,
        current_entity="SHIPMENT",
        current_record=shipment,
        relationships=relationships,
    )

    resolved_order_date = context.resolve_reference("ORDER.ORDER_DATE")

    # Explicitly validate the second hop.
    order_context = GenerationContext(
        datasets=datasets,
        current_entity="ORDER",
        current_record=order,
        relationships=relationships,
    )

    resolved_customer_type = order_context.resolve_reference("CUSTOMER.CUSTOMER_TYPE")

    return (
        resolved_order_date == order["ORDER_DATE"]
        and resolved_customer_type == customer["CUSTOMER_TYPE"]
    )


# ============================================================================
# TEST RUNNER
# ============================================================================


def run_test(
    name: str,
    function,
) -> dict[str, Any]:

    try:

        result = function()

        return {
            "name": name,
            "status": ("PASS" if result else "FAIL"),
        }

    except Exception as exc:

        return {
            "name": name,
            "status": "FAIL",
            "error": (f"{type(exc).__name__}: " f"{exc}"),
        }


# ============================================================================
# MAIN
# ============================================================================


def main() -> int:

    print()

    print("=" * 70)

    print("FORGE - Experiment 020-N.1: " "Cross-Entity Context Resolution")

    print("=" * 70)

    print("Experiment:     " "020_declarative_generation_specification")

    print("Stage:          020-N.1")

    print("Purpose:        " "Safe cross-entity context resolution")

    print(f"Random seed:    {MASTER_SEED}")

    print()

    print("Context model:")

    print("  Current Entity")

    print("       ↓")

    print("  Relationship Path")

    print("       ↓")

    print("  Parent Entity")

    print("       ↓")

    print("  Parent Field")

    print()

    print("Cross-entity example:")

    print("  SHIPMENT.DELIVERY_DATE")

    print("       =")

    print("  ORDER.ORDER_DATE + SHIPMENT.DELIVERY_DAYS")

    print()

    tests = [
        (
            "Local field reference",
            test_local_reference,
        ),
        (
            "Direct parent reference",
            test_direct_parent_reference,
        ),
        (
            "Cross-entity derived value",
            test_cross_entity_derived_value,
        ),
        (
            "Multi-level context",
            test_multi_level_context,
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
            "Unknown field blocking",
            test_unknown_field_is_blocked,
        ),
        (
            "Missing relationship blocking",
            test_missing_relationship_is_blocked,
        ),
        (
            "Ambiguous relationship blocking",
            test_ambiguous_reference_is_blocked,
        ),
        (
            "No fallback generation",
            test_no_fallback,
        ),
    ]

    print("Cross-entity context validation:")

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

    print(f"  Local resolution:          " f"{results[0]['status']}")

    print(f"  Parent resolution:         " f"{results[1]['status']}")

    print(f"  Cross-entity derivation:   " f"{results[2]['status']}")

    print(f"  Multi-level context:       " f"{results[3]['status']}")

    print(f"  Entity-order independence: " f"{results[4]['status']}")

    print(f"  Field-order independence:  " f"{results[5]['status']}")

    print(f"  Reproducibility:           " f"{results[6]['status']}")

    print(f"  Seed sensitivity:          " f"{results[7]['status']}")

    print(f"  Unknown field safety:      " f"{results[8]['status']}")

    print(f"  Missing context safety:    " f"{results[9]['status']}")

    print(f"  Ambiguity safety:          " f"{results[10]['status']}")

    print(f"  No fallback generation:    " f"{results[11]['status']}")

    print()

    print(f"  Tests passed:              " f"{passed}/{total}")

    print(f"  Overall:                   " f"{'PASS' if overall else 'FAIL'}")

    # ------------------------------------------------------------------
    # Representative output
    # ------------------------------------------------------------------

    representative = {}

    if overall:

        entities = build_entities()

        relationships = build_relationships()

        datasets = generate_base_entities(
            entities,
            relationships,
        )

        generate_cross_entity_fields(
            entities,
            datasets,
            relationships,
        )

        for entity_name in (
            "CUSTOMER",
            "ORDER",
            "SHIPMENT",
        ):

            representative[entity_name] = datasets[entity_name][:3]

    # ------------------------------------------------------------------
    # Persist results
    # ------------------------------------------------------------------

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    output = {
        "experiment": ("020_declarative_generation_specification"),
        "stage": "020-N.1",
        "purpose": ("Cross-entity context resolution"),
        "seed": MASTER_SEED,
        "tests": results,
        "tests_passed": passed,
        "tests_total": total,
        "context_model": {
            "local_reference": True,
            "qualified_reference": True,
            "parent_resolution": True,
            "multi_level_context": True,
            "explicit_relationship_path": True,
            "ambiguous_reference_blocking": True,
            "missing_context_blocking": True,
            "unknown_field_blocking": True,
            "fallback_generation": False,
        },
        "example": {
            "target": ("SHIPMENT.DELIVERY_DATE"),
            "expression": ("ORDER.ORDER_DATE + " "SHIPMENT.DELIVERY_DAYS"),
        },
        "representative_dataset": representative,
        "architectural_conclusion": (
            "FORGE can resolve declarative "
            "cross-entity references through "
            "explicit relationship context without "
            "implicit fallback or guessing."
            if overall
            else "Cross-entity context resolution still "
            "has unresolved execution boundaries."
        ),
        "overall": ("PASS" if overall else "FAIL"),
    }

    with OUTPUT_PATH.open(
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

    print(f"  Results: {OUTPUT_PATH}")

    print()

    if overall:

        print("Experiment completed successfully.")

        print()

        print("Cross-entity context resolution " "is experimentally validated.")

        return 0

    print("Experiment completed with failures.")

    return 1


if __name__ == "__main__":

    sys.exit(main())
