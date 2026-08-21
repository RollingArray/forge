"""
FORGE - Experiment 020-G: Declarative Identity and Uniqueness
==============================================================

Purpose
-------
This experiment validates identity and uniqueness as first-class
declarative generation controls.

The experiment establishes the foundation required for later
relationship generation without implementing relationship resolution
itself.

The following FORGE vocabulary is tested:

    PRIMARY_KEY
    FOREIGN_KEY
    COMPOSITE_KEY
    NATURAL_KEY
    SURROGATE_KEY
    UNIQUE
    STABLE
    SEQUENTIAL_ID
    UUID
    COMPOSITE_ID

Stage
-----
020-G - Identity and Uniqueness

Research Question
-----------------
Can FORGE declaratively generate different forms of identity while
guaranteeing the identity properties requested by the specification?

Hypothesis
----------
Identity semantics can be separated from the underlying value type
and generation strategy.

The generator should be able to represent:

    - sequential identities
    - UUID identities
    - natural identities
    - surrogate identities
    - composite identities
    - unique non-key values
    - stable identities

while preserving:

    - uniqueness
    - non-nullability for primary identities
    - deterministic reproducibility where requested
    - field-order independence

Scope
-----
Included:

    - PRIMARY_KEY
    - FOREIGN_KEY vocabulary representation
    - COMPOSITE_KEY
    - NATURAL_KEY
    - SURROGATE_KEY
    - UNIQUE
    - STABLE
    - SEQUENTIAL_ID
    - UUID
    - COMPOSITE_ID
    - uniqueness validation
    - deterministic identity generation
    - composite identity generation
    - identity collision detection

Excluded:

    - actual foreign-key resolution
    - parent-child generation
    - relationship cardinality
    - 1:1 relationships
    - 1:N relationships
    - N:M relationships
    - dependency graphs
    - conditional dependencies
    - statistical correlation

Those capabilities are addressed by later experiments.

Important Architectural Principle
---------------------------------
Identity semantics must not be coupled to a particular business domain.

The identity mechanism must work for arbitrary entities such as:

    CUSTOMER
    PRODUCT
    ORDER
    SENSOR
    EMPLOYEE

without entity-specific generation code.

Important Boundary
------------------
FOREIGN_KEY is validated as an identity semantic in this experiment,
but actual foreign-key value resolution is deliberately excluded.

A foreign key answers:

    "This field identifies a parent record."

Relationship generation answers:

    "Which parent record should this value reference?"

Those are separate concerns.

Author
------
Ranjoy Sen

Status
------
Experimental

How to Run
----------
From the repository root:

    uv run python experiments/020_declarative_generation_specification/experiment-020-G.py

Output
------
Results are written to:

    experiments/020_declarative_generation_specification/output/
"""

from __future__ import annotations

import hashlib
import json
import re
import sys
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any

# ============================================================================
# PATHS / CONSTANTS
# ============================================================================

EXPERIMENT_DIR = Path(__file__).resolve().parent

OUTPUT_DIR = EXPERIMENT_DIR / "output"

RESULT_OUTPUT_PATH = OUTPUT_DIR / "identity_uniqueness_results.json"

RANDOM_SEED = 42

DEFAULT_RECORD_COUNT = 100


# ============================================================================
# CONTROLLED VOCABULARY
# ============================================================================

IDENTITY_SEMANTICS = {
    "PRIMARY_KEY",
    "FOREIGN_KEY",
    "COMPOSITE_KEY",
    "NATURAL_KEY",
    "SURROGATE_KEY",
    "UNIQUE",
    "STABLE",
    "SEQUENTIAL_ID",
    "UUID",
    "COMPOSITE_ID",
}


# ============================================================================
# DECLARATIVE IDENTITY SPECIFICATION
# ============================================================================


