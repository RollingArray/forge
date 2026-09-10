"""
FORGE - Experiment 021-A: Declarative Model to Dataset
=======================================================

Purpose
-------
This experiment validates the first complete FORGE path from a
declarative model to an actual dataset.

Experiment 020 established that FORGE can understand and validate a
declarative generation specification.

Experiment 021-A takes the next step:

    A declarative model
            |
            v
    Generic FORGE runtime
            |
            v
    Generated relational dataset

The experiment intentionally uses a small model containing multiple
entities and fields.

No entity-specific generation logic is used.

The runtime does not know what CUSTOMER, PRODUCT, or any other entity
means. It only interprets the metadata contained in specification.json.

The generated dataset is materialized as one CSV file per entity.

Experiment
----------
021 - Declarative Model to Dataset

Implementation Stage
--------------------
021-A - Basic Model to Dataset

Key Question
------------
Can a generic FORGE runtime take a declarative model and materialize
that model into actual entity datasets without containing domain-specific
generation logic?

Architecture
------------

    specification.json
           |
           v
    Specification Validation
           |
           v
    Generation Planning
           |
           v
    Generic Field Generation
           |
           v
    Record Construction
           |
           v
    Entity Dataset Materialization
           |
           v
    CSV Output
           |
           v
    Dataset Validation

Design Principles
-----------------
- Specification over hard-coded business logic.
- Entity names are opaque identifiers.
- Field names are opaque identifiers.
- Generation behavior comes from declarative metadata.
- Generic iteration over entities and fields.
- Deterministic field-level random streams.
- Same specification + same seed produces the same dataset.
- Different seeds affect stochastic fields.
- One entity is materialized as one dataset.
- Dataset output is CSV.
- Metadata and experiment evidence remain JSON.
- No domain inference.
- No machine learning.
- No LLM.
- No real production data.
- No hidden generation fallback.

Scope
-----
This stage validates the simplest complete path from a declarative
model to actual entity datasets.

Included
--------
- Multiple entities.
- Multiple fields per entity.
- Population counts.
- Sequential identity generation.
- Random numeric generation.
- Categorical generation.
- Boolean categorical generation.
- CSV dataset materialization.
- Dataset structure validation.
- Population count validation.
- Field presence validation.
- Identity uniqueness validation.
- Declared range validation.
- Categorical value validation.
- Reproducibility.
- Seed sensitivity.

Excluded
--------
- Foreign-key resolution.
- Relationships.
- Cross-field constraints.
- Conditional generation.
- Derived fields.
- Statistical relationships.
- Scenarios.
- Provenance.
- Conflict diagnosis.
- Large-scale performance testing.

These capabilities will be introduced incrementally in later
Experiment 021 stages.

Output Structure
----------------

    021-A/
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
        +-- model_to_dataset_results.json

The entity names shown in the output are determined entirely by the
specification.

The runtime does not contain hard-coded entity names.

Important
---------
The CSV files are the generated datasets.

JSON is used only for structured metadata and experiment evidence:

    specification.json
        Describes what should be generated.

    generation_manifest.json
        Describes what was generated and with which configuration.

    model_to_dataset_results.json
        Records validation and experiment results.

The experiment therefore establishes an important FORGE separation:

    Specification
        describes the model

    Runtime
        interprets the model

    Dataset
        materializes the model

Author
------
Ranjoy Sen

Status
------
Experimental

How to Run
----------
From the repository root:

    uv run python experiments/021_declarative_model_to_dataset/021-A/experiment.py

Input
-----
    experiments/021_declarative_model_to_dataset/021-A/specification.json

Output
------
    experiments/021_declarative_model_to_dataset/021-A/output/

Expected Dataset Output
-----------------------
Each entity defined in specification.json produces one CSV file:

    output/dataset/<ENTITY_NAME>.csv

Expected Metadata Output
------------------------
    output/generation_manifest.json
    output/model_to_dataset_results.json
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

# ----------------------------------------------------------------------
# Experiment configuration
# ----------------------------------------------------------------------

EXPERIMENT_ID = "021-A"
EXPERIMENT_NAME = "021_declarative_model_to_dataset"

EXPERIMENT_DIR = Path(__file__).resolve().parent

SPECIFICATION_FILE = EXPERIMENT_DIR / "specification.json"

OUTPUT_DIR = EXPERIMENT_DIR / "output"

DATASET_DIR = OUTPUT_DIR / "dataset"


# ----------------------------------------------------------------------
# Specification loading
# ----------------------------------------------------------------------


def load_specification(
    path: Path = SPECIFICATION_FILE,
) -> dict[str, Any]:
    """
    Load the declarative model from specification.json.
    """

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


# ----------------------------------------------------------------------
# Specification helpers
# ----------------------------------------------------------------------


def get_model_name(
    specification: dict[str, Any],
) -> str:
    """
    Resolve the model name without interpreting its domain.
    """

    model = specification.get("model")

    if isinstance(model, str):
        return model

    if isinstance(model, dict):
        name = model.get("name")

        if isinstance(name, str) and name:
            return name

    raise ValueError("Specification must define a model name.")


def get_seed(
    specification: dict[str, Any],
) -> int:
    """
    Resolve the master generation seed.
    """

    generation = specification.get(
        "generation",
        {},
    )

    seed = generation.get(
        "seed",
        specification.get("seed"),
    )

    if not isinstance(
        seed,
        int,
    ):
        raise ValueError("Specification must define an integer seed.")

    return seed


def get_scenario(
    specification: dict[str, Any],
) -> str:
    """
    Resolve the active generation scenario.
    """

    generation = specification.get(
        "generation",
        {},
    )

    scenario = generation.get(
        "scenario",
        specification.get(
            "scenario",
            "NORMAL",
        ),
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
    """
    Resolve the population count declared for an entity.
    """

    population = entity.get("population")

    if isinstance(
        population,
        int,
    ):
        count = population

    elif isinstance(
        population,
        dict,
    ):
        count = population.get("count")

    else:
        count = None

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


# ----------------------------------------------------------------------
# Basic specification validation
# ----------------------------------------------------------------------


def validate_specification(
    specification: dict[str, Any],
) -> list[str]:
    """
    Validate only the model capabilities required by 021-A.

    The validation is intentionally generic. It does not know anything
    about the meaning of individual entity or field names.
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
        errors.append("Specification must contain " "at least one entity.")

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
            errors.append(f"{prefix} must define a " "non-empty name.")

            continue

        if entity_name in entity_names:
            errors.append(f"Duplicate entity name: " f"{entity_name!r}.")

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
            field_prefix = f"{entity_name}.fields" f"[{field_index}]"

            if not isinstance(
                field,
                dict,
            ):
                errors.append(f"{field_prefix} " "must be an object.")

                continue

            field_name = field.get("name")

            field_type = field.get("type")

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

            if (
                not isinstance(
                    field_type,
                    str,
                )
                or not field_type
            ):
                errors.append(f"{entity_name}.{field_name} " "must define a type.")

            if "identity" not in field and "generation" not in field:
                errors.append(
                    f"{entity_name}.{field_name} "
                    "must define either identity "
                    "or generation metadata."
                )

    return errors


