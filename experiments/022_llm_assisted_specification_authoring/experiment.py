#!/usr/bin/env python3
"""
FORGE - Experiment 022: LLM-Assisted Progressive Specification Authoring
==========================================================================

Purpose
-------
Validate whether a real LLM can progressively translate natural-language
data requirements into controlled FORGE model operations.

The LLM is an authoring assistant only.

It does not:
- generate Python
- generate CSV
- execute generation
- invent FORGE vocabulary
- directly modify the canonical specification

The FORGE model and validation layer remain authoritative.

Experiment
----------
022 - LLM-Assisted Progressive Specification Authoring

Research Question
-----------------
Can a real LLM progressively construct a valid FORGE model from
natural-language requirements while remaining constrained to the
existing FORGE specification contract?

Architecture
------------
    User requirement
           |
           v
    LLM Authoring Assistant
           |
           v
    Structured FORGE Operations
           |
           v
    Operation Validation
           |
           v
    Candidate Model
           |
           v
    Authoring Model Validation
           |
           v
    Accepted Model State
           |
           v
    Next User Requirement
           |
           v
          ...
           |
           v
    Final FORGE Specification
           |
           v
    Strict Specification Validation

LLM
---
Default provider: Ollama
Default model:    gemma4:12b

Configuration:
    AIXP_OLLAMA_URL
    AIXP_LLM_MODEL

The model can be overridden without changing this experiment.

No pre-existing specification.json is required.

Output
------
    output/specification.json
    output/specification_authoring_results.json
    output/authoring_trace.json

Author
------
Ranjoy Sen

Status
------
Experimental
"""

from __future__ import annotations

import copy
import json
import os
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

# ============================================================================
# PATHS
# ============================================================================

EXPERIMENT_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = EXPERIMENT_DIR / "output"

SPECIFICATION_OUTPUT = OUTPUT_DIR / "specification.json"
RESULTS_OUTPUT = OUTPUT_DIR / "specification_authoring_results.json"
TRACE_OUTPUT = OUTPUT_DIR / "authoring_trace.json"


# ============================================================================
# LLM CONFIGURATION
# ============================================================================

OLLAMA_URL = os.getenv(
    "AIXP_OLLAMA_URL",
    "http://localhost:11434/api/generate",
)

MODEL = os.getenv(
    "AIXP_LLM_MODEL",
    "gemma4:12b",
)

LLM_TIMEOUT_SECONDS = int(
    os.getenv(
        "AIXP_LLM_TIMEOUT",
        "120",
    )
)


# ============================================================================
# FORGE CONTRACT
# ============================================================================

FORGE_VERSION = "1.0.0"
FORGE_VOCABULARY_VERSION = "1.0"

ALLOWED_OPERATIONS = {
    "ADD_ENTITY",
    "ADD_FIELD",
    "UPDATE_FIELD",
    "UPDATE_POPULATION",
    "ADD_CONSTRAINT",
    "ADD_DEPENDENCY",
    "ADD_RELATIONSHIP",
}


SUPPORTED_FIELD_TYPES = {
    "IDENTIFIER",
    "STRING",
    "INTEGER",
    "DECIMAL",
    "BOOLEAN",
    "CATEGORICAL",
}

SUPPORTED_IDENTITY_STRATEGIES = {
    "SEQUENTIAL_ID",
}

SUPPORTED_GENERATION_STRATEGIES = {
    "RANDOM",
}

SUPPORTED_DISTRIBUTIONS = {
    "UNIFORM",
    "CATEGORICAL",
    "DISCRETE_UNIFORM",
    "NORMAL",
    "POISSON",
}

SUPPORTED_STRING_GENERATORS = {
    "RANDOM_STRING",
    "PATTERN",
    "SEMANTIC",
}

SEMANTIC_PREVIEW_COUNT = 10

SUPPORTED_STRING_CHARACTER_SETS = {
    "ALPHA",
    "DIGITS",
    "ALPHANUMERIC",
}

SUPPORTED_OPERATORS = {
    ">",
    ">=",
    "<",
    "<=",
    "==",
    "!=",
}

# ============================================================================
# INITIAL FORGE MODEL
# ============================================================================


def create_empty_model() -> dict[str, Any]:
    """
    Create the empty progressive authoring model.

    This is NOT yet an executable specification.
    """

    return {
        "version": FORGE_VERSION,
        "vocabulary_version": FORGE_VOCABULARY_VERSION,
        "model": {
            "name": "llm_authored_model",
            "description": ("Progressively authored FORGE model."),
        },
        "generation": {
            "seed": 42,
            "scenario": "NORMAL",
        },
        "entities": [],
        "relationships": [],
        "constraints": [],
        "dependencies": [],
        "statistical_behavior": [],
        "scenarios": [],
    }


# ============================================================================
# MODEL HELPERS
# ============================================================================


def entity_map(
    model: dict[str, Any],
) -> dict[str, dict[str, Any]]:
    return {entity["name"]: entity for entity in model.get("entities", [])}


def field_map(
    model: dict[str, Any],
) -> dict[str, dict[str, dict[str, Any]]]:
    return {
        entity["name"]: {field["name"]: field for field in entity.get("fields", [])}
        for entity in model.get("entities", [])
    }


def split_reference(
    reference: str,
) -> tuple[str, str]:
    if not isinstance(reference, str) or "." not in reference:
        raise ValueError(f"Invalid field reference: {reference!r}")

    entity_name, field_name = reference.split(
        ".",
        1,
    )

    if not entity_name or not field_name:
        raise ValueError(f"Invalid field reference: {reference!r}")

    return entity_name, field_name


def find_field(
    model: dict[str, Any],
    reference: str,
) -> dict[str, Any]:
    entity_name, field_name = split_reference(reference)

    entities = entity_map(model)

    if entity_name not in entities:
        raise ValueError(f"Unknown entity: {entity_name}")

    for field in entities[entity_name].get(
        "fields",
        [],
    ):
        if field["name"] == field_name:
            return field

    raise ValueError(f"Unknown field: {reference}")


def field_exists(
    model: dict[str, Any],
    reference: str,
) -> bool:
    try:
        find_field(
            model,
            reference,
        )
        return True
    except ValueError:
        return False


# ============================================================================
# STRICT FORGE SPECIFICATION VALIDATION
# ============================================================================


def validate_specification(
    specification: dict[str, Any],
) -> list[str]:

    errors: list[str] = []

    required_top_level = {
        "version",
        "vocabulary_version",
        "model",
        "generation",
        "entities",
        "relationships",
        "constraints",
        "dependencies",
        "statistical_behavior",
        "scenarios",
    }

    missing = sorted(required_top_level - set(specification))

    if missing:
        errors.append(f"Missing top-level sections: {missing}")

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

    for entity in entities:

        if not isinstance(
            entity,
            dict,
        ):
            errors.append("Each entity must be an object.")
            continue

        name = entity.get("name")

        if (
            not isinstance(
                name,
                str,
            )
            or not name
        ):
            errors.append("Every entity must have a non-empty name.")
            continue

        if name in entity_names:
            errors.append(f"Duplicate entity: {name}")

        entity_names.add(name)

        population = entity.get("population")

        if not isinstance(
            population,
            dict,
        ):
            errors.append(f"{name}: population must be an object.")
        else:

            count = population.get("count")

            if (
                not isinstance(
                    count,
                    int,
                )
                or isinstance(
                    count,
                    bool,
                )
                or count < 0
            ):
                errors.append(
                    f"{name}: population.count must be " "a non-negative integer."
                )

        fields = entity.get("fields")

        if (
            not isinstance(
                fields,
                list,
            )
            or not fields
        ):
            errors.append(f"{name}: entity must contain at least one field.")
            continue

        field_names: set[str] = set()

        for field in fields:

            if not isinstance(
                field,
                dict,
            ):
                errors.append(f"{name}: each field must be an object.")
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
                errors.append(f"{name}: field has no valid name.")
                continue

            if field_name in field_names:
                errors.append(f"{name}: duplicate field {field_name}")

            field_names.add(field_name)

            if field_type not in SUPPORTED_FIELD_TYPES:
                errors.append(
                    f"{name}.{field_name}: unsupported " f"field type {field_type!r}."
                )
                continue

            # ------------------------------------------------------------
            # IDENTIFIER
            # ------------------------------------------------------------

            if field_type == "IDENTIFIER":

                identity = field.get("identity")

                if not isinstance(
                    identity,
                    dict,
                ):
                    errors.append(
                        f"{name}.{field_name}: IDENTIFIER "
                        "requires identity configuration."
                    )

                else:

                    strategy = identity.get("strategy")

                    if strategy not in SUPPORTED_IDENTITY_STRATEGIES:
                        errors.append(
                            f"{name}.{field_name}: unsupported "
                            f"identity strategy {strategy!r}."
                        )

                continue

            # ------------------------------------------------------------
            # NON-IDENTIFIER
            # ------------------------------------------------------------

            generation = field.get("generation")

            relationship_managed = is_field_relationship_managed(
                specification,
                name,
                field_name,
            )

            dependency_managed = is_field_dependency_managed(
                specification,
                name,
                field_name,
            )

            managed_by_relationship_or_dependency = (
                relationship_managed or dependency_managed
            )

            # A normal non-identifier field must have executable
            # generation configuration unless its value is supplied by
            # a relationship or dependency.
            if (
                not isinstance(
                    generation,
                    dict,
                )
                and not managed_by_relationship_or_dependency
            ):
                errors.append(
                    f"{name}.{field_name}: non-identifier "
                    "field requires generation configuration "
                    "unless relationship- or dependency-managed."
                )

            # Validate generation configuration when present.
            if isinstance(
                generation,
                dict,
            ):

                strategy = generation.get("strategy")

                if strategy not in SUPPORTED_GENERATION_STRATEGIES:
                    errors.append(
                        f"{name}.{field_name}: unsupported "
                        f"generation strategy {strategy!r}."
                    )

                if field_type == "BOOLEAN" and strategy != "RANDOM":
                    errors.append(
                        f"{name}.{field_name}: BOOLEAN fields only support "
                        "RANDOM generation."
                    )

                if field_type == "BOOLEAN":
                    # BOOLEAN generation is intrinsically binary.
                    # It does not use a statistical distribution.
                    if "distribution" in generation:
                        errors.append(
                            f"{name}.{field_name}: BOOLEAN fields must not "
                            "specify a distribution."
                        )

                elif field_type == "STRING" and generation.get("generator"):

                    generator = generation.get("generator")

                    if generator not in SUPPORTED_STRING_GENERATORS:
                        errors.append(
                            f"{name}.{field_name}: unsupported "
                            f"STRING generator {generator!r}."
                        )

                    elif generator == "RANDOM_STRING":

                        parameters = generation.get("parameters")

                        if not isinstance(parameters, dict):
                            errors.append(
                                f"{name}.{field_name}: RANDOM_STRING "
                                "requires parameters."
                            )
                        else:
                            minimum_length = parameters.get("minimum_length")
                            maximum_length = parameters.get("maximum_length")
                            character_set = parameters.get("character_set")

                            if not isinstance(minimum_length, int) or isinstance(
                                minimum_length, bool
                            ):
                                errors.append(
                                    f"{name}.{field_name}: RANDOM_STRING "
                                    "minimum_length must be an integer."
                                )

                            if not isinstance(maximum_length, int) or isinstance(
                                maximum_length, bool
                            ):
                                errors.append(
                                    f"{name}.{field_name}: RANDOM_STRING "
                                    "maximum_length must be an integer."
                                )

                            if (
                                isinstance(minimum_length, int)
                                and not isinstance(minimum_length, bool)
                                and isinstance(maximum_length, int)
                                and not isinstance(maximum_length, bool)
                                and minimum_length > maximum_length
                            ):
                                errors.append(
                                    f"{name}.{field_name}: RANDOM_STRING "
                                    "minimum_length cannot be greater than "
                                    "maximum_length."
                                )

                            if (
                                isinstance(minimum_length, int)
                                and not isinstance(minimum_length, bool)
                                and minimum_length < 1
                            ):
                                errors.append(
                                    f"{name}.{field_name}: RANDOM_STRING "
                                    "minimum_length must be greater than "
                                    "or equal to 1."
                                )

                            if (
                                isinstance(maximum_length, int)
                                and not isinstance(maximum_length, bool)
                                and maximum_length < 1
                            ):
                                errors.append(
                                    f"{name}.{field_name}: RANDOM_STRING "
                                    "maximum_length must be greater than "
                                    "or equal to 1."
                                )

                            if character_set not in (SUPPORTED_STRING_CHARACTER_SETS):
                                errors.append(
                                    f"{name}.{field_name}: unsupported "
                                    f"RANDOM_STRING character set "
                                    f"{character_set!r}."
                                )
                    elif generator == "PATTERN":

                        parameters = generation.get("parameters")

                        if not isinstance(parameters, dict):
                            errors.append(
                                f"{name}.{field_name}: PATTERN " "requires parameters."
                            )
                        else:
                            pattern = parameters.get("pattern")

                            if not isinstance(pattern, str):
                                errors.append(
                                    f"{name}.{field_name}: PATTERN "
                                    "pattern must be a string."
                                )
                            elif not pattern:
                                errors.append(
                                    f"{name}.{field_name}: PATTERN "
                                    "pattern must not be empty."
                                )
                    elif generator == "SEMANTIC":

                        parameters = generation.get("parameters")

                        if not isinstance(parameters, dict):
                            errors.append(
                                f"{name}.{field_name}: SEMANTIC " "requires parameters."
                            )
                        else:
                            description = parameters.get("description")

                            if not isinstance(description, str):
                                errors.append(
                                    f"{name}.{field_name}: SEMANTIC "
                                    "description must be a string."
                                )
                            elif not description.strip():
                                errors.append(
                                    f"{name}.{field_name}: SEMANTIC "
                                    "description must not be empty."
                                )

                else:
                    distribution = generation.get("distribution")

                    if distribution not in SUPPORTED_DISTRIBUTIONS:
                        errors.append(
                            f"{name}.{field_name}: unsupported "
                            f"distribution {distribution!r}."
                        )

                    if field_type == "DECIMAL" and distribution not in {
                        "UNIFORM",
                        "NORMAL",
                    }:
                        errors.append(
                            f"{name}.{field_name}: DECIMAL fields only support "
                            "UNIFORM or NORMAL distribution."
                        )

                    # --------------------------------------------------------
                    # INTEGER DISTRIBUTION RULES
                    # --------------------------------------------------------

                    if field_type == "INTEGER":
                        parameters = generation.get("parameters")

                        if distribution in {
                            "UNIFORM",
                            "DISCRETE_UNIFORM",
                        }:
                            if not isinstance(parameters, dict):
                                errors.append(
                                    f"{name}.{field_name}: INTEGER "
                                    f"{distribution} distribution requires "
                                    "parameters with minimum and maximum."
                                )
                            else:
                                minimum = parameters.get("minimum")
                                maximum = parameters.get("maximum")

                                if not isinstance(minimum, int) or isinstance(
                                    minimum, bool
                                ):
                                    errors.append(
                                        f"{name}.{field_name}: INTEGER "
                                        f"{distribution} minimum must be an integer."
                                    )

                                if not isinstance(maximum, int) or isinstance(
                                    maximum, bool
                                ):
                                    errors.append(
                                        f"{name}.{field_name}: INTEGER "
                                        f"{distribution} maximum must be an integer."
                                    )

                                if (
                                    isinstance(minimum, int)
                                    and not isinstance(minimum, bool)
                                    and isinstance(maximum, int)
                                    and not isinstance(maximum, bool)
                                    and minimum > maximum
                                ):
                                    errors.append(
                                        f"{name}.{field_name}: INTEGER "
                                        f"{distribution} minimum cannot be "
                                        "greater than maximum."
                                    )

                        elif distribution == "CATEGORICAL":
                            if not isinstance(parameters, dict):
                                errors.append(
                                    f"{name}.{field_name}: INTEGER "
                                    "CATEGORICAL distribution requires "
                                    "parameters with values."
                                )
                            else:
                                values = parameters.get("values")

                                if not isinstance(values, list) or not values:
                                    errors.append(
                                        f"{name}.{field_name}: INTEGER "
                                        "CATEGORICAL distribution requires "
                                        "a non-empty values list."
                                    )
                                elif any(
                                    not isinstance(value, int)
                                    or isinstance(value, bool)
                                    for value in values
                                ):
                                    errors.append(
                                        f"{name}.{field_name}: INTEGER "
                                        "CATEGORICAL values must all be integers."
                                    )

                        else:
                            errors.append(
                                f"{name}.{field_name}: INTEGER fields do not "
                                f"support {distribution!r} distribution."
                            )

    validate_relationships(
        specification,
        errors,
    )

    validate_constraints(
        specification,
        errors,
    )

    validate_dependencies(
        specification,
        errors,
    )

    return errors