@dataclass(frozen=True)
class IdentitySpecification:
    """
    Declarative identity definition.

    semantic:
        Identity meaning, for example PRIMARY_KEY or NATURAL_KEY.

    strategy:
        Concrete identity generation mechanism.

    fields:
        One or more fields participating in the identity.

    prefix:
        Optional textual prefix.

    start:
        Starting value for sequential identities.

    stable:
        Whether the identity must be reproducible from the same
        specification and seed.
    """

    semantic: str

    strategy: str

    fields: tuple[str, ...]

    prefix: str = ""

    start: int = 1

    stable: bool = True


# ============================================================================
# GENERIC IDENTITY ENGINE
# ============================================================================


class IdentityGenerator:
    """
    Generic identity generation engine.

    This class contains no business-specific knowledge.
    """

    def __init__(
        self,
        seed: int = RANDOM_SEED,
    ) -> None:

        self.seed = seed

    # ------------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------------

    def validate_specification(
        self,
        specification: IdentitySpecification,
    ) -> None:

        if specification.semantic not in IDENTITY_SEMANTICS:

            raise ValueError(
                "Unsupported identity semantic: " f"{specification.semantic}"
            )

        if not specification.fields:

            raise ValueError("Identity must reference " "at least one field.")

        if specification.strategy == "COMPOSITE_ID" and len(specification.fields) < 2:

            raise ValueError("COMPOSITE_ID requires " "at least two fields.")

        if specification.strategy == "SEQUENTIAL_ID":

            if not isinstance(
                specification.start,
                int,
            ):

                raise ValueError("SEQUENTIAL_ID start " "must be an integer.")

    # ------------------------------------------------------------------------
    # Generate identity values
    # ------------------------------------------------------------------------

    def generate(
        self,
        specification: IdentitySpecification,
        record_count: int,
        source_records: list[dict[str, Any]] | None = None,
    ) -> list[Any]:

        self.validate_specification(specification)

        if record_count < 0:

            raise ValueError("Record count cannot be negative.")

        strategy = specification.strategy

        if strategy == "SEQUENTIAL_ID":

            return self._generate_sequential(
                specification,
                record_count,
            )

        if strategy == "UUID":

            return self._generate_uuid(
                specification,
                record_count,
            )

        if strategy == "COMPOSITE_ID":

            if source_records is None:

                raise ValueError("COMPOSITE_ID requires " "source records.")

            return self._generate_composite(
                specification,
                source_records,
            )

        if strategy == "NATURAL_KEY":

            if source_records is None:

                raise ValueError("NATURAL_KEY requires " "source records.")

            return self._generate_natural(
                specification,
                source_records,
            )

        if strategy == "SURROGATE_KEY":

            return self._generate_surrogate(
                specification,
                record_count,
            )

        raise ValueError(f"Unsupported identity strategy: " f"{strategy}")

    # ------------------------------------------------------------------------
    # Sequential identity
    # ------------------------------------------------------------------------

    def _generate_sequential(
        self,
        specification: IdentitySpecification,
        record_count: int,
    ) -> list[str]:

        return [
            (f"{specification.prefix}" f"{specification.start + index}")
            for index in range(record_count)
        ]

    # ------------------------------------------------------------------------
    # Deterministic UUID
    # ------------------------------------------------------------------------

    def _generate_uuid(
        self,
        specification: IdentitySpecification,
        record_count: int,
    ) -> list[str]:

        values = []

        for index in range(record_count):

            namespace = f"FORGE:{self.seed}:" f"{specification.fields}:" f"{index}"

            value = uuid.uuid5(
                uuid.NAMESPACE_URL,
                namespace,
            )

            values.append(str(value))

        return values

    # ------------------------------------------------------------------------
    # Surrogate key
    # ------------------------------------------------------------------------

    def _generate_surrogate(
        self,
        specification: IdentitySpecification,
        record_count: int,
    ) -> list[str]:
        """
        A surrogate key has no business meaning.

        This implementation uses a deterministic digest rather than
        deriving the identity from a business field.
        """

        values = []

        for index in range(record_count):

            material = (f"{self.seed}:" f"{specification.fields}:" f"{index}").encode(
                "utf-8"
            )

            digest = hashlib.sha256(material).hexdigest()

            values.append(f"{specification.prefix}" f"{digest[:16]}")

        return values

    # ------------------------------------------------------------------------
    # Natural key
    # ------------------------------------------------------------------------

    def _generate_natural(
        self,
        specification: IdentitySpecification,
        source_records: list[dict[str, Any]],
    ) -> list[str]:

        values = []

        for record in source_records:

            components = []

            for field in specification.fields:

                if field not in record:

                    raise ValueError(f"Natural key field " f"'{field}' not present.")

                components.append(str(record[field]))

            value = "|".join(components)

            values.append(value)

        return values

    # ------------------------------------------------------------------------
    # Composite identity
    # ------------------------------------------------------------------------

    def _generate_composite(
        self,
        specification: IdentitySpecification,
        source_records: list[dict[str, Any]],
    ) -> list[str]:

        values = []

        for record in source_records:

            components = []

            for field in specification.fields:

                if field not in record:

                    raise ValueError(f"Composite key field " f"'{field}' not present.")

                value = record[field]

                if value is None:

                    raise ValueError(
                        "Composite identity "
                        "cannot contain null "
                        f"component: {field}"
                    )

                components.append(str(value))

            values.append("|".join(components))

        return values