# ----------------------------------------------------------------------
# Deterministic random stream
# ----------------------------------------------------------------------


def derive_field_seed(
    master_seed: int,
    entity_name: str,
    field_name: str,
) -> int:
    """
    Derive a deterministic independent random stream for a field.

    The stream depends on:

        master seed
        entity name
        field name

    It does not depend on field declaration order.
    """

    namespace = f"FIELD:{entity_name}:{field_name}"

    digest = hashlib.sha256((f"{master_seed}:{namespace}").encode("utf-8")).digest()

    return int.from_bytes(
        digest[:8],
        "big",
    )


# ----------------------------------------------------------------------
# Identity generation
# ----------------------------------------------------------------------


def generate_identity_values(
    entity_name: str,
    field: dict[str, Any],
    record_count: int,
) -> list[Any]:
    """
    Generate sequential identity values from metadata.
    """

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

    if not isinstance(
        start,
        int,
    ):
        raise ValueError(
            f"{entity_name}.{field_name} " "identity start must be an integer."
        )

    return [
        f"{prefix}{index}"
        for index in range(
            start,
            start + record_count,
        )
    ]


# ----------------------------------------------------------------------
# Random generation
# ----------------------------------------------------------------------


def generate_random_values(
    entity_name: str,
    field: dict[str, Any],
    record_count: int,
    master_seed: int,
) -> list[Any]:
    """
    Generate field values from declarative metadata.
    """

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

    if not isinstance(
        parameters,
        dict,
    ):
        raise ValueError(
            f"{entity_name}.{field_name} " "generation parameters must be an object."
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

        field_type = field.get("type")

        if field_type in {
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
                "integer minimum and maximum."
            )

        if minimum > maximum:
            raise ValueError(
                f"{entity_name}.{field_name} " "has minimum greater than maximum."
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
                    "the number of values."
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


# ----------------------------------------------------------------------
# Generic field generation
# ----------------------------------------------------------------------


def generate_field_values(
    entity_name: str,
    field: dict[str, Any],
    record_count: int,
    master_seed: int,
) -> list[Any]:
    """
    Generate one field using only its declarative metadata.
    """

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


# ----------------------------------------------------------------------
# Entity generation
# ----------------------------------------------------------------------


def generate_entity(
    entity: dict[str, Any],
    master_seed: int,
) -> list[dict[str, Any]]:
    """
    Generate one entity without knowing anything about its domain.
    """

    entity_name = entity["name"]

    record_count = get_population_count(entity)

    fields = entity["fields"]

    generated_columns: dict[
        str,
        list[Any],
    ] = {}

    for field in fields:

        generated_columns[field["name"]] = generate_field_values(
            entity_name,
            field,
            record_count,
            master_seed,
        )

    records: list[dict[str, Any]] = []

    for record_index in range(record_count):

        record = {
            field["name"]: generated_columns[field["name"]][record_index]
            for field in fields
        }

        records.append(record)

    return records


# ----------------------------------------------------------------------
# Dataset generation
# ----------------------------------------------------------------------


def generate_dataset(
    specification: dict[str, Any],
) -> dict[
    str,
    list[dict[str, Any]],
]:
    """
    Generate every entity declared in the specification.

    There is intentionally no entity-specific branching here.
    """

    master_seed = get_seed(specification)

    dataset: dict[
        str,
        list[dict[str, Any]],
    ] = {}

    for entity in specification["entities"]:

        entity_name = entity["name"]

        dataset[entity_name] = generate_entity(
            entity,
            master_seed,
        )

    return dataset


# ----------------------------------------------------------------------
# Dataset validation
# ----------------------------------------------------------------------


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

        expected_count = get_population_count(entity)

        if (
            len(
                dataset.get(
                    entity_name,
                    [],
                )
            )
            != expected_count
        ):
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


def validate_declared_ranges(
    specification: dict[str, Any],
    dataset: dict[
        str,
        list[dict[str, Any]],
    ],
) -> bool:

    for entity in specification["entities"]:

        entity_name = entity["name"]

        for field in entity["fields"]:

            generation = field.get(
                "generation",
                {},
            )

            distribution = generation.get("distribution")

            if distribution not in {
                "UNIFORM",
                "DISCRETE_UNIFORM",
            }:
                continue

            parameters = generation.get(
                "parameters",
                {},
            )

            minimum = parameters.get("minimum")

            maximum = parameters.get("maximum")

            if minimum is None or maximum is None:
                continue

            for record in dataset[entity_name]:

                value = record[field["name"]]

                if value < minimum or value > maximum:
                    return False

    return True


def validate_categorical_values(
    specification: dict[str, Any],
    dataset: dict[
        str,
        list[dict[str, Any]],
    ],
) -> bool:

    for entity in specification["entities"]:

        entity_name = entity["name"]

        for field in entity["fields"]:

            generation = field.get(
                "generation",
                {},
            )

            if generation.get("distribution") != "CATEGORICAL":
                continue

            allowed_values = set(
                generation.get(
                    "parameters",
                    {},
                ).get(
                    "values",
                    [],
                )
            )

            for record in dataset[entity_name]:

                if record[field["name"]] not in allowed_values:
                    return False

    return True


# ----------------------------------------------------------------------
# Reproducibility
# ----------------------------------------------------------------------


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

    generation = alternate.setdefault(
        "generation",
        {},
    )

    generation["seed"] = get_seed(specification) + 1

    second = generate_dataset(alternate)

    return first != second


# ----------------------------------------------------------------------
# CSV materialization
# ----------------------------------------------------------------------


def write_entity_csv(
    entity_name: str,
    records: list[dict[str, Any]],
) -> Path:
    """
    Materialize one entity as one CSV dataset.

    The CSV column order follows the record structure generated from
    the declarative field order.
    """

    DATASET_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    path = DATASET_DIR / f"{entity_name}.csv"

    fieldnames: list[str] = []

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
    """
    Materialize every entity in the dataset.
    """

    paths: dict[str, Path] = {}

    for entity_name, records in dataset.items():

        paths[entity_name] = write_entity_csv(
            entity_name,
            records,
        )

    return paths


# ----------------------------------------------------------------------
# JSON output helpers
# ----------------------------------------------------------------------


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


# ----------------------------------------------------------------------
# Main experiment
# ----------------------------------------------------------------------


def main() -> int:

    print("=" * 70)

    print("FORGE - Experiment 021-A: " "Declarative Model to Dataset")

    print("=" * 70)

    print("Experiment:     " "021_declarative_model_to_dataset")

    print("Stage:          021-A")

    print("Purpose:        " "Declarative model to actual dataset")

    try:

        specification = load_specification()

        model_name = get_model_name(specification)

        seed = get_seed(specification)

        scenario = get_scenario(specification)

        print(f"Random seed:    {seed}")

        print()
        print("Model-to-dataset architecture:")
        print("  Declarative specification")
        print("       ↓")
        print("  Specification validation")
        print("       ↓")
        print("  Generation planning")
        print("       ↓")
        print("  Declarative field generation")
        print("       ↓")
        print("  Dataset materialization")
        print("       ↓")
        print("  CSV dataset validation")

        print()
        print("Specification:")

        print(f"  Model:          {model_name}")

        print(f"  Version:        " f"{specification.get('version', 'N/A')}")

        print(f"  Vocabulary:     " f"{specification.get('vocabulary_version', 'N/A')}")

        print(f"  Seed:           {seed}")

        print(f"  Scenario:       {scenario}")

        print(f"  Entities:       " f"{len(specification.get('entities', []))}")

        # --------------------------------------------------------------
        # Specification validation
        # --------------------------------------------------------------

        validation_errors = validate_specification(specification)

        specification_valid = len(validation_errors) == 0

        print()
        print("Specification validation:")

        print(
            "  Declarative structure              "
            f"{'PASS' if specification_valid else 'FAIL'}"
        )

        if validation_errors:

            for error in validation_errors:
                print(f"    ERROR: {error}")

            result_path = write_json(
                "model_to_dataset_results.json",
                {
                    "experiment": EXPERIMENT_NAME,
                    "stage": EXPERIMENT_ID,
                    "specification_validity": "FAIL",
                    "dataset_generation": "BLOCKED",
                    "overall": "FAIL",
                    "errors": validation_errors,
                },
            )

            print()
            print("Experiment result:")
            print("  Specification validity:       FAIL")
            print("  Dataset generation:           BLOCKED")
            print("  Overall:                      FAIL")

            print()
            print("Output:")
            print(f"  Results:     {result_path}")

            return 1

        # --------------------------------------------------------------
        # Generation plan
        # --------------------------------------------------------------

        print()
        print("Generation plan:")

        for entity in specification["entities"]:

            print(
                f"  {entity['name']}: "
                f"{get_population_count(entity)} "
                f"records, "
                f"{len(entity['fields'])} fields"
            )

        # --------------------------------------------------------------
        # Dataset generation
        # --------------------------------------------------------------

        print()
        print("Generating dataset...")

        dataset = generate_dataset(specification)

        print()
        print("Generated dataset:")

        for entity in specification["entities"]:

            entity_name = entity["name"]

            records = dataset[entity_name]

            print(f"  {entity_name}: " f"{len(records)} records")

            if records:
                print(f"    Sample: " f"{records[0]}")

        # --------------------------------------------------------------
        # Dataset validation
        # --------------------------------------------------------------

        dataset_checks = {
            "Dataset Structure": validate_dataset_structure(
                specification,
                dataset,
            ),
            "Population Counts": validate_population_counts(
                specification,
                dataset,
            ),
            "Field Presence": validate_field_presence(
                specification,
                dataset,
            ),
            "Identity Uniqueness": validate_identity_uniqueness(
                specification,
                dataset,
            ),
            "Declared Ranges": validate_declared_ranges(
                specification,
                dataset,
            ),
            "Categorical Values": validate_categorical_values(
                specification,
                dataset,
            ),
        }

        print()
        print("Dataset validation:")

        for name, passed in dataset_checks.items():

            print(f"  {name:<35}" f"{'PASS' if passed else 'FAIL'}")

        # --------------------------------------------------------------
        # Reproducibility
        # --------------------------------------------------------------

        reproducibility = test_reproducibility(specification)

        seed_sensitivity = test_seed_sensitivity(specification)

        print()
        print("Reproducibility validation:")

        print(
            "  Same specification + same seed       "
            f"{'PASS' if reproducibility else 'FAIL'}"
        )

        print()
        print("Seed sensitivity validation:")

        print(
            "  Different seed changes stochastic data "
            f"{'PASS' if seed_sensitivity else 'FAIL'}"
        )

        # --------------------------------------------------------------
        # CSV output
        # --------------------------------------------------------------

        csv_paths = write_dataset_csv(dataset)

        # --------------------------------------------------------------
        # Overall result
        # --------------------------------------------------------------

        dataset_generation = all(dataset_checks.values())

        total_records = sum(len(records) for records in dataset.values())

        overall = (
            specification_valid
            and dataset_generation
            and reproducibility
            and seed_sensitivity
        )

        # --------------------------------------------------------------
        # Generation manifest
        # --------------------------------------------------------------

        manifest = {
            "experiment": EXPERIMENT_NAME,
            "stage": EXPERIMENT_ID,
            "model": model_name,
            "specification_version": specification.get("version"),
            "vocabulary_version": specification.get("vocabulary_version"),
            "seed": seed,
            "scenario": scenario,
            "dataset_format": "CSV",
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

        # --------------------------------------------------------------
        # Experiment result
        # --------------------------------------------------------------

        results = {
            "experiment": EXPERIMENT_NAME,
            "stage": EXPERIMENT_ID,
            "specification_validity": ("PASS" if specification_valid else "FAIL"),
            "dataset_generation": ("PASS" if dataset_generation else "FAIL"),
            "dataset_format": "CSV",
            "dataset_validation": {
                name: ("PASS" if passed else "FAIL")
                for name, passed in dataset_checks.items()
            },
            "reproducibility": ("PASS" if reproducibility else "FAIL"),
            "seed_sensitivity": ("PASS" if seed_sensitivity else "FAIL"),
            "total_records": total_records,
            "overall": ("PASS" if overall else "FAIL"),
        }

        result_path = write_json(
            "model_to_dataset_results.json",
            results,
        )

        # --------------------------------------------------------------
        # Console result
        # --------------------------------------------------------------

        print()
        print("Experiment result:")

        print(
            "  Specification validity:       "
            f"{'PASS' if specification_valid else 'FAIL'}"
        )

        print(
            "  Dataset generation:           "
            f"{'PASS' if dataset_generation else 'FAIL'}"
        )

        print(
            "  Reproducibility:              "
            f"{'PASS' if reproducibility else 'FAIL'}"
        )

        print(
            "  Seed sensitivity:             "
            f"{'PASS' if seed_sensitivity else 'FAIL'}"
        )

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
                "Declarative model-to-dataset "
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
            "model_to_dataset_results.json",
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
