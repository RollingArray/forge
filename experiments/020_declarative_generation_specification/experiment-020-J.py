"""
FORGE - Experiment 020-J: End-to-End Declarative Generation
=============================================================

Purpose
-------
This experiment integrates the foundational capabilities established by
Experiments 020-A through 020-I into one generic end-to-end generation
pipeline.

The experiment verifies that a complete declarative specification can be
validated, planned, executed, related, and validated without
entity-specific generation logic.

Stage
-----
020-J - End-to-End Declarative Execution

Research Question
-----------------
Can FORGE execute a complete declarative synthetic-data specification
from specification through generated dataset while preserving the
semantics established by the previous experiments?

Hypothesis
----------
The capabilities established in Experiments 020-A through 020-I can be
composed into a generic execution pipeline.

The pipeline should:

    1. validate the specification
    2. assess executable capabilities
    3. construct the dependency graph
    4. derive a deterministic generation order
    5. generate entity records
    6. generate identities
    7. resolve foreign-key relationships
    8. apply population / nullability
    9. validate the generated dataset
   10. produce an execution result

The pipeline must not depend on business-specific entity names.

Scope
-----
Included:

    - complete declarative specification
    - multiple entities
    - primitive and semantic types
    - constant generation
    - random generation
    - sequential generation
    - categorical generation
    - numeric distributions
    - population control
    - nullability
    - primary identities
    - foreign-key resolution
    - 1:N relationships
    - 0:1 relationships
    - N:M through associative entity
    - dependency planning
    - deterministic generation
    - entity-order independence
    - final dataset validation
    - safe capability blocking

Excluded:

    - unsupported transformation execution
    - arbitrary derived-field execution
    - statistical correlation execution
    - scenario overrides
    - provenance generation
    - LLM specification translation
    - production persistence

Those capabilities remain separate concerns.

Important Architectural Principle
---------------------------------
020-J is an integration experiment, not a second implementation of every
previous experiment.

The execution pipeline composes generic capabilities.

The entities used here are deliberately domain-neutral:

    CUSTOMER
    CUSTOMER_PROFILE
    PRODUCT
    ORDER
    ORDER_ITEM
    SHIPMENT

These names exist only to exercise a realistic relational topology.

No generator branch should contain logic such as:

    if entity == "ORDER":
        ...

The specification determines the behavior.

Safe Capability Boundary
------------------------
A valid FORGE specification may contain vocabulary that the current
runtime cannot execute.

That must not result in silent approximation.

Therefore this experiment contains:

    NORMAL specification
        -> generation allowed

    BLOCKED specification
        -> specification valid
        -> unsupported capability detected
        -> generation refused safely

A capability being deferred is not a validation failure.

It is an execution-planning decision.

Determinism
-----------
The same specification and seed must produce the same dataset.

Changing the entity declaration order must not change the generated
values or relationship assignments.

Author
------
Ranjoy Sen

Status
------
Experimental

How to Run
----------
From the repository root:

    uv run python experiments/020_declarative_generation_specification/experiment-020-J.py

Output
------
Results are written to:

    experiments/020_declarative_generation_specification/output/

Important
---------
All generated data is synthetic and domain-neutral.
"""

from __future__ import annotations

import json
import random
import sys
from copy import deepcopy
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from pathlib import Path
from typing import Any

# ============================================================================
# PATHS / CONSTANTS
# ============================================================================

EXPERIMENT_DIR = Path(__file__).resolve().parent

OUTPUT_DIR = EXPERIMENT_DIR / "output"

RESULT_OUTPUT_PATH = OUTPUT_DIR / "end_to_end_results.json"

RANDOM_SEED = 42


# ============================================================================
# EXECUTABLE CAPABILITIES
# ============================================================================

EXECUTABLE_TYPES = {
    "INTEGER",
    "DECIMAL",
    "FLOAT",
    "STRING",
    "BOOLEAN",
    "DATE",
    "DATETIME",
    "TIME",
    "CATEGORICAL",
    "ENUM",
    "IDENTIFIER",
    "CODE",
    "PERCENTAGE",
    "CURRENCY",
}

EXECUTABLE_STRATEGIES = {
    "CONSTANT",
    "SEQUENTIAL",
    "RANDOM",
    "NULL",
}

EXECUTABLE_DISTRIBUTIONS = {
    "CATEGORICAL",
    "DISCRETE_UNIFORM",
    "NORMAL",
    "UNIFORM",
}


# ============================================================================
# DECLARATIVE MODELS
# ============================================================================


@dataclass(frozen=True)
class FieldSpecification:
    """
    Declarative field generation definition.
    """

    name: str
    type: str
    strategy: str

    semantic: str | None = None
    distribution: str | None = None

    parameters: dict[str, Any] | None = None

    nullable: bool = False
    population_rate: float = 1.0