def is_field_relationship_managed(
    specification: dict[str, Any],
    entity_name: str,
    field_name: str,
) -> bool:

    field_reference = f"{entity_name}.{field_name}"

    relationships = specification.get(
        "relationships",
        [],
    )

    for relationship in relationships:

        source = relationship.get("source")

        if source == field_reference:
            return True

    return False


def is_field_dependency_managed(
    specification: dict[str, Any],
    entity_name: str,
    field_name: str,
) -> bool:

    relationships = specification.get(
        "relationships",
        [],
    )

    for relationship in relationships:

        source = relationship.get("source")

        target = relationship.get("target")

        if target == f"{entity_name}.{field_name}":
            return True

        if source == f"{entity_name}.{field_name}":
            return False

    dependencies = specification.get(
        "dependencies",
        [],
    )

    for dependency in dependencies:

        target = dependency.get("target")

        if target == f"{entity_name}.{field_name}":
            return True

    return False


def validate_relationships(
    specification: dict[str, Any],
    errors: list[str],
) -> None:

    entities = entity_map(specification)

    relationships = specification.get(
        "relationships",
        [],
    )

    if not isinstance(
        relationships,
        list,
    ):
        errors.append("relationships must be a list.")
        return

    for relationship in relationships:

        if not isinstance(
            relationship,
            dict,
        ):
            errors.append("Each relationship must be an object.")
            continue

        source = relationship.get("source")

        target = relationship.get("target")

        relationship_type = relationship.get("type")

        for reference in (
            source,
            target,
        ):
            if not isinstance(
                reference,
                str,
            ):
                errors.append("Relationship source and target " "must be strings.")
                continue

            try:
                entity_name, field_name = split_reference(reference)
            except ValueError as exc:
                errors.append(str(exc))
                continue

            if entity_name not in entities:
                errors.append(
                    f"Relationship references unknown entity " f"{entity_name}."
                )
                continue

            if not any(
                field["name"] == field_name
                for field in entities[entity_name].get(
                    "fields",
                    [],
                )
            ):
                errors.append(f"Relationship references unknown field " f"{reference}.")

        if relationship_type not in {
            "ONE_TO_ONE",
            "ONE_TO_MANY",
            "MANY_TO_ONE",
            "MANY_TO_MANY",
        }:
            errors.append(f"Unsupported relationship type " f"{relationship_type!r}.")


def validate_constraints(
    specification: dict[str, Any],
    errors: list[str],
) -> None:

    for constraint in specification.get(
        "constraints",
        [],
    ):

        if not isinstance(
            constraint,
            dict,
        ):
            errors.append("Each constraint must be an object.")
            continue

        entity = constraint.get("entity")

        field = constraint.get("field")

        operator = constraint.get("operator")

        if entity not in entity_map(specification):
            errors.append(f"Constraint references unknown entity " f"{entity!r}.")
            continue

        referenced_field = None

        if not field_exists(
            specification,
            f"{entity}.{field}",
        ):
            errors.append(f"Constraint references unknown field " f"{entity}.{field}.")
        else:
            entity_object = entity_map(specification).get(entity)

            if entity_object:
                referenced_field = next(
                    (
                        candidate
                        for candidate in entity_object.get(
                            "fields",
                            [],
                        )
                        if candidate.get("name") == field
                    ),
                    None,
                )

        if operator not in SUPPORTED_OPERATORS:
            errors.append(f"Unsupported constraint operator " f"{operator!r}.")

        # -------------------------------------------------------------
        # CATEGORICAL OPERATOR VALIDATION
        # -------------------------------------------------------------

        if referenced_field is not None:

            generation = referenced_field.get(
                "generation",
            )

            is_categorical = referenced_field.get("type") == "CATEGORICAL" or (
                isinstance(generation, dict)
                and generation.get("distribution") == "CATEGORICAL"
            )

            if is_categorical and operator not in {"==", "!="}:
                errors.append(
                    f"{entity}.{field}: categorical constraints only "
                    "support == or != operators."
                )

        # -------------------------------------------------------------
        # CATEGORICAL VALUE VALIDATION
        # -------------------------------------------------------------

        if referenced_field is not None and "value" in constraint:

            generation = referenced_field.get(
                "generation",
            )

            is_categorical = referenced_field.get("type") == "CATEGORICAL" or (
                isinstance(generation, dict)
                and generation.get("distribution") == "CATEGORICAL"
            )

            if is_categorical:

                parameters = (
                    generation.get("parameters")
                    if isinstance(generation, dict)
                    else None
                )

                values = (
                    parameters.get("values") if isinstance(parameters, dict) else None
                )

                if not isinstance(values, list) or not values:

                    errors.append(
                        f"{entity}.{field}: categorical constraint "
                        "requires a non-empty declared vocabulary."
                    )

                elif constraint["value"] not in values:

                    errors.append(
                        f"{entity}.{field}: constraint value "
                        f"{constraint['value']!r} is not in the "
                        "declared categorical vocabulary."
                    )


def validate_dependencies(
    specification: dict[str, Any],
    errors: list[str],
) -> None:

    entities = entity_map(specification)

    for dependency in specification.get(
        "dependencies",
        [],
    ):

        if not isinstance(
            dependency,
            dict,
        ):
            errors.append("Each dependency must be an object.")
            continue

        target = dependency.get("target")

        if not isinstance(
            target,
            str,
        ):
            errors.append("Dependency target must be a string.")
            continue

        if not field_exists(
            specification,
            target,
        ):
            errors.append(f"Dependency references unknown target " f"{target}.")

        dependency_type = dependency.get("type")

        if dependency_type not in {
            "DERIVED",
            "CONDITIONAL",
        }:
            errors.append(f"Unsupported dependency type " f"{dependency_type!r}.")

        source_fields = dependency.get(
            "source_fields",
            [],
        )

        if not isinstance(
            source_fields,
            list,
        ):
            errors.append(f"{target}: source_fields must be a list.")
            continue

        for source in source_fields:

            if not isinstance(
                source,
                str,
            ):
                errors.append(f"{target}: invalid source field " f"{source!r}.")
                continue

            if not field_exists(
                specification,
                source,
            ):
                errors.append(f"{target}: unknown source field " f"{source}.")


# ============================================================================
# PROGRESSIVE AUTHORING VALIDATION
# ============================================================================


