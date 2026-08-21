"""
FORGE - Experiment 020-D: Declarative Field Generation
========================================================

Purpose
-------
This experiment proves that a generic field generator can interpret
declarative FORGE field specifications and generate values without
field-specific or entity-specific generation logic.

Stage
-----
020-D - Declarative Field Generation

Relationship to previous stages
--------------------------------
020-A established the declarative FORGE specification and controlled
vocabulary.

020-B / 020-B.1 established runtime capability assessment.

020-C established the declarative rule and expression engine.

020-C.1 hardened and validated expression evaluation.

020-D introduces the first executable generation layer.

Research Question
-----------------
Can a generic field-generation engine interpret a declarative field
specification and generate values using type, strategy, distribution,
and parameters without embedding knowledge of the business field
itself?

Hypothesis
----------
A generic generation engine can generate multiple field types using
declarative specifications and shared generation strategies.

The engine should not require logic such as:

    if field_name == "CUSTOMER_ID":
        ...

or:

    if field_name == "UNIT_PRICE":
        ...

Generation behavior should be determined by the specification.

The hypothesis is supported if:

    - multiple field types can be generated
    - multiple generation strategies can be executed
    - multiple distributions can be executed
    - generated values satisfy their declared types
    - categorical values remain within their declared vocabulary
    - sequential values are deterministic
    - seeded random generation is reproducible
    - NULL generation behaves explicitly
    - the same generator can operate on unrelated field names

The hypothesis is rejected if generation requires field-specific
business logic or if the same declarative specification produces
different results under the same seed.

Scope
-----
Included:

    - INTEGER
    - DECIMAL
    - FLOAT
    - STRING
    - BOOLEAN
    - DATE
    - DATETIME
    - TIME
    - CATEGORICAL
    - ENUM
    - CODE
    - PERCENTAGE
    - CURRENCY
    - CONSTANT
    - SEQUENTIAL
    - RANDOM
    - NULL
    - UNIFORM
    - NORMAL
    - DISCRETE_UNIFORM
    - CATEGORICAL
    - deterministic generation
    - type validation
    - generation reproducibility

Excluded:

    - parent/child references
    - foreign-key generation
    - LOOKUP
    - CONDITIONAL generation
    - DERIVED fields
    - FORMULA fields
    - TRANSFORM fields
    - cross-field dependencies
    - relationship generation
    - scenario overrides
    - statistical correlation
    - provenance
    - full dataset validation

These capabilities will be addressed by later stages of Experiment 020.

Experiment
----------
020-D - Declarative Field Generation

Author
------
Ranjoy Sen

Status
------
Experimental

How to Run
----------
From the repository root:

    uv run python experiments/020_declarative_generation_specification/experiment-020-D.py

Output
------
Generated validation results are written to:

    experiments/020_declarative_generation_specification/output/

Important
---------
The generated values are synthetic and domain-neutral.

This experiment intentionally tests the generation engine independently
of business-specific entities such as CUSTOMER or ORDER.
"""

from __future__ import annotations

import json
import random
import sys
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any

# ============================================================================
# CONSTANTS
# ============================================================================

EXPERIMENT_DIR = Path(__file__).resolve().parent

OUTPUT_DIR = EXPERIMENT_DIR / "output"

RESULT_OUTPUT_PATH = OUTPUT_DIR / "field_generation_results.json"

RANDOM_SEED = 42


# ============================================================================
# EXCEPTIONS
# ============================================================================


class GenerationError(Exception):
    """Base exception for field generation."""


class UnsupportedGenerationError(GenerationError):
    """Raised when a valid vocabulary capability is not executable."""


class InvalidFieldSpecificationError(GenerationError):
    """Raised when a field specification is invalid."""


class GeneratedTypeError(GenerationError):
    """Raised when a generated value violates its declared type."""


# ============================================================================
# CONTROLLED VOCABULARY
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
    "UNIFORM",
    "NORMAL",
    "DISCRETE_UNIFORM",
    "CATEGORICAL",
}


# ============================================================================
# FIELD SPECIFICATION
# ============================================================================


