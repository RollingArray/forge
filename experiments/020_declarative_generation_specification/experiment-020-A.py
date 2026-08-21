"""
FORGE - Experiment 020: Declarative Generation Specification
==============================================================

Purpose
-------
This experiment establishes the executable foundation for the FORGE
declarative generation model.

Unlike earlier experiments, Experiment 020 is intentionally designed as
a small, modular prototype of the eventual FORGE generation framework.

The experiment validates that a declarative JSON specification can be:

    1. Loaded safely.
    2. Validated against the FORGE Controlled Vocabulary v1.
    3. Validated structurally.
    4. Validated for entity and field references.
    5. Validated for generation dependencies.
    6. Converted into an execution context.

No entity-specific generation logic is used.

The implementation is specification-driven. The generator does not
contain business rules for CUSTOMER, ORDER, PRODUCT, or any other
specific entity.

Experiment
----------
020 - Declarative Generation Specification

Implementation Stage
--------------------
020-A - Foundation

Key Question
------------
Can a generic FORGE engine safely interpret and validate a declarative
generation specification before any data generation takes place?

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

Design Principles
-----------------
- Specification over hard-coded business logic.
- Controlled vocabulary over arbitrary keywords.
- Fail fast on invalid specifications.
- No entity-specific generation logic.
- Deterministic execution context.
- Modular components suitable for later extraction into the FORGE core.
- Explicit distinction between vocabulary registration and executable
  support.

No machine learning, LLM, or real production data is used.

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

Input
-----
    experiments/020_declarative_generation_specification/specification.json

Output
------
    experiments/020_declarative_generation_specification/output/

Important
---------
This stage does not generate the final synthetic dataset.

It establishes and validates the declarative execution foundation.
Subsequent stages of Experiment 020 will add generic generation,
distribution, rule, relationship, validation, scenario, and provenance
engines.
"""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

# ============================================================================
# PATHS
# ============================================================================

EXPERIMENT_DIR = Path(__file__).resolve().parent
SPECIFICATION_PATH = EXPERIMENT_DIR / "specification.json"
OUTPUT_DIR = EXPERIMENT_DIR / "output"
VALIDATION_OUTPUT_PATH = OUTPUT_DIR / "foundation_validation.json"


# ============================================================================
# EXCEPTIONS
# ============================================================================


class ForgeSpecificationError(Exception):
    """Base exception for specification-related failures."""


class SpecificationLoadError(ForgeSpecificationError):
    """Raised when the specification cannot be loaded."""


class VocabularyError(ForgeSpecificationError):
    """Raised when the specification contains unsupported vocabulary."""


class StructuralValidationError(ForgeSpecificationError):
    """Raised when the specification structure is invalid."""


# ============================================================================
# CONTROLLED VOCABULARY
# ============================================================================