def validate_authoring_model(
    model: dict[str, Any],
) -> list[str]:
    """
    Validate an intermediate authoring state.

    Unlike final specification validation, this function permits
    incomplete entities and fields.

    It still rejects structurally unsafe states such as duplicate
    entities, duplicate fields, invalid population values, and
    references to unknown entities.
    """

    errors: list[str] = []

    entities = model.get("entities", [])

    if not isinstance(
        entities,
        list,
    ):
        return ["entities must be a list."]

    entity_names: set[str] = set()

    for entity in entities:

        name = entity.get("name")

        if (
            not isinstance(
                name,
                str,
            )
            or not name
        ):
            errors.append("Entity must have a name.")
            continue

        if name in entity_names:
            errors.append(f"Duplicate entity: {name}")

        entity_names.add(name)

        population = entity.get("population")

        if population is not None:

            count = population.get("count")

            if count is not None and (
                not isinstance(
                    count,
                    int,
                )
                or isinstance(
                    count,
                    bool,
                )
                or count < 0
            ):
                errors.append(f"{name}: invalid population count.")

        fields = entity.get("fields", [])

        field_names: set[str] = set()

        for field in fields:

            field_name = field.get("name")

            if (
                not isinstance(
                    field_name,
                    str,
                )
                or not field_name
            ):
                errors.append(f"{name}: field must have a name.")
                continue

            if field_name in field_names:
                errors.append(f"{name}: duplicate field {field_name}")

            field_names.add(field_name)

            field_type = field.get("type")

            if field_type is not None and field_type not in SUPPORTED_FIELD_TYPES:
                errors.append(
                    f"{name}.{field_name}: unsupported " f"field type {field_type!r}."
                )

            # ------------------------------------------------------------
            # GENERATION SEMANTICS
            # ------------------------------------------------------------

            generation = field.get("generation")

            if isinstance(generation, dict):

                strategy = generation.get("strategy")

                if strategy not in SUPPORTED_GENERATION_STRATEGIES:
                    errors.append(
                        f"{name}.{field_name}: unsupported "
                        f"generation strategy {strategy!r}."
                    )

                if field_type == "BOOLEAN":

                    if strategy != "RANDOM":
                        errors.append(
                            f"{name}.{field_name}: BOOLEAN fields only support "
                            "RANDOM generation."
                        )

                    if "distribution" in generation:
                        errors.append(
                            f"{name}.{field_name}: BOOLEAN fields must not "
                            "specify a distribution."
                        )

                elif field_type == "STRING" and generation.get("generator"):

                    generator = generation.get("generator")

                    if generator not in SUPPORTED_STRING_GENERATORS:
                        errors.append(
                            f"{name}.{field_name}: unsupported "
                            f"STRING generator {generator!r}."
                        )

                    elif generator == "RANDOM_STRING":

                        parameters = generation.get("parameters")

                        if not isinstance(parameters, dict):
                            errors.append(
                                f"{name}.{field_name}: RANDOM_STRING "
                                "requires parameters."
                            )
                        else:
                            minimum_length = parameters.get("minimum_length")
                            maximum_length = parameters.get("maximum_length")
                            character_set = parameters.get("character_set")

                            if not isinstance(minimum_length, int) or isinstance(
                                minimum_length, bool
                            ):
                                errors.append(
                                    f"{name}.{field_name}: RANDOM_STRING "
                                    "minimum_length must be an integer."
                                )

                            if not isinstance(maximum_length, int) or isinstance(
                                maximum_length, bool
                            ):
                                errors.append(
                                    f"{name}.{field_name}: RANDOM_STRING "
                                    "maximum_length must be an integer."
                                )

                            if (
                                isinstance(minimum_length, int)
                                and not isinstance(minimum_length, bool)
                                and isinstance(maximum_length, int)
                                and not isinstance(maximum_length, bool)
                                and minimum_length > maximum_length
                            ):
                                errors.append(
                                    f"{name}.{field_name}: RANDOM_STRING "
                                    "minimum_length cannot be greater than "
                                    "maximum_length."
                                )

                            if (
                                isinstance(minimum_length, int)
                                and not isinstance(minimum_length, bool)
                                and minimum_length < 1
                            ):
                                errors.append(
                                    f"{name}.{field_name}: RANDOM_STRING "
                                    "minimum_length must be greater than "
                                    "or equal to 1."
                                )

                            if (
                                isinstance(maximum_length, int)
                                and not isinstance(maximum_length, bool)
                                and maximum_length < 1
                            ):
                                errors.append(
                                    f"{name}.{field_name}: RANDOM_STRING "
                                    "maximum_length must be greater than "
                                    "or equal to 1."
                                )

                            if character_set not in (SUPPORTED_STRING_CHARACTER_SETS):
                                errors.append(
                                    f"{name}.{field_name}: unsupported "
                                    f"RANDOM_STRING character set "
                                    f"{character_set!r}."
                                )
                    elif generator == "PATTERN":

                        parameters = generation.get("parameters")

                        if not isinstance(parameters, dict):
                            errors.append(
                                f"{name}.{field_name}: PATTERN " "requires parameters."
                            )
                        else:
                            pattern = parameters.get("pattern")

                            if not isinstance(pattern, str):
                                errors.append(
                                    f"{name}.{field_name}: PATTERN "
                                    "pattern must be a string."
                                )
                            elif not pattern:
                                errors.append(
                                    f"{name}.{field_name}: PATTERN "
                                    "pattern must not be empty."
                                )

                    elif generator == "SEMANTIC":

                        parameters = generation.get("parameters")

                        if not isinstance(parameters, dict):
                            errors.append(
                                f"{name}.{field_name}: SEMANTIC " "requires parameters."
                            )
                        else:
                            description = parameters.get("description")

                            if not isinstance(description, str):
                                errors.append(
                                    f"{name}.{field_name}: SEMANTIC "
                                    "description must be a string."
                                )
                            elif not description.strip():
                                errors.append(
                                    f"{name}.{field_name}: SEMANTIC "
                                    "description must not be empty."
                                )

                else:

                    distribution = generation.get("distribution")

                    if distribution not in SUPPORTED_DISTRIBUTIONS:
                        errors.append(
                            f"{name}.{field_name}: unsupported "
                            f"distribution {distribution!r}."
                        )

                    # --------------------------------------------------------
                    # DECIMAL DISTRIBUTION RULES
                    # --------------------------------------------------------

                    if field_type == "DECIMAL" and distribution not in {
                        "UNIFORM",
                        "NORMAL",
                    }:
                        errors.append(
                            f"{name}.{field_name}: DECIMAL fields only support "
                            "UNIFORM or NORMAL distribution."
                        )

                    # --------------------------------------------------------
                    # INTEGER DISTRIBUTION RULES
                    # --------------------------------------------------------

                    if field_type == "INTEGER":
                        parameters = generation.get("parameters")

                        if distribution in {
                            "UNIFORM",
                            "DISCRETE_UNIFORM",
                        }:
                            if not isinstance(parameters, dict):
                                errors.append(
                                    f"{name}.{field_name}: INTEGER "
                                    f"{distribution} distribution requires "
                                    "parameters with minimum and maximum."
                                )
                            else:
                                minimum = parameters.get("minimum")
                                maximum = parameters.get("maximum")

                                if not isinstance(minimum, int) or isinstance(
                                    minimum, bool
                                ):
                                    errors.append(
                                        f"{name}.{field_name}: INTEGER "
                                        f"{distribution} minimum must be an integer."
                                    )

                                if not isinstance(maximum, int) or isinstance(
                                    maximum, bool
                                ):
                                    errors.append(
                                        f"{name}.{field_name}: INTEGER "
                                        f"{distribution} maximum must be an integer."
                                    )

                                if (
                                    isinstance(minimum, int)
                                    and not isinstance(minimum, bool)
                                    and isinstance(maximum, int)
                                    and not isinstance(maximum, bool)
                                    and minimum > maximum
                                ):
                                    errors.append(
                                        f"{name}.{field_name}: INTEGER "
                                        f"{distribution} minimum cannot be "
                                        "greater than maximum."
                                    )

                        elif distribution == "CATEGORICAL":
                            if not isinstance(parameters, dict):
                                errors.append(
                                    f"{name}.{field_name}: INTEGER "
                                    "CATEGORICAL distribution requires "
                                    "parameters with values."
                                )
                            else:
                                values = parameters.get("values")

                                if not isinstance(values, list) or not values:
                                    errors.append(
                                        f"{name}.{field_name}: INTEGER "
                                        "CATEGORICAL distribution requires "
                                        "a non-empty values list."
                                    )
                                elif any(
                                    not isinstance(value, int)
                                    or isinstance(value, bool)
                                    for value in values
                                ):
                                    errors.append(
                                        f"{name}.{field_name}: INTEGER "
                                        "CATEGORICAL values must all be integers."
                                    )

                        else:
                            errors.append(
                                f"{name}.{field_name}: INTEGER fields do not "
                                f"support {distribution!r} distribution."
                            )

    entities_by_name = entity_map(model)

    for relationship in model.get(
        "relationships",
        [],
    ):

        source = relationship.get("source")

        target = relationship.get("target")

        for reference in (
            source,
            target,
        ):

            if not isinstance(
                reference,
                str,
            ):
                errors.append("Relationship reference must be a string.")
                continue

            entity_name, field_name = split_reference(reference)

            if entity_name not in entities_by_name:
                errors.append(
                    f"Relationship references unknown entity " f"{entity_name}."
                )
                continue

            if not any(
                field["name"] == field_name
                for field in entities_by_name[entity_name].get(
                    "fields",
                    [],
                )
            ):
                errors.append(f"Relationship references unknown field " f"{reference}.")

        # -------------------------------------------------------------------------
        # CONSTRAINTS
        # -------------------------------------------------------------------------

        for constraint in model.get(
            "constraints",
            [],
        ):
            if not isinstance(
                constraint,
                dict,
            ):
                errors.append("Each constraint must be an object.")
                continue

            entity_name = constraint.get("entity")
            field_name = constraint.get("field")
            operator = constraint.get("operator")

            if (
                not isinstance(
                    entity_name,
                    str,
                )
                or not entity_name
            ):
                errors.append("Constraint entity must be a non-empty string.")
                continue

            if entity_name not in entities_by_name:
                errors.append(f"Constraint references unknown entity {entity_name}.")
                continue

            if (
                not isinstance(
                    field_name,
                    str,
                )
                or not field_name
            ):
                errors.append(
                    f"{entity_name}: constraint field must be a non-empty string."
                )
            elif not any(
                field["name"] == field_name
                for field in entities_by_name[entity_name].get(
                    "fields",
                    [],
                )
            ):
                errors.append(
                    f"Constraint references unknown field "
                    f"{entity_name}.{field_name}."
                )

            if operator not in SUPPORTED_OPERATORS:
                errors.append(f"Unsupported constraint operator {operator!r}.")

            # -------------------------------------------------------------
            # CATEGORICAL OPERATOR VALIDATION
            # -------------------------------------------------------------

            referenced_field = next(
                (
                    field
                    for field in entities_by_name[entity_name].get(
                        "fields",
                        [],
                    )
                    if field.get("name") == field_name
                ),
                None,
            )

            if referenced_field is not None:

                generation = referenced_field.get(
                    "generation",
                )

                is_categorical = referenced_field.get("type") == "CATEGORICAL" or (
                    isinstance(generation, dict)
                    and generation.get("distribution") == "CATEGORICAL"
                )

                if is_categorical and operator not in {"==", "!="}:
                    errors.append(
                        f"{entity_name}.{field_name}: categorical constraints "
                        "only support == or != operators."
                    )

            if "value" not in constraint:
                errors.append(
                    f"{entity_name}.{field_name}: constraint value is required."
                )

            # -------------------------------------------------------------
            # CATEGORICAL VALUE VALIDATION
            # -------------------------------------------------------------

            referenced_field = next(
                (
                    field
                    for field in entities_by_name[entity_name].get(
                        "fields",
                        [],
                    )
                    if field.get("name") == field_name
                ),
                None,
            )

            if referenced_field is not None and "value" in constraint:

                generation = referenced_field.get(
                    "generation",
                )

                is_categorical = referenced_field.get("type") == "CATEGORICAL" or (
                    isinstance(generation, dict)
                    and generation.get("distribution") == "CATEGORICAL"
                )

                if is_categorical:

                    parameters = (
                        generation.get("parameters")
                        if isinstance(generation, dict)
                        else None
                    )

                    values = (
                        parameters.get("values")
                        if isinstance(parameters, dict)
                        else None
                    )

                    if not isinstance(values, list) or not values:

                        errors.append(
                            f"{entity_name}.{field_name}: categorical "
                            "constraint requires a non-empty declared "
                            "vocabulary."
                        )

                    elif constraint["value"] not in values:

                        errors.append(
                            f"{entity_name}.{field_name}: constraint value "
                            f"{constraint['value']!r} is not in the declared "
                            "categorical vocabulary."
                        )

    return errors


# ============================================================================
# OPERATION VALIDATION
# ============================================================================


def validate_operation(
    model: dict[str, Any],
    operation: dict[str, Any],
) -> list[str]:

    errors: list[str] = []

    if not isinstance(
        operation,
        dict,
    ):
        return ["Operation must be an object."]

    operation_type = operation.get("operation")

    if operation_type not in ALLOWED_OPERATIONS:
        errors.append(f"Unsupported operation: {operation_type!r}")
        return errors

    entities = entity_map(model)

    fields = field_map(model)

    if operation_type == "ADD_ENTITY":

        entity = operation.get("entity")

        if not isinstance(
            entity,
            dict,
        ):
            errors.append("ADD_ENTITY requires entity.")
            return errors

        name = entity.get("name")

        if (
            not isinstance(
                name,
                str,
            )
            or not name
        ):
            errors.append("ADD_ENTITY requires a name.")

        elif name in entities:
            errors.append(f"Entity already exists: {name}")

        population = entity.get("population")

        if population is not None:

            count = population.get("count")

            if (
                not isinstance(
                    count,
                    int,
                )
                or isinstance(
                    count,
                    bool,
                )
                or count < 0
            ):
                errors.append("Population count must be a " "non-negative integer.")

    elif operation_type == "ADD_FIELD":

        entity_name = operation.get("entity")

        field = operation.get("field")

        if entity_name not in entities:
            errors.append(f"Unknown entity: {entity_name}")

        if not isinstance(
            field,
            dict,
        ):
            errors.append("ADD_FIELD requires field.")
            return errors

        field_name = field.get("name")

        if (
            not isinstance(
                field_name,
                str,
            )
            or not field_name
        ):
            errors.append("ADD_FIELD requires field.name.")

        elif entity_name in fields and field_name in fields[entity_name]:
            errors.append(f"Field already exists: " f"{entity_name}.{field_name}")

        field_type = field.get("type")

        if field_type not in SUPPORTED_FIELD_TYPES:
            errors.append(f"Unsupported field type: " f"{field_type!r}")

    elif operation_type == "UPDATE_FIELD":

        reference = operation.get("field")

        if not isinstance(
            reference,
            str,
        ):
            errors.append("UPDATE_FIELD requires field reference.")
        elif not field_exists(
            model,
            reference,
        ):
            errors.append(f"Unknown field: {reference}")

    elif operation_type == "UPDATE_POPULATION":

        entity_name = operation.get("entity")

        if entity_name not in entities:
            errors.append(f"Unknown entity: {entity_name}")

        count = operation.get("count")

        if (
            not isinstance(
                count,
                int,
            )
            or isinstance(
                count,
                bool,
            )
            or count < 0
        ):
            errors.append("Population count must be " "a non-negative integer.")

    elif operation_type == "ADD_CONSTRAINT":

        constraint = operation.get("constraint")

        if not isinstance(
            constraint,
            dict,
        ):
            errors.append("ADD_CONSTRAINT requires constraint.")
            return errors

        entity_name = constraint.get("entity")

        field_name = constraint.get("field")

        if entity_name not in entities:
            errors.append(f"Unknown entity: {entity_name}")

        elif not field_exists(
            model,
            f"{entity_name}.{field_name}",
        ):
            errors.append(f"Unknown field: " f"{entity_name}.{field_name}")

        if constraint.get("operator") not in SUPPORTED_OPERATORS:
            errors.append(
                f"Unsupported constraint operator: " f"{constraint.get('operator')!r}"
            )

    elif operation_type == "ADD_DEPENDENCY":

        dependency = operation.get("dependency")

        if not isinstance(
            dependency,
            dict,
        ):
            errors.append("ADD_DEPENDENCY requires dependency.")
            return errors

        target = dependency.get("target")

        if not isinstance(
            target,
            str,
        ):
            errors.append("Dependency target is required.")

        elif not field_exists(
            model,
            target,
        ):
            errors.append(f"Unknown dependency target: {target}")

        source_fields = dependency.get(
            "source_fields",
            [],
        )

        for source in source_fields:

            if not field_exists(
                model,
                source,
            ):
                errors.append(f"Unknown dependency source: {source}")

        if dependency.get("type") not in {
            "DERIVED",
            "CONDITIONAL",
        }:
            errors.append("Dependency type must be DERIVED or CONDITIONAL.")

    elif operation_type == "ADD_RELATIONSHIP":

        relationship = operation.get("relationship")

        if not isinstance(
            relationship,
            dict,
        ):
            errors.append("ADD_RELATIONSHIP requires relationship.")
            return errors

        source = relationship.get("source")

        target = relationship.get("target")

        if not isinstance(
            source,
            str,
        ) or not field_exists(
            model,
            source,
        ):
            errors.append(f"Unknown relationship source: {source}")

        if not isinstance(
            target,
            str,
        ) or not field_exists(
            model,
            target,
        ):
            errors.append(f"Unknown relationship target: {target}")

        if relationship.get("type") not in {
            "ONE_TO_ONE",
            "ONE_TO_MANY",
            "MANY_TO_ONE",
            "MANY_TO_MANY",
        }:
            errors.append("Unsupported relationship type.")

    return errors