@dataclass(frozen=True)
class FieldSpecification:

    name: str
    type: str
    strategy: str

    distribution: str | None = None

    parameters: dict[str, Any] | None = None

    semantic: str | None = None


# ============================================================================
# GENERIC FIELD GENERATOR
# ============================================================================


class DeclarativeFieldGenerator:
    """
    Generic field generator.

    The generator knows how to interpret FORGE vocabulary.

    It deliberately does not know what a particular field means.

    For example, there is no CUSTOMER_ID or UNIT_PRICE implementation.
    """

    def __init__(
        self,
        seed: int = RANDOM_SEED,
    ) -> None:

        self.seed = seed

        self.random = random.Random(seed)

    # ------------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------------

    def generate(
        self,
        specification: FieldSpecification,
        count: int,
    ) -> list[Any]:

        self.validate_specification(specification)

        if count < 0:

            raise InvalidFieldSpecificationError("Record count cannot be negative.")

        strategy = specification.strategy

        if strategy not in (EXECUTABLE_STRATEGIES):

            raise UnsupportedGenerationError(
                f"Strategy '{strategy}' " "is not executable in 020-D."
            )

        if strategy == "CONSTANT":

            values = self._generate_constant(
                specification,
                count,
            )

        elif strategy == "SEQUENTIAL":

            values = self._generate_sequential(
                specification,
                count,
            )

        elif strategy == "RANDOM":

            values = self._generate_random(
                specification,
                count,
            )

        elif strategy == "NULL":

            values = [None for _ in range(count)]

        else:

            raise UnsupportedGenerationError(
                f"Strategy '{strategy}' " "is not executable."
            )

        self.validate_generated_values(
            specification,
            values,
        )

        return values

    # ------------------------------------------------------------------------
    # Specification validation
    # ------------------------------------------------------------------------

    def validate_specification(
        self,
        specification: FieldSpecification,
    ) -> None:

        if not specification.name:

            raise InvalidFieldSpecificationError("Field name cannot be empty.")

        if specification.type not in EXECUTABLE_TYPES:

            raise UnsupportedGenerationError(
                f"Type '{specification.type}' " "is not executable in 020-D."
            )

        if specification.strategy not in EXECUTABLE_STRATEGIES:

            raise UnsupportedGenerationError(
                f"Strategy "
                f"'{specification.strategy}' "
                "is not executable in 020-D."
            )

        if (
            specification.distribution is not None
            and specification.distribution not in EXECUTABLE_DISTRIBUTIONS
        ):

            raise UnsupportedGenerationError(
                f"Distribution "
                f"'{specification.distribution}' "
                "is not executable in 020-D."
            )

    # ------------------------------------------------------------------------
    # Strategies
    # ------------------------------------------------------------------------

    def _generate_constant(
        self,
        specification: FieldSpecification,
        count: int,
    ) -> list[Any]:

        parameters = specification.parameters or {}

        if "value" not in parameters:

            raise InvalidFieldSpecificationError(
                "CONSTANT strategy requires " "'value'."
            )

        raw_value = parameters["value"]

        value = self._coerce_type(
            specification.type,
            raw_value,
        )

        return [value for _ in range(count)]

    def _generate_sequential(
        self,
        specification: FieldSpecification,
        count: int,
    ) -> list[Any]:

        parameters = specification.parameters or {}

        start = parameters.get(
            "start",
            1,
        )

        step = parameters.get(
            "step",
            1,
        )

        prefix = parameters.get(
            "prefix",
            "",
        )

        values = []

        for index in range(count):

            sequence_value = start + (index * step)

            if specification.type in {
                "IDENTIFIER",
                "CODE",
                "STRING",
            }:

                value = f"{prefix}" f"{sequence_value}"

            else:

                value = sequence_value

            values.append(
                self._coerce_type(
                    specification.type,
                    value,
                )
            )

        return values

    def _generate_random(
        self,
        specification: FieldSpecification,
        count: int,
    ) -> list[Any]:

        parameters = specification.parameters or {}

        distribution = specification.distribution or "UNIFORM"

        if distribution not in (EXECUTABLE_DISTRIBUTIONS):

            raise UnsupportedGenerationError(
                f"Distribution " f"'{distribution}' " "is not executable."
            )

        values = []

        for _ in range(count):

            raw_value = self._sample_distribution(
                distribution,
                specification,
                parameters,
            )

            values.append(
                self._coerce_type(
                    specification.type,
                    raw_value,
                )
            )

        return values

    # ------------------------------------------------------------------------
    # Distribution execution
    # ------------------------------------------------------------------------

    def _sample_distribution(
        self,
        distribution: str,
        specification: FieldSpecification,
        parameters: dict[str, Any],
    ) -> Any:

        if distribution == "UNIFORM":

            minimum = parameters.get(
                "min",
                0,
            )

            maximum = parameters.get(
                "max",
                1,
            )

            return self.random.uniform(
                minimum,
                maximum,
            )

        if distribution == "NORMAL":

            mean = parameters.get(
                "mean",
                0,
            )

            stddev = parameters.get(
                "stddev",
                1,
            )

            return self.random.gauss(
                mean,
                stddev,
            )

        if distribution == "DISCRETE_UNIFORM":

            minimum = int(
                parameters.get(
                    "min",
                    0,
                )
            )

            maximum = int(
                parameters.get(
                    "max",
                    1,
                )
            )

            return self.random.randint(
                minimum,
                maximum,
            )

        if distribution == "CATEGORICAL":

            categories = parameters.get("values")

            if not categories:

                raise InvalidFieldSpecificationError(
                    "CATEGORICAL distribution " "requires 'values'."
                )

            weights = parameters.get("weights")

            if weights is not None:

                if len(weights) != len(categories):

                    raise InvalidFieldSpecificationError(
                        "CATEGORICAL weights " "must match values."
                    )

                return self.random.choices(
                    categories,
                    weights=weights,
                    k=1,
                )[0]

            return self.random.choice(categories)

        raise UnsupportedGenerationError(
            f"Distribution " f"'{distribution}' " "is not executable."
        )

    # ------------------------------------------------------------------------
    # Type coercion
    # ------------------------------------------------------------------------

    def _coerce_type(
        self,
        field_type: str,
        value: Any,
    ) -> Any:

        if value is None:

            return None

        if field_type == "INTEGER":

            return int(round(float(value)))

        if field_type in {
            "DECIMAL",
            "CURRENCY",
        }:

            return round(
                float(value),
                2,
            )

        if field_type == "FLOAT":

            return float(value)

        if field_type == "BOOLEAN":

            if isinstance(
                value,
                bool,
            ):

                return value

            if isinstance(
                value,
                str,
            ):

                normalized = value.strip().lower()

                if normalized in {
                    "true",
                    "1",
                    "yes",
                }:

                    return True

                if normalized in {
                    "false",
                    "0",
                    "no",
                }:

                    return False

            return bool(value)

        if field_type in {
            "STRING",
            "IDENTIFIER",
            "CODE",
            "ENUM",
            "CATEGORICAL",
        }:

            return str(value)

        if field_type == "PERCENTAGE":

            numeric = float(value)

            return round(
                numeric,
                2,
            )

        if field_type == "DATE":

            if isinstance(
                value,
                date,
            ) and not isinstance(
                value,
                datetime,
            ):

                return value

            return date.fromisoformat(str(value))

        if field_type == "DATETIME":

            if isinstance(
                value,
                datetime,
            ):

                return value

            return datetime.fromisoformat(str(value))

        if field_type == "TIME":

            if isinstance(
                value,
                time,
            ):

                return value

            return time.fromisoformat(str(value))

        raise UnsupportedGenerationError(f"Type '{field_type}' " "cannot be coerced.")

    # ------------------------------------------------------------------------
    # Generated-value validation
    # ------------------------------------------------------------------------

    def validate_generated_values(
        self,
        specification: FieldSpecification,
        values: list[Any],
    ) -> None:

        for value in values:

            if value is None:

                continue

            if not self._matches_type(
                specification.type,
                value,
            ):

                raise GeneratedTypeError(
                    f"Field "
                    f"'{specification.name}' "
                    f"declared as "
                    f"{specification.type} "
                    f"generated invalid value "
                    f"{value!r}."
                )

            parameters = specification.parameters or {}

            if specification.distribution == "CATEGORICAL":

                allowed = parameters.get(
                    "values",
                    [],
                )

                if value not in allowed:

                    raise GeneratedTypeError(
                        f"Value {value!r} "
                        "is outside the declared "
                        "categorical vocabulary."
                    )

    def _matches_type(
        self,
        field_type: str,
        value: Any,
    ) -> bool:

        if field_type == "INTEGER":
            return isinstance(
                value,
                int,
            ) and not isinstance(
                value,
                bool,
            )

        if field_type in {
            "DECIMAL",
            "CURRENCY",
            "PERCENTAGE",
            "FLOAT",
        }:

            return isinstance(
                value,
                (
                    int,
                    float,
                ),
            ) and not isinstance(
                value,
                bool,
            )

        if field_type == "BOOLEAN":
            return isinstance(
                value,
                bool,
            )

        if field_type in {
            "STRING",
            "IDENTIFIER",
            "CODE",
            "ENUM",
            "CATEGORICAL",
        }:

            return isinstance(
                value,
                str,
            )

        if field_type == "DATE":

            return isinstance(
                value,
                date,
            ) and not isinstance(
                value,
                datetime,
            )

        if field_type == "DATETIME":

            return isinstance(
                value,
                datetime,
            )

        if field_type == "TIME":

            return isinstance(
                value,
                time,
            )

        return False


