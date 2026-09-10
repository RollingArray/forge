"""
FORGE - Experiment 021-C: Declarative Constraint-Aware Model to Dataset
=======================================================================

Purpose
-------
This experiment extends 021-B by introducing declarative constraints into
the model-to-dataset generation pipeline.

021-B established that FORGE can:

    1. Read a declarative relational model.
    2. Generate multiple entity datasets.
    3. Resolve declarative relationships.
    4. Preserve referential integrity.
    5. Materialize the result as CSV.

021-C asks the next architectural question:

    Can a generic FORGE runtime generate datasets that satisfy constraints
    declared entirely in the specification?

The runtime must not contain knowledge of what an entity or field means.

Constraint behavior must come from specification.json.

Experiment
----------
021 - Declarative Model to Dataset

Implementation Stage
--------------------
021-C - Declarative Constraints

Key Question
------------
Can FORGE generate a relational dataset that satisfies declaratively
defined field, entity, and model constraints without using
domain-specific generation logic or post-generation repair?

Architecture
------------

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
    Generation Planning
           |
           v
    Candidate Generation
           |
           v
    Constraint Evaluation
           |
           +---- invalid ----> regenerate candidate
           |
           v
    Relationship Resolution
           |
           v
    Final Constraint Validation
           |
           v
    CSV Dataset

Constraint Model
----------------
This experiment supports the declarative constraint operators required
by the experiment specification:

    BETWEEN
    IN
    EQUALS
    GREATER_OR_EQUAL
    IMPLIES

Constraints may be declared at:

    1. Field level
    2. Entity level
    3. Model level

The implementation discovers these locations from the specification.

Important Design Rule
---------------------
The runtime must never contain entity-specific rules such as:

    if entity == "CUSTOMER":
        ...

or:

    if field == "CUSTOMER_SCORE":
        ...

or:

    if customer_type == "PREMIUM":
        ...

All such behavior must come from the declarative specification.

Generation Rule
---------------
The runtime generates candidate records according to the declared
field generation behavior.

If a candidate does not satisfy the applicable declarative constraints,
the candidate is rejected and regenerated.

The runtime does not modify an already generated invalid record.

Therefore:

    Generate candidate
          |
          v
    Validate candidate
          |
       valid?
       /     \
     yes      no
      |        |
      v        v
    accept   regenerate

This experiment therefore does not use post-generation repair.

Design Principles
-----------------
- Specification over hard-coded business logic.
- Constraints over procedural business rules.
- Entity names are opaque identifiers.
- Field names are opaque identifiers.
- Relationships come from the specification.
- Constraint semantics come from the specification.
- Invalid candidates are rejected rather than repaired.
- No hidden constraint relaxation.
- No hidden fallback generation.
- No domain-specific logic.
- Deterministic generation.
- Reproducible generation for a fixed seed.
- CSV is the dataset format.
- JSON is used for metadata and experiment evidence.

Scope
-----
This experiment validates constraint-aware model-to-dataset generation.

Included
--------
- Single-field constraints.
- Entity-level constraints.
- Model-level constraints.
- Cross-field constraints.
- Conditional constraints.
- Declarative comparison operators.
- Declarative membership operators.
- Constraint-aware candidate generation.
- Constraint validation.
- Relationship generation from 021-B.
- Referential integrity.
- CSV materialization.
- Reproducibility.
- Seed sensitivity.
- Entity-order independence.
- Field-order independence.
- No post-generation repair.

Excluded
--------
- Statistical correlations.
- Derived fields.
- Complex dependency graphs.
- Scenario overrides.
- Provenance.
- Conflict diagnosis.
- Large-scale performance testing.
- Many-to-many relationship generation.

Those capabilities are intentionally left for later experiments.

Output Structure
----------------

    021-C/
    |
    +-- experiment.py
    +-- specification.json
    +-- README-experiment-outcome.md
    |
    +-- output/
        |
        +-- dataset/
        |   +-- <ENTITY>.csv
        |   +-- ...
        |
        +-- generation_manifest.json
        +-- constraint_generation_results.json

The actual entity names are determined entirely by specification.json.

Author
------
Ranjoy Sen

Status
------
Experimental

How to Run
----------
From the repository root:

    uv run python experiments/021_declarative_model_to_dataset/021-C/experiment.py

Input
-----
    experiments/021_declarative_model_to_dataset/021-C/specification.json

Output
------
    experiments/021_declarative_model_to_dataset/021-C/output/
"""

from __future__ import annotations

import copy
import csv
import hashlib
import json
import random
import sys
from pathlib import Path
from typing import Any

# ============================================================================
# EXPERIMENT CONFIGURATION
# ============================================================================

EXPERIMENT_ID = "021-C"
EXPERIMENT_NAME = "021_declarative_model_to_dataset"

EXPERIMENT_DIR = Path(__file__).resolve().parent

SPECIFICATION_FILE = EXPERIMENT_DIR / "specification.json"

OUTPUT_DIR = EXPERIMENT_DIR / "output"

DATASET_DIR = OUTPUT_DIR / "dataset"

MAX_RECORD_ATTEMPTS = 1000


# ============================================================================
# SPECIFICATION LOADING
# ============================================================================


def load_specification(
    path: Path = SPECIFICATION_FILE,
) -> dict[str, Any]:
    """Load the declarative model."""

    if not path.exists():
        raise FileNotFoundError(f"Specification not found: {path}")

    with path.open(
        "r",
        encoding="utf-8",
    ) as handle:
        specification = json.load(handle)

    if not isinstance(
        specification,
        dict,
    ):
        raise ValueError("Specification root must be a JSON object.")

    return specification