# ============================================================================
# VALIDATION HELPERS
# ============================================================================


def is_unique(
    values: list[Any],
) -> bool:

    return len(values) == len(set(values))


def is_non_null(
    values: list[Any],
) -> bool:

    return all(value is not None for value in values)


def validate_uuid_values(
    values: list[Any],
) -> bool:

    try:

        for value in values:

            uuid.UUID(str(value))

        return True

    except ValueError:

        return False


def compare_field_identity(
    records_a: list[dict[str, Any]],
    records_b: list[dict[str, Any]],
    field: str,
) -> bool:

    values_a = [record[field] for record in records_a]

    values_b = [record[field] for record in records_b]

    return values_a == values_b


# ============================================================================
# SAMPLE DOMAIN-NEUTRAL RECORDS
# ============================================================================


def build_source_records(
    record_count: int = DEFAULT_RECORD_COUNT,
) -> list[dict[str, Any]]:

    records = []

    for index in range(record_count):

        records.append(
            {
                "COUNTRY_CODE": ("US" if index % 2 == 0 else "IN"),
                "CUSTOMER_NUMBER": (f"CUS-{index + 1:05d}"),
                "PRODUCT_CODE": (f"PRD-{(index % 10) + 1:03d}"),
                "VERSION": ((index % 3) + 1),
            }
        )

    return records


# ============================================================================
# VALIDATION 1: SEQUENTIAL ID
# ============================================================================


def validate_sequential_id() -> dict[str, Any]:

    generator = IdentityGenerator(seed=RANDOM_SEED)

    specification = IdentitySpecification(
        semantic="PRIMARY_KEY",
        strategy="SEQUENTIAL_ID",
        fields=("ENTITY_ID",),
        prefix="ENT-",
        start=100,
    )

    values = generator.generate(
        specification,
        100,
    )

    expected = [f"ENT-{100 + index}" for index in range(100)]

    passed = values == expected and is_unique(values) and is_non_null(values)

    return {
        "status": ("PASS" if passed else "FAIL"),
        "first": values[0],
        "last": values[-1],
        "unique": is_unique(values),
        "non_null": is_non_null(values),
    }


# ============================================================================
# VALIDATION 2: UUID
# ============================================================================


def validate_uuid() -> dict[str, Any]:

    generator = IdentityGenerator(seed=RANDOM_SEED)

    specification = IdentitySpecification(
        semantic="PRIMARY_KEY",
        strategy="UUID",
        fields=("ENTITY_ID",),
    )

    values = generator.generate(
        specification,
        100,
    )

    valid_uuid = validate_uuid_values(values)

    unique = is_unique(values)

    non_null = is_non_null(values)

    passed = valid_uuid and unique and non_null

    return {
        "status": ("PASS" if passed else "FAIL"),
        "valid_uuid": valid_uuid,
        "unique": unique,
        "non_null": non_null,
    }


# ============================================================================
# VALIDATION 3: STABLE IDENTITY
# ============================================================================


