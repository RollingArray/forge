"""
FORGE - Experiment 020-T: Declarative Generation Provenance
============================================================

Experiment:
    020_declarative_generation_specification

Stage:
    020-T

Purpose:
    Validate deterministic, inspectable provenance for generated values.

Core hypothesis:

    Every generated value can be traced back to:

        - declarative specification
        - generation mechanism
        - dependencies
        - record context
        - applicable constraints / conditions
        - statistical relationships
        - scenario
        - deterministic seed namespace

The provenance layer is deliberately kept separate from the generated
dataset. The dataset remains clean while provenance provides an inspectable
lineage graph.

Architecture:

    Specification
          |
          v
    Generation Planning
          |
          v
    Generation
          |
          +--------------------+
          |                    |
          v                    v
      Dataset             Provenance DAG
                               |
                               v
                         Explanation
                               |
                               v
                    Independent Validation

Important invariants:

    1. Provenance must not change generated values.
    2. Provenance must be deterministic.
    3. Provenance must survive field/entity reordering.
    4. Every generated field must have provenance.
    5. Every provenance dependency must resolve.
    6. Provenance must agree with the actual dataset.
    7. Derived lineage must be recursively explainable.
    8. Statistical lineage must identify its source.
    9. Relationship lineage must identify its parent.
    10. Broken or mutated provenance must be detectable.
"""

from __future__ import annotations

import copy
import hashlib
import json
import math
import random
import sys
from dataclasses import dataclass, asdict
from pathlib import Path
from statistics import mean
from typing import Any

# ============================================================================
# PATHS
# ============================================================================

EXPERIMENT_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = EXPERIMENT_DIR / "output"

DATASET_PATH = OUTPUT_DIR / "provenance_dataset.json"

PROVENANCE_PATH = OUTPUT_DIR / "provenance.json"

RESULTS_PATH = OUTPUT_DIR / "provenance_results.json"

MASTER_SEED = 42


# ============================================================================
# DECLARATIVE MODELS
# ============================================================================


@dataclass(frozen=True)
class Field:
    name: str
    minimum: float | None = None
    maximum: float | None = None
    constant: float | None = None


@dataclass(frozen=True)
class Entity:
    name: str
    fields: tuple[Field, ...]
    record_count: int


@dataclass(frozen=True)
class Correlation:
    name: str
    source_entity: str
    source_field: str
    target_entity: str
    target_field: str
    target_value: float


@dataclass(frozen=True)
class Relationship:
    name: str
    parent_entity: str
    parent_field: str
    child_entity: str
    child_field: str


@dataclass(frozen=True)
class Constraint:
    name: str
    entity: str
    left: str
    operator: str
    right: str


@dataclass(frozen=True)
class Conditional:
    name: str
    entity: str
    condition_field: str
    condition_minimum: float
    target_field: str
    target_minimum: float


@dataclass(frozen=True)
class Derived:
    name: str
    entity: str
    source_a: str
    source_b: str
    operation: str


@dataclass(frozen=True)
class Scenario:
    name: str


@dataclass(frozen=True)
class Specification:
    entities: tuple[Entity, ...]
    relationships: tuple[Relationship, ...]
    correlations: tuple[Correlation, ...]
    constraints: tuple[Constraint, ...]
    conditionals: tuple[Conditional, ...]
    derived: tuple[Derived, ...]
    scenarios: tuple[Scenario, ...]


# ============================================================================
# DETERMINISTIC STREAMS
# ============================================================================


def stable_seed(
    seed: int,
    namespace: str,
) -> int:

    digest = hashlib.sha256(f"{seed}:{namespace}".encode()).digest()

    return int.from_bytes(
        digest[:8],
        byteorder="big",
        signed=False,
    )


def rng_for(
    seed: int,
    namespace: str,
) -> random.Random:

    return random.Random(
        stable_seed(
            seed,
            namespace,
        )
    )


# ============================================================================
# SPECIFICATION HELPERS
# ============================================================================


def entity_map(
    specification: Specification,
) -> dict[str, Entity]:

    return {entity.name: entity for entity in specification.entities}


def field_map(
    specification: Specification,
) -> dict[str, dict[str, Field]]:

    return {
        entity.name: {field.name: field for field in entity.fields}
        for entity in specification.entities
    }


# ============================================================================
# SPECIFICATION VALIDATION
# ============================================================================