@dataclass(frozen=True)
class EntitySpecification:
    """
    Declarative entity definition.
    """

    name: str
    record_count: int
    fields: tuple[FieldSpecification, ...]


@dataclass(frozen=True)
class RelationshipSpecification:
    """
    Declarative relationship definition.
    """

    name: str

    parent: str
    child: str

    parent_key: str
    child_key: str

    cardinality: str
    requirement: str

    associative: bool = False


@dataclass(frozen=True)
class GenerationSpecification:
    """
    Complete executable specification.
    """

    entities: tuple[EntitySpecification, ...]

    relationships: tuple[RelationshipSpecification, ...]

    seed: int = RANDOM_SEED


# ============================================================================
# FIELD GENERATOR
# ============================================================================


class FieldGenerator:
    """
    Generic field generator.

    No entity-specific logic exists here.
    """

    def __init__(
        self,
        seed: int,
    ) -> None:

        self.seed = seed

    # ------------------------------------------------------------------------
    # Field stream
    # ------------------------------------------------------------------------

    def _rng(
        self,
        entity_name: str,
        field_name: str,
    ) -> random.Random:

        material = f"{self.seed}:" f"{entity_name}:" f"{field_name}"

        derived = hash(material) & ((1 << 63) - 1)

        return random.Random(derived)

    # ------------------------------------------------------------------------
    # Generate
    # ------------------------------------------------------------------------

    def generate(
        self,
        entity_name: str,
        field: FieldSpecification,
        record_count: int,
    ) -> list[Any]:

        if field.strategy not in EXECUTABLE_STRATEGIES:

            raise ValueError(f"Strategy '{field.strategy}' " "is not executable.")

        if (
            field.distribution is not None
            and field.distribution not in EXECUTABLE_DISTRIBUTIONS
        ):

            raise ValueError(
                f"Distribution " f"'{field.distribution}' " "is not executable."
            )

        if field.type not in EXECUTABLE_TYPES:

            raise ValueError(f"Type '{field.type}' " "is not executable.")

        parameters = field.parameters or {}

        if field.strategy == "CONSTANT":

            values = [parameters.get("value") for _ in range(record_count)]

        elif field.strategy == "NULL":

            values = [None for _ in range(record_count)]

        elif field.strategy == "SEQUENTIAL":

            start = int(
                parameters.get(
                    "start",
                    1,
                )
            )

            prefix = str(
                parameters.get(
                    "prefix",
                    "",
                )
            )

            values = [(f"{prefix}" f"{start + index}") for index in range(record_count)]

        elif field.strategy == "RANDOM":

            rng = self._rng(
                entity_name,
                field.name,
            )

            values = self._generate_random(
                rng,
                field,
                parameters,
                record_count,
            )

        else:

            raise ValueError(f"Unsupported strategy: " f"{field.strategy}")

        return self._apply_population(
            values,
            field,
        )

    # ------------------------------------------------------------------------
    # Random generation
    # ------------------------------------------------------------------------

    def _generate_random(
        self,
        rng: random.Random,
        field: FieldSpecification,
        parameters: dict[str, Any],
        record_count: int,
    ) -> list[Any]:

        distribution = field.distribution

        if distribution == "UNIFORM":

            low = float(
                parameters.get(
                    "min",
                    0,
                )
            )

            high = float(
                parameters.get(
                    "max",
                    1,
                )
            )

            values = [
                rng.uniform(
                    low,
                    high,
                )
                for _ in range(record_count)
            ]

        elif distribution == "DISCRETE_UNIFORM":

            low = int(
                parameters.get(
                    "min",
                    0,
                )
            )

            high = int(
                parameters.get(
                    "max",
                    100,
                )
            )

            values = [
                rng.randint(
                    low,
                    high,
                )
                for _ in range(record_count)
            ]

        elif distribution == "NORMAL":

            mean = float(
                parameters.get(
                    "mean",
                    0,
                )
            )

            stddev = float(
                parameters.get(
                    "stddev",
                    1,
                )
            )

            values = [
                rng.gauss(
                    mean,
                    stddev,
                )
                for _ in range(record_count)
            ]

        elif distribution == "CATEGORICAL":

            categories = parameters.get("values")

            weights = parameters.get("weights")

            if not categories:

                raise ValueError(
                    f"Categorical field " f"'{field.name}' requires " "values."
                )

            if weights:

                values = [
                    rng.choices(
                        categories,
                        weights=weights,
                        k=1,
                    )[0]
                    for _ in range(record_count)
                ]

            else:

                values = [rng.choice(categories) for _ in range(record_count)]

        else:

            raise ValueError(f"Unsupported distribution: " f"{distribution}")

        return values

    # ------------------------------------------------------------------------
    # Population
    # ------------------------------------------------------------------------

    def _apply_population(
        self,
        values: list[Any],
        field: FieldSpecification,
    ) -> list[Any]:

        if field.population_rate >= 1.0:

            return values

        if field.population_rate <= 0.0:

            if not field.nullable:

                raise ValueError(
                    f"Field '{field.name}' "
                    "cannot have zero population "
                    "when it is not nullable."
                )

            return [None for _ in values]

        rng = self._rng(
            "POPULATION",
            field.name,
        )

        result = []

        for value in values:

            if rng.random() <= field.population_rate:

                result.append(value)

            else:

                if not field.nullable:

                    raise ValueError(
                        f"Field '{field.name}' "
                        "population rate would "
                        "produce null for a "
                        "non-nullable field."
                    )

                result.append(None)

        return result