class VocabularyRegistry:
    """
    Registry for FORGE Controlled Vocabulary v1.

    The registry is deliberately independent from the specification.
    This allows the same vocabulary definition to be reused by later
    validators and generation engines.
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

    SCENARIO = {
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
        "scenarios": SCENARIO,
        "statistical_behavior": STATISTICAL_BEHAVIOR,
        "validation_evidence": VALIDATION_EVIDENCE,
    }

    def validate_declared_vocabulary(
        self,
        vocabulary: dict[str, Any],
    ) -> list[str]:
        """
        Validate vocabulary declarations supplied by the specification.

        Returns a list of errors rather than raising immediately so the
        caller can report all vocabulary problems in one execution.
        """

        errors: list[str] = []

        declared_version = vocabulary.get("version")

        if declared_version != self.VERSION:
            errors.append(
                f"Unsupported vocabulary version: {declared_version!r}; "
                f"expected {self.VERSION!r}"
            )

        for category, supported_values in self.CATEGORIES.items():
            declared_values = vocabulary.get(category, [])

            if not isinstance(declared_values, list):
                errors.append(f"Vocabulary category '{category}' must be a list.")
                continue

            duplicates = [
                value
                for value in set(declared_values)
                if declared_values.count(value) > 1
            ]

            if duplicates:
                errors.append(
                    f"Vocabulary category '{category}' contains "
                    f"duplicates: {sorted(duplicates)}"
                )

            unsupported = sorted(set(declared_values) - supported_values)

            if unsupported:
                errors.append(
                    f"Vocabulary category '{category}' contains "
                    f"unsupported values: {unsupported}"
                )

        return errors

    def category_for(self, value: str) -> str | None:
        """Return the vocabulary category containing a value."""

        for category, values in self.CATEGORIES.items():
            if value in values:
                return category

        return None

    def is_supported(self, value: str) -> bool:
        """Return whether a vocabulary value is supported."""

        return self.category_for(value) is not None


# ============================================================================
# SPECIFICATION LOADER
# ============================================================================


class SpecificationLoader:
    """Loads and performs basic parsing of a FORGE specification."""

    def __init__(self, path: Path) -> None:
        self.path = path

    def load(self) -> dict[str, Any]:
        if not self.path.exists():
            raise SpecificationLoadError(f"Specification not found: {self.path}")

        if not self.path.is_file():
            raise SpecificationLoadError(
                f"Specification path is not a file: {self.path}"
            )

        try:
            with self.path.open("r", encoding="utf-8") as file:
                specification = json.load(file)
        except json.JSONDecodeError as exc:
            raise SpecificationLoadError(
                f"Invalid JSON in specification: {exc}"
            ) from exc
        except OSError as exc:
            raise SpecificationLoadError(
                f"Unable to read specification: {exc}"
            ) from exc

        if not isinstance(specification, dict):
            raise SpecificationLoadError("Specification root must be a JSON object.")

        return specification


# ============================================================================
# VALIDATION RESULT
# ============================================================================


@dataclass
class ValidationResult:
    """Represents one validation category."""

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
    Validates the declarative specification without generating data.

    This validator intentionally does not contain generation logic.
    """

    def __init__(self, vocabulary: VocabularyRegistry) -> None:
        self.vocabulary = vocabulary

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
            self._validate_validation_configuration(specification),
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

        errors: list[str] = []

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

        missing = sorted(required - specification.keys())

        if missing:
            errors.append(f"Missing required root sections: {missing}")

        metadata = specification.get("specification")

        if not isinstance(metadata, dict):
            errors.append("'specification' must be an object.")
        else:
            for key in ("name", "version", "experiment"):
                if not metadata.get(key):
                    errors.append(f"specification.{key} is required.")

        return ValidationResult(
            category="Specification structure",
            passed=not errors,
            errors=errors,
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
                category="Controlled vocabulary",
                passed=False,
                errors=["'vocabulary' must be an object."],
            )

        errors = self.vocabulary.validate_declared_vocabulary(vocabulary)

        return ValidationResult(
            category="Controlled vocabulary",
            passed=not errors,
            errors=errors,
        )

    # ------------------------------------------------------------------
    # Entities
    # ------------------------------------------------------------------

    def _validate_entities(
        self,
        specification: dict[str, Any],
    ) -> ValidationResult:

        entities = specification.get("entities")

        if not isinstance(entities, list):
            return ValidationResult(
                category="Entities and fields",
                passed=False,
                errors=["'entities' must be a list."],
            )

        errors: list[str] = []
        entity_names: set[str] = set()

        for entity in entities:
            if not isinstance(entity, dict):
                errors.append("Every entity must be an object.")
                continue

            entity_name = entity.get("name")

            if not entity_name:
                errors.append("Entity is missing 'name'.")
                continue

            if entity_name in entity_names:
                errors.append(f"Duplicate entity: {entity_name}")

            entity_names.add(entity_name)

            fields = entity.get("fields")

            if not isinstance(fields, list):
                errors.append(f"{entity_name}: 'fields' must be a list.")
                continue

            field_names: set[str] = set()

            for field_spec in fields:
                if not isinstance(field_spec, dict):
                    errors.append(f"{entity_name}: field must be an object.")
                    continue

                field_name = field_spec.get("name")

                if not field_name:
                    errors.append(f"{entity_name}: field missing 'name'.")
                    continue

                if field_name in field_names:
                    errors.append(f"{entity_name}: duplicate field " f"{field_name}.")

                field_names.add(field_name)

                field_type = field_spec.get("type")

                if field_type and not self._supports(
                    field_type,
                    "type_system",
                ):
                    errors.append(
                        f"{entity_name}.{field_name}: unsupported "
                        f"type '{field_type}'."
                    )

                semantic = field_spec.get("semantic")

                if semantic and not self._supports_any(
                    semantic,
                    [
                        "type_system",
                    ],
                ):
                    errors.append(
                        f"{entity_name}.{field_name}: unsupported "
                        f"semantic '{semantic}'."
                    )

                self._validate_field_generation(
                    entity_name,
                    field_spec,
                    errors,
                )

                self._validate_field_identity(
                    entity_name,
                    field_spec,
                    errors,
                )

                self._validate_field_nullability(
                    entity_name,
                    field_spec,
                    errors,
                )

                self._validate_field_dependencies(
                    entity_name,
                    field_spec,
                    errors,
                )

        return ValidationResult(
            category="Entities and fields",
            passed=not errors,
            errors=errors,
        )

    def _validate_field_generation(
        self,
        entity_name: str,
        field_spec: dict[str, Any],
        errors: list[str],
    ) -> None:

        field_name = field_spec.get("name")
        generation = field_spec.get("generation")

        if not isinstance(generation, dict):
            errors.append(
                f"{entity_name}.{field_name}: " "'generation' must be an object."
            )
            return

        strategy = generation.get("strategy")

        if not strategy:
            errors.append(
                f"{entity_name}.{field_name}: generation strategy " "is required."
            )
            return

        if strategy not in VocabularyRegistry.GENERATION_STRATEGIES:
            errors.append(
                f"{entity_name}.{field_name}: unsupported generation "
                f"strategy '{strategy}'."
            )

        distribution = generation.get("distribution")

        if distribution is not None:
            if not isinstance(distribution, dict):
                errors.append(
                    f"{entity_name}.{field_name}: distribution " "must be an object."
                )
            else:
                distribution_type = distribution.get("type")

                if distribution_type not in (VocabularyRegistry.DISTRIBUTIONS):
                    errors.append(
                        f"{entity_name}.{field_name}: unsupported "
                        f"distribution '{distribution_type}'."
                    )

    def _validate_field_identity(
        self,
        entity_name: str,
        field_spec: dict[str, Any],
        errors: list[str],
    ) -> None:

        identity = field_spec.get("identity")

        if identity is None:
            return

        if not isinstance(identity, list):
            errors.append(
                f"{entity_name}.{field_spec.get('name')}: " "'identity' must be a list."
            )
            return

        for identity_type in identity:
            if identity_type not in VocabularyRegistry.IDENTITY:
                errors.append(
                    f"{entity_name}.{field_spec.get('name')}: "
                    f"unsupported identity '{identity_type}'."
                )

    def _validate_field_nullability(
        self,
        entity_name: str,
        field_spec: dict[str, Any],
        errors: list[str],
    ) -> None:

        nullability = field_spec.get("nullability")

        if nullability is None:
            return

        if nullability not in (
            "ALWAYS",
            "NEVER",
            "OPTIONAL",
            "NULLABLE",
            "NOT_NULL",
        ):
            errors.append(
                f"{entity_name}.{field_spec.get('name')}: "
                f"unsupported nullability '{nullability}'."
            )

    def _validate_field_dependencies(
        self,
        entity_name: str,
        field_spec: dict[str, Any],
        errors: list[str],
    ) -> None:

        dependencies = field_spec.get("dependencies", [])

        if not isinstance(dependencies, list):
            errors.append(
                f"{entity_name}.{field_spec.get('name')}: "
                "'dependencies' must be a list."
            )
            return

        for dependency in dependencies:
            if not isinstance(dependency, dict):
                errors.append(
                    f"{entity_name}.{field_spec.get('name')}: "
                    "dependency must be an object."
                )
                continue

            dependency_type = dependency.get("type")

            if dependency_type not in VocabularyRegistry.DEPENDENCIES:
                errors.append(
                    f"{entity_name}.{field_spec.get('name')}: "
                    f"unsupported dependency '{dependency_type}'."
                )

    # ------------------------------------------------------------------
    # Relationships
    # ------------------------------------------------------------------

    def _validate_relationships(
        self,
        specification: dict[str, Any],
    ) -> ValidationResult:

        relationships = specification.get("relationships")

        if not isinstance(relationships, list):
            return ValidationResult(
                category="Relationships",
                passed=False,
                errors=["'relationships' must be a list."],
            )

        errors: list[str] = []
        entity_names = self._entity_names(specification)

        relationship_ids: set[str] = set()

        for relationship in relationships:

            if not isinstance(relationship, dict):
                errors.append("Every relationship must be an object.")
                continue

            relationship_id = relationship.get("id")

            if not relationship_id:
                errors.append("Relationship is missing 'id'.")
            elif relationship_id in relationship_ids:
                errors.append(f"Duplicate relationship ID: {relationship_id}")

            relationship_ids.add(relationship_id)

            relationship_type = relationship.get("type")

            if relationship_type not in (
                "1:1",
                "0:1",
                "1:N",
                "0:N",
                "N:M",
            ):
                errors.append(
                    f"{relationship_id}: unsupported relationship "
                    f"type '{relationship_type}'."
                )

            semantics = relationship.get("semantics", [])

            for semantic in semantics:
                if semantic not in VocabularyRegistry.RELATIONSHIPS:
                    errors.append(
                        f"{relationship_id}: unsupported relationship "
                        f"semantic '{semantic}'."
                    )

            if relationship_type == "N:M":
                self._validate_endpoint(
                    relationship_id,
                    relationship.get("left"),
                    entity_names,
                    errors,
                )
                self._validate_endpoint(
                    relationship_id,
                    relationship.get("right"),
                    entity_names,
                    errors,
                )

                associative = relationship.get("associative_entity")

                if associative not in entity_names:
                    errors.append(
                        f"{relationship_id}: associative entity "
                        f"'{associative}' does not exist."
                    )
            else:
                self._validate_endpoint(
                    relationship_id,
                    relationship.get("parent"),
                    entity_names,
                    errors,
                )
                self._validate_endpoint(
                    relationship_id,
                    relationship.get("child"),
                    entity_names,
                    errors,
                )

        return ValidationResult(
            category="Relationships",
            passed=not errors,
            errors=errors,
        )

    def _validate_endpoint(
        self,
        relationship_id: str | None,
        endpoint: Any,
        entity_names: set[str],
        errors: list[str],
    ) -> None:

        if not isinstance(endpoint, dict):
            errors.append(
                f"{relationship_id}: relationship endpoint " "must be an object."
            )
            return

        entity = endpoint.get("entity")
        field_name = endpoint.get("field")

        if entity not in entity_names:
            errors.append(
                f"{relationship_id}: referenced entity " f"'{entity}' does not exist."
            )
            return

        if not field_name:
            errors.append(
                f"{relationship_id}: relationship endpoint " "is missing field."
            )

    # ------------------------------------------------------------------
    # Rules
    # ------------------------------------------------------------------

    def _validate_rules(
        self,
        specification: dict[str, Any],
    ) -> ValidationResult:

        rules = specification.get("rules")

        if not isinstance(rules, list):
            return ValidationResult(
                category="Rules",
                passed=False,
                errors=["'rules' must be a list."],
            )

        errors: list[str] = []
        rule_ids: set[str] = set()

        for rule in rules:

            if not isinstance(rule, dict):
                errors.append("Every rule must be an object.")
                continue

            rule_id = rule.get("id")

            if not rule_id:
                errors.append("Rule is missing 'id'.")
            elif rule_id in rule_ids:
                errors.append(f"Duplicate rule ID: {rule_id}")

            rule_ids.add(rule_id)

            expression = rule.get("expression")

            if not isinstance(expression, dict):
                errors.append(f"{rule_id}: expression must be an object.")
                continue

            operators = self._find_operators(expression)

            for operator in operators:
                if operator not in VocabularyRegistry.RULE_OPERATORS:
                    errors.append(
                        f"{rule_id}: unsupported rule operator " f"'{operator}'."
                    )

        return ValidationResult(
            category="Rules",
            passed=not errors,
            errors=errors,
        )

    def _find_operators(
        self,
        value: Any,
    ) -> set[str]:

        operators: set[str] = set()

        if isinstance(value, dict):
            operator = value.get("operator")

            if isinstance(operator, str):
                operators.add(operator)

            for nested in value.values():
                operators.update(self._find_operators(nested))

        elif isinstance(value, list):
            for item in value:
                operators.update(self._find_operators(item))

        return operators

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

        if not isinstance(definitions, list):
            return ValidationResult(
                category="Statistical behavior",
                passed=False,
                errors=["'statistical_behavior' must be a list."],
            )

        errors: list[str] = []

        for definition in definitions:
            if not isinstance(definition, dict):
                errors.append("Statistical behavior entry must be an object.")
                continue

            behavior_type = definition.get("type")

            if behavior_type not in ("CORRELATION",):
                errors.append(
                    f"Unsupported statistical behavior " f"'{behavior_type}'."
                )

            method = definition.get("method")

            if method not in (
                "PEARSON",
                "SPEARMAN",
            ):
                errors.append(f"Unsupported statistical method '{method}'.")

            direction = definition.get("direction")

            if direction not in (
                "POSITIVE",
                "NEGATIVE",
            ):
                errors.append(f"Unsupported statistical direction " f"'{direction}'.")

        return ValidationResult(
            category="Statistical behavior",
            passed=not errors,
            errors=errors,
        )

    # ------------------------------------------------------------------
    # Scenarios
    # ------------------------------------------------------------------

    def _validate_scenarios(
        self,
        specification: dict[str, Any],
    ) -> ValidationResult:

        scenarios = specification.get("scenarios", [])

        if not isinstance(scenarios, list):
            return ValidationResult(
                category="Scenarios",
                passed=False,
                errors=["'scenarios' must be a list."],
            )

        errors: list[str] = []
        names: set[str] = set()

        for scenario in scenarios:
            if not isinstance(scenario, dict):
                errors.append("Scenario must be an object.")
                continue

            name = scenario.get("name")

            if not name:
                errors.append("Scenario is missing 'name'.")
            elif name in names:
                errors.append(f"Duplicate scenario: {name}")

            names.add(name)

            scenario_type = scenario.get("type")

            if scenario_type != "SCENARIO":
                errors.append(
                    f"{name}: expected type SCENARIO, " f"got {scenario_type!r}."
                )

        return ValidationResult(
            category="Scenarios",
            passed=not errors,
            errors=errors,
        )

    # ------------------------------------------------------------------
    # Validation configuration
    # ------------------------------------------------------------------

    def _validate_validation_configuration(
        self,
        specification: dict[str, Any],
    ) -> ValidationResult:

        validation = specification.get("validation")

        errors: list[str] = []

        if not isinstance(validation, dict):
            errors.append("'validation' must be an object.")
        else:
            categories = validation.get("categories", [])

            if not isinstance(categories, list):
                errors.append("validation.categories must be a list.")
            else:
                for category in categories:
                    if category not in (VocabularyRegistry.VALIDATION_EVIDENCE):
                        errors.append(
                            f"Unsupported validation category " f"'{category}'."
                        )

        return ValidationResult(
            category="Validation configuration",
            passed=not errors,
            errors=errors,
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

        if not isinstance(provenance, dict):
            errors.append("'provenance' must be an object.")
        else:
            if provenance.get("enabled") is not True:
                errors.append("Provenance must be enabled for Experiment 020.")

        return ValidationResult(
            category="Provenance configuration",
            passed=not errors,
            errors=errors,
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

        if not isinstance(reproducibility, dict):
            errors.append("'reproducibility' must be an object.")
        else:
            if reproducibility.get("enabled") is not True:
                errors.append("Reproducibility must be enabled.")

        return ValidationResult(
            category="Reproducibility configuration",
            passed=not errors,
            errors=errors,
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _supports(
        self,
        value: str,
        category: str,
    ) -> bool:

        values = VocabularyRegistry.CATEGORIES.get(
            category,
            set(),
        )

        return value in values

    def _supports_any(
        self,
        value: str,
        categories: list[str],
    ) -> bool:

        return any(
            value
            in VocabularyRegistry.CATEGORIES.get(
                category,
                set(),
            )
            for category in categories
        )

    @staticmethod
    def _entity_names(
        specification: dict[str, Any],
    ) -> set[str]:

        return {
            entity["name"]
            for entity in specification.get("entities", [])
            if isinstance(entity, dict) and entity.get("name")
        }


# ============================================================================
# GENERATION CONTEXT
# ============================================================================


@dataclass
class GenerationContext:
    """
    Runtime context shared by future generation components.

    This is deliberately small at 020-A. Later stages will add generated
    datasets, dependency graphs, random generators, scenario state, and
    provenance collectors.
    """

    specification_version: str
    seed: int
    random_state: int
    random_stream: str
    deterministic: bool
    scenario: str

    entities: dict[str, Any] = field(default_factory=dict)
    generated_data: dict[str, Any] = field(default_factory=dict)
    dependency_graph: dict[str, set[str]] = field(default_factory=dict)
    provenance: list[dict[str, Any]] = field(default_factory=list)

    @classmethod
    def from_specification(
        cls,
        specification: dict[str, Any],
    ) -> "GenerationContext":

        metadata = specification["specification"]
        control = specification["generation_control"]
        execution = specification.get("execution", {})

        entities = {
            entity["name"]: entity for entity in specification.get("entities", [])
        }

        return cls(
            specification_version=metadata["version"],
            seed=int(control["seed"]),
            random_state=int(control["random_state"]),
            random_stream=str(control["random_stream"]),
            deterministic=bool(control["deterministic"]),
            scenario=str(
                execution.get(
                    "scenario",
                    "NORMAL",
                )
            ),
            entities=entities,
        )


# ============================================================================
# FOUNDATION ENGINE
# ============================================================================


class FoundationEngine:
    """
    Coordinates the 020-A foundation workflow.

    This class is intentionally orchestration-only. It does not contain
    generation algorithms.
    """

    def __init__(
        self,
        specification_path: Path,
    ) -> None:

        self.specification_path = specification_path

        self.loader = SpecificationLoader(specification_path)

        self.vocabulary = VocabularyRegistry()

        self.validator = SpecificationValidator(self.vocabulary)

    def run(
        self,
    ) -> tuple[
        dict[str, Any],
        GenerationContext,
        list[ValidationResult],
    ]:

        specification = self.loader.load()

        validation_results = self.validator.validate(specification)

        if not all(result.passed for result in validation_results):
            raise StructuralValidationError("Specification validation failed.")

        context = GenerationContext.from_specification(specification)

        return (
            specification,
            context,
            validation_results,
        )


# ============================================================================
# OUTPUT
# ============================================================================


def save_validation_results(
    specification: dict[str, Any],
    context: GenerationContext,
    results: list[ValidationResult],
) -> None:

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    payload = {
        "experiment": "020",
        "stage": "020-A",
        "status": "PASS",
        "specification": {
            "name": specification["specification"]["name"],
            "version": specification["specification"]["version"],
            "experiment": specification["specification"]["experiment"],
        },
        "context": {
            "seed": context.seed,
            "random_state": context.random_state,
            "random_stream": context.random_stream,
            "deterministic": context.deterministic,
            "scenario": context.scenario,
        },
        "validation": [
            {
                "category": result.category,
                "status": result.status,
                "errors": result.errors,
            }
            for result in results
        ],
    }

    with VALIDATION_OUTPUT_PATH.open(
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(
            payload,
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
    print(f"Stage:          020-A - Foundation")
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


def print_context(
    context: GenerationContext,
) -> None:

    print("Generation context:")
    print(f"  Entities:       {len(context.entities)}")
    print(f"  Seed:           {context.seed}")
    print(f"  Random state:   {context.random_state}")
    print(f"  Random stream:  {context.random_stream}")
    print(f"  Deterministic:  {context.deterministic}")
    print(f"  Scenario:       {context.scenario}")
    print()


def print_vocabulary_summary() -> None:

    print("Controlled vocabulary:")

    for category, values in VocabularyRegistry.CATEGORIES.items():
        print(f"  {category:<28}" f"{len(values):>3} supported")

    print()


# ============================================================================
# MAIN
# ============================================================================


def main() -> int:

    try:
        engine = FoundationEngine(SPECIFICATION_PATH)

        specification = engine.loader.load()

        context = GenerationContext.from_specification(specification)

        print_header(
            specification,
            context,
        )

        print_vocabulary_summary()

        (
            specification,
            context,
            validation_results,
        ) = engine.run()

        print_validation_results(validation_results)

        print_context(context)

        save_validation_results(
            specification,
            context,
            validation_results,
        )

        print("Foundation result:")
        print("  Vocabulary validation:       PASS")
        print("  Specification validation:    PASS")
        print("  Generation context:          PASS")
        print("  Overall:                     PASS")
        print()
        print("Output:")
        print(f"  Validation: " f"{VALIDATION_OUTPUT_PATH}")
        print()
        print("Experiment completed successfully.")

        return 0

    except ForgeSpecificationError as exc:
        print()
        print("Experiment result:")
        print("  Overall:                     FAIL")
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