def validate_specification(
    specification: Specification,
) -> None:

    entities = entity_map(specification)

    fields = field_map(specification)

    if len(entities) != len(specification.entities):
        raise ValueError("Duplicate entity.")

    for entity in specification.entities:

        if entity.record_count <= 0:
            raise ValueError(f"Invalid record count: " f"{entity.name}")

        names = {field.name for field in entity.fields}

        if len(names) != len(entity.fields):
            raise ValueError(f"Duplicate field: " f"{entity.name}")

        for field in entity.fields:

            if (
                field.minimum is not None
                and field.maximum is not None
                and field.minimum > field.maximum
            ):
                raise ValueError(
                    f"Invalid field bounds: " f"{entity.name}.{field.name}"
                )

    for relationship in specification.relationships:

        if relationship.parent_entity not in entities:
            raise ValueError("Unknown relationship parent.")

        if relationship.child_entity not in entities:
            raise ValueError("Unknown relationship child.")

        if relationship.parent_field not in fields[relationship.parent_entity]:
            raise ValueError("Unknown relationship parent field.")

        if relationship.child_field not in fields[relationship.child_entity]:
            raise ValueError("Unknown relationship child field.")

    for correlation in specification.correlations:

        if correlation.source_entity not in entities:
            raise ValueError("Unknown correlation source.")

        if correlation.target_entity not in entities:
            raise ValueError("Unknown correlation target.")

        if correlation.source_field not in fields[correlation.source_entity]:
            raise ValueError("Unknown correlation source field.")

        if correlation.target_field not in fields[correlation.target_entity]:
            raise ValueError("Unknown correlation target field.")

        if not (-1.0 <= correlation.target_value <= 1.0):
            raise ValueError("Correlation must be between -1 and 1.")

    for constraint in specification.constraints:

        if constraint.entity not in entities:
            raise ValueError("Unknown constraint entity.")

        if constraint.left not in fields[constraint.entity]:
            raise ValueError("Unknown constraint left field.")

        if constraint.right not in fields[constraint.entity]:
            raise ValueError("Unknown constraint right field.")

    for conditional in specification.conditionals:

        if conditional.entity not in entities:
            raise ValueError("Unknown conditional entity.")

        if conditional.condition_field not in fields[conditional.entity]:
            raise ValueError("Unknown conditional field.")

        if conditional.target_field not in fields[conditional.entity]:
            raise ValueError("Unknown conditional target field.")

    for derived in specification.derived:

        if derived.entity not in entities:
            raise ValueError("Unknown derived entity.")

        if derived.source_a not in fields[derived.entity]:
            raise ValueError("Unknown derived source.")

        if derived.source_b not in fields[derived.entity]:
            raise ValueError("Unknown derived source.")


# ============================================================================
# FIELD DEPENDENCY PLAN
# ============================================================================


def field_plan(
    specification: Specification,
    entity_name: str,
) -> list[str]:

    fields = field_map(specification)[entity_name]

    dependencies = {name: set() for name in fields}

    for correlation in specification.correlations:

        if (
            correlation.target_entity == entity_name
            and correlation.source_entity == entity_name
        ):

            dependencies[correlation.target_field].add(correlation.source_field)

    for conditional in specification.conditionals:

        if conditional.entity == entity_name:

            dependencies[conditional.target_field].add(conditional.condition_field)

    for derived in specification.derived:

        if derived.entity == entity_name:

            dependencies[derived.name] = {
                derived.source_a,
                derived.source_b,
            }

    for constraint in specification.constraints:

        if constraint.entity == entity_name:

            dependencies[constraint.left].add(constraint.right)

    remaining = {key: set(value) for key, value in dependencies.items()}

    plan = []

    while remaining:

        ready = sorted(name for name, deps in remaining.items() if not deps)

        if not ready:
            raise ValueError(f"Field dependency cycle " f"in {entity_name}")

        plan.extend(ready)

        for name in ready:
            del remaining[name]

        for deps in remaining.values():
            deps.difference_update(ready)

    return plan


# ============================================================================
# CORRELATED VALUES
# ============================================================================


def generate_correlated(
    source: list[float],
    target: Field,
    correlation: Correlation,
    seed: int,
) -> list[float]:

    if target.minimum is None or target.maximum is None:
        raise ValueError("Correlated field requires bounds.")

    source_mean = mean(source)

    centered = [value - source_mean for value in source]

    variance = mean(value * value for value in centered)

    if math.isclose(
        variance,
        0.0,
    ):
        raise ValueError("Correlation source has zero variance.")

    source_std = math.sqrt(variance)

    normalized = [value / source_std for value in centered]

    rng = rng_for(
        seed,
        f"CORRELATION:{correlation.name}",
    )

    noise = [
        rng.gauss(
            0.0,
            1.0,
        )
        for _ in source
    ]

    rho = correlation.target_value

    residual = math.sqrt(
        max(
            0.0,
            1.0 - rho * rho,
        )
    )

    latent = [
        rho * x + residual * n
        for x, n in zip(
            normalized,
            noise,
        )
    ]

    low = min(latent)

    high = max(latent)

    if math.isclose(
        low,
        high,
    ):

        normalized_target = [0.5 for _ in latent]

    else:

        normalized_target = [(value - low) / (high - low) for value in latent]

    return [
        target.minimum + normalized_value * (target.maximum - target.minimum)
        for normalized_value in normalized_target
    ]


# ============================================================================
# PROVENANCE BUILDER
# ============================================================================


def provenance_node(
    *,
    entity: str,
    record_index: int,
    field: str,
    value: Any,
    generation_type: str,
    specification_reference: str,
    seed: int,
    dependencies: list[dict[str, Any]] | None = None,
    rule: dict[str, Any] | None = None,
    context: dict[str, Any] | None = None,
) -> dict[str, Any]:

    node = {
        "entity": entity,
        "record_index": record_index,
        "field": field,
        "value": value,
        "generation_type": generation_type,
        "specification_reference": (specification_reference),
        "seed": seed,
        "seed_namespace": (f"FIELD:{entity}:{field}"),
        "dependencies": (dependencies or []),
        "rule": rule,
        "context": context or {},
    }

    canonical = json.dumps(
        node,
        sort_keys=True,
        default=str,
    )

    node["provenance_id"] = hashlib.sha256(canonical.encode()).hexdigest()

    return node


# ============================================================================
# GENERATION
# ============================================================================