# ============================================================================
# APPLY OPERATIONS
# ============================================================================


def apply_operation(
    model: dict[str, Any],
    operation: dict[str, Any],
) -> None:

    operation_type = operation["operation"]

    if operation_type == "ADD_ENTITY":

        entity = copy.deepcopy(operation["entity"])

        entity.setdefault(
            "population",
            {},
        )

        entity.setdefault(
            "fields",
            [],
        )

        model["entities"].append(entity)

    elif operation_type == "ADD_FIELD":

        entity_name = operation["entity"]

        field = copy.deepcopy(operation["field"])

        for entity in model["entities"]:
            if entity["name"] == entity_name:
                entity.setdefault(
                    "fields",
                    [],
                ).append(field)
                return

        raise ValueError(f"Unknown entity: {entity_name}")

    elif operation_type == "UPDATE_FIELD":

        reference = operation["field"]

        entity_name, field_name = split_reference(reference)

        updates = operation.get(
            "updates",
            {},
        )

        for entity in model["entities"]:
            if entity["name"] == entity_name:

                for field in entity.get(
                    "fields",
                    [],
                ):
                    if field["name"] == field_name:
                        field.update(copy.deepcopy(updates))
                        return

        raise ValueError(f"Unknown field: {reference}")

    elif operation_type == "UPDATE_POPULATION":

        entity_name = operation["entity"]

        count = operation["count"]

        for entity in model["entities"]:
            if entity["name"] == entity_name:
                entity["population"] = {"count": count}
                return

        raise ValueError(f"Unknown entity: {entity_name}")

    elif operation_type == "ADD_CONSTRAINT":

        model["constraints"].append(copy.deepcopy(operation["constraint"]))

    elif operation_type == "ADD_DEPENDENCY":

        model["dependencies"].append(copy.deepcopy(operation["dependency"]))

    elif operation_type == "ADD_RELATIONSHIP":

        model["relationships"].append(copy.deepcopy(operation["relationship"]))

    else:
        raise ValueError(f"Unsupported operation: {operation_type}")


# ============================================================================
# LLM PROMPT
# ============================================================================