def validate_stability() -> dict[str, Any]:

    specification = IdentitySpecification(
        semantic="STABLE",
        strategy="UUID",
        fields=("ENTITY_ID",),
    )

    generator_a = IdentityGenerator(seed=RANDOM_SEED)

    generator_b = IdentityGenerator(seed=RANDOM_SEED)

    values_a = generator_a.generate(
        specification,
        100,
    )

    values_b = generator_b.generate(
        specification,
        100,
    )

    passed = values_a == values_b

    return {
        "status": ("PASS" if passed else "FAIL"),
        "stable": passed,
    }


# ============================================================================
# VALIDATION 4: SEED SENSITIVITY
# ============================================================================


def validate_seed_sensitivity() -> dict[str, Any]:

    specification = IdentitySpecification(
        semantic="STABLE",
        strategy="UUID",
        fields=("ENTITY_ID",),
    )

    values_a = IdentityGenerator(seed=42).generate(
        specification,
        100,
    )

    values_b = IdentityGenerator(seed=43).generate(
        specification,
        100,
    )

    changed = values_a != values_b

    return {
        "status": ("PASS" if changed else "FAIL"),
        "different_seed_changes_identity": changed,
    }


# ============================================================================
# VALIDATION 5: SURROGATE KEY
# ============================================================================


def validate_surrogate_key() -> dict[str, Any]:

    specification = IdentitySpecification(
        semantic="SURROGATE_KEY",
        strategy="SURROGATE_KEY",
        fields=("ENTITY_ID",),
        prefix="SK-",
    )

    values = IdentityGenerator(seed=RANDOM_SEED).generate(
        specification,
        100,
    )

    unique = is_unique(values)

    non_null = is_non_null(values)

    prefix_valid = all(str(value).startswith("SK-") for value in values)

    passed = unique and non_null and prefix_valid

    return {
        "status": ("PASS" if passed else "FAIL"),
        "unique": unique,
        "non_null": non_null,
        "prefix_valid": prefix_valid,
    }


# ============================================================================
# VALIDATION 6: NATURAL KEY
# ============================================================================


def validate_natural_key() -> dict[str, Any]:

    source_records = build_source_records()

    specification = IdentitySpecification(
        semantic="NATURAL_KEY",
        strategy="NATURAL_KEY",
        fields=(
            "COUNTRY_CODE",
            "CUSTOMER_NUMBER",
        ),
    )

    values = IdentityGenerator(seed=RANDOM_SEED).generate(
        specification,
        len(source_records),
        source_records,
    )

    unique = is_unique(values)

    expected_first = "US|CUS-00001"

    passed = unique and values[0] == expected_first

    return {
        "status": ("PASS" if passed else "FAIL"),
        "unique": unique,
        "first_value": values[0],
        "expected_first": expected_first,
    }


# ============================================================================
# VALIDATION 7: COMPOSITE ID
# ============================================================================


def validate_composite_id() -> dict[str, Any]:

    source_records = build_source_records()

    specification = IdentitySpecification(
        semantic="COMPOSITE_KEY",
        strategy="COMPOSITE_ID",
        fields=(
            "PRODUCT_CODE",
            "VERSION",
        ),
    )

    values = IdentityGenerator(seed=RANDOM_SEED).generate(
        specification,
        len(source_records),
        source_records,
    )

    expected_first = "PRD-001|1"

    # The sample data intentionally contains
    # repeated product/version combinations.
    # Therefore the identity generator must not
    # silently claim uniqueness.
    unique = is_unique(values)

    passed = values[0] == expected_first and not unique

    return {
        "status": ("PASS" if passed else "FAIL"),
        "first_value": values[0],
        "expected_first": expected_first,
        "unique": unique,
        "duplicate_detected": not unique,
    }


# ============================================================================
# VALIDATION 8: UNIQUE SEMANTIC
# ============================================================================


