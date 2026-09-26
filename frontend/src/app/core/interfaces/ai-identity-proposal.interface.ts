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
  status: AIIdentityProposalStatus;
  message: string;
  proposal: AIIdentityProposal | null;
}

export interface AIIdentityProposalRequest {
  mode: 'CREATE' | 'EDIT';
  entityName: string;
  fields: Array<Record<string, unknown>>;
  request: string;
  existingIdentity?: Record<string, unknown> | null;
}
