"""
FORGE - Experiment 020: Declarative Generation Specification
==============================================================

Purpose
-------
This experiment establishes the executable foundation of the FORGE
declarative generation model.

Stage
-----
020-B - Generic Type, Strategy and Distribution Generation

This stage extends 020-A by executing declarative field specifications
through generic generation engines.

The implementation is intentionally specification-driven.

There is no business logic for CUSTOMER, ORDER, PRODUCT, or any other
specific entity.

Architecture
------------
    specification.json
           |
           v
    SpecificationLoader
           |
           v
    VocabularyRegistry
           |
           v
    SpecificationValidator
           |
           v
    GenerationContext
           |
           v
    GenerationEngine
       /      |      \
      v       v       v
    Type   Strategy  Distribution
    Engine   Engine     Engine
           |
           v
      Generated Data

Design Principles
-----------------
- Specification over hard-coded business logic.
- Controlled vocabulary over arbitrary keywords.
- Registered vocabulary is distinct from executable vocabulary.
- Fail fast on invalid specifications.
- Deterministic generation through explicit random state.
- No entity-specific generation logic.
- Generic engines operate on metadata rather than field names.

Executable Scope
----------------
Types:

    INTEGER
    DECIMAL
    FLOAT
    STRING
    BOOLEAN
    DATE
    DATETIME
    TIME
    CATEGORICAL
    ENUM
    IDENTIFIER
    CODE
    PERCENTAGE
    CURRENCY

Generation strategies:

    CONSTANT
    SEQUENTIAL
    RANDOM
    NULL

Distributions:

    UNIFORM
    DISCRETE_UNIFORM
    NORMAL
    CATEGORICAL

Other vocabulary elements remain registered for later stages.

No machine learning, LLM, or real production data is used.

Experiment
----------
020 - Declarative Generation Specification

Author
------
Ranjoy Sen

Status
------
Experimental

How to Run
----------
From the repository root:

    uv run python experiments/020_declarative_generation_specification/experiment.py

Output
------
    experiments/020_declarative_generation_specification/output/

Important
---------
This stage focuses on generic value generation.

Relationships, advanced dependencies, rules, scenarios, validation
execution, statistical behavior, and provenance generation are handled
by later stages of Experiment 020.
"""

from __future__ import annotations

import json
import random
import sys
import uuid
from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta
from pathlib import Path
from typing import Any

# ============================================================================
# PATHS
# ============================================================================

EXPERIMENT_DIR = Path(__file__).resolve().parent
SPECIFICATION_PATH = EXPERIMENT_DIR / "specification.json"
OUTPUT_DIR = EXPERIMENT_DIR / "output"

VALIDATION_OUTPUT_PATH = OUTPUT_DIR / "generation_validation.json"

GENERATED_OUTPUT_PATH = OUTPUT_DIR / "generated_sample.json"


# ============================================================================
# EXCEPTIONS
# ============================================================================


class ForgeSpecificationError(Exception):
    """Base exception for FORGE specification failures."""


class SpecificationLoadError(ForgeSpecificationError):
    """Raised when the specification cannot be loaded."""


class StructuralValidationError(ForgeSpecificationError):
    """Raised when the specification structure is invalid."""


class GenerationError(ForgeSpecificationError):
    """Raised when a value cannot be generated."""


# ============================================================================
# CONTROLLED VOCABULARY
# ============================================================================


