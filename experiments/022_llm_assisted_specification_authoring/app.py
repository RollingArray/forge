"""
FORGE - Experiment 022
Interactive LLM-Assisted Specification Authoring
=================================================

The LLM proposes.
FORGE validates.
The user decides.

This Streamlit application is the interactive UI layer over the
existing Experiment 022 FORGE authoring backend.

The accepted FORGE model is the source of truth.

The LLM never directly modifies the accepted model.
Manual edits also pass through FORGE validation before
they are committed.

Run:

    cd /Users/e10936535/forge

    uv run streamlit run \
        experiments/022_llm_assisted_specification_authoring/app.py
"""

from __future__ import annotations

import copy
import importlib.util
import json
import sys
from pathlib import Path
from typing import Any
import random

import streamlit as st

# ============================================================================
# PATHS
# ============================================================================

APP_DIR = Path(__file__).resolve().parent
EXPERIMENT_PATH = APP_DIR / "experiment.py"
SPECIFICATION_PATH = APP_DIR / "output" / "specification.json"

# ============================================================================
# LOAD FORGE BACKEND
# ============================================================================

spec = importlib.util.spec_from_file_location(
    "forge_experiment_022",
    EXPERIMENT_PATH,
)

if spec is None or spec.loader is None:
    raise RuntimeError(f"Unable to load FORGE backend from {EXPERIMENT_PATH}")

forge_backend = importlib.util.module_from_spec(spec)

sys.modules["forge_experiment_022"] = forge_backend

spec.loader.exec_module(forge_backend)


# ============================================================================
# PAGE
# ============================================================================

st.set_page_config(
    page_title="FORGE Specification Authoring",
    page_icon="⚒️",
    layout="wide",
)


# ============================================================================
# CONSTANTS
# ============================================================================

SUPPORTED_FIELD_TYPES = sorted(forge_backend.SUPPORTED_FIELD_TYPES)

SUPPORTED_DISTRIBUTIONS = sorted(forge_backend.SUPPORTED_DISTRIBUTIONS)

SUPPORTED_STRING_GENERATORS = sorted(forge_backend.SUPPORTED_STRING_GENERATORS)

SUPPORTED_STRING_CHARACTER_SETS = sorted(forge_backend.SUPPORTED_STRING_CHARACTER_SETS)

SUPPORTED_GENERATION_STRATEGIES = sorted(forge_backend.SUPPORTED_GENERATION_STRATEGIES)

# Field-type-specific distribution restrictions.
# Types not listed here retain the full FORGE distribution vocabulary.
DISTRIBUTIONS_BY_FIELD_TYPE = {
    "INTEGER": [
        "UNIFORM",
        "DISCRETE_UNIFORM",
        "CATEGORICAL",
    ],
    "DECIMAL": [
        "UNIFORM",
        "NORMAL",
    ],
    "STRING": [
        "CATEGORICAL",
    ],
}

SUPPORTED_GENERATION_STRATEGIES = sorted(forge_backend.SUPPORTED_GENERATION_STRATEGIES)

SUPPORTED_IDENTITY_STRATEGIES = sorted(forge_backend.SUPPORTED_IDENTITY_STRATEGIES)

SUPPORTED_RELATIONSHIP_TYPES = [
    "ONE_TO_ONE",
    "ONE_TO_MANY",
    "MANY_TO_ONE",
    "MANY_TO_MANY",
]

SUPPORTED_OPERATORS = sorted(forge_backend.SUPPORTED_OPERATORS)


def preview_pattern(pattern: str) -> str:
    """Render one deterministic illustrative value from a FORGE PATTERN."""

    rng = random.Random(f"FORGE_PATTERN_PREVIEW:{pattern}")

    uppercase = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    lowercase = "abcdefghijklmnopqrstuvwxyz"
    digits = "0123456789"
    alphanumeric = uppercase + lowercase + digits

    result = []

    for character in pattern:

        if character == "#":
            result.append(rng.choice(digits))

        elif character == "A":
            result.append(rng.choice(uppercase))

        elif character == "a":
            result.append(rng.choice(lowercase))

        elif character == "X":
            result.append(rng.choice(alphanumeric))

        else:
            result.append(character)

    return "".join(result)


def integer_distribution_requires_range(distribution: str) -> bool:
    return distribution in {
        "UNIFORM",
        "DISCRETE_UNIFORM",
    }


def integer_distribution_requires_values(distribution: str) -> bool:
    return distribution == "CATEGORICAL"


# ============================================================================
# SESSION STATE
# ============================================================================


def load_initial_model() -> dict[str, Any]:
    if not SPECIFICATION_PATH.exists():
        return forge_backend.create_empty_model()

    try:
        with SPECIFICATION_PATH.open("r", encoding="utf-8") as handle:
            specification = json.load(handle)

        errors = forge_backend.validate_specification(specification)

        if errors:
            raise ValueError(
                "Saved specification is invalid:\n"
                + "\n".join(f"- {error}" for error in errors)
            )

        return copy.deepcopy(specification)

    except Exception as exc:
        st.error(
            f"Unable to load saved FORGE specification "
            f"from `{SPECIFICATION_PATH}`: {exc}"
        )
        st.stop()


def save_specification(model: dict[str, Any]) -> None:
    """
    Persist the accepted FORGE model as the canonical specification.
    The model must already have passed FORGE validation before this is called.
    """
    specification = forge_backend.model_to_specification(model)

    SPECIFICATION_PATH.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with SPECIFICATION_PATH.open("w", encoding="utf-8") as handle:
        json.dump(
            specification,
            handle,
            indent=2,
            ensure_ascii=False,
        )
        handle.write("\n")


def initialise_state() -> None:

    defaults = {
        "model": load_initial_model(),
        "conversation": [],
        "pending_proposal": None,
        "pending_candidate": None,
        "pending_errors": [],
        "last_raw_response": "",
        "semantic_preview": None,
        "semantic_preview_error": [],
        "semantic_preview_description": "",
        "semantic_preview_field": None,
        "manual_error": [],
        "manual_success": None,
        "editing_field": None,
        "adding_field": None,
        "editing_population": None,
        "editing_relationship": None,
        "adding_relationship": False,
        "editing_relationship": None,
        "adding_relationship": False,
        "editing_foreign_key": None,
        "adding_foreign_key": False,
        "editing_constraint": None,
        "adding_entity": False,
        "adding_constraint": False,
    }

    for key, value in defaults.items():

        if key not in st.session_state:

            st.session_state[key] = copy.deepcopy(value)


initialise_state()


# ============================================================================
# MODEL HELPERS
# ============================================================================


def get_entity(
    model: dict[str, Any],
    entity_name: str,
) -> dict[str, Any] | None:

    for entity in model.get("entities", []):

        if entity.get("name") == entity_name:

            return entity

    return None


def get_field(
    model: dict[str, Any],
    reference: str,
) -> dict[str, Any] | None:

    if "." not in reference:

        return None

    entity_name, field_name = reference.split(".", 1)

    entity = get_entity(
        model,
        entity_name,
    )

    if entity is None:

        return None

    for field in entity.get("fields", []):

        if field.get("name") == field_name:

            return field

    return None


def entity_names(
    model: dict[str, Any],
) -> list[str]:

    return [entity["name"] for entity in model.get("entities", [])]


def field_references(
    model: dict[str, Any],
) -> list[str]:

    result = []

    for entity in model.get("entities", []):

        for field in entity.get("fields", []):

            result.append(f"{entity['name']}.{field['name']}")

    return result


# ============================================================================
# VALIDATION
# ============================================================================


def authoring_errors(
    model: dict[str, Any],
) -> list[str]:

    return forge_backend.validate_authoring_model(model)


def specification_errors(
    model: dict[str, Any],
) -> list[str]:

    specification = forge_backend.model_to_specification(model)

    return forge_backend.validate_specification(specification)


def generation_errors(
    model: dict[str, Any],
) -> list[str]:

    errors = specification_errors(model)

    return [error for error in errors if "requires generation configuration" in error]


# ============================================================================
# OPERATION HANDLING
# ============================================================================


def build_candidate(
    model: dict[str, Any],
    operations: list[dict[str, Any]],
) -> tuple[
    dict[str, Any] | None,
    list[str],
]:

    candidate = copy.deepcopy(model)

    errors: list[str] = []

    for operation in operations:

        validation_errors = forge_backend.validate_operation(
            candidate,
            operation,
        )

        if validation_errors:

            errors.extend(validation_errors)

            continue

        try:

            forge_backend.apply_operation(
                candidate,
                operation,
            )

        except Exception as exc:

            errors.append(f"Operation application failed: {exc}")

    if errors:

        return None, errors

    structural_errors = forge_backend.validate_authoring_model(candidate)

    if structural_errors:

        return None, structural_errors

    return candidate, []


def commit_manual_candidate(
    candidate: dict[str, Any],
    success_message: str,
) -> None:

    errors = forge_backend.validate_authoring_model(candidate)

    if errors:

        st.session_state.manual_error = errors
        st.session_state.manual_success = None

        return

    st.session_state.model = copy.deepcopy(candidate)

    try:
        save_specification(st.session_state.model)
    except Exception as exc:
        st.session_state.manual_error = [
            f"Model was updated in memory, but saving the specification failed: {exc}"
        ]
        st.session_state.manual_success = None
        return

    st.session_state.manual_error = []
    st.session_state.manual_success = success_message
    st.rerun()


# ============================================================================
# OPERATION SUMMARY
# ============================================================================


def operation_summary(
    operation: dict[str, Any],
) -> str:

    operation_type = operation.get("operation")

    if operation_type == "ADD_ENTITY":

        entity = operation.get(
            "entity",
            {},
        )

        name = entity.get(
            "name",
            "?",
        )

        population = entity.get(
            "population",
            {},
        ).get("count")

        if population is not None:

            return f"Add entity **{name}** " f"with population **{population:,}**."

        return f"Add entity **{name}**."

    if operation_type == "ADD_FIELD":

        entity = operation.get(
            "entity",
            "?",
        )

        field = operation.get(
            "field",
            {},
        )

        return (
            f"Add field "
            f"**{entity}.{field.get('name', '?')}** "
            f"of type **{field.get('type', '?')}**."
        )

    if operation_type == "UPDATE_FIELD":

        field_reference = operation.get(
            "field",
            "?",
        )

        updates = operation.get(
            "updates",
            {},
        )

        updates_json = json.dumps(
            updates,
            ensure_ascii=False,
        )

        return f"Update **{field_reference}**: " f"`{updates_json}`"

    if operation_type == "UPDATE_POPULATION":

        return (
            f"Set **{operation.get('entity', '?')}** "
            f"population to **{operation.get('count', '?')}**."
        )

    if operation_type == "ADD_CONSTRAINT":

        constraint = operation.get(
            "constraint",
            {},
        )

        return (
            f"Add constraint **"
            f"{constraint.get('entity', '?')}."
            f"{constraint.get('field', '?')} "
            f"{constraint.get('operator', '?')} "
            f"{constraint.get('value', '?')}**."
        )

    if operation_type == "ADD_DEPENDENCY":

        dependency = operation.get(
            "dependency",
            {},
        )

        return (
            f"Add **{dependency.get('type', '?')}** "
            f"dependency for "
            f"**{dependency.get('target', '?')}** "
            f"from "
            f"**{', '.join(dependency.get('source_fields', []))}**."
        )

    if operation_type == "ADD_RELATIONSHIP":

        relationship = operation.get(
            "relationship",
            {},
        )

        return (
            f"Add **{relationship.get('type', '?')}** "
            f"relationship "
            f"**{relationship.get('source', '?')}** → "
            f"**{relationship.get('target', '?')}**."
        )

    return f"Operation `{operation_type}`."


# ============================================================================
# HEADER
# ============================================================================

header_left, header_right = st.columns([0.8, 0.2])

with header_left:

    st.title("⚒️ FORGE")

    st.caption("Interactive Synthetic Data Specification Authoring")

with header_right:

    st.write("")

    if st.button(
        "New Session",
        use_container_width=True,
    ):

        for key in list(st.session_state.keys()):

            del st.session_state[key]

        initialise_state()

        st.rerun()


st.info(
    "**FORGE principle:** " "The LLM proposes. FORGE validates. " "The user decides."
)


# ============================================================================
# METRICS
# ============================================================================

model = st.session_state.model

entities = model.get("entities", [])

field_count = sum(len(entity.get("fields", [])) for entity in entities)

relationships = model.get("relationships", [])

constraints = model.get("constraints", [])

dependencies = model.get("dependencies", [])

metrics = st.columns(5)

metrics[0].metric(
    "Entities",
    len(entities),
)

metrics[1].metric(
    "Fields",
    field_count,
)

metrics[2].metric(
    "Relationships",
    len(relationships),
)

metrics[3].metric(
    "Constraints",
    len(constraints),
)

metrics[4].metric(
    "Dependencies",
    len(dependencies),
)


