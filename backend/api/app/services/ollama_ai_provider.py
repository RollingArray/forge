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
from app.interfaces.ai_provider import (
    AIDataModelProposal,
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

        system_prompt = """
You are FORGE AI, an assistant for creating enterprise Data Models.

Your responsibility in this step is ONLY to help define the identity and
high-level metadata of a Data Model.

Rules:
- Create a concise, meaningful Data Model name.
- Create a concise enterprise-friendly description.
- Suggest 3 to 10 useful tags.
- Tags should describe business domains, processes, systems, technologies,
  or concepts present in the user's request.
- Keep tags concise.
- Do not generate entities.
- Do not generate fields.
- Do not generate relationships.
- Do not generate foreign keys.
- Do not generate constraints.
- Do not generate SAP technical table or field metadata.
- Do not generate synthetic data.
- Do not invent detailed technical architecture.
- The reasoning should briefly explain how the proposal reflects the user's
  stated intent.
""".strip()

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