# ============================================================================
# TEST SPECIFICATIONS
# ============================================================================


def build_specifications() -> list[FieldSpecification]:

    return [
        FieldSpecification(
            name="FIELD_INTEGER",
            type="INTEGER",
            strategy="RANDOM",
            distribution="DISCRETE_UNIFORM",
            parameters={
                "min": 1,
                "max": 100,
            },
        ),
        FieldSpecification(
            name="FIELD_DECIMAL",
            type="DECIMAL",
            strategy="RANDOM",
            distribution="UNIFORM",
            parameters={
                "min": 10,
                "max": 500,
            },
        ),
        FieldSpecification(
            name="FIELD_FLOAT",
            type="FLOAT",
            strategy="RANDOM",
            distribution="NORMAL",
            parameters={
                "mean": 100,
                "stddev": 15,
            },
        ),
        FieldSpecification(
            name="FIELD_STRING",
            type="STRING",
            strategy="CONSTANT",
            parameters={
                "value": "FORGE",
            },
        ),
        FieldSpecification(
            name="FIELD_BOOLEAN",
            type="BOOLEAN",
            strategy="RANDOM",
            distribution="CATEGORICAL",
            parameters={
                "values": [
                    True,
                    False,
                ],
                "weights": [
                    0.7,
                    0.3,
                ],
            },
        ),
        FieldSpecification(
            name="FIELD_DATE",
            type="DATE",
            strategy="CONSTANT",
            parameters={
                "value": "2026-01-01",
            },
        ),
        FieldSpecification(
            name="FIELD_DATETIME",
            type="DATETIME",
            strategy="CONSTANT",
            parameters={
                "value": ("2026-01-01T12:00:00"),
            },
        ),
        FieldSpecification(
            name="FIELD_TIME",
            type="TIME",
            strategy="CONSTANT",
            parameters={
                "value": "12:30:00",
            },
        ),
        FieldSpecification(
            name="FIELD_CATEGORY",
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
            name="FIELD_ENUM",
            type="ENUM",
            strategy="RANDOM",
            distribution="CATEGORICAL",
            parameters={
                "values": [
                    "NEW",
                    "ACTIVE",
                    "CLOSED",
                ],
            },
        ),
        FieldSpecification(
            name="FIELD_CODE",
            type="CODE",
            strategy="SEQUENTIAL",
            parameters={
                "start": 1,
                "step": 1,
                "prefix": "C-",
            },
        ),
        FieldSpecification(
            name="FIELD_IDENTIFIER",
            type="IDENTIFIER",
            strategy="SEQUENTIAL",
            parameters={
                "start": 1,
                "step": 1,
                "prefix": "ID-",
            },
        ),
        FieldSpecification(
            name="FIELD_PERCENTAGE",
            type="PERCENTAGE",
            strategy="RANDOM",
            distribution="UNIFORM",
            parameters={
                "min": 0,
                "max": 100,
            },
        ),
        FieldSpecification(
            name="FIELD_CURRENCY",
            type="CURRENCY",
            strategy="RANDOM",
            distribution="UNIFORM",
            parameters={
                "min": 10,
                "max": 10000,
            },
        ),
        FieldSpecification(
            name="FIELD_NULL",
            type="STRING",
            strategy="NULL",
        ),
    ]