def build_system_prompt() -> str:
    return """
You are the FORGE Specification Authoring Assistant.

Your role is to translate a user's natural-language data-modeling requirement
into controlled FORGE authoring operations.

FORGE stands for:

    Framework for Observed Rules, Generation & Engineered Data

You are NOT the data generator.

You are NOT the dataset generator.

You are NOT allowed to write Python, SQL, CSV, or generated records.

Your only responsibility is to propose valid FORGE authoring operations that
modify the CURRENT FORGE MODEL.

============================================================
1. CORE PRINCIPLE
============================================================

FORGE is domain agnostic.

You must NOT assume or introduce knowledge about any particular business,
industry, application, enterprise system, or domain.

The user supplies the domain concepts.

You supply only the FORGE modeling semantics.

Do not assume that an entity, field, relationship, constraint, or behavior
has any meaning beyond what the user explicitly states.

Never introduce domain-specific entities or fields that the user did not
request.

Never use predefined business examples to influence your interpretation.

============================================================
2. CURRENT MODEL AND CURRENT REQUEST ARE THE SOURCE OF TRUTH
============================================================

The CURRENT FORGE MODEL supplied with each request is authoritative.

The USER'S LATEST REQUEST is the only source of new requirements for the
current authoring step.

Before proposing operations:

- Inspect the current model.
- Determine what entities and fields already exist.
- Do not recreate existing entities.
- Do not recreate existing fields.
- Do not overwrite existing information unless the user explicitly requests
  a change.
- Build new operations on top of the current model.
- Treat the user's latest requirement as an incremental change to the model.

CURRENT-REQUEST BOUNDARY:

- Author ONLY what is explicitly requested in the user's latest request.
- Do NOT anticipate future requirements.
- Do NOT add fields because they would normally belong to an entity.
- Do NOT add fields because they are common in a known business system.
- Do NOT add fields because they were mentioned as possible future requirements.
- Do NOT infer a complete schema from the name or meaning of an entity.
- Do NOT convert a business concept into a field unless the latest user request
  explicitly requires that field.
- Do NOT use domain knowledge to expand the requested model.
- If the user asks only for an entity and its population, propose ONLY the
  entity and population.
- If the user asks only for a field and provides enough information to define
  that field completely, propose ONLY that field.
- If the user asks for several fields, propose those fields and no additional
  fields.
- If a later request is expected to add more information, wait for that request.

For example, if the user says:

    "Create an entity named CustomerRecord with 100 records."

the correct response is to create CustomerRecord with population 100.

Do NOT add fields such as CUSTOMER_ID, NAME, COUNTRY, STATUS, or any other
fields unless the user explicitly requests them.

Before proposing an operation, resolve all referenced model elements against
the CURRENT FORGE MODEL.

A natural-language concept is not automatically a model field.

If a requirement depends on a model element that cannot be resolved to the
CURRENT FORGE MODEL, do not guess or substitute another element.

Ask for clarification when the missing information is necessary to construct
a valid operation.

The model may be incomplete during progressive authoring.

Do not require an incomplete intermediate model to already satisfy the final
FORGE specification rules.

However, do not confuse an incomplete AUTHORING MODEL with an incomplete
OPERATION.

An operation proposed by the assistant must itself be valid for the stated
requirement.

============================================================
3. CONTROLLED OPERATIONS
============================================================

You may use ONLY these operations:

ADD_ENTITY
ADD_FIELD
UPDATE_FIELD
UPDATE_POPULATION
ADD_CONSTRAINT
ADD_DEPENDENCY
ADD_RELATIONSHIP

Do not invent additional operation names.

Do not invent additional top-level operation properties.

Do not create arbitrary FORGE vocabulary.

============================================================
4. SUPPORTED FIELD TYPES
============================================================

The currently supported field types are:

- IDENTIFIER
- STRING
- INTEGER
- DECIMAL
- BOOLEAN
- CATEGORICAL

Use only these field types.

Do not invent additional field types.

============================================================
5. IDENTITY STRATEGIES
============================================================

The currently supported identity strategy is:

- SEQUENTIAL_ID

An IDENTIFIER field must contain an identity configuration.

Canonical structure:

{
  "operation": "ADD_FIELD",
  "entity": "<ENTITY_NAME>",
  "field": {
    "name": "<FIELD_NAME>",
    "type": "IDENTIFIER",
    "identity": {
      "strategy": "SEQUENTIAL_ID"
    }
  }
}

Do not add generation configuration to an IDENTIFIER field unless the
current FORGE vocabulary explicitly supports it.

============================================================
6. GENERATION STRATEGIES
============================================================

The currently supported generation strategy is:

- RANDOM

Generated fields require executable generation configuration unless their
value is managed by a relationship or dependency.

For a normal distribution-based generated field, the canonical structure is:

{
  "operation": "ADD_FIELD",
  "entity": "<ENTITY_NAME>",
  "field": {
    "name": "<FIELD_NAME>",
    "type": "<SUPPORTED_FIELD_TYPE>",
    "generation": {
      "strategy": "RANDOM",
      "distribution": "<SUPPORTED_DISTRIBUTION>"
    }
  }
}

Do not use "DERIVED" or "CONDITIONAL" as generation strategies.

DERIVED and CONDITIONAL are dependency types.

IMPORTANT:

If the user requests a generated field but does not provide enough
information to construct its required generation configuration, do NOT
invent a distribution.

Return CLARIFY instead.

For example:

User:
    "Add a decimal field called ORDER_VALUE."

If no generation behavior has been specified, do NOT assume UNIFORM.

Return CLARIFY because DECIMAL requires generation configuration in a
complete FORGE specification.

============================================================
6A. STRING GENERATION
============================================================

STRING fields may use distribution-based generation or an explicit
STRING generator, depending on the requested generation behavior.

The currently supported explicit STRING generator is:

- RANDOM_STRING

Do not invent additional STRING generators.

------------------------------------------------------------
6A.1. CATEGORICAL STRING GENERATION
------------------------------------------------------------

When a STRING field should be randomly selected from a finite set of
explicit values, use the CATEGORICAL distribution.

The canonical structure is:

{
  "strategy": "RANDOM",
  "distribution": "CATEGORICAL",
  "parameters": {
    "values": ["<VALUE_1>", "<VALUE_2>", "..."]
  }
}

The values must be explicitly provided by the user.

Do not invent categorical values.

------------------------------------------------------------
6A.2. RANDOM_STRING GENERATION
------------------------------------------------------------

Use RANDOM_STRING when the user requests an opaque randomly generated
string rather than selecting from a finite set of known values.

The canonical RANDOM_STRING structure is:

{
  "strategy": "RANDOM",
  "generator": "RANDOM_STRING",
  "parameters": {
    "minimum_length": <INTEGER>,
    "maximum_length": <INTEGER>,
    "character_set": "<SUPPORTED_CHARACTER_SET>"
  }
}

The currently supported RANDOM_STRING character sets are:

- ALPHA
- DIGITS
- ALPHANUMERIC

minimum_length and maximum_length must be positive integers.

minimum_length must not be greater than maximum_length.

Do not invent additional character sets.

Do not invent a default minimum length.

Do not invent a default maximum length.

Do not invent a default character set when the user's requirement does not
provide enough information to determine the intended character set.

If the user requests RANDOM_STRING but does not provide enough information
to construct its required parameters, return CLARIFY.

For example:

User:
    "Add a random string field called CUSTOMER_CODE."

Correct response:

{
  "status": "CLARIFY",
  "message": "What length range and character set should CUSTOMER_CODE use?",
  "operations": []
}

If the user says:

    "Add an 8 to 12 character alphanumeric random string called CUSTOMER_CODE."

the canonical operation is:

{
  "operation": "ADD_FIELD",
  "entity": "<ENTITY_NAME>",
  "field": {
    "name": "CUSTOMER_CODE",
    "type": "STRING",
    "generation": {
      "strategy": "RANDOM",
      "generator": "RANDOM_STRING",
      "parameters": {
        "minimum_length": 8,
        "maximum_length": 12,
        "character_set": "ALPHANUMERIC"
      }
    }
  }
}

RANDOM_STRING is not a distribution.

Do not add RANDOM_STRING to the distribution vocabulary.

Do not use RANDOM_STRING for INTEGER, DECIMAL, BOOLEAN, IDENTIFIER, or
CATEGORICAL fields.

RANDOM_STRING generates opaque strings. Do not infer semantic names,
business codes, words, dates, identifiers, or domain-specific formats from
the field name.

If the user requests a specific pattern or semantic format that cannot be
represented by RANDOM_STRING, return CLARIFY or UNSUPPORTED as appropriate.

============================================================
6B. BOOLEAN GENERATION
============================================================

DECIMAL represents numeric values that may contain a fractional
component.

DECIMAL is the single FORGE field type for fractional numeric values.

Use DECIMAL for values such as:

- prices
- monetary amounts
- rates
- percentages
- measurements
- calculated numeric values
- other numeric values that may contain fractional components

Do NOT create or use a separate FLOAT field type.

If the user describes a value using terms such as:

- floating-point
- floating point
- float
- fractional number
- decimal number
- numeric value with decimals

map the requirement to DECIMAL unless the user explicitly requires
machine-level floating-point representation.

FORGE does not currently model machine-level floating-point
representation as a separate field type.

The canonical DECIMAL generation structure is:

{
  "operation": "ADD_FIELD",
  "entity": "<ENTITY_NAME>",
  "field": {
    "name": "<FIELD_NAME>",
    "type": "DECIMAL",
    "generation": {
      "strategy": "RANDOM",
      "distribution": "<SUPPORTED_DISTRIBUTION>"
    }
  }
}

DECIMAL currently supports:

- UNIFORM
- NORMAL

Use only these distributions for DECIMAL fields.

Do NOT use:

- CATEGORICAL
- DISCRETE_UNIFORM
- POISSON

for DECIMAL fields.

Do NOT assume a distribution when the user has not provided enough
information to determine the intended generation behavior.

For example:

"Generate a decimal SCORE using a uniform distribution."

must produce conceptually:

{
  "operation": "ADD_FIELD",
  "entity": "<ENTITY_NAME>",
  "field": {
    "name": "SCORE",
    "type": "DECIMAL",
    "generation": {
      "strategy": "RANDOM",
      "distribution": "UNIFORM"
    }
  }
}

If the user specifies a DECIMAL field but does not specify how it
should be generated, create the DECIMAL field without inventing a
distribution.

Do NOT infer precision, scale, rounding, minimum, maximum, or other
numeric parameters unless those properties are explicitly supported
by the current FORGE vocabulary.

Do NOT invent properties such as:

- precision
- scale
- rounding
- decimal_places
- significant_digits
- min
- max
- minimum
- maximum

unless those properties are explicitly supported by the current
FORGE operation contract.

If the user provides numeric bounds or other generation parameters,
use them only when the current FORGE vocabulary explicitly supports
their representation.

If the user says how DECIMAL values should be generated, sampled,
selected, or distributed, represent that as generation configuration.

If the user says what values a DECIMAL field must or must not satisfy,
represent that as a constraint when the requirement is deterministic.

If the requested DECIMAL behavior cannot be represented using the
current FORGE vocabulary, return CLARIFY or UNSUPPORTED as
appropriate.

============================================================
6C. DECIMAL GENERATION
============================================================

DECIMAL represents exact decimal or fixed-point numeric values.

Use DECIMAL when the user explicitly requests or describes decimal,
fixed-point, monetary-style, or exact decimal semantics.

DECIMAL is the single FORGE field type for fractional numeric values.

Do NOT create or infer another fractional numeric field type.

Whether the user describes the value as decimal, fractional, floating-point,
monetary, measurement-based, or another numeric value with a fractional
component, use DECIMAL unless the user explicitly requires a capability that
is outside the current FORGE vocabulary.

DECIMAL fields require generation configuration when they are generated
directly.

The currently supported DECIMAL distributions are ONLY:

- UNIFORM
- NORMAL

Canonical DECIMAL structure:

{
  "operation": "ADD_FIELD",
  "entity": "<ENTITY_NAME>",
  "field": {
    "name": "<FIELD_NAME>",
    "type": "DECIMAL",
    "generation": {
      "strategy": "RANDOM",
      "distribution": "<DECIMAL_SUPPORTED_DISTRIBUTION>"
    }
  }
}

For example:

"Add a decimal field called ORDER_VALUE using a uniform distribution."

must produce conceptually:

{
  "operation": "ADD_FIELD",
  "entity": "<ENTITY_NAME>",
  "field": {
    "name": "ORDER_VALUE",
    "type": "DECIMAL",
    "generation": {
      "strategy": "RANDOM",
      "distribution": "UNIFORM"
    }
  }
}

The following distributions are NOT currently supported for DECIMAL:

- CATEGORICAL
- DISCRETE_UNIFORM
- POISSON

If the user explicitly requests one of these for a DECIMAL field, return
UNSUPPORTED.

For example:

User:
    "Generate ORDER_VALUE using a Poisson distribution."

Correct response:

{
  "status": "UNSUPPORTED",
  "message": "POISSON generation is not currently supported for DECIMAL fields.",
  "operations": []
}

If the user requests a DECIMAL field but does not specify its generation
behavior, return CLARIFY.

For example:

User:
    "Add a decimal field called ORDER_VALUE."

Correct response:

{
  "status": "CLARIFY",
  "message": "What generation behavior should ORDER_VALUE use? For example,
  specify UNIFORM or NORMAL.",
  "operations": []
}

Do NOT silently default DECIMAL generation to UNIFORM.

Do NOT silently default DECIMAL generation to NORMAL.

Do NOT invent DECIMAL-specific properties such as:

- precision
- scale
- decimal_places
- rounding
- significant_digits
- currency
- currency_code
- minimum
- maximum
- min
- max

unless those properties are explicitly supported by the current FORGE
vocabulary.

If the user provides numeric bounds, precision, scale, rounding, or other
DECIMAL requirements that cannot be represented using the current FORGE
operation contract, return CLARIFY or UNSUPPORTED as appropriate.

Do not encode DECIMAL generation behavior as an ADD_CONSTRAINT.

If the user describes how DECIMAL values should be generated, sampled,
selected, or distributed, represent that as generation configuration.

If the user describes what DECIMAL values must or must not satisfy,
represent that as a constraint when the requirement is deterministic.

============================================================
7. SUPPORTED DISTRIBUTIONS
============================================================

The currently supported distributions are:

- UNIFORM
- CATEGORICAL
- DISCRETE_UNIFORM
- NORMAL
- POISSON

Use only these distributions.

Distribution support is field-type-specific.

Do NOT assume that every supported distribution is valid for every
field type.

Current distribution rules:

- BOOLEAN:
    RANDOM only
    No distribution

- DECIMAL:
    UNIFORM
    NORMAL

-- INTEGER:
    UNIFORM
    CATEGORICAL
    DISCRETE_UNIFORM

- CATEGORICAL:
    CATEGORICAL

For field types not explicitly described above, do not infer additional
distribution compatibility beyond the FORGE vocabulary.

Field-type-specific rules take precedence over the generic distribution
list.

============================================================
7A. GENERATION INTENT VS VALIDATION CONSTRAINT
============================================================

Distinguish between a requirement that controls HOW VALUES ARE
GENERATED and a requirement that VALIDATES values after generation.

If the user describes how a generated value should be selected,
chosen, sampled, picked, or generated from a finite set of values,
use field generation configuration.

Examples of generation intent:

- "Country should be selected from US, DE, IN, GB and CA."
- "Choose one of A, B or C for this field."
- "Generate status from NEW, ACTIVE and CLOSED."
- "Pick the region randomly from North, South and West."
- "The country should be randomly selected from US, DE and IN."

For an existing field, these requirements MUST use UPDATE_FIELD
and configure:

{
  "generation": {
    "strategy": "RANDOM",
    "distribution": "CATEGORICAL",
    "values": ["<VALUE_1>", "<VALUE_2>", "..."]
  }
}

Do NOT represent generation selection from a finite set as an
ADD_CONSTRAINT operation.

Use ADD_CONSTRAINT when the user is describing a rule that must be
satisfied or validated rather than how a value should be generated.

Examples of validation intent:

- "Country must be US."
- "Country cannot be XX."
- "Quantity must be greater than zero."
- "Credit limit must be at least 1000."

GENERAL RULE:

"How should the value be generated?"
    -> generation configuration

"What values/ranges are allowed or required?"
    -> constraint

When the wording is genuinely ambiguous, ask for clarification
rather than guessing.

If the user explicitly requests an unsupported distribution, return:

{
  "status": "UNSUPPORTED",
  "message": "<explain that the requested capability is not currently supported>",
  "operations": []
}

============================================================
8. ADD_ENTITY
============================================================

Use ADD_ENTITY when the user requests a new entity.

Exact structure:

{
  "operation": "ADD_ENTITY",
  "entity": {
    "name": "<ENTITY_NAME>",
    "population": {
      "count": <NON_NEGATIVE_INTEGER>
    }
  }
}

If the user does not specify a population, the population may be omitted.

Do not invent a population unless the current authoring contract requires one.

============================================================
8A. CURRENT FORGE MODEL RESOLUTION
============================================================

The CURRENT FORGE MODEL is the authoritative source for all existing
entities and fields.

Existing entity and field references are CLOSED-WORLD REFERENCES.

Before proposing any operation that references an existing entity or field:

1. Inspect the CURRENT FORGE MODEL.
2. Resolve the reference against the entities and fields that actually
   exist in the CURRENT FORGE MODEL.
3. Use the exact existing entity and field names.
4. Never invent, rename, abbreviate, normalize, or substitute an entity
   or field name.
5. Never assume that an entity has an identifier field unless that field
   actually exists.
6. Never create a placeholder, helper field, foreign-key field, or
   semantic substitute merely to satisfy another operation.
7. If the required entity or field does not exist, return CLARIFY.
8. If multiple existing fields could match a semantic description and
   the match is not unambiguous, return CLARIFY.
9. Do not propose the operation until every referenced entity and field
   has been resolved successfully.

This rule applies to:

- UPDATE_FIELD
- UPDATE_POPULATION
- ADD_CONSTRAINT
- ADD_DEPENDENCY
- ADD_RELATIONSHIP

IMPORTANT:

A field mentioned by the user in a previous request is NOT considered
part of the CURRENT FORGE MODEL unless an ADD_FIELD operation for that
field was accepted.

Do not use fields from rejected, clarified, or unaccepted requests.

============================================================
8B. ADD_RELATIONSHIP REFERENCE RULES
============================================================

ADD_RELATIONSHIP operates only on fields that already exist.

The relationship operation MUST reference two existing entity.field
references.

Before proposing ADD_RELATIONSHIP:

1. Resolve the source entity against the CURRENT FORGE MODEL.
2. Resolve the source field against that entity.
3. Resolve the target entity against the CURRENT FORGE MODEL.
4. Resolve the target field against that entity.
5. Confirm that both complete entity.field references exist.
6. Use their exact names.

The relationship operation MUST NOT create the fields required for the
relationship.

Never invent relationship endpoint fields such as:

- ID
- IDENTIFIER
- KEY
- ORDER_ID
- CUSTOMER_ID
- <OTHER_ENTITY>_ID
- <OTHER_ENTITY>_LINK
- <OTHER_ENTITY>_REFERENCE

unless that exact field already exists in the CURRENT FORGE MODEL.

Do not infer an identifier field from the fact that an entity represents
an identifiable business object.

Do not infer a foreign-key field from the relationship described by the
user.

If the user describes a relationship but the required endpoint fields
do not exist, return CLARIFY and ask for the missing field information.

If the user describes a relationship semantically, resolve it only
against existing fields. Never invent a new field name to make the
relationship possible.

The relationship type must also be selected according to the user's
stated cardinality. Do not change MANY_TO_ONE into MANY_TO_MANY merely
because multiple child records may exist.

============================================================
8C. ADD_CONSTRAINT REFERENCE RULES
============================================================

ADD_CONSTRAINT operates only on an existing field.

Before proposing ADD_CONSTRAINT:

1. Resolve the entity against the CURRENT FORGE MODEL.
2. Resolve the field against that entity.
3. Use the exact existing field name.
4. Do not invent a semantic replacement for the field.
5. Do not create a field merely to satisfy the constraint.

If the user describes a field semantically, match that description only
against fields that actually exist in the CURRENT FORGE MODEL.

For example, if the CURRENT FORGE MODEL contains:

ORDER:
    NETWR

and the user says:

"The order net value must be greater than or equal to zero."

The constraint must reference:

ORDER.NETWR

Do NOT invent:

ORDER.NET_VALUE
ORDER.NET_ORDER_VALUE
ORDER.ORDER_VALUE

If no unambiguous existing field matches the user's description, return
CLARIFY.

============================================================
9. ADD_FIELD
============================================================

Use ADD_FIELD when the user requests a new field.

The field type must be explicitly provided by the user or otherwise
unambiguously determined from the user's explicit requirement.

For an IDENTIFIER:

{
  "operation": "ADD_FIELD",
  "entity": "<ENTITY_NAME>",
  "field": {
    "name": "<FIELD_NAME>",
    "type": "IDENTIFIER",
    "identity": {
      "strategy": "SEQUENTIAL_ID"
    }
  }
}

For BOOLEAN:

{
  "operation": "ADD_FIELD",
  "entity": "<ENTITY_NAME>",
  "field": {
    "name": "<FIELD_NAME>",
    "type": "BOOLEAN",
    "generation": {
      "strategy": "RANDOM"
    }
  }
}

For INTEGER:

INTEGER fields support only the following distributions:

- UNIFORM
- DISCRETE_UNIFORM
- CATEGORICAL

For INTEGER with UNIFORM:

{
  "operation": "ADD_FIELD",
  "entity": "<ENTITY_NAME>",
  "field": {
    "name": "<FIELD_NAME>",
    "type": "INTEGER",
    "generation": {
      "strategy": "RANDOM",
      "distribution": "UNIFORM",
      "parameters": {
        "minimum": <INTEGER>,
        "maximum": <INTEGER>
      }
    }
  }
}

For INTEGER with DISCRETE_UNIFORM:

{
  "operation": "ADD_FIELD",
  "entity": "<ENTITY_NAME>",
  "field": {
    "name": "<FIELD_NAME>",
    "type": "INTEGER",
    "generation": {
      "strategy": "RANDOM",
      "distribution": "DISCRETE_UNIFORM",
      "parameters": {
        "minimum": <INTEGER>,
        "maximum": <INTEGER>
      }
    }
  }
}

For INTEGER with CATEGORICAL:

{
  "operation": "ADD_FIELD",
  "entity": "<ENTITY_NAME>",
  "field": {
    "name": "<FIELD_NAME>",
    "type": "INTEGER",
    "generation": {
      "strategy": "RANDOM",
      "distribution": "CATEGORICAL",
      "parameters": {
        "values": [<INTEGER>, <INTEGER>, <INTEGER>]
      }
    }
  }
}

For UNIFORM and DISCRETE_UNIFORM, parameters.minimum and
parameters.maximum are required and must be integers.

For CATEGORICAL, parameters.values is required and must be a
non-empty list of integers.

Do not place INTEGER distribution parameters directly under
"generation". They must be contained inside "generation.parameters".

Do not use NORMAL or POISSON for INTEGER fields.

============================================================
9A. STRING ADD_FIELD
============================================================

STRING fields may use either CATEGORICAL distribution-based generation
or RANDOM_STRING generation.

For STRING with CATEGORICAL:

{
  "operation": "ADD_FIELD",
  "entity": "<ENTITY_NAME>",
  "field": {
    "name": "<FIELD_NAME>",
    "type": "STRING",
    "generation": {
      "strategy": "RANDOM",
      "distribution": "CATEGORICAL",
      "parameters": {
        "values": ["<VALUE_1>", "<VALUE_2>", "<VALUE_3>"]
      }
    }
  }
}

For STRING with RANDOM_STRING:

{
  "operation": "ADD_FIELD",
  "entity": "<ENTITY_NAME>",
  "field": {
    "name": "<FIELD_NAME>",
    "type": "STRING",
    "generation": {
      "strategy": "RANDOM",
      "generator": "RANDOM_STRING",
      "parameters": {
        "minimum_length": <INTEGER>,
        "maximum_length": <INTEGER>,
        "character_set": "<SUPPORTED_CHARACTER_SET>"
      }
    }
  }
}

RANDOM_STRING supports only these character sets:

- ALPHA
- DIGITS
- ALPHANUMERIC

For RANDOM_STRING:

- minimum_length is required.
- maximum_length is required.
- character_set is required.
- minimum_length must be a positive integer.
- maximum_length must be a positive integer.
- minimum_length must not be greater than maximum_length.

Do not place RANDOM_STRING under "distribution".

Do not use a RANDOM_STRING distribution.

Do not invent additional RANDOM_STRING parameters.

Do not invent a default length.

Do not invent a default character set.

If the user requests RANDOM_STRING but does not provide enough information
to construct the required parameters, return CLARIFY.

For example:

User:
    "Add a random string field called CUSTOMER_CODE."

Return CLARIFY.

User:
    "Add an 8 to 12 character alphanumeric random string called CUSTOMER_CODE."

Propose:

{
  "operation": "ADD_FIELD",
  "entity": "<ENTITY_NAME>",
  "field": {
    "name": "CUSTOMER_CODE",
    "type": "STRING",
    "generation": {
      "strategy": "RANDOM",
      "generator": "RANDOM_STRING",
      "parameters": {
        "minimum_length": 8,
        "maximum_length": 12,
        "character_set": "ALPHANUMERIC"
      }
    }
  }
}

Do not infer a semantic string format from the field name.

For example, do not assume that CUSTOMER_CODE means a particular code
pattern, prefix, suffix, character count, or character set unless the user
explicitly provides that requirement.

If the user requests a string pattern that cannot be represented by the
current RANDOM_STRING vocabulary, return UNSUPPORTED or CLARIFY as
appropriate.

Do not invent another STRING field type to represent the requested pattern.

If the user requests an INTEGER field without enough information to
construct its required generation configuration, return CLARIFY.

Do not invent INTEGER minimum, maximum, or categorical values.

For a directly generated non-BOOLEAN field, generation configuration is
required in a complete proposed operation.

If the user has not provided enough information to determine that
generation configuration, return CLARIFY.

Do NOT create an incomplete generated field merely because the field name
and type are known.

For example:

User:
    "Add a decimal field called ORDER_VALUE."

Do NOT propose:

{
  "operation": "ADD_FIELD",
  "entity": "ORDER",
  "field": {
    "name": "ORDER_VALUE",
    "type": "DECIMAL"
  }
}

Instead return CLARIFY because the generation behavior is required.

Do not invent unsupported field configuration.

============================================================
10. UPDATE_FIELD
============================================================

Use UPDATE_FIELD when an existing field needs to be modified.

The field must be specified as a complete entity.field reference.

Exact structure:

{
  "operation": "UPDATE_FIELD",
  "field": "<ENTITY_NAME>.<FIELD_NAME>",
  "updates": {
    "<SUPPORTED_PROPERTY>": "<VALUE>"
  }
}

Do NOT use this structure:

{
  "operation": "UPDATE_FIELD",
  "entity": "...",
  "field": {
    "name": "..."
  }
}

The "field" property for UPDATE_FIELD MUST be a string reference.

Only modify properties that are supported by the FORGE model.

Before using UPDATE_FIELD, resolve the field against the CURRENT FORGE
MODEL.

Do not update a field that does not exist.

============================================================
11. UPDATE_POPULATION
============================================================

Use UPDATE_POPULATION when the user changes the population of an existing
entity.

Exact structure:

{
  "operation": "UPDATE_POPULATION",
  "entity": "<ENTITY_NAME>",
  "count": <NON_NEGATIVE_INTEGER>
}

Before using UPDATE_POPULATION, resolve the entity against the CURRENT
FORGE MODEL.

============================================================
12. ADD_CONSTRAINT
============================================================

Use ADD_CONSTRAINT when the user specifies a deterministic constraint on
a field.

Exact structure:

{
  "operation": "ADD_CONSTRAINT",
  "constraint": {
    "entity": "<ENTITY_NAME>",
    "field": "<FIELD_NAME>",
    "operator": "<SUPPORTED_OPERATOR>",
    "value": <VALUE>
  }
}

Supported operators:

- >
- >=
- <
- <=
- ==
- !=

Multiple constraints should be represented as multiple ADD_CONSTRAINT
operations.

Do not encode arbitrary natural-language conditions into the constraint
object.

Do not invent constraint properties.

============================================================
13. ADD_DEPENDENCY
============================================================

Use ADD_DEPENDENCY when the value or behavior of one field depends on one
or more other fields.

Supported dependency types:

- DERIVED
- CONDITIONAL

Exact structure:

{
  "operation": "ADD_DEPENDENCY",
  "dependency": {
    "target": "<ENTITY_NAME>.<TARGET_FIELD>",
    "type": "DERIVED",
    "source_fields": [
      "<ENTITY_NAME>.<SOURCE_FIELD_1>",
      "<ENTITY_NAME>.<SOURCE_FIELD_2>"
    ]
  }
}

or:

{
  "operation": "ADD_DEPENDENCY",
  "dependency": {
    "target": "<ENTITY_NAME>.<TARGET_FIELD>",
    "type": "CONDITIONAL",
    "source_fields": [
      "<ENTITY_NAME>.<SOURCE_FIELD>"
    ]
  }
}

The current authoring operation contract does NOT define an expression
property or an arbitrary condition property.

Therefore:

- Do not invent "expression".
- Do not invent "condition".
- Do not invent other dependency properties.
- If the user's requirement requires dependency semantics that cannot be
  represented by the current operation contract, return CLARIFY or
  UNSUPPORTED rather than inventing a schema.

Before proposing ADD_DEPENDENCY:

- Resolve the target against the CURRENT FORGE MODEL.
- Resolve every source field against the CURRENT FORGE MODEL.
- Every source field MUST correspond to an existing field.
- Do not invent a source field.
- Do not infer a missing source field from a field name.
- Do not substitute an existing field for a missing source field.
- Do not use the target as its own source field unless the current FORGE
  vocabulary explicitly supports that dependency pattern.

If the requirement refers to a concept that cannot be resolved to an
existing field in the CURRENT FORGE MODEL, return CLARIFY.

Do not create an ADD_DEPENDENCY operation until all required source fields
can be resolved.

============================================================
14. ADD_RELATIONSHIP
============================================================

Use ADD_RELATIONSHIP when the user defines a relationship between fields
belonging to different entities.

The source and target MUST be complete entity.field references.

Exact structure:

{
  "operation": "ADD_RELATIONSHIP",
  "relationship": {
    "source": "<ENTITY_A>.<FIELD_A>",
    "target": "<ENTITY_B>.<FIELD_B>",
    "type": "<RELATIONSHIP_TYPE>"
  }
}

Supported relationship types:

- ONE_TO_ONE
- ONE_TO_MANY
- MANY_TO_ONE
- MANY_TO_MANY

If a relationship requires a field that does not yet exist, create the
required entity and field first, then create the relationship, provided
the user explicitly requested or necessarily requires those elements.

Within one response, operations are applied sequentially.

Therefore operation ordering matters.

============================================================
15. OPERATION ORDER
============================================================

When multiple operations are required, order them logically.

Typical progression:

1. ADD_ENTITY
2. ADD_FIELD
3. UPDATE_FIELD
4. UPDATE_POPULATION
5. ADD_CONSTRAINT
6. ADD_DEPENDENCY
7. ADD_RELATIONSHIP

This is not a mandatory global sequence.

The important rule is:

An operation must not reference an entity or field that does not yet exist
unless an earlier operation in the SAME response creates it.

============================================================
16. DOMAIN INTERPRETATION
============================================================

Interpret the user's terminology literally and conservatively.

If the user says:

- create an entity
- add a field
- increase the population
- constrain a field
- define a dependency
- relate two fields

translate the requirement into the corresponding FORGE operation.

Do not add information that was not requested.

Do not assume semantic meaning from a field name alone.

Do not assume distributions, ranges, relationships, or business rules
unless the user provides enough information to justify them.

============================================================
17. DETERMINISTIC VS STATISTICAL BEHAVIOR
============================================================

Distinguish deterministic requirements from statistical requirements.

A deterministic statement describes a rule that should hold for records.

A statistical statement describes a tendency, distribution, correlation,
or population-level behavior.

Do not convert a statistical statement into a deterministic constraint.

For example, a statement equivalent to:

"One category should generally have higher values than another category."

describes statistical behavior, not a simple field constraint.

If the currently available operations cannot represent the requested
statistical behavior, do not approximate it using an unrelated deterministic
constraint.

Return CLARIFY or UNSUPPORTED as appropriate.

============================================================
18. NO HIDDEN ASSUMPTIONS
============================================================

Never silently assume:

- a field type
- a distribution
- a population
- an identity strategy
- a relationship cardinality
- a constraint value
- a dependency expression
- a conditional rule
- a statistical relationship

when the requirement does not provide enough information.

If the missing information is necessary to construct a valid operation,
return CLARIFY.

IMPORTANT EXCEPTION:

BOOLEAN has a fixed generation contract.

If the user explicitly requests a BOOLEAN field and does not specify
generation behavior, RANDOM generation is implied by the FORGE BOOLEAN
semantics.

Therefore BOOLEAN does not require a distribution clarification.

============================================================
19. CLARIFICATION
============================================================

If the user's requirement cannot be safely translated without additional
information, return:

{
  "status": "CLARIFY",
  "message": "<specific question that must be answered>",
  "operations": []
}

Ask only for information necessary to continue authoring.

Do not propose speculative operations while asking for clarification.

A clarification should identify the specific missing information.

For example:

{
  "status": "CLARIFY",
  "message": "What generation behavior should ORDER_VALUE use? Specify a supported DECIMAL distribution such as UNIFORM or NORMAL.",
  "operations": []
}

============================================================
20. UNSUPPORTED CAPABILITY
============================================================

If the user requests a capability that is outside the currently supported
FORGE vocabulary or operation contract, return:

{
  "status": "UNSUPPORTED",
  "message": "<specific explanation of the unsupported capability>",
  "operations": []
}

Do not invent a new operation.

Do not invent a new vocabulary value.

Do not approximate the requested capability using an unrelated feature.

Use UNSUPPORTED when the user explicitly requests a capability that FORGE
does not currently support.

Use CLARIFY when the capability may be representable but required
information is missing or ambiguous.

============================================================
21. PROGRESSIVE AUTHORING
============================================================

Authoring is incremental.

The user may provide requirements one at a time.

Each response should propose ONLY the operations required for the user's
LATEST requirement, taking the CURRENT FORGE MODEL into account.

Do not regenerate the entire model.

Do not repeat operations that have already been accepted.

Do not recreate existing entities or fields.

A field may be introduced in one request and its generation behavior
configured in a later request only if the current operation/model contract
allows the intermediate state.

However, when responding to a request that asks for a complete generated
field definition, do not intentionally propose an incomplete field.

============================================================
22. OUTPUT CONTRACT
============================================================

Your response MUST be valid JSON.

The top-level JSON object MUST contain exactly:

{
  "status": "PROPOSE" | "CLARIFY" | "UNSUPPORTED",
  "message": "<short explanation>",
  "operations": []
}

For PROPOSE:

- operations MUST contain one or more valid FORGE operations.
- Every proposed operation MUST conform to the current FORGE operation
  contract.
- Do not propose an operation that is known to fail final specification
  validation when the requirement is asking for a complete field definition.

For CLARIFY:

- operations MUST be an empty list.

For UNSUPPORTED:

- operations MUST be an empty list.

Do not include:

- thoughts
- reasoning
- analysis
- tool calls
- markdown
- code fences
- commentary outside the JSON object
- arbitrary metadata

============================================================
23. FINAL RULE
============================================================

Your job is NOT to decide what the user's domain model should be.

Your job is to translate the user's stated requirements into the controlled
FORGE authoring language.

The user defines the domain.

FORGE defines the modeling vocabulary.

You bridge the two without adding domain knowledge or unsupported behavior.

When information is missing:

    Do NOT guess.
    Do NOT invent.
    Do NOT silently default.

Instead:

    CLARIFY when additional user information is required.

    UNSUPPORTED when the requested capability is outside the current
    FORGE vocabulary or operation contract.

    PROPOSE only when the requested change can be represented correctly
    using the current FORGE model and operation contract.
"""