# ============================================================================
# MAIN LAYOUT
# ============================================================================

conversation_column, model_column = st.columns(
    [0.9, 1.4],
    gap="large",
)


# ============================================================================
# LEFT: CONVERSATION
# ============================================================================

with conversation_column:

    st.subheader("💬 Authoring conversation")

    if not st.session_state.conversation:

        st.caption("Start by describing the data model " "you want FORGE to build.")

    for message in st.session_state.conversation:

        role = message.get("role")

        content = message.get(
            "content",
            "",
        )

        if role == "user":

            with st.chat_message("user"):

                st.write(content)

        elif role == "assistant":

            with st.chat_message("assistant"):

                st.write(content)

        elif role == "error":

            st.error(content)

        elif role == "system":

            st.caption(content)

    # ------------------------------------------------------------------------
    # PROPOSAL
    # ------------------------------------------------------------------------

    proposal = st.session_state.pending_proposal

    candidate = st.session_state.pending_candidate

    if proposal is not None:

        st.divider()

        st.subheader("🤖 Proposed changes")

        message = proposal.get(
            "message",
            "",
        )

        if message:

            st.write(message)

        operations = proposal.get(
            "operations",
            [],
        )

        if not operations:

            st.info("No model change is required.")

        else:

            for operation in operations:

                st.markdown("• " + operation_summary(operation))

        if candidate is not None:

            candidate_errors = authoring_errors(candidate)

            if candidate_errors:

                st.error("FORGE rejected this candidate.")

                for error in candidate_errors:

                    st.write(f"• {error}")

            else:

                st.success("FORGE validated the proposed model change.")

                candidate_generation_errors = generation_errors(candidate)

                if candidate_generation_errors:

                    st.warning(
                        f"{len(candidate_generation_errors)} "
                        "generation configuration issue(s) "
                        "remain."
                    )

        accept, reject = st.columns(2)

        with accept:

            if st.button(
                "✓ Accept",
                type="primary",
                use_container_width=True,
                disabled=candidate is None,
            ):

                accepted_model = copy.deepcopy(candidate)

                try:
                    save_specification(accepted_model)
                except Exception as exc:
                    st.session_state.manual_error = [
                        f"Changes were validated but could not be saved: {exc}"
                    ]
                    st.session_state.manual_success = None
                else:
                    st.session_state.model = accepted_model
                    st.session_state.pending_proposal = None
                    st.session_state.pending_candidate = None
                    st.session_state.pending_errors = []

                    st.session_state.conversation.append(
                        {
                            "role": "system",
                            "content": "Changes accepted and saved.",
                        }
                    )

                    st.rerun()

                st.session_state.pending_candidate = None

                st.session_state.pending_errors = []

                st.session_state.conversation.append(
                    {
                        "role": "system",
                        "content": "Changes accepted.",
                    }
                )

                st.rerun()

        with reject:

            if st.button(
                "✕ Reject",
                use_container_width=True,
            ):

                st.session_state.pending_proposal = None

                st.session_state.pending_candidate = None

                st.session_state.pending_errors = []

                st.session_state.conversation.append(
                    {
                        "role": "system",
                        "content": "Proposed changes rejected.",
                    }
                )

                st.rerun()

    # ------------------------------------------------------------------------
    # MANUAL ERRORS
    # ------------------------------------------------------------------------

    if st.session_state.manual_error:

        st.error("Manual change rejected by FORGE.")

        for error in st.session_state.manual_error:

            st.write(f"• {error}")

    if st.session_state.manual_success:

        st.success(st.session_state.manual_success)

        st.session_state.manual_success = None


# ============================================================================
# RIGHT: MODEL
# ============================================================================

