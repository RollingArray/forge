/**
 * File: ai-constraint-proposal.interface.ts
 * Purpose: Frontend contract for FORGE AI constraint proposals.
 */

export type AIConstraintProposalStatus =
  | 'PROPOSE'
  | 'CLARIFY'
  | 'UNSUPPORTED';

export type AIConstraintOperator =
  | '>'
  | '>='
  | '<'
  | '<='
  | '=='
  | '!=';

export interface AIConstraintProposal {
  entity: string;
  field: string;
  operator: AIConstraintOperator;
  value: string | number | boolean;
}

export interface AIConstraintProposalResponse {
  status: AIConstraintProposalStatus;
  message: string;
  proposal: AIConstraintProposal | null;
}

export interface AIConstraintProposalRequest {
  mode: 'CREATE' | 'EDIT';
  entities: Array<Record<string, unknown>>;
  request: string;
  existingConstraint?: Record<string, unknown> | null;
}
