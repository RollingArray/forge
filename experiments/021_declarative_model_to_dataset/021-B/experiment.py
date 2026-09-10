"""
FORGE - Experiment 021-B: Declarative Relational Model to Dataset
==================================================================

Purpose
-------
This experiment extends 021-A by introducing declarative relationships
between generated entities.

021-A established that FORGE can:

    1. Read a declarative model.
    2. Generate multiple entity datasets.
    3. Materialize those datasets as CSV files.
    4. Validate the generated datasets.
    5. Reproduce the same dataset using the same seed.

021-B asks the next architectural question:

    Can a generic FORGE runtime use relationships declared in the
    model to generate related entity datasets while preserving
    referential integrity?

The runtime must not contain knowledge of what an entity represents.

It must interpret relationships from specification.json and use the
declared relationship metadata to resolve references.

Experiment
----------
021 - Declarative Model to Dataset

Implementation Stage
--------------------
021-B - Declarative Relationships

Key Question
------------
Can a generic FORGE runtime generate relational datasets from
declaratively defined relationships and preserve referential integrity?

Architecture
------------

    specification.json
           |
           v
    Specification Validation
           |
           v
    Entity Discovery
           |
           v
    Relationship Discovery
           |
           v
    Generation Planning
           |
           v
    Parent Entity Generation
           |
           v
    Child Entity Generation
           |
           v
    Reference Resolution
           |
           v
    Referential Integrity Validation
           |
           v
    CSV Dataset Materialization

Important Design Rule
---------------------
A field may obtain its value in one of two ways:

    1. Independent generation
       The field has its own generation or identity definition.

    2. Relationship resolution
       The field is the child side of a declared relationship.

Relationship-managed fields must not be independently generated.

The relationship definition is the source of truth for those fields.

Design Principles
-----------------
- Specification over hard-coded business logic.
- Entity names are opaque identifiers.
- Field names are opaque identifiers.
- Relationship semantics come from the specification.
- Parent entities are generated before dependent entities.
- Relationship-managed child fields are resolved from generated parent data.
- Foreign-key values must come from valid parent keys.
- Invalid references must never be silently generated.
- No entity-specific generation logic.
- No domain inference.
- No hidden fallback generation.
- No post-generation repair.
- Deterministic generation.
- Reproducible generation for a fixed seed.
- CSV is the dataset format.
- JSON is used for metadata and experiment evidence.

Scope
-----
This experiment validates the first relational model-to-dataset path.

Included
--------
- Multiple entities.
- Primary identity generation.
- Declarative parent-child relationships.
- Relationship-managed child fields.
- Required relationships.
- Parent-before-child generation.
- Reference resolution.
- Referential integrity.
- Entity population.
- CSV materialization.
- Dataset structure validation.
- Reproducibility.
- Seed sensitivity.
- Entity-order independence.
- Configuration safety.

Excluded
--------
- Many-to-many associative generation.
- Complex dependency graphs.
- Cross-field constraints.
- Conditional generation.
- Derived fields.
- Statistical relationships.
- Scenario overrides.
- Provenance.
- Conflict diagnosis.
- Large-scale performance testing.

These capabilities will be explored in later experiments.

Important
---------
The experiment must remain completely domain-neutral.

The runtime must not contain logic such as:

    if entity == "CUSTOMER":
        ...

or:

    if field == "CUSTOMER_ID":
        ...

The relationship behavior must be obtained entirely from
specification.json.

Output Structure
----------------

    021-B/
    |
    +-- experiment.py
    +-- specification.json
    +-- README-experiment-outcome.md
    |
    +-- output/
        |
        +-- dataset/
        |   +-- <ENTITY>.csv
        |   +-- <ENTITY>.csv
        |   +-- ...
        |
        +-- generation_manifest.json
        +-- relational_generation_results.json

The actual entity names are determined entirely by the specification.

Author
------
Ranjoy Sen

Status
------
Experimental

How to Run
----------
From the repository root:

    uv run python experiments/021_declarative_model_to_dataset/021-B/experiment.py

Input
-----
    experiments/021_declarative_model_to_dataset/021-B/specification.json

Output
------
    experiments/021_declarative_model_to_dataset/021-B/output/

Expected Dataset Output
-----------------------
One CSV file is produced for every entity declared in the model:

    output/dataset/<ENTITY_NAME>.csv

Expected Metadata Output
------------------------
    output/generation_manifest.json
    output/relational_generation_results.json

Architectural Outcome
---------------------
021-B should demonstrate that FORGE can move from:

    Independent entity generation

to:

    Model-driven relational dataset generation

without introducing domain-specific generation code.
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

EXPERIMENT_ID = "021-B"
EXPERIMENT_NAME = "021_declarative_model_to_dataset"

EXPERIMENT_DIR = Path(__file__).resolve().parent

SPECIFICATION_FILE = EXPERIMENT_DIR / "specification.json"

OUTPUT_DIR = EXPERIMENT_DIR / "output"

DATASET_DIR = OUTPUT_DIR / "dataset"


# ============================================================================
# SPECIFICATION LOADING
# ============================================================================


def load_specification(
    path: Path = SPECIFICATION_FILE,
) -> dict[str, Any]:
    """Load the declarative relational model."""

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

    if not isinstance(
        generation,
        dict,
    ):
        raise ValueError("Generation configuration must be an object.")

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


def build_entity_map(
    specification: dict[str, Any],
) -> dict[str, dict[str, Any]]:

    return {entity["name"]: entity for entity in specification["entities"]}


def build_field_map(
    entity: dict[str, Any],
) -> dict[str, dict[str, Any]]:

    return {field["name"]: field for field in entity["fields"]}


# ============================================================================
# SPECIFICATION VALIDATION
# ============================================================================


def validate_specification(
    specification: dict[str, Any],
) -> list[str]:
    """
    Validate the declarative model required by this experiment.
    """

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
        errors.append("Specification must contain at least one entity.")
        return errors

    entity_names: set[str] = set()

    for entity_index, entity in enumerate(entities):

        prefix = f"entities[{entity_index}]"

        if not isinstance(
            entity,
            dict,
        ):
            errors.append(f"{prefix} must be an object.")
            continue

        entity_name = entity.get("name")

        if (
            not isinstance(
                entity_name,
                str,
            )
            or not entity_name
        ):
            errors.append(f"{prefix} must define a non-empty name.")
            continue

        if entity_name in entity_names:
            errors.append(f"Duplicate entity name: {entity_name!r}.")

        entity_names.add(entity_name)

        try:
            get_population_count(entity)
        except ValueError as exc:
            errors.append(str(exc))

        fields = entity.get("fields")

        if (
            not isinstance(
                fields,
                list,
            )
            or not fields
        ):
            errors.append(f"Entity {entity_name!r} " "must contain fields.")
            continue

        field_names: set[str] = set()

        for field_index, field in enumerate(fields):

            field_prefix = f"{entity_name}.fields[{field_index}]"

            if not isinstance(
                field,
                dict,
            ):
                errors.append(f"{field_prefix} must be an object.")
                continue

            field_name = field.get("name")

            if (
                not isinstance(
                    field_name,
                    str,
                )
                or not field_name
            ):
                errors.append(f"{field_prefix} must define " "a non-empty name.")
                continue

            if field_name in field_names:
                errors.append(f"Duplicate field name " f"{entity_name}.{field_name}.")

            field_names.add(field_name)

            if not isinstance(
                field.get("type"),
                str,
            ):
                errors.append(f"{entity_name}.{field_name} " "must define a type.")

    # ------------------------------------------------------------------------
    # Relationship validation
    # ------------------------------------------------------------------------

    relationships = specification.get(
        "relationships",
        [],
    )

    if not isinstance(
        relationships,
        list,
    ):
        errors.append("Relationships must be a list.")
        return errors

    entity_map = build_entity_map(specification)

    relationship_names: set[str] = set()

    for relationship_index, relationship in enumerate(relationships):

        prefix = f"relationships[{relationship_index}]"

        if not isinstance(
            relationship,
            dict,
        ):
            errors.append(f"{prefix} must be an object.")
            continue

        relationship_name = relationship.get("name")

        if relationship_name:

            if relationship_name in relationship_names:
                errors.append(
                    f"Duplicate relationship name: " f"{relationship_name!r}."
                )

            relationship_names.add(relationship_name)

        parent_entity = relationship.get("parent_entity")

        child_entity = relationship.get("child_entity")

        parent_field = relationship.get("parent_field")

        child_field = relationship.get("child_field")

        if parent_entity not in entity_map:
            errors.append(
                f"{prefix} references unknown " f"parent entity {parent_entity!r}."
            )
            continue

        if child_entity not in entity_map:
            errors.append(
                f"{prefix} references unknown " f"child entity {child_entity!r}."
            )
            continue

        parent_fields = build_field_map(entity_map[parent_entity])

        child_fields = build_field_map(entity_map[child_entity])

        if parent_field not in parent_fields:
            errors.append(
                f"{prefix} references unknown parent field "
                f"{parent_entity}.{parent_field}."
            )

        if child_field not in child_fields:
            errors.append(
                f"{prefix} references unknown child field "
                f"{child_entity}.{child_field}."
            )

        cardinality = relationship.get("cardinality")

        if cardinality not in {
            "1:1",
            "0:1",
            "1:N",
            "0:N",
        }:
            errors.append(f"{prefix} has unsupported " f"cardinality {cardinality!r}.")

        if not isinstance(
            relationship.get("required"),
            bool,
        ):
            errors.append(f"{prefix} must define boolean 'required'.")

    return errors


# ============================================================================
# DETERMINISTIC FIELD STREAMS
# ============================================================================


def derive_field_seed(
    master_seed: int,
    entity_name: str,
    field_name: str,
) -> int:

    namespace = f"FIELD:{entity_name}:{field_name}"

    digest = hashlib.sha256((f"{master_seed}:{namespace}").encode("utf-8")).digest()

    return int.from_bytes(
        digest[:8],
        "big",
    )


# ============================================================================
# IDENTITY GENERATION
# ============================================================================


def generate_identity_values(
    entity_name: str,
    field: dict[str, Any],
    record_count: int,
) -> list[Any]:

    field_name = field["name"]

    identity = field.get("identity")

    if not isinstance(
        identity,
        dict,
    ):
        raise ValueError(
            f"{entity_name}.{field_name} " "has invalid identity metadata."
        )

    strategy = identity.get("strategy")

    if strategy != "SEQUENTIAL_ID":
        raise ValueError(
            f"Unsupported identity strategy "
            f"{strategy!r} for "
            f"{entity_name}.{field_name}."
        )

    prefix = identity.get(
        "prefix",
        "",
    )

    start = identity.get(
        "start",
        1,
    )

    return [
        f"{prefix}{index}"
        for index in range(
            start,
            start + record_count,
        )
    ]


# ============================================================================
# RANDOM FIELD GENERATION
# ============================================================================


def generate_random_values(
    entity_name: str,
    field: dict[str, Any],
    record_count: int,
    master_seed: int,
) -> list[Any]:

    field_name = field["name"]

    generation = field.get("generation")

    if not isinstance(
        generation,
        dict,
    ):
        raise ValueError(
            f"{entity_name}.{field_name} " "has invalid generation metadata."
        )

    strategy = generation.get("strategy")

    if strategy != "RANDOM":
        raise ValueError(
            f"Unsupported generation strategy "
            f"{strategy!r} for "
            f"{entity_name}.{field_name}."
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
            field_name,
        )
    )

    if distribution == "UNIFORM":

        minimum = parameters.get("minimum")

        maximum = parameters.get("maximum")

        if minimum is None or maximum is None:
            raise ValueError(
                f"{entity_name}.{field_name} "
                "UNIFORM generation requires "
                "minimum and maximum."
            )

        if minimum > maximum:
            raise ValueError(
                f"{entity_name}.{field_name} " "has minimum greater than maximum."
            )

        values = [
            rng.uniform(
                minimum,
                maximum,
            )
            for _ in range(record_count)
        ]

        if field.get("type") in {
            "DECIMAL",
            "CURRENCY",
            "PERCENTAGE",
        }:

            precision = parameters.get(
                "precision",
                2,
            )

            values = [
                round(
                    value,
                    precision,
                )
                for value in values
            ]

        return values

    if distribution == "DISCRETE_UNIFORM":

        minimum = parameters.get("minimum")

        maximum = parameters.get("maximum")

        if not isinstance(
            minimum,
            int,
        ) or not isinstance(
            maximum,
            int,
        ):
            raise ValueError(
                f"{entity_name}.{field_name} "
                "DISCRETE_UNIFORM requires "
                "integer bounds."
            )

        return [
            rng.randint(
                minimum,
                maximum,
            )
            for _ in range(record_count)
        ]

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
                f"{entity_name}.{field_name} "
                "CATEGORICAL generation requires "
                "a non-empty values list."
            )

        if weights is not None:

            if not isinstance(
                weights,
                list,
            ) or len(
                weights
            ) != len(values):
                raise ValueError(
                    f"{entity_name}.{field_name} "
                    "categorical weights must match "
                    "the values."
                )

        return rng.choices(
            values,
            weights=weights,
            k=record_count,
        )

    raise ValueError(
        f"Unsupported distribution "
        f"{distribution!r} for "
        f"{entity_name}.{field_name}."
    )


# ============================================================================
# GENERIC FIELD GENERATION
# ============================================================================


def generate_field_values(
    entity_name: str,
    field: dict[str, Any],
    record_count: int,
    master_seed: int,
) -> list[Any]:

    if "identity" in field:

        return generate_identity_values(
            entity_name,
            field,
            record_count,
        )

    if "generation" in field:

        return generate_random_values(
            entity_name,
            field,
            record_count,
            master_seed,
        )

    raise ValueError(
        f"No executable generation behavior "
        f"declared for "
        f"{entity_name}.{field['name']}."
    )


# ============================================================================
# RELATIONSHIP-MANAGED FIELD DISCOVERY
# ============================================================================


def get_relationship_managed_fields(
    specification: dict[str, Any],
) -> set[tuple[str, str]]:
    """
    Return all fields whose values are supplied by a relationship.

    Each tuple contains:

        (child_entity, child_field)

    These fields must not be independently generated.
    """

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
    """
    Build a generic parent-before-child generation order.

    The plan is derived entirely from relationships.

    No entity name is treated specially.
    """

    entities = [entity["name"] for entity in specification["entities"]]

    relationships = specification.get(
        "relationships",
        [],
    )

    dependencies: dict[
        str,
        set[str],
    ] = {entity_name: set() for entity_name in entities}

    for relationship in relationships:

        parent = relationship["parent_entity"]

        child = relationship["child_entity"]

        dependencies[child].add(parent)

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
                "Generation planning failed: "
                "relationship dependencies contain "
                "a cycle."
            )

        ordered.extend(ready)

        remaining.difference_update(ready)

    return ordered


# ============================================================================
# GENERIC ENTITY GENERATION
# ============================================================================


def generate_independent_entity(
    entity: dict[str, Any],
    master_seed: int,
    relationship_managed_fields: set[tuple[str, str]],
) -> list[dict[str, Any]]:
    """
    Generate all fields that have independent generation behavior.

    Fields managed by relationships are deliberately skipped.

    This is the critical distinction introduced by 021-B:

        Independent field
            -> generate directly

        Relationship-managed field
            -> resolve later from parent dataset
    """

    entity_name = entity["name"]

    record_count = get_population_count(entity)

    generated_columns: dict[
        str,
        list[Any],
    ] = {}

    for field in entity["fields"]:

        field_name = field["name"]

        if (
            entity_name,
            field_name,
        ) in relationship_managed_fields:

            continue

        generated_columns[field_name] = generate_field_values(
            entity_name,
            field,
            record_count,
            master_seed,
        )

    records: list[dict[str, Any]] = []

    for index in range(record_count):

        records.append(
            {
                field_name: generated_columns[field_name][index]
                for field_name in generated_columns
            }
        )

    return records


# ============================================================================
# RELATIONSHIP RESOLUTION
# ============================================================================


def resolve_relationship_field(
    child_entity: dict[str, Any],
    child_records: list[dict[str, Any]],
    relationship: dict[str, Any],
    parent_records: list[dict[str, Any]],
    master_seed: int,
) -> None:
    """
    Populate a child relationship field from valid parent records.

    Relationship semantics are read entirely from the specification.

    No knowledge of the domain is required.
    """

    child_entity_name = child_entity["name"]

    child_field = relationship["child_field"]

    parent_field = relationship["parent_field"]

    cardinality = relationship["cardinality"]

    required = relationship["required"]

    if not parent_records:

        if required:

            raise ValueError(
                f"Required relationship for "
                f"{child_entity_name}.{child_field} "
                "cannot be resolved because the "
                "parent dataset contains no records."
            )

        for record in child_records:

            record[child_field] = None

        return

    parent_values = [record[parent_field] for record in parent_records]

    if not parent_values:

        if required:

            raise ValueError(
                f"Required relationship for "
                f"{child_entity_name}.{child_field} "
                "has no valid parent values."
            )

        for record in child_records:

            record[child_field] = None

        return

    field_seed = derive_field_seed(
        master_seed,
        child_entity_name,
        child_field,
    )

    rng = random.Random(field_seed)

    optional = (
        cardinality
        in {
            "0:1",
            "0:N",
        }
        or not required
    )

    for record in child_records:

        if optional:

            use_reference = rng.random() >= 0.20

            if not use_reference:

                record[child_field] = None

                continue

        record[child_field] = rng.choice(parent_values)


# ============================================================================
# DATASET GENERATION
# ============================================================================


def generate_dataset(
    specification: dict[str, Any],
) -> dict[
    str,
    list[dict[str, Any]],
]:

    master_seed = get_seed(specification)

    entity_map = build_entity_map(specification)

    relationships = specification.get(
        "relationships",
        [],
    )

    relationship_managed_fields = get_relationship_managed_fields(specification)

    generation_order = build_generation_plan(specification)

    dataset: dict[
        str,
        list[dict[str, Any]],
    ] = {}

    for entity_name in generation_order:

        entity = entity_map[entity_name]

        records = generate_independent_entity(
            entity,
            master_seed,
            relationship_managed_fields,
        )

        dataset[entity_name] = records

        # --------------------------------------------------------------
        # Resolve all relationships for which this entity is the child.
        # --------------------------------------------------------------

        for relationship in relationships:

            if relationship["child_entity"] != entity_name:
                continue

            parent_entity_name = relationship["parent_entity"]

            parent_records = dataset.get(parent_entity_name)

            if parent_records is None:
                raise ValueError(
                    f"Parent entity "
                    f"{parent_entity_name!r} "
                    "has not been generated."
                )

            resolve_relationship_field(
                entity,
                records,
                relationship,
                parent_records,
                master_seed,
            )

    return dataset


# ============================================================================
# DATASET VALIDATION
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

        if len(
            dataset.get(
                entity_name,
                [],
            )
        ) != get_population_count(entity):
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

        expected = {field["name"] for field in entity["fields"]}

        for record in dataset[entity_name]:

            if set(record) != expected:
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


def validate_referential_integrity(
    specification: dict[str, Any],
    dataset: dict[
        str,
        list[dict[str, Any]],
    ],
) -> bool:
    """
    Verify that every relationship reference points to an existing
    parent value.

    Required relationships cannot contain null references.

    Optional relationships may contain null references.
    """

    for relationship in specification.get(
        "relationships",
        [],
    ):

        parent_entity = relationship["parent_entity"]

        child_entity = relationship["child_entity"]

        parent_field = relationship["parent_field"]

        child_field = relationship["child_field"]

        required = relationship["required"]

        parent_values = {record[parent_field] for record in dataset[parent_entity]}

        for child_record in dataset[child_entity]:

            if child_field not in child_record:
                return False

            value = child_record[child_field]

            if value is None:

                if required:
                    return False

                continue

            if value not in parent_values:
                return False

    return True


def validate_relationship_configuration(
    specification: dict[str, Any],
) -> bool:
    """
    Validate that every relationship points to real entities and fields.
    """

    entity_map = build_entity_map(specification)

    for relationship in specification.get(
        "relationships",
        [],
    ):

        parent_entity = relationship["parent_entity"]

        child_entity = relationship["child_entity"]

        parent_field = relationship["parent_field"]

        child_field = relationship["child_field"]

        if parent_entity not in entity_map:
            return False

        if child_entity not in entity_map:
            return False

        parent_fields = build_field_map(entity_map[parent_entity])

        child_fields = build_field_map(entity_map[child_entity])

        if parent_field not in parent_fields:
            return False

        if child_field not in child_fields:
            return False

    return True


# ============================================================================
# DETERMINISM VALIDATION
# ============================================================================


def test_reproducibility(
    specification: dict[str, Any],
) -> bool:

    first = generate_dataset(specification)

    second = generate_dataset(specification)

    return first == second


def test_seed_sensitivity(
    specification: dict[str, Any],
) -> bool:

    first = generate_dataset(specification)

    alternate = copy.deepcopy(specification)

    alternate["generation"]["seed"] = get_seed(specification) + 1

    second = generate_dataset(alternate)

    return first != second


def test_entity_order_independence(
    specification: dict[str, Any],
) -> bool:

    first = generate_dataset(specification)

    alternate = copy.deepcopy(specification)

    alternate["entities"] = list(reversed(alternate["entities"]))

    second = generate_dataset(alternate)

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

    if records:

        fieldnames = list(records[0].keys())

    else:

        fieldnames = []

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

    paths: dict[
        str,
        Path,
    ] = {}

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

    print("FORGE - Experiment 021-B: " "Declarative Relational Model to Dataset")

    print("=" * 70)

    print("Experiment:     " "021_declarative_model_to_dataset")

    print("Stage:          021-B")

    print("Purpose:        " "Declarative relationships and " "referential integrity")

    try:

        specification = load_specification()

        model_name = get_model_name(specification)

        seed = get_seed(specification)

        scenario = get_scenario(specification)

        relationships = specification.get(
            "relationships",
            [],
        )

        print(f"Random seed:    {seed}")

        print()
        print("Relational model-to-dataset architecture:")
        print("  Declarative specification")
        print("       ↓")
        print("  Specification validation")
        print("       ↓")
        print("  Relationship discovery")
        print("       ↓")
        print("  Generation planning")
        print("       ↓")
        print("  Parent generation")
        print("       ↓")
        print("  Child generation")
        print("       ↓")
        print("  Reference resolution")
        print("       ↓")
        print("  Referential integrity validation")
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

            results = {
                "experiment": EXPERIMENT_NAME,
                "stage": EXPERIMENT_ID,
                "overall": "FAIL",
                "specification_valid": False,
                "errors": specification_errors,
            }

            result_path = write_json(
                "relational_generation_results.json",
                results,
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
        print("Generating relational dataset...")

        dataset = generate_dataset(specification)

        print()
        print("Generated dataset:")

        total_records = 0

        for entity_name, records in dataset.items():

            total_records += len(records)

            print(f"  {entity_name}: " f"{len(records)} records")

            if records:

                print(f"    Sample: " f"{records[0]}")

        # ------------------------------------------------------------------
        # Dataset validation
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
            "relationship_configuration": validate_relationship_configuration(
                specification,
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
        )

        # ------------------------------------------------------------------
        # Generation manifest
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
            "relationships": relationships,
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
            "relational_generation": ("PASS" if dataset_valid else "FAIL"),
            "dataset_validation": {
                name: ("PASS" if passed else "FAIL")
                for name, passed in validation.items()
            },
            "reproducibility": ("PASS" if reproducibility else "FAIL"),
            "seed_sensitivity": ("PASS" if seed_sensitive else "FAIL"),
            "entity_order_independence": (
                "PASS" if entity_order_independent else "FAIL"
            ),
            "generation_order": generation_order,
            "relationship_count": len(relationships),
            "relationship_managed_field_count": len(relationship_managed_fields),
            "total_records": total_records,
            "overall": ("PASS" if overall else "FAIL"),
        }

        result_path = write_json(
            "relational_generation_results.json",
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
            "  Relational generation:        " f"{'PASS' if dataset_valid else 'FAIL'}"
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

        print(f"  Relationships:                " f"{len(relationships)}")

        print(f"  Relationship-managed fields:  " f"{len(relationship_managed_fields)}")

        print(f"  Total records:                " f"{total_records}")

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
                "Declarative relational model-to-dataset "
                "generation is experimentally validated."
            )

            return 0

        print()
        print("Experiment completed with failures.")

        return 1

    except Exception as exc:

        print()
        print(f"ERROR: " f"{type(exc).__name__}: {exc}")

        result_path = write_json(
            "relational_generation_results.json",
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
