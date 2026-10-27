/**
 * File: ai-identity-proposal.interface.ts
 * Purpose: Frontend contract for FORGE AI entity identity proposals.
 */

export type AIIdentityProposalStatus =
  | 'PROPOSE'
  | 'CLARIFY'
  | 'UNSUPPORTED';

export interface AIIdentityProposal {
  fields: string[];
}

export interface AIIdentityProposalResponse {
  proposalId: string;
  status: AIIdentityProposalStatus;
  message: string;
  proposal: AIIdentityProposal | null;
}

export interface AIIdentityProposalRequest {
  dataModelId: string;
  regenerate?: boolean;
  mode: 'CREATE' | 'EDIT';
  entityName: string;
  fields: Array<Record<string, unknown>>;
  request: string;
  existingIdentity?: Record<string, unknown> | null;
}