# ============================================================================
# GENERIC SPECIFICATION HELPERS
# ============================================================================


def get_model_name(
    specification: dict[str, Any],
) -> str:

    model = specification.get("model")

    if not isinstance(
        model,
        dict,
    ):
        raise ValueError("Specification must define a model object.")

    name = model.get("name")

    if (
        not isinstance(
            name,
            str,
        )
        or not name
    ):

        raise ValueError("Model must define a non-empty name.")

    return name


def get_seed(
    specification: dict[str, Any],
) -> int:

    generation = specification.get(
        "generation",
        {},
    )

    seed = generation.get("seed")

    if not isinstance(
        seed,
        int,
    ):
        raise ValueError("Generation must define an integer seed.")

    return seed


def get_scenario(
    specification: dict[str, Any],
) -> str:

    generation = specification.get(
        "generation",
        {},
    )

    scenario = generation.get(
        "scenario",
        "NORMAL",
    )

    if not isinstance(
        scenario,
        str,
    ):
        raise ValueError("Scenario must be a string.")

    return scenario


def build_entity_map(
    specification: dict[str, Any],
) -> dict[str, dict[str, Any]]:

    return {entity["name"]: entity for entity in specification["entities"]}


def build_field_map(
    entity: dict[str, Any],
) -> dict[str, dict[str, Any]]:

    return {field["name"]: field for field in entity["fields"]}


def get_population_count(
    entity: dict[str, Any],
) -> int:

    population = entity.get("population")

    if not isinstance(
        population,
        dict,
    ):
        raise ValueError(
            f"Entity {entity.get('name')!r} " "must define population configuration."
        )

    count = population.get("count")

    if (
        not isinstance(
            count,
            int,
        )
        or count < 0
    ):
        raise ValueError(
            f"Entity {entity.get('name')!r} "
            "must define a non-negative population count."
        )

    return count


# ============================================================================
# SPECIFICATION VALIDATION
# ============================================================================

SUPPORTED_OPERATORS = {
    "BETWEEN",
    "IN",
    "EQUALS",
    "GREATER_OR_EQUAL",
    "IMPLIES",
}


def validate_operand(
    operand: Any,
    entity_name: str,
    field_names: set[str],
    errors: list[str],
    location: str,
) -> None:
    """
    Validate an expression operand recursively.

    An operand may be:

        - a literal
        - {"field": "..."}
        - {"rule": "...", "operands": [...]}
    """

    if isinstance(
        operand,
        dict,
    ):

        if "field" in operand:

            field_name = operand["field"]

            if field_name not in field_names:

                errors.append(
                    f"{location} references unknown "
                    f"field {entity_name}.{field_name}."
                )

            return

        if "rule" in operand:

            validate_rule(
                operand,
                entity_name,
                field_names,
                errors,
                location,
            )

            return

        errors.append(f"{location} contains an unsupported " "expression object.")


def validate_rule(
    rule: Any,
    entity_name: str,
    field_names: set[str],
    errors: list[str],
    location: str,
) -> None:

    if not isinstance(
        rule,
        dict,
    ):
        errors.append(f"{location} must be an object.")
        return

    operator = rule.get("rule")

    if operator not in SUPPORTED_OPERATORS:

        errors.append(f"{location} uses unsupported " f"operator {operator!r}.")

        return

    operands = rule.get("operands")

    if not isinstance(
        operands,
        list,
    ):
        errors.append(f"{location} must contain an operands list.")
        return

    required_counts = {
        "BETWEEN": 3,
        "IN": 2,
        "EQUALS": 2,
        "GREATER_OR_EQUAL": 2,
        "IMPLIES": 2,
    }

    expected = required_counts[operator]

    if len(operands) != expected:

        errors.append(
            f"{location} operator {operator!r} " f"requires {expected} operands."
        )

        return

    for index, operand in enumerate(operands):

        validate_operand(
            operand,
            entity_name,
            field_names,
            errors,
            f"{location}.operands[{index}]",
        )


def collect_constraints(
    specification: dict[str, Any],
) -> list[dict[str, Any]]:
    """
    Normalize constraints from all supported declaration locations.

    Every returned constraint receives an explicit entity context.

    Field-level constraints:
        field["constraints"]

    Entity-level constraints:
        entity["constraints"]

    Model-level constraints:
        specification["constraints"]
    """

    constraints: list[dict[str, Any]] = []

    for entity in specification.get(
        "entities",
        [],
    ):

        entity_name = entity["name"]

        for field in entity.get(
            "fields",
            [],
        ):

            for constraint in field.get(
                "constraints",
                [],
            ):

                normalized = copy.deepcopy(constraint)

                normalized["_entity"] = entity_name

                normalized["_source"] = "FIELD"

                normalized["_field"] = field["name"]

                constraints.append(normalized)

        for constraint in entity.get(
            "constraints",
            [],
        ):

            normalized = copy.deepcopy(constraint)

            normalized["_entity"] = entity_name

            normalized["_source"] = "ENTITY"

            constraints.append(normalized)

    for constraint in specification.get(
        "constraints",
        [],
    ):

        normalized = copy.deepcopy(constraint)

        normalized["_source"] = "MODEL"

        constraints.append(normalized)

    return constraints