# ============================================================================
# VALIDATION
# ============================================================================


def validate_generation(
    generator: DeclarativeFieldGenerator,
    specification: FieldSpecification,
    values: list[Any],
) -> dict[str, Any]:

    result = {
        "field": specification.name,
        "type": specification.type,
        "strategy": specification.strategy,
        "distribution": specification.distribution,
        "record_count": len(values),
        "generated": True,
        "type_valid": True,
        "constraints_valid": True,
        "sample": [_serialize(value) for value in values[:5]],
    }

    try:

        generator.validate_generated_values(
            specification,
            values,
        )

    except Exception as exc:

        result["type_valid"] = False

        result["generated"] = False

        result["error"] = str(exc)

    if specification.strategy == "NULL":

        result["null_behavior_valid"] = all(value is None for value in values)

    else:

        result["null_behavior_valid"] = True

    return result


# ============================================================================
# SERIALIZATION
# ============================================================================


def _serialize(
    value: Any,
) -> Any:

    if isinstance(
        value,
        (
            date,
            datetime,
            time,
        ),
    ):

        return value.isoformat()

    return value


# ============================================================================
# REPRODUCIBILITY
# ============================================================================


def validate_reproducibility(
    specifications: list[FieldSpecification],
) -> dict[str, Any]:

    generator_a = DeclarativeFieldGenerator(seed=RANDOM_SEED)

    generator_b = DeclarativeFieldGenerator(seed=RANDOM_SEED)

    results = []

    for specification in specifications:

        values_a = generator_a.generate(
            specification,
            25,
        )

        values_b = generator_b.generate(
            specification,
            25,
        )

        results.append(
            {
                "field": specification.name,
                "deterministic": (values_a == values_b),
            }
        )

    passed = all(result["deterministic"] for result in results)

    return {
        "status": ("PASS" if passed else "FAIL"),
        "fields": results,
    }