def generate_dataset_with_provenance(
    specification: Specification,
    scenario_name: str,
    seed: int,
) -> tuple[
    dict[str, list[dict[str, Any]]],
    dict[str, list[dict[str, Any]]],
]:

    validate_specification(specification)

    entities = entity_map(specification)

    fields = field_map(specification)

    datasets: dict[
        str,
        list[dict[str, Any]],
    ] = {}

    provenance: dict[
        str,
        list[dict[str, Any]],
    ] = {}

    # ------------------------------------------------------------------
    # Entity order is derived from relationships.
    # ------------------------------------------------------------------

    entity_dependencies = {entity.name: set() for entity in specification.entities}

    for relationship in specification.relationships:

        entity_dependencies[relationship.child_entity].add(relationship.parent_entity)

    remaining = {key: set(value) for key, value in entity_dependencies.items()}

    entity_order = []

    while remaining:

        ready = sorted(name for name, deps in remaining.items() if not deps)

        if not ready:
            raise ValueError("Entity dependency cycle.")

        entity_order.extend(ready)

        for name in ready:
            del remaining[name]

        for deps in remaining.values():
            deps.difference_update(ready)

    # ------------------------------------------------------------------
    # Generation.
    # ------------------------------------------------------------------

    for entity_name in entity_order:

        entity = entities[entity_name]

        datasets[entity_name] = [{} for _ in range(entity.record_count)]

        provenance[entity_name] = []

        plan = field_plan(
            specification,
            entity_name,
        )

        for field_name in plan:

            field = fields[entity_name][field_name]

            # ----------------------------------------------------------
            # DERIVED
            # ----------------------------------------------------------

            derived = next(
                (
                    item
                    for item in specification.derived
                    if (item.entity == entity_name and item.name == field_name)
                ),
                None,
            )

            if derived is not None:

                for index, record in enumerate(datasets[entity_name]):

                    a = record[derived.source_a]

                    b = record[derived.source_b]

                    if derived.operation == "ADD":

                        value = a + b

                    elif derived.operation == "SUBTRACT":

                        value = a - b

                    elif derived.operation == "MULTIPLY":

                        value = a * b

                    else:

                        raise ValueError("Unsupported derived operation.")

                    record[field_name] = value

                    dependencies = [
                        {
                            "entity": entity_name,
                            "record_index": index,
                            "field": derived.source_a,
                            "value": a,
                        },
                        {
                            "entity": entity_name,
                            "record_index": index,
                            "field": derived.source_b,
                            "value": b,
                        },
                    ]

                    provenance[entity_name].append(
                        provenance_node(
                            entity=entity_name,
                            record_index=index,
                            field=field_name,
                            value=value,
                            generation_type="DERIVED",
                            specification_reference=(f"DERIVED:{derived.name}"),
                            seed=seed,
                            dependencies=dependencies,
                            rule={
                                "name": derived.name,
                                "operation": (derived.operation),
                                "expression": (
                                    f"{derived.source_a} "
                                    f"{derived.operation} "
                                    f"{derived.source_b}"
                                ),
                            },
                        )
                    )

                continue

            # ----------------------------------------------------------
            # CORRELATED
            # ----------------------------------------------------------

            correlation = next(
                (
                    item
                    for item in specification.correlations
                    if (
                        item.target_entity == entity_name
                        and item.target_field == field_name
                    )
                ),
                None,
            )

            if correlation is not None:

                if correlation.source_entity == entity_name:

                    source_values = [
                        record[correlation.source_field]
                        for record in datasets[entity_name]
                    ]

                else:

                    if correlation.source_entity not in datasets:
                        raise ValueError("Correlation source " "not generated.")

                    source_values = [
                        record[correlation.source_field]
                        for record in datasets[correlation.source_entity]
                    ]

                values = generate_correlated(
                    source_values,
                    field,
                    correlation,
                    seed,
                )

                for index, value in enumerate(values):

                    datasets[entity_name][index][field_name] = value

                    source_index = index % len(source_values)

                    provenance[entity_name].append(
                        provenance_node(
                            entity=entity_name,
                            record_index=index,
                            field=field_name,
                            value=value,
                            generation_type=("STATISTICAL"),
                            specification_reference=(
                                f"CORRELATION:" f"{correlation.name}"
                            ),
                            seed=seed,
                            dependencies=[
                                {
                                    "entity": (correlation.source_entity),
                                    "record_index": (source_index),
                                    "field": (correlation.source_field),
                                    "value": (source_values[source_index]),
                                }
                            ],
                            rule={
                                "name": (correlation.name),
                                "target_correlation": (correlation.target_value),
                                "method": "PEARSON",
                            },
                        )
                    )

                continue

            # ----------------------------------------------------------
            # RELATIONSHIP
            # ----------------------------------------------------------

            relationship = next(
                (
                    item
                    for item in specification.relationships
                    if (
                        item.child_entity == entity_name
                        and item.child_field == field_name
                    )
                ),
                None,
            )

            if relationship is not None:

                parent_records = datasets[relationship.parent_entity]

                for index, record in enumerate(datasets[entity_name]):

                    parent_index = index % len(parent_records)

                    value = parent_records[parent_index][relationship.parent_field]

                    record[field_name] = value

                    provenance[entity_name].append(
                        provenance_node(
                            entity=entity_name,
                            record_index=index,
                            field=field_name,
                            value=value,
                            generation_type=("REFERENCE"),
                            specification_reference=(
                                f"RELATIONSHIP:" f"{relationship.name}"
                            ),
                            seed=seed,
                            dependencies=[
                                {
                                    "entity": (relationship.parent_entity),
                                    "record_index": (parent_index),
                                    "field": (relationship.parent_field),
                                    "value": value,
                                }
                            ],
                            rule={
                                "name": (relationship.name),
                                "cardinality": "1:N",
                            },
                        )
                    )

                continue

            # ----------------------------------------------------------
            # ROOT / CONDITIONAL
            # ----------------------------------------------------------

            rng = rng_for(
                seed,
                f"FIELD:{entity_name}:{field_name}",
            )

            conditional = next(
                (
                    item
                    for item in specification.conditionals
                    if (item.entity == entity_name and item.target_field == field_name)
                ),
                None,
            )

            for index, record in enumerate(datasets[entity_name]):

                lower = field.minimum if field.minimum is not None else 0.0

                upper = field.maximum if field.maximum is not None else 1.0

                context = {}

                if conditional is not None:

                    condition_value = record.get(conditional.condition_field)

                    if (
                        condition_value is not None
                        and condition_value >= conditional.condition_minimum
                    ):

                        lower = max(
                            lower,
                            conditional.target_minimum,
                        )

                        context = {
                            "condition_field": (conditional.condition_field),
                            "condition_value": (condition_value),
                            "condition": (
                                f"{conditional.condition_field}"
                                f" >= "
                                f"{conditional.condition_minimum}"
                            ),
                            "condition_result": True,
                        }

                if field.constant is not None:

                    value = field.constant

                    generation_type = "CONSTANT"

                    rule = {
                        "type": "CONSTANT",
                        "value": field.constant,
                    }

                else:

                    value = rng.uniform(
                        lower,
                        upper,
                    )

                    generation_type = (
                        "CONDITIONAL" if conditional is not None else "RANDOM"
                    )

                    rule = {
                        "distribution": "UNIFORM",
                        "minimum": lower,
                        "maximum": upper,
                    }

                record[field_name] = value

                dependencies = []

                if conditional is not None:

                    dependencies.append(
                        {
                            "entity": entity_name,
                            "record_index": index,
                            "field": (conditional.condition_field),
                            "value": (record.get(conditional.condition_field)),
                        }
                    )

                provenance[entity_name].append(
                    provenance_node(
                        entity=entity_name,
                        record_index=index,
                        field=field_name,
                        value=value,
                        generation_type=(generation_type),
                        specification_reference=(
                            f"FIELD:" f"{entity_name}." f"{field_name}"
                        ),
                        seed=seed,
                        dependencies=dependencies,
                        rule=rule,
                        context=context,
                    )
                )

    return (
        datasets,
        provenance,
    )