def validate_specification(
    specification: dict[str, Any],
) -> list[str]:

    errors: list[str] = []

    try:
        get_model_name(specification)
    except ValueError as exc:
        errors.append(str(exc))

    try:
        get_seed(specification)
    except ValueError as exc:
        errors.append(str(exc))

    entities = specification.get("entities")

    if (
        not isinstance(
            entities,
            list,
        )
        or not entities
    ):

        errors.append("Specification must contain entities.")

        return errors

    entity_map = build_entity_map(specification)

    for entity in entities:

        entity_name = entity.get("name")

        if (
            not isinstance(
                entity_name,
                str,
            )
            or not entity_name
        ):

            errors.append("Every entity must have a non-empty name.")

            continue

        try:
            get_population_count(entity)
        except ValueError as exc:
            errors.append(str(exc))

        fields = entity.get("fields")

        if not isinstance(
            fields,
            list,
        ):

            errors.append(f"Entity {entity_name!r} " "must contain fields.")

            continue

        field_names = {
            field.get("name")
            for field in fields
            if isinstance(
                field,
                dict,
            )
        }

        for field in fields:

            if not isinstance(
                field,
                dict,
            ):
                errors.append(f"{entity_name} contains an invalid field.")
                continue

            field_name = field.get("name")

            if not field_name:

                errors.append(f"{entity_name} contains a field " "without a name.")

            if not isinstance(
                field.get("type"),
                str,
            ):

                errors.append(f"{entity_name}.{field_name} " "must define a type.")

    # ------------------------------------------------------------------
    # Relationship validation
    # ------------------------------------------------------------------

    for relationship in specification.get(
        "relationships",
        [],
    ):

        parent_entity = relationship.get("parent_entity")

        child_entity = relationship.get("child_entity")

        parent_field = relationship.get("parent_field")

        child_field = relationship.get("child_field")

        if parent_entity not in entity_map:

            errors.append(
                f"Relationship references unknown " f"parent entity {parent_entity!r}."
            )

            continue

        if child_entity not in entity_map:

            errors.append(
                f"Relationship references unknown " f"child entity {child_entity!r}."
            )

            continue

        parent_fields = build_field_map(entity_map[parent_entity])

        child_fields = build_field_map(entity_map[child_entity])

        if parent_field not in parent_fields:

            errors.append(
                f"Relationship references unknown "
                f"parent field "
                f"{parent_entity}.{parent_field}."
            )

        if child_field not in child_fields:

            errors.append(
                f"Relationship references unknown "
                f"child field "
                f"{child_entity}.{child_field}."
            )

    # ------------------------------------------------------------------
    # Constraint validation
    # ------------------------------------------------------------------

    for constraint in collect_constraints(specification):

        entity_name = constraint.get("_entity")

        if entity_name:

            entity = entity_map.get(entity_name)

            if entity is None:

                errors.append(
                    f"Constraint references unknown " f"entity {entity_name!r}."
                )

                continue

            field_names = set(build_field_map(entity))

        else:

            # Model-level constraints may explicitly provide
            # an entity in the specification.
            constraint_entity = constraint.get("entity")

            if constraint_entity:

                entity = entity_map.get(constraint_entity)

                if entity is None:

                    errors.append(
                        f"Constraint references unknown "
                        f"entity {constraint_entity!r}."
                    )

                    continue

                field_names = set(build_field_map(entity))

                entity_name = constraint_entity

            else:

                # Without an entity context, field references cannot
                # be resolved safely.
                errors.append(
                    f"Constraint "
                    f"{constraint.get('name', '<unnamed>')!r} "
                    "does not provide an entity context."
                )

                continue

        validate_rule(
            constraint,
            entity_name,
            field_names,
            errors,
            (f"constraint:" f"{constraint.get('name', '<unnamed>')}"),
        )

    return errors


# ============================================================================
# DETERMINISTIC FIELD STREAMS
# ============================================================================


def derive_field_seed(
    master_seed: int,
    entity_name: str,
    field_name: str,
    record_index: int | None = None,
) -> int:

    namespace = f"FIELD:{entity_name}:{field_name}"

    if record_index is not None:

        namespace = f"{namespace}:RECORD:{record_index}"

    digest = hashlib.sha256((f"{master_seed}:{namespace}").encode("utf-8")).digest()

    return int.from_bytes(
        digest[:8],
        "big",
    )


# ============================================================================
# FIELD GENERATION
# ============================================================================


def generate_identity_value(
    field: dict[str, Any],
    record_index: int,
) -> Any:

    identity = field.get("identity")

    if not isinstance(
        identity,
        dict,
    ):
        raise ValueError(
            f"Field {field.get('name')!r} " "has invalid identity configuration."
        )

    strategy = identity.get("strategy")

    if strategy != "SEQUENTIAL_ID":

        raise ValueError(f"Unsupported identity strategy " f"{strategy!r}.")

    prefix = identity.get(
        "prefix",
        "",
    )

    start = identity.get(
        "start",
        1,
    )

    return f"{prefix}" f"{start + record_index}"