with model_column:

    st.subheader("⚒️ FORGE model")

    current_model = st.session_state.model

    current_entities = current_model.get("entities", [])

    if not current_entities:
        st.info(
            "No entities yet. "
            "Create one manually or describe the first entity in the conversation."
        )

    # ========================================================================
    # MANUAL ENTITY CREATION
    # ========================================================================

    add_entity_left, add_entity_right = st.columns([0.75, 0.25])

    with add_entity_left:
        st.markdown("**Entities**")

    with add_entity_right:
        if st.button(
            "+ Add Entity",
            key="add_entity",
            use_container_width=True,
        ):
            st.session_state.adding_entity = True
            st.session_state.manual_error = []
            st.rerun()

    if st.session_state.adding_entity:
        with st.form(key="add_entity_form"):
            entity_name = st.text_input(
                "Entity name",
                placeholder="e.g. CUSTOMER",
            )

            entity_population = st.number_input(
                "Population",
                min_value=0,
                value=100,
                step=1,
            )

            save, cancel = st.columns(2)

            with save:
                create_entity = st.form_submit_button(
                    "Create Entity",
                    type="primary",
                    use_container_width=True,
                )

            with cancel:
                cancel_entity = st.form_submit_button(
                    "Cancel",
                    use_container_width=True,
                )

        if cancel_entity:
            st.session_state.adding_entity = False
            st.session_state.manual_error = []
            st.rerun()

        if create_entity:
            operation = {
                "operation": "ADD_ENTITY",
                "entity": {
                    "name": entity_name.strip(),
                    "population": {
                        "count": int(entity_population),
                    },
                    "fields": [],
                },
            }

            candidate, errors = build_candidate(
                current_model,
                [operation],
            )

            if errors:
                st.session_state.manual_error = errors
                st.session_state.manual_success = None
            else:
                st.session_state.model = candidate
                st.session_state.adding_entity = False
                st.session_state.manual_error = []
                st.session_state.manual_success = (
                    f"Created entity **{entity_name.strip()}** "
                    f"with population **{int(entity_population):,}**."
                )

            st.rerun()

    # ========================================================================
    # ENTITY CARDS
    # ========================================================================

    for entity in current_entities:

        entity_name = entity["name"]

        population = entity.get(
            "population",
            {},
        ).get("count")

        fields = entity.get("fields", [])

        with st.container(border=True):

            top_left, top_right = st.columns([0.75, 0.25])

            with top_left:

                st.markdown(f"### {entity_name}")

                if population is not None:

                    st.caption(f"{population:,} records • " f"{len(fields)} fields")

                else:

                    st.caption(f"{len(fields)} fields")

            with top_right:

                if st.button(
                    "Population",
                    key=f"population_{entity_name}",
                    use_container_width=True,
                ):

                    st.session_state.editing_population = entity_name

                    st.rerun()

            # ----------------------------------------------------------------
            # POPULATION EDITOR
            # ----------------------------------------------------------------

            if st.session_state.editing_population == entity_name:

                with st.form(key=f"population_form_{entity_name}"):

                    current_population = population if population is not None else 0

                    new_population = st.number_input(
                        "Population",
                        min_value=0,
                        value=int(current_population),
                        step=1,
                    )

                    save, cancel = st.columns(2)

                    with save:

                        save_population = st.form_submit_button(
                            "Save",
                            type="primary",
                            use_container_width=True,
                        )

                    with cancel:

                        cancel_population = st.form_submit_button(
                            "Cancel",
                            use_container_width=True,
                        )

                if cancel_population:

                    st.session_state.editing_population = None

                    st.rerun()

                if save_population:

                    operation = {
                        "operation": "UPDATE_POPULATION",
                        "entity": entity_name,
                        "count": int(new_population),
                    }

                    candidate, errors = build_candidate(
                        current_model,
                        [operation],
                    )

                    if errors:

                        st.session_state.manual_error = errors

                    else:
                        try:
                            save_specification(candidate)
                        except Exception as exc:
                            st.session_state.manual_error = [
                                f"Population was validated but could not be saved: {exc}"
                            ]
                        else:
                            st.session_state.model = candidate
                            st.session_state.editing_population = None
                            st.session_state.manual_success = (
                                f"Population for **{entity_name}** updated and saved."
                            )

                    st.rerun()

            # ----------------------------------------------------------------
            # ENTITY IDENTITY
            # ----------------------------------------------------------------

            identity = entity.get(
                "identity",
                {},
            )

            identity_fields = (
                identity.get(
                    "fields",
                    [],
                )
                if isinstance(identity, dict)
                else []
            )

            has_identity = bool(identity_fields)

            st.markdown("**Primary Key / Identity**")

            available_identity_fields = [
                field.get("name")
                for field in fields
                if isinstance(field, dict)
                and isinstance(field.get("name"), str)
                and field.get("name")
            ]

            identity_editor_key = f"editing_identity_{entity_name}"

            identity_editor_version_key = f"identity_editor_version_{entity_name}"

            identity_editor_version = st.session_state.get(
                identity_editor_version_key,
                0,
            )

            editing_identity = st.session_state.get(
                identity_editor_key,
                False,
            )

            # ------------------------------------------------------------
            # VIEW MODE
            # ------------------------------------------------------------

            if has_identity and not editing_identity:

                if len(identity_fields) == 1:

                    st.markdown(f"Primary key: **{identity_fields[0]}**")

                else:

                    st.markdown(
                        "Composite primary key: "
                        + " + ".join(
                            f"**{field_name}**" for field_name in identity_fields
                        )
                    )

                if st.button(
                    "Edit Identity",
                    key=f"edit_identity_{entity_name}",
                    use_container_width=True,
                ):

                    st.session_state[identity_editor_key] = True

                    st.rerun()

            # ------------------------------------------------------------
            # NO IDENTITY
            # ------------------------------------------------------------

            elif not has_identity and not editing_identity:

                st.caption("No primary key / identity defined.")

                if st.button(
                    "Set Identity",
                    key=f"set_identity_{entity_name}",
                    type="primary",
                    use_container_width=True,
                ):

                    st.session_state[identity_editor_key] = True

                    st.rerun()

            # ------------------------------------------------------------
            # EDIT MODE
            # ------------------------------------------------------------

            if editing_identity:

                selected_identity_fields = st.multiselect(
                    "Identity fields",
                    options=available_identity_fields,
                    default=[
                        field_name
                        for field_name in identity_fields
                        if field_name in available_identity_fields
                    ],
                    key=(
                        f"identity_fields_{entity_name}_" f"{identity_editor_version}"
                    ),
                    help=(
                        "Select one field for a single-field primary key, "
                        "or multiple fields for a composite primary key."
                    ),
                )

                identity_save_left, identity_save_middle, identity_save_right = (
                    st.columns(3)
                )

                with identity_save_left:

                    save_identity = st.button(
                        "Save Identity",
                        key=f"save_identity_{entity_name}",
                        type="primary",
                        use_container_width=True,
                    )

                with identity_save_middle:

                    clear_identity = st.button(
                        "Clear Identity",
                        key=f"clear_identity_{entity_name}",
                        use_container_width=True,
                    )

                with identity_save_right:

                    cancel_identity = st.button(
                        "Cancel",
                        key=f"cancel_identity_{entity_name}",
                        use_container_width=True,
                    )

                if cancel_identity:

                    st.session_state[identity_editor_key] = False

                    st.session_state[identity_editor_version_key] = (
                        identity_editor_version + 1
                    )

                    st.rerun()

                if save_identity or clear_identity:

                    candidate = copy.deepcopy(current_model)

                    target_entity = get_entity(
                        candidate,
                        entity_name,
                    )

                    if target_entity is None:

                        st.session_state.manual_error = [
                            f"Entity {entity_name} does not exist."
                        ]

                        st.session_state.manual_success = None

                    else:

                        if clear_identity:

                            target_entity.pop(
                                "identity",
                                None,
                            )

                        else:

                            target_entity["identity"] = {
                                "fields": selected_identity_fields,
                            }

                        errors = forge_backend.validate_authoring_model(candidate)

                        if errors:

                            st.session_state.manual_error = errors
                            st.session_state.manual_success = None

                        else:

                            try:

                                save_specification(candidate)

                            except Exception as exc:

                                st.session_state.manual_error = [
                                    "Identity was validated but could not be saved: "
                                    f"{exc}"
                                ]

                                st.session_state.manual_success = None

                            else:

                                st.session_state.model = candidate

                                st.session_state.manual_error = []

                                st.session_state.manual_success = (
                                    f"Identity for **{entity_name}** "
                                    f"{'cleared' if clear_identity else 'updated'} "
                                    "and saved."
                                )

                                st.session_state[identity_editor_key] = False

                                st.session_state[identity_editor_version_key] = (
                                    identity_editor_version + 1
                                )

                    st.rerun()

            # ----------------------------------------------------------------
            # FIELDS
            # ----------------------------------------------------------------

            field_header_left, field_header_right = st.columns([0.82, 0.18])

            with field_header_left:

                st.markdown("**Fields**")

            with field_header_right:

                if st.button(
                    "+ Add Field",
                    key=f"add_field_{entity_name}",
                    use_container_width=True,
                ):

                    st.session_state.adding_field = entity_name

                    st.session_state.manual_error = []

                    st.session_state.manual_success = None

                    st.rerun()

            if not fields:

                st.caption("No fields defined.")

            # ----------------------------------------------------------------
            # MANUAL FIELD CREATION
            # ----------------------------------------------------------------

            if st.session_state.adding_field == entity_name:

                st.markdown("#### Add field")

                new_field_name = st.text_input(
                    "Field name",
                    key=f"new_field_name_{entity_name}",
                    placeholder="e.g. CUSTOMER_ID",
                )

                new_field_type = st.selectbox(
                    "Field type",
                    SUPPORTED_FIELD_TYPES,
                    key=f"new_field_type_{entity_name}",
                )

                # ------------------------------------------------------------
                # IDENTIFIER
                # ------------------------------------------------------------

                new_identity_strategy = None

                if new_field_type == "IDENTIFIER":

                    new_identity_strategy = st.selectbox(
                        "Identity strategy",
                        SUPPORTED_IDENTITY_STRATEGIES,
                        key=f"new_field_identity_{entity_name}",
                    )

                # ------------------------------------------------------------
                # GENERATION
                # ------------------------------------------------------------

                else:

                    st.markdown("**Generation**")

                    new_generation_strategy = None
                    new_distribution = None
                    new_generator = None
                    new_categorical_values = None
                    new_minimum = None
                    new_maximum = None
                    new_character_set = None

                    # --------------------------------------------------------
                    # BOOLEAN
                    # --------------------------------------------------------

                    if new_field_type == "BOOLEAN":

                        new_generation_strategy = "RANDOM"

                        st.caption("Randomly generate true / false.")

                    # --------------------------------------------------------
                    # OTHER NON-IDENTIFIER TYPES
                    # --------------------------------------------------------

                    else:

                        new_generation_strategy = st.selectbox(
                            "Generation strategy",
                            SUPPORTED_GENERATION_STRATEGIES,
                            key=f"new_generation_strategy_{entity_name}",
                        )

                        # ----------------------------------------------------
                        # STRING GENERATION
                        # ----------------------------------------------------

                        if new_field_type == "STRING":

                            string_generation_mode = st.selectbox(
                                "String generation",
                                [
                                    "CATEGORICAL",
                                    "RANDOM_STRING",
                                    "PATTERN",
                                    "SEMANTIC",
                                ],
                                key=f"new_string_generation_mode_{entity_name}",
                            )

                            if string_generation_mode == "RANDOM_STRING":

                                new_generator = "RANDOM_STRING"

                                new_minimum = st.number_input(
                                    "Minimum length",
                                    min_value=1,
                                    value=8,
                                    step=1,
                                    format="%d",
                                    key=f"new_random_string_minimum_{entity_name}",
                                )

                                new_maximum = st.number_input(
                                    "Maximum length",
                                    min_value=1,
                                    value=12,
                                    step=1,
                                    format="%d",
                                    key=f"new_random_string_maximum_{entity_name}",
                                )

                                new_character_set = st.selectbox(
                                    "Character set",
                                    SUPPORTED_STRING_CHARACTER_SETS,
                                    key=f"new_random_string_character_set_{entity_name}",
                                )

                            elif string_generation_mode == "PATTERN":

                                new_generator = "PATTERN"

                                new_pattern = st.text_input(
                                    "Pattern",
                                    value="AA-####-XX",
                                    key=f"new_pattern_{entity_name}",
                                    help=(
                                        "# = digit | "
                                        "A = uppercase letter | "
                                        "a = lowercase letter | "
                                        "X = alphanumeric. "
                                        "All other characters are literals."
                                    ),
                                )

                                st.caption(
                                    r"\# = digit · A = uppercase · a = lowercase · X = alphanumeric"
                                )

                                st.caption(f"Preview: `{preview_pattern(new_pattern)}`")

                            elif string_generation_mode == "SEMANTIC":

                                new_generator = "SEMANTIC"

                                semantic_description = st.text_area(
                                    "Semantic description",
                                    key=f"new_semantic_description_{entity_name}",
                                    placeholder=(
                                        "Generate realistic aerospace component "
                                        "descriptions suitable for an engineering dataset."
                                    ),
                                    help=(
                                        "Describe the kind of realistic STRING "
                                        "values you want FORGE to generate."
                                    ),
                                )

                                preview_col, clear_col = st.columns(2)

                                with preview_col:

                                    preview_semantic = st.button(
                                        "Interpret & Preview",
                                        key=f"preview_semantic_{entity_name}",
                                        use_container_width=True,
                                    )

                                with clear_col:

                                    clear_semantic = st.button(
                                        "Clear Preview",
                                        key=f"clear_semantic_{entity_name}",
                                        use_container_width=True,
                                    )

                                if clear_semantic:

                                    st.session_state.semantic_preview = None
                                    st.session_state.semantic_preview_error = []
                                    st.session_state.semantic_preview_description = ""
                                    st.session_state.semantic_preview_field = None

                                    st.rerun()

                                if preview_semantic:

                                    description = semantic_description.strip()

                                    if not description:

                                        st.session_state.semantic_preview = None
                                        st.session_state.semantic_preview_error = [
                                            "Semantic description must not be empty."
                                        ]
                                        st.session_state.semantic_preview_description = (
                                            ""
                                        )
                                        st.session_state.semantic_preview_field = (
                                            entity_name
                                        )

                                    else:

                                        try:

                                            semantic_result = (
                                                forge_backend.generate_semantic_preview(
                                                    description
                                                )
                                            )

                                            st.session_state.semantic_preview = (
                                                semantic_result
                                            )

                                            st.session_state.semantic_preview_error = []

                                            st.session_state.semantic_preview_description = (
                                                description
                                            )

                                            st.session_state.semantic_preview_field = (
                                                entity_name
                                            )

                                        except Exception as exc:

                                            st.session_state.semantic_preview = None
                                            st.session_state.semantic_preview_error = [
                                                str(exc)
                                            ]
                                            st.session_state.semantic_preview_description = (
                                                description
                                            )
                                            st.session_state.semantic_preview_field = (
                                                entity_name
                                            )

                                # ------------------------------------------------
                                # SEMANTIC PREVIEW
                                # ------------------------------------------------

                                semantic_result = st.session_state.semantic_preview

                                if (
                                    semantic_result is not None
                                    and st.session_state.semantic_preview_field
                                    == entity_name
                                ):

                                    status = semantic_result.get("status")

                                    if status == "PROPOSE":

                                        st.markdown("**LLM interpretation**")

                                        st.info(
                                            semantic_result.get(
                                                "message",
                                                "",
                                            )
                                        )

                                        st.markdown("**10-value preview**")

                                        preview_values = semantic_result.get(
                                            "preview_values",
                                            [],
                                        )

                                        for index, value in enumerate(
                                            preview_values,
                                            start=1,
                                        ):

                                            st.write(f"{index}. {value}")

                                        st.success(
                                            "Review the interpretation and "
                                            "preview values, then click "
                                            "**Create Field** to accept them."
                                        )

                                    elif status == "CLARIFY":

                                        st.warning(
                                            semantic_result.get(
                                                "message",
                                                "Additional clarification is required.",
                                            )
                                        )

                                    elif status == "UNSUPPORTED":

                                        st.error(
                                            semantic_result.get(
                                                "message",
                                                "This semantic requirement is unsupported.",
                                            )
                                        )

                                for error in st.session_state.semantic_preview_error:

                                    st.error(error)
                            else:

                                new_distribution = "CATEGORICAL"

                                categorical_text = st.text_area(
                                    "Categorical values",
                                    key=f"new_categorical_values_{entity_name}",
                                    help="Enter one generated value per line.",
                                    placeholder="RETAIL\nWHOLESALE\nGOVERNMENT",
                                )

                                new_categorical_values = [
                                    value.strip()
                                    for value in categorical_text.splitlines()
                                    if value.strip()
                                ]

                        # ----------------------------------------------------
                        # NON-STRING TYPES
                        # ----------------------------------------------------

                        else:

                            available_distributions = DISTRIBUTIONS_BY_FIELD_TYPE.get(
                                new_field_type,
                                SUPPORTED_DISTRIBUTIONS,
                            )

                            new_distribution = st.selectbox(
                                "Distribution",
                                available_distributions,
                                key=f"new_distribution_{entity_name}",
                            )

                        # ----------------------------------------------------
                        # DISTRIBUTION PARAMETERS
                        # ----------------------------------------------------

                        if new_field_type == "INTEGER":

                            # ------------------------------------------------
                            # INTEGER RANGE DISTRIBUTIONS
                            # ------------------------------------------------

                            if integer_distribution_requires_range(new_distribution):

                                new_minimum = st.number_input(
                                    "Minimum",
                                    value=1,
                                    step=1,
                                    format="%d",
                                    key=f"new_integer_minimum_{entity_name}",
                                )

                                new_maximum = st.number_input(
                                    "Maximum",
                                    value=100,
                                    step=1,
                                    format="%d",
                                    key=f"new_integer_maximum_{entity_name}",
                                )

                            # ------------------------------------------------
                            # INTEGER CATEGORICAL
                            # ------------------------------------------------

                            elif integer_distribution_requires_values(new_distribution):

                                integer_values_text = st.text_area(
                                    "Integer values",
                                    key=f"new_integer_values_{entity_name}",
                                    help="Enter one integer value per line.",
                                    placeholder="1\n5\n10\n20",
                                )

                                new_categorical_values = []

                                for value in integer_values_text.splitlines():

                                    value = value.strip()

                                    if not value:
                                        continue

                                    try:
                                        new_categorical_values.append(int(value))
                                    except ValueError:
                                        st.warning(
                                            f"'{value}' is not a valid integer value."
                                        )

                        # ----------------------------------------------------
                        # OTHER CATEGORICAL TYPES
                        # ----------------------------------------------------

                        elif (
                            new_field_type != "STRING"
                            and new_distribution == "CATEGORICAL"
                        ):

                            categorical_text = st.text_area(
                                "Categorical values",
                                key=f"new_string_categorical_values_{entity_name}",
                                help="Enter one generated value per line.",
                                placeholder="RETAIL\nWHOLESALE\nGOVERNMENT",
                            )

                            new_categorical_values = [
                                value.strip()
                                for value in categorical_text.splitlines()
                                if value.strip()
                            ]

                # ------------------------------------------------------------
                # CREATE / CANCEL
                # ------------------------------------------------------------

                create_col, cancel_col = st.columns(2)

                with create_col:

                    create_field = st.button(
                        "Create Field",
                        key=f"create_field_{entity_name}",
                        type="primary",
                        use_container_width=True,
                    )

                with cancel_col:

                    cancel_field_creation = st.button(
                        "Cancel",
                        key=f"cancel_field_{entity_name}",
                        use_container_width=True,
                    )

                # ------------------------------------------------------------
                # CANCEL
                # ------------------------------------------------------------

                if cancel_field_creation:

                    st.session_state.adding_field = None

                    st.session_state.manual_error = []

                    st.rerun()

                # ------------------------------------------------------------
                # CREATE
                # ------------------------------------------------------------

                if create_field:

                    operation = {
                        "operation": "ADD_FIELD",
                        "entity": entity_name,
                        "field": {
                            "name": new_field_name.strip(),
                            "type": new_field_type,
                        },
                    }

                    # --------------------------------------------------------
                    # IDENTIFIER
                    # --------------------------------------------------------

                    if new_field_type == "IDENTIFIER":

                        operation["field"]["identity"] = {
                            "strategy": new_identity_strategy,
                        }

                    # --------------------------------------------------------
                    # NON-IDENTIFIER GENERATION
                    # --------------------------------------------------------

                    else:

                        if (
                            new_field_type == "STRING"
                            and new_generator == "RANDOM_STRING"
                        ):

                            operation["field"]["generation"] = {
                                "strategy": new_generation_strategy,
                                "generator": new_generator,
                                "parameters": {
                                    "minimum_length": int(new_minimum),
                                    "maximum_length": int(new_maximum),
                                    "character_set": new_character_set,
                                },
                            }

                        elif new_field_type == "STRING" and new_generator == "PATTERN":

                            operation["field"]["generation"] = {
                                "strategy": new_generation_strategy,
                                "generator": "PATTERN",
                                "parameters": {
                                    "pattern": new_pattern,
                                },
                            }

                        elif new_field_type == "STRING" and new_generator == "SEMANTIC":

                            semantic_description = st.session_state.get(
                                "semantic_preview_description",
                                "",
                            ).strip()

                            semantic_preview = st.session_state.get(
                                "semantic_preview",
                            )

                            if (
                                not semantic_description
                                or not isinstance(semantic_preview, dict)
                                or semantic_preview.get("status") != "PROPOSE"
                            ):

                                st.session_state.manual_error = [
                                    "SEMANTIC generation requires a successful "
                                    "LLM interpretation and preview before the "
                                    "field can be created."
                                ]

                                st.rerun()

                            operation["field"]["generation"] = {
                                "strategy": new_generation_strategy,
                                "generator": "SEMANTIC",
                                "parameters": {
                                    "description": semantic_description,
                                },
                            }

                        else:

                            operation["field"]["generation"] = {
                                "strategy": new_generation_strategy,
                                "distribution": new_distribution,
                            }

                        # ------------------------------------------------
                        # INTEGER PARAMETERS
                        # ------------------------------------------------

                        if new_field_type == "INTEGER":

                            if integer_distribution_requires_range(new_distribution):

                                operation["field"]["generation"]["parameters"] = {
                                    "minimum": int(new_minimum),
                                    "maximum": int(new_maximum),
                                }

                            elif integer_distribution_requires_values(new_distribution):

                                operation["field"]["generation"]["parameters"] = {
                                    "values": new_categorical_values or [],
                                }

                        # ------------------------------------------------
                        # OTHER CATEGORICAL TYPES
                        # ------------------------------------------------

                        elif (
                            new_distribution == "CATEGORICAL"
                            and new_categorical_values is not None
                        ):

                            operation["field"]["generation"]["parameters"] = {
                                "values": new_categorical_values,
                            }
                    # --------------------------------------------------------
                    # FORGE VALIDATION
                    # --------------------------------------------------------

                    candidate, errors = build_candidate(
                        current_model,
                        [operation],
                    )

                    if errors:

                        st.session_state.manual_error = errors

                        st.session_state.manual_success = None

                    else:

                        try:
                            save_specification(candidate)
                        except Exception as exc:

                            st.session_state.manual_error = [
                                f"Field was validated but could not be saved: {exc}"
                            ]

                            st.session_state.manual_success = None

                        else:

                            st.session_state.model = candidate

                            st.session_state.adding_field = None

                            st.session_state.manual_error = []

                            st.session_state.manual_success = f"Created **{entity_name}.{new_field_name.strip()}** and saved."

                    st.rerun()

            for field in fields:

                field_name = field["name"]

                field_type = field.get(
                    "type",
                    "UNKNOWN",
                )

                reference = f"{entity_name}.{field_name}"

                field_left, field_right = st.columns([0.82, 0.18])

                with field_left:

                    st.markdown(f"**{field_name}**")

                    st.caption(field_type)

                    if "identity" in field:

                        st.write(
                            "Identity: " f"`{field['identity'].get('strategy', '?')}`"
                        )

                    generation = field.get("generation")

                    if generation:

                        if field_type == "BOOLEAN":

                            st.write(
                                "Generation: " f"`{generation.get('strategy', '?')}`"
                            )

                            st.caption("Randomly generates true / false.")

                        else:

                            generator = generation.get("generator")

                            if generator:

                                st.write(
                                    "Generation: "
                                    f"`{generation.get('strategy', '?')}` / "
                                    f"`{generator}`"
                                )

                                if generator == "RANDOM_STRING":

                                    parameters = generation.get("parameters", {})

                                    minimum_length = parameters.get(
                                        "minimum_length", "?"
                                    )
                                    maximum_length = parameters.get(
                                        "maximum_length", "?"
                                    )
                                    character_set = parameters.get("character_set", "?")

                                    st.caption(
                                        f"Length: {minimum_length}–{maximum_length} | "
                                        f"Character set: {character_set}"
                                    )

                            else:

                                st.write(
                                    "Generation: "
                                    f"`{generation.get('strategy', '?')}` / "
                                    f"`{generation.get('distribution', '?')}`"
                                )

                    elif field_type != "IDENTIFIER":

                        st.warning("Generation not configured")

                with field_right:

                    edit_col, delete_col = st.columns(2)

                    with edit_col:

                        if st.button(
                            "Edit",
                            key=f"field_edit_{reference}",
                            use_container_width=True,
                        ):

                            st.session_state.editing_field = reference

                            st.rerun()

                    with delete_col:

                        if st.button(
                            "Delete",
                            key=f"field_delete_{reference}",
                            use_container_width=True,
                        ):

                            candidate = copy.deepcopy(current_model)

                            target = get_field(
                                candidate,
                                reference,
                            )

                            if target is None:

                                st.session_state.manual_error = [
                                    f"Field {reference} does not exist."
                                ]

                                st.session_state.manual_success = None

                            else:

                                entity_name, field_name = reference.split(
                                    ".",
                                    1,
                                )

                                entity = get_entity(
                                    candidate,
                                    entity_name,
                                )

                                if entity is None:

                                    st.session_state.manual_error = [
                                        f"Entity {entity_name} does not exist."
                                    ]

                                    st.session_state.manual_success = None

                                else:

                                    identity = entity.get(
                                        "identity",
                                        {},
                                    )

                                    identity_fields = (
                                        identity.get("fields", [])
                                        if isinstance(identity, dict)
                                        else []
                                    )

                                    # ------------------------------------------------
                                    # FOREIGN KEY PROTECTION
                                    # ------------------------------------------------

                                    foreign_key_references = []

                                    for foreign_key in current_model.get(
                                        "foreign_keys",
                                        [],
                                    ):
                                        if not isinstance(
                                            foreign_key,
                                            dict,
                                        ):
                                            continue

                                        source = foreign_key.get(
                                            "source"
                                        )

                                        if not isinstance(
                                            source,
                                            dict,
                                        ):
                                            continue

                                        source_entity = source.get(
                                            "entity"
                                        )

                                        source_fields = source.get(
                                            "fields",
                                            [],
                                        )

                                        if (
                                            source_entity == entity_name
                                            and isinstance(
                                                source_fields,
                                                list,
                                            )
                                            and field_name in source_fields
                                        ):
                                            foreign_key_references.append(
                                                foreign_key.get(
                                                    "name",
                                                    "Unnamed foreign key",
                                                )
                                            )

                                    if foreign_key_references:

                                        st.session_state.manual_error = [
                                            f"Field **{reference}** cannot be "
                                            "deleted because it is referenced "
                                            "by foreign key(s): "
                                            + ", ".join(
                                                f"**{name}**"
                                                for name in foreign_key_references
                                            )
                                            + ". Remove the foreign key first."
                                        ]

                                        st.session_state.manual_success = None

                                    # ------------------------------------------------
                                    # ENTITY IDENTITY PROTECTION
                                    # ------------------------------------------------

                                    elif field_name in identity_fields:

                                        st.session_state.manual_error = [
                                            f"Field **{reference}** cannot be "
                                            "deleted because it is part of the "
                                            "entity identity."
                                        ]

                                        st.session_state.manual_success = None

                                    else:

                                        entity["fields"] = [
                                            field
                                            for field in entity.get(
                                                "fields",
                                                [],
                                            )
                                            if field.get("name") != field_name
                                        ]

                                        validation_errors = (
                                            forge_backend.validate_authoring_model(
                                                candidate
                                            )
                                        )

                                        if validation_errors:

                                            st.session_state.manual_error = (
                                                validation_errors
                                            )

                                            st.session_state.manual_success = None

                                        else:

                                            try:

                                                save_specification(candidate)

                                            except Exception as exc:

                                                st.session_state.manual_error = [
                                                    "Field was validated but "
                                                    f"could not be saved: {exc}"
                                                ]

                                                st.session_state.manual_success = None

                                            else:

                                                st.session_state.model = candidate
                                                st.session_state.editing_field = None
                                                st.session_state.manual_success = f"Deleted **{reference}** and saved."

                            st.rerun()

                # ------------------------------------------------------------
                # FIELD EDITOR
                # ------------------------------------------------------------

                if st.session_state.editing_field == reference:

                    st.markdown("#### Edit field")

                    # --------------------------------------------------------
                    # FIELD TYPE
                    # --------------------------------------------------------

                    new_type = st.selectbox(
                        "Field type",
                        SUPPORTED_FIELD_TYPES,
                        index=(
                            SUPPORTED_FIELD_TYPES.index(field_type)
                            if field_type in SUPPORTED_FIELD_TYPES
                            else 0
                        ),
                        key=f"edit_field_type_{reference}",
                    )

                    identifier = new_type == "IDENTIFIER"

                    new_identity = None
                    new_strategy = None
                    new_distribution = None
                    new_generator = None
                    new_categorical_values = None
                    new_minimum = None
                    new_maximum = None

                    # --------------------------------------------------------
                    # IDENTIFIER
                    # --------------------------------------------------------

                    if identifier:

                        current_identity = field.get(
                            "identity",
                            {},
                        ).get(
                            "strategy",
                            SUPPORTED_IDENTITY_STRATEGIES[0],
                        )

                        new_identity = st.selectbox(
                            "Identity strategy",
                            SUPPORTED_IDENTITY_STRATEGIES,
                            index=(
                                SUPPORTED_IDENTITY_STRATEGIES.index(current_identity)
                                if current_identity in SUPPORTED_IDENTITY_STRATEGIES
                                else 0
                            ),
                            key=f"edit_field_identity_{reference}",
                        )

                    # --------------------------------------------------------
                    # GENERATION
                    # --------------------------------------------------------

                    else:

                        new_identity = None

                        generation = field.get(
                            "generation",
                            {},
                        )

                        new_strategy = None
                        new_distribution = None
                        new_categorical_values = None

                        # ----------------------------------------------------
                        # BOOLEAN
                        # ----------------------------------------------------

                        if new_type == "BOOLEAN":

                            new_strategy = "RANDOM"

                            st.caption("Randomly generate true / false.")

                        # ----------------------------------------------------
                        # OTHER NON-IDENTIFIER TYPES
                        # ----------------------------------------------------

                        else:

                            current_strategy = generation.get(
                                "strategy",
                                SUPPORTED_GENERATION_STRATEGIES[0],
                            )

                            new_strategy = st.selectbox(
                                "Generation strategy",
                                SUPPORTED_GENERATION_STRATEGIES,
                                index=(
                                    SUPPORTED_GENERATION_STRATEGIES.index(
                                        current_strategy
                                    )
                                    if current_strategy
                                    in SUPPORTED_GENERATION_STRATEGIES
                                    else 0
                                ),
                                key=f"edit_generation_strategy_{reference}",
                            )

                            # ------------------------------------------------
                            # STRING GENERATION
                            # ------------------------------------------------

                            if new_type == "STRING":

                                current_generator = generation.get("generator")

                                if current_generator in {
                                    "RANDOM_STRING",
                                    "PATTERN",
                                    "SEMANTIC",
                                }:

                                    current_parameters = generation.get(
                                        "parameters",
                                        {},
                                    )

                                    string_generation_modes = [
                                        "CATEGORICAL",
                                        "RANDOM_STRING",
                                        "PATTERN",
                                        "SEMANTIC",
                                    ]

                                    string_generation_mode = st.selectbox(
                                        "String generation",
                                        string_generation_modes,
                                        index=(
                                            string_generation_modes.index(
                                                current_generator
                                            )
                                            if current_generator
                                            in string_generation_modes
                                            else 0
                                        ),
                                        key=f"edit_string_generation_mode_{reference}",
                                    )

                                    if string_generation_mode == "RANDOM_STRING":

                                        new_generator = "RANDOM_STRING"

                                        current_minimum = current_parameters.get(
                                            "minimum_length",
                                            8,
                                        )

                                        current_maximum = current_parameters.get(
                                            "maximum_length",
                                            12,
                                        )

                                        current_character_set = current_parameters.get(
                                            "character_set",
                                            SUPPORTED_STRING_CHARACTER_SETS[0],
                                        )

                                        new_minimum = st.number_input(
                                            "Minimum length",
                                            min_value=1,
                                            value=int(current_minimum),
                                            step=1,
                                            format="%d",
                                            key=f"edit_random_string_minimum_{reference}",
                                        )

                                        new_maximum = st.number_input(
                                            "Maximum length",
                                            min_value=1,
                                            value=int(current_maximum),
                                            step=1,
                                            format="%d",
                                            key=f"edit_random_string_maximum_{reference}",
                                        )

                                        new_character_set = st.selectbox(
                                            "Character set",
                                            SUPPORTED_STRING_CHARACTER_SETS,
                                            index=(
                                                SUPPORTED_STRING_CHARACTER_SETS.index(
                                                    current_character_set
                                                )
                                                if current_character_set
                                                in SUPPORTED_STRING_CHARACTER_SETS
                                                else 0
                                            ),
                                            key=f"edit_random_string_character_set_{reference}",
                                        )

                                    elif string_generation_mode == "PATTERN":

                                        new_generator = "PATTERN"

                                        current_pattern = current_parameters.get(
                                            "pattern",
                                            "AA-####-XX",
                                        )

                                        new_pattern = st.text_input(
                                            "Pattern",
                                            value=str(current_pattern),
                                            key=f"edit_pattern_{reference}",
                                            help=(
                                                "# = digit | "
                                                "A = uppercase letter | "
                                                "a = lowercase letter | "
                                                "X = alphanumeric. "
                                                "All other characters are literals."
                                            ),
                                        )

                                        st.caption(
                                            r"\# digit · A uppercase · a lowercase · X alphanumeric"
                                        )
                                        st.caption(
                                            f"Preview: `{preview_pattern(new_pattern)}`"
                                        )

                                    elif string_generation_mode == "SEMANTIC":

                                        new_generator = "SEMANTIC"

                                        current_description = current_parameters.get(
                                            "description",
                                            "",
                                        )

                                        new_semantic_description = st.text_area(
                                            "Semantic description",
                                            value=str(current_description),
                                            key=f"edit_semantic_description_{reference}",
                                            placeholder=(
                                                "Generate realistic engineering "
                                                "document titles."
                                            ),
                                            help=(
                                                "Describe the kind of realistic "
                                                "STRING values you want FORGE "
                                                "to generate."
                                            ),
                                        )

                                        preview_col, clear_col = st.columns(2)

                                        with preview_col:

                                            preview_semantic = st.button(
                                                "Interpret & Preview",
                                                key=f"edit_preview_semantic_{reference}",
                                                use_container_width=True,
                                            )

                                        with clear_col:

                                            clear_semantic = st.button(
                                                "Clear Preview",
                                                key=f"edit_clear_semantic_{reference}",
                                                use_container_width=True,
                                            )

                                        if clear_semantic:

                                            st.session_state.semantic_preview = None
                                            st.session_state.semantic_preview_error = []
                                            st.session_state.semantic_preview_description = (
                                                ""
                                            )
                                            st.session_state.semantic_preview_field = (
                                                None
                                            )

                                            st.rerun()

                                        if preview_semantic:

                                            description = (
                                                new_semantic_description.strip()
                                            )

                                            if not description:

                                                st.session_state.semantic_preview = None
                                                st.session_state.semantic_preview_error = [
                                                    "Semantic description must not be empty."
                                                ]
                                                st.session_state.semantic_preview_description = (
                                                    ""
                                                )
                                                st.session_state.semantic_preview_field = (
                                                    reference
                                                )

                                            else:

                                                try:

                                                    semantic_result = forge_backend.generate_semantic_preview(
                                                        description
                                                    )

                                                    st.session_state.semantic_preview = (
                                                        semantic_result
                                                    )

                                                    st.session_state.semantic_preview_error = (
                                                        []
                                                    )

                                                    st.session_state.semantic_preview_description = (
                                                        description
                                                    )

                                                    st.session_state.semantic_preview_field = (
                                                        reference
                                                    )

                                                except Exception as exc:

                                                    st.session_state.semantic_preview = (
                                                        None
                                                    )
                                                    st.session_state.semantic_preview_error = [
                                                        str(exc)
                                                    ]
                                                    st.session_state.semantic_preview_description = (
                                                        description
                                                    )
                                                    st.session_state.semantic_preview_field = (
                                                        reference
                                                    )

                                        semantic_result = (
                                            st.session_state.semantic_preview
                                        )

                                        if (
                                            semantic_result is not None
                                            and st.session_state.semantic_preview_field
                                            == reference
                                        ):

                                            status = semantic_result.get("status")

                                            if status == "PROPOSE":

                                                st.markdown("**LLM interpretation**")

                                                st.info(
                                                    semantic_result.get(
                                                        "message",
                                                        "",
                                                    )
                                                )

                                                st.markdown("**10-value preview**")

                                                preview_values = semantic_result.get(
                                                    "preview_values",
                                                    [],
                                                )

                                                for index, value in enumerate(
                                                    preview_values,
                                                    start=1,
                                                ):

                                                    st.write(f"{index}. {value}")

                                            elif status == "CLARIFY":

                                                st.warning(
                                                    semantic_result.get(
                                                        "message",
                                                        "Additional clarification is required.",
                                                    )
                                                )

                                            elif status == "UNSUPPORTED":

                                                st.error(
                                                    semantic_result.get(
                                                        "message",
                                                        "This semantic requirement is unsupported.",
                                                    )
                                                )

                                        for (
                                            error
                                        ) in st.session_state.semantic_preview_error:

                                            st.error(error)

                                    else:

                                        new_generator = None

                                        parameters = generation.get(
                                            "parameters",
                                            {},
                                        )

                                        current_values = parameters.get(
                                            "values",
                                            [],
                                        )

                                        if not isinstance(
                                            current_values,
                                            list,
                                        ):
                                            current_values = []

                                        categorical_text = st.text_area(
                                            "Categorical values",
                                            value="\n".join(
                                                str(value) for value in current_values
                                            ),
                                            help="Enter one generated value per line.",
                                            placeholder="RETAIL\nWHOLESALE\nGOVERNMENT",
                                            key=f"edit_string_categorical_values_{reference}",
                                        )

                                        new_categorical_values = [
                                            value.strip()
                                            for value in categorical_text.splitlines()
                                            if value.strip()
                                        ]

                                        new_distribution = "CATEGORICAL"

                                else:

                                    # Existing STRING categorical generation
                                    current_distribution = generation.get(
                                        "distribution",
                                        "CATEGORICAL",
                                    )

                                    new_distribution = "CATEGORICAL"

                                    parameters = generation.get(
                                        "parameters",
                                        {},
                                    )

                                    current_values = parameters.get(
                                        "values",
                                        [],
                                    )

                                    if not isinstance(
                                        current_values,
                                        list,
                                    ):
                                        current_values = []

                                    categorical_text = st.text_area(
                                        "Categorical values",
                                        value="\n".join(
                                            str(value) for value in current_values
                                        ),
                                        help="Enter one generated value per line.",
                                        placeholder="RETAIL\nWHOLESALE\nGOVERNMENT",
                                        key=f"edit_string_categorical_values_{reference}",
                                    )

                                    new_categorical_values = [
                                        value.strip()
                                        for value in categorical_text.splitlines()
                                        if value.strip()
                                    ]

                            # ------------------------------------------------
                            # NON-STRING TYPES
                            # ------------------------------------------------

                            else:

                                available_distributions = (
                                    DISTRIBUTIONS_BY_FIELD_TYPE.get(
                                        new_type,
                                        SUPPORTED_DISTRIBUTIONS,
                                    )
                                )

                                current_distribution = generation.get(
                                    "distribution",
                                    available_distributions[0],
                                )

                                new_distribution = st.selectbox(
                                    "Distribution",
                                    available_distributions,
                                    index=(
                                        available_distributions.index(
                                            current_distribution
                                        )
                                        if current_distribution
                                        in available_distributions
                                        else 0
                                    ),
                                    key=f"edit_generation_distribution_{reference}",
                                )

                                # --------------------------------------------
                                # DISTRIBUTION PARAMETERS
                                # --------------------------------------------

                                if new_type == "INTEGER":

                                    parameters = generation.get(
                                        "parameters",
                                        {},
                                    )

                                    # ----------------------------------------
                                    # INTEGER RANGE DISTRIBUTIONS
                                    # ----------------------------------------

                                    if integer_distribution_requires_range(
                                        new_distribution
                                    ):

                                        current_minimum = parameters.get(
                                            "minimum",
                                            1,
                                        )

                                        current_maximum = parameters.get(
                                            "maximum",
                                            100,
                                        )

                                        new_minimum = st.number_input(
                                            "Minimum",
                                            value=int(current_minimum),
                                            step=1,
                                            format="%d",
                                            key=f"edit_integer_minimum_{reference}",
                                        )

                                        new_maximum = st.number_input(
                                            "Maximum",
                                            value=int(current_maximum),
                                            step=1,
                                            format="%d",
                                            key=f"edit_integer_maximum_{reference}",
                                        )

                                    # ----------------------------------------
                                    # INTEGER CATEGORICAL
                                    # ----------------------------------------

                                    elif integer_distribution_requires_values(
                                        new_distribution
                                    ):

                                        current_values = parameters.get(
                                            "values",
                                            [],
                                        )

                                        if not isinstance(
                                            current_values,
                                            list,
                                        ):
                                            current_values = []

                                        integer_values_text = st.text_area(
                                            "Integer values",
                                            value="\n".join(
                                                str(value) for value in current_values
                                            ),
                                            help="Enter one integer value per line.",
                                            placeholder="1\n5\n10\n20",
                                            key=f"edit_integer_values_{reference}",
                                        )

                                        new_categorical_values = []

                                        for value in integer_values_text.splitlines():

                                            value = value.strip()

                                            if not value:
                                                continue

                                            try:
                                                new_categorical_values.append(
                                                    int(value)
                                                )
                                            except ValueError:
                                                st.warning(
                                                    f"'{value}' is not a valid integer value."
                                                )

                                # --------------------------------------------
                                # OTHER CATEGORICAL TYPES
                                # --------------------------------------------

                                elif new_distribution == "CATEGORICAL":

                                    parameters = generation.get(
                                        "parameters",
                                        {},
                                    )

                                    current_values = parameters.get(
                                        "values",
                                        [],
                                    )

                                    if not isinstance(
                                        current_values,
                                        list,
                                    ):
                                        current_values = []

                                    categorical_text = st.text_area(
                                        "Categorical values",
                                        value="\n".join(
                                            str(value) for value in current_values
                                        ),
                                        help="Enter one generated value per line.",
                                        placeholder="RETAIL\nWHOLESALE\nGOVERNMENT",
                                        key=f"edit_categorical_values_{reference}",
                                    )

                                    new_categorical_values = [
                                        value.strip()
                                        for value in categorical_text.splitlines()
                                        if value.strip()
                                    ]

                    # --------------------------------------------------------
                    # SAVE / CANCEL
                    # --------------------------------------------------------

                    save, cancel = st.columns(2)

                    with save:

                        save_field = st.button(
                            "Save field",
                            key=f"save_field_{reference}",
                            type="primary",
                            use_container_width=True,
                        )

                    with cancel:

                        cancel_field = st.button(
                            "Cancel",
                            key=f"cancel_field_{reference}",
                            use_container_width=True,
                        )

                    if cancel_field:

                        st.session_state.editing_field = None

                        st.rerun()

                    if save_field:

                        candidate = copy.deepcopy(current_model)

                        target = get_field(
                            candidate,
                            reference,
                        )

                        if target is None:

                            st.session_state.manual_error = [
                                f"Field {reference} does not exist."
                            ]

                            st.rerun()

                        # ----------------------------------------------------
                        # Reset mutually exclusive configuration
                        # ----------------------------------------------------

                        target["type"] = new_type

                        target.pop(
                            "identity",
                            None,
                        )

                        target.pop(
                            "generation",
                            None,
                        )

                        # ----------------------------------------------------
                        # Identifier configuration
                        # ----------------------------------------------------

                        if identifier:

                            target["identity"] = {
                                "strategy": new_identity,
                            }

                        # ----------------------------------------------------
                        # Generation configuration
                        # ----------------------------------------------------

                        elif new_type == "BOOLEAN":

                            target["generation"] = {
                                "strategy": "RANDOM",
                            }

                        else:

                            # ------------------------------------------------
                            # STRING RANDOM STRING
                            # ------------------------------------------------

                            if (
                                new_type == "STRING"
                                and new_generator == "RANDOM_STRING"
                            ):

                                target["generation"] = {
                                    "strategy": new_strategy,
                                    "generator": "RANDOM_STRING",
                                    "parameters": {
                                        "minimum_length": int(new_minimum),
                                        "maximum_length": int(new_maximum),
                                        "character_set": new_character_set,
                                    },
                                }

                            # ------------------------------------------------
                            # STRING PATTERN
                            # ------------------------------------------------

                            elif new_type == "STRING" and new_generator == "SEMANTIC":

                                semantic_description = new_semantic_description.strip()

                                semantic_preview = st.session_state.get(
                                    "semantic_preview",
                                )

                                semantic_preview_field = st.session_state.get(
                                    "semantic_preview_field",
                                )

                                semantic_preview_description = st.session_state.get(
                                    "semantic_preview_description",
                                    "",
                                ).strip()

                                # ------------------------------------------------
                                # Require successful interpretation
                                # ------------------------------------------------

                                if (
                                    not semantic_description
                                    or semantic_preview_field != reference
                                    or semantic_preview_description
                                    != semantic_description
                                    or not isinstance(
                                        semantic_preview,
                                        dict,
                                    )
                                    or semantic_preview.get("status") != "PROPOSE"
                                ):

                                    st.session_state.manual_error = [
                                        "SEMANTIC generation requires a successful "
                                        "LLM interpretation and preview for the "
                                        "current description before the field "
                                        "can be saved."
                                    ]

                                    st.rerun()

                                target["generation"] = {
                                    "strategy": new_strategy,
                                    "generator": "SEMANTIC",
                                    "parameters": {
                                        "description": semantic_description,
                                    },
                                }

                            # ------------------------------------------------
                            # STRING CATEGORICAL
                            # ------------------------------------------------

                            elif new_type == "STRING":

                                target["generation"] = {
                                    "strategy": new_strategy,
                                    "distribution": "CATEGORICAL",
                                    "parameters": {
                                        "values": (new_categorical_values or []),
                                    },
                                }

                            # ------------------------------------------------
                            # OTHER DISTRIBUTION-BASED TYPES
                            # ------------------------------------------------

                            else:

                                target["generation"] = {
                                    "strategy": new_strategy,
                                    "distribution": new_distribution,
                                }

                                # --------------------------------------------
                                # INTEGER PARAMETERS
                                # --------------------------------------------

                                if new_type == "INTEGER":

                                    if integer_distribution_requires_range(
                                        new_distribution
                                    ):

                                        target["generation"]["parameters"] = {
                                            "minimum": int(new_minimum),
                                            "maximum": int(new_maximum),
                                        }

                                    elif integer_distribution_requires_values(
                                        new_distribution
                                    ):

                                        target["generation"]["parameters"] = {
                                            "values": (new_categorical_values or []),
                                        }

                                # --------------------------------------------
                                # OTHER CATEGORICAL TYPES
                                # --------------------------------------------

                                elif (
                                    new_distribution == "CATEGORICAL"
                                    and new_categorical_values is not None
                                ):

                                    target["generation"]["parameters"] = {
                                        "values": (new_categorical_values),
                                    }

                        # ----------------------------------------------------
                        # FORGE VALIDATION
                        # ----------------------------------------------------

                        errors = forge_backend.validate_authoring_model(candidate)

                        if errors:

                            st.session_state.manual_error = errors

                            st.session_state.manual_success = None

                        else:
                            try:
                                save_specification(candidate)
                            except Exception as exc:
                                st.session_state.manual_error = [
                                    f"Field was validated but could not be saved: {exc}"
                                ]
                            else:
                                st.session_state.model = candidate
                                st.session_state.editing_field = None
                                st.session_state.manual_success = (
                                    f"Updated **{reference}** and saved."
                                )

                        st.rerun()

    # =========================================================================
    # RELATIONSHIPS
    # =========================================================================

    st.divider()

    st.subheader("🔗 Relationships")

    relationships = current_model.get("relationships", [])

    if not relationships:

        st.caption("No relationships defined.")

    # -------------------------------------------------------------------------
    # ADD RELATIONSHIP
    # -------------------------------------------------------------------------

    if st.button(
        "➕ Add relationship",
        key="add_relationship",
        use_container_width=True,
    ):

        st.session_state.adding_relationship = True

        st.session_state.manual_error = []

        st.rerun()

    if st.session_state.get("adding_relationship", False):

        entity_list = entity_names(current_model)

        if not entity_list:

            st.warning("Create at least two entities before adding a relationship.")

        elif len(entity_list) < 2:

            st.warning("A relationship requires at least two entities.")

        else:

            with st.container(border=True):

                st.markdown("**New relationship**")

                source_entity = st.selectbox(
                    "Source entity",
                    entity_list,
                    key="new_relationship_source_entity",
                )

                source_object = get_entity(
                    current_model,
                    source_entity,
                )

                source_fields = [
                    field["name"] for field in (source_object or {}).get("fields", [])
                ]

                if not source_fields:

                    st.warning(f"Source entity **{source_entity}** has no fields.")

                else:

                    source_field = st.selectbox(
                        "Source field",
                        source_fields,
                        key="new_relationship_source_field",
                    )

                    target_entity_options = [
                        entity for entity in entity_list if entity != source_entity
                    ]

                    target_entity = st.selectbox(
                        "Target entity",
                        target_entity_options,
                        key="new_relationship_target_entity",
                    )

                    target_object = get_entity(
                        current_model,
                        target_entity,
                    )

                    target_fields = [
                        field["name"]
                        for field in (target_object or {}).get("fields", [])
                    ]

                    if not target_fields:

                        st.warning(f"Target entity **{target_entity}** has no fields.")

                    else:

                        target_field = st.selectbox(
                            "Target field",
                            target_fields,
                            key="new_relationship_target_field",
                        )

                        relationship_type = st.selectbox(
                            "Relationship type",
                            SUPPORTED_RELATIONSHIP_TYPES,
                            key="new_relationship_type",
                        )

                        create_col, cancel_col = st.columns(2)

                        with create_col:

                            create_relationship = st.button(
                                "Add Relationship",
                                key="create_relationship",
                                type="primary",
                                use_container_width=True,
                            )

                        with cancel_col:

                            cancel_relationship = st.button(
                                "Cancel",
                                key="cancel_new_relationship",
                                use_container_width=True,
                            )

                        if cancel_relationship:

                            st.session_state.adding_relationship = False

                            st.session_state.manual_error = []

                            st.rerun()

                        if create_relationship:

                            candidate = copy.deepcopy(current_model)

                            candidate.setdefault(
                                "relationships",
                                [],
                            )

                            candidate["relationships"].append(
                                {
                                    "source": (f"{source_entity}.{source_field}"),
                                    "target": (f"{target_entity}.{target_field}"),
                                    "type": relationship_type,
                                }
                            )

                            errors = forge_backend.validate_authoring_model(candidate)

                            if errors:

                                st.session_state.manual_error = errors

                                st.session_state.manual_success = None

                            else:

                                try:

                                    save_specification(candidate)

                                except Exception as exc:

                                    st.session_state.manual_error = [
                                        "Relationship was validated but "
                                        f"could not be saved: {exc}"
                                    ]

                                    st.session_state.manual_success = None

                                else:

                                    st.session_state.model = candidate

                                    st.session_state.adding_relationship = False

                                    st.session_state.manual_success = (
                                        "Relationship added, validated, and saved."
                                    )

                                    st.session_state.manual_error = []

                            st.rerun()
    for index, relationship in enumerate(relationships):

        with st.container(border=True):

            st.markdown(f"**{relationship.get('type', '?')}**")

            st.caption(
                f"{relationship.get('source', '?')} "
                f"→ "
                f"{relationship.get('target', '?')}"
            )

            col1, col2 = st.columns(2)

            with col1:
                if st.button("Edit relationship", key=f"relationship_edit_{index}"):
                    st.session_state.editing_relationship = index
                    st.rerun()

            with col2:
                if st.button("Delete relationship", key=f"relationship_delete_{index}"):
                    candidate = copy.deepcopy(current_model)
                    candidate["relationships"].pop(index)

                    validation_errors = forge_backend.validate_authoring_model(
                        candidate
                    )

                    if validation_errors:
                        st.error("Cannot delete relationship:")
                        for error in validation_errors:
                            st.error(error)
                    else:
                        save_specification(candidate)
                        st.session_state.model = candidate
                        st.session_state.editing_relationship = None
                        st.session_state.manual_success = (
                            "Relationship deleted successfully."
                        )
                        st.rerun()

        if st.session_state.editing_relationship == index:

            entity_list = entity_names(current_model)

            relationship_source = relationship.get(
                "source",
                "",
            )

            relationship_target = relationship.get(
                "target",
                "",
            )

            source_entity_current = (
                relationship_source.split(".", 1)[0]
                if "." in relationship_source
                else ""
            )

            target_entity_current = (
                relationship_target.split(".", 1)[0]
                if "." in relationship_target
                else ""
            )

            source_field_current = (
                relationship_source.split(".", 1)[1]
                if "." in relationship_source
                else ""
            )

            target_field_current = (
                relationship_target.split(".", 1)[1]
                if "." in relationship_target
                else ""
            )

            with st.form(key=f"relationship_form_{index}"):

                source_entity = st.selectbox(
                    "Source entity",
                    entity_list,
                    index=(
                        entity_list.index(source_entity_current)
                        if source_entity_current in entity_list
                        else 0
                    ),
                )

                source_object = get_entity(
                    current_model,
                    source_entity,
                )

                source_fields = [
                    field["name"] for field in (source_object or {}).get("fields", [])
                ]

                source_field = st.selectbox(
                    "Source field",
                    source_fields,
                    index=(
                        (
                            source_fields.index(source_field_current)
                            if source_field_current in source_fields
                            else 0
                        )
                        if source_fields
                        else 0
                    ),
                )

                target_entity = st.selectbox(
                    "Target entity",
                    entity_list,
                    index=(
                        entity_list.index(target_entity_current)
                        if target_entity_current in entity_list
                        else 0
                    ),
                )

                target_object = get_entity(
                    current_model,
                    target_entity,
                )

                target_fields = [
                    field["name"] for field in (target_object or {}).get("fields", [])
                ]

                target_field = st.selectbox(
                    "Target field",
                    target_fields,
                    index=(
                        (
                            target_fields.index(target_field_current)
                            if target_field_current in target_fields
                            else 0
                        )
                        if target_fields
                        else 0
                    ),
                )

                relationship_type = st.selectbox(
                    "Relationship type",
                    SUPPORTED_RELATIONSHIP_TYPES,
                    index=(
                        SUPPORTED_RELATIONSHIP_TYPES.index(
                            relationship.get(
                                "type",
                                "ONE_TO_MANY",
                            )
                        )
                        if relationship.get(
                            "type",
                            "ONE_TO_MANY",
                        )
                        in SUPPORTED_RELATIONSHIP_TYPES
                        else 0
                    ),
                )

                save, cancel = st.columns(2)

                with save:

                    save_relationship = st.form_submit_button(
                        "Save",
                        type="primary",
                        use_container_width=True,
                    )

                with cancel:

                    cancel_relationship = st.form_submit_button(
                        "Cancel",
                        use_container_width=True,
                    )

            if cancel_relationship:

                st.session_state.editing_relationship = None

                st.rerun()

            if save_relationship:

                candidate = copy.deepcopy(current_model)

                candidate["relationships"][index] = {
                    "source": (f"{source_entity}.{source_field}"),
                    "target": (f"{target_entity}.{target_field}"),
                    "type": relationship_type,
                }

                errors = forge_backend.validate_authoring_model(candidate)

                if errors:

                    st.session_state.manual_error = errors

                else:
                    try:
                        save_specification(candidate)
                    except Exception as exc:
                        st.session_state.manual_error = [
                            f"Relationship was validated but could not be saved: {exc}"
                        ]
                    else:
                        st.session_state.model = candidate
                        st.session_state.editing_relationship = None
                        st.session_state.manual_success = (
                            "Relationship updated, validated, and saved."
                        )

                st.rerun()