# ============================================================================
# CAPABILITY ASSESSMENT
# ============================================================================


def assess_capabilities(
    specification: GenerationSpecification,
) -> dict[str, Any]:

    deferred: list[dict[str, Any]] = []

    for entity in specification.entities:

        for field in entity.fields:

            if field.type not in EXECUTABLE_TYPES:

                deferred.append(
                    {
                        "entity": entity.name,
                        "field": field.name,
                        "kind": "type",
                        "value": field.type,
                    }
                )

            if field.strategy not in EXECUTABLE_STRATEGIES:

                deferred.append(
                    {
                        "entity": entity.name,
                        "field": field.name,
                        "kind": "strategy",
                        "value": field.strategy,
                    }
                )

            if (
                field.distribution is not None
                and field.distribution not in EXECUTABLE_DISTRIBUTIONS
            ):

                deferred.append(
                    {
                        "entity": entity.name,
                        "field": field.name,
                        "kind": "distribution",
                        "value": (field.distribution),
                    }
                )

    return {
        "status": ("PASS" if not deferred else "BLOCKED"),
        "deferred": deferred,
    }


# ============================================================================
# DEPENDENCY GRAPH
# ============================================================================


class DependencyPlanner:
    """
    Generic deterministic topological planner.
    """

    def __init__(
        self,
        entities: list[str],
        relationships: list[RelationshipSpecification],
    ) -> None:

        self.entities = set(entities)

        self.relationships = list(relationships)

        self.edges: dict[
            str,
            set[str],
        ] = {entity: set() for entity in entities}

    def build(
        self,
    ) -> None:

        for relationship in self.relationships:

            if relationship.parent not in self.entities:

                raise ValueError(f"Unknown parent entity: " f"{relationship.parent}")

            if relationship.child not in self.entities:

                raise ValueError(f"Unknown child entity: " f"{relationship.child}")

            if relationship.parent == relationship.child:

                raise ValueError(f"Self dependency: " f"{relationship.parent}")

            self.edges[relationship.parent].add(relationship.child)

    def plan(
        self,
    ) -> list[str]:

        self.build()

        indegree = {entity: 0 for entity in self.entities}

        for parent, children in self.edges.items():

            for child in children:

                indegree[child] += 1

        ready = sorted(entity for entity, degree in indegree.items() if degree == 0)

        result = []

        while ready:

            current = ready.pop(0)

            result.append(current)

            for child in sorted(self.edges[current]):

                indegree[child] -= 1

                if indegree[child] == 0:

                    ready.append(child)

            ready.sort()

        if len(result) != len(self.entities):

            raise ValueError("Dependency cycle detected.")

        return result


# ============================================================================
# EXECUTION ENGINE
# ============================================================================


