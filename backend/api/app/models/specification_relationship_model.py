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


class CreateRelationshipRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source_entity: str = Field(min_length=1)
    target_entity: str = Field(min_length=1)

    type: RelationshipType

    source_participation: RelationshipParticipation = "MANDATORY"
    target_participation: RelationshipParticipation = "MANDATORY"


class DeleteRelationshipRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source: str = Field(min_length=1)
    target: str = Field(min_length=1)

    type: RelationshipType

    source_participation: RelationshipParticipation = "MANDATORY"
    target_participation: RelationshipParticipation = "MANDATORY"


class UpdateRelationshipRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    existing: DeleteRelationshipRequest
    relationship: CreateRelationshipRequest