# ============================================================================
# FOREIGN KEYS
# ============================================================================

st.divider()

st.subheader("🔑 Foreign Keys")

foreign_keys = current_model.get(
    "foreign_keys",
    [],
)

if not foreign_keys:

    st.caption("No foreign keys defined.")


# ---------------------------------------------------------------------------
# ADD FOREIGN KEY
# ---------------------------------------------------------------------------

if st.button(
    "➕ Add foreign key",
    key="add_foreign_key",
    use_container_width=True,
):

    st.session_state.adding_foreign_key = True
    st.session_state.editing_foreign_key = None

    st.rerun()


if st.session_state.get(
    "adding_foreign_key",
    False,
):

    if len(entities) < 2:

        st.warning(
            "Create at least two entities before adding a foreign key."
        )

    else:

        st.markdown("**New foreign key**")

        fk_entity_names = [
            entity.get("name")
            for entity in entities
            if isinstance(entity, dict)
            and entity.get("name")
        ]

        fk_source_entity = st.selectbox(
            "Source entity",
            fk_entity_names,
            key="new_foreign_key_source_entity",
        )

        fk_source_entity_object = get_entity(
            current_model,
            fk_source_entity,
        )

        fk_source_fields = [
            field.get("name")
            for field in (
                fk_source_entity_object or {}
            ).get(
                "fields",
                [],
            )
            if isinstance(field, dict)
            and field.get("name")
        ]

        fk_source_selected_fields = st.multiselect(
            "Source fields",
            options=fk_source_fields,
            key="new_foreign_key_source_fields",
            help=(
                "Select source fields in the same order as "
                "the target identity fields."
            ),
        )

        fk_target_entity = st.selectbox(
            "Target entity",
            fk_entity_names,
            key="new_foreign_key_target_entity",
        )

        fk_target_entity_object = get_entity(
            current_model,
            fk_target_entity,
        )

        fk_target_identity = (
            fk_target_entity_object.get(
                "identity",
                {},
            )
            if fk_target_entity_object
            else {}
        )

        fk_target_identity_fields = (
            fk_target_identity.get(
                "fields",
                [],
            )
            if isinstance(
                fk_target_identity,
                dict,
            )
            else []
        )

        if not fk_target_identity_fields:

            st.warning(
                f"Target entity **{fk_target_entity}** "
                "must define an identity before it can be "
                "referenced by a foreign key."
            )

        else:

            st.markdown("**Target identity**")

            st.code(
                " + ".join(
                    fk_target_identity_fields
                )
            )

            st.caption(
                "Target fields are automatically taken from "
                "the target entity identity."
            )

        fk_add_left, fk_add_right = st.columns(2)

        with fk_add_left:

            create_foreign_key = st.button(
                "Add Foreign Key",
                key="create_foreign_key",
                type="primary",
                use_container_width=True,
            )

        with fk_add_right:

            cancel_foreign_key = st.button(
                "Cancel",
                key="cancel_new_foreign_key",
                use_container_width=True,
            )

        if cancel_foreign_key:

            st.session_state.adding_foreign_key = False

            st.rerun()

        if create_foreign_key:

            validation_error = None

            if not fk_source_selected_fields:

                validation_error = (
                    "Select at least one source field."
                )

            elif not fk_target_identity_fields:

                validation_error = (
                    f"Target entity **{fk_target_entity}** "
                    "must define an identity."
                )

            elif len(
                fk_source_selected_fields
            ) != len(
                fk_target_identity_fields
            ):

                validation_error = (
                    "The number of source fields must match "
                    "the number of target identity fields."
                )

            if validation_error:

                st.session_state.manual_error = [
                    validation_error
                ]

                st.session_state.manual_success = None

            else:

                candidate = copy.deepcopy(
                    current_model
                )

                candidate.setdefault(
                    "foreign_keys",
                    [],
                )

                foreign_key_name = (
                    f"FK_{fk_source_entity}_{fk_target_entity}"
                )

                candidate["foreign_keys"].append(
                    {
                        "name": foreign_key_name,
                        "source": {
                            "entity": fk_source_entity,
                            "fields": fk_source_selected_fields,
                        },
                        "target": {
                            "entity": fk_target_entity,
                            "fields": fk_target_identity_fields,
                        },
                    }
                )

                errors = forge_backend.validate_authoring_model(
                    candidate
                )

                if errors:

                    st.session_state.manual_error = errors
                    st.session_state.manual_success = None

                else:

                    try:

                        save_specification(
                            candidate
                        )

                    except Exception as exc:

                        st.session_state.manual_error = [
                            "Foreign key was validated but could not be saved: "
                            f"{exc}"
                        ]

                        st.session_state.manual_success = None

                    else:

                        st.session_state.model = candidate

                        st.session_state.manual_error = []

                        st.session_state.manual_success = (
                            f"Foreign key **{foreign_key_name}** "
                            "added, validated, and saved."
                        )

                        st.session_state.adding_foreign_key = False

            st.rerun()