class VocabularyRegistry:
    """
    FORGE Controlled Vocabulary v1.

    This registry represents the vocabulary that the declarative
    specification is allowed to express.

    Executable support is intentionally smaller than the complete
    vocabulary at this stage.
    """

    VERSION = "1.0"

    TYPE_SYSTEM = {
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

    GENERATION_STRATEGIES = {
        "CONSTANT",
        "SEQUENTIAL",
        "RANDOM",
        "SAMPLE",
        "REFERENCE",
        "LOOKUP",
        "CONDITIONAL",
        "DERIVED",
        "FORMULA",
        "TRANSFORM",
        "COPY",
        "NULL",
    }

    DISTRIBUTIONS = {
        "UNIFORM",
        "NORMAL",
        "LOGNORMAL",
        "EXPONENTIAL",
        "GAMMA",
        "BETA",
        "WEIBULL",
        "TRIANGULAR",
        "DISCRETE_UNIFORM",
        "BINOMIAL",
        "POISSON",
        "CATEGORICAL",
        "EMPIRICAL",
        "TRUNCATED",
        "MIXTURE",
    }

    IDENTITY = {
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

    RELATIONSHIPS = {
        "1:1",
        "0:1",
        "1:N",
        "0:N",
        "N:M",
        "PARENT",
        "CHILD",
        "ASSOCIATIVE",
        "REQUIRED",
        "OPTIONAL",
        "DEPENDENT",
    }

    DEPENDENCIES = {
        "FIELD_DEPENDENCY",
        "CONDITIONAL_DEPENDENCY",
        "PARENT_DEPENDENCY",
        "CHILD_DEPENDENCY",
        "SEQUENTIAL_DEPENDENCY",
        "TEMPORAL_DEPENDENCY",
        "STATISTICAL_DEPENDENCY",
    }

    RULE_OPERATORS = {
        "EQUALS",
        "NOT_EQUALS",
        "GREATER_THAN",
        "LESS_THAN",
        "GREATER_OR_EQUAL",
        "LESS_OR_EQUAL",
        "BETWEEN",
        "IN",
        "NOT_IN",
        "IS_NULL",
        "IS_NOT_NULL",
        "AND",
        "OR",
        "NOT",
        "XOR",
        "IMPLIES",
        "IF",
        "THEN",
        "ELSE",
        "ADD",
        "SUBTRACT",
        "MULTIPLY",
        "DIVIDE",
        "MODULO",
        "ABS",
        "MIN",
        "MAX",
        "ROUND",
        "FLOOR",
        "CEILING",
        "CONCAT",
        "LENGTH",
        "CONTAINS",
        "STARTS_WITH",
        "ENDS_WITH",
        "MATCH",
        "UPPER",
        "LOWER",
        "TRIM",
        "REPLACE",
        "DATE_ADD",
        "DATE_SUBTRACT",
        "DATE_DIFF",
        "REFERENCE",
        "LOOKUP",
        "SAMPLE",
        "DERIVE",
    }

    POPULATION_NULLABILITY = {
        "POPULATION_RATE",
        "POPULATION_COUNT",
        "ALWAYS",
        "NEVER",
        "OPTIONAL",
        "NULLABLE",
        "NOT_NULL",
    }

    SCENARIOS = {
        "SCENARIO",
        "SCENARIO_PARAMETER",
        "SCENARIO_OVERRIDE",
        "SCENARIO_CONSTRAINT",
        "SCENARIO_DISTRIBUTION",
    }

    STATISTICAL_BEHAVIOR = {
        "CORRELATION",
        "TARGET_CORRELATION",
        "POSITIVE",
        "NEGATIVE",
        "PEARSON",
        "SPEARMAN",
    }

    VALIDATION_EVIDENCE = {
        "VALIDATION",
        "PROVENANCE",
        "REPRODUCIBILITY",
        "EVIDENCE_ID",
        "STRUCTURAL_VALID",
        "CONSTRAINT_VALID",
        "RELATIONSHIP_VALID",
        "DEPENDENCY_VALID",
        "DISTRIBUTION_VALID",
        "STATISTICAL_VALID",
        "PROVENANCE_VALID",
    }

    CATEGORIES = {
        "type_system": TYPE_SYSTEM,
        "generation_strategies": GENERATION_STRATEGIES,
        "distributions": DISTRIBUTIONS,
        "identity": IDENTITY,
        "relationships": RELATIONSHIPS,
        "dependencies": DEPENDENCIES,
        "rules": RULE_OPERATORS,
        "population_nullability": POPULATION_NULLABILITY,
        "scenarios": SCENARIOS,
        "statistical_behavior": STATISTICAL_BEHAVIOR,
        "validation_evidence": VALIDATION_EVIDENCE,
    }

    # ------------------------------------------------------------------
    # Executable vocabulary for 020-B
    # ------------------------------------------------------------------

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
        "DISCRETE_UNIFORM",
        "NORMAL",
        "CATEGORICAL",
    }

    @classmethod
    def is_supported(cls, value: str) -> bool:
        return any(value in values for values in cls.CATEGORIES.values())

    @classmethod
    def category_for(
        cls,
        value: str,
    ) -> str | None:

        for category, values in cls.CATEGORIES.items():
            if value in values:
                return category

        return None


# ============================================================================
# SPECIFICATION LOADER
# ============================================================================


class SpecificationLoader:
    """Load a FORGE JSON specification."""

    def __init__(self, path: Path) -> None:
        self.path = path

    def load(self) -> dict[str, Any]:

        if not self.path.exists():
            raise SpecificationLoadError(f"Specification not found: {self.path}")

        try:
            with self.path.open(
                "r",
                encoding="utf-8",
            ) as file:
                specification = json.load(file)

        except json.JSONDecodeError as exc:
            raise SpecificationLoadError(f"Invalid JSON: {exc}") from exc

        if not isinstance(specification, dict):
            raise SpecificationLoadError("Specification root must be an object.")

        return specification


# ============================================================================
# VALIDATION RESULT
# ============================================================================


@dataclass
class ValidationResult:
    category: str
    passed: bool
    errors: list[str] = field(default_factory=list)

    @property
    def status(self) -> str:
        return "PASS" if self.passed else "FAIL"


# ============================================================================
# SPECIFICATION VALIDATOR
# ============================================================================


class SpecificationValidator:
    """
    Validates the declarative specification.

    This validator is intentionally independent from the generation
    algorithms.
    """

    def validate(
        self,
        specification: dict[str, Any],
    ) -> list[ValidationResult]:

        return [
            self._validate_root(specification),
            self._validate_vocabulary(specification),
            self._validate_entities(specification),
            self._validate_relationships(specification),
            self._validate_rules(specification),
            self._validate_statistical_behavior(specification),
            self._validate_scenarios(specification),
            self._validate_validation(specification),
            self._validate_provenance(specification),
            self._validate_reproducibility(specification),
        ]

    # ------------------------------------------------------------------
    # Root
    # ------------------------------------------------------------------

    def _validate_root(
        self,
        specification: dict[str, Any],
    ) -> ValidationResult:

        required = {
            "specification",
            "generation_control",
            "vocabulary",
            "entities",
            "relationships",
            "rules",
            "validation",
            "provenance",
            "reproducibility",
        }

        errors: list[str] = []

        missing = sorted(required - specification.keys())

        if missing:
            errors.append(f"Missing sections: {missing}")

        metadata = specification.get("specification")

        if not isinstance(metadata, dict):
            errors.append("'specification' must be an object.")
        else:
            for key in (
                "name",
                "version",
                "experiment",
            ):
                if not metadata.get(key):
                    errors.append(f"specification.{key} is required.")

        return ValidationResult(
            "Specification structure",
            not errors,
            errors,
        )

    # ------------------------------------------------------------------
    # Vocabulary
    # ------------------------------------------------------------------

    def _validate_vocabulary(
        self,
        specification: dict[str, Any],
    ) -> ValidationResult:

        vocabulary = specification.get("vocabulary")

        if not isinstance(vocabulary, dict):
            return ValidationResult(
                "Controlled vocabulary",
                False,
                ["vocabulary must be an object."],
            )

        errors: list[str] = []

        if vocabulary.get("version") != (VocabularyRegistry.VERSION):
            errors.append("Unsupported vocabulary version.")

        for category, supported in VocabularyRegistry.CATEGORIES.items():

            declared = vocabulary.get(
                category,
                [],
            )

            if not isinstance(declared, list):
                errors.append(f"{category} must be a list.")
                continue

            unsupported = sorted(set(declared) - supported)

            if unsupported:
                errors.append(f"{category}: unsupported " f"{unsupported}")

        return ValidationResult(
            "Controlled vocabulary",
            not errors,
            errors,
        )

    # ------------------------------------------------------------------
    # Entities
    # ------------------------------------------------------------------

    def _validate_entities(
        self,
        specification: dict[str, Any],
    ) -> ValidationResult:

        entities = specification.get("entities")

        errors: list[str] = []

        if not isinstance(entities, list):
            return ValidationResult(
                "Entities and fields",
                False,
                ["entities must be a list."],
            )

        entity_names: set[str] = set()

        for entity in entities:

            if not isinstance(entity, dict):
                errors.append("Entity must be an object.")
                continue

            name = entity.get("name")

            if not name:
                errors.append("Entity missing name.")
                continue

            if name in entity_names:
                errors.append(f"Duplicate entity: {name}")

            entity_names.add(name)

            fields = entity.get("fields")

            if not isinstance(fields, list):
                errors.append(f"{name}: fields must be a list.")
                continue

            field_names: set[str] = set()

            for field_spec in fields:

                if not isinstance(
                    field_spec,
                    dict,
                ):
                    errors.append(f"{name}: field must be object.")
                    continue

                field_name = field_spec.get("name")

                if not field_name:
                    errors.append(f"{name}: field missing name.")
                    continue

                if field_name in field_names:
                    errors.append(f"{name}: duplicate field " f"{field_name}")

                field_names.add(field_name)

                field_type = field_spec.get("type")

                if field_type not in (VocabularyRegistry.TYPE_SYSTEM):
                    errors.append(
                        f"{name}.{field_name}: " f"unsupported type " f"{field_type!r}"
                    )

                generation = field_spec.get("generation")

                if not isinstance(
                    generation,
                    dict,
                ):
                    errors.append(f"{name}.{field_name}: " "generation must be object.")
                    continue

                strategy = generation.get("strategy")

                if strategy not in (VocabularyRegistry.GENERATION_STRATEGIES):
                    errors.append(
                        f"{name}.{field_name}: "
                        f"unsupported strategy "
                        f"{strategy!r}"
                    )

                distribution = generation.get("distribution")

                if distribution is not None:

                    if not isinstance(
                        distribution,
                        dict,
                    ):
                        errors.append(
                            f"{name}.{field_name}: " "distribution must be object."
                        )

                    else:

                        distribution_type = distribution.get("type")

                        if distribution_type not in (VocabularyRegistry.DISTRIBUTIONS):
                            errors.append(
                                f"{name}.{field_name}: "
                                f"unsupported distribution "
                                f"{distribution_type!r}"
                            )

        return ValidationResult(
            "Entities and fields",
            not errors,
            errors,
        )

    # ------------------------------------------------------------------
    # Relationships
    # ------------------------------------------------------------------

    def _validate_relationships(
        self,
        specification: dict[str, Any],
    ) -> ValidationResult:

        relationships = specification.get("relationships")

        if not isinstance(
            relationships,
            list,
        ):
            return ValidationResult(
                "Relationships",
                False,
                ["relationships must be a list."],
            )

        entity_names = {
            entity["name"]
            for entity in specification.get("entities", [])
            if isinstance(entity, dict) and entity.get("name")
        }

        errors: list[str] = []

        for relationship in relationships:

            if not isinstance(
                relationship,
                dict,
            ):
                errors.append("Relationship must be object.")
                continue

            relationship_id = relationship.get("id")

            relationship_type = relationship.get("type")

            if relationship_type not in (
                "1:1",
                "0:1",
                "1:N",
                "0:N",
                "N:M",
            ):
                errors.append(
                    f"{relationship_id}: "
                    f"unsupported relationship "
                    f"{relationship_type!r}"
                )

            endpoints = []

            if relationship_type == "N:M":
                endpoints.extend(
                    [
                        relationship.get("left"),
                        relationship.get("right"),
                    ]
                )
            else:
                endpoints.extend(
                    [
                        relationship.get("parent"),
                        relationship.get("child"),
                    ]
                )

            for endpoint in endpoints:

                if not isinstance(
                    endpoint,
                    dict,
                ):
                    errors.append(f"{relationship_id}: " "invalid endpoint.")
                    continue

                entity = endpoint.get("entity")

                if entity not in entity_names:
                    errors.append(f"{relationship_id}: " f"unknown entity {entity!r}")

                if not endpoint.get("field"):
                    errors.append(f"{relationship_id}: " "endpoint missing field.")

        return ValidationResult(
            "Relationships",
            not errors,
            errors,
        )

    # ------------------------------------------------------------------
    # Rules
    # ------------------------------------------------------------------

    def _validate_rules(
        self,
        specification: dict[str, Any],
    ) -> ValidationResult:

        rules = specification.get("rules")

        if not isinstance(
            rules,
            list,
        ):
            return ValidationResult(
                "Rules",
                False,
                ["rules must be a list."],
            )

        errors: list[str] = []

        for rule in rules:

            if not isinstance(
                rule,
                dict,
            ):
                errors.append("Rule must be object.")
                continue

            expression = rule.get("expression")

            if not isinstance(
                expression,
                dict,
            ):
                errors.append(f"{rule.get('id')}: " "expression must be object.")
                continue

            operators = self._find_operators(expression)

            for operator in operators:
                if operator not in (VocabularyRegistry.RULE_OPERATORS):
                    errors.append(
                        f"{rule.get('id')}: " f"unsupported operator " f"{operator!r}"
                    )

        return ValidationResult(
            "Rules",
            not errors,
            errors,
        )

    def _find_operators(
        self,
        value: Any,
    ) -> set[str]:

        result: set[str] = set()

        if isinstance(
            value,
            dict,
        ):

            operator = value.get("operator")

            if isinstance(
                operator,
                str,
            ):
                result.add(operator)

            for nested in value.values():
                result.update(self._find_operators(nested))

        elif isinstance(
            value,
            list,
        ):

            for item in value:
                result.update(self._find_operators(item))

        return result

    # ------------------------------------------------------------------
    # Statistical behavior
    # ------------------------------------------------------------------

    def _validate_statistical_behavior(
        self,
        specification: dict[str, Any],
    ) -> ValidationResult:

        definitions = specification.get(
            "statistical_behavior",
            [],
        )

        if not isinstance(
            definitions,
            list,
        ):
            return ValidationResult(
                "Statistical behavior",
                False,
                ["statistical_behavior must " "be a list."],
            )

        errors: list[str] = []

        for definition in definitions:

            if not isinstance(
                definition,
                dict,
            ):
                errors.append("Statistical behavior must " "be object.")
                continue

            method = definition.get("method")

            if method not in (
                "PEARSON",
                "SPEARMAN",
            ):
                errors.append(f"Unsupported method " f"{method!r}")

        return ValidationResult(
            "Statistical behavior",
            not errors,
            errors,
        )

    # ------------------------------------------------------------------
    # Scenarios
    # ------------------------------------------------------------------

    def _validate_scenarios(
        self,
        specification: dict[str, Any],
    ) -> ValidationResult:

        scenarios = specification.get(
            "scenarios",
            [],
        )

        if not isinstance(
            scenarios,
            list,
        ):
            return ValidationResult(
                "Scenarios",
                False,
                ["scenarios must be a list."],
            )

        errors: list[str] = []

        for scenario in scenarios:

            if not isinstance(
                scenario,
                dict,
            ):
                errors.append("Scenario must be object.")
                continue

            if scenario.get("type") != ("SCENARIO"):
                errors.append(
                    f"{scenario.get('name')}: " "scenario type must be SCENARIO."
                )

        return ValidationResult(
            "Scenarios",
            not errors,
            errors,
        )

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    def _validate_validation(
        self,
        specification: dict[str, Any],
    ) -> ValidationResult:

        validation = specification.get("validation")

        errors: list[str] = []

        if not isinstance(
            validation,
            dict,
        ):
            errors.append("validation must be object.")

        return ValidationResult(
            "Validation configuration",
            not errors,
            errors,
        )

    # ------------------------------------------------------------------
    # Provenance
    # ------------------------------------------------------------------

    def _validate_provenance(
        self,
        specification: dict[str, Any],
    ) -> ValidationResult:

        provenance = specification.get("provenance")

        errors: list[str] = []

        if not isinstance(
            provenance,
            dict,
        ):
            errors.append("provenance must be object.")
        elif provenance.get("enabled") is not True:
            errors.append("provenance.enabled must be true.")

        return ValidationResult(
            "Provenance configuration",
            not errors,
            errors,
        )

    # ------------------------------------------------------------------
    # Reproducibility
    # ------------------------------------------------------------------

    def _validate_reproducibility(
        self,
        specification: dict[str, Any],
    ) -> ValidationResult:

        reproducibility = specification.get("reproducibility")

        errors: list[str] = []

        if not isinstance(
            reproducibility,
            dict,
        ):
            errors.append("reproducibility must be object.")
        elif reproducibility.get("enabled") is not True:
            errors.append("reproducibility.enabled " "must be true.")

        return ValidationResult(
            "Reproducibility configuration",
            not errors,
            errors,
        )


# ============================================================================
# GENERATION CONTEXT
# ============================================================================


@dataclass
class GenerationContext:

    seed: int
    random_stream: str
    deterministic: bool
    scenario: str

    random: random.Random = field(repr=False)

    entities: dict[str, Any] = field(default_factory=dict)

    generated_data: dict[
        str,
        list[dict[str, Any]],
    ] = field(default_factory=dict)

    @classmethod
    def from_specification(
        cls,
        specification: dict[str, Any],
    ) -> "GenerationContext":

        control = specification["generation_control"]

        seed = int(control["seed"])

        return cls(
            seed=seed,
            random_stream=str(control["random_stream"]),
            deterministic=bool(control["deterministic"]),
            scenario=str(
                specification.get(
                    "execution",
                    {},
                ).get(
                    "scenario",
                    "NORMAL",
                )
            ),
            random=random.Random(seed),
            entities={entity["name"]: entity for entity in specification["entities"]},
        )


# ============================================================================
# DISTRIBUTION ENGINE
# ============================================================================


class DistributionEngine:
    """
    Generic distribution engine.

    The engine knows nothing about business entities or field names.
    """

    EXECUTABLE = {
        "UNIFORM",
        "DISCRETE_UNIFORM",
        "NORMAL",
        "CATEGORICAL",
    }

    def __init__(
        self,
        rng: random.Random,
    ) -> None:

        self.rng = rng

    def generate(
        self,
        distribution: dict[str, Any],
    ) -> Any:

        distribution_type = distribution.get("type")

        if distribution_type not in (self.EXECUTABLE):
            raise GenerationError(
                f"Distribution '{distribution_type}' "
                "is registered but not executable "
                "in 020-B."
            )

        if distribution_type == ("UNIFORM"):
            return self._uniform(distribution)

        if distribution_type == ("DISCRETE_UNIFORM"):
            return self._discrete_uniform(distribution)

        if distribution_type == ("NORMAL"):
            return self._normal(distribution)

        if distribution_type == ("CATEGORICAL"):
            return self._categorical(distribution)

        raise GenerationError(f"Unsupported distribution " f"{distribution_type!r}")

    def _uniform(
        self,
        definition: dict[str, Any],
    ) -> float:

        minimum = float(definition["min"])

        maximum = float(definition["max"])

        return self.rng.uniform(
            minimum,
            maximum,
        )

    def _discrete_uniform(
        self,
        definition: dict[str, Any],
    ) -> int:

        minimum = int(definition["min"])

        maximum = int(definition["max"])

        return self.rng.randint(
            minimum,
            maximum,
        )

    def _normal(
        self,
        definition: dict[str, Any],
    ) -> float:

        mean = float(definition["mean"])

        stddev = float(definition["stddev"])

        value = self.rng.gauss(
            mean,
            stddev,
        )

        minimum = definition.get("min")

        maximum = definition.get("max")

        if minimum is not None:
            value = max(
                value,
                float(minimum),
            )

        if maximum is not None:
            value = min(
                value,
                float(maximum),
            )

        return value

    def _categorical(
        self,
        definition: dict[str, Any],
    ) -> Any:

        values = definition.get("values")

        weights = definition.get("weights")

        if not values:
            raise GenerationError("Categorical distribution " "requires values.")

        if weights is None:
            return self.rng.choice(values)

        if len(values) != len(weights):
            raise GenerationError(
                "Categorical values and " "weights must have the " "same length."
            )

        return self.rng.choices(
            values,
            weights=weights,
            k=1,
        )[0]


# ============================================================================
# TYPE ENGINE
# ============================================================================


class TypeEngine:
    """
    Converts generic generated values into the declared FORGE type.
    """

    def convert(
        self,
        value: Any,
        field_spec: dict[str, Any],
    ) -> Any:

        field_type = field_spec["type"]

        if value is None:
            return None

        if field_type == "INTEGER":
            return int(round(float(value)))

        if field_type in (
            "DECIMAL",
            "CURRENCY",
            "PERCENTAGE",
        ):
            precision = int(
                field_spec.get(
                    "precision",
                    2,
                )
            )

            return round(
                float(value),
                precision,
            )

        if field_type == "FLOAT":
            return float(value)

        if field_type in (
            "STRING",
            "CODE",
            "CATEGORICAL",
            "ENUM",
        ):
            return str(value)

        if field_type == "BOOLEAN":
            return bool(value)

        if field_type == "DATE":
            return self._to_date(value)

        if field_type == "DATETIME":
            return self._to_datetime(value)

        if field_type == "TIME":
            return self._to_time(value)

        if field_type == "IDENTIFIER":
            return str(value)

        raise GenerationError(f"Type '{field_type}' is not " "executable in 020-B.")

    @staticmethod
    def _to_date(
        value: Any,
    ) -> date:

        if isinstance(
            value,
            date,
        ) and not isinstance(
            value,
            datetime,
        ):
            return value

        if isinstance(
            value,
            datetime,
        ):
            return value.date()

        return date.fromisoformat(str(value))

    @staticmethod
    def _to_datetime(
        value: Any,
    ) -> datetime:

        if isinstance(
            value,
            datetime,
        ):
            return value

        return datetime.fromisoformat(str(value))

    @staticmethod
    def _to_time(
        value: Any,
    ) -> time:

        if isinstance(
            value,
            time,
        ):
            return value

        return time.fromisoformat(str(value))


# ============================================================================
# STRATEGY ENGINE
# ============================================================================


class StrategyEngine:
    """
    Executes generic generation strategies.

    Strategy execution does not know the business meaning of the field.
    """

    EXECUTABLE = {
        "CONSTANT",
        "SEQUENTIAL",
        "RANDOM",
        "NULL",
    }

    def __init__(
        self,
        rng: random.Random,
        distribution_engine: DistributionEngine,
        type_engine: TypeEngine,
    ) -> None:

        self.rng = rng
        self.distribution_engine = distribution_engine
        self.type_engine = type_engine

    def generate(
        self,
        field_spec: dict[str, Any],
        record_index: int,
    ) -> Any:

        generation = field_spec["generation"]

        strategy = generation["strategy"]

        if strategy not in (self.EXECUTABLE):
            raise GenerationError(
                f"Strategy '{strategy}' is "
                "registered but not executable "
                "in 020-B."
            )

        if strategy == "NULL":
            return None

        if strategy == "CONSTANT":
            value = generation.get("value")

            return self.type_engine.convert(
                value,
                field_spec,
            )

        if strategy == "SEQUENTIAL":
            return self._sequential(
                field_spec,
                record_index,
            )

        if strategy == "RANDOM":
            distribution = generation.get("distribution")

            if not isinstance(
                distribution,
                dict,
            ):
                raise GenerationError(
                    f"{field_spec['name']}: "
                    "RANDOM strategy requires "
                    "a distribution."
                )

            value = self.distribution_engine.generate(distribution)

            return self.type_engine.convert(
                value,
                field_spec,
            )

        raise GenerationError(f"Unhandled strategy '{strategy}'.")

    def _sequential(
        self,
        field_spec: dict[str, Any],
        record_index: int,
    ) -> Any:

        generation = field_spec["generation"]

        start = int(
            generation.get(
                "start",
                1,
            )
        )

        step = int(
            generation.get(
                "step",
                1,
            )
        )

        value = start + (record_index * step)

        return self.type_engine.convert(
            value,
            field_spec,
        )


# ============================================================================
# GENERATION ENGINE
# ============================================================================


class GenerationEngine:
    """
    Generic record generation engine.

    The engine operates entirely from entity and field metadata.
    """

    def __init__(
        self,
        context: GenerationContext,
    ) -> None:

        self.context = context

        self.distribution_engine = DistributionEngine(context.random)

        self.type_engine = TypeEngine()

        self.strategy_engine = StrategyEngine(
            context.random,
            self.distribution_engine,
            self.type_engine,
        )

    def generate_entity(
        self,
        entity_spec: dict[str, Any],
        record_count: int,
    ) -> list[dict[str, Any]]:

        entity_name = entity_spec["name"]

        records: list[dict[str, Any]] = []

        for index in range(record_count):

            record: dict[str, Any] = {}

            for field_spec in entity_spec["fields"]:

                field_name = field_spec["name"]

                value = self.strategy_engine.generate(
                    field_spec,
                    index,
                )

                record[field_name] = value

            records.append(record)

        self.context.generated_data[entity_name] = records

        return records


# ============================================================================
# SERIALIZATION
# ============================================================================


def serialize_value(
    value: Any,
) -> Any:

    if isinstance(
        value,
        (
            datetime,
            date,
            time,
        ),
    ):
        return value.isoformat()

    return value


def serialize_records(
    records: list[dict[str, Any]],
) -> list[dict[str, Any]]:

    return [
        {key: serialize_value(value) for key, value in record.items()}
        for record in records
    ]


# ============================================================================
# OUTPUT
# ============================================================================


def save_output(
    specification: dict[str, Any],
    context: GenerationContext,
    validation_results: list[ValidationResult],
) -> None:

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    validation_payload = {
        "experiment": "020",
        "stage": "020-B",
        "status": "PASS",
        "executable_types": sorted(VocabularyRegistry.EXECUTABLE_TYPES),
        "executable_strategies": sorted(VocabularyRegistry.EXECUTABLE_STRATEGIES),
        "executable_distributions": sorted(VocabularyRegistry.EXECUTABLE_DISTRIBUTIONS),
        "validation": [
            {
                "category": result.category,
                "status": result.status,
                "errors": result.errors,
            }
            for result in validation_results
        ],
    }

    with VALIDATION_OUTPUT_PATH.open(
        "w",
        encoding="utf-8",
    ) as file:

        json.dump(
            validation_payload,
            file,
            indent=2,
        )

    generated_payload = {
        entity_name: serialize_records(records[:10])
        for entity_name, records in context.generated_data.items()
    }

    with GENERATED_OUTPUT_PATH.open(
        "w",
        encoding="utf-8",
    ) as file:

        json.dump(
            generated_payload,
            file,
            indent=2,
        )


# ============================================================================
# REPORTING
# ============================================================================


def print_header(
    specification: dict[str, Any],
    context: GenerationContext,
) -> None:

    metadata = specification["specification"]

    print("=" * 70)
    print("FORGE - Experiment 020: " "Declarative Generation Specification")
    print("=" * 70)
    print("Stage:          020-B - Generic Generation")
    print(f"Experiment:     {metadata['experiment']}")
    print(f"Specification:  {SPECIFICATION_PATH}")
    print(f"Version:        {metadata['version']}")
    print(f"Vocabulary:     {VocabularyRegistry.VERSION}")
    print(f"Random seed:    {context.seed}")
    print(f"Scenario:       {context.scenario}")
    print()


def print_validation_results(
    results: list[ValidationResult],
) -> None:

    print("Specification validation:")

    for result in results:

        print(f"  {result.category:<32}" f"{result.status}")

        for error in result.errors:
            print(f"    ERROR: {error}")

    print()


def print_executable_capabilities() -> None:

    print("020-B executable capabilities:")

    print("  Types:")

    print("    " + ", ".join(sorted(VocabularyRegistry.EXECUTABLE_TYPES)))

    print("  Strategies:")

    print("    " + ", ".join(sorted(VocabularyRegistry.EXECUTABLE_STRATEGIES)))

    print("  Distributions:")

    print("    " + ", ".join(sorted(VocabularyRegistry.EXECUTABLE_DISTRIBUTIONS)))

    print()


def print_generation_summary(
    context: GenerationContext,
) -> None:

    print("Generation summary:")

    for entity_name, records in context.generated_data.items():

        print(f"  {entity_name:<20}" f"{len(records):>6} records")

        if records:
            print(f"    First record: " f"{records[0]}")

    print()


# ============================================================================
# MAIN
# ============================================================================


def main() -> int:

    try:

        loader = SpecificationLoader(SPECIFICATION_PATH)

        specification = loader.load()

        control = specification["generation_control"]

        seed = int(control["seed"])

        context = GenerationContext(
            seed=seed,
            random_stream=str(control["random_stream"]),
            deterministic=bool(control["deterministic"]),
            scenario=str(
                specification.get(
                    "execution",
                    {},
                ).get(
                    "scenario",
                    "NORMAL",
                )
            ),
            random=random.Random(seed),
            entities={entity["name"]: entity for entity in specification["entities"]},
        )

        print_header(
            specification,
            context,
        )

        validator = SpecificationValidator()

        validation_results = validator.validate(specification)

        if not all(result.passed for result in validation_results):
            print_validation_results(validation_results)

            raise StructuralValidationError("Specification validation failed.")

        print_validation_results(validation_results)

        print_executable_capabilities()

        generation_engine = GenerationEngine(context)

        record_count = int(
            control.get(
                "record_count",
                10,
            )
        )

        print(f"Generating {record_count} " "records per entity...")

        print()

        for entity_spec in specification["entities"]:

            entity_name = entity_spec["name"]

            records = generation_engine.generate_entity(
                entity_spec,
                record_count,
            )

            print(f"  {entity_name:<20}" f"{len(records):>6} records")

        print()

        print_generation_summary(context)

        save_output(
            specification,
            context,
            validation_results,
        )

        print("Generation result:")
        print("  Specification validation: PASS")
        print("  Type engine:               PASS")
        print("  Strategy engine:           PASS")
        print("  Distribution engine:       PASS")
        print("  Generic generation:         PASS")
        print("  Overall:                   PASS")

        print()

        print("Output:")
        print(f"  Validation: " f"{VALIDATION_OUTPUT_PATH}")
        print(f"  Sample data: " f"{GENERATED_OUTPUT_PATH}")

        print()

        print("Experiment completed successfully.")

        return 0

    except ForgeSpecificationError as exc:

        print()
        print("Experiment result:")
        print("  Overall:                   FAIL")
        print()
        print(f"ERROR: {exc}")

        return 1

    except Exception as exc:

        print()
        print("Unexpected error:")
        print(f"  {type(exc).__name__}: {exc}")

        return 1


if __name__ == "__main__":
    sys.exit(main())
