"""
FORGE - Experiment 020-F: Population and Nullability
======================================================

Purpose
-------
This experiment validates population and nullability as first-class
declarative generation controls.

Population and nullability are deliberately treated as controls around
field generation rather than as domain-specific generation logic.

The experiment validates:

    - POPULATION_COUNT
    - POPULATION_RATE
    - ALWAYS
    - NEVER
    - OPTIONAL
    - NULLABLE
    - NOT_NULL
    - deterministic population decisions
    - population rate tolerance
    - interaction between population and generated values
    - field-order independence

Stage
-----
020-F - Population and Nullability

Research Question
-----------------
Can FORGE declaratively control whether records and field values are
populated while preserving deterministic and generic generation behavior?

Hypothesis
----------
Population and nullability can be represented independently from the
underlying field generation strategy.

The same field generation logic should therefore support:

    - always populated fields
    - never populated fields
    - nullable fields
    - non-null fields
    - probabilistically populated fields

The population decision must be deterministic when a seed is supplied.

Scope
-----
Included:

    - record population count
    - field population rate
    - deterministic population decisions
    - nullability semantics
    - population-rate validation
    - count validation
    - field-order independence
    - interaction with existing field generation

Excluded:

    - relationships
    - foreign keys
    - parent dependencies
    - conditional dependencies
    - statistical correlation
    - scenario overrides
    - provenance
    - validation evidence

Those capabilities are addressed by later experiments.

Important Architectural Principle
---------------------------------
Population/nullability controls must not be coupled to a particular
business domain or field name.

The same mechanism must work for:

    CUSTOMER.EMAIL
    PRODUCT.DESCRIPTION
    ORDER.COMMENT
    SENSOR.READING
    EMPLOYEE.PHONE

without field-specific generation code.

Author
------
Ranjoy Sen

Status
------
Experimental

How to Run
----------
From the repository root:

    uv run python experiments/020_declarative_generation_specification/experiment-020-F.py

Output
------
Results are written to:

    experiments/020_declarative_generation_specification/output/
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import math
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

RESULT_OUTPUT_PATH = OUTPUT_DIR / "population_nullability_results.json"

RANDOM_SEED = 42

DEFAULT_RECORD_COUNT = 1000


# ============================================================================
# LOAD 020-D FIELD ENGINE
# ============================================================================


def load_field_engine():
    """
    Load the generic field generator from Experiment 020-D.

    020-F owns population/nullability behavior while 020-D owns the
    underlying field-value generation.
    """

    spec = importlib.util.spec_from_file_location(
        "forge_experiment_020_d_f",
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
# CONTROLLED VOCABULARY
# ============================================================================

POPULATION_CONTROLS = {
    "POPULATION_RATE",
    "POPULATION_COUNT",
}

NULLABILITY_CONTROLS = {
    "ALWAYS",
    "NEVER",
    "OPTIONAL",
    "NULLABLE",
    "NOT_NULL",
}


# ============================================================================
# DECLARATIVE SPECIFICATION
# ============================================================================


@dataclass(frozen=True)
class PopulationSpecification:
    """
    Population configuration.

    Exactly one population mode is normally supplied:

        POPULATION_COUNT
        POPULATION_RATE

    If neither is supplied, the requested record count is used.
    """

    mode: str = "POPULATION_COUNT"

    value: float | int = DEFAULT_RECORD_COUNT


@dataclass(frozen=True)
class NullabilitySpecification:
    """
    Declarative nullability configuration.

    population_rate is interpreted as the probability that a field
    receives a generated value.

    Therefore:

        1.0 -> always populated
        0.0 -> never populated
        0.5 -> approximately half populated
    """

    mode: str = "NOT_NULL"

    population_rate: float = 1.0


@dataclass(frozen=True)
class DeclarativeField:
    """
    Field specification combining value generation with population
    and nullability controls.
    """

    specification: Any
    nullability: NullabilitySpecification


@dataclass(frozen=True)
class EntitySpecification:
    name: str
    fields: tuple[DeclarativeField, ...]
    population: PopulationSpecification


# ============================================================================
# DETERMINISTIC STREAM
# ============================================================================


def derive_seed(
    master_seed: int,
    namespace: str,
) -> int:
    """
    Derive a deterministic seed from a master seed and namespace.

    This follows the same principle established by 020-E.1.

    Population decisions therefore do not consume the field value
    generation stream.
    """

    material = (f"{master_seed}:{namespace}").encode("utf-8")

    digest = hashlib.sha256(material).digest()

    return int.from_bytes(
        digest[:8],
        byteorder="big",
    )


class DeterministicRandom:
    """
    Small deterministic random helper.

    A local pseudo-random implementation is used instead of sharing
    the field generator's random stream.
    """

    def __init__(
        self,
        seed: int,
    ) -> None:

        # Import locally to keep the experiment dependencies explicit.
        import random

        self._random = random.Random(seed)

    def random(self) -> float:

        return self._random.random()


# ============================================================================
# POPULATION / NULLABILITY ENGINE
# ============================================================================


class PopulationNullabilityEngine:
    """
    Generic population/nullability controller.

    This component has no knowledge of business entities.
    """

    def __init__(
        self,
        seed: int = RANDOM_SEED,
    ) -> None:

        self.seed = seed

    # ------------------------------------------------------------------------
    # Record count
    # ------------------------------------------------------------------------

    def resolve_record_count(
        self,
        population: PopulationSpecification,
        requested_count: int,
    ) -> int:
        """
        Resolve the number of records to generate.
        """

        if requested_count < 0:
            raise ValueError("Requested record count cannot be negative.")

        if population.mode == "POPULATION_COUNT":

            count = int(population.value)

            if count < 0:
                raise ValueError("POPULATION_COUNT cannot be negative.")

            return count

        if population.mode == "POPULATION_RATE":

            rate = float(population.value)

            if not 0.0 <= rate <= 1.0:
                raise ValueError("POPULATION_RATE must be " "between 0 and 1.")

            return round(requested_count * rate)

        raise ValueError(f"Unsupported population mode: " f"{population.mode}")

    # ------------------------------------------------------------------------
    # Population decision
    # ------------------------------------------------------------------------

    def should_populate(
        self,
        field_name: str,
        record_index: int,
        nullability: NullabilitySpecification,
    ) -> bool:
        """
        Determine whether a field receives a generated value.

        The decision is based on:

            master seed
            field identity
            record identity

        This ensures that population decisions are deterministic and
        independent of field declaration order.
        """

        mode = nullability.mode

        if mode == "ALWAYS":
            return True

        if mode == "NOT_NULL":
            return True

        if mode == "NEVER":
            return False

        if mode == "NULLABLE":

            rate = nullability.population_rate

            return self._rate_decision(
                field_name,
                record_index,
                rate,
            )

        if mode == "OPTIONAL":

            rate = nullability.population_rate

            return self._rate_decision(
                field_name,
                record_index,
                rate,
            )

        raise ValueError(f"Unsupported nullability mode: " f"{mode}")

    # ------------------------------------------------------------------------
    # Rate decision
    # ------------------------------------------------------------------------

    def _rate_decision(
        self,
        field_name: str,
        record_index: int,
        rate: float,
    ) -> bool:

        if not 0.0 <= rate <= 1.0:
            raise ValueError("Population rate must be " "between 0 and 1.")

        seed = derive_seed(
            self.seed,
            (f"population:" f"{field_name}:" f"{record_index}"),
        )

        random_source = DeterministicRandom(seed)

        return random_source.random() < rate


# ============================================================================
# RECORD GENERATOR
# ============================================================================


class PopulationAwareRecordGenerator:
    """
    Generic record generator combining:

        field generation
        population
        nullability
    """

    def __init__(
        self,
        seed: int = RANDOM_SEED,
    ) -> None:

        self.seed = seed

        self.population_engine = PopulationNullabilityEngine(seed=seed)

    def generate(
        self,
        specification: EntitySpecification,
        requested_count: int,
    ) -> list[dict[str, Any]]:

        record_count = self.population_engine.resolve_record_count(
            specification.population,
            requested_count,
        )

        field_values: dict[
            str,
            list[Any],
        ] = {}

        for field in specification.fields:

            field_name = field.specification.name

            field_seed = derive_seed(
                self.seed,
                f"value:{field_name}",
            )

            generator = DeclarativeFieldGenerator(seed=field_seed)

            field_values[field_name] = generator.generate(
                field.specification,
                record_count,
            )

        records: list[dict[str, Any]] = []

        for index in range(record_count):

            record: dict[str, Any] = {}

            for field in specification.fields:

                field_name = field.specification.name

                populated = self.population_engine.should_populate(
                    field_name,
                    index,
                    field.nullability,
                )

                if populated:

                    record[field_name] = field_values[field_name][index]

                else:

                    record[field_name] = None

            records.append(record)

        return records


# ============================================================================
# TEST SPECIFICATIONS
# ============================================================================


def build_base_field(
    name: str,
) -> Any:
    """
    Create a simple generic field.

    The name is intentionally arbitrary to prove that the population
    mechanism is field-agnostic.
    """

    return FieldSpecification(
        name=name,
        type="INTEGER",
        strategy="RANDOM",
        distribution="DISCRETE_UNIFORM",
        parameters={
            "min": 1,
            "max": 100,
        },
    )


def build_entity(
    population: PopulationSpecification,
    fields: tuple[DeclarativeField, ...],
) -> EntitySpecification:

    return EntitySpecification(
        name="GENERIC_ENTITY",
        fields=fields,
        population=population,
    )


# ============================================================================
# VALIDATION HELPERS
# ============================================================================


def count_non_null(
    records: list[dict[str, Any]],
    field_name: str,
) -> int:

    return sum(1 for record in records if record[field_name] is not None)


def count_null(
    records: list[dict[str, Any]],
    field_name: str,
) -> int:

    return sum(1 for record in records if record[field_name] is None)


def population_rate(
    records: list[dict[str, Any]],
    field_name: str,
) -> float:

    if not records:
        return 0.0

    return count_non_null(
        records,
        field_name,
    ) / len(records)


def rate_within_tolerance(
    observed: float,
    expected: float,
    tolerance: float,
) -> bool:

    return abs(observed - expected) <= tolerance


# ============================================================================
# VALIDATION 1: POPULATION COUNT
# ============================================================================


def validate_population_count() -> dict[str, Any]:

    entity = build_entity(
        PopulationSpecification(
            mode="POPULATION_COUNT",
            value=250,
        ),
        fields=(
            DeclarativeField(
                specification=build_base_field("VALUE"),
                nullability=(NullabilitySpecification(mode="NOT_NULL")),
            ),
        ),
    )

    generator = PopulationAwareRecordGenerator(seed=RANDOM_SEED)

    records = generator.generate(
        entity,
        requested_count=1000,
    )

    passed = len(records) == 250

    return {
        "status": ("PASS" if passed else "FAIL"),
        "requested_count": 1000,
        "configured_count": 250,
        "actual_count": len(records),
    }


# ============================================================================
# VALIDATION 2: POPULATION RATE
# ============================================================================


def validate_population_rate() -> dict[str, Any]:

    expected_rate = 0.70

    entity = build_entity(
        PopulationSpecification(
            mode="POPULATION_COUNT",
            value=5000,
        ),
        fields=(
            DeclarativeField(
                specification=build_base_field("OPTIONAL_VALUE"),
                nullability=(
                    NullabilitySpecification(
                        mode="OPTIONAL",
                        population_rate=(expected_rate),
                    )
                ),
            ),
        ),
    )

    generator = PopulationAwareRecordGenerator(seed=RANDOM_SEED)

    records = generator.generate(
        entity,
        requested_count=5000,
    )

    observed_rate = population_rate(
        records,
        "OPTIONAL_VALUE",
    )

    # A 5% tolerance is deliberately used for
    # a finite synthetic population.
    passed = rate_within_tolerance(
        observed_rate,
        expected_rate,
        tolerance=0.05,
    )

    return {
        "status": ("PASS" if passed else "FAIL"),
        "expected_rate": expected_rate,
        "observed_rate": observed_rate,
        "tolerance": 0.05,
        "populated": count_non_null(
            records,
            "OPTIONAL_VALUE",
        ),
        "null": count_null(
            records,
            "OPTIONAL_VALUE",
        ),
    }


# ============================================================================
# VALIDATION 3: ALWAYS
# ============================================================================


def validate_always() -> dict[str, Any]:

    entity = build_entity(
        PopulationSpecification(
            mode="POPULATION_COUNT",
            value=100,
        ),
        fields=(
            DeclarativeField(
                specification=build_base_field("ALWAYS_VALUE"),
                nullability=(NullabilitySpecification(mode="ALWAYS")),
            ),
        ),
    )

    records = PopulationAwareRecordGenerator(seed=RANDOM_SEED).generate(
        entity,
        requested_count=100,
    )

    null_count = count_null(
        records,
        "ALWAYS_VALUE",
    )

    passed = null_count == 0

    return {
        "status": ("PASS" if passed else "FAIL"),
        "null_count": null_count,
    }


# ============================================================================
# VALIDATION 4: NEVER
# ============================================================================


def validate_never() -> dict[str, Any]:

    entity = build_entity(
        PopulationSpecification(
            mode="POPULATION_COUNT",
            value=100,
        ),
        fields=(
            DeclarativeField(
                specification=build_base_field("NEVER_VALUE"),
                nullability=(NullabilitySpecification(mode="NEVER")),
            ),
        ),
    )

    records = PopulationAwareRecordGenerator(seed=RANDOM_SEED).generate(
        entity,
        requested_count=100,
    )

    non_null_count = count_non_null(
        records,
        "NEVER_VALUE",
    )

    passed = non_null_count == 0

    return {
        "status": ("PASS" if passed else "FAIL"),
        "non_null_count": non_null_count,
    }


# ============================================================================
# VALIDATION 5: NULLABLE
# ============================================================================


def validate_nullable() -> dict[str, Any]:

    entity = build_entity(
        PopulationSpecification(
            mode="POPULATION_COUNT",
            value=1000,
        ),
        fields=(
            DeclarativeField(
                specification=build_base_field("NULLABLE_VALUE"),
                nullability=(
                    NullabilitySpecification(
                        mode="NULLABLE",
                        population_rate=0.80,
                    )
                ),
            ),
        ),
    )

    records = PopulationAwareRecordGenerator(seed=RANDOM_SEED).generate(
        entity,
        requested_count=1000,
    )

    observed_rate = population_rate(
        records,
        "NULLABLE_VALUE",
    )

    passed = rate_within_tolerance(
        observed_rate,
        0.80,
        0.05,
    )

    return {
        "status": ("PASS" if passed else "FAIL"),
        "expected_population_rate": 0.80,
        "observed_population_rate": observed_rate,
        "tolerance": 0.05,
    }


# ============================================================================
# VALIDATION 6: NOT_NULL
# ============================================================================


def validate_not_null() -> dict[str, Any]:

    entity = build_entity(
        PopulationSpecification(
            mode="POPULATION_COUNT",
            value=1000,
        ),
        fields=(
            DeclarativeField(
                specification=build_base_field("REQUIRED_VALUE"),
                nullability=(NullabilitySpecification(mode="NOT_NULL")),
            ),
        ),
    )

    records = PopulationAwareRecordGenerator(seed=RANDOM_SEED).generate(
        entity,
        requested_count=1000,
    )

    null_count = count_null(
        records,
        "REQUIRED_VALUE",
    )

    passed = null_count == 0

    return {
        "status": ("PASS" if passed else "FAIL"),
        "null_count": null_count,
    }


# ============================================================================
# VALIDATION 7: OPTIONAL
# ============================================================================


def validate_optional() -> dict[str, Any]:

    entity = build_entity(
        PopulationSpecification(
            mode="POPULATION_COUNT",
            value=1000,
        ),
        fields=(
            DeclarativeField(
                specification=build_base_field("OPTIONAL_VALUE"),
                nullability=(
                    NullabilitySpecification(
                        mode="OPTIONAL",
                        population_rate=0.25,
                    )
                ),
            ),
        ),
    )

    records = PopulationAwareRecordGenerator(seed=RANDOM_SEED).generate(
        entity,
        requested_count=1000,
    )

    observed_rate = population_rate(
        records,
        "OPTIONAL_VALUE",
    )

    passed = rate_within_tolerance(
        observed_rate,
        0.25,
        0.05,
    )

    return {
        "status": ("PASS" if passed else "FAIL"),
        "expected_population_rate": 0.25,
        "observed_population_rate": observed_rate,
        "tolerance": 0.05,
    }


# ============================================================================
# VALIDATION 8: DETERMINISM
# ============================================================================


def validate_determinism() -> dict[str, Any]:

    entity = build_entity(
        PopulationSpecification(
            mode="POPULATION_COUNT",
            value=1000,
        ),
        fields=(
            DeclarativeField(
                specification=build_base_field("OPTIONAL_VALUE"),
                nullability=(
                    NullabilitySpecification(
                        mode="OPTIONAL",
                        population_rate=0.35,
                    )
                ),
            ),
        ),
    )

    generator_a = PopulationAwareRecordGenerator(seed=RANDOM_SEED)

    generator_b = PopulationAwareRecordGenerator(seed=RANDOM_SEED)

    records_a = generator_a.generate(
        entity,
        requested_count=1000,
    )

    records_b = generator_b.generate(
        entity,
        requested_count=1000,
    )

    passed = records_a == records_b

    return {
        "status": ("PASS" if passed else "FAIL"),
        "records_identical": passed,
    }


# ============================================================================
# VALIDATION 9: FIELD ORDER INDEPENDENCE
# ============================================================================


def validate_field_order_independence() -> dict[str, Any]:

    fields = (
        DeclarativeField(
            specification=build_base_field("FIELD_A"),
            nullability=(
                NullabilitySpecification(
                    mode="OPTIONAL",
                    population_rate=0.40,
                )
            ),
        ),
        DeclarativeField(
            specification=build_base_field("FIELD_B"),
            nullability=(
                NullabilitySpecification(
                    mode="OPTIONAL",
                    population_rate=0.70,
                )
            ),
        ),
        DeclarativeField(
            specification=build_base_field("FIELD_C"),
            nullability=(NullabilitySpecification(mode="NOT_NULL")),
        ),
    )

    entity_a = build_entity(
        PopulationSpecification(
            mode="POPULATION_COUNT",
            value=500,
        ),
        fields=fields,
    )

    entity_b = build_entity(
        PopulationSpecification(
            mode="POPULATION_COUNT",
            value=500,
        ),
        fields=tuple(reversed(fields)),
    )

    generator_a = PopulationAwareRecordGenerator(seed=RANDOM_SEED)

    generator_b = PopulationAwareRecordGenerator(seed=RANDOM_SEED)

    records_a = generator_a.generate(
        entity_a,
        requested_count=500,
    )

    records_b = generator_b.generate(
        entity_b,
        requested_count=500,
    )

    normalized_a = [
        {key: record[key] for key in sorted(record)} for record in records_a
    ]

    normalized_b = [
        {key: record[key] for key in sorted(record)} for record in records_b
    ]

    passed = normalized_a == normalized_b

    return {
        "status": ("PASS" if passed else "FAIL"),
        "records_identical": passed,
    }


# ============================================================================
# VALIDATION 10: INVALID CONFIGURATION
# ============================================================================


def validate_invalid_configuration() -> dict[str, Any]:

    engine = PopulationNullabilityEngine(seed=RANDOM_SEED)

    failures = []

    # Invalid rate.
    try:

        engine.should_populate(
            "FIELD",
            0,
            NullabilitySpecification(
                mode="OPTIONAL",
                population_rate=1.5,
            ),
        )

        failures.append("population rate > 1 accepted")

    except ValueError:
        pass

    # Invalid negative rate.
    try:

        engine.should_populate(
            "FIELD",
            0,
            NullabilitySpecification(
                mode="OPTIONAL",
                population_rate=-0.1,
            ),
        )

        failures.append("negative population rate accepted")

    except ValueError:
        pass

    # Invalid nullability vocabulary.
    try:

        engine.should_populate(
            "FIELD",
            0,
            NullabilitySpecification(mode="UNKNOWN"),
        )

        failures.append("unknown nullability mode accepted")

    except ValueError:
        pass

    passed = not failures

    return {
        "status": ("PASS" if passed else "FAIL"),
        "unexpected_acceptances": failures,
    }


# ============================================================================
# MAIN
# ============================================================================


def main() -> int:

    print()

    print("=" * 70)

    print("FORGE - Experiment 020-F: " "Population and Nullability")

    print("=" * 70)

    print("Experiment:     " "020_declarative_generation_specification")

    print("Stage:          020-F")

    print("Purpose:        " "Declarative population and nullability")

    print(f"Random seed:    {RANDOM_SEED}")

    print()

    print("Controlled vocabulary:")

    print("  Population:")

    for value in sorted(POPULATION_CONTROLS):
        print(f"    {value}")

    print("  Nullability:")

    for value in sorted(NULLABILITY_CONTROLS):
        print(f"    {value}")

    print()

    # ------------------------------------------------------------------------
    # Execute validations
    # ------------------------------------------------------------------------

    results = {
        "population_count": (validate_population_count()),
        "population_rate": (validate_population_rate()),
        "always": (validate_always()),
        "never": (validate_never()),
        "nullable": (validate_nullable()),
        "not_null": (validate_not_null()),
        "optional": (validate_optional()),
        "determinism": (validate_determinism()),
        "field_order_independence": (validate_field_order_independence()),
        "invalid_configuration": (validate_invalid_configuration()),
    }

    print("Population / nullability validation:")

    labels = {
        "population_count": ("Population count"),
        "population_rate": ("Population rate"),
        "always": ("ALWAYS semantics"),
        "never": ("NEVER semantics"),
        "nullable": ("NULLABLE semantics"),
        "not_null": ("NOT_NULL semantics"),
        "optional": ("OPTIONAL semantics"),
        "determinism": ("Deterministic population"),
        "field_order_independence": ("Field-order independence"),
        "invalid_configuration": ("Invalid configuration handling"),
    }

    for key, result in results.items():

        print(f"  " f"{labels[key]:<32}" f"{result['status']}")

    print()

    # ------------------------------------------------------------------------
    # Overall result
    # ------------------------------------------------------------------------

    overall = all(result["status"] == "PASS" for result in results.values())

    print("Experiment result:")

    print(f"  Population count:          " f"{results['population_count']['status']}")

    print(f"  Population rate:           " f"{results['population_rate']['status']}")

    print(
        f"  Nullability semantics:     "
        f"{'PASS' if all(results[key]['status'] == 'PASS' for key in ['always', 'never', 'nullable', 'not_null', 'optional']) else 'FAIL'}"
    )

    print(f"  Determinism:                " f"{results['determinism']['status']}")

    print(
        f"  Field-order independence:   "
        f"{results['field_order_independence']['status']}"
    )

    print(
        f"  Configuration safety:       "
        f"{results['invalid_configuration']['status']}"
    )

    print(f"  Overall:                    " f"{'PASS' if overall else 'FAIL'}")

    # ------------------------------------------------------------------------
    # Output
    # ------------------------------------------------------------------------

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    payload = {
        "experiment": ("020_declarative_generation_specification"),
        "stage": "020-F",
        "purpose": ("Population and nullability"),
        "random_seed": RANDOM_SEED,
        "controlled_vocabulary": {
            "population": sorted(POPULATION_CONTROLS),
            "nullability": sorted(NULLABILITY_CONTROLS),
        },
        "results": results,
        "architectural_conclusion": (
            "Population and nullability "
            "are independent declarative "
            "controls around field value "
            "generation. Population "
            "decisions use deterministic "
            "field- and record-specific "
            "streams and therefore do not "
            "implicitly depend on field "
            "declaration order."
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