# ============================================================================
# FIELD-AGNOSTICITY
# ============================================================================


def validate_field_agnosticism() -> dict[
    str,
    Any,
]:

    generator = DeclarativeFieldGenerator(seed=RANDOM_SEED)

    specification_a = FieldSpecification(
        name="CUSTOMER_SCORE",
        type="DECIMAL",
        strategy="RANDOM",
        distribution="UNIFORM",
        parameters={
            "min": 0,
            "max": 100,
        },
    )

    specification_b = FieldSpecification(
        name="ENGINE_TEMPERATURE",
        type="DECIMAL",
        strategy="RANDOM",
        distribution="UNIFORM",
        parameters={
            "min": 0,
            "max": 100,
        },
    )

    values_a = generator.generate(
        specification_a,
        10,
    )

    generator = DeclarativeFieldGenerator(seed=RANDOM_SEED)

    values_b = generator.generate(
        specification_b,
        10,
    )

    identical = values_a == values_b

    return {
        "status": ("PASS" if identical else "FAIL"),
        "field_a": specification_a.name,
        "field_b": specification_b.name,
        "same_specification_behavior": (identical),
    }


# ============================================================================
# MAIN
# ============================================================================


def main() -> int:

    print()
    print("=" * 70)

    print("FORGE - Experiment 020-D: " "Declarative Field Generation")

    print("=" * 70)

    print("Experiment:     " "020_declarative_generation_specification")

    print("Stage:          020-D")

    print("Purpose:        " "Generic declarative field generation")

    print(f"Random seed:    " f"{RANDOM_SEED}")

    print()

    print("Executable capabilities:")

    print("  Types:         " + ", ".join(sorted(EXECUTABLE_TYPES)))

    print("  Strategies:    " + ", ".join(sorted(EXECUTABLE_STRATEGIES)))

    print("  Distributions: " + ", ".join(sorted(EXECUTABLE_DISTRIBUTIONS)))

    print()

    generator = DeclarativeFieldGenerator(seed=RANDOM_SEED)

    specifications = build_specifications()

    results = []

    print("Field generation:")

    for specification in specifications:

        try:

            values = generator.generate(
                specification,
                10,
            )

            validation = validate_generation(
                generator,
                specification,
                values,
            )

            result = (
                validation["generated"]
                and validation["type_valid"]
                and validation["null_behavior_valid"]
            )

            print(
                f"  "
                f"{specification.name:<24}"
                f"type={specification.type:<12}"
                f"strategy={specification.strategy:<12}"
                f"distribution="
                f"{str(specification.distribution):<20}"
                f"{'PASS' if result else 'FAIL'}"
            )

            if result:

                print(f"      sample: " f"{validation['sample']}")

            else:

                print(f"      error: " f"{validation.get('error')}")

            results.append(validation)

        except Exception as exc:

            print(f"  " f"{specification.name:<24}" f"FAIL")

            print(f"      error: " f"{type(exc).__name__}: " f"{exc}")

            results.append(
                {
                    "field": (specification.name),
                    "generated": False,
                    "type_valid": False,
                    "null_behavior_valid": False,
                    "error": str(exc),
                }
            )

    print()

    print("Field-agnostic generation validation:")

    agnostic = validate_field_agnosticism()

    print(
        f"  Same specification behavior "
        f"across unrelated field names: "
        f"{agnostic['status']}"
    )

    print()

    print("Reproducibility validation:")

    reproducibility = validate_reproducibility(specifications)

    print(f"  Seeded generation: " f"{reproducibility['status']}")

    print()

    field_generation_pass = all(
        result.get(
            "generated",
            False,
        )
        and result.get(
            "type_valid",
            False,
        )
        and result.get(
            "null_behavior_valid",
            False,
        )
        for result in results
    )

    overall = (
        field_generation_pass
        and agnostic["status"] == "PASS"
        and reproducibility["status"] == "PASS"
    )

    print("Experiment result:")

    print(
        f"  Field generation:       " f"{'PASS' if field_generation_pass else 'FAIL'}"
    )

    print(f"  Field agnosticism:      " f"{agnostic['status']}")

    print(f"  Reproducibility:        " f"{reproducibility['status']}")

    print(f"  Overall:                " f"{'PASS' if overall else 'FAIL'}")

    print()

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    payload = {
        "experiment": ("020_declarative_generation_specification"),
        "stage": "020-D",
        "purpose": ("Generic declarative " "field generation"),
        "seed": RANDOM_SEED,
        "capabilities": {
            "types": sorted(EXECUTABLE_TYPES),
            "strategies": sorted(EXECUTABLE_STRATEGIES),
            "distributions": sorted(EXECUTABLE_DISTRIBUTIONS),
        },
        "results": results,
        "field_agnosticism": (agnostic),
        "reproducibility": (reproducibility),
        "summary": {
            "fields_tested": len(results),
            "fields_passed": sum(
                result.get(
                    "generated",
                    False,
                )
                and result.get(
                    "type_valid",
                    False,
                )
                and result.get(
                    "null_behavior_valid",
                    False,
                )
                for result in results
            ),
            "field_generation": ("PASS" if field_generation_pass else "FAIL"),
            "field_agnosticism": (agnostic["status"]),
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
