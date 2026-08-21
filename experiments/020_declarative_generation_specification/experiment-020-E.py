"""
FORGE - Experiment 020-E: Declarative Multi-Field Record Generation
====================================================================

Purpose
-------
This experiment proves that the generic field-generation capability
established by Experiment 020-D can be composed into a generic
multi-field record generator.

The record generator interprets an entity specification containing
multiple declarative field specifications and produces records without
entity-specific or field-specific generation logic.

Stage
-----
020-E - Declarative Multi-Field Record Generation

Relationship to previous stages
--------------------------------
020-A established the declarative FORGE specification and controlled
vocabulary.

020-B / 020-B.1 established runtime capability assessment.

020-C established the declarative rule and expression engine.

020-C.1 hardened and validated expression evaluation.

020-D established generic declarative field generation.

020-E composes those capabilities into record generation.

Research Question
-----------------
Can a generic record-generation engine compose independently declared
field specifications into complete records without requiring knowledge
of the business entity or field semantics?

Hypothesis
----------
A generic record generator can construct complete records by evaluating
each field specification through the generic field-generation engine.

The generator should not contain logic such as:

    if entity == "CUSTOMER":
        ...

or:

    if field_name == "CUSTOMER_ID":
        ...

The entity definition should determine what fields exist and how
their values are generated.

The hypothesis is supported if:

    - multiple fields can be generated into the same record
    - fields retain their declared types
    - each field follows its declared strategy
    - categorical fields remain within their vocabulary
    - record counts are respected
    - field order does not change generation semantics
    - unrelated entity specifications can use the same generator
    - seeded generation is reproducible
    - the generator remains independent of business field names

The hypothesis is rejected if generation requires hard-coded entity
or field-specific generation logic.

Scope
-----
Included:

    - entity specification
    - multiple field specifications
    - record generation
    - record count
    - field-level generation
    - primitive types
    - semantic types
    - CONSTANT
    - SEQUENTIAL
    - RANDOM
    - NULL
    - UNIFORM
    - NORMAL
    - DISCRETE_UNIFORM
    - CATEGORICAL
    - deterministic generation
    - field-order independence
    - entity agnosticism
    - record-level validation

Excluded:

    - foreign keys
    - parent/child relationships
    - 1:1 / 1:N / N:M relationships
    - cross-field dependencies
    - conditional generation
    - derived fields
    - formulas
    - lookups
    - references
    - scenarios
    - statistical correlation
    - provenance
    - full unified validation

These capabilities will be addressed by later stages of Experiment 020.

Experiment
----------
020-E - Declarative Multi-Field Record Generation

Author
------
Ranjoy Sen

Status
------
Experimental

How to Run
----------
From the repository root:

    uv run python experiments/020_declarative_generation_specification/experiment-020-E.py

Output
------
Validation results are written to:

    experiments/020_declarative_generation_specification/output/

Important
---------
The generated values are synthetic and domain-neutral.

The entities used by this experiment are intentionally generic examples.
The generator must not contain business-specific generation logic.
"""

from __future__ import annotations

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

RESULT_OUTPUT_PATH = OUTPUT_DIR / "record_generation_results.json"

RANDOM_SEED = 42

DEFAULT_RECORD_COUNT = 10


# ============================================================================
# LOAD 020-D FIELD ENGINE
# ============================================================================


def load_field_engine():
    """
    Load the 020-D field-generation implementation.

    The module is registered in sys.modules before execution because
    020-D uses runtime introspection and dataclasses.
    """

    spec = importlib.util.spec_from_file_location(
        "forge_experiment_020_d",
        FIELD_ENGINE_PATH,
    )

    if spec is None or spec.loader is None:

        raise RuntimeError("Unable to load Experiment 020-D.")

    module = importlib.util.module_from_spec(spec)

    sys.modules[spec.name] = module

    spec.loader.exec_module(module)

    return module


FIELD_ENGINE = load_field_engine()

DeclarativeFieldGenerator = FIELD_ENGINE.DeclarativeFieldGenerator

FieldSpecification = FIELD_ENGINE.FieldSpecification


# ============================================================================
# EXCEPTIONS
# ============================================================================


class RecordGenerationError(Exception):
    """Base exception for record generation."""


class InvalidEntitySpecificationError(RecordGenerationError):
    """Raised when an entity specification is invalid."""