# ---------------------------------------------------------------------------
# EXISTING FOREIGN KEYS
# ---------------------------------------------------------------------------

for index, foreign_key in enumerate(
    foreign_keys
):

    foreign_key_name = foreign_key.get(
        "name",
        "?",
    )

    source = foreign_key.get(
        "source",
        {},
    )

    target = foreign_key.get(
        "target",
        {},
    )

    source_entity_name = source.get(
        "entity",
        "?",
    )

    source_fields = source.get(
        "fields",
        [],
    )

    target_entity_name = target.get(
        "entity",
        "?",
    )

    target_fields = target.get(
        "fields",
        [],
    )

    st.markdown(
        f"**{foreign_key_name}**"
    )

    st.caption(
        f"{source_entity_name}."
        f"{', '.join(source_fields)}"
        " → "
        f"{target_entity_name}."
        f"{', '.join(target_fields)}"
    )

    fk_edit_left, fk_edit_right = st.columns(2)

    with fk_edit_left:

        if st.button(
            "Edit foreign key",
            key=f"foreign_key_edit_{index}",
            use_container_width=True,
        ):

            st.session_state.editing_foreign_key = index
            st.session_state.adding_foreign_key = False

            st.rerun()

    with fk_edit_right:

        if st.button(
            "Delete foreign key",
            key=f"foreign_key_delete_{index}",
            use_container_width=True,
        ):

            candidate = copy.deepcopy(
                current_model
            )

            candidate.get(
                "foreign_keys",
                [],
            ).pop(index)

            errors = forge_backend.validate_authoring_model(
                candidate
            )

            if errors:

                st.session_state.manual_error = errors
                st.session_state.manual_success = None

            else:

                try:

                    save_specification(
                        candidate
                    )

                except Exception as exc:

                    st.session_state.manual_error = [
                        "Foreign key could not be deleted: "
                        f"{exc}"
                    ]

                    st.session_state.manual_success = None

                else:

                    st.session_state.model = candidate

                    st.session_state.manual_error = []

                    st.session_state.manual_success = (
                        "Foreign key deleted successfully."
                    )

            st.session_state.editing_foreign_key = None

            st.rerun()


    # -----------------------------------------------------------------------
    # EDIT FOREIGN KEY
    # -----------------------------------------------------------------------

    if st.session_state.get(
        "editing_foreign_key"
    ) == index:

        fk_edit_entity_names = [
            entity.get("name")
            for entity in entities
            if isinstance(entity, dict)
            and entity.get("name")
        ]

        edit_fk_source_entity = st.selectbox(
            "Source entity",
            fk_edit_entity_names,
            index=(
                fk_edit_entity_names.index(
                    source_entity_name
                )
                if source_entity_name
                in fk_edit_entity_names
                else 0
            ),
            key=f"edit_fk_source_entity_{index}",
        )

        edit_fk_source_entity_object = get_entity(
            current_model,
            edit_fk_source_entity,
        )

        edit_fk_source_fields = [
            field.get("name")
            for field in (
                edit_fk_source_entity_object or {}
            ).get(
                "fields",
                [],
            )
            if isinstance(field, dict)
            and field.get("name")
        ]

        edit_fk_source_selected_fields = st.multiselect(
            "Source fields",
            options=edit_fk_source_fields,
            default=[
                field_name
                for field_name in source_fields
                if field_name in edit_fk_source_fields
            ],
            key=f"edit_fk_source_fields_{index}",
            help=(
                "Select source fields in the same order as "
                "the target identity fields."
            ),
        )

        edit_fk_target_entity = st.selectbox(
            "Target entity",
            fk_edit_entity_names,
            index=(
                fk_edit_entity_names.index(
                    target_entity_name
                )
                if target_entity_name
                in fk_edit_entity_names
                else 0
            ),
            key=f"edit_fk_target_entity_{index}",
        )

        edit_fk_target_entity_object = get_entity(
            current_model,
            edit_fk_target_entity,
        )

        edit_fk_target_identity = (
            edit_fk_target_entity_object.get(
                "identity",
                {},
            )
            if edit_fk_target_entity_object
            else {}
        )

        edit_fk_target_identity_fields = (
            edit_fk_target_identity.get(
                "fields",
                [],
            )
            if isinstance(
                edit_fk_target_identity,
                dict,
            )
            else []
        )

        if edit_fk_target_identity_fields:

            st.markdown(
                "**Target identity**"
            )

            st.code(
                " + ".join(
                    edit_fk_target_identity_fields
                )
            )

        else:

            st.warning(
                f"Target entity **{edit_fk_target_entity}** "
                "does not define an identity."
            )

        fk_save_left, fk_save_middle = st.columns(2)

        with fk_save_left:

            save_foreign_key = st.button(
                "Save Foreign Key",
                key=f"save_foreign_key_{index}",
                type="primary",
                use_container_width=True,
            )

        with fk_save_middle:

            cancel_foreign_key = st.button(
                "Cancel",
                key=f"cancel_foreign_key_{index}",
                use_container_width=True,
            )

        if cancel_foreign_key:

            st.session_state.editing_foreign_key = None

            st.rerun()

        if save_foreign_key:

            candidate = copy.deepcopy(
                current_model
            )

            candidate_foreign_keys = candidate.get(
                "foreign_keys",
                [],
            )

            validation_error = None

            if not edit_fk_source_selected_fields:

                validation_error = (
                    "Select at least one source field."
                )

            elif not edit_fk_target_identity_fields:

                validation_error = (
                    f"Target entity **{edit_fk_target_entity}** "
                    "must define an identity."
                )

            elif len(
                edit_fk_source_selected_fields
            ) != len(
                edit_fk_target_identity_fields
            ):

                validation_error = (
                    "The number of source fields must match "
                    "the number of target identity fields."
                )

            if validation_error:

                st.session_state.manual_error = [
                    validation_error
                ]

                st.session_state.manual_success = None

            else:

                candidate_foreign_keys[index] = {
                    "name": (
                        f"FK_{edit_fk_source_entity}_"
                        f"{edit_fk_target_entity}"
                    ),
                    "source": {
                        "entity": edit_fk_source_entity,
                        "fields": edit_fk_source_selected_fields,
                    },
                    "target": {
                        "entity": edit_fk_target_entity,
                        "fields": edit_fk_target_identity_fields,
                    },
                }

                errors = forge_backend.validate_authoring_model(
                    candidate
                )

                if errors:

                    st.session_state.manual_error = errors
                    st.session_state.manual_success = None

                else:

                    try:

                        save_specification(
                            candidate
                        )

                    except Exception as exc:

                        st.session_state.manual_error = [
                            "Foreign key was validated but could not be saved: "
                            f"{exc}"
                        ]

                        st.session_state.manual_success = None

                    else:

                        st.session_state.model = candidate

                        st.session_state.manual_error = []

                        st.session_state.manual_success = (
                            f"Foreign key **"
                            f"FK_{edit_fk_source_entity}_"
                            f"{edit_fk_target_entity}"
                            "** updated, validated, and saved."
                        )

                        st.session_state.editing_foreign_key = None

            st.rerun()



    # =========================================================================
    # CONSTRAINTS
    # =========================================================================

    st.divider()
    st.subheader("✓ Constraints")

    entity_list = entity_names(current_model)

    if st.button(
        "➕ Add constraint",
        key="add_constraint_button",
        use_container_width=True,
    ):
        st.session_state.adding_constraint = True
        st.session_state.editing_constraint = None
        st.rerun()

    # -------------------------------------------------------------------------
    # ADD CONSTRAINT
    # -------------------------------------------------------------------------

    if st.session_state.get("adding_constraint", False):

        if not entity_list:
            st.warning("Add an entity before creating a constraint.")

        else:
            st.markdown("**New constraint**")

            constraint_entity = st.selectbox(
                "Entity",
                entity_list,
                key="new_constraint_entity",
            )

            constraint_entity_object = get_entity(
                current_model,
                constraint_entity,
            )

            constraint_fields = [
                field["name"]
                for field in (constraint_entity_object or {}).get(
                    "fields",
                    [],
                )
            ]

            if not constraint_fields:
                st.warning(
                    f"Entity `{constraint_entity}` has no fields. "
                    "Add a field before creating a constraint."
                )

            else:
                constraint_field = st.selectbox(
                    "Field",
                    constraint_fields,
                    key="new_constraint_field",
                )

                selected_constraint_field = get_field(
                    current_model,
                    f"{constraint_entity}.{constraint_field}",
                )

                field_type = (
                    selected_constraint_field.get("type")
                    if selected_constraint_field
                    else None
                )

                generation = (
                    selected_constraint_field.get("generation", {})
                    if selected_constraint_field
                    else {}
                )

                is_categorical = field_type == "CATEGORICAL" or (
                    isinstance(generation, dict)
                    and generation.get("distribution") == "CATEGORICAL"
                )

                constraint_operators = (
                    ["==", "!="] if is_categorical else SUPPORTED_OPERATORS
                )

                constraint_operator = st.selectbox(
                    "Operator",
                    constraint_operators,
                    key="new_constraint_operator",
                )

                # -------------------------------------------------------------
                # VALUE
                # -------------------------------------------------------------

                if field_type == "INTEGER":

                    constraint_value = st.number_input(
                        "Value",
                        value=0,
                        step=1,
                        format="%d",
                        key="new_constraint_value_integer",
                    )

                elif field_type == "DECIMAL":

                    constraint_value = st.number_input(
                        "Value",
                        value=0.0,
                        step=0.1,
                        key="new_constraint_value_decimal",
                    )

                elif field_type == "BOOLEAN":

                    constraint_value = st.selectbox(
                        "Value",
                        [True, False],
                        key="new_constraint_value_boolean",
                    )

                else:

                    generation = (
                        selected_constraint_field.get("generation", {})
                        if selected_constraint_field
                        else {}
                    )

                    is_categorical = field_type == "CATEGORICAL" or (
                        isinstance(generation, dict)
                        and generation.get("distribution") == "CATEGORICAL"
                    )

                    if is_categorical:

                        parameters = (
                            generation.get(
                                "parameters",
                                {},
                            )
                            if isinstance(generation, dict)
                            else {}
                        )

                        categorical_values = (
                            parameters.get(
                                "values",
                                [],
                            )
                            if isinstance(parameters, dict)
                            else []
                        )

                        if isinstance(categorical_values, list) and categorical_values:

                            constraint_value = st.selectbox(
                                "Value",
                                categorical_values,
                                key="new_constraint_value_categorical",
                            )

                        else:

                            st.warning(
                                "This categorical field has no declared "
                                "vocabulary. Add categorical values to the "
                                "field before creating a constraint."
                            )

                            constraint_value = None

                    else:

                        constraint_value = st.text_input(
                            "Value",
                            key="new_constraint_value_text",
                        )

                add_col, cancel_col = st.columns(2)

                with add_col:
                    add_constraint = st.button(
                        "Add Constraint",
                        type="primary",
                        use_container_width=True,
                        key="add_constraint_submit",
                    )

                with cancel_col:
                    cancel_constraint = st.button(
                        "Cancel",
                        use_container_width=True,
                        key="add_constraint_cancel",
                    )

                if cancel_constraint:
                    st.session_state.adding_constraint = False
                    st.rerun()

                if add_constraint:

                    candidate = copy.deepcopy(current_model)

                    candidate["constraints"].append(
                        {
                            "entity": constraint_entity,
                            "field": constraint_field,
                            "operator": constraint_operator,
                            "value": constraint_value,
                        }
                    )

                    errors = forge_backend.validate_authoring_model(candidate)

                    if errors:

                        st.session_state.manual_error = errors
                        st.session_state.manual_success = None

                    else:

                        try:
                            save_specification(candidate)

                        except Exception as exc:

                            st.session_state.manual_error = [
                                "Constraint was validated but could not "
                                f"be saved: {exc}"
                            ]

                        else:

                            st.session_state.model = candidate
                            st.session_state.adding_constraint = False
                            st.session_state.manual_success = (
                                "Constraint added, validated, and saved."
                            )

                    st.rerun()

    # -------------------------------------------------------------------------
    # EXISTING CONSTRAINTS
    # -------------------------------------------------------------------------

    if not constraints:
        st.caption("No constraints defined.")

    for index, constraint in enumerate(constraints):

        with st.container(border=True):

            st.markdown(
                f"**{constraint.get('entity', '?')}."
                f"{constraint.get('field', '?')}** "
                f"`{constraint.get('operator', '?')}` "
                f"**{constraint.get('value', '?')}**"
            )

            edit_col, delete_col = st.columns(2)

            with edit_col:

                if st.button(
                    "Edit constraint",
                    key=f"constraint_edit_{index}",
                    use_container_width=True,
                ):
                    st.session_state.editing_constraint = index
                    st.session_state.adding_constraint = False
                    st.rerun()

            with delete_col:

                if st.button(
                    "Delete constraint",
                    key=f"constraint_delete_{index}",
                    use_container_width=True,
                ):

                    candidate = copy.deepcopy(current_model)

                    candidate["constraints"].pop(index)

                    errors = forge_backend.validate_authoring_model(candidate)

                    if errors:

                        st.session_state.manual_error = errors
                        st.session_state.manual_success = None

                    else:

                        try:
                            save_specification(candidate)

                        except Exception as exc:

                            st.session_state.manual_error = [
                                "Constraint was validated but could not "
                                f"be deleted: {exc}"
                            ]

                        else:

                            st.session_state.model = candidate
                            st.session_state.editing_constraint = None
                            st.session_state.manual_success = (
                                "Constraint deleted, validated, and saved."
                            )

                    st.rerun()

    # -------------------------------------------------------------------------
    # EDIT CONSTRAINT
    # -------------------------------------------------------------------------

    if st.session_state.editing_constraint is not None:

        index = st.session_state.editing_constraint

        if 0 <= index < len(constraints):

            constraint = constraints[index]

            entity_list = entity_names(current_model)

            current_entity = constraint.get("entity", "")

            with st.container(border=True):

                st.markdown("**Edit constraint**")

                constraint_entity = st.selectbox(
                    "Entity",
                    entity_list,
                    index=(
                        entity_list.index(current_entity)
                        if current_entity in entity_list
                        else 0
                    ),
                    key=f"edit_constraint_entity_{index}",
                )

                constraint_entity_object = get_entity(
                    current_model,
                    constraint_entity,
                )

                constraint_fields = [
                    field["name"]
                    for field in (constraint_entity_object or {}).get(
                        "fields",
                        [],
                    )
                ]

                current_field = constraint.get("field", "")

                constraint_field = st.selectbox(
                    "Field",
                    constraint_fields,
                    index=(
                        constraint_fields.index(current_field)
                        if current_field in constraint_fields
                        else 0
                    ),
                    key=f"edit_constraint_field_{index}",
                )

                selected_constraint_field = get_field(
                    current_model,
                    f"{constraint_entity}.{constraint_field}",
                )

                current_operator = constraint.get(
                    "operator",
                    ">=",
                )

                field_type = (
                    selected_constraint_field.get("type")
                    if selected_constraint_field
                    else None
                )

                generation = (
                    selected_constraint_field.get("generation", {})
                    if selected_constraint_field
                    else {}
                )

                is_categorical = field_type == "CATEGORICAL" or (
                    isinstance(generation, dict)
                    and generation.get("distribution") == "CATEGORICAL"
                )

                constraint_operators = (
                    ["==", "!="] if is_categorical else SUPPORTED_OPERATORS
                )

                constraint_operator = st.selectbox(
                    "Operator",
                    constraint_operators,
                    index=(
                        constraint_operators.index(current_operator)
                        if current_operator in constraint_operators
                        else 0
                    ),
                    key=f"edit_constraint_operator_{index}",
                )

                field_type = (
                    selected_constraint_field.get("type")
                    if selected_constraint_field
                    else None
                )

                current_value = constraint.get("value")

                if field_type == "INTEGER":

                    constraint_value = st.number_input(
                        "Value",
                        value=(
                            int(current_value)
                            if isinstance(current_value, int)
                            and not isinstance(current_value, bool)
                            else 0
                        ),
                        step=1,
                        format="%d",
                        key=f"edit_constraint_value_integer_{index}",
                    )

                elif field_type == "DECIMAL":

                    constraint_value = st.number_input(
                        "Value",
                        value=(
                            float(current_value)
                            if isinstance(current_value, (int, float))
                            and not isinstance(current_value, bool)
                            else 0.0
                        ),
                        step=0.1,
                        key=f"edit_constraint_value_decimal_{index}",
                    )

                elif field_type == "BOOLEAN":

                    constraint_value = st.selectbox(
                        "Value",
                        [True, False],
                        index=(0 if current_value is True else 1),
                        key=f"edit_constraint_value_boolean_{index}",
                    )

                else:

                    generation = (
                        selected_constraint_field.get("generation", {})
                        if selected_constraint_field
                        else {}
                    )

                    is_categorical = field_type == "CATEGORICAL" or (
                        isinstance(generation, dict)
                        and generation.get("distribution") == "CATEGORICAL"
                    )

                    if is_categorical:

                        parameters = (
                            generation.get(
                                "parameters",
                                {},
                            )
                            if isinstance(generation, dict)
                            else {}
                        )

                        categorical_values = (
                            parameters.get(
                                "values",
                                [],
                            )
                            if isinstance(parameters, dict)
                            else []
                        )

                        if isinstance(categorical_values, list) and categorical_values:

                            if current_value in categorical_values:
                                categorical_index = categorical_values.index(
                                    current_value
                                )
                            else:
                                categorical_index = 0

                                st.warning(
                                    f"Current constraint value "
                                    f"`{current_value}` is not in the "
                                    "field's declared vocabulary. "
                                    "Select a valid value before saving."
                                )

                            constraint_value = st.selectbox(
                                "Value",
                                categorical_values,
                                index=categorical_index,
                                key=f"edit_constraint_value_categorical_{index}",
                            )

                        else:

                            st.warning(
                                "This categorical field has no declared "
                                "vocabulary. Add categorical values to the "
                                "field before editing this constraint."
                            )

                            constraint_value = None

                    else:

                        constraint_value = st.text_input(
                            "Value",
                            value=("" if current_value is None else str(current_value)),
                            key=f"edit_constraint_value_text_{index}",
                        )

                save_col, cancel_col = st.columns(2)

                with save_col:

                    save_constraint = st.button(
                        "Save",
                        type="primary",
                        use_container_width=True,
                        key=f"save_constraint_{index}",
                    )

                with cancel_col:

                    cancel_constraint = st.button(
                        "Cancel",
                        use_container_width=True,
                        key=f"cancel_constraint_{index}",
                    )

                if cancel_constraint:

                    st.session_state.editing_constraint = None
                    st.rerun()

                if save_constraint:

                    candidate = copy.deepcopy(current_model)

                    candidate["constraints"][index] = {
                        "entity": constraint_entity,
                        "field": constraint_field,
                        "operator": constraint_operator,
                        "value": constraint_value,
                    }

                    errors = forge_backend.validate_authoring_model(candidate)

                    if errors:

                        st.session_state.manual_error = errors
                        st.session_state.manual_success = None

                    else:

                        try:
                            save_specification(candidate)

                        except Exception as exc:

                            st.session_state.manual_error = [
                                "Constraint was validated but could not "
                                f"be saved: {exc}"
                            ]

                        else:

                            st.session_state.model = candidate
                            st.session_state.editing_constraint = None
                            st.session_state.manual_success = (
                                "Constraint updated, validated, and saved."
                            )

                    st.rerun()

    # =========================================================================
    # DEPENDENCIES
    # =========================================================================

    st.divider()

    st.subheader("↳ Dependencies")

    if not dependencies:

        st.caption("No dependencies defined.")

    for dependency in dependencies:

        st.markdown(
            f"• **{dependency.get('type', '?')}** "
            f"**{dependency.get('target', '?')}** ← "
            f"{', '.join(dependency.get('source_fields', []))}"
        )