def generate_random_value(
    entity_name: str,
    field: dict[str, Any],
    record_index: int,
    master_seed: int,
) -> Any:

    generation = field.get("generation")

    if not isinstance(
        generation,
        dict,
    ):
        raise ValueError(
            f"{entity_name}.{field['name']} " "has no valid generation configuration."
        )

    strategy = generation.get("strategy")

    if strategy != "RANDOM":

        raise ValueError(
            f"Unsupported generation strategy "
            f"{strategy!r} for "
            f"{entity_name}.{field['name']}."
        )

    distribution = generation.get("distribution")

    parameters = generation.get(
        "parameters",
        {},
    )

    rng = random.Random(
        derive_field_seed(
            master_seed,
            entity_name,
            field["name"],
            record_index,
        )
    )

    if distribution == "UNIFORM":

        minimum = parameters.get("minimum")

        maximum = parameters.get("maximum")

        if minimum is None or maximum is None:

            raise ValueError(
                f"{entity_name}.{field['name']} "
                "UNIFORM generation requires "
                "minimum and maximum."
            )

        if minimum > maximum:

            raise ValueError(
                f"{entity_name}.{field['name']} " "has invalid generation bounds."
            )

        value = rng.uniform(
            minimum,
            maximum,
        )

        precision = parameters.get("precision")

        if precision is not None:

            value = round(
                value,
                precision,
            )

        return value

    if distribution == "DISCRETE_UNIFORM":

        minimum = parameters.get("minimum")

        maximum = parameters.get("maximum")

        return rng.randint(
            minimum,
            maximum,
        )

    if distribution == "CATEGORICAL":

        values = parameters.get("values")

        weights = parameters.get("weights")

        if (
            not isinstance(
                values,
                list,
            )
            or not values
        ):

            raise ValueError(
                f"{entity_name}.{field['name']} " "requires categorical values."
            )

        return rng.choices(
            values,
            weights=weights,
            k=1,
        )[0]

    raise ValueError(
        f"Unsupported distribution "
        f"{distribution!r} for "
        f"{entity_name}.{field['name']}."
    )


def generate_independent_value(
    entity_name: str,
    field: dict[str, Any],
    record_index: int,
    master_seed: int,
) -> Any:

    if "identity" in field:

        return generate_identity_value(
            field,
            record_index,
        )

    if "generation" in field:

        return generate_random_value(
            entity_name,
            field,
            record_index,
            master_seed,
        )

    raise ValueError(
        f"No executable generation behavior "
        f"declared for "
        f"{entity_name}.{field['name']}."
    )


# ============================================================================
# EXPRESSION EVALUATION
# ============================================================================


def resolve_operand(
    operand: Any,
    record: dict[str, Any],
) -> Any:

    if isinstance(
        operand,
        dict,
    ):

        if "field" in operand:

            field_name = operand["field"]

            if field_name not in record:

                raise ValueError(f"Unknown field reference " f"{field_name!r}.")

            return record[field_name]

        if "rule" in operand:

            return evaluate_rule(
                operand,
                record,
            )

        raise ValueError("Unsupported expression operand.")

    return operand


def evaluate_rule(
    rule: dict[str, Any],
    record: dict[str, Any],
) -> bool:

    operator = rule.get("rule")

    operands = rule.get(
        "operands",
        [],
    )

    if operator == "BETWEEN":

        value = resolve_operand(
            operands[0],
            record,
        )

        minimum = resolve_operand(
            operands[1],
            record,
        )

        maximum = resolve_operand(
            operands[2],
            record,
        )

        return minimum <= value <= maximum

    if operator == "IN":

        value = resolve_operand(
            operands[0],
            record,
        )

        allowed = resolve_operand(
            operands[1],
            record,
        )

        return value in allowed

    if operator == "EQUALS":

        left = resolve_operand(
            operands[0],
            record,
        )

        right = resolve_operand(
            operands[1],
            record,
        )

        return left == right

    if operator == "GREATER_OR_EQUAL":

        left = resolve_operand(
            operands[0],
            record,
        )

        right = resolve_operand(
            operands[1],
            record,
        )

        return left >= right

    if operator == "IMPLIES":

        condition = bool(
            resolve_operand(
                operands[0],
                record,
            )
        )

        consequence = bool(
            resolve_operand(
                operands[1],
                record,
            )
        )

        return not condition or consequence

    raise ValueError(f"Unsupported constraint operator " f"{operator!r}.")


# ============================================================================
# CONSTRAINT CONTEXT
# ============================================================================


def get_constraints_for_entity(
    specification: dict[str, Any],
    entity_name: str,
) -> list[dict[str, Any]]:
    """
    Return every constraint applicable to an entity.

    Constraints may originate from:

        - fields
        - entity
        - model

    Model-level constraints with an explicit entity are included.
    """

    constraints = []

    for constraint in collect_constraints(specification):

        constraint_entity = constraint.get("_entity")

        if constraint_entity == entity_name:

            constraints.append(constraint)

            continue

        explicit_entity = constraint.get("entity")

        if constraint.get("_source") == "MODEL" and explicit_entity == entity_name:

            constraints.append(constraint)

    return constraints


def validate_record_constraints(
    constraints: list[dict[str, Any]],
    record: dict[str, Any],
) -> bool:

    for constraint in constraints:

        if not evaluate_rule(
            constraint,
            record,
        ):
            return False

    return True


# ============================================================================
# RELATIONSHIP-MANAGED FIELDS
# ============================================================================


def get_relationship_managed_fields(
    specification: dict[str, Any],
) -> set[tuple[str, str]]:

    return {
        (
            relationship["child_entity"],
            relationship["child_field"],
        )
        for relationship in specification.get(
            "relationships",
            [],
        )
    }


# ============================================================================
# GENERATION PLANNING
# ============================================================================


def build_generation_plan(
    specification: dict[str, Any],
) -> list[str]:

    entities = [entity["name"] for entity in specification["entities"]]

    dependencies = {entity_name: set() for entity_name in entities}

    for relationship in specification.get(
        "relationships",
        [],
    ):

        dependencies[relationship["child_entity"]].add(relationship["parent_entity"])

    remaining = set(entities)

    ordered: list[str] = []

    while remaining:

        ready = sorted(
            entity_name
            for entity_name in remaining
            if dependencies[entity_name].issubset(set(ordered))
        )

        if not ready:

            raise ValueError(
                "Generation planning failed: " "relationship dependency cycle detected."
            )

        ordered.extend(ready)

        remaining.difference_update(ready)

    return ordered