# ============================================================================
# ENTITY SPECIFICATION
# ============================================================================


@dataclass(frozen=True)
class EntitySpecification:

    name: str

    fields: tuple[FieldSpecification, ...]

    record_count: int = DEFAULT_RECORD_COUNT


# ============================================================================
# GENERIC RECORD GENERATOR
# ============================================================================


class DeclarativeRecordGenerator:
    """
    Generic multi-field record generator.

    This class deliberately contains no knowledge of CUSTOMER,
    ORDER, PRODUCT, or any other business entity.

    It simply composes field specifications and delegates actual
    value generation to the generic 020-D field generator.
    """

    def __init__(
        self,
        seed: int = RANDOM_SEED,
    ) -> None:

        self.seed = seed

    # ------------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------------

    def generate(
        self,
        specification: EntitySpecification,
    ) -> list[dict[str, Any]]:

        self.validate_entity_specification(specification)

        generator = DeclarativeFieldGenerator(seed=self.seed)

        field_values: dict[
            str,
            list[Any],
        ] = {}

        for field in specification.fields:

            field_values[field.name] = generator.generate(
                field,
                specification.record_count,
            )

        records = []

        for index in range(specification.record_count):

            record = {}

            for field in specification.fields:

                record[field.name] = field_values[field.name][index]

            records.append(record)

        return records

    # ------------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------------

    def validate_entity_specification(
        self,
        specification: EntitySpecification,
    ) -> None:

        if not specification.name:

            raise InvalidEntitySpecificationError("Entity name cannot be empty.")

        if specification.record_count < 0:

            raise InvalidEntitySpecificationError("Record count cannot be negative.")

        if not specification.fields:

            raise InvalidEntitySpecificationError(
                "Entity must contain at least " "one field."
            )

        field_names = set()

        for field in specification.fields:

            if field.name in field_names:

                raise InvalidEntitySpecificationError(
                    f"Duplicate field " f"'{field.name}'."
                )

            field_names.add(field.name)

    # ------------------------------------------------------------------------
    # Record validation
    # ------------------------------------------------------------------------

    def validate_records(
        self,
        specification: EntitySpecification,
        records: list[dict[str, Any]],
    ) -> dict[str, Any]:

        errors = []

        if len(records) != (specification.record_count):

            errors.append("Generated record count " "does not match specification.")

        expected_fields = {field.name for field in specification.fields}

        for index, record in enumerate(records):

            actual_fields = set(record.keys())

            if actual_fields != (expected_fields):

                errors.append(
                    f"Record {index} " "does not contain the " "expected fields."
                )

        return {
            "valid": not errors,
            "errors": errors,
        }


# ============================================================================
# ENTITY SPECIFICATIONS
# ============================================================================


