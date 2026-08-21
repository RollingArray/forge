"""
FORGE - Experiment 020-E.1: Deterministic Field Stream Isolation
=================================================================

Purpose
-------
This experiment hardens Experiment 020-E by validating that independent
fields receive independent deterministic random streams.

The initial 020-E implementation used a shared random stream. This
created an unintended coupling between field declaration order and
generated values.

020-E.1 derives a deterministic random stream for each field from:

    master seed + field identity

This ensures that changing the declaration order of independent fields
does not change their generated values.

Stage
-----
020-E.1 - Deterministic Field Stream Isolation

Research Question
-----------------
Can FORGE isolate independent field generation streams while preserving
deterministic reproducibility?

Hypothesis
----------
Independent fields should produce identical values when generated from
the same master seed regardless of their declaration order.

The implementation should also demonstrate:

    - same seed + same field -> same stream
    - different seed + same field -> different stream
    - same seed + different fields -> independent streams
    - sequential fields remain stable
    - field declaration order does not affect independent fields

Scope
-----
Included:

    - deterministic field-level random streams
    - master seed derivation
    - field identity based stream derivation
    - field-order independence
    - reproducibility
    - seed sensitivity
    - field stream isolation
    - sequential field stability

Excluded:

    - cross-field dependencies
    - conditional generation
    - formulas
    - derived fields
    - references
    - relationships
    - scenarios
    - statistical correlation
    - provenance

Important
---------
This experiment establishes that field order must not implicitly create
a generation dependency.

Explicit dependencies will be introduced by later experiments.

Author
------
Ranjoy Sen

Status
------
Experimental

How to Run
----------
From the repository root:

    uv run python experiments/020_declarative_generation_specification/experiment-020-E.1.py

Output
------
Results are written to:

    experiments/020_declarative_generation_specification/output/
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

# ============================================================================
# PATHS / CONSTANTS
# ============================================================================

EXPERIMENT_DIR = Path(__file__).resolve().parent

FIELD_ENGINE_PATH = EXPERIMENT_DIR / "experiment-020-D.py"

OUTPUT_DIR = EXPERIMENT_DIR / "output"

RESULT_OUTPUT_PATH = OUTPUT_DIR / "field_stream_isolation_results.json"

RANDOM_SEED = 42


# ============================================================================
# LOAD 020-D FIELD ENGINE
# ============================================================================


def load_field_engine():
    """Load the generic field generator from Experiment 020-D."""

    spec = importlib.util.spec_from_file_location(
        "forge_experiment_020_d_e1",
        FIELD_ENGINE_PATH,
    )

    if spec is None or spec.loader is None:
        raise RuntimeError("Unable to load Experiment 020-D.")

    module = importlib.util.module_from_spec(spec)

    # Required for dataclasses and runtime module resolution.
    sys.modules[spec.name] = module

    spec.loader.exec_module(module)

    return module


FIELD_ENGINE = load_field_engine()

DeclarativeFieldGenerator = FIELD_ENGINE.DeclarativeFieldGenerator

FieldSpecification = FIELD_ENGINE.FieldSpecification


# ============================================================================
# ENTITY SPECIFICATION
# ============================================================================


@dataclass(frozen=True)
class EntitySpecification:
    """Declarative entity definition used by this experiment."""

    name: str
    fields: tuple[FieldSpecification, ...]
    record_count: int = 10


# ============================================================================
# DETERMINISTIC RECORD GENERATOR
# ============================================================================


class DeterministicRecordGenerator:
    """
    Generic record generator using field-isolated deterministic streams.

    The generator contains no knowledge of CUSTOMER, ORDER, PRODUCT,
    or any other business entity.
    """

    def __init__(
        self,
        seed: int = RANDOM_SEED,
    ) -> None:

        self.seed = seed

    # ------------------------------------------------------------------------
    # Field seed derivation
    # ------------------------------------------------------------------------

    def field_seed(
        self,
        field_name: str,
    ) -> int:
        """
        Derive a stable deterministic seed for a field.

        Python's built-in hash() is deliberately not used because its
        result can vary between interpreter processes.

        SHA-256 gives us a stable mapping from:

            master seed + field identity

        to a deterministic integer seed.
        """

        material = (f"{self.seed}:{field_name}").encode("utf-8")

        digest = hashlib.sha256(material).digest()

        return int.from_bytes(
            digest[:8],
            byteorder="big",
        )

    # ------------------------------------------------------------------------
    # Entity generation
    # ------------------------------------------------------------------------

    def generate(
        self,
        specification: EntitySpecification,
    ) -> list[dict[str, Any]]:

        self.validate_specification(specification)

        field_values: dict[
            str,
            list[Any],
        ] = {}

        for field in specification.fields:

            field_generator = DeclarativeFieldGenerator(
                seed=self.field_seed(field.name)
            )

            field_values[field.name] = field_generator.generate(
                field,
                specification.record_count,
            )

        records: list[dict[str, Any]] = []

        for index in range(specification.record_count):

            record: dict[str, Any] = {}

            for field in specification.fields:

                record[field.name] = field_values[field.name][index]

            records.append(record)

        return records

    # ------------------------------------------------------------------------
    # Specification validation
    # ------------------------------------------------------------------------

    def validate_specification(
        self,
        specification: EntitySpecification,
    ) -> None:

        if not specification.name:
            raise ValueError("Entity name cannot be empty.")

        if specification.record_count < 0:
            raise ValueError("Record count cannot be negative.")

        if not specification.fields:
            raise ValueError("Entity must contain fields.")

        field_names: set[str] = set()

        for field in specification.fields:

            if field.name in field_names:
                raise ValueError(f"Duplicate field: {field.name}")

            field_names.add(field.name)


# ============================================================================
# TEST SPECIFICATION
# ============================================================================


def build_entity() -> EntitySpecification:
    """Build a domain-neutral multi-field entity."""

    return EntitySpecification(
        name="GENERIC_ENTITY",
        record_count=20,
        fields=(
            FieldSpecification(
                name="FIELD_ALPHA",
                type="DECIMAL",
                strategy="RANDOM",
                distribution="UNIFORM",
                parameters={
                    "min": 0,
                    "max": 1000,
                },
            ),
            FieldSpecification(
                name="FIELD_BETA",
                type="INTEGER",
                strategy="RANDOM",
                distribution="DISCRETE_UNIFORM",
                parameters={
                    "min": 1,
                    "max": 100,
                },
            ),
            FieldSpecification(
                name="FIELD_GAMMA",
                type="CATEGORICAL",
                strategy="RANDOM",
                distribution="CATEGORICAL",
                parameters={
                    "values": [
                        "A",
                        "B",
                        "C",
                    ],
                    "weights": [
                        0.5,
                        0.3,
                        0.2,
                    ],
                },
            ),
            FieldSpecification(
                name="FIELD_DELTA",
                type="FLOAT",
                strategy="RANDOM",
                distribution="NORMAL",
                parameters={
                    "mean": 50,
                    "stddev": 10,
                },
            ),
            FieldSpecification(
                name="FIELD_SEQUENCE",
                type="IDENTIFIER",
                strategy="SEQUENTIAL",
                parameters={
                    "start": 1,
                    "step": 1,
                    "prefix": "ID-",
                },
            ),
        ),
    )


# ============================================================================
# NORMALIZATION
# ============================================================================


def normalize_records(
    records: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """
    Normalize dictionary field order so that comparison is based on
    values rather than dictionary insertion order.
    """

    return [{key: record[key] for key in sorted(record)} for record in records]


# ============================================================================
# VALIDATION 1: FIELD ORDER INDEPENDENCE
# ============================================================================


def validate_field_order_independence(
    specification: EntitySpecification,
) -> dict[str, Any]:

    reordered = EntitySpecification(
        name=specification.name,
        record_count=specification.record_count,
        fields=tuple(reversed(specification.fields)),
    )

    generator_a = DeterministicRecordGenerator(seed=RANDOM_SEED)

    generator_b = DeterministicRecordGenerator(seed=RANDOM_SEED)

    records_a = generator_a.generate(specification)

    records_b = generator_b.generate(reordered)

    normalized_a = normalize_records(records_a)

    normalized_b = normalize_records(records_b)

    passed = normalized_a == normalized_b

    return {
        "status": ("PASS" if passed else "FAIL"),
        "records_identical": passed,
        "original_order": [field.name for field in specification.fields],
        "reordered": [field.name for field in reordered.fields],
    }


# ============================================================================
# VALIDATION 2: REPRODUCIBILITY
# ============================================================================


def validate_reproducibility(
    specification: EntitySpecification,
) -> dict[str, Any]:

    generator_a = DeterministicRecordGenerator(seed=RANDOM_SEED)

    generator_b = DeterministicRecordGenerator(seed=RANDOM_SEED)

    records_a = generator_a.generate(specification)

    records_b = generator_b.generate(specification)

    passed = records_a == records_b

    return {
        "status": ("PASS" if passed else "FAIL"),
        "records_identical": passed,
    }


# ============================================================================
# VALIDATION 3: SEED SENSITIVITY
# ============================================================================


def validate_seed_sensitivity(
    specification: EntitySpecification,
) -> dict[str, Any]:

    generator_a = DeterministicRecordGenerator(seed=42)

    generator_b = DeterministicRecordGenerator(seed=43)

    records_a = generator_a.generate(specification)

    records_b = generator_b.generate(specification)

    random_fields = [
        field.name for field in specification.fields if field.strategy == "RANDOM"
    ]

    changed_fields: list[str] = []

    for field_name in random_fields:

        values_a = [record[field_name] for record in records_a]

        values_b = [record[field_name] for record in records_b]

        if values_a != values_b:
            changed_fields.append(field_name)

    passed = len(changed_fields) == len(random_fields)

    return {
        "status": ("PASS" if passed else "FAIL"),
        "random_fields": random_fields,
        "changed_fields": changed_fields,
    }


# ============================================================================
# VALIDATION 4: FIELD STREAM ISOLATION
# ============================================================================


def validate_field_stream_isolation(
    specification: EntitySpecification,
) -> dict[str, Any]:

    generator = DeterministicRecordGenerator(seed=RANDOM_SEED)

    seeds = {
        field.name: generator.field_seed(field.name) for field in specification.fields
    }

    unique_seeds = len(set(seeds.values())) == len(seeds)

    return {
        "status": ("PASS" if unique_seeds else "FAIL"),
        "field_seeds": seeds,
        "unique_field_seeds": unique_seeds,
    }


# ============================================================================
# VALIDATION 5: FIELD NAME SENSITIVITY
# ============================================================================


def validate_field_name_sensitivity() -> dict[str, Any]:

    generator = DeterministicRecordGenerator(seed=RANDOM_SEED)

    seed_a = generator.field_seed("FIELD_A")

    seed_b = generator.field_seed("FIELD_B")

    passed = seed_a != seed_b

    return {
        "status": ("PASS" if passed else "FAIL"),
        "FIELD_A_seed": seed_a,
        "FIELD_B_seed": seed_b,
    }


# ============================================================================
# VALIDATION 6: SEQUENTIAL FIELD STABILITY
# ============================================================================


def validate_sequential_stability(
    specification: EntitySpecification,
) -> dict[str, Any]:

    sequence_fields = [
        field for field in specification.fields if field.strategy == "SEQUENTIAL"
    ]

    if not sequence_fields:

        return {
            "status": "PASS",
            "reason": ("No sequential fields."),
        }

    generator_a = DeterministicRecordGenerator(seed=RANDOM_SEED)

    generator_b = DeterministicRecordGenerator(seed=RANDOM_SEED)

    original_records = generator_a.generate(specification)

    reordered = EntitySpecification(
        name=specification.name,
        record_count=specification.record_count,
        fields=tuple(reversed(specification.fields)),
    )

    reordered_records = generator_b.generate(reordered)

    field_name = sequence_fields[0].name

    original_values = [record[field_name] for record in original_records]

    reordered_values = [record[field_name] for record in reordered_records]

    passed = original_values == reordered_values

    return {
        "status": ("PASS" if passed else "FAIL"),
        "field": field_name,
        "stable": passed,
    }


# ============================================================================
# MAIN
# ============================================================================


def main() -> int:

    print()

    print("=" * 70)

    print("FORGE - Experiment 020-E.1: " "Deterministic Field Stream Isolation")

    print("=" * 70)

    print("Experiment:     " "020_declarative_generation_specification")

    print("Stage:          020-E.1")

    print("Purpose:        " "Field-level deterministic random streams")

    print(f"Master seed:    {RANDOM_SEED}")

    print()

    specification = build_entity()

    generator = DeterministicRecordGenerator(seed=RANDOM_SEED)

    print("Field stream derivation:")

    for field in specification.fields:

        print(f"  " f"{field.name:<20}" f"seed={generator.field_seed(field.name)}")

    print()

    print("Deterministic stream validation:")

    field_order = validate_field_order_independence(specification)

    print(f"  Field-order independence: " f"{field_order['status']}")

    reproducibility = validate_reproducibility(specification)

    print(f"  Same seed reproducibility: " f"{reproducibility['status']}")

    seed_sensitivity = validate_seed_sensitivity(specification)

    print(f"  Seed sensitivity: " f"{seed_sensitivity['status']}")

    isolation = validate_field_stream_isolation(specification)

    print(f"  Field stream isolation: " f"{isolation['status']}")

    field_name_sensitivity = validate_field_name_sensitivity()

    print(f"  Field identity sensitivity: " f"{field_name_sensitivity['status']}")

    sequential_stability = validate_sequential_stability(specification)

    print(f"  Sequential field stability: " f"{sequential_stability['status']}")

    print()

    results = [
        field_order,
        reproducibility,
        seed_sensitivity,
        isolation,
        field_name_sensitivity,
        sequential_stability,
    ]

    overall = all(result["status"] == "PASS" for result in results)

    print("Experiment result:")

    print(f"  Field-order independence: " f"{field_order['status']}")

    print(f"  Reproducibility:           " f"{reproducibility['status']}")

    print(f"  Seed sensitivity:          " f"{seed_sensitivity['status']}")

    print(f"  Stream isolation:          " f"{isolation['status']}")

    print(f"  Field identity sensitivity:" f" {field_name_sensitivity['status']}")

    print(f"  Sequential stability:      " f"{sequential_stability['status']}")

    print(f"  Overall:                   " f"{'PASS' if overall else 'FAIL'}")

    # ------------------------------------------------------------------------
    # OUTPUT
    # ------------------------------------------------------------------------

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    payload = {
        "experiment": ("020_declarative_generation_specification"),
        "stage": "020-E.1",
        "purpose": ("Deterministic field " "stream isolation"),
        "master_seed": RANDOM_SEED,
        "field_streams": {
            field.name: generator.field_seed(field.name)
            for field in specification.fields
        },
        "field_order_independence": (field_order),
        "reproducibility": (reproducibility),
        "seed_sensitivity": (seed_sensitivity),
        "field_stream_isolation": (isolation),
        "field_name_sensitivity": (field_name_sensitivity),
        "sequential_stability": (sequential_stability),
        "architectural_conclusion": (
            "Independent fields derive "
            "deterministic random streams "
            "from master seed and field "
            "identity. Field declaration "
            "order therefore does not "
            "implicitly create a generation "
            "dependency."
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