# ============================================================================
# LLM CALL
# ============================================================================


def call_ollama(
    system_prompt: str,
    user_request: str,
    current_model: dict[str, Any],
) -> str:

    prompt = f"""
CURRENT FORGE MODEL:

{json.dumps(current_model, indent=2)}

USER REQUIREMENT:

{user_request}

Translate ONLY this user requirement into FORGE operations.
"""

    payload = {
        "model": MODEL,
        "prompt": prompt,
        "system": system_prompt,
        "stream": False,
        "format": "json",
        "options": {
            "temperature": 0,
        },
        "think": False,
    }

    request = urllib.request.Request(
        OLLAMA_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
        },
        method="POST",
    )

    try:

        with urllib.request.urlopen(
            request,
            timeout=LLM_TIMEOUT_SECONDS,
        ) as response:

            response_body = response.read().decode("utf-8")

    except urllib.error.URLError as exc:

        raise RuntimeError(
            "Unable to reach Ollama at "
            f"{OLLAMA_URL}. "
            "Make sure Ollama is running and the selected "
            f"model '{MODEL}' is available."
        ) from exc

    try:

        response_payload = json.loads(response_body)

    except json.JSONDecodeError as exc:

        raise RuntimeError("Ollama returned invalid JSON.") from exc

    response_text = response_payload.get("response")

    if not isinstance(
        response_text,
        str,
    ):
        raise RuntimeError("Ollama response did not contain " "a textual response.")

    return response_text.strip()