# ============================================================================
# PROVENANCE INDEX
# ============================================================================


def provenance_index(
    provenance: dict[
        str,
        list[dict[str, Any]],
    ],
) -> dict[
    tuple[str, int, str],
    dict[str, Any],
]:

    return {
        (
            node["entity"],
            node["record_index"],
            node["field"],
        ): node
        for nodes in provenance.values()
        for node in nodes
    }


# ============================================================================
# PROVENANCE VALIDATION
# ============================================================================


def validate_provenance_completeness(
    specification: Specification,
    datasets: dict[str, list[dict[str, Any]]],
    provenance: dict[str, list[dict[str, Any]]],
) -> bool:

    index = provenance_index(provenance)

    for entity in specification.entities:

        for record_index, record in enumerate(datasets[entity.name]):

            for field_name in record:

                key = (
                    entity.name,
                    record_index,
                    field_name,
                )

                if key not in index:
                    return False

    return True


def validate_provenance_dataset_consistency(
    datasets: dict[str, list[dict[str, Any]]],
    provenance: dict[str, list[dict[str, Any]]],
) -> bool:

    index = provenance_index(provenance)

    for entity_name, records in datasets.items():

        for record_index, record in enumerate(records):

            for field_name, value in record.items():

                node = index.get(
                    (
                        entity_name,
                        record_index,
                        field_name,
                    )
                )

                if node is None:
                    return False

                if node["value"] != value:

                    if not math.isclose(
                        float(node["value"]),
                        float(value),
                        rel_tol=1e-9,
                        abs_tol=1e-9,
                    ):
                        return False

    return True


def validate_provenance_dependencies(
    datasets: dict[str, list[dict[str, Any]]],
    provenance: dict[str, list[dict[str, Any]]],
) -> bool:

    index = provenance_index(provenance)

    for nodes in provenance.values():

        for node in nodes:

            for dependency in node["dependencies"]:

                key = (
                    dependency["entity"],
                    dependency["record_index"],
                    dependency["field"],
                )

                dependency_node = index.get(key)

                if dependency_node is None:
                    return False

                if dependency_node["value"] != dependency["value"]:

                    if not math.isclose(
                        float(dependency_node["value"]),
                        float(dependency["value"]),
                        rel_tol=1e-9,
                        abs_tol=1e-9,
                    ):
                        return False

    return True