class DeclarativeExecutionEngine:
    """
    End-to-end execution coordinator.

    The engine composes:

        capability assessment
        dependency planning
        field generation
        identity generation
        relationship resolution
        final validation
    """

    def __init__(
        self,
        seed: int,
    ) -> None:

        self.seed = seed

    # ------------------------------------------------------------------------
    # Execute
    # ------------------------------------------------------------------------

    def execute(
        self,
        specification: GenerationSpecification,
    ) -> dict[str, Any]:

        capability = assess_capabilities(specification)

        if capability["status"] != "PASS":

            return {
                "status": "BLOCKED",
                "phase": ("CAPABILITY_ASSESSMENT"),
                "capability": capability,
            }

        entities_by_name = {entity.name: entity for entity in specification.entities}

        planner = DependencyPlanner(
            list(entities_by_name.keys()),
            list(specification.relationships),
        )

        try:

            execution_order = planner.plan()

        except ValueError as exc:

            return {
                "status": "BLOCKED",
                "phase": ("DEPENDENCY_PLANNING"),
                "error": str(exc),
            }

        generated: dict[
            str,
            list[dict[str, Any]],
        ] = {}

        field_generator = FieldGenerator(self.seed)

        # --------------------------------------------------------------
        # Generate entities in derived order.
        # --------------------------------------------------------------

        for entity_name in execution_order:

            entity = entities_by_name[entity_name]

            records = [{} for _ in range(entity.record_count)]

            for field in entity.fields:

                values = field_generator.generate(
                    entity_name,
                    field,
                    entity.record_count,
                )

                for index, value in enumerate(values):

                    records[index][field.name] = value

            generated[entity_name] = records

        # --------------------------------------------------------------
        # Resolve relationships.
        # --------------------------------------------------------------

        relationship_results = []

        for relationship in specification.relationships:

            result = self._resolve_relationship(
                relationship,
                generated,
            )

            relationship_results.append(result)

            if result["status"] != "PASS":

                return {
                    "status": "FAIL",
                    "phase": ("RELATIONSHIP_RESOLUTION"),
                    "execution_order": (execution_order),
                    "relationships": (relationship_results),
                    "entities": generated,
                }

        # --------------------------------------------------------------
        # Validate final dataset.
        # --------------------------------------------------------------

        validation = self._validate_dataset(
            specification,
            generated,
        )

        overall = validation["status"] == "PASS"

        return {
            "status": ("PASS" if overall else "FAIL"),
            "phase": "COMPLETED",
            "execution_order": (execution_order),
            "relationships": (relationship_results),
            "validation": validation,
            "entities": generated,
        }

    # ------------------------------------------------------------------------
    # Relationship resolution
    # ------------------------------------------------------------------------

    def _resolve_relationship(
        self,
        relationship: RelationshipSpecification,
        generated: dict[
            str,
            list[dict[str, Any]],
        ],
    ) -> dict[str, Any]:

        parent_records = generated[relationship.parent]

        child_records = generated[relationship.child]

        parent_values = [record[relationship.parent_key] for record in parent_records]

        if not parent_values:

            return {
                "status": "FAIL",
                "relationship": (relationship.name),
                "reason": ("Parent entity is empty."),
            }

        if len(parent_values) != len(set(parent_values)):

            return {
                "status": "FAIL",
                "relationship": (relationship.name),
                "reason": ("Parent identity is " "not unique."),
            }

        # --------------------------------------------------------------
        # 1:1 / 0:1
        # --------------------------------------------------------------

        if relationship.cardinality in {"1:1", "0:1"}:

            if relationship.requirement == "REQUIRED" and len(child_records) > len(
                parent_values
            ):

                return {
                    "status": "FAIL",
                    "relationship": (relationship.name),
                    "reason": (
                        "Required 1:1 relationship "
                        "has more children than "
                        "parents."
                    ),
                }

            for index, record in enumerate(child_records):

                if index < len(parent_values):

                    record[relationship.child_key] = parent_values[index]

                else:

                    record[relationship.child_key] = None

        # --------------------------------------------------------------
        # 1:N / 0:N
        # --------------------------------------------------------------

        elif relationship.cardinality in {"1:N", "0:N"}:

            for index, record in enumerate(child_records):

                record[relationship.child_key] = parent_values[
                    index % len(parent_values)
                ]

        # --------------------------------------------------------------
        # N:M
        # --------------------------------------------------------------

        else:

            return {
                "status": "PASS",
                "relationship": (relationship.name),
                "mode": ("ASSOCIATIVE_ENTITY"),
            }

        # --------------------------------------------------------------
        # Validate references.
        # --------------------------------------------------------------

        parent_set = set(parent_values)

        references = [record.get(relationship.child_key) for record in child_records]

        invalid = [
            value
            for value in references
            if value is not None and value not in parent_set
        ]

        null_count = sum(value is None for value in references)

        if relationship.requirement == "REQUIRED" and null_count > 0:

            return {
                "status": "FAIL",
                "relationship": (relationship.name),
                "reason": ("Required relationship " "contains null references."),
            }

        if invalid:

            return {
                "status": "FAIL",
                "relationship": (relationship.name),
                "reason": ("Invalid foreign-key " "references detected."),
                "invalid": invalid,
            }

        return {
            "status": "PASS",
            "relationship": (relationship.name),
            "parent_count": len(parent_records),
            "child_count": len(child_records),
            "null_references": (null_count),
            "invalid_references": 0,
        }

    # ------------------------------------------------------------------------
    # Final validation
    # ------------------------------------------------------------------------

    def _validate_dataset(
        self,
        specification: GenerationSpecification,
        generated: dict[
            str,
            list[dict[str, Any]],
        ],
    ) -> dict[str, Any]:

        entity_results = {}

        for entity in specification.entities:

            records = generated[entity.name]

            structure_valid = len(records) == entity.record_count

            fields_valid = all(
                set(record.keys()) == {field.name for field in entity.fields}
                for record in records
            )

            entity_results[entity.name] = {
                "record_count": len(records),
                "expected_record_count": (entity.record_count),
                "structure_valid": (structure_valid),
                "fields_valid": (fields_valid),
                "status": ("PASS" if (structure_valid and fields_valid) else "FAIL"),
            }

        overall = all(result["status"] == "PASS" for result in entity_results.values())

        return {
            "status": ("PASS" if overall else "FAIL"),
            "entities": entity_results,
        }


