"""
FORGE Generation Core
Semantic value generation service.

This module is responsible for obtaining semantic STRING values
from the configured LLM service.

It is UI-independent.
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Any


DEFAULT_OLLAMA_URL = "http://localhost:11434/api/generate"
DEFAULT_MODEL = "gemma4:12b"
SEMANTIC_VALUE_COUNT = 10

SEMANTIC_MODE_VOCABULARY = "VOCABULARY"
SEMANTIC_MODE_UNIQUE = "UNIQUE"

SUPPORTED_SEMANTIC_MODES = {
    SEMANTIC_MODE_VOCABULARY,
    SEMANTIC_MODE_UNIQUE,
}


def get_ollama_url() -> str:
    """Return the configured Ollama endpoint."""

    return os.getenv(
        "AIXP_OLLAMA_URL",
        DEFAULT_OLLAMA_URL,
    )


def get_model() -> str:
    """Return the configured Ollama model."""

    return os.getenv(
        "AIXP_LLM_MODEL",
        DEFAULT_MODEL,
    )


def normalize_semantic_mode(mode: str | None) -> str:
    """Return a validated semantic generation mode."""

    if mode is None:
        return SEMANTIC_MODE_VOCABULARY

    normalized = str(mode).strip().upper()

    if normalized not in SUPPORTED_SEMANTIC_MODES:
        raise ValueError(
            f"Unsupported SEMANTIC mode: {mode!r}. "
            f"Supported modes: {sorted(SUPPORTED_SEMANTIC_MODES)}"
        )

    return normalized


def build_semantic_system_prompt(
    mode: str = SEMANTIC_MODE_VOCABULARY,
) -> str:
    """Build the semantic generation contract."""

    normalized_mode = normalize_semantic_mode(mode)

    mode_instruction = (
        "Generate reusable categorical values. "
        "The values may intentionally repeat across records."
        if normalized_mode == SEMANTIC_MODE_VOCABULARY
        else
        "Generate representative semantic base values that FORGE "
        "will use to construct unique record-level values."
    )

    return f"""
You are the FORGE Semantic Data Generation Service.

Your responsibility is to generate representative STRING values
for a declared semantic field.

You will receive one natural-language description of the values
that are required.

Semantic mode: {normalized_mode}

{mode_instruction}

Return ONLY valid JSON with exactly these keys:

{{
  "status": "PROPOSE" | "CLARIFY" | "UNSUPPORTED",
  "message": "<short explanation>",
  "preview_values": []
}}

For PROPOSE:
- status must be PROPOSE
- message must be non-empty
- preview_values must contain exactly {SEMANTIC_VALUE_COUNT} strings
- values must directly represent the supplied semantic description
- do not number the values
- do not add commentary

For CLARIFY:
- status must be CLARIFY
- message must explain what is missing
- preview_values must be []

For UNSUPPORTED:
- status must be UNSUPPORTED
- message must explain why
- preview_values must be []

Do not return FORGE operations.
Do not return FORGE specifications.
Do not return metadata.
Do not return reasoning.
Do not return markdown.
"""


def call_semantic_llm(
    description: str,
    mode: str = SEMANTIC_MODE_VOCABULARY,
) -> str:
    """Call the configured Ollama model for semantic values."""

    normalized_mode = normalize_semantic_mode(mode)

    payload = {
        "model": get_model(),
        "prompt": (
            "SEMANTIC STRING REQUIREMENT:\n\n"
            f"MODE: {normalized_mode}\n\n"
            f"{description}\n\n"
            "Generate representative values according to the semantic contract."
        ),
        "system": build_semantic_system_prompt(),
        "stream": False,
        "format": "json",
        "options": {
            "temperature": 0,
        },
        "think": False,
    }

    request = urllib.request.Request(
        get_ollama_url(),
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(
            request,
            timeout=120,
        ) as response:
            response_body = response.read().decode("utf-8")

    except urllib.error.URLError as exc:
        raise RuntimeError(
            "Unable to reach Ollama at "
            f"{get_ollama_url()}. "
            f"Make sure Ollama is running and model '{get_model()}' "
            "is available."
        ) from exc

    try:
        response_payload = json.loads(response_body)

    except json.JSONDecodeError as exc:
        raise RuntimeError(
            "Ollama returned invalid JSON."
        ) from exc

    response_text = response_payload.get("response")

    if not isinstance(response_text, str):
        raise RuntimeError(
            "Ollama response did not contain a textual response."
        )

    return response_text.strip()


def parse_semantic_response(
    raw_response: str,
) -> list[str]:
    """Validate a semantic response and return its values."""

    text = raw_response.strip()

    if text.startswith("```"):
        lines = text.splitlines()

        if lines and lines[0].startswith("```"):
            lines = lines[1:]

        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]

        text = "\n".join(lines).strip()

    try:
        response: Any = json.loads(text)

    except json.JSONDecodeError as exc:
        raise ValueError(
            "SEMANTIC LLM response was not valid JSON."
        ) from exc

    if not isinstance(response, dict):
        raise ValueError(
            "SEMANTIC LLM response must be a JSON object."
        )

    expected_keys = {
        "status",
        "message",
        "preview_values",
    }

    if set(response.keys()) != expected_keys:
        raise ValueError(
            "SEMANTIC LLM response must contain exactly "
            "status, message, and preview_values."
        )

    status = response["status"]
    message = response["message"]
    values = response["preview_values"]

    if status not in {
        "PROPOSE",
        "CLARIFY",
        "UNSUPPORTED",
    }:
        raise ValueError(
            f"Unsupported SEMANTIC status: {status!r}"
        )

    if not isinstance(message, str) or not message.strip():
        raise ValueError(
            "SEMANTIC LLM response message must be non-empty."
        )

    if not isinstance(values, list):
        raise ValueError(
            "SEMANTIC preview_values must be a list."
        )

    if status == "PROPOSE":
        if len(values) != SEMANTIC_VALUE_COUNT:
            raise ValueError(
                "SEMANTIC PROPOSE response must contain exactly "
                f"{SEMANTIC_VALUE_COUNT} values; got {len(values)}."
            )

        if any(not isinstance(value, str) for value in values):
            raise ValueError(
                "SEMANTIC values must all be strings."
            )

        return values

    if values:
        raise ValueError(
            f"SEMANTIC {status} response must not contain values."
        )

    raise RuntimeError(
        f"SEMANTIC generation returned {status}: {message.strip()}"
    )


def generate_semantic_values(
    description: str,
    mode: str = SEMANTIC_MODE_VOCABULARY,
) -> list[str]:
    """Generate semantic values from a field description."""

    if not isinstance(description, str) or not description.strip():
        raise ValueError(
            "SEMANTIC description must be a non-empty string."
        )

    normalized_mode = normalize_semantic_mode(mode)

    raw_response = call_semantic_llm(
        description.strip(),
        mode=normalized_mode,
    )

    return parse_semantic_response(
        raw_response,
    )
