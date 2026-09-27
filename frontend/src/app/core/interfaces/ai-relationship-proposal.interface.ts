/**
 * File: ai-relationship-proposal.interface.ts
 * Purpose: Frontend contract for FORGE AI relationship proposals.
 */

export type AIRelationshipProposalStatus =
  | 'PROPOSE'
  | 'CLARIFY'
  | 'UNSUPPORTED';

export type AIRelationshipType =
  | 'ONE_TO_ONE'
  | 'ONE_TO_MANY'
  | 'MANY_TO_ONE'
  | 'MANY_TO_MANY';

export type AIRelationshipParticipation =
  | 'MANDATORY'
  | 'OPTIONAL';

export interface AIRelationshipProposal {
  sourceEntity: string;
  sourceField: string;
  targetEntity: string;
  targetField: string;
  type: AIRelationshipType;
  sourceParticipation: AIRelationshipParticipation;
  targetParticipation: AIRelationshipParticipation;
}

export interface AIRelationshipProposalResponse {
  status: AIRelationshipProposalStatus;
  message: string;
  proposal: AIRelationshipProposal | null;
}

export interface AIRelationshipProposalRequest {
  mode: 'CREATE' | 'EDIT';
  entities: Array<Record<string, unknown>>;
  request: string;
  existingRelationship?: Record<string, unknown> | null;
}
