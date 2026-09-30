"""
============================================================================
FORGE — Framework for Observed Rules, Generation & Engineered Data
============================================================================

File: ollama_ai_provider.py
Purpose: Provides FORGE AI capabilities through a local Ollama instance.

Author: Ranjoy Sen
Email: ranjoy.sen@collins.com

============================================================================
"""

from __future__ import annotations

import json
from urllib.error import URLError
from urllib.request import Request, urlopen

from app.core.ai_settings import AIConfiguration
from app.prompts.data_model_prompt import DATA_MODEL_PROPOSAL_SYSTEM_PROMPT
from app.prompts.constraint_proposal_prompt import (
    CONSTRAINT_PROPOSAL_SYSTEM_PROMPT,
)
from app.prompts.field_proposal_prompt import FIELD_PROPOSAL_SYSTEM_PROMPT
from app.prompts.identity_proposal_prompt import IDENTITY_PROPOSAL_SYSTEM_PROMPT
from app.prompts.semantic_prompt import (
    SEMANTIC_GENERATION_SYSTEM_PROMPT,
    SEMANTIC_PREVIEW_SYSTEM_PROMPT,
)
from app.interfaces.ai_provider import (
    AIConstraintProposal,
    AIForeignKeyProposal,
    AIDataModelProposal,
    AIFieldProposal,
    AIIdentityProposal,
    AIRelationshipProposal,
    AISemanticPreview,
    AIProvider,
    AIProviderStatus,
)
from app.prompts.foreign_key_proposal_prompt import FORGE_FOREIGN_KEY_PROPOSAL_SYSTEM_PROMPT


