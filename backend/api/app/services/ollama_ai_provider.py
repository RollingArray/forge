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
from app.prompts.field_proposal_prompt import FIELD_PROPOSAL_SYSTEM_PROMPT
from app.prompts.identity_proposal_prompt import IDENTITY_PROPOSAL_SYSTEM_PROMPT
from app.prompts.semantic_prompt import SEMANTIC_PREVIEW_SYSTEM_PROMPT
from app.interfaces.ai_provider import (
    AIDataModelProposal,
    AIFieldProposal,
    AIIdentityProposal,
    AISemanticPreview,
    AIProvider,
    AIProviderStatus,
)


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