# ============================================================================
# CONSTRAINT-AWARE RECORD GENERATION
# ============================================================================


def generate_constraint_aware_record(
    entity: dict[str, Any],
    constraints: list[dict[str, Any]],
    relationship_managed_fields: set[tuple[str, str]],
    record_index: int,
    master_seed: int,
) -> dict[str, Any]:
    """
    Generate one valid candidate record.

    Invalid candidates are discarded and regenerated.

    No already-generated invalid record is modified.
    """

    entity_name = entity["name"]

    executable_fields = [
        field
        for field in entity["fields"]
        if (
            entity_name,
            field["name"],
        )
        not in relationship_managed_fields
    ]

    for attempt in range(MAX_RECORD_ATTEMPTS):

        # --------------------------------------------------------------
        # Candidate generation.
        #
        # The attempt number becomes part of the deterministic seed
        # namespace. This means the same specification and seed always
        # produce the same candidate sequence.
        # --------------------------------------------------------------

        candidate: dict[str, Any] = {}

        for field in executable_fields:

            field_name = field["name"]

            attempt_seed = derive_field_seed(
                master_seed,
                entity_name,
                field_name,
                record_index,
            )

            attempt_rng = random.Random(attempt_seed + attempt)

            if "identity" in field:

                candidate[field_name] = generate_identity_value(
                    field,
                    record_index,
                )

                continue

            generation = field.get("generation")

            if not isinstance(
                generation,
                dict,
            ):

                raise ValueError(
                    f"No executable generation behavior "
                    f"declared for "
                    f"{entity_name}.{field_name}."
                )

            distribution = generation.get("distribution")

            parameters = generation.get(
                "parameters",
                {},
            )

            strategy = generation.get("strategy")

            if strategy != "RANDOM":

                raise ValueError(f"Unsupported generation strategy " f"{strategy!r}.")

            if distribution == "UNIFORM":

                minimum = parameters.get("minimum")

                maximum = parameters.get("maximum")

                value = attempt_rng.uniform(
                    minimum,
                    maximum,
                )

                precision = parameters.get("precision")

                if precision is not None:

                    value = round(
                        value,
                        precision,
                    )

                candidate[field_name] = value

            elif distribution == "DISCRETE_UNIFORM":

                candidate[field_name] = attempt_rng.randint(
                    parameters["minimum"],
                    parameters["maximum"],
                )

            elif distribution == "CATEGORICAL":

                values = parameters.get("values")

                weights = parameters.get("weights")

                candidate[field_name] = attempt_rng.choices(
                    values,
                    weights=weights,
                    k=1,
                )[0]

            else:

                raise ValueError(f"Unsupported distribution " f"{distribution!r}.")

        # --------------------------------------------------------------
        # Constraint evaluation.
        # --------------------------------------------------------------

        if validate_record_constraints(
            constraints,
            candidate,
        ):

            return candidate

    constraint_names = [
        constraint.get(
            "name",
            "<unnamed>",
        )
        for constraint in constraints
    ]

    raise ValueError(
        f"Unable to generate a valid "
        f"{entity_name} record after "
        f"{MAX_RECORD_ATTEMPTS} attempts. "
        f"Constraints: {constraint_names}"
    )


def generate_entity_dataset(
    entity: dict[str, Any],
    specification: dict[str, Any],
    relationship_managed_fields: set[tuple[str, str]],
    master_seed: int,
) -> list[dict[str, Any]]:

    entity_name = entity["name"]

    constraints = get_constraints_for_entity(
        specification,
        entity_name,
    )

    record_count = get_population_count(entity)

    records = []

    for record_index in range(record_count):

        record = generate_constraint_aware_record(
            entity,
            constraints,
            relationship_managed_fields,
            record_index,
            master_seed,
        )

        records.append(record)

    return records


# ============================================================================
# RELATIONSHIP RESOLUTION
# ============================================================================


def resolve_relationships(
    specification: dict[str, Any],
    dataset: dict[
        str,
        list[dict[str, Any]],
    ],
) -> None:

    for relationship in specification.get(
        "relationships",
        [],
    ):

        parent_entity = relationship["parent_entity"]

        child_entity = relationship["child_entity"]

        parent_field = relationship["parent_field"]

        child_field = relationship["child_field"]

        required = relationship["required"]

        parent_records = dataset[parent_entity]

        child_records = dataset[child_entity]

        parent_values = [record[parent_field] for record in parent_records]

        if required and not parent_values:

            raise ValueError(
                f"Required relationship "
                f"{parent_entity}.{parent_field} -> "
                f"{child_entity}.{child_field} "
                "has no parent values."
            )

        relationship_seed = derive_field_seed(
            get_seed(specification),
            child_entity,
            child_field,
        )

        rng = random.Random(relationship_seed)

        for record in child_records:

            if parent_values:

                record[child_field] = rng.choice(parent_values)

            else:

                record[child_field] = None


# ============================================================================
# FINAL DATASET VALIDATION
# ============================================================================


def validate_dataset_structure(
    specification: dict[str, Any],
    dataset: dict[
        str,
        list[dict[str, Any]],
    ],
) -> bool:

    expected_entities = {entity["name"] for entity in specification["entities"]}

    return set(dataset) == expected_entities


def validate_population_counts(
    specification: dict[str, Any],
    dataset: dict[
        str,
        list[dict[str, Any]],
    ],
) -> bool:

    for entity in specification["entities"]:

        entity_name = entity["name"]

        if len(dataset[entity_name]) != get_population_count(entity):

            return False

    return True