class OllamaAIProvider(AIProvider):
    """Provides FORGE AI capabilities through Ollama."""

    def __init__(self, configuration: AIConfiguration) -> None:
        self._base_url = configuration.base_url.rstrip("/")
        self._model = configuration.model
        self._capability_timeout_seconds = configuration.capability_timeout_seconds
        self._generation_timeout_seconds = configuration.generation_timeout_seconds

    def get_status(self) -> AIProviderStatus:
        """Return the current Ollama availability status."""

        try:
            models = self._get_models()
        except (OSError, URLError):
            return AIProviderStatus(
                available=False,
                provider="ollama",
                mode="offline",
                model=self._model,
                message="FORGE AI is currently unavailable.",
            )

        installed_models = {
            model.get("name")
            for model in models
            if model.get("name")
        }

        if self._model not in installed_models:
            return AIProviderStatus(
                available=False,
                provider="ollama",
                mode="offline",
                model=self._model,
                message=(
                    f"FORGE AI model '{self._model}' is not available."
                ),
            )

        return AIProviderStatus(
            available=True,
            provider="ollama",
            mode="offline",
            model=self._model,
            message="FORGE AI is available.",
        )

    def suggest_data_model(
        self,
        prompt: str,
    ) -> AIDataModelProposal:
        """Generate a structured Data Model proposal from user intent."""

        system_prompt = DATA_MODEL_PROPOSAL_SYSTEM_PROMPT

        request_payload = {
            "model": self._model,
            "messages": [
                {
                    "role": "system",
                    "content": system_prompt,
                },
                {
                    "role": "user",
                    "content": prompt,
                },
            ],
            "stream": False,
            "format": {
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                    },
                    "description": {
                        "type": "string",
                    },
                    "suggested_tags": {
                        "type": "array",
                        "items": {
                            "type": "string",
                        },
                    },
                    "reasoning": {
                        "type": "string",
                    },
                },
                "required": [
                    "name",
                    "description",
                    "suggested_tags",
                    "reasoning",
                ],
            },
        }

        request = Request(
            f"{self._base_url}/api/chat",
            data=json.dumps(request_payload).encode("utf-8"),
            headers={
                "Accept": "application/json",
                "Content-Type": "application/json",
            },
            method="POST",
        )

        try:
            with urlopen(
                request,
                timeout=self._generation_timeout_seconds,
            ) as response:
                payload = json.loads(
                    response.read().decode("utf-8"),
                )
        except (OSError, URLError) as exc:
            raise RuntimeError(
                "FORGE AI could not reach the configured Ollama provider.",
            ) from exc

        message = payload.get("message")

        if not isinstance(message, dict):
            raise RuntimeError(
                "FORGE AI returned an invalid chat response.",
            )

        raw_response = message.get("content")

        if not isinstance(raw_response, str) or not raw_response.strip():
            raise RuntimeError(
                "FORGE AI returned an empty proposal.",
            )

        try:
            proposal = json.loads(raw_response)
        except json.JSONDecodeError as exc:
            raise RuntimeError(
                "FORGE AI returned an invalid structured proposal.",
            ) from exc

        if not isinstance(proposal, dict):
            raise RuntimeError(
                "FORGE AI returned an invalid proposal structure.",
            )

        name = proposal.get("name")
        description = proposal.get("description")
        suggested_tags = proposal.get("suggested_tags")
        reasoning = proposal.get("reasoning")

        if not isinstance(name, str) or not name.strip():
            raise RuntimeError(
                "FORGE AI proposal is missing a valid name.",
            )

        if not isinstance(description, str):
            raise RuntimeError(
                "FORGE AI proposal is missing a valid description.",
            )

        if not isinstance(suggested_tags, list):
            raise RuntimeError(
                "FORGE AI proposal is missing valid suggested tags.",
            )

        if not all(
            isinstance(tag, str) and tag.strip()
            for tag in suggested_tags
        ):
            raise RuntimeError(
                "FORGE AI proposal contains invalid suggested tags.",
            )

        if not isinstance(reasoning, str):
            raise RuntimeError(
                "FORGE AI proposal is missing valid reasoning.",
            )

        return AIDataModelProposal(
            name=name.strip(),
            description=description.strip(),
            suggested_tags=[
                tag.strip()
                for tag in suggested_tags
            ],
            reasoning=reasoning.strip(),
        )

    def propose_identity(
        self,
        mode: str,
        entity_name: str,
        fields: list[dict[str, object]],
        request: str,
        existing_identity: dict[str, object] | None = None,
    ) -> AIIdentityProposal:
        """Generate a structured FORGE entity identity proposal."""

        normalized_mode = mode.strip().upper()

        if normalized_mode not in {"CREATE", "EDIT"}:
            raise ValueError(
                "Identity proposal mode must be CREATE or EDIT.",
            )

        normalized_entity_name = entity_name.strip()

        if not normalized_entity_name:
            raise ValueError(
                "Entity name must not be empty.",
            )

        if not fields:
            raise ValueError(
                "At least one entity field is required.",
            )

        normalized_request = request.strip()

        if not normalized_request:
            raise ValueError(
                "Identity proposal request must not be empty.",
            )

        if normalized_mode == "EDIT" and existing_identity is None:
            raise ValueError(
                "Existing identity is required in EDIT mode.",
            )

        payload = {
            "mode": normalized_mode,
            "entity_name": normalized_entity_name,
            "fields": fields,
            "request": normalized_request,
            "existing_identity": existing_identity,
        }

        request_payload = {
            "model": self._model,
            "messages": [
                {
                    "role": "system",
                    "content": IDENTITY_PROPOSAL_SYSTEM_PROMPT,
                },
                {
                    "role": "user",
                    "content": json.dumps(payload),
                },
            ],
            "stream": False,
            "format": {
                "type": "object",
                "properties": {
                    "status": {
                        "type": "string",
                        "enum": [
                            "PROPOSE",
                            "CLARIFY",
                            "UNSUPPORTED",
                        ],
                    },
                    "message": {
                        "type": "string",
                    },
                    "proposal": {
                        "type": [
                            "object",
                            "null",
                        ],
                        "properties": {
                            "fields": {
                                "type": "array",
                                "items": {
                                    "type": "string",
                                },
                            },
                        },
                        "required": [
                            "fields",
                        ],
                        "additionalProperties": False,
                    },
                },
                "required": [
                    "status",
                    "message",
                    "proposal",
                ],
                "additionalProperties": False,
            },
        }

        provider_request = Request(
            f"{self._base_url}/api/chat",
            data=json.dumps(request_payload).encode("utf-8"),
            headers={
                "Accept": "application/json",
                "Content-Type": "application/json",
            },
            method="POST",
        )

        try:
            with urlopen(
                provider_request,
                timeout=self._generation_timeout_seconds,
            ) as response:
                provider_response = json.loads(
                    response.read().decode("utf-8"),
                )
        except (OSError, URLError) as exc:
            raise RuntimeError(
                "FORGE AI could not reach the configured Ollama provider.",
            ) from exc

        message = provider_response.get("message")

        if not isinstance(message, dict):
            raise RuntimeError(
                "FORGE AI returned an invalid chat response.",
            )

        raw_response = message.get("content")

        if not isinstance(raw_response, str) or not raw_response.strip():
            raise RuntimeError(
                "FORGE AI returned an empty identity proposal.",
            )

        try:
            proposal_response = json.loads(raw_response)
        except json.JSONDecodeError as exc:
            raise RuntimeError(
                "FORGE AI returned an invalid structured identity proposal.",
            ) from exc

        if not isinstance(proposal_response, dict):
            raise RuntimeError(
                "FORGE AI returned an invalid identity proposal structure.",
            )

        status = proposal_response.get("status")
        response_message = proposal_response.get("message")
        proposal = proposal_response.get("proposal")

        if status not in {
            "PROPOSE",
            "CLARIFY",
            "UNSUPPORTED",
        }:
            raise RuntimeError(
                "FORGE AI identity proposal returned an invalid status.",
            )

        if (
            not isinstance(response_message, str)
            or not response_message.strip()
        ):
            raise RuntimeError(
                "FORGE AI identity proposal returned an invalid message.",
            )

        if status == "PROPOSE":
            if not isinstance(proposal, dict):
                raise RuntimeError(
                    "FORGE AI identity proposal is missing proposal data.",
                )

            proposed_fields = proposal.get("fields")

            if not isinstance(proposed_fields, list):
                raise RuntimeError(
                    "FORGE AI identity proposal fields must be a list.",
                )

            available_fields = {
                field.get("name")
                for field in fields
                if isinstance(field, dict)
            }

            if not proposed_fields:
                raise RuntimeError(
                    "FORGE AI identity proposal must contain at least "
                    "one field.",
                )

            if any(
                not isinstance(field, str)
                or field not in available_fields
                for field in proposed_fields
            ):
                raise RuntimeError(
                    "FORGE AI identity proposal contains a field "
                    "that does not exist on the entity.",
                )

            if len(proposed_fields) != len(set(proposed_fields)):
                raise RuntimeError(
                    "FORGE AI identity proposal contains duplicate fields.",
                )

            proposal = {
                "fields": proposed_fields,
            }

        else:
            proposal = None

        return AIIdentityProposal(
            status=status,
            message=response_message.strip(),
            proposal=proposal,
        )

    def propose_relationship(
        self,
        mode: str,
        entities: list[dict[str, object]],
        request: str,
        existing_relationship: dict[str, object] | None = None,
    ) -> AIRelationshipProposal:
        """Generate a structured FORGE relationship proposal."""

        normalized_mode = mode.strip().upper()
        normalized_request = request.strip()

        if normalized_mode not in {"CREATE", "EDIT"}:
            raise ValueError(
                "Relationship proposal mode must be CREATE or EDIT.",
            )

        if len(entities) < 2:
            raise ValueError(
                "At least two entities are required for a relationship proposal.",
            )

        if not normalized_request:
            raise ValueError(
                "Relationship proposal request must not be empty.",
            )

        if normalized_mode == "EDIT" and existing_relationship is None:
            raise ValueError(
                "Existing relationship is required in EDIT mode.",
            )

        payload = {
            "mode": normalized_mode,
            "entities": entities,
            "request": normalized_request,
            "existing_relationship": existing_relationship,
        }

        request_payload = {
            "model": self._model,
            "messages": [
                {
                    "role": "system",
                    "content": RELATIONSHIP_PROPOSAL_SYSTEM_PROMPT,
                },
                {
                    "role": "user",
                    "content": json.dumps(
                        payload,
                        ensure_ascii=False,
                    ),
                },
            ],
            "stream": False,
            "format": {
                "type": "object",
                "properties": {
                    "status": {
                        "type": "string",
                        "enum": [
                            "PROPOSE",
                            "CLARIFY",
                            "UNSUPPORTED",
                        ],
                    },
                    "message": {
                        "type": "string",
                    },
                    "proposal": {
                        "type": [
                            "object",
                            "null",
                        ],
                        "properties": {
                            "source_entity": {"type": "string"},
                            "source_field": {"type": "string"},
                            "target_entity": {"type": "string"},
                            "target_field": {"type": "string"},
                            "type": {
                                "type": "string",
                                "enum": [
                                    "ONE_TO_ONE",
                                    "ONE_TO_MANY",
                                    "MANY_TO_ONE",
                                    "MANY_TO_MANY",
                                ],
                            },
                            "source_participation": {
                                "type": "string",
                                "enum": [
                                    "MANDATORY",
                                    "OPTIONAL",
                                ],
                            },
                            "target_participation": {
                                "type": "string",
                                "enum": [
                                    "MANDATORY",
                                    "OPTIONAL",
                                ],
                            },
                        },
                        "required": [
                            "source_entity",
                            "source_field",
                            "target_entity",
                            "target_field",
                            "type",
                            "source_participation",
                            "target_participation",
                        ],
                        "additionalProperties": False,
                    },
                },
                "required": [
                    "status",
                    "message",
                    "proposal",
                ],
                "additionalProperties": False,
            },
        }

        provider_request = Request(
            f"{self._base_url}/api/chat",
            data=json.dumps(request_payload).encode("utf-8"),
            headers={
                "Accept": "application/json",
                "Content-Type": "application/json",
            },
            method="POST",
        )

        try:
            with urlopen(
                provider_request,
                timeout=self._generation_timeout_seconds,
            ) as response:
                provider_response = json.loads(
                    response.read().decode("utf-8"),
                )
        except (OSError, URLError) as exc:
            raise RuntimeError(
                "FORGE AI could not reach the configured Ollama provider.",
            ) from exc

        message = provider_response.get("message")

        if not isinstance(message, dict):
            raise RuntimeError(
                "FORGE AI returned an invalid chat response.",
            )

        raw_response = message.get("content")

        if not isinstance(raw_response, str) or not raw_response.strip():
            raise RuntimeError(
                "FORGE AI returned an empty relationship proposal.",
            )

        try:
            proposal_response = json.loads(raw_response)
        except json.JSONDecodeError as exc:
            raise RuntimeError(
                "FORGE AI returned an invalid structured relationship proposal.",
            ) from exc

        if not isinstance(proposal_response, dict):
            raise RuntimeError(
                "FORGE AI returned an invalid relationship proposal structure.",
            )

        proposal_status = proposal_response.get("status")
        response_message = proposal_response.get("message")
        proposal = proposal_response.get("proposal")

        if proposal_status not in {
            "PROPOSE",
            "CLARIFY",
            "UNSUPPORTED",
        }:
            raise RuntimeError(
                "FORGE AI relationship proposal returned an invalid status.",
            )

        if (
            not isinstance(response_message, str)
            or not response_message.strip()
        ):
            raise RuntimeError(
                "FORGE AI relationship proposal returned an invalid message.",
            )

        if proposal_status == "PROPOSE":
            if not isinstance(proposal, dict):
                raise RuntimeError(
                    "FORGE AI relationship proposal is missing proposal data.",
                )

            for field_name in (
                "source_entity",
                "source_field",
                "target_entity",
                "target_field",
            ):
                value = proposal.get(field_name)
                if not isinstance(value, str) or not value.strip():
                    raise RuntimeError(
                        f"FORGE AI relationship proposal contains "
                        f"an invalid {field_name}.",
                    )

            if proposal.get("type") not in {
                "ONE_TO_ONE",
                "ONE_TO_MANY",
                "MANY_TO_ONE",
                "MANY_TO_MANY",
            }:
                raise RuntimeError(
                    "FORGE AI relationship proposal contains "
                    "an invalid relationship type.",
                )

            if proposal.get("source_participation") not in {
                "MANDATORY",
                "OPTIONAL",
            }:
                raise RuntimeError(
                    "FORGE AI relationship proposal contains "
                    "invalid source participation.",
                )

            if proposal.get("target_participation") not in {
                "MANDATORY",
                "OPTIONAL",
            }:
                raise RuntimeError(
                    "FORGE AI relationship proposal contains "
                    "invalid target participation.",
                )

            available_entities = {
                entity.get("name")
                for entity in entities
                if isinstance(entity, dict)
            }

            source_entity = proposal["source_entity"]
            target_entity = proposal["target_entity"]

            if source_entity not in available_entities:
                raise RuntimeError(
                    "FORGE AI relationship proposal references "
                    "an unknown source entity.",
                )

            if target_entity not in available_entities:
                raise RuntimeError(
                    "FORGE AI relationship proposal references "
                    "an unknown target entity.",
                )

            entity_fields = {
                entity.get("name"): {
                    field.get("name")
                    for field in entity.get("fields", [])
                    if isinstance(field, dict)
                }
                for entity in entities
                if isinstance(entity, dict)
            }

            if proposal["source_field"] not in entity_fields.get(
                source_entity,
                set(),
            ):
                raise RuntimeError(
                    "FORGE AI relationship proposal references "
                    "an unknown source field.",
                )

            if proposal["target_field"] not in entity_fields.get(
                target_entity,
                set(),
            ):
                raise RuntimeError(
                    "FORGE AI relationship proposal references "
                    "an unknown target field.",
                )

            proposal = {
                "source_entity": source_entity,
                "source_field": proposal["source_field"],
                "target_entity": target_entity,
                "target_field": proposal["target_field"],
                "type": proposal["type"],
                "source_participation": proposal["source_participation"],
                "target_participation": proposal["target_participation"],
            }

        else:
            proposal = None

        return AIRelationshipProposal(
            status=proposal_status,
            message=response_message.strip(),
            proposal=proposal,
        )


    def propose_field(
        self,
        mode: str,
        entity_name: str,
        request: str,
        existing_field: dict[str, object] | None = None,
    ) -> AIFieldProposal:
        """Generate a structured FORGE field proposal."""

        normalized_mode = mode.strip().upper()
        normalized_entity_name = entity_name.strip()
        normalized_request = request.strip()

        if normalized_mode not in {"CREATE", "EDIT"}:
            raise ValueError(
                "Field proposal mode must be CREATE or EDIT.",
            )

        if not normalized_entity_name:
            raise ValueError(
                "Field proposal requires an entity name.",
            )

        if not normalized_request:
            raise ValueError(
                "Field proposal requires a user request.",
            )

        user_payload = {
            "mode": normalized_mode,
            "entity_name": normalized_entity_name,
            "request": normalized_request,
        }

        if normalized_mode == "EDIT":
            if not isinstance(existing_field, dict):
                raise ValueError(
                    "EDIT field proposals require an existing field.",
                )

            user_payload["existing_field"] = existing_field

        request_payload = {
            "model": self._model,
            "messages": [
                {
                    "role": "system",
                    "content": FIELD_PROPOSAL_SYSTEM_PROMPT,
                },
                {
                    "role": "user",
                    "content": json.dumps(
                        user_payload,
                        ensure_ascii=False,
                    ),
                },
            ],
            "stream": False,
            "format": {
                "type": "object",
                "properties": {
                    "status": {
                        "type": "string",
                        "enum": [
                            "PROPOSE",
                            "CLARIFY",
                            "UNSUPPORTED",
                        ],
                    },
                    "message": {
                        "type": "string",
                    },
                    "proposal": {
                        "type": [
                            "object",
                            "null",
                        ],
                        "properties": {
                            "name": {
                                "type": "string",
                            },
                            "type": {
                                "type": "string",
                                "enum": [
                                    "IDENTIFIER",
                                    "STRING",
                                    "INTEGER",
                                    "DECIMAL",
                                    "BOOLEAN",
                                    "CATEGORICAL",
                                ],
                            },
                            "identity": {
                                "type": [
                                    "object",
                                    "null",
                                ],
                                "properties": {
                                    "strategy": {
                                        "type": "string",
                                        "enum": [
                                            "SEQUENTIAL_ID",
                                        ],
                                    },
                                },
                                "required": [
                                    "strategy",
                                ],
                            },
                            "generation": {
                                "type": [
                                    "object",
                                    "null",
                                ],
                                "properties": {
                                    "strategy": {
                                        "type": [
                                            "string",
                                            "null",
                                        ],
                                    },
                                    "distribution": {
                                        "type": [
                                            "string",
                                            "null",
                                        ],
                                    },
                                    "generator": {
                                        "type": [
                                            "string",
                                            "null",
                                        ],
                                    },
                                    "parameters": {
                                        "type": [
                                            "object",
                                            "null",
                                        ],
                                    },
                                },
                            },
                        },
                        "required": [
                            "name",
                            "type",
                            "identity",
                            "generation",
                        ],
                    },
                },
                "required": [
                    "status",
                    "message",
                    "proposal",
                ],
            },
        }

        request = Request(
            f"{self._base_url}/api/chat",
            data=json.dumps(request_payload).encode("utf-8"),
            headers={
                "Accept": "application/json",
                "Content-Type": "application/json",
            },
            method="POST",
        )

        try:
            with urlopen(
                request,
                timeout=self._generation_timeout_seconds,
            ) as response:
                payload = json.loads(
                    response.read().decode("utf-8"),
                )
        except (OSError, URLError) as exc:
            raise RuntimeError(
                "FORGE AI could not reach the configured Ollama provider.",
            ) from exc

        message = payload.get("message")

        if not isinstance(message, dict):
            raise RuntimeError(
                "FORGE AI returned an invalid chat response.",
            )

        raw_response = message.get("content")

        if not isinstance(raw_response, str) or not raw_response.strip():
            raise RuntimeError(
                "FORGE AI returned an empty field proposal.",
            )

        try:
            proposal_response = json.loads(raw_response)
        except json.JSONDecodeError as exc:
            raise RuntimeError(
                "FORGE AI returned an invalid structured field proposal.",
            ) from exc

        if not isinstance(proposal_response, dict):
            raise RuntimeError(
                "FORGE AI returned an invalid field proposal structure.",
            )

        proposal_status = proposal_response.get("status")
        proposal_message = proposal_response.get("message")
        proposal = proposal_response.get("proposal")

        if proposal_status not in {
            "PROPOSE",
            "CLARIFY",
            "UNSUPPORTED",
        }:
            raise RuntimeError(
                "FORGE AI returned an invalid field proposal status.",
            )

        if (
            not isinstance(proposal_message, str)
            or not proposal_message.strip()
        ):
            raise RuntimeError(
                "FORGE AI field proposal is missing a valid message.",
            )

        if proposal_status != "PROPOSE":
            if proposal is not None:
                raise RuntimeError(
                    "FORGE AI returned a proposal for a non-proposal status.",
                )

            return AIFieldProposal(
                status=proposal_status,
                message=proposal_message.strip(),
                proposal=None,
            )

        if not isinstance(proposal, dict):
            raise RuntimeError(
                "FORGE AI PROPOSE response is missing a proposal.",
            )

        field_name = proposal.get("name")
        field_type = proposal.get("type")

        if not isinstance(field_name, str) or not field_name.strip():
            raise RuntimeError(
                "FORGE AI field proposal is missing a valid name.",
            )

        if field_type not in {
            "IDENTIFIER",
            "STRING",
            "INTEGER",
            "DECIMAL",
            "BOOLEAN",
            "CATEGORICAL",
        }:
            raise RuntimeError(
                "FORGE AI field proposal contains an unsupported field type.",
            )

        identity = proposal.get("identity")
        generation = proposal.get("generation")

        if identity is not None and not isinstance(identity, dict):
            raise RuntimeError(
                "FORGE AI field proposal contains invalid identity metadata.",
            )

        if generation is not None and not isinstance(generation, dict):
            raise RuntimeError(
                "FORGE AI field proposal contains invalid generation metadata.",
            )

        normalized_proposal = {
            "name": field_name.strip(),
            "type": field_type,
            "identity": identity,
            "generation": generation,
        }

        return AIFieldProposal(
            status="PROPOSE",
            message=proposal_message.strip(),
            proposal=normalized_proposal,
        )

    def preview_semantic_values(
        self,
        description: str,
    ) -> AISemanticPreview:
        """Generate representative semantic field values for preview."""

        normalized_description = description.strip()

        if not normalized_description:
            raise ValueError(
                "Semantic generation requires a description.",
            )

        system_prompt = SEMANTIC_PREVIEW_SYSTEM_PROMPT

        request_payload = {
            "model": self._model,
            "messages": [
                {
                    "role": "system",
                    "content": system_prompt,
                },
                {
                    "role": "user",
                    "content": normalized_description,
                },
            ],
            "stream": False,
            "format": {
                "type": "object",
                "properties": {
                    "status": {
                        "type": "string",
                        "enum": [
                            "PROPOSE",
                            "CLARIFY",
                            "UNSUPPORTED",
                        ],
                    },
                    "message": {
                        "type": "string",
                    },
                    "preview_values": {
                        "type": "array",
                        "items": {
                            "type": "string",
                        },
                    },
                },
                "required": [
                    "status",
                    "message",
                    "preview_values",
                ],
            },
        }

        request = Request(
            f"{self._base_url}/api/chat",
            data=json.dumps(request_payload).encode("utf-8"),
            headers={
                "Accept": "application/json",
                "Content-Type": "application/json",
            },
            method="POST",
        )

        try:
            with urlopen(
                request,
                timeout=self._generation_timeout_seconds,
            ) as response:
                payload = json.loads(
                    response.read().decode("utf-8"),
                )
        except (OSError, URLError) as exc:
            raise RuntimeError(
                "FORGE AI could not reach the configured Ollama provider.",
            ) from exc

        message = payload.get("message")

        if not isinstance(message, dict):
            raise RuntimeError(
                "FORGE AI returned an invalid chat response.",
            )

        raw_response = message.get("content")

        if not isinstance(raw_response, str) or not raw_response.strip():
            raise RuntimeError(
                "FORGE AI returned an empty semantic preview.",
            )

        try:
            preview = json.loads(raw_response)
        except json.JSONDecodeError as exc:
            raise RuntimeError(
                "FORGE AI returned an invalid semantic preview.",
            ) from exc

        if not isinstance(preview, dict):
            raise RuntimeError(
                "FORGE AI returned an invalid semantic preview structure.",
            )

        preview_status = preview.get("status")
        preview_message = preview.get("message")
        preview_values = preview.get("preview_values")

        if preview_status not in {
            "PROPOSE",
            "CLARIFY",
            "UNSUPPORTED",
        }:
            raise RuntimeError(
                "FORGE AI returned an invalid semantic preview status.",
            )

        if (
            not isinstance(preview_message, str)
            or not preview_message.strip()
        ):
            raise RuntimeError(
                "FORGE AI semantic preview is missing a valid message.",
            )

        if not isinstance(preview_values, list):
            raise RuntimeError(
                "FORGE AI semantic preview contains invalid values.",
            )

        if not all(
            isinstance(value, str) and value.strip()
            for value in preview_values
        ):
            raise RuntimeError(
                "FORGE AI semantic preview contains invalid STRING values.",
            )

        if preview_status == "PROPOSE":
            if len(preview_values) != 10:
                raise RuntimeError(
                    "FORGE AI semantic preview must contain exactly 10 values.",
                )
        elif preview_values:
            raise RuntimeError(
                "FORGE AI semantic preview must not contain values for "
                f"{preview_status}.",
            )

        return AISemanticPreview(
            status=preview_status,
            message=preview_message.strip(),
            preview_values=[
                value.strip()
                for value in preview_values
            ],
        )

    def generate_semantic_values(
        self,
        description: str,
        mode: str,
        count: int,
    ) -> list[str]:
        """Generate semantic STRING values for production generation."""

        normalized_description = description.strip()
        normalized_mode = mode.strip().upper()

        if not normalized_description:
            raise ValueError(
                "Semantic generation requires a description.",
            )

        if normalized_mode not in {"UNIQUE", "VOCABULARY"}:
            raise ValueError(
                "Semantic generation mode must be UNIQUE or VOCABULARY.",
            )

        if count <= 0:
            raise ValueError(
                "Semantic generation count must be greater than zero.",
            )

        collected_values: list[str] = []
        collected_set: set[str] = set()

        while len(collected_values) < count:
            remaining = count - len(collected_values)

            request_payload = {
                "model": self._model,
                "messages": [
                    {
                        "role": "system",
                        "content": SEMANTIC_GENERATION_SYSTEM_PROMPT,
                    },
                    {
                        "role": "user",
                        "content": (
                            f"Mode: {normalized_mode}\\n"
                            f"Count: {remaining}\\n"
                            f"Description: {normalized_description}"
                        ),
                    },
                ],
                "stream": False,
                "format": {
                    "type": "object",
                    "properties": {
                        "values": {
                            "type": "array",
                            "items": {
                                "type": "string",
                            },
                        },
                    },
                    "required": ["values"],
                },
            }

            request = Request(
                f"{self._base_url}/api/chat",
                data=json.dumps(request_payload).encode("utf-8"),
                headers={
                    "Accept": "application/json",
                    "Content-Type": "application/json",
                },
                method="POST",
            )

            try:
                with urlopen(
                    request,
                    timeout=self._generation_timeout_seconds,
                ) as response:
                    payload = json.loads(
                        response.read().decode("utf-8"),
                    )
            except (OSError, URLError) as exc:
                raise RuntimeError(
                    "FORGE AI could not reach the configured Ollama provider.",
                ) from exc

            message = payload.get("message")

            if not isinstance(message, dict):
                raise RuntimeError(
                    "FORGE AI returned an invalid chat response.",
                )

            raw_response = message.get("content")

            if not isinstance(raw_response, str) or not raw_response.strip():
                raise RuntimeError(
                    "FORGE AI returned an empty semantic generation response.",
                )

            try:
                result = json.loads(raw_response)
            except json.JSONDecodeError as exc:
                raise RuntimeError(
                    "FORGE AI returned invalid semantic generation JSON.",
                ) from exc

            if not isinstance(result, dict):
                raise RuntimeError(
                    "FORGE AI returned an invalid semantic generation structure.",
                )

            values = result.get("values")

            if not isinstance(values, list):
                raise RuntimeError(
                    "FORGE AI semantic generation did not return a values list.",
                )

            if not all(
                isinstance(value, str) and value.strip()
                for value in values
            ):
                raise RuntimeError(
                    "FORGE AI semantic generation returned invalid STRING values.",
                )

            for value in values:
                normalized_value = value.strip()

                if normalized_value not in collected_set:
                    collected_set.add(normalized_value)
                    collected_values.append(normalized_value)

                    if len(collected_values) == count:
                        break

            if not values:
                raise RuntimeError(
                    "FORGE AI semantic generation returned no usable values.",
                )

        normalized_values = collected_values[:count]

        return normalized_values

    def propose_foreign_key(
        self,
        mode: str,
        entities: list[dict[str, object]],
        request: str,
        existing_foreign_key: dict[str, object] | None = None,
    ) -> AIForeignKeyProposal:
        """Generate a structured FORGE foreign key proposal."""

        normalized_mode = mode.strip().upper()
        normalized_request = request.strip()

        if normalized_mode not in {"CREATE", "EDIT"}:
            raise ValueError(
                "Foreign key proposal mode must be CREATE or EDIT.",
            )

        if len(entities) < 2:
            raise ValueError(
                "At least two entities are required for a foreign key proposal.",
            )

        if not normalized_request:
            raise ValueError(
                "Foreign key proposal request must not be empty.",
            )

        if normalized_mode == "EDIT" and existing_foreign_key is None:
            raise ValueError(
                "Existing foreign key is required in EDIT mode.",
            )

        payload = {
            "mode": normalized_mode,
            "entities": entities,
            "request": normalized_request,
            "existing_foreign_key": existing_foreign_key,
        }

        request_payload = {
            "model": self._model,
            "messages": [
                {
                    "role": "system",
                    "content": FORGE_FOREIGN_KEY_PROPOSAL_SYSTEM_PROMPT,
                },
                {
                    "role": "user",
                    "content": json.dumps(
                        payload,
                        ensure_ascii=False,
                    ),
                },
            ],
            "stream": False,
            "format": {
                "type": "object",
                "properties": {
                    "status": {
                        "type": "string",
                        "enum": [
                            "PROPOSE",
                            "CLARIFY",
                            "UNSUPPORTED",
                        ],
                    },
                    "message": {
                        "type": "string",
                    },
                    "proposal": {
                        "type": [
                            "object",
                            "null",
                        ],
                        "properties": {
                            "source_entity": {
                                "type": "string",
                            },
                            "source_fields": {
                                "type": "array",
                                "items": {
                                    "type": "string",
                                },
                            },
                            "target_entity": {
                                "type": "string",
                            },
                        },
                        "required": [
                            "source_entity",
                            "source_fields",
                            "target_entity",
                        ],
                        "additionalProperties": False,
                    },
                },
                "required": [
                    "status",
                    "message",
                    "proposal",
                ],
                "additionalProperties": False,
            },
        }

        provider_request = Request(
            f"{self._base_url}/api/chat",
            data=json.dumps(request_payload).encode("utf-8"),
            headers={
                "Accept": "application/json",
                "Content-Type": "application/json",
            },
            method="POST",
        )

        try:
            with urlopen(
                provider_request,
                timeout=self._generation_timeout_seconds,
            ) as response:
                provider_response = json.loads(
                    response.read().decode("utf-8"),
                )
        except (OSError, URLError) as exc:
            raise RuntimeError(
                "FORGE AI could not reach the configured Ollama provider.",
            ) from exc

        message = provider_response.get("message")

        if not isinstance(message, dict):
            raise RuntimeError(
                "FORGE AI returned an invalid chat response.",
            )

        raw_response = message.get("content")

        if not isinstance(raw_response, str) or not raw_response.strip():
            raise RuntimeError(
                "FORGE AI returned an empty foreign key proposal.",
            )

        try:
            proposal_response = json.loads(raw_response)
        except json.JSONDecodeError as exc:
            raise RuntimeError(
                "FORGE AI returned an invalid structured foreign key proposal.",
            ) from exc

        if not isinstance(proposal_response, dict):
            raise RuntimeError(
                "FORGE AI returned an invalid foreign key proposal structure.",
            )

        proposal_status = proposal_response.get("status")
        response_message = proposal_response.get("message")
        proposal = proposal_response.get("proposal")

        if proposal_status not in {
            "PROPOSE",
            "CLARIFY",
            "UNSUPPORTED",
        }:
            raise RuntimeError(
                "FORGE AI foreign key proposal returned an invalid status.",
            )

        if (
            not isinstance(response_message, str)
            or not response_message.strip()
        ):
            raise RuntimeError(
                "FORGE AI foreign key proposal returned an invalid message.",
            )

        if proposal_status != "PROPOSE":
            if proposal is not None:
                raise RuntimeError(
                    "FORGE AI returned a proposal for a non-proposal status.",
                )

            return AIForeignKeyProposal(
                status=proposal_status,
                message=response_message.strip(),
                proposal=None,
            )

        if not isinstance(proposal, dict):
            raise RuntimeError(
                "FORGE AI foreign key proposal is missing proposal data.",
            )

        source_entity = proposal.get("source_entity")
        source_fields = proposal.get("source_fields")
        target_entity = proposal.get("target_entity")

        if (
            not isinstance(source_entity, str)
            or not source_entity.strip()
        ):
            raise RuntimeError(
                "FORGE AI foreign key proposal contains an invalid source entity.",
            )

        if (
            not isinstance(source_fields, list)
            or not source_fields
            or not all(
                isinstance(field, str) and field.strip()
                for field in source_fields
            )
        ):
            raise RuntimeError(
                "FORGE AI foreign key proposal contains invalid source fields.",
            )

        if (
            not isinstance(target_entity, str)
            or not target_entity.strip()
        ):
            raise RuntimeError(
                "FORGE AI foreign key proposal contains an invalid target entity.",
            )

        normalized_source_entity = source_entity.strip()
        normalized_source_fields = [
            field.strip()
            for field in source_fields
        ]
        normalized_target_entity = target_entity.strip()

        if normalized_source_entity == normalized_target_entity:
            raise RuntimeError(
                "FORGE AI foreign key proposal cannot reference the same entity.",
            )

        entity_by_name = {
            item.get("name"): item
            for item in entities
            if isinstance(item, dict) and item.get("name")
        }

        source_metadata = entity_by_name.get(normalized_source_entity)
        target_metadata = entity_by_name.get(normalized_target_entity)

        if source_metadata is None:
            raise RuntimeError(
                "FORGE AI foreign key proposal contains an unknown source entity.",
            )

        if target_metadata is None:
            raise RuntimeError(
                "FORGE AI foreign key proposal contains an unknown target entity.",
            )

        source_metadata_fields = {
            field.get("name")
            for field in source_metadata.get("fields", [])
            if isinstance(field, dict) and field.get("name")
        }

        missing_source_fields = [
            field
            for field in normalized_source_fields
            if field not in source_metadata_fields
        ]

        if missing_source_fields:
            raise RuntimeError(
                "FORGE AI foreign key proposal contains source fields "
                "that do not exist: "
                + ", ".join(missing_source_fields),
            )

        target_identity_fields = target_metadata.get("identity_fields", [])

        if (
            not isinstance(target_identity_fields, list)
            or not target_identity_fields
        ):
            raise RuntimeError(
                "FORGE AI foreign key proposal targets an entity without an identity.",
            )

        if len(normalized_source_fields) != len(target_identity_fields):
            raise RuntimeError(
                "FORGE AI foreign key proposal source-field count does not "
                "match the target identity.",
            )

        return AIForeignKeyProposal(
            status=proposal_status,
            message=response_message.strip(),
            proposal={
                "source_entity": normalized_source_entity,
                "source_fields": normalized_source_fields,
                "target_entity": normalized_target_entity,
            },
        )

    def propose_constraint(
        self,
        mode: str,
        entities: list[dict[str, object]],
        request: str,
        existing_constraint: dict[str, object] | None = None,
    ) -> AIConstraintProposal:
        """Generate a structured FORGE constraint proposal."""

        normalized_mode = mode.strip().upper()
        normalized_request = request.strip()

        if normalized_mode not in {"CREATE", "EDIT"}:
            raise ValueError(
                "Constraint proposal mode must be CREATE or EDIT.",
            )

        if not entities:
            raise ValueError(
                "At least one entity is required for a constraint proposal.",
            )

        if not normalized_request:
            raise ValueError(
                "Constraint proposal request must not be empty.",
            )

        if normalized_mode == "EDIT" and existing_constraint is None:
            raise ValueError(
                "Existing constraint is required in EDIT mode.",
            )

        payload = {
            "mode": normalized_mode,
            "entities": entities,
            "request": normalized_request,
            "existing_constraint": existing_constraint,
        }

        request_payload = {
            "model": self._model,
            "messages": [
                {
                    "role": "system",
                    "content": CONSTRAINT_PROPOSAL_SYSTEM_PROMPT,
                },
                {
                    "role": "user",
                    "content": json.dumps(
                        payload,
                        ensure_ascii=False,
                    ),
                },
            ],
            "stream": False,
            "format": {
                "type": "object",
                "properties": {
                    "status": {
                        "type": "string",
                        "enum": [
                            "PROPOSE",
                            "CLARIFY",
                            "UNSUPPORTED",
                        ],
                    },
                    "message": {
                        "type": "string",
                    },
                    "proposal": {
                        "type": [
                            "object",
                            "null",
                        ],
                        "properties": {
                            "entity": {
                                "type": "string",
                            },
                            "field": {
                                "type": "string",
                            },
                            "operator": {
                                "type": "string",
                                "enum": [
                                    ">",
                                    ">=",
                                    "<",
                                    "<=",
                                    "==",
                                    "!=",
                                ],
                            },
                            "value": {
                                "type": [
                                    "string",
                                    "integer",
                                    "number",
                                    "boolean",
                                ],
                            },
                        },
                        "required": [
                            "entity",
                            "field",
                            "operator",
                            "value",
                        ],
                        "additionalProperties": False,
                    },
                },
                "required": [
                    "status",
                    "message",
                    "proposal",
                ],
                "additionalProperties": False,
            },
        }

        provider_request = Request(
            f"{self._base_url}/api/chat",
            data=json.dumps(request_payload).encode("utf-8"),
            headers={
                "Accept": "application/json",
                "Content-Type": "application/json",
            },
            method="POST",
        )

        try:
            with urlopen(
                provider_request,
                timeout=self._generation_timeout_seconds,
            ) as response:
                provider_response = json.loads(
                    response.read().decode("utf-8"),
                )
        except (OSError, URLError) as exc:
            raise RuntimeError(
                "FORGE AI could not reach the configured Ollama provider.",
            ) from exc

        message = provider_response.get("message")

        if not isinstance(message, dict):
            raise RuntimeError(
                "FORGE AI returned an invalid chat response.",
            )

        raw_response = message.get("content")

        if not isinstance(raw_response, str) or not raw_response.strip():
            raise RuntimeError(
                "FORGE AI returned an empty constraint proposal.",
            )

        try:
            proposal_response = json.loads(raw_response)
        except json.JSONDecodeError as exc:
            raise RuntimeError(
                "FORGE AI returned an invalid structured constraint proposal.",
            ) from exc

        if not isinstance(proposal_response, dict):
            raise RuntimeError(
                "FORGE AI returned an invalid constraint proposal structure.",
            )

        proposal_status = proposal_response.get("status")
        response_message = proposal_response.get("message")
        proposal = proposal_response.get("proposal")

        if proposal_status not in {
            "PROPOSE",
            "CLARIFY",
            "UNSUPPORTED",
        }:
            raise RuntimeError(
                "FORGE AI constraint proposal returned an invalid status.",
            )

        if (
            not isinstance(response_message, str)
            or not response_message.strip()
        ):
            raise RuntimeError(
                "FORGE AI constraint proposal returned an invalid message.",
            )

        if proposal_status != "PROPOSE":
            if proposal is not None:
                raise RuntimeError(
                    "FORGE AI returned a proposal for a non-proposal status.",
                )

            return AIConstraintProposal(
                status=proposal_status,
                message=response_message.strip(),
                proposal=None,
            )

        if not isinstance(proposal, dict):
            raise RuntimeError(
                "FORGE AI constraint proposal is missing proposal data.",
            )

        entity = proposal.get("entity")
        field = proposal.get("field")
        operator = proposal.get("operator")
        value = proposal.get("value")

        if not isinstance(entity, str) or not entity.strip():
            raise RuntimeError(
                "FORGE AI constraint proposal contains an invalid entity.",
            )

        if not isinstance(field, str) or not field.strip():
            raise RuntimeError(
                "FORGE AI constraint proposal contains an invalid field.",
            )

        if operator not in {
            ">",
            ">=",
            "<",
            "<=",
            "==",
            "!=",
        }:
            raise RuntimeError(
                "FORGE AI constraint proposal contains an invalid operator.",
            )

        if isinstance(value, (dict, list)) or value is None:
            raise RuntimeError(
                "FORGE AI constraint proposal contains an invalid value.",
            )

        normalized_entity = entity.strip()
        normalized_field = field.strip()

        available_entities = {
            item.get("name")
            for item in entities
            if isinstance(item, dict)
        }

        if normalized_entity not in available_entities:
            raise RuntimeError(
                "FORGE AI constraint proposal references "
                "an unknown entity.",
            )

        entity_fields = {
            item.get("name")
            for item in entities
            if isinstance(item, dict)
            and item.get("name") == normalized_entity
            for item in item.get("fields", [])
            if isinstance(item, dict)
        }

        if normalized_field not in entity_fields:
            raise RuntimeError(
                "FORGE AI constraint proposal references "
                "an unknown field.",
            )

        normalized_proposal = {
            "entity": normalized_entity,
            "field": normalized_field,
            "operator": operator,
            "value": value,
        }

        return AIConstraintProposal(
            status="PROPOSE",
            message=response_message.strip(),
            proposal=normalized_proposal,
        )

    def _get_models(self) -> list[dict[str, object]]:
        """Retrieve models currently available from Ollama."""

        request = Request(
            f"{self._base_url}/api/tags",
            headers={"Accept": "application/json"},
            method="GET",
        )

        with urlopen(
            request,
            timeout=self._capability_timeout_seconds,
        ) as response:
            payload = json.loads(
                response.read().decode("utf-8"),
            )

        return payload.get("models", [])