# ============================================================================
# SEMANTIC STRING LLM CONTRACT
# ============================================================================


def build_semantic_system_prompt() -> str:
    """
    Build the dedicated LLM contract for SEMANTIC STRING authoring.

    This contract is intentionally separate from the general FORGE
    operation-authoring protocol.

    The LLM interprets semantic intent and produces representative preview
    values. It does not create or modify FORGE model operations.
    """

    return f"""
You are the FORGE Semantic String Authoring Assistant.

Your only responsibility is to interpret a natural-language requirement for
the values of a FORGE STRING field and demonstrate that interpretation using
exactly {SEMANTIC_PREVIEW_COUNT} representative preview values.

You are NOT the FORGE data generator.

You are NOT the FORGE specification authoring assistant.

You must NOT create FORGE operations.

You must NOT create entities, fields, relationships, constraints,
dependencies, distributions, or generation rules.

You must NOT return Python, SQL, CSV, markdown, explanations outside the
defined JSON contract, or arbitrary metadata.

============================================================
1. INPUT
============================================================

You will receive one natural-language semantic description.

Example:

    Generate realistic first and last names.

Other examples:

    Generate realistic US street addresses.

    Generate realistic aerospace component descriptions.

    Generate concise descriptions of manufacturing defects.

    Generate realistic engineering document titles.

    Generate realistic customer email addresses for an enterprise dataset.

The description is the user's intent.

Do not silently add requirements that are not present in the description.

============================================================
2. INTERPRETATION
============================================================

First determine whether the description is sufficiently clear to generate
representative STRING values.

If it is clear:

- Return status PROPOSE.
- Provide a concise interpretation of the requested semantic content.
- Provide exactly {SEMANTIC_PREVIEW_COUNT} representative STRING values.

The interpretation must describe what the values represent.

Do not turn the interpretation into a FORGE operation.

============================================================
3. NO HIDDEN ASSUMPTIONS
============================================================

Do not silently assume important semantic requirements that the user did not
provide.

Examples of information that may require clarification include:

- country or geographic scope
- language
- naming convention
- business context
- audience
- format requirements
- level of realism
- required terminology
- domain-specific meaning
- required structure

Use reasonable interpretation only when the description is sufficiently clear
without materially changing the user's intent.

If an important ambiguity prevents a meaningful preview, return CLARIFY.

Do not guess merely to produce a preview.

============================================================
4. CLARIFY
============================================================

If additional user information is required, return:

{{
  "status": "CLARIFY",
  "message": "<short explanation of what needs clarification>",
  "preview_values": []
}}

The message must contain a specific clarification question or explain the
missing information.

Do not provide preview values when returning CLARIFY.

============================================================
5. UNSUPPORTED
============================================================

If the requested semantic capability cannot reasonably be represented as
STRING values by this capability, return:

{{
  "status": "UNSUPPORTED",
  "message": "<short explanation>",
  "preview_values": []
}}

Do not attempt to invent an alternative requirement.

============================================================
6. PROPOSE
============================================================

For a valid semantic requirement, return:

{{
  "status": "PROPOSE",
  "message": "<concise interpretation of the semantic requirement>",
  "preview_values": [
    "<value 1>",
    "<value 2>",
    "<value 3>",
    "<value 4>",
    "<value 5>",
    "<value 6>",
    "<value 7>",
    "<value 8>",
    "<value 9>",
    "<value 10>"
  ]
}}

The preview_values array MUST contain exactly {SEMANTIC_PREVIEW_COUNT}
values.

Every preview value MUST be a JSON string.

The values should be representative of the interpretation.

Do not number the values.

Do not add commentary to the values.

Do not return fewer or more than {SEMANTIC_PREVIEW_COUNT} values.

============================================================
7. IMPORTANT BOUNDARY
============================================================

The preview values are examples only.

They are NOT the FORGE specification.

Do not infer or return:

- field names
- field types
- generation strategies
- generators
- distributions
- constraints
- dependencies
- FORGE operations

The user's original semantic description remains the input that will
eventually be stored in the FORGE specification.

============================================================
8. OUTPUT CONTRACT
============================================================

Your response MUST be valid JSON.

The top-level JSON object MUST contain exactly:

{{
  "status": "PROPOSE" | "CLARIFY" | "UNSUPPORTED",
  "message": "<short explanation>",
  "preview_values": []
}}

For PROPOSE:

- status MUST be "PROPOSE"
- message MUST be a non-empty string
- preview_values MUST contain exactly {SEMANTIC_PREVIEW_COUNT} strings

For CLARIFY:

- status MUST be "CLARIFY"
- message MUST be a non-empty string
- preview_values MUST be an empty list

For UNSUPPORTED:

- status MUST be "UNSUPPORTED"
- message MUST be a non-empty string
- preview_values MUST be an empty list

Do not include:

- operations
- thoughts
- reasoning
- analysis
- markdown
- code fences
- tool calls
- arbitrary metadata
- model information
- FORGE specification objects

Return JSON only.
"""


def call_semantic_llm(
    description: str,
) -> str:
    """
    Call the LLM using the dedicated SEMANTIC STRING contract.

    This call is intentionally independent from the general FORGE
    operation-authoring flow.
    """

    prompt = f"""
SEMANTIC STRING REQUIREMENT:

{description}

Interpret this requirement according to the SEMANTIC STRING contract.
Return only the required JSON response.
"""

    payload = {
        "model": MODEL,
        "prompt": prompt,
        "system": build_semantic_system_prompt(),
        "stream": False,
        "format": "json",
        "options": {
            "temperature": 0,
        },
        "think": False,
    }

    request = urllib.request.Request(
        OLLAMA_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
        },
        method="POST",
    )

    try:

        with urllib.request.urlopen(
            request,
            timeout=LLM_TIMEOUT_SECONDS,
        ) as response:

            response_body = response.read().decode("utf-8")

    except urllib.error.URLError as exc:

        raise RuntimeError(
            "Unable to reach Ollama at "
            f"{OLLAMA_URL}. "
            "Make sure Ollama is running and the selected "
            f"model '{MODEL}' is available."
        ) from exc

    try:

        response_payload = json.loads(response_body)

    except json.JSONDecodeError as exc:

        raise RuntimeError("Ollama returned invalid JSON.") from exc

    response_text = response_payload.get("response")

    if not isinstance(response_text, str):

        raise RuntimeError("Ollama response did not contain a textual response.")

    return response_text.strip()


def parse_semantic_response(
    raw_response: str,
) -> dict[str, Any]:
    """
    Parse and strictly validate a SEMANTIC LLM response.

    This parser is intentionally independent from parse_llm_response(),
    because SEMANTIC responses are not FORGE operation responses.
    """

    text = raw_response.strip()

    # ------------------------------------------------------------------------
    # Tolerate accidental markdown fences
    # ------------------------------------------------------------------------

    if text.startswith("```"):

        lines = text.splitlines()

        if lines and lines[0].startswith("```"):
            lines = lines[1:]

        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]

        text = "\n".join(lines).strip()

    # ------------------------------------------------------------------------
    # Parse JSON
    # ------------------------------------------------------------------------

    try:

        response = json.loads(text)

    except json.JSONDecodeError as exc:

        raise ValueError("SEMANTIC LLM response was not valid JSON.") from exc

    if not isinstance(response, dict):

        raise ValueError("SEMANTIC LLM response must be a JSON object.")

    # ------------------------------------------------------------------------
    # Strict top-level contract
    # ------------------------------------------------------------------------

    expected_keys = {
        "status",
        "message",
        "preview_values",
    }

    actual_keys = set(response.keys())

    unexpected_keys = actual_keys - expected_keys

    if unexpected_keys:

        raise ValueError(
            "SEMANTIC LLM response contains unsupported keys: "
            f"{sorted(unexpected_keys)}."
        )

    missing_keys = expected_keys - actual_keys

    if missing_keys:

        raise ValueError(
            "SEMANTIC LLM response is missing required keys: "
            f"{sorted(missing_keys)}."
        )

    status = response.get("status")
    message = response.get("message")
    preview_values = response.get("preview_values")

    # ------------------------------------------------------------------------
    # Status
    # ------------------------------------------------------------------------

    allowed_statuses = {
        "PROPOSE",
        "CLARIFY",
        "UNSUPPORTED",
    }

    if status not in allowed_statuses:

        raise ValueError(
            "SEMANTIC LLM response contains unsupported status " f"{status!r}."
        )

    # ------------------------------------------------------------------------
    # Message
    # ------------------------------------------------------------------------

    if not isinstance(message, str) or not message.strip():

        raise ValueError("SEMANTIC LLM response message must be a non-empty string.")

    # ------------------------------------------------------------------------
    # Preview values container
    # ------------------------------------------------------------------------

    if not isinstance(preview_values, list):

        raise ValueError("SEMANTIC LLM preview_values must be a list.")

    # ------------------------------------------------------------------------
    # PROPOSE
    # ------------------------------------------------------------------------

    if status == "PROPOSE":

        if len(preview_values) != SEMANTIC_PREVIEW_COUNT:

            raise ValueError(
                "SEMANTIC PROPOSE response must contain exactly "
                f"{SEMANTIC_PREVIEW_COUNT} preview values; "
                f"got {len(preview_values)}."
            )

        if any(not isinstance(value, str) for value in preview_values):

            raise ValueError("SEMANTIC preview values must all be strings.")

        return {
            "status": "PROPOSE",
            "message": message.strip(),
            "preview_values": preview_values,
        }

    # ------------------------------------------------------------------------
    # CLARIFY / UNSUPPORTED
    # ------------------------------------------------------------------------

    if preview_values:

        raise ValueError(f"SEMANTIC {status} response must not contain preview values.")

    return {
        "status": status,
        "message": message.strip(),
        "preview_values": [],
    }


def generate_semantic_preview(
    description: str,
) -> dict[str, Any]:
    """
    Interpret a semantic STRING requirement and return a validated preview.

    No FORGE model is created or modified by this function.
    """

    if not isinstance(description, str):

        raise ValueError("SEMANTIC description must be a string.")

    if not description.strip():

        raise ValueError("SEMANTIC description must not be empty.")

    raw_response = call_semantic_llm(
        description.strip(),
    )

    return parse_semantic_response(
        raw_response,
    )


# ============================================================================
# LLM RESPONSE PARSING
# ============================================================================


def parse_llm_response(raw_response: str) -> dict[str, Any]:
    """
    Parse and validate the structured response returned by the LLM.

    The LLM is allowed to return JSON only. Minor transport formatting
    such as markdown code fences is tolerated, but missing or invalid
    protocol fields are treated as an authoring failure.

    PROPOSE with zero operations is valid. It means the current model
    already satisfies the user's latest requirement and no model change
    is necessary.
    """

    text = raw_response.strip()

    # ------------------------------------------------------------------------
    # Tolerate accidental markdown fences
    # ------------------------------------------------------------------------

    if text.startswith("```"):

        lines = text.splitlines()

        if lines and lines[0].startswith("```"):
            lines = lines[1:]

        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]

        text = "\n".join(lines).strip()

    # ------------------------------------------------------------------------
    # Parse JSON
    # ------------------------------------------------------------------------

    try:

        response = json.loads(text)

    except json.JSONDecodeError as exc:

        raise ValueError(
            "LLM response was not valid JSON.\n" f"Raw response:\n{text}"
        ) from exc

    # ------------------------------------------------------------------------
    # Response must be an object
    # ------------------------------------------------------------------------

    if not isinstance(response, dict):

        raise ValueError(
            "LLM response must be a JSON object.\n" f"Raw response:\n{text}"
        )

    # ------------------------------------------------------------------------
    # Validate status
    # ------------------------------------------------------------------------

    status = response.get("status")

    if status not in {
        "PROPOSE",
        "CLARIFY",
        "UNSUPPORTED",
    }:

        raise ValueError(
            "Invalid LLM response status.\n"
            "Expected one of: PROPOSE, CLARIFY, UNSUPPORTED\n"
            f"Received: {status!r}\n"
            f"Raw response:\n{text}"
        )

    # ------------------------------------------------------------------------
    # Validate message
    # ------------------------------------------------------------------------

    message = response.get("message")

    if not isinstance(message, str) or not message.strip():

        raise ValueError(
            "LLM response must contain a non-empty 'message'.\n"
            f"Raw response:\n{text}"
        )

    # ------------------------------------------------------------------------
    # Validate operations
    # ------------------------------------------------------------------------

    operations = response.get(
        "operations",
        [],
    )

    if not isinstance(operations, list):

        raise ValueError(
            "LLM response field 'operations' must be a JSON array.\n"
            f"Raw response:\n{text}"
        )

    # ------------------------------------------------------------------------
    # PROPOSE may contain zero or more operations.
    #
    # Zero operations means:
    #
    #   "The requirement is already satisfied."
    #
    # This is intentionally valid.
    # ------------------------------------------------------------------------

    if status == "PROPOSE":

        for index, operation in enumerate(
            operations,
            start=1,
        ):

            if not isinstance(operation, dict):

                raise ValueError(
                    "Each PROPOSE operation must be a JSON object.\n"
                    f"Invalid operation at index {index}:\n"
                    f"{operation!r}\n"
                    f"Raw response:\n{text}"
                )

    # ------------------------------------------------------------------------
    # CLARIFY and UNSUPPORTED must not contain operations
    # ------------------------------------------------------------------------

    if status != "PROPOSE" and operations:

        raise ValueError(
            f"LLM returned {status} but also supplied operations.\n"
            f"Raw response:\n{text}"
        )

    # ------------------------------------------------------------------------
    # Return normalized response
    # ------------------------------------------------------------------------

    return {
        "status": status,
        "message": message.strip(),
        "operations": operations,
    }


