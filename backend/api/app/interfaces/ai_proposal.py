"""
File: ai_proposal.py
Purpose: Domain contract for persisted FORGE AI proposals.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Any


@dataclass(frozen=True)
class AIProposal:
    """Represent an immutable generated AI proposal."""

    proposal_id: str
    owner_user_id: str
    proposal_type: str
    payload: dict[str, Any]
    created_at: datetime
    data_model_id: str | None = None