RELATIONSHIP_PROPOSAL_SYSTEM_PROMPT = r'''
You are FORGE AI, an assistant for authoring executable synthetic-data specifications.

Propose an explicit relationship using ONLY entities and fields supplied in the
user payload.

Rules:

1. Never invent an entity.
2. Never invent a field.
3. Never rename a field.
4. Never create a helper field.
5. Never infer or create a foreign key.
6. Only reference fields that exist in the supplied entities.
7. If the user explicitly names entities and fields, use those exact names.
8. The payload may identify an entity's identity fields using
   "identity_fields". Identity fields are the fields that identify records
   of that entity. They are useful relationship targets, but relationship
   source fields do NOT have to be identity fields.
9. Supported relationship types:
   ONE_TO_ONE
   ONE_TO_MANY
   MANY_TO_ONE
   MANY_TO_MANY
10. Supported participation:
    MANDATORY
    OPTIONAL
11. Preserve the user's stated relationship semantics.
12. Preserve the user's stated source and target direction.
13. Interpret natural-language relationship direction literally.

    For example:

    "Each SalesOrder belongs to one Customer. Every SalesOrder must have a
    Customer, and a Customer can have many SalesOrders."

    MUST produce:

    source_entity = "SalesOrder"
    source_field = "CUSTOMER_ID"
    target_entity = "Customer"
    target_field = "CUSTOMER_ID"
    type = "MANY_TO_ONE"
    source_participation = "MANDATORY"
    target_participation = "OPTIONAL"

14. In a "belongs to", "references", or equivalent statement, the entity
    doing the belonging or referencing is the source and the entity being
    referenced is the target.
15. If the user explicitly names endpoint fields, use those exact fields.
16. If endpoint fields are not explicitly named, use the available model
    semantics to identify them only when the relationship is unambiguous.
    Otherwise return CLARIFY.
17. A request such as "create the relationship", "define a relationship",
    or "connect these entities" without explicit relationship semantics
    MUST return CLARIFY.
18. Do not choose a relationship direction, type, field, or participation
    merely because it appears plausible from the supplied schema.
19. If the request does not identify the entities or fields clearly enough,
    return CLARIFY.
20. If the request is asking to create a foreign key rather than define a
    relationship, return UNSUPPORTED.
21. For CREATE, propose a new relationship.
22. For EDIT, consider the supplied existing relationship.
23. Keep the response message concise and business-friendly.
24. Return JSON only.

Expected JSON:

{
  "status": "PROPOSE | CLARIFY | UNSUPPORTED",
  "message": "short explanation",
  "proposal": {
    "source_entity": "...",
    "source_field": "...",
    "target_entity": "...",
    "target_field": "...",
    "type": "ONE_TO_ONE | ONE_TO_MANY | MANY_TO_ONE | MANY_TO_MANY",
    "source_participation": "MANDATORY | OPTIONAL",
    "target_participation": "MANDATORY | OPTIONAL"
  }
}

For CLARIFY and UNSUPPORTED, proposal must be null.
'''