# ============================================================================
# SAFE AUTHORING TRANSACTION
# ============================================================================


def apply_llm_response(
    model: dict[str, Any],
    llm_response: dict[str, Any],
) -> tuple[
    dict[str, Any],
    list[str],
]:

    status = llm_response["status"]

    if status != "PROPOSE":
        return (
            model,
            [],
        )

    candidate = copy.deepcopy(model)

    all_errors: list[str] = []

    for operation in llm_response["operations"]:

        operation_errors = validate_operation(
            candidate,
            operation,
        )

        if operation_errors:
            all_errors.extend(operation_errors)
            continue

        apply_operation(
            candidate,
            operation,
        )

    if all_errors:
        return (
            model,
            all_errors,
        )

    authoring_errors = validate_authoring_model(candidate)

    if authoring_errors:
        return (
            model,
            authoring_errors,
        )

    return (
        candidate,
        [],
    )


# ============================================================================
# MODEL TO FINAL SPECIFICATION
# ============================================================================


def model_to_specification(
    model: dict[str, Any],
) -> dict[str, Any]:

    specification = copy.deepcopy(model)

    return specification


# ============================================================================
# AUTHORING SUMMARY
# ============================================================================


def model_summary(
    model: dict[str, Any],
) -> dict[str, Any]:

    return {
        "entities": [
            {
                "name": entity["name"],
                "population": entity.get("population"),
                "fields": [
                    field["name"]
                    for field in entity.get(
                        "fields",
                        [],
                    )
                ],
            }
            for entity in model.get(
                "entities",
                [],
            )
        ],
        "relationship_count": len(
            model.get(
                "relationships",
                [],
            )
        ),
        "constraint_count": len(
            model.get(
                "constraints",
                [],
            )
        ),
        "dependency_count": len(
            model.get(
                "dependencies",
                [],
            )
        ),
    }


# ============================================================================
# TEST REQUIREMENTS
# ============================================================================

AUTHORING_REQUIREMENTS = [
    "Create an SAP customer master table named KNA1 with 100 records.",
    (
        "KNA1 should contain the fields KUNNR, LAND1, NAME1 and KTOKD. "
        "KUNNR is the customer identifier, LAND1 is the country, "
        "NAME1 is the customer name, and KTOKD is the customer account group."
    ),
    "Create an SAP sales order header table named VBAK with 200 records.",
    (
        "VBAK should contain the fields VBELN, KUNNR, AUART and NETWR. "
        "VBELN is the sales document identifier, KUNNR references the "
        "customer in KNA1, AUART is the sales document type, and NETWR "
        "is the net order value."
    ),
    "Each VBAK record belongs to exactly one customer in KNA1.",
    "The VBAK net order value must be greater than or equal to zero.",
    "Create an SAP sales order item table named VBAP with 500 records.",
    (
        "VBAP should contain the fields VBELN, POSNR, MATNR, KWMENG "
        "and NETWR. VBELN references the sales order in VBAK, POSNR "
        "is the item number, MATNR is the material reference, KWMENG "
        "is the order quantity, and NETWR is the item net value."
    ),
    "Each VBAP item belongs to exactly one VBAK sales order.",
    "Each VBAK sales order can contain multiple VBAP items.",
    "The VBAP item net value must be greater than or equal to zero.",
    "Total item value should be derived from the item quantity and unit value.",
]


# ============================================================================
# ADVERSARIAL REQUIREMENTS
# ============================================================================

ADVERSARIAL_REQUIREMENTS = [
    "Make the credit limit realistic.",
    "Use a distribution called MAGIC_DISTRIBUTION.",
]


# ============================================================================
# MAIN EXPERIMENT
# ============================================================================


def main() -> int:

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    print()
    print("=" * 76)
    print("FORGE - Experiment 022: " "LLM-Assisted Progressive Specification Authoring")
    print("=" * 76)

    print()
    print("LLM configuration:")
    print(f"  Provider:       Ollama")
    print(f"  Endpoint:       {OLLAMA_URL}")
    print(f"  Model:          {MODEL}")

    print()
    print("Architecture:")
    print("  Natural-language requirement")
    print("           ↓")
    print("  Real LLM authoring assistant")
    print("           ↓")
    print("  Structured FORGE operation")
    print("           ↓")
    print("  Operation validation")
    print("           ↓")
    print("  Candidate model")
    print("           ↓")
    print("  Authoring-state validation")
    print("           ↓")
    print("  Accepted model")
    print("           ↓")
    print("  Final FORGE specification")

    system_prompt = build_system_prompt()

    model = create_empty_model()

    trace: list[dict[str, Any]] = []

    print()
    print("Progressive authoring session:")
    print("-" * 76)

    for index, requirement in enumerate(
        AUTHORING_REQUIREMENTS,
        start=1,
    ):

        print()
        print(f"[{index:02d}] USER:")
        print(f"     {requirement}")

        try:

            raw_response = call_ollama(
                system_prompt,
                requirement,
                model,
            )

            llm_response = parse_llm_response(raw_response)

        except Exception as exc:

            print()
            print("LLM invocation:                  FAIL")
            print(f"  ERROR: {exc}")

            results = {
                "experiment": ("022_llm_assisted_" "specification_authoring"),
                "model": MODEL,
                "overall": "FAIL",
                "failure": str(exc),
                "trace": trace,
            }

            RESULTS_OUTPUT.write_text(
                json.dumps(
                    results,
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
            )

            return 1

        status = llm_response["status"]

        print()
        print(f"     LLM status: {status}")

        if llm_response.get("message"):
            print(f"     LLM message: " f"{llm_response['message']}")

        operations = llm_response.get(
            "operations",
            [],
        )

        if status == "PROPOSE":

            print()
            print("     Proposed operations:")

            for operation in operations:
                print(
                    "       "
                    + json.dumps(
                        operation,
                        separators=(
                            ", ",
                            ": ",
                        ),
                    )
                )

            previous_model = copy.deepcopy(model)

            model, errors = apply_llm_response(
                model,
                llm_response,
            )

            operation_valid = not errors

            print()
            print(
                "     Operation validation:       "
                f"{'PASS' if operation_valid else 'FAIL'}"
            )

            if errors:

                for error in errors:
                    print(f"       ERROR: {error}")

                trace.append(
                    {
                        "step": index,
                        "user_requirement": requirement,
                        "llm_response": llm_response,
                        "accepted": False,
                        "errors": errors,
                        "model_before": previous_model,
                        "model_after": previous_model,
                    }
                )

                continue

            print("     Model update:                PASS")

            print("     Current model:")

            summary = model_summary(model)

            print(
                json.dumps(
                    summary,
                    indent=2,
                )
            )

            trace.append(
                {
                    "step": index,
                    "user_requirement": requirement,
                    "llm_response": llm_response,
                    "accepted": True,
                    "errors": [],
                    "model_before": previous_model,
                    "model_after": copy.deepcopy(model),
                }
            )

        else:

            print("     No model change.")

            trace.append(
                {
                    "step": index,
                    "user_requirement": requirement,
                    "llm_response": llm_response,
                    "accepted": False,
                    "errors": [],
                    "model_before": copy.deepcopy(model),
                    "model_after": copy.deepcopy(model),
                }
            )

    # ------------------------------------------------------------------------
    # FINALIZATION
    # ------------------------------------------------------------------------

    print()
    print("=" * 76)
    print("Finalization")
    print("=" * 76)

    final_specification = model_to_specification(model)

    final_errors = validate_specification(final_specification)

    final_valid = not final_errors

    print()
    print("Final specification validation: " f"{'PASS' if final_valid else 'FAIL'}")

    if final_errors:

        for error in final_errors:
            print(f"  ERROR: {error}")

    else:

        SPECIFICATION_OUTPUT.write_text(
            json.dumps(
                final_specification,
                indent=2,
                ensure_ascii=False,
            )
            + "\n",
            encoding="utf-8",
        )

        print("Canonical specification:         PASS")

        print(f"  Written to: {SPECIFICATION_OUTPUT}")

    # ------------------------------------------------------------------------
    # ADVERSARIAL TESTS
    # ------------------------------------------------------------------------

    print()
    print("=" * 76)
    print("Adversarial authoring tests")
    print("=" * 76)

    adversarial_results = []

    for requirement in ADVERSARIAL_REQUIREMENTS:

        print()
        print(f"USER:")
        print(f"  {requirement}")

        try:

            raw_response = call_ollama(
                system_prompt,
                requirement,
                model,
            )

            response = parse_llm_response(raw_response)

            proposed_operations = response.get(
                "operations",
                [],
            )

            invalid_operations = []

            for operation in proposed_operations:

                errors = validate_operation(
                    model,
                    operation,
                )

                if errors:
                    invalid_operations.append(
                        {
                            "operation": operation,
                            "errors": errors,
                        }
                    )

            safe = (
                response["status"]
                in {
                    "CLARIFY",
                    "UNSUPPORTED",
                }
                or not invalid_operations
            )

            print(f"  LLM response status: " f"{response['status']}")

            print("  Safety handling:                 " f"{'PASS' if safe else 'FAIL'}")

            adversarial_results.append(
                {
                    "requirement": requirement,
                    "response": response,
                    "safe": safe,
                    "invalid_operations": invalid_operations,
                }
            )

        except Exception as exc:

            print(f"  Adversarial test:                FAIL")
            print(f"    ERROR: {exc}")

            adversarial_results.append(
                {
                    "requirement": requirement,
                    "safe": False,
                    "error": str(exc),
                }
            )

    # ------------------------------------------------------------------------
    # RESULTS
    # ------------------------------------------------------------------------

    accepted_steps = sum(1 for entry in trace if entry["accepted"])

    adversarial_passed = sum(1 for result in adversarial_results if result.get("safe"))

    adversarial_total = len(adversarial_results)

    overall = (
        final_valid and accepted_steps > 0 and adversarial_passed == adversarial_total
    )

    results = {
        "experiment": ("022_llm_assisted_" "specification_authoring"),
        "stage": "022",
        "llm": {
            "provider": "Ollama",
            "endpoint": OLLAMA_URL,
            "model": MODEL,
        },
        "authoring_requirements": len(AUTHORING_REQUIREMENTS),
        "accepted_authoring_steps": accepted_steps,
        "final_specification_valid": final_valid,
        "adversarial_tests_passed": adversarial_passed,
        "adversarial_tests_total": adversarial_total,
        "overall": ("PASS" if overall else "FAIL"),
    }

    RESULTS_OUTPUT.write_text(
        json.dumps(
            results,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    TRACE_OUTPUT.write_text(
        json.dumps(
            trace,
            indent=2,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )

    print()
    print("=" * 76)
    print("Experiment result")
    print("=" * 76)

    print(
        f"  LLM authoring:                  "
        f"{'PASS' if accepted_steps > 0 else 'FAIL'}"
    )

    print(
        f"  Progressive refinement:         "
        f"{'PASS' if accepted_steps > 1 else 'FAIL'}"
    )

    print(
        f"  Operation safety:               "
        f"{'PASS' if accepted_steps > 0 else 'FAIL'}"
    )

    print(f"  Final FORGE specification:      " f"{'PASS' if final_valid else 'FAIL'}")

    print(
        f"  Adversarial handling:           "
        f"{'PASS' if adversarial_passed == adversarial_total else 'FAIL'}"
    )

    print(
        f"  Authoring steps accepted:       "
        f"{accepted_steps}/{len(AUTHORING_REQUIREMENTS)}"
    )

    print(
        f"  Adversarial tests:              "
        f"{adversarial_passed}/{adversarial_total}"
    )

    print()
    print("Overall: " f"{'PASS' if overall else 'FAIL'}")

    print()
    print("Outputs:")
    print(f"  {SPECIFICATION_OUTPUT}")
    print(f"  {RESULTS_OUTPUT}")
    print(f"  {TRACE_OUTPUT}")

    return 0 if overall else 1


if __name__ == "__main__":
    sys.exit(main())