# ============================================================================
# SPECIFICATION BUILDERS
# ============================================================================


def field(
    name: str,
    type_name: str,
    strategy: str,
    *,
    semantic: str | None = None,
    distribution: str | None = None,
    parameters: dict[str, Any] | None = None,
    nullable: bool = False,
    population_rate: float = 1.0,
) -> FieldSpecification:

    return FieldSpecification(
        name=name,
        type=type_name,
        strategy=strategy,
        semantic=semantic,
        distribution=distribution,
        parameters=parameters,
        nullable=nullable,
        population_rate=population_rate,
    )


def build_normal_specification(
    reverse_entity_order: bool = False,
) -> GenerationSpecification:

    customer = EntitySpecification(
        name="CUSTOMER",
        record_count=20,
        fields=(
            field(
                "CUSTOMER_ID",
                "IDENTIFIER",
                "SEQUENTIAL",
                semantic="PRIMARY_KEY",
                parameters={
                    "prefix": "CUS-",
                    "start": 1,
                },
            ),
            field(
                "CUSTOMER_TYPE",
                "CATEGORICAL",
                "RANDOM",
                distribution="CATEGORICAL",
                parameters={
                    "values": [
                        "STANDARD",
                        "PREMIUM",
                    ],
                    "weights": [
                        0.7,
                        0.3,
                    ],
                },
            ),
            field(
                "COUNTRY",
                "CATEGORICAL",
                "RANDOM",
                distribution="CATEGORICAL",
                parameters={
                    "values": [
                        "US",
                        "IN",
                        "DE",
                    ],
                },
            ),
            field(
                "CREDIT_LIMIT",
                "DECIMAL",
                "RANDOM",
                distribution="UNIFORM",
                parameters={
                    "min": 1000,
                    "max": 10000,
                },
            ),
        ),
    )

    customer_profile = EntitySpecification(
        name="CUSTOMER_PROFILE",
        record_count=20,
        fields=(
            field(
                "PROFILE_ID",
                "IDENTIFIER",
                "SEQUENTIAL",
                semantic="PRIMARY_KEY",
                parameters={
                    "prefix": "PRF-",
                    "start": 1,
                },
            ),
            field(
                "CUSTOMER_ID",
                "IDENTIFIER",
                "NULL",
                semantic="FOREIGN_KEY",
                nullable=True,
            ),
            field(
                "STATUS",
                "CATEGORICAL",
                "RANDOM",
                distribution="CATEGORICAL",
                parameters={
                    "values": [
                        "ACTIVE",
                        "INACTIVE",
                    ],
                },
            ),
        ),
    )

    product = EntitySpecification(
        name="PRODUCT",
        record_count=10,
        fields=(
            field(
                "PRODUCT_ID",
                "IDENTIFIER",
                "SEQUENTIAL",
                semantic="PRIMARY_KEY",
                parameters={
                    "prefix": "PRD-",
                    "start": 1,
                },
            ),
            field(
                "PRODUCT_TYPE",
                "CATEGORICAL",
                "RANDOM",
                distribution="CATEGORICAL",
                parameters={
                    "values": [
                        "STANDARD",
                        "SPECIAL",
                        "PREMIUM",
                    ],
                },
            ),
            field(
                "UNIT_PRICE",
                "DECIMAL",
                "RANDOM",
                distribution="UNIFORM",
                parameters={
                    "min": 10,
                    "max": 5000,
                },
            ),
        ),
    )

    order = EntitySpecification(
        name="ORDER",
        record_count=100,
        fields=(
            field(
                "ORDER_ID",
                "IDENTIFIER",
                "SEQUENTIAL",
                semantic="PRIMARY_KEY",
                parameters={
                    "prefix": "ORD-",
                    "start": 1,
                },
            ),
            field(
                "CUSTOMER_ID",
                "IDENTIFIER",
                "NULL",
                semantic="FOREIGN_KEY",
            ),
            field(
                "ORDER_AMOUNT",
                "DECIMAL",
                "RANDOM",
                distribution="UNIFORM",
                parameters={
                    "min": 100,
                    "max": 10000,
                },
            ),
            field(
                "STATUS",
                "ENUM",
                "RANDOM",
                distribution="CATEGORICAL",
                parameters={
                    "values": [
                        "NEW",
                        "PROCESSING",
                        "COMPLETE",
                    ],
                },
            ),
        ),
    )

    order_item = EntitySpecification(
        name="ORDER_ITEM",
        record_count=200,
        fields=(
            field(
                "ORDER_ITEM_ID",
                "IDENTIFIER",
                "SEQUENTIAL",
                semantic="PRIMARY_KEY",
                parameters={
                    "prefix": "ITM-",
                    "start": 1,
                },
            ),
            field(
                "ORDER_ID",
                "IDENTIFIER",
                "NULL",
                semantic="FOREIGN_KEY",
            ),
            field(
                "PRODUCT_ID",
                "IDENTIFIER",
                "NULL",
                semantic="FOREIGN_KEY",
            ),
            field(
                "QUANTITY",
                "INTEGER",
                "RANDOM",
                distribution="DISCRETE_UNIFORM",
                parameters={
                    "min": 1,
                    "max": 10,
                },
            ),
        ),
    )

    shipment = EntitySpecification(
        name="SHIPMENT",
        record_count=80,
        fields=(
            field(
                "SHIPMENT_ID",
                "IDENTIFIER",
                "SEQUENTIAL",
                semantic="PRIMARY_KEY",
                parameters={
                    "prefix": "SHP-",
                    "start": 1,
                },
            ),
            field(
                "ORDER_ID",
                "IDENTIFIER",
                "NULL",
                semantic="FOREIGN_KEY",
                nullable=True,
            ),
            field(
                "STATUS",
                "CATEGORICAL",
                "RANDOM",
                distribution="CATEGORICAL",
                parameters={
                    "values": [
                        "CREATED",
                        "IN_TRANSIT",
                        "DELIVERED",
                    ],
                },
            ),
        ),
    )

    entities = [
        customer,
        customer_profile,
        product,
        order,
        order_item,
        shipment,
    ]

    if reverse_entity_order:

        entities.reverse()

    relationships = (
        RelationshipSpecification(
            name="CUSTOMER_PROFILE",
            parent="CUSTOMER",
            child="CUSTOMER_PROFILE",
            parent_key="CUSTOMER_ID",
            child_key="CUSTOMER_ID",
            cardinality="0:1",
            requirement="OPTIONAL",
        ),
        RelationshipSpecification(
            name="CUSTOMER_ORDER",
            parent="CUSTOMER",
            child="ORDER",
            parent_key="CUSTOMER_ID",
            child_key="CUSTOMER_ID",
            cardinality="1:N",
            requirement="REQUIRED",
        ),
        RelationshipSpecification(
            name="ORDER_ORDER_ITEM",
            parent="ORDER",
            child="ORDER_ITEM",
            parent_key="ORDER_ID",
            child_key="ORDER_ID",
            cardinality="1:N",
            requirement="REQUIRED",
            associative=True,
        ),
        RelationshipSpecification(
            name="PRODUCT_ORDER_ITEM",
            parent="PRODUCT",
            child="ORDER_ITEM",
            parent_key="PRODUCT_ID",
            child_key="PRODUCT_ID",
            cardinality="1:N",
            requirement="REQUIRED",
            associative=True,
        ),
        RelationshipSpecification(
            name="ORDER_SHIPMENT",
            parent="ORDER",
            child="SHIPMENT",
            parent_key="ORDER_ID",
            child_key="ORDER_ID",
            cardinality="0:1",
            requirement="OPTIONAL",
        ),
    )

    return GenerationSpecification(
        entities=tuple(entities),
        relationships=relationships,
        seed=RANDOM_SEED,
    )


