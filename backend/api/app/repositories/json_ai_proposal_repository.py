"""
File: json_ai_proposal_repository.py
Purpose: JSON-backed persistence for FORGE AI proposals.
"""

from __future__ import annotations

import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock
from typing import Any

from app.interfaces.ai_proposal import AIProposal


class JsonAIProposalRepository:
    """Persist each AI proposal as an independent JSON record."""

    def __init__(self) -> None:
        self._data_directory = (
            Path(__file__).resolve().parents[2]
            / "data"
            / "ai_proposals"
        )
        self._lock = Lock()
        self._data_directory.mkdir(parents=True, exist_ok=True)

    def create(
        self,
        proposal_id: str,
        owner_user_id: str,
        proposal_type: str,
        payload: dict[str, Any],
        data_model_id: str | None = None,
    ) -> AIProposal:
        """Persist a proposal without allowing an existing ID to be overwritten."""

        if not proposal_id or not proposal_id.isalnum():
            raise ValueError("proposal_id must be a non-empty alphanumeric ID.")
        if not owner_user_id.strip():
            raise ValueError("owner_user_id must not be empty.")
        if not proposal_type.strip():
            raise ValueError("proposal_type must not be empty.")
        if not isinstance(payload, dict):
            raise ValueError("payload must be a JSON object.")

        # Validate JSON compatibility and detach the stored payload from callers.
        serialized_payload = json.dumps(payload, ensure_ascii=False)
        detached_payload = json.loads(serialized_payload)

        created_at = datetime.now(timezone.utc)
        proposal = AIProposal(
            proposal_id=proposal_id,
            owner_user_id=owner_user_id,
            proposal_type=proposal_type,
            payload=detached_payload,
            created_at=created_at,
            data_model_id=data_model_id,
        )

        record = {
            "proposal_id": proposal.proposal_id,
            "owner_user_id": proposal.owner_user_id,
            "proposal_type": proposal.proposal_type,
            "payload": proposal.payload,
            "created_at": proposal.created_at.isoformat(),
            "data_model_id": proposal.data_model_id,
        }

        destination = self._proposal_path(
            proposal_id,
            proposal_type,
            data_model_id,
        )
        destination.parent.mkdir(parents=True, exist_ok=True)

        with self._lock:
            temporary_path = None
            try:
                with tempfile.NamedTemporaryFile(
                    mode="w",
                    encoding="utf-8",
                    dir=destination.parent,
                    prefix=f".{proposal_id}.",
                    suffix=".tmp",
                    delete=False,
                ) as file:
                    temporary_path = Path(file.name)
                    json.dump(record, file, indent=2, ensure_ascii=False)
                    file.write("\n")
                    file.flush()
                    os.fsync(file.fileno())

                # Atomic creation fails rather than replacing an existing record.
                try:
                    os.link(temporary_path, destination)
                except FileExistsError as exc:
                    raise ValueError(
                        f"AI proposal already exists: {proposal_id}"
                    ) from exc
            finally:
                if temporary_path is not None and temporary_path.exists():
                    temporary_path.unlink()

        return proposal

    def get_by_id(
        self,
        proposal_id: str,
        owner_user_id: str,
    ) -> AIProposal | None:
        """Return a proposal only to its recorded owner."""

        if not proposal_id or not proposal_id.isalnum():
            return None

        with self._lock:
            matches = list(self._data_directory.rglob(f"{proposal_id}.json"))
            if len(matches) != 1:
                return None

            with matches[0].open("r", encoding="utf-8") as file:
                record = json.load(file)

        if record.get("owner_user_id") != owner_user_id:
            return None

        return self._to_proposal(record)

    def _proposal_path(
        self,
        proposal_id: str,
        proposal_type: str,
        data_model_id: str | None,
    ) -> Path:
        """Resolve a proposal to its category-specific JSON location."""

        if not proposal_id or not proposal_id.isalnum():
            raise ValueError("Invalid proposal ID.")

        if not proposal_type or not proposal_type.strip():
            raise ValueError("Invalid proposal type.")

        storage_type = proposal_type.strip().lower().replace(" ", "_")
        if not all(
            character.isalnum() or character == "_"
            for character in storage_type
        ):
            raise ValueError("Invalid proposal type.")

        if storage_type == "data_model":
            if data_model_id is not None:
                raise ValueError(
                    "A workspace data-model proposal must not have a data_model_id."
                )
            directory = self._data_directory / "data_model"
        else:
            if not data_model_id or not all(
                character.isalnum() or character == "-"
                for character in data_model_id
            ):
                raise ValueError(
                    "A Model Studio proposal requires a valid data_model_id."
                )
            directory = (
                self._data_directory
                / "model_studio"
                / data_model_id
                / storage_type
            )

        return directory / f"{proposal_id}.json"

    @staticmethod
    def _to_proposal(record: dict[str, Any]) -> AIProposal:
        """Convert a persisted record into the domain contract."""

        return AIProposal(
            proposal_id=record["proposal_id"],
            owner_user_id=record["owner_user_id"],
            proposal_type=record["proposal_type"],
            payload=record["payload"],
            created_at=datetime.fromisoformat(record["created_at"]),
            data_model_id=record.get("data_model_id"),
        )