def validate_unique_semantic() -> dict[str, Any]:

    unique_values = [f"VALUE-{index}" for index in range(100)]

    duplicate_values = list(unique_values)

    duplicate_values[-1] = duplicate_values[0]

    passed = is_unique(unique_values) and not is_unique(duplicate_values)

    return {
        "status": ("PASS" if passed else "FAIL"),
        "unique_dataset_detected": (is_unique(unique_values)),
        "duplicate_dataset_detected": (not is_unique(duplicate_values)),
    }


# ============================================================================
# VALIDATION 9: PRIMARY KEY PROPERTIES
# ============================================================================


def validate_primary_key_properties() -> dict[str, Any]:

    specification = IdentitySpecification(
        semantic="PRIMARY_KEY",
        strategy="SEQUENTIAL_ID",
        fields=("ENTITY_ID",),
        prefix="ENT-",
    )

    values = IdentityGenerator(seed=RANDOM_SEED).generate(
        specification,
        1000,
    )

    unique = is_unique(values)

    non_null = is_non_null(values)

    passed = unique and non_null

    return {
        "status": ("PASS" if passed else "FAIL"),
        "unique": unique,
        "non_null": non_null,
        "record_count": len(values),
    }


# ============================================================================
# VALIDATION 10: FIELD ORDER INDEPENDENCE
# ============================================================================


def validate_field_order_independence() -> dict[str, Any]:

    source_records = build_source_records(100)

    specification_a = IdentitySpecification(
        semantic="COMPOSITE_KEY",
        strategy="COMPOSITE_ID",
        fields=(
            "COUNTRY_CODE",
            "CUSTOMER_NUMBER",
        ),
    )

    specification_b = IdentitySpecification(
        semantic="COMPOSITE_KEY",
        strategy="COMPOSITE_ID",
        fields=(
            "COUNTRY_CODE",
            "CUSTOMER_NUMBER",
        ),
    )

    generator_a = IdentityGenerator(seed=RANDOM_SEED)

    generator_b = IdentityGenerator(seed=RANDOM_SEED)

    values_a = generator_a.generate(
        specification_a,
        len(source_records),
        source_records,
    )

    values_b = generator_b.generate(
        specification_b,
        len(source_records),
        source_records,
    )

    passed = values_a == values_b

    return {
        "status": ("PASS" if passed else "FAIL"),
        "identical": passed,
    }


# ============================================================================
# VALIDATION 11: VOCABULARY SAFETY
# ============================================================================


def validate_vocabulary_safety() -> dict[str, Any]:

    generator = IdentityGenerator(seed=RANDOM_SEED)

    failures = []

    try:

        generator.generate(
            IdentitySpecification(
                semantic="UNKNOWN",
                strategy="UUID",
                fields=("ID",),
            ),
            10,
        )

        failures.append("Unknown identity semantic accepted.")

    except ValueError:
        pass

    try:

        generator.generate(
            IdentitySpecification(
                semantic="PRIMARY_KEY",
                strategy="UNKNOWN",
                fields=("ID",),
            ),
            10,
        )

        failures.append("Unknown identity strategy accepted.")

    except ValueError:
        pass

    try:

        generator.generate(
            IdentitySpecification(
                semantic="COMPOSITE_KEY",
                strategy="COMPOSITE_ID",
                fields=("ONLY_ONE",),
            ),
            10,
            [{"ONLY_ONE": "A"}],
        )

        failures.append("Single-field composite ID accepted.")

    except ValueError:
        pass

    passed = not failures

    return {
        "status": ("PASS" if passed else "FAIL"),
        "unexpected_acceptances": failures,
    }


# ============================================================================
# VALIDATION 12: FOREIGN KEY BOUNDARY
# ============================================================================


def validate_foreign_key_boundary() -> dict[str, Any]:

    specification = IdentitySpecification(
        semantic="FOREIGN_KEY",
        strategy="SEQUENTIAL_ID",
        fields=("PARENT_ID",),
        prefix="PAR-",
    )

    values = IdentityGenerator(seed=RANDOM_SEED).generate(
        specification,
        100,
    )

    passed = len(values) == 100 and is_non_null(values) and is_unique(values)

    return {
        "status": ("PASS" if passed else "FAIL"),
        "identity_values_generated": len(values),
        "non_null": is_non_null(values),
        "unique": is_unique(values),
        "relationship_resolution": ("DEFERRED"),
    }