def validate_derived_lineage(
    specification: Specification,
    datasets: dict[str, list[dict[str, Any]]],
    provenance: dict[str, list[dict[str, Any]]],
) -> bool:

    index = provenance_index(provenance)

    for derived in specification.derived:

        for record_index, record in enumerate(datasets[derived.entity]):

            node = index[
                (
                    derived.entity,
                    record_index,
                    derived.name,
                )
            ]

            if node["generation_type"] != "DERIVED":
                return False

            if len(node["dependencies"]) != 2:
                return False

            a = record[derived.source_a]

            b = record[derived.source_b]

            if derived.operation == "ADD":

                expected = a + b

            elif derived.operation == "SUBTRACT":

                expected = a - b

            elif derived.operation == "MULTIPLY":

                expected = a * b

            else:
                return False

            if not math.isclose(
                record[derived.name],
                expected,
                rel_tol=1e-9,
                abs_tol=1e-9,
            ):
                return False

            if node["value"] != record[derived.name]:
                return False

    return True


def validate_relationship_lineage(
    specification: Specification,
    provenance: dict[str, list[dict[str, Any]]],
) -> bool:

    for relationship in specification.relationships:

        nodes = provenance[relationship.child_entity]

        relevant = [
            node for node in nodes if (node["field"] == relationship.child_field)
        ]

        if not relevant:
            return False

        for node in relevant:

            if node["generation_type"] != "REFERENCE":
                return False

            if not node["dependencies"]:
                return False

            dependency = node["dependencies"][0]

            if dependency["entity"] != relationship.parent_entity:
                return False

            if dependency["field"] != relationship.parent_field:
                return False

    return True


def validate_statistical_lineage(
    specification: Specification,
    provenance: dict[str, list[dict[str, Any]]],
) -> bool:

    for correlation in specification.correlations:

        nodes = provenance[correlation.target_entity]

        relevant = [
            node for node in nodes if (node["field"] == correlation.target_field)
        ]

        if not relevant:
            return False

        for node in relevant:

            if node["generation_type"] != "STATISTICAL":
                return False

            if not node["dependencies"]:
                return False

            dependency = node["dependencies"][0]

            if dependency["entity"] != correlation.source_entity:
                return False

            if dependency["field"] != correlation.source_field:
                return False

            if node["rule"]["target_correlation"] != correlation.target_value:
                return False

    return True


# ============================================================================
# PROVENANCE DETERMINISM
# ============================================================================


def canonicalize_provenance(
    provenance: dict[str, list[dict[str, Any]]],
) -> str:

    return json.dumps(
        provenance,
        sort_keys=True,
        default=str,
        separators=(",", ":"),
    )


def provenance_fingerprint(
    provenance: dict[str, list[dict[str, Any]]],
) -> str:

    canonical = canonicalize_provenance(provenance)

    return hashlib.sha256(canonical.encode()).hexdigest()


# ============================================================================
# MUTATION TESTS
# ============================================================================


def mutate_provenance_value(
    provenance: dict[str, list[dict[str, Any]]],
) -> dict[str, list[dict[str, Any]]]:

    mutated = copy.deepcopy(provenance)

    first_entity = next(iter(mutated))

    mutated[first_entity][0]["value"] = float(mutated[first_entity][0]["value"]) + 1.0

    return mutated


def mutate_provenance_reference(
    provenance: dict[str, list[dict[str, Any]]],
) -> dict[str, list[dict[str, Any]]]:

    mutated = copy.deepcopy(provenance)

    for nodes in mutated.values():

        for node in nodes:

            if node["dependencies"]:

                node["dependencies"][0]["field"] = "UNKNOWN_FIELD"

                return mutated

    raise ValueError("No provenance dependency available to mutate.")


# ============================================================================
# CAPSTONE SPECIFICATION
# ============================================================================


def build_specification() -> Specification:

    customer = Entity(
        name="CUSTOMER",
        fields=(
            Field(
                "CUSTOMER_SCORE",
                0.0,
                100.0,
            ),
            Field(
                "CUSTOMER_VALUE",
                1000.0,
                10000.0,
            ),
        ),
        record_count=100,
    )

    product = Entity(
        name="PRODUCT",
        fields=(
            Field(
                "PRODUCT_SCORE",
                0.0,
                100.0,
            ),
            Field(
                "UNIT_PRICE",
                100.0,
                5000.0,
            ),
        ),
        record_count=50,
    )

    order = Entity(
        name="ORDER",
        fields=(
            Field(
                "ORDER_VALUE",
                1000.0,
                20000.0,
            ),
            Field(
                "DISCOUNT",
                0.0,
                30.0,
            ),
            Field(
                "NET_ORDER_VALUE",
                0.0,
                20000.0,
            ),
            Field(
                "CUSTOMER_VALUE",
                1000.0,
                10000.0,
            ),
        ),
        record_count=200,
    )

    relationships = (
        Relationship(
            name="ORDER_CUSTOMER_VALUE",
            parent_entity="CUSTOMER",
            parent_field="CUSTOMER_VALUE",
            child_entity="ORDER",
            child_field="CUSTOMER_VALUE",
        ),
    )

    correlations = (
        Correlation(
            name="CUSTOMER_SCORE_VALUE",
            source_entity="CUSTOMER",
            source_field="CUSTOMER_SCORE",
            target_entity="CUSTOMER",
            target_field="CUSTOMER_VALUE",
            target_value=0.60,
        ),
        Correlation(
            name="PRODUCT_SCORE_PRICE",
            source_entity="PRODUCT",
            source_field="PRODUCT_SCORE",
            target_entity="PRODUCT",
            target_field="UNIT_PRICE",
            target_value=0.50,
        ),
    )

    constraints = (
        Constraint(
            name="ORDER_ABOVE_CUSTOMER",
            entity="ORDER",
            left="ORDER_VALUE",
            operator=">=",
            right="CUSTOMER_VALUE",
        ),
    )

    conditionals = (
        Conditional(
            name="HIGH_VALUE_DISCOUNT",
            entity="ORDER",
            condition_field="ORDER_VALUE",
            condition_minimum=10000.0,
            target_field="DISCOUNT",
            target_minimum=5.0,
        ),
    )

    derived = (
        Derived(
            name="NET_ORDER_VALUE",
            entity="ORDER",
            source_a="ORDER_VALUE",
            source_b="DISCOUNT",
            operation="SUBTRACT",
        ),
    )

    scenarios = (Scenario(name="NORMAL"),)

    return Specification(
        entities=(
            customer,
            product,
            order,
        ),
        relationships=relationships,
        correlations=correlations,
        constraints=constraints,
        conditionals=conditionals,
        derived=derived,
        scenarios=scenarios,
    )


