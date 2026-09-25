"""
File: activity.py
Purpose: FORGE activity constants.

Author: Ranjoy Sen
Email: ranjoy.sen@collins.com
"""

from dataclasses import dataclass
from enum import StrEnum


class ActivityType(StrEnum):
    """Define supported FORGE activity event types."""

    USER_SIGNED_IN = "USER_SIGNED_IN"

    DATA_MODEL_CREATED = "DATA_MODEL_CREATED"
    DATA_MODEL_UPDATED = "DATA_MODEL_UPDATED"
    DATA_MODEL_DELETED = "DATA_MODEL_DELETED"
    DATA_MODEL_DUPLICATED = "DATA_MODEL_DUPLICATED"
    DATA_MODEL_ACCESS_GRANTED = "DATA_MODEL_ACCESS_GRANTED"
    DATA_MODEL_ACCESS_ROLE_CHANGED = "DATA_MODEL_ACCESS_ROLE_CHANGED"
    DATA_MODEL_ACCESS_REVOKED = "DATA_MODEL_ACCESS_REVOKED"

    ENTITY_ADDED = "ENTITY_ADDED"
    ENTITY_UPDATED = "ENTITY_UPDATED"
    ENTITY_DELETED = "ENTITY_DELETED"

    FIELD_ADDED = "FIELD_ADDED"
    FIELD_UPDATED = "FIELD_UPDATED"
    FIELD_DELETED = "FIELD_DELETED"

    RELATIONSHIP_ADDED = "RELATIONSHIP_ADDED"
    RELATIONSHIP_UPDATED = "RELATIONSHIP_UPDATED"
    RELATIONSHIP_DELETED = "RELATIONSHIP_DELETED"

    CONSTRAINT_ADDED = "CONSTRAINT_ADDED"
    CONSTRAINT_UPDATED = "CONSTRAINT_UPDATED"
    CONSTRAINT_DELETED = "CONSTRAINT_DELETED"

    AI_PROPOSAL_GENERATED = "AI_PROPOSAL_GENERATED"
    AI_PROPOSAL_ACCEPTED = "AI_PROPOSAL_ACCEPTED"
    AI_PROPOSAL_REGENERATED = "AI_PROPOSAL_REGENERATED"
    AI_PROPOSAL_DISMISSED = "AI_PROPOSAL_DISMISSED"

    MODEL_VALIDATED = "MODEL_VALIDATED"
    MODEL_VALIDATION_FAILED = "MODEL_VALIDATION_FAILED"

    GENERATION_STARTED = "GENERATION_STARTED"
    GENERATION_COMPLETED = "GENERATION_COMPLETED"
    GENERATION_FAILED = "GENERATION_FAILED"
    GENERATION_CANCELLED = "GENERATION_CANCELLED"

    DATASET_EXPORTED = "DATASET_EXPORTED"


@dataclass(frozen=True)
class ActivityPresentation:
    """Define Workspace presentation metadata for an activity type."""

    icon: str
    accent: str


ACTIVITY_PRESENTATION: dict[ActivityType, ActivityPresentation] = {
    ActivityType.USER_SIGNED_IN: ActivityPresentation(
        icon="login",
        accent="purple",
    ),
    ActivityType.DATA_MODEL_CREATED: ActivityPresentation(
        icon="add_circle",
        accent="green",
    ),
    ActivityType.DATA_MODEL_UPDATED: ActivityPresentation(
        icon="edit",
        accent="blue",
    ),
    ActivityType.DATA_MODEL_DELETED: ActivityPresentation(
        icon="delete",
        accent="red",
    ),
    ActivityType.DATA_MODEL_DUPLICATED: ActivityPresentation(
        icon="content_copy",
        accent="purple",
    ),
    ActivityType.DATA_MODEL_ACCESS_GRANTED: ActivityPresentation(
        icon="person_add",
        accent="green",
    ),
    ActivityType.DATA_MODEL_ACCESS_ROLE_CHANGED: ActivityPresentation(
        icon="manage_accounts",
        accent="blue",
    ),
    ActivityType.DATA_MODEL_ACCESS_REVOKED: ActivityPresentation(
        icon="person_remove",
        accent="red",
    ),
    ActivityType.ENTITY_ADDED: ActivityPresentation(
        icon="account_tree",
        accent="green",
    ),
    ActivityType.ENTITY_UPDATED: ActivityPresentation(
        icon="account_tree",
        accent="blue",
    ),
    ActivityType.ENTITY_DELETED: ActivityPresentation(
        icon="account_tree",
        accent="red",
    ),
    ActivityType.FIELD_ADDED: ActivityPresentation(
        icon="view_column",
        accent="green",
    ),
    ActivityType.FIELD_UPDATED: ActivityPresentation(
        icon="view_column",
        accent="blue",
    ),
    ActivityType.FIELD_DELETED: ActivityPresentation(
        icon="view_column",
        accent="red",
    ),
    ActivityType.RELATIONSHIP_ADDED: ActivityPresentation(
        icon="hub",
        accent="green",
    ),
    ActivityType.RELATIONSHIP_UPDATED: ActivityPresentation(
        icon="hub",
        accent="blue",
    ),
    ActivityType.RELATIONSHIP_DELETED: ActivityPresentation(
        icon="hub",
        accent="red",
    ),
    ActivityType.CONSTRAINT_ADDED: ActivityPresentation(
        icon="rule",
        accent="green",
    ),
    ActivityType.CONSTRAINT_UPDATED: ActivityPresentation(
        icon="rule",
        accent="blue",
    ),
    ActivityType.CONSTRAINT_DELETED: ActivityPresentation(
        icon="rule",
        accent="red",
    ),
    ActivityType.AI_PROPOSAL_GENERATED: ActivityPresentation(
        icon="auto_awesome",
        accent="purple",
    ),
    ActivityType.AI_PROPOSAL_ACCEPTED: ActivityPresentation(
        icon="check_circle",
        accent="green",
    ),
    ActivityType.AI_PROPOSAL_REGENERATED: ActivityPresentation(
        icon="refresh",
        accent="blue",
    ),
    ActivityType.AI_PROPOSAL_DISMISSED: ActivityPresentation(
        icon="close",
        accent="gray",
    ),
    ActivityType.MODEL_VALIDATED: ActivityPresentation(
        icon="verified",
        accent="green",
    ),
    ActivityType.MODEL_VALIDATION_FAILED: ActivityPresentation(
        icon="error",
        accent="red",
    ),
    ActivityType.GENERATION_STARTED: ActivityPresentation(
        icon="play_circle",
        accent="blue",
    ),
    ActivityType.GENERATION_COMPLETED: ActivityPresentation(
        icon="check_circle",
        accent="green",
    ),
    ActivityType.GENERATION_FAILED: ActivityPresentation(
        icon="error",
        accent="red",
    ),
    ActivityType.GENERATION_CANCELLED: ActivityPresentation(
        icon="cancel",
        accent="gray",
    ),
    ActivityType.DATASET_EXPORTED: ActivityPresentation(
        icon="download",
        accent="blue",
    ),
}