# ============================================================================
# CHAT INPUT
# ============================================================================

user_request = st.chat_input("Describe the next change to your data model...")

if user_request:

    user_request = user_request.strip()

    if user_request:

        st.session_state.conversation.append(
            {
                "role": "user",
                "content": user_request,
            }
        )

        try:

            system_prompt = forge_backend.build_system_prompt()

            with st.spinner("FORGE assistant is reasoning..."):

                raw_response = forge_backend.call_ollama(
                    system_prompt,
                    user_request,
                    st.session_state.model,
                )

            st.session_state.last_raw_response = raw_response

            response = forge_backend.parse_llm_response(raw_response)

            status = response.get("status")

            message = response.get(
                "message",
                "",
            )

            operations = response.get(
                "operations",
                [],
            )

            if status == "PROPOSE":

                if not operations:

                    st.session_state.conversation.append(
                        {
                            "role": "assistant",
                            "content": message or "No model change is required.",
                        }
                    )

                else:

                    candidate, errors = build_candidate(
                        st.session_state.model,
                        operations,
                    )

                    if errors:

                        st.session_state.pending_proposal = None

                        st.session_state.pending_candidate = None

                        st.session_state.pending_errors = errors

                        st.session_state.conversation.append(
                            {
                                "role": "error",
                                "content": (
                                    "FORGE rejected the "
                                    "proposed changes:\n\n"
                                    + "\n".join(f"- {error}" for error in errors)
                                ),
                            }
                        )

                    else:

                        st.session_state.pending_proposal = response

                        st.session_state.pending_candidate = candidate

                        st.session_state.pending_errors = []

                        st.session_state.conversation.append(
                            {
                                "role": "assistant",
                                "content": message,
                            }
                        )

            elif status in {
                "CLARIFY",
                "UNSUPPORTED",
            }:

                st.session_state.pending_proposal = None

                st.session_state.pending_candidate = None

                st.session_state.pending_errors = []

                st.session_state.conversation.append(
                    {
                        "role": "assistant",
                        "content": message,
                    }
                )

            else:

                st.session_state.conversation.append(
                    {
                        "role": "error",
                        "content": ("Unexpected LLM response status: " f"{status}"),
                    }
                )

        except Exception as exc:

            st.session_state.conversation.append(
                {
                    "role": "error",
                    "content": ("LLM authoring error:\n\n" f"{exc}"),
                }
            )

        st.rerun()