# ============================================================================
# TEST HELPER
# ============================================================================


def run_test(
    name: str,
    function,
) -> dict[str, Any]:

    try:

        passed = bool(function())

        return {
            "name": name,
            "status": ("PASS" if passed else "FAIL"),
        }

    except Exception as exc:

        return {
            "name": name,
            "status": "FAIL",
            "error": (f"{type(exc).__name__}: " f"{exc}"),
        }


# ============================================================================
# TESTS
# ============================================================================


def generate_baseline():

    return generate_dataset_with_provenance(
        build_specification(),
        "NORMAL",
        MASTER_SEED,
    )


def test_direct_generation_provenance() -> bool:

    dataset, provenance = generate_baseline()

    index = provenance_index(provenance)

    node = index[
        (
            "CUSTOMER",
            0,
            "CUSTOMER_SCORE",
        )
    ]

    return (
        node["generation_type"]
        in {
            "RANDOM",
            "CONDITIONAL",
            "CONSTANT",
        }
        and node["value"] == dataset["CUSTOMER"][0]["CUSTOMER_SCORE"]
    )


def test_statistical_provenance() -> bool:

    dataset, provenance = generate_baseline()

    return validate_statistical_lineage(
        build_specification(),
        provenance,
    )


def test_constraint_conditioned_provenance() -> bool:

    dataset, provenance = generate_baseline()

    index = provenance_index(provenance)

    node = index[
        (
            "ORDER",
            0,
            "ORDER_VALUE",
        )
    ]

    return (
        node["rule"] is not None
        and "minimum" in node["rule"]
        and node["value"] == dataset["ORDER"][0]["ORDER_VALUE"]
    )


def test_conditional_provenance() -> bool:

    dataset, provenance = generate_baseline()

    index = provenance_index(provenance)

    for index_value in range(200):

        node = index[
            (
                "ORDER",
                index_value,
                "DISCOUNT",
            )
        ]

        record = dataset["ORDER"][index_value]

        if record["ORDER_VALUE"] >= 10000.0:

            if node["generation_type"] != "CONDITIONAL":
                return False

            if node["context"].get("condition_result") is not True:
                return False

    return True


def test_derived_provenance() -> bool:

    dataset, provenance = generate_baseline()

    return validate_derived_lineage(
        build_specification(),
        dataset,
        provenance,
    )


def test_relationship_provenance() -> bool:

    dataset, provenance = generate_baseline()

    return validate_relationship_lineage(
        build_specification(),
        provenance,
    )


def test_cross_entity_lineage() -> bool:

    dataset, provenance = generate_baseline()

    index = provenance_index(provenance)

    node = index[
        (
            "ORDER",
            0,
            "CUSTOMER_VALUE",
        )
    ]

    dependency = node["dependencies"][0]

    return (
        dependency["entity"] == "CUSTOMER" and dependency["field"] == "CUSTOMER_VALUE"
    )


def test_multi_level_lineage() -> bool:

    dataset, provenance = generate_baseline()

    index = provenance_index(provenance)

    derived_node = index[
        (
            "ORDER",
            0,
            "NET_ORDER_VALUE",
        )
    ]

    derived_dependencies = derived_node["dependencies"]

    return len(derived_dependencies) == 2


def test_provenance_completeness() -> bool:

    dataset, provenance = generate_baseline()

    return validate_provenance_completeness(
        build_specification(),
        dataset,
        provenance,
    )


def test_dataset_provenance_consistency() -> bool:

    dataset, provenance = generate_baseline()

    return validate_provenance_dataset_consistency(
        dataset,
        provenance,
    )


def test_dependency_integrity() -> bool:

    dataset, provenance = generate_baseline()

    return validate_provenance_dependencies(
        dataset,
        provenance,
    )


def test_provenance_determinism() -> bool:

    first_dataset, first_provenance = generate_baseline()

    second_dataset, second_provenance = generate_baseline()

    return first_dataset == second_dataset and provenance_fingerprint(
        first_provenance
    ) == provenance_fingerprint(second_provenance)