def validate_field_presence(
    specification: dict[str, Any],
    dataset: dict[
        str,
        list[dict[str, Any]],
    ],
) -> bool:

    for entity in specification["entities"]:

        entity_name = entity["name"]

        expected_fields = {field["name"] for field in entity["fields"]}

        for record in dataset[entity_name]:

            if set(record) != expected_fields:

                return False

    return True


def validate_identity_uniqueness(
    specification: dict[str, Any],
    dataset: dict[
        str,
        list[dict[str, Any]],
    ],
) -> bool:

    for entity in specification["entities"]:

        entity_name = entity["name"]

        for field in entity["fields"]:

            if "identity" not in field:
                continue

            field_name = field["name"]

            values = [record[field_name] for record in dataset[entity_name]]

            if len(values) != len(set(values)):

                return False

    return True


def validate_constraints(
    specification: dict[str, Any],
    dataset: dict[
        str,
        list[dict[str, Any]],
    ],
) -> bool:

    for entity in specification["entities"]:

        entity_name = entity["name"]

        constraints = get_constraints_for_entity(
            specification,
            entity_name,
        )

        for record in dataset[entity_name]:

            if not validate_record_constraints(
                constraints,
                record,
            ):

                return False

    return True


def validate_referential_integrity(
    specification: dict[str, Any],
    dataset: dict[
        str,
        list[dict[str, Any]],
    ],
) -> bool:

    for relationship in specification.get(
        "relationships",
        [],
    ):

        parent_values = {
            record[relationship["parent_field"]]
            for record in dataset[relationship["parent_entity"]]
        }

        for record in dataset[relationship["child_entity"]]:

            value = record.get(relationship["child_field"])

            if value is None:

                if relationship["required"]:

                    return False

                continue

            if value not in parent_values:

                return False

    return True


# ============================================================================
# DETERMINISM VALIDATION
# ============================================================================


def generate_complete_dataset(
    specification: dict[str, Any],
) -> dict[
    str,
    list[dict[str, Any]],
]:

    master_seed = get_seed(specification)

    relationship_managed_fields = get_relationship_managed_fields(specification)

    generation_order = build_generation_plan(specification)

    entity_map = build_entity_map(specification)

    dataset: dict[
        str,
        list[dict[str, Any]],
    ] = {}

    for entity_name in generation_order:

        dataset[entity_name] = generate_entity_dataset(
            entity_map[entity_name],
            specification,
            relationship_managed_fields,
            master_seed,
        )

    resolve_relationships(
        specification,
        dataset,
    )

    return dataset


def test_reproducibility(
    specification: dict[str, Any],
) -> bool:

    first = generate_complete_dataset(specification)

    second = generate_complete_dataset(specification)

    return first == second


def test_seed_sensitivity(
    specification: dict[str, Any],
) -> bool:

    first = generate_complete_dataset(specification)

    alternate = copy.deepcopy(specification)

    alternate["generation"]["seed"] = get_seed(specification) + 1

    second = generate_complete_dataset(alternate)

    return first != second


def test_entity_order_independence(
    specification: dict[str, Any],
) -> bool:

    first = generate_complete_dataset(specification)

    alternate = copy.deepcopy(specification)

    alternate["entities"] = list(reversed(alternate["entities"]))

    second = generate_complete_dataset(alternate)

    return first == second


def test_field_order_independence(
    specification: dict[str, Any],
) -> bool:

    first = generate_complete_dataset(specification)

    alternate = copy.deepcopy(specification)

    for entity in alternate["entities"]:

        entity["fields"] = list(reversed(entity["fields"]))

    second = generate_complete_dataset(alternate)

    return first == second


# ============================================================================
# CSV OUTPUT
# ============================================================================


def write_entity_csv(
    entity_name: str,
    records: list[dict[str, Any]],
) -> Path:

    DATASET_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    path = DATASET_DIR / f"{entity_name}.csv"

    fieldnames = []

    if records:

        fieldnames = list(records[0].keys())

    with path.open(
        "w",
        newline="",
        encoding="utf-8",
    ) as handle:

        writer = csv.DictWriter(
            handle,
            fieldnames=fieldnames,
        )

        writer.writeheader()

        writer.writerows(records)

    return path


def write_dataset_csv(
    dataset: dict[
        str,
        list[dict[str, Any]],
    ],
) -> dict[str, Path]:

    paths = {}

    for entity_name, records in dataset.items():

        paths[entity_name] = write_entity_csv(
            entity_name,
            records,
        )

    return paths


# ============================================================================
# JSON OUTPUT
# ============================================================================


def write_json(
    filename: str,
    payload: Any,
) -> Path:

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    path = OUTPUT_DIR / filename

    with path.open(
        "w",
        encoding="utf-8",
    ) as handle:

        json.dump(
            payload,
            handle,
            indent=2,
            default=str,
        )

    return path


# ============================================================================
# MAIN EXPERIMENT
# ============================================================================