def build_blocked_specification() -> GenerationSpecification:

    normal = build_normal_specification()

    customer = normal.entities[0]

    blocked_customer = EntitySpecification(
        name=customer.name,
        record_count=customer.record_count,
        fields=(
            *customer.fields,
            field(
                "DERIVED_VALUE",
                "DECIMAL",
                "DERIVED",
            ),
        ),
    )

    entities = (
        blocked_customer,
        *normal.entities[1:],
    )

    return GenerationSpecification(
        entities=tuple(entities),
        relationships=normal.relationships,
        seed=RANDOM_SEED,
    )


# ============================================================================
# TEST 1: COMPLETE GENERATION
# ============================================================================


def test_complete_generation() -> dict[str, Any]:

    specification = build_normal_specification()

    result = DeclarativeExecutionEngine(seed=specification.seed).execute(specification)

    passed = (
        result["status"] == "PASS"
        and result["phase"] == "COMPLETED"
        and result["validation"]["status"] == "PASS"
    )

    return {
        "status": ("PASS" if passed else "FAIL"),
        "execution_order": result.get("execution_order"),
        "validation": result.get("validation"),
    }


# ============================================================================
# TEST 2: RELATIONSHIPS
# ============================================================================


def test_relationships() -> dict[str, Any]:

    specification = build_normal_specification()

    result = DeclarativeExecutionEngine(seed=specification.seed).execute(specification)

    relationship_results = result.get(
        "relationships",
        [],
    )

    passed = result["status"] == "PASS" and all(
        item["status"] == "PASS" for item in relationship_results
    )

    return {
        "status": ("PASS" if passed else "FAIL"),
        "relationships": (relationship_results),
    }


