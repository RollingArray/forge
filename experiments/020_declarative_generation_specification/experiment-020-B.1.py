"""
FORGE - Experiment 020: Declarative Generation Specification
==============================================================

Purpose
-------
This experiment establishes the executable foundation of the FORGE
declarative generation model.

Stage
-----
020-B - Execution Capability Assessment

This stage extends 020-B by introducing an explicit distinction between:

    1. Vocabulary supported by the FORGE specification language.
    2. Capabilities executable by the current generation runtime.

A specification may therefore be valid while still containing capabilities
that are not executable by the current engine.

Architecture
------------

    specification.json
           |
           v
    SpecificationLoader
           |
           v
    SpecificationValidator
           |
           v
    ExecutionCapabilities
           |
           v
    CapabilityAssessor
           |
           v
    ExecutionPlan
           |
       +---+---+
       |       |
       v       v
  EXECUTABLE  DEFERRED
       |       |
       v       v
   Generate   BLOCK

Design Principles
-----------------
- Specification over hard-coded business logic.
- Controlled vocabulary over arbitrary keywords.
- Registered vocabulary is distinct from executable capabilities.
- Valid specification does not imply executable specification.
- Unsupported execution capabilities are reported explicitly.
- Generation is blocked when required capabilities are unavailable.
- No partial or silently degraded dataset is produced.
- No entity-specific generation logic.
- Deterministic execution through explicit random state.

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

All remaining vocabulary remains registered but may be deferred by
the current runtime.

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
This stage does not attempt to implement every FORGE vocabulary capability.

Instead, it establishes a safe execution boundary between what the
specification can express and what the current runtime can execute.
"""

from __future__ import annotations

import json
import random
import sys
from dataclasses import dataclass, field
from datetime import date, datetime, time
from pathlib import Path
from typing import Any

# ============================================================================
# PATHS
# ============================================================================

EXPERIMENT_DIR = Path(__file__).resolve().parent

SPECIFICATION_PATH = EXPERIMENT_DIR / "specification.json"

OUTPUT_DIR = EXPERIMENT_DIR / "output"

VALIDATION_OUTPUT_PATH = OUTPUT_DIR / "generation_validation.json"

EXECUTION_PLAN_OUTPUT_PATH = OUTPUT_DIR / "execution_plan.json"

GENERATED_OUTPUT_PATH = OUTPUT_DIR / "generated_sample.json"


# ============================================================================
# EXCEPTIONS
# ============================================================================


class ForgeSpecificationError(Exception):
    """Base exception for FORGE specification failures."""


class SpecificationLoadError(ForgeSpecificationError):
    """Raised when the specification cannot be loaded."""


class StructuralValidationError(ForgeSpecificationError):
    """Raised when specification structure is invalid."""


class CapabilityError(ForgeSpecificationError):
    """Raised when required runtime capability is unavailable."""


class GenerationError(ForgeSpecificationError):
    """Raised when generation cannot be performed."""


# ============================================================================
# CONTROLLED VOCABULARY
# ============================================================================