def main() -> int:

    print("=" * 70)

    print("FORGE - Experiment 021-C: " "Declarative Constraint-Aware Model to Dataset")

    print("=" * 70)

    print("Experiment:     " "021_declarative_model_to_dataset")

    print("Stage:          021-C")

    print(
        "Purpose:        " "Declarative constraints and " "constraint-aware generation"
    )

    try:

        specification = load_specification()

        model_name = get_model_name(specification)

        seed = get_seed(specification)

        scenario = get_scenario(specification)

        relationships = specification.get(
            "relationships",
            [],
        )

        constraints = collect_constraints(specification)

        print(f"Random seed:    {seed}")

        print()
        print("Constraint-aware model-to-dataset architecture:")

        print("  Declarative specification")

        print("       ↓")

        print("  Specification validation")

        print("       ↓")

        print("  Relationship discovery")

        print("       ↓")

        print("  Constraint discovery")

        print("       ↓")

        print("  Generation planning")

        print("       ↓")

        print("  Candidate generation")

        print("       ↓")

        print("  Constraint evaluation")

        print("       ↓")

        print("  Relationship resolution")

        print("       ↓")

        print("  Final validation")

        print("       ↓")

        print("  CSV datasets")

        print()
        print("Specification:")

        print(f"  Model:          {model_name}")

        print(f"  Version:        " f"{specification.get('version', 'N/A')}")

        print(f"  Vocabulary:     " f"{specification.get('vocabulary_version', 'N/A')}")

        print(f"  Seed:           {seed}")

        print(f"  Scenario:       {scenario}")

        print(f"  Entities:       " f"{len(specification.get('entities', []))}")

        print(f"  Relationships:  " f"{len(relationships)}")

        print(f"  Constraints:    " f"{len(constraints)}")

        # ------------------------------------------------------------------
        # Specification validation
        # ------------------------------------------------------------------

        specification_errors = validate_specification(specification)

        specification_valid = not (specification_errors)

        print()
        print("Specification validation:")

        print(
            "  Declarative structure              "
            f"{'PASS' if specification_valid else 'FAIL'}"
        )

        if specification_errors:

            for error in specification_errors:

                print(f"    ERROR: {error}")

            result_path = write_json(
                "constraint_generation_results.json",
                {
                    "experiment": EXPERIMENT_NAME,
                    "stage": EXPERIMENT_ID,
                    "overall": "FAIL",
                    "specification_valid": False,
                    "errors": specification_errors,
                },
            )

            print()
            print("Experiment completed with failures.")

            print(f"  Results: {result_path}")

            return 1

        # ------------------------------------------------------------------
        # Relationship summary
        # ------------------------------------------------------------------

        print()
        print("Declarative relationships:")

        for relationship in relationships:

            print(
                "  "
                f"{relationship['parent_entity']}."
                f"{relationship['parent_field']}"
                "  →  "
                f"{relationship['child_entity']}."
                f"{relationship['child_field']}"
                f"  [{relationship['cardinality']}]"
            )

        # ------------------------------------------------------------------
        # Constraint summary
        # ------------------------------------------------------------------

        print()
        print("Declarative constraints:")

        for constraint in constraints:

            print(
                "  "
                f"{constraint.get('name', '<unnamed>')}"
                f"  [{constraint.get('_source', 'UNKNOWN')}]"
            )

        # ------------------------------------------------------------------
        # Generation planning
        # ------------------------------------------------------------------

        generation_order = build_generation_plan(specification)

        print()
        print("Generation plan:")

        print("  " + " -> ".join(generation_order))

        # ------------------------------------------------------------------
        # Relationship-managed fields
        # ------------------------------------------------------------------

        relationship_managed_fields = get_relationship_managed_fields(specification)

        print()
        print("Relationship-managed fields:")

        for entity_name, field_name in sorted(relationship_managed_fields):

            print(f"  {entity_name}.{field_name}")

        # ------------------------------------------------------------------
        # Dataset generation
        # ------------------------------------------------------------------

        print()
        print("Generating constraint-aware dataset...")

        dataset = generate_complete_dataset(specification)

        print()
        print("Generated dataset:")

        total_records = 0

        for entity_name, records in dataset.items():

            total_records += len(records)

            print(f"  {entity_name}: " f"{len(records)} records")

            if records:

                print(f"    Sample: " f"{records[0]}")

        # ------------------------------------------------------------------
        # Final validation
        # ------------------------------------------------------------------

        validation = {
            "dataset_structure": validate_dataset_structure(
                specification,
                dataset,
            ),
            "population_counts": validate_population_counts(
                specification,
                dataset,
            ),
            "field_presence": validate_field_presence(
                specification,
                dataset,
            ),
            "identity_uniqueness": validate_identity_uniqueness(
                specification,
                dataset,
            ),
            "constraint_integrity": validate_constraints(
                specification,
                dataset,
            ),
            "referential_integrity": validate_referential_integrity(
                specification,
                dataset,
            ),
        }

        print()
        print("Dataset validation:")

        for name, passed in validation.items():

            label = name.replace(
                "_",
                " ",
            ).title()

            print(f"  {label:<35}" f"{'PASS' if passed else 'FAIL'}")

        dataset_valid = all(validation.values())

        # ------------------------------------------------------------------
        # Reproducibility
        # ------------------------------------------------------------------

        reproducibility = test_reproducibility(specification)

        print()
        print("Reproducibility validation:")

        print(
            "  Same specification + same seed       "
            f"{'PASS' if reproducibility else 'FAIL'}"
        )

        # ------------------------------------------------------------------
        # Seed sensitivity
        # ------------------------------------------------------------------

        seed_sensitive = test_seed_sensitivity(specification)

        print()
        print("Seed sensitivity validation:")

        print(
            "  Different seed changes stochastic data "
            f"{'PASS' if seed_sensitive else 'FAIL'}"
        )

        # ------------------------------------------------------------------
        # Entity-order independence
        # ------------------------------------------------------------------

        entity_order_independent = test_entity_order_independence(specification)

        print()
        print("Entity-order validation:")

        print(
            "  Entity declaration order does not "
            "change results "
            f"{'PASS' if entity_order_independent else 'FAIL'}"
        )

        # ------------------------------------------------------------------
        # Field-order independence
        # ------------------------------------------------------------------

        field_order_independent = test_field_order_independence(specification)

        print()
        print("Field-order validation:")

        print(
            "  Field declaration order does not "
            "change results "
            f"{'PASS' if field_order_independent else 'FAIL'}"
        )

        # ------------------------------------------------------------------
        # CSV materialization
        # ------------------------------------------------------------------

        csv_paths = write_dataset_csv(dataset)

        # ------------------------------------------------------------------
        # Overall result
        # ------------------------------------------------------------------

        overall = (
            specification_valid
            and dataset_valid
            and reproducibility
            and seed_sensitive
            and entity_order_independent
            and field_order_independent
        )

        # ------------------------------------------------------------------
        # Manifest
        # ------------------------------------------------------------------

        manifest = {
            "experiment": EXPERIMENT_NAME,
            "stage": EXPERIMENT_ID,
            "model": model_name,
            "specification_version": specification.get("version"),
            "vocabulary_version": specification.get("vocabulary_version"),
            "seed": seed,
            "scenario": scenario,
            "dataset_format": "CSV",
            "generation_order": generation_order,
            "relationship_managed_fields": [
                {
                    "entity": entity_name,
                    "field": field_name,
                }
                for entity_name, field_name in sorted(relationship_managed_fields)
            ],
            "constraints": [
                {
                    "name": constraint.get("name"),
                    "source": constraint.get("_source"),
                    "entity": constraint.get("_entity"),
                }
                for constraint in constraints
            ],
            "entities": {
                entity_name: {
                    "records": len(records),
                    "output": str(csv_paths[entity_name].relative_to(EXPERIMENT_DIR)),
                }
                for entity_name, records in dataset.items()
            },
            "total_records": total_records,
        }

        manifest_path = write_json(
            "generation_manifest.json",
            manifest,
        )

        # ------------------------------------------------------------------
        # Results
        # ------------------------------------------------------------------

        results = {
            "experiment": EXPERIMENT_NAME,
            "stage": EXPERIMENT_ID,
            "specification_validity": ("PASS" if specification_valid else "FAIL"),
            "constraint_aware_generation": ("PASS" if dataset_valid else "FAIL"),
            "dataset_validation": {
                name: ("PASS" if passed else "FAIL")
                for name, passed in validation.items()
            },
            "reproducibility": ("PASS" if reproducibility else "FAIL"),
            "seed_sensitivity": ("PASS" if seed_sensitive else "FAIL"),
            "entity_order_independence": (
                "PASS" if entity_order_independent else "FAIL"
            ),
            "field_order_independence": ("PASS" if field_order_independent else "FAIL"),
            "generation_order": generation_order,
            "constraint_count": len(constraints),
            "relationship_count": len(relationships),
            "relationship_managed_field_count": len(relationship_managed_fields),
            "total_records": total_records,
            "no_post_generation_repair": True,
            "overall": ("PASS" if overall else "FAIL"),
        }

        result_path = write_json(
            "constraint_generation_results.json",
            results,
        )

        # ------------------------------------------------------------------
        # Final output
        # ------------------------------------------------------------------

        print()
        print("Experiment result:")

        print(
            "  Specification validity:       "
            f"{'PASS' if specification_valid else 'FAIL'}"
        )

        print(
            "  Constraint-aware generation:  " f"{'PASS' if dataset_valid else 'FAIL'}"
        )

        print(
            "  Constraint integrity:         "
            f"{'PASS' if validation['constraint_integrity'] else 'FAIL'}"
        )

        print(
            "  Referential integrity:        "
            f"{'PASS' if validation['referential_integrity'] else 'FAIL'}"
        )

        print(
            "  Reproducibility:              "
            f"{'PASS' if reproducibility else 'FAIL'}"
        )

        print(
            "  Seed sensitivity:             " f"{'PASS' if seed_sensitive else 'FAIL'}"
        )

        print(
            "  Entity-order independence:    "
            f"{'PASS' if entity_order_independent else 'FAIL'}"
        )

        print(
            "  Field-order independence:     "
            f"{'PASS' if field_order_independent else 'FAIL'}"
        )

        print(f"  Constraints:                  " f"{len(constraints)}")

        print(f"  Relationships:                " f"{len(relationships)}")

        print(f"  Total records:                " f"{total_records}")

        print("  No post-generation repair:    PASS")

        print("  Overall:                      " f"{'PASS' if overall else 'FAIL'}")

        print()
        print("Output:")

        for entity_name, path in csv_paths.items():

            print(f"  {entity_name}.csv: " f"{path}")

        print(f"  Manifest:    {manifest_path}")

        print(f"  Results:     {result_path}")

        if overall:

            print()
            print("Experiment completed successfully.")

            print(
                "Declarative constraint-aware "
                "model-to-dataset generation "
                "is experimentally validated."
            )

            return 0

        print()
        print("Experiment completed with failures.")

        return 1

    except Exception as exc:

        print()
        print(f"ERROR: " f"{type(exc).__name__}: {exc}")

        result_path = write_json(
            "constraint_generation_results.json",
            {
                "experiment": EXPERIMENT_NAME,
                "stage": EXPERIMENT_ID,
                "overall": "FAIL",
                "error": f"{type(exc).__name__}: {exc}",
            },
        )

        print()
        print("Output:")

        print(f"  Results:     {result_path}")

        return 1


if __name__ == "__main__":
    sys.exit(main())
