/**
 * File: ai-field-proposal.interface.ts
 * Purpose: Frontend contract for FORGE AI field proposals.
 */

export type AIFieldType =
  | 'IDENTIFIER'
  | 'STRING'
  | 'INTEGER'
  | 'DECIMAL'
  | 'BOOLEAN'
  | 'CATEGORICAL';

export type AIFieldProposalStatus =
  | 'PROPOSE'
  | 'CLARIFY'
  | 'UNSUPPORTED';

export interface AIFieldGenerationProposal {
  strategy?: string | null;
  distribution?: string | null;
  generator?: string | null;
  parameters?: Record<string, unknown> | null;
}

export interface AIFieldIdentityProposal {
  strategy: 'SEQUENTIAL_ID';
}

export interface AIFieldProposal {
  name: string;
  type: AIFieldType;
  identity?: AIFieldIdentityProposal | null;
  generation?: AIFieldGenerationProposal | null;
}

export interface AIFieldProposalResponse {
  status: AIFieldProposalStatus;
  message: string;
  proposal: AIFieldProposal | null;
}

export interface AIFieldProposalRequest {
  mode: 'CREATE' | 'EDIT';
  entityName: string;
  request: string;
  existingField?: Record<string, unknown> | null;
}
