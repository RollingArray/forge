"""
File: specification_relationship_model.py
Purpose: API contracts for FORGE relationship authoring.

Author: Ranjoy Sen
Email: ranjoy.sen@collins.com
"""

from app.constants.specification_vocabulary import (
    RelationshipParticipation,
    RelationshipType,
)

from pydantic import BaseModel, ConfigDict, Field


class RelationshipEndpointRequest(BaseModel):
    """Complete endpoint definition for a relationship."""

    model_config = ConfigDict(extra="forbid")

    entity: str = Field(min_length=1)
    fields: list[str] = Field(min_length=1)


RelationshipEndpointValue = str | RelationshipEndpointRequest


class CreateRelationshipRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source_entity: str = Field(min_length=1)
    target_entity: str = Field(min_length=1)

    type: RelationshipType

    source_participation: RelationshipParticipation = "MANDATORY"
    target_participation: RelationshipParticipation = "MANDATORY"


class DeleteRelationshipRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source: RelationshipEndpointValue = Field(...)
    target: RelationshipEndpointValue = Field(...)

    type: RelationshipType

    source_participation: RelationshipParticipation = "MANDATORY"
    target_participation: RelationshipParticipation = "MANDATORY"


class UpdateRelationshipRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    existing: DeleteRelationshipRequest
    relationship: CreateRelationshipRequest