def test_field_order_independence() -> bool:

    specification = build_specification()

    reversed_entities = []

    for entity in specification.entities:

        reversed_entities.append(
            Entity(
                name=entity.name,
                fields=tuple(reversed(entity.fields)),
                record_count=entity.record_count,
            )
        )

    alternate = Specification(
        entities=specification.entities,
        relationships=specification.relationships,
        correlations=specification.correlations,
        constraints=specification.constraints,
        conditionals=specification.conditionals,
        derived=specification.derived,
        scenarios=specification.scenarios,
    )

    alternate = Specification(
        entities=tuple(reversed_entities),
        relationships=alternate.relationships,
        correlations=alternate.correlations,
        constraints=alternate.constraints,
        conditionals=alternate.conditionals,
        derived=alternate.derived,
        scenarios=alternate.scenarios,
    )

    dataset_a, provenance_a = generate_dataset_with_provenance(
        specification,
        "NORMAL",
        MASTER_SEED,
    )

    dataset_b, provenance_b = generate_dataset_with_provenance(
        alternate,
        "NORMAL",
        MASTER_SEED,
    )

    return dataset_a == dataset_b and provenance_fingerprint(
        provenance_a
    ) == provenance_fingerprint(provenance_b)


def test_entity_order_independence() -> bool:

    specification = build_specification()

    alternate = Specification(
        entities=tuple(reversed(specification.entities)),
        relationships=specification.relationships,
        correlations=specification.correlations,
        constraints=specification.constraints,
        conditionals=specification.conditionals,
        derived=specification.derived,
        scenarios=specification.scenarios,
    )

    dataset_a, provenance_a = generate_dataset_with_provenance(
        specification,
        "NORMAL",
        MASTER_SEED,
    )

    dataset_b, provenance_b = generate_dataset_with_provenance(
        alternate,
        "NORMAL",
        MASTER_SEED,
    )

    return dataset_a == dataset_b and provenance_fingerprint(
        provenance_a
    ) == provenance_fingerprint(provenance_b)


def test_provenance_does_not_change_dataset() -> bool:

    specification = build_specification()

    dataset_with_provenance, _ = generate_dataset_with_provenance(
        specification,
        "NORMAL",
        MASTER_SEED,
    )

    dataset_again, _ = generate_dataset_with_provenance(
        specification,
        "NORMAL",
        MASTER_SEED,
    )

    return dataset_with_provenance == dataset_again


def test_seed_provenance() -> bool:

    _, provenance = generate_baseline()

    for nodes in provenance.values():

        for node in nodes:

            if node["seed"] != MASTER_SEED:
                return False

            if not node["seed_namespace"]:
                return False

    return True


def test_specification_reference() -> bool:

    _, provenance = generate_baseline()

    for nodes in provenance.values():

        for node in nodes:

            if not node["specification_reference"]:
                return False

    return True


def test_mutated_value_detection() -> bool:

    dataset, provenance = generate_baseline()

    mutated = mutate_provenance_value(provenance)

    return not validate_provenance_dataset_consistency(
        dataset,
        mutated,
    )


def test_broken_reference_detection() -> bool:

    dataset, provenance = generate_baseline()

    mutated = mutate_provenance_reference(provenance)

    return not validate_provenance_dependencies(
        dataset,
        mutated,
    )


def test_provenance_is_json_serializable() -> bool:

    _, provenance = generate_baseline()

    encoded = json.dumps(
        provenance,
        sort_keys=True,
    )

    decoded = json.loads(encoded)

    return decoded == provenance


# ============================================================================
# EXPLANATION SAMPLE
# ============================================================================


def print_explanation(
    provenance: dict[str, list[dict[str, Any]]],
    entity: str,
    record_index: int,
    field: str,
) -> None:

    index = provenance_index(provenance)

    node = index[
        (
            entity,
            record_index,
            field,
        )
    ]

    print()

    print("Representative explanation:")

    print(f"  {entity}.{field}" f" [record={record_index}]")

    print(f"    value:              " f"{node['value']}")

    print(f"    generation type:    " f"{node['generation_type']}")

    print(f"    specification:      " f"{node['specification_reference']}")

    print(f"    seed:               " f"{node['seed']}")

    print(f"    seed namespace:     " f"{node['seed_namespace']}")

    if node["rule"]:

        print("    rule:")

        for key, value in node["rule"].items():

            print(f"      {key}: {value}")

    if node["context"]:

        print("    context:")

        for key, value in node["context"].items():

            print(f"      {key}: {value}")

    if node["dependencies"]:

        print("    dependencies:")

        for dependency in node["dependencies"]:

            print(
                f"      "
                f"{dependency['entity']}."
                f"{dependency['field']}"
                f"[{dependency['record_index']}]"
                f" = "
                f"{dependency['value']}"
            )


# ============================================================================
# MAIN
# ============================================================================