# ============================================================================
# TEST 3: ENTITY ORDER INDEPENDENCE
# ============================================================================


def test_entity_order_independence() -> dict[str, Any]:

    first_spec = build_normal_specification(reverse_entity_order=False)

    second_spec = build_normal_specification(reverse_entity_order=True)

    engine_a = DeclarativeExecutionEngine(seed=RANDOM_SEED)

    engine_b = DeclarativeExecutionEngine(seed=RANDOM_SEED)

    first = engine_a.execute(first_spec)

    second = engine_b.execute(second_spec)

    first_clean = {key: value for key, value in first["entities"].items()}

    second_clean = {key: value for key, value in second["entities"].items()}

    passed = (
        first["execution_order"] == second["execution_order"]
        and first_clean == second_clean
    )

    return {
        "status": ("PASS" if passed else "FAIL"),
        "execution_order_a": (first.get("execution_order")),
        "execution_order_b": (second.get("execution_order")),
    }


# ============================================================================
# TEST 4: REPRODUCIBILITY
# ============================================================================


def test_reproducibility() -> dict[str, Any]:

    specification = build_normal_specification()

    engine_a = DeclarativeExecutionEngine(seed=RANDOM_SEED)

    engine_b = DeclarativeExecutionEngine(seed=RANDOM_SEED)

    first = engine_a.execute(specification)

    second = engine_b.execute(specification)

    passed = first["entities"] == second["entities"]

    return {
        "status": ("PASS" if passed else "FAIL"),
        "identical": passed,
    }


# ============================================================================
# TEST 5: DIFFERENT SEED
# ============================================================================


def test_seed_sensitivity() -> dict[str, Any]:

    specification_a = build_normal_specification()

    specification_b = GenerationSpecification(
        entities=(specification_a.entities),
        relationships=(specification_a.relationships),
        seed=99,
    )

    first = DeclarativeExecutionEngine(seed=42).execute(specification_a)

    second = DeclarativeExecutionEngine(seed=99).execute(specification_b)

    changed = first["entities"] != second["entities"]

    passed = changed and first["status"] == "PASS" and second["status"] == "PASS"

    return {
        "status": ("PASS" if passed else "FAIL"),
        "different_seed_changes_data": (changed),
    }


# ============================================================================
# TEST 6: SAFE BLOCKING
# ============================================================================


def test_safe_capability_blocking() -> dict[str, Any]:

    specification = build_blocked_specification()

    result = DeclarativeExecutionEngine(seed=specification.seed).execute(specification)

    deferred = result.get("capability", {}).get("deferred", [])

    derived_detected = any(item.get("value") == "DERIVED" for item in deferred)

    passed = (
        result["status"] == "BLOCKED"
        and result["phase"] == "CAPABILITY_ASSESSMENT"
        and derived_detected
    )

    return {
        "status": ("PASS" if passed else "FAIL"),
        "execution_blocked": (result["status"] == "BLOCKED"),
        "deferred_capabilities": (deferred),
    }


# ============================================================================
# TEST 7: NO BUSINESS-SPECIFIC BRANCHING
# ============================================================================


def test_entity_agnostic_execution() -> dict[str, Any]:

    first = EntitySpecification(
        name="ALPHA",
        record_count=10,
        fields=(
            field(
                "ALPHA_ID",
                "IDENTIFIER",
                "SEQUENTIAL",
                semantic="PRIMARY_KEY",
                parameters={
                    "prefix": "A-",
                    "start": 1,
                },
            ),
            field(
                "CATEGORY",
                "CATEGORICAL",
                "RANDOM",
                distribution="CATEGORICAL",
                parameters={
                    "values": [
                        "X",
                        "Y",
                    ]
                },
            ),
        ),
    )

    second = EntitySpecification(
        name="BETA",
        record_count=10,
        fields=(
            field(
                "BETA_ID",
                "IDENTIFIER",
                "SEQUENTIAL",
                semantic="PRIMARY_KEY",
                parameters={
                    "prefix": "B-",
                    "start": 1,
                },
            ),
            field(
                "CATEGORY",
                "CATEGORICAL",
                "RANDOM",
                distribution="CATEGORICAL",
                parameters={
                    "values": [
                        "M",
                        "N",
                    ]
                },
            ),
        ),
    )

    specification = GenerationSpecification(
        entities=(
            first,
            second,
        ),
        relationships=(),
        seed=RANDOM_SEED,
    )

    result = DeclarativeExecutionEngine(seed=RANDOM_SEED).execute(specification)

    passed = result["status"] == "PASS" and set(result["entities"].keys()) == {
        "ALPHA",
        "BETA",
    }

    return {
        "status": ("PASS" if passed else "FAIL"),
        "entities": list(result["entities"].keys()),
    }