# ============================================================================
# MODEL STATUS
# ============================================================================

st.divider()

st.subheader("⚙️ Model status")

current_model = st.session_state.model

current_authoring_errors = authoring_errors(current_model)

current_generation_errors = generation_errors(current_model)

status_left, status_right = st.columns(2)

with status_left:

    if current_authoring_errors:

        st.error(f"Authoring validation: " f"{len(current_authoring_errors)} issue(s)")

        with st.expander("View authoring issues"):

            for error in current_authoring_errors:

                st.write(f"• {error}")

    else:

        st.success("Authoring validation: PASS")


with status_right:

    if current_generation_errors:

        st.warning(
            f"Generation readiness: " f"{len(current_generation_errors)} issue(s)"
        )

        with st.expander("View generation configuration issues"):

            for error in current_generation_errors:

                st.write(f"• {error}")

    else:

        st.success("Generation readiness: PASS")


# ============================================================================
# TECHNICAL JSON
# ============================================================================

with st.expander("Technical specification JSON"):

    st.json(forge_backend.model_to_specification(st.session_state.model))


# ============================================================================
# RAW LLM RESPONSE
# ============================================================================

if st.session_state.last_raw_response:

    with st.expander("Last raw LLM response"):

        st.code(
            st.session_state.last_raw_response,
            language="json",
        )