def build_customer_specification():
    """
    A domain-neutral customer-shaped entity.

    The generator does not know that this is a customer.
    """

    return EntitySpecification(
        name="CUSTOMER",
        record_count=10,
        fields=(
            FieldSpecification(
                name="CUSTOMER_ID",
                type="IDENTIFIER",
                strategy="SEQUENTIAL",
                parameters={
                    "start": 1,
                    "step": 1,
                    "prefix": "CUS-",
                },
            ),
            FieldSpecification(
                name="CUSTOMER_TYPE",
                type="CATEGORICAL",
                strategy="RANDOM",
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
            FieldSpecification(
                name="COUNTRY",
                type="CATEGORICAL",
                strategy="RANDOM",
                distribution="CATEGORICAL",
                parameters={
                    "values": [
                        "US",
                        "IN",
                        "DE",
                        "FR",
                    ],
                    "weights": [
                        0.5,
                        0.3,
                        0.15,
                        0.05,
                    ],
                },
            ),
            FieldSpecification(
                name="CREDIT_LIMIT",
                type="CURRENCY",
                strategy="RANDOM",
                distribution="UNIFORM",
                parameters={
                    "min": 1000,
                    "max": 10000,
                },
            ),
            FieldSpecification(
                name="IS_ACTIVE",
                type="BOOLEAN",
                strategy="RANDOM",
                distribution="CATEGORICAL",
                parameters={
                    "values": [
                        True,
                        False,
                    ],
                    "weights": [
                        0.9,
                        0.1,
                    ],
                },
            ),
        ),
    )


def build_product_specification():
    """
    A completely different entity using the same generic generator.
    """

    return EntitySpecification(
        name="PRODUCT",
        record_count=10,
        fields=(
            FieldSpecification(
                name="PRODUCT_ID",
                type="IDENTIFIER",
                strategy="SEQUENTIAL",
                parameters={
                    "start": 100,
                    "step": 1,
                    "prefix": "PRD-",
                },
            ),
            FieldSpecification(
                name="PRODUCT_TYPE",
                type="ENUM",
                strategy="RANDOM",
                distribution="CATEGORICAL",
                parameters={
                    "values": [
                        "STANDARD",
                        "PREMIUM",
                        "SPECIAL",
                    ],
                },
            ),
            FieldSpecification(
                name="UNIT_PRICE",
                type="CURRENCY",
                strategy="RANDOM",
                distribution="UNIFORM",
                parameters={
                    "min": 10,
                    "max": 5000,
                },
            ),
            FieldSpecification(
                name="PRODUCT_SCORE",
                type="DECIMAL",
                strategy="RANDOM",
                distribution="NORMAL",
                parameters={
                    "mean": 75,
                    "stddev": 10,
                },
            ),
            FieldSpecification(
                name="CREATED_DATE",
                type="DATE",
                strategy="CONSTANT",
                parameters={
                    "value": "2026-01-01",
                },
            ),
        ),
    )


# ============================================================================
# FIELD-ORDER INDEPENDENCE
# ============================================================================


def validate_field_order_independence():
    """
    Verify that changing field declaration order does not change
    generated values for the same seed.

    Each field receives its own deterministic generation stream
    derived from the generator sequence.

    This validation deliberately exposes an architectural property
    that will need strengthening as dependencies are introduced.
    """

    original = build_customer_specification()

    reversed_specification = EntitySpecification(
        name=original.name,
        record_count=original.record_count,
        fields=tuple(reversed(original.fields)),
    )

    generator_a = DeclarativeRecordGenerator(seed=RANDOM_SEED)

    generator_b = DeclarativeRecordGenerator(seed=RANDOM_SEED)

    records_a = generator_a.generate(original)

    records_b = generator_b.generate(reversed_specification)

    normalized_a = [
        {key: record[key] for key in sorted(record)} for record in records_a
    ]

    normalized_b = [
        {key: record[key] for key in sorted(record)} for record in records_b
    ]

    return {
        "status": ("PASS" if normalized_a == normalized_b else "FAIL"),
        "records_identical": (normalized_a == normalized_b),
    }


# ============================================================================
# ENTITY AGNOSTICISM
# ============================================================================


def validate_entity_agnosticism():
    """
    Demonstrate that the same generator handles unrelated entities
    without entity-specific logic.
    """

    generator = DeclarativeRecordGenerator(seed=RANDOM_SEED)

    customer = build_customer_specification()

    product = build_product_specification()

    customer_records = generator.generate(customer)

    product_records = generator.generate(product)

    customer_valid = all(
        set(record.keys()) == {field.name for field in customer.fields}
        for record in customer_records
    )

    product_valid = all(
        set(record.keys()) == {field.name for field in product.fields}
        for record in product_records
    )

    return {
        "status": ("PASS" if customer_valid and product_valid else "FAIL"),
        "customer_generated": (len(customer_records)),
        "product_generated": (len(product_records)),
        "same_generic_generator": True,
    }


# ============================================================================
# REPRODUCIBILITY
# ============================================================================


def validate_reproducibility(
    specification: EntitySpecification,
):
    """
    Same entity specification + same seed must produce the same records.
    """

    generator_a = DeclarativeRecordGenerator(seed=RANDOM_SEED)

    generator_b = DeclarativeRecordGenerator(seed=RANDOM_SEED)

    records_a = generator_a.generate(specification)

    records_b = generator_b.generate(specification)

    identical = records_a == records_b

    return {
        "status": ("PASS" if identical else "FAIL"),
        "identical": identical,
    }


# ============================================================================
# MAIN
# ============================================================================


def main() -> int:

    print()

    print("=" * 70)

    print("FORGE - Experiment 020-E: " "Declarative Multi-Field Record Generation")

    print("=" * 70)

    print("Experiment:     " "020_declarative_generation_specification")

    print("Stage:          020-E")

    print("Purpose:        " "Generic declarative record generation")

    print(f"Random seed:    " f"{RANDOM_SEED}")

    print()

    customer = build_customer_specification()

    product = build_product_specification()

    generator = DeclarativeRecordGenerator(seed=RANDOM_SEED)

    # ------------------------------------------------------------------------
    # CUSTOMER
    # ------------------------------------------------------------------------

    print("Generating CUSTOMER records...")

    customer_records = generator.generate(customer)

    customer_validation = generator.validate_records(
        customer,
        customer_records,
    )

    print(f"  Records generated: " f"{len(customer_records)}")

    print(
        f"  Record structure: " f"{'PASS' if customer_validation['valid'] else 'FAIL'}"
    )

    for record in customer_records[:5]:

        print(f"    {record}")

    # ------------------------------------------------------------------------
    # PRODUCT
    # ------------------------------------------------------------------------

    print()

    print("Generating PRODUCT records...")

    product_records = generator.generate(product)

    product_validation = generator.validate_records(
        product,
        product_records,
    )

    print(f"  Records generated: " f"{len(product_records)}")

    print(
        f"  Record structure: " f"{'PASS' if product_validation['valid'] else 'FAIL'}"
    )

    for record in product_records[:5]:

        print(f"    {record}")

    # ------------------------------------------------------------------------
    # ENTITY AGNOSTICISM
    # ------------------------------------------------------------------------

    print()

    print("Entity agnosticism validation:")

    entity_agnosticism = validate_entity_agnosticism()

    print(
        f"  Generic generator handles "
        f"multiple entities: "
        f"{entity_agnosticism['status']}"
    )

    # ------------------------------------------------------------------------
    # FIELD ORDER
    # ------------------------------------------------------------------------

    print()

    print("Field-order independence validation:")

    field_order = validate_field_order_independence()

    print(
        f"  Field declaration order "
        f"does not alter results: "
        f"{field_order['status']}"
    )

    # ------------------------------------------------------------------------
    # REPRODUCIBILITY
    # ------------------------------------------------------------------------

    print()

    print("Reproducibility validation:")

    reproducibility = validate_reproducibility(customer)

    print(f"  Same specification + same seed: " f"{reproducibility['status']}")

    # ------------------------------------------------------------------------
    # OVERALL
    # ------------------------------------------------------------------------

    overall = (
        customer_validation["valid"]
        and product_validation["valid"]
        and entity_agnosticism["status"] == "PASS"
        and field_order["status"] == "PASS"
        and reproducibility["status"] == "PASS"
    )

    print()

    print("Experiment result:")

    print(
        f"  CUSTOMER generation:   "
        f"{'PASS' if customer_validation['valid'] else 'FAIL'}"
    )

    print(
        f"  PRODUCT generation:    "
        f"{'PASS' if product_validation['valid'] else 'FAIL'}"
    )

    print(f"  Entity agnosticism:    " f"{entity_agnosticism['status']}")

    print(f"  Field-order behavior:  " f"{field_order['status']}")

    print(f"  Reproducibility:       " f"{reproducibility['status']}")

    print(f"  Overall:               " f"{'PASS' if overall else 'FAIL'}")

    # ------------------------------------------------------------------------
    # OUTPUT
    # ------------------------------------------------------------------------

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    payload = {
        "experiment": ("020_declarative_generation_specification"),
        "stage": "020-E",
        "purpose": ("Generic declarative " "multi-field record generation"),
        "seed": RANDOM_SEED,
        "entities": {
            "CUSTOMER": {
                "record_count": (customer.record_count),
                "field_count": len(customer.fields),
                "validation": (customer_validation),
                "sample": (customer_records[:5]),
            },
            "PRODUCT": {
                "record_count": (product.record_count),
                "field_count": len(product.fields),
                "validation": (product_validation),
                "sample": (product_records[:5]),
            },
        },
        "entity_agnosticism": (entity_agnosticism),
        "field_order_independence": (field_order),
        "reproducibility": (reproducibility),
        "summary": {
            "customer_generation": ("PASS" if customer_validation["valid"] else "FAIL"),
            "product_generation": ("PASS" if product_validation["valid"] else "FAIL"),
            "entity_agnosticism": (entity_agnosticism["status"]),
            "field_order_independence": (field_order["status"]),
            "reproducibility": (reproducibility["status"]),
            "overall": ("PASS" if overall else "FAIL"),
        },
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