# ============================================================================
# TEST 8: FINAL DATASET QUALITY
# ============================================================================


def test_final_dataset_quality() -> dict[str, Any]:

    specification = build_normal_specification()

    result = DeclarativeExecutionEngine(seed=specification.seed).execute(specification)

    checks = []

    for entity_name, records in result["entities"].items():

        checks.append(len(records) > 0)

        checks.append(all(record for record in records))

    passed = all(checks)

    return {
        "status": ("PASS" if passed else "FAIL"),
        "entity_counts": {
            name: len(records) for name, records in result["entities"].items()
        },
    }


# ============================================================================
# MAIN
# ============================================================================


def main() -> int:

    print()

    print("=" * 70)

    print("FORGE - Experiment 020-J: " "End-to-End Declarative Generation")

    print("=" * 70)

    print("Experiment:     " "020_declarative_generation_specification")

    print("Stage:          020-J")

    print("Purpose:        " "End-to-end declarative execution")

    print(f"Random seed:    {RANDOM_SEED}")

    print()

    print("Execution pipeline:")

    print("  Specification")

    print("       ↓")

    print("  Capability assessment")

    print("       ↓")

    print("  Dependency planning")

    print("       ↓")

    print("  Field generation")

    print("       ↓")

    print("  Identity generation")

    print("       ↓")

    print("  Relationship resolution")

    print("       ↓")

    print("  Final validation")

    print()

    tests = {
        "complete_generation": (test_complete_generation()),
        "relationships": (test_relationships()),
        "entity_order_independence": (test_entity_order_independence()),
        "reproducibility": (test_reproducibility()),
        "seed_sensitivity": (test_seed_sensitivity()),
        "safe_capability_blocking": (test_safe_capability_blocking()),
        "entity_agnostic_execution": (test_entity_agnostic_execution()),
        "final_dataset_quality": (test_final_dataset_quality()),
    }

    labels = {
        "complete_generation": "Complete generation",
        "relationships": "Relationship resolution",
        "entity_order_independence": "Entity-order independence",
        "reproducibility": "Reproducibility",
        "seed_sensitivity": "Seed sensitivity",
        "safe_capability_blocking": "Safe capability blocking",
        "entity_agnostic_execution": "Entity-agnostic execution",
        "final_dataset_quality": "Final dataset quality",
    }

    print("End-to-end validation:")

    for key, result in tests.items():

        print(f"  " f"{labels[key]:<34}" f"{result['status']}")

    print()

    passed_count = sum(result["status"] == "PASS" for result in tests.values())

    total_count = len(tests)

    overall = passed_count == total_count

    print("Experiment result:")

    print(f"  Complete generation:       " f"{tests['complete_generation']['status']}")

    print(f"  Relationships:              " f"{tests['relationships']['status']}")

    print(f"  Determinism:               " f"{tests['reproducibility']['status']}")

    print(
        f"  Entity-order independence: "
        f"{tests['entity_order_independence']['status']}"
    )

    print(
        f"  Capability safety:         "
        f"{tests['safe_capability_blocking']['status']}"
    )

    print(
        f"  Entity agnosticism:        "
        f"{tests['entity_agnostic_execution']['status']}"
    )

    print(f"  Tests passed:              " f"{passed_count}/{total_count}")

    print(f"  Overall:                   " f"{'PASS' if overall else 'FAIL'}")

    # ------------------------------------------------------------------------
    # Produce representative dataset
    # ------------------------------------------------------------------------

    specification = build_normal_specification()

    execution = DeclarativeExecutionEngine(seed=specification.seed).execute(
        specification
    )

    # ------------------------------------------------------------------------
    # Output
    # ------------------------------------------------------------------------

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    payload = {
        "experiment": ("020_declarative_generation_specification"),
        "stage": "020-J",
        "purpose": ("End-to-end declarative " "generation"),
        "seed": RANDOM_SEED,
        "tests": tests,
        "tests_passed": passed_count,
        "tests_total": total_count,
        "execution_order": execution.get("execution_order"),
        "dataset_counts": {
            entity: len(records)
            for entity, records in execution.get(
                "entities",
                {},
            ).items()
        },
        "architectural_conclusion": (
            "The foundational FORGE "
            "capabilities established in "
            "020-A through 020-I can be "
            "composed into a generic "
            "declarative execution pipeline. "
            "The runtime validates "
            "capabilities before execution, "
            "derives generation order from "
            "relationships, generates fields "
            "and identities, resolves "
            "references, and validates the "
            "resulting dataset."
        ),
        "important_boundary": (
            "This experiment does not "
            "implement statistical correlation, "
            "advanced constraints, scenarios, "
            "provenance, or LLM specification "
            "translation."
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