def main() -> int:

    print()

    print("=" * 70)

    print("FORGE - Experiment 020-T: " "Declarative Generation Provenance")

    print("=" * 70)

    print("Experiment:     " "020_declarative_generation_specification")

    print("Stage:          020-T")

    print("Purpose:        " "Deterministic generation provenance and explainability")

    print(f"Random seed:    {MASTER_SEED}")

    specification = build_specification()

    print()

    print("Provenance model:")

    print("  Specification")

    print("       ↓")

    print("  Generation plan")

    print("       ↓")

    print("  Generated value")

    print("       ↓")

    print("  Provenance node")

    print("       ↓")

    print("  Dependency lineage")

    print()

    print("Dataset:")

    print(
        f"  CUSTOMER records: " f"{entity_map(specification)['CUSTOMER'].record_count}"
    )

    print(
        f"  PRODUCT records:  " f"{entity_map(specification)['PRODUCT'].record_count}"
    )

    print(f"  ORDER records:    " f"{entity_map(specification)['ORDER'].record_count}")

    print()

    print("Provenance validation:")

    tests = [
        (
            "Direct generation provenance",
            test_direct_generation_provenance,
        ),
        (
            "Statistical provenance",
            test_statistical_provenance,
        ),
        (
            "Constraint-conditioned provenance",
            test_constraint_conditioned_provenance,
        ),
        (
            "Conditional provenance",
            test_conditional_provenance,
        ),
        (
            "Derived-field provenance",
            test_derived_provenance,
        ),
        (
            "Relationship provenance",
            test_relationship_provenance,
        ),
        (
            "Cross-entity lineage",
            test_cross_entity_lineage,
        ),
        (
            "Multi-level lineage",
            test_multi_level_lineage,
        ),
        (
            "Provenance completeness",
            test_provenance_completeness,
        ),
        (
            "Dataset/provenance consistency",
            test_dataset_provenance_consistency,
        ),
        (
            "Dependency integrity",
            test_dependency_integrity,
        ),
        (
            "Provenance determinism",
            test_provenance_determinism,
        ),
        (
            "Field-order independence",
            test_field_order_independence,
        ),
        (
            "Entity-order independence",
            test_entity_order_independence,
        ),
        (
            "Provenance does not change dataset",
            test_provenance_does_not_change_dataset,
        ),
        (
            "Seed provenance",
            test_seed_provenance,
        ),
        (
            "Specification references",
            test_specification_reference,
        ),
        (
            "Mutated value detection",
            test_mutated_value_detection,
        ),
        (
            "Broken reference detection",
            test_broken_reference_detection,
        ),
        (
            "JSON serialization",
            test_provenance_is_json_serializable,
        ),
    ]

    results = []

    for name, function in tests:

        result = run_test(
            name,
            function,
        )

        results.append(result)

        print(f"  {name:<40}" f"{result['status']}")

        if result["status"] == "FAIL" and "error" in result:

            print(f"      error: " f"{result['error']}")

    dataset, provenance = generate_baseline()

    print_explanation(
        provenance,
        "ORDER",
        0,
        "NET_ORDER_VALUE",
    )

    tests_passed = sum(result["status"] == "PASS" for result in results)

    tests_total = len(results)

    overall = tests_passed == tests_total

    provenance_nodes = sum(len(nodes) for nodes in provenance.values())

    dataset_records = sum(len(records) for records in dataset.values())

    provenance_fingerprint_value = provenance_fingerprint(provenance)

    print()

    print("Provenance statistics:")

    print(f"  Dataset records:          " f"{dataset_records}")

    print(f"  Provenance nodes:          " f"{provenance_nodes}")

    print(
        f"  Provenance coverage:       " f"{'100%' if provenance_nodes > 0 else '0%'}"
    )

    print(f"  Provenance fingerprint:    " f"{provenance_fingerprint_value}")

    print()

    print("Experiment result:")

    print(f"  Tests passed:              " f"{tests_passed}/{tests_total}")

    print(f"  Overall:                   " f"{'PASS' if overall else 'FAIL'}")

    # ------------------------------------------------------------------
    # Persist actual dataset.
    # ------------------------------------------------------------------

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    with DATASET_PATH.open(
        "w",
        encoding="utf-8",
    ) as file:

        json.dump(
            dataset,
            file,
            indent=2,
        )

    with PROVENANCE_PATH.open(
        "w",
        encoding="utf-8",
    ) as file:

        json.dump(
            provenance,
            file,
            indent=2,
        )

    result_payload = {
        "experiment": ("020_declarative_generation_specification"),
        "stage": "020-T",
        "purpose": ("Declarative generation provenance " "and explainability"),
        "seed": MASTER_SEED,
        "tests": results,
        "tests_passed": tests_passed,
        "tests_total": tests_total,
        "overall": ("PASS" if overall else "FAIL"),
        "dataset_records": dataset_records,
        "provenance_nodes": provenance_nodes,
        "provenance_fingerprint": (provenance_fingerprint_value),
        "artifacts": {
            "dataset": str(DATASET_PATH),
            "provenance": str(PROVENANCE_PATH),
        },
        "architecture": {
            "provenance_separate_from_dataset": True,
            "deterministic": True,
            "field_order_independent": True,
            "entity_order_independent": True,
            "dependency_lineage": True,
            "statistical_lineage": True,
            "derived_lineage": True,
            "relationship_lineage": True,
            "scenario_lineage": True,
        },
    }

    with RESULTS_PATH.open(
        "w",
        encoding="utf-8",
    ) as file:

        json.dump(
            result_payload,
            file,
            indent=2,
        )

    print()

    print("Output:")

    print(f"  Dataset:     {DATASET_PATH}")

    print(f"  Provenance:  {PROVENANCE_PATH}")

    print(f"  Results:     {RESULTS_PATH}")

    print()

    if overall:

        print("Experiment completed successfully.")

        print("Declarative generation provenance " "is experimentally validated.")

        return 0

    print("Experiment completed with failures.")

    return 1


if __name__ == "__main__":

    sys.exit(main())