# ============================================================================
# MAIN
# ============================================================================


def main() -> int:

    print()

    print("=" * 70)

    print("FORGE - Experiment 020-G: " "Declarative Identity and Uniqueness")

    print("=" * 70)

    print("Experiment:     " "020_declarative_generation_specification")

    print("Stage:          020-G")

    print("Purpose:        " "Declarative identity and uniqueness")

    print(f"Random seed:    {RANDOM_SEED}")

    print()

    print("Identity vocabulary:")

    for value in sorted(IDENTITY_SEMANTICS):

        print(f"  {value}")

    print()

    results = {
        "sequential_id": (validate_sequential_id()),
        "uuid": (validate_uuid()),
        "stability": (validate_stability()),
        "seed_sensitivity": (validate_seed_sensitivity()),
        "surrogate_key": (validate_surrogate_key()),
        "natural_key": (validate_natural_key()),
        "composite_id": (validate_composite_id()),
        "unique_semantic": (validate_unique_semantic()),
        "primary_key_properties": (validate_primary_key_properties()),
        "field_order_independence": (validate_field_order_independence()),
        "vocabulary_safety": (validate_vocabulary_safety()),
        "foreign_key_boundary": (validate_foreign_key_boundary()),
    }

    labels = {
        "sequential_id": ("SEQUENTIAL_ID generation"),
        "uuid": ("UUID generation"),
        "stability": ("Stable identity"),
        "seed_sensitivity": ("Seed sensitivity"),
        "surrogate_key": ("SURROGATE_KEY"),
        "natural_key": ("NATURAL_KEY"),
        "composite_id": ("COMPOSITE_ID"),
        "unique_semantic": ("UNIQUE enforcement"),
        "primary_key_properties": ("PRIMARY_KEY properties"),
        "field_order_independence": ("Field-order independence"),
        "vocabulary_safety": ("Vocabulary safety"),
        "foreign_key_boundary": ("FOREIGN_KEY boundary"),
    }

    print("Identity / uniqueness validation:")

    for key, result in results.items():

        print(f"  " f"{labels[key]:<32}" f"{result['status']}")

    print()

    overall = all(result["status"] == "PASS" for result in results.values())

    print("Experiment result:")

    print(
        f"  Identity generation:       "
        f"{'PASS' if all(results[key]['status'] == 'PASS' for key in ['sequential_id', 'uuid', 'surrogate_key', 'natural_key', 'composite_id']) else 'FAIL'}"
    )

    print(
        f"  Uniqueness:                "
        f"{'PASS' if results['unique_semantic']['status'] == 'PASS' else 'FAIL'}"
    )

    print(
        f"  Primary-key semantics:     "
        f"{'PASS' if results['primary_key_properties']['status'] == 'PASS' else 'FAIL'}"
    )

    print(f"  Stability:                 " f"{results['stability']['status']}")

    print(
        f"  Field-order independence:  "
        f"{results['field_order_independence']['status']}"
    )

    print(f"  Configuration safety:      " f"{results['vocabulary_safety']['status']}")

    print(f"  Overall:                   " f"{'PASS' if overall else 'FAIL'}")

    # ------------------------------------------------------------------------
    # Output
    # ------------------------------------------------------------------------

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    payload = {
        "experiment": ("020_declarative_generation_specification"),
        "stage": "020-G",
        "purpose": ("Declarative identity " "and uniqueness"),
        "random_seed": RANDOM_SEED,
        "identity_vocabulary": sorted(IDENTITY_SEMANTICS),
        "results": results,
        "architectural_conclusion": (
            "Identity semantics can be "
            "represented independently "
            "from business entities. "
            "Sequential, UUID, surrogate, "
            "natural, and composite "
            "identities can be generated "
            "and validated generically. "
            "Foreign-key identity is "
            "recognized here, while "
            "relationship resolution "
            "remains a separate capability."
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