class VocabularyRegistry:
    """
    FORGE Controlled Vocabulary v1.

    The vocabulary represents what the FORGE specification language
    can express.

    It is intentionally broader than the executable capabilities of
    the current runtime.
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


# ============================================================================
# SPECIFICATION LOADER
# ============================================================================


class SpecificationLoader:
    """Load a FORGE JSON specification."""

    def __init__(
        self,
        path: Path,
    ) -> None:
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

        if not isinstance(
            specification,
            dict,
        ):
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

    This validates whether the specification is valid FORGE vocabulary
    and structure. It does not determine whether the current runtime
    can execute every capability.
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

        if not isinstance(
            metadata,
            dict,
        ):
            errors.append("'specification' must be an object.")

        else:

            for key in (
                "name",
                "version",
                "experiment",
            ):
                if not metadata.get(key):
                    errors.append(f"specification.{key} " "is required.")

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

        if not isinstance(
            vocabulary,
            dict,
        ):
            return ValidationResult(
                "Controlled vocabulary",
                False,
                ["vocabulary must be an object."],
            )

        errors: list[str] = []

        if vocabulary.get("version") != VocabularyRegistry.VERSION:
            errors.append("Unsupported vocabulary version.")

        for category, supported in VocabularyRegistry.CATEGORIES.items():

            declared = vocabulary.get(
                category,
                [],
            )

            if not isinstance(
                declared,
                list,
            ):
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

        if not isinstance(
            entities,
            list,
        ):
            return ValidationResult(
                "Entities and fields",
                False,
                ["entities must be a list."],
            )

        entity_names: set[str] = set()

        for entity in entities:

            if not isinstance(
                entity,
                dict,
            ):
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

            if not isinstance(
                fields,
                list,
            ):
                errors.append(f"{name}: fields must " "be a list.")
                continue

            field_names: set[str] = set()

            for field_spec in fields:

                if not isinstance(
                    field_spec,
                    dict,
                ):
                    errors.append(f"{name}: field must " "be object.")
                    continue

                field_name = field_spec.get("name")

                if not field_name:
                    errors.append(f"{name}: field " "missing name.")
                    continue

                if field_name in field_names:
                    errors.append(f"{name}: duplicate " f"field {field_name}")

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
                    errors.append(
                        f"{name}.{field_name}: " "generation must " "be object."
                    )
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
                            f"{name}.{field_name}: " "distribution must " "be object."
                        )

                    else:

                        distribution_type = distribution.get("type")

                        if distribution_type not in (VocabularyRegistry.DISTRIBUTIONS):
                            errors.append(
                                f"{name}.{field_name}: "
                                f"unsupported "
                                f"distribution "
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
                ["relationships must " "be a list."],
            )

        entity_names = {
            entity["name"]
            for entity in specification.get("entities", [])
            if isinstance(
                entity,
                dict,
            )
            and entity.get("name")
        }

        errors: list[str] = []

        for relationship in relationships:

            if not isinstance(
                relationship,
                dict,
            ):
                errors.append("Relationship must " "be object.")
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

            if relationship_type == "N:M":

                endpoints = [
                    relationship.get("left"),
                    relationship.get("right"),
                ]

            else:

                endpoints = [
                    relationship.get("parent"),
                    relationship.get("child"),
                ]

            for endpoint in endpoints:

                if not isinstance(
                    endpoint,
                    dict,
                ):
                    errors.append(f"{relationship_id}: " "invalid endpoint.")
                    continue

                entity = endpoint.get("entity")

                if entity not in entity_names:
                    errors.append(
                        f"{relationship_id}: " f"unknown entity " f"{entity!r}"
                    )

                if not endpoint.get("field"):
                    errors.append(f"{relationship_id}: " "endpoint missing " "field.")

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
                errors.append(f"{rule.get('id')}: " "expression must " "be object.")
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
                ["statistical_behavior " "must be a list."],
            )

        errors: list[str] = []

        for definition in definitions:

            if not isinstance(
                definition,
                dict,
            ):
                errors.append("Statistical behavior " "must be object.")
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
                ["scenarios must " "be a list."],
            )

        errors: list[str] = []

        for scenario in scenarios:

            if not isinstance(
                scenario,
                dict,
            ):
                errors.append("Scenario must " "be object.")
                continue

            if scenario.get("type") != "SCENARIO":

                errors.append(
                    f"{scenario.get('name')}: " "scenario type must " "be SCENARIO."
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
            errors.append("validation must " "be object.")

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
            errors.append("provenance must " "be object.")

        elif provenance.get("enabled") is not True:

            errors.append("provenance.enabled " "must be true.")

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
            errors.append("reproducibility must " "be object.")

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


# ============================================================================
# EXECUTION CAPABILITY MODEL
# ============================================================================


@dataclass(frozen=True)
class ExecutionCapabilities:
    """
    Describes what the current runtime can actually execute.

    This is intentionally separate from VocabularyRegistry.
    """

    types: frozenset[str]
    strategies: frozenset[str]
    distributions: frozenset[str]

    @classmethod
    def current(cls) -> "ExecutionCapabilities":

        return cls(
            types=frozenset(
                {
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
            ),
            strategies=frozenset(
                {
                    "CONSTANT",
                    "SEQUENTIAL",
                    "RANDOM",
                    "NULL",
                }
            ),
            distributions=frozenset(
                {
                    "UNIFORM",
                    "DISCRETE_UNIFORM",
                    "NORMAL",
                    "CATEGORICAL",
                }
            ),
        )


# ============================================================================
# EXECUTION PLAN
# ============================================================================


@dataclass
class FieldExecutionPlan:

    entity: str
    field: str
    field_type: str
    strategy: str
    distribution: str | None

    type_status: str
    strategy_status: str
    distribution_status: str

    status: str
    reason: str | None = None

    @property
    def executable(self) -> bool:
        return self.status == "EXECUTABLE"


@dataclass
class ExecutionPlan:

    fields: list[FieldExecutionPlan] = field(default_factory=list)

    @property
    def executable(self) -> bool:
        return all(field.executable for field in self.fields)

    @property
    def deferred_fields(self) -> list[FieldExecutionPlan]:

        return [field for field in self.fields if not field.executable]


# ============================================================================
# CAPABILITY ASSESSOR
# ============================================================================


class CapabilityAssessor:
    """
    Determines whether every field in a specification can be executed
    by the current runtime.
    """

    def __init__(
        self,
        capabilities: ExecutionCapabilities,
    ) -> None:

        self.capabilities = capabilities

    def assess(
        self,
        specification: dict[str, Any],
    ) -> ExecutionPlan:

        plan = ExecutionPlan()

        for entity in specification["entities"]:

            entity_name = entity["name"]

            for field_spec in entity["fields"]:

                plan.fields.append(
                    self._assess_field(
                        entity_name,
                        field_spec,
                    )
                )

        return plan

    def _assess_field(
        self,
        entity_name: str,
        field_spec: dict[str, Any],
    ) -> FieldExecutionPlan:

        field_name = field_spec["name"]

        field_type = field_spec["type"]

        generation = field_spec["generation"]

        strategy = generation["strategy"]

        distribution_definition = generation.get("distribution")

        distribution = None

        if isinstance(
            distribution_definition,
            dict,
        ):
            distribution = distribution_definition.get("type")

        type_status = (
            "EXECUTABLE" if field_type in self.capabilities.types else "DEFERRED"
        )

        strategy_status = (
            "EXECUTABLE" if strategy in self.capabilities.strategies else "DEFERRED"
        )

        if distribution is None:

            distribution_status = "NOT_REQUIRED"

        else:

            distribution_status = (
                "EXECUTABLE"
                if distribution in self.capabilities.distributions
                else "DEFERRED"
            )

        failures: list[str] = []

        if type_status != "EXECUTABLE":

            failures.append(f"type '{field_type}' " "is not executable")

        if strategy_status != "EXECUTABLE":

            failures.append(f"strategy '{strategy}' " "is not executable")

        if distribution_status == "DEFERRED":

            failures.append(f"distribution " f"'{distribution}' " "is not executable")

        if failures:

            status = "DEFERRED"

            reason = "; ".join(failures)

        else:

            status = "EXECUTABLE"
            reason = None

        return FieldExecutionPlan(
            entity=entity_name,
            field=field_name,
            field_type=field_type,
            strategy=strategy,
            distribution=distribution,
            type_status=type_status,
            strategy_status=strategy_status,
            distribution_status=(distribution_status),
            status=status,
            reason=reason,
        )


# ============================================================================
# DISTRIBUTION ENGINE
# ============================================================================


class DistributionEngine:

    def __init__(
        self,
        rng: random.Random,
    ) -> None:

        self.rng = rng

    def generate(
        self,
        distribution: dict[str, Any],
    ) -> Any:

        distribution_type = distribution["type"]

        if distribution_type == ("UNIFORM"):

            return self.rng.uniform(
                float(distribution["min"]),
                float(distribution["max"]),
            )

        if distribution_type == ("DISCRETE_UNIFORM"):

            return self.rng.randint(
                int(distribution["min"]),
                int(distribution["max"]),
            )

        if distribution_type == ("NORMAL"):

            value = self.rng.gauss(
                float(distribution["mean"]),
                float(distribution["stddev"]),
            )

            if "min" in distribution:
                value = max(
                    value,
                    float(distribution["min"]),
                )

            if "max" in distribution:
                value = min(
                    value,
                    float(distribution["max"]),
                )

            return value

        if distribution_type == ("CATEGORICAL"):

            values = distribution["values"]

            weights = distribution.get("weights")

            if weights is None:

                return self.rng.choice(values)

            return self.rng.choices(
                values,
                weights=weights,
                k=1,
            )[0]

        raise GenerationError(
            f"Distribution '{distribution_type}' " "is not executable."
        )


# ============================================================================
# TYPE ENGINE
# ============================================================================


class TypeEngine:

    def convert(
        self,
        value: Any,
        field_spec: dict[str, Any],
    ) -> Any:

        if value is None:
            return None

        field_type = field_spec["type"]

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
            "CATEGORICAL",
            "ENUM",
            "CODE",
            "IDENTIFIER",
        ):

            return str(value)

        if field_type == "BOOLEAN":

            return bool(value)

        if field_type == "DATE":

            if isinstance(
                value,
                datetime,
            ):
                return value.date()

            if isinstance(
                value,
                date,
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

        raise GenerationError(f"Type '{field_type}' " "is not executable.")


# ============================================================================
# STRATEGY ENGINE
# ============================================================================


class StrategyEngine:

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

        if strategy == "NULL":
            return None

        if strategy == "CONSTANT":

            value = generation.get("value")

            return self.type_engine.convert(
                value,
                field_spec,
            )

        if strategy == "SEQUENTIAL":

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

            value = start + record_index * step

            return self.type_engine.convert(
                value,
                field_spec,
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
                    "distribution."
                )

            value = self.distribution_engine.generate(distribution)

            return self.type_engine.convert(
                value,
                field_spec,
            )

        raise GenerationError(f"Strategy '{strategy}' " "is not executable.")


# ============================================================================
# GENERATION ENGINE
# ============================================================================


class GenerationEngine:

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

    def generate(
        self,
        specification: dict[str, Any],
        execution_plan: ExecutionPlan,
    ) -> None:

        if not execution_plan.executable:

            deferred = execution_plan.deferred_fields

            details = [
                (f"{item.entity}.{item.field}: " f"{item.reason}") for item in deferred
            ]

            raise CapabilityError(
                "Generation blocked because "
                "required capabilities are "
                "not executable: " + " | ".join(details)
            )

        record_count = int(
            specification["generation_control"].get(
                "record_count",
                10,
            )
        )

        for entity in specification["entities"]:

            entity_name = entity["name"]

            records: list[dict[str, Any]] = []

            for index in range(record_count):

                record: dict[
                    str,
                    Any,
                ] = {}

                for field_spec in entity["fields"]:

                    field_name = field_spec["name"]

                    record[field_name] = self.strategy_engine.generate(
                        field_spec,
                        index,
                    )

                records.append(record)

            self.context.generated_data[entity_name] = records


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


def save_json(
    path: Path,
    payload: Any,
) -> None:

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    with path.open(
        "w",
        encoding="utf-8",
    ) as file:

        json.dump(
            payload,
            file,
            indent=2,
        )


def save_outputs(
    specification: dict[str, Any],
    validation_results: list[ValidationResult],
    execution_plan: ExecutionPlan,
    context: GenerationContext,
) -> None:

    save_json(
        VALIDATION_OUTPUT_PATH,
        {
            "experiment": "020",
            "stage": "020-B.1",
            "status": "PASS",
            "validation": [
                {
                    "category": result.category,
                    "status": result.status,
                    "errors": result.errors,
                }
                for result in validation_results
            ],
        },
    )

    save_json(
        EXECUTION_PLAN_OUTPUT_PATH,
        {
            "experiment": "020",
            "stage": "020-B.1",
            "executable": (execution_plan.executable),
            "fields": [
                {
                    "entity": item.entity,
                    "field": item.field,
                    "type": item.field_type,
                    "strategy": item.strategy,
                    "distribution": (item.distribution),
                    "type_status": (item.type_status),
                    "strategy_status": (item.strategy_status),
                    "distribution_status": (item.distribution_status),
                    "status": item.status,
                    "reason": item.reason,
                }
                for item in execution_plan.fields
            ],
        },
    )

    generated_payload = {
        entity: serialize_records(records[:10])
        for entity, records in context.generated_data.items()
    }

    save_json(
        GENERATED_OUTPUT_PATH,
        generated_payload,
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

    print("Stage:          020-B.1 - " "Capability Assessment")

    print(f"Experiment:     " f"{metadata['experiment']}")

    print(f"Specification:  " f"{SPECIFICATION_PATH}")

    print(f"Version:        " f"{metadata['version']}")

    print(f"Vocabulary:     " f"{VocabularyRegistry.VERSION}")

    print(f"Random seed:    " f"{context.seed}")

    print(f"Scenario:       " f"{context.scenario}")

    print()


def print_validation(
    results: list[ValidationResult],
) -> None:

    print("Specification validation:")

    for result in results:

        print(f"  {result.category:<32}" f"{result.status}")

        for error in result.errors:

            print(f"    ERROR: {error}")

    print()


def print_capabilities(
    capabilities: ExecutionCapabilities,
) -> None:

    print("Runtime execution capabilities:")

    print("  Types:")

    print("    " + ", ".join(sorted(capabilities.types)))

    print("  Strategies:")

    print("    " + ", ".join(sorted(capabilities.strategies)))

    print("  Distributions:")

    print("    " + ", ".join(sorted(capabilities.distributions)))

    print()


def print_execution_plan(
    plan: ExecutionPlan,
) -> None:

    print("Execution capability assessment:")

    current_entity = None

    for item in plan.fields:

        if item.entity != current_entity:

            current_entity = item.entity

            print()
            print(f"  {current_entity}")

        distribution = item.distribution or "-"

        print(
            f"    "
            f"{item.field:<22}"
            f"type={item.type_status:<11}"
            f"strategy={item.strategy_status:<11}"
            f"distribution={distribution:<18}"
            f"{item.status}"
        )

        if item.reason:

            print(f"      Reason: " f"{item.reason}")

    print()

    executable_count = sum(item.executable for item in plan.fields)

    deferred_count = len(plan.deferred_fields)

    print("Execution plan summary:")

    print(f"  Fields assessed:  " f"{len(plan.fields)}")

    print(f"  Executable:       " f"{executable_count}")

    print(f"  Deferred:         " f"{deferred_count}")

    print(f"  Plan status:      " f"{'EXECUTABLE' if plan.executable else 'BLOCKED'}")

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

        # --------------------------------------------------------------
        # 1. Structural validation
        # --------------------------------------------------------------

        validator = SpecificationValidator()

        validation_results = validator.validate(specification)

        print_validation(validation_results)

        if not all(result.passed for result in validation_results):

            raise StructuralValidationError("Specification validation failed.")

        # --------------------------------------------------------------
        # 2. Runtime capability assessment
        # --------------------------------------------------------------

        capabilities = ExecutionCapabilities.current()

        print_capabilities(capabilities)

        assessor = CapabilityAssessor(capabilities)

        execution_plan = assessor.assess(specification)

        print_execution_plan(execution_plan)

        # --------------------------------------------------------------
        # 3. Generation
        # --------------------------------------------------------------

        generation_engine = GenerationEngine(context)

        try:

            generation_engine.generate(
                specification,
                execution_plan,
            )

            generation_status = "PASS"

        except CapabilityError:

            generation_status = "BLOCKED"

        # --------------------------------------------------------------
        # 4. Save outputs
        # --------------------------------------------------------------

        save_outputs(
            specification,
            validation_results,
            execution_plan,
            context,
        )

        # --------------------------------------------------------------
        # 5. Report
        # --------------------------------------------------------------

        print("Experiment result:")

        print("  Specification validity: " "PASS")

        print("  Capability assessment:  " "PASS")

        if generation_status == "PASS":

            print("  Generation:             PASS")

            print("  Overall:                PASS")

            print()

            print("Output:")

            print(f"  Validation: " f"{VALIDATION_OUTPUT_PATH}")

            print(f"  Execution plan: " f"{EXECUTION_PLAN_OUTPUT_PATH}")

            print(f"  Generated data: " f"{GENERATED_OUTPUT_PATH}")

            print()

            print("Experiment completed successfully.")

            return 0

        # --------------------------------------------------------------
        # Expected deferred capability case
        # --------------------------------------------------------------

        print("  Generation:             BLOCKED")

        print("  Overall:                PASS")

        print()

        print(
            "Generation was intentionally blocked "
            "because the specification contains "
            "capabilities that are valid FORGE "
            "vocabulary but are not executable "
            "by the current runtime."
        )

        print()

        print("Output:")

        print(f"  Validation: " f"{VALIDATION_OUTPUT_PATH}")

        print(f"  Execution plan: " f"{EXECUTION_PLAN_OUTPUT_PATH}")

        print()

        print("Experiment completed successfully.")

        return 0

    except ForgeSpecificationError as exc:

        print()

        print("Experiment result:")

        print("  Overall:                FAIL")

        print()

        print(f"ERROR: {exc}")

        return 1

    except Exception as exc:

        print()

        print("Unexpected error:")

        print(f"  {type(exc).__name__}: " f"{exc}")

        return 1


if __name__ == "__main__":
    sys.exit(main())
