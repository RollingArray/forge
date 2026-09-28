/**
 * File: ai-foreign-key-proposal.interface.ts
 * Purpose: Defines the frontend contract for FORGE AI foreign-key proposals.
 *
 * Author: Ranjoy Sen
 * Email: ranjoy.sen@collins.com
 */

export type AIForeignKeyProposalStatus =
  | 'PROPOSE'
  | 'CLARIFY'
  | 'UNSUPPORTED';

export interface AIForeignKeyProposal {
  sourceEntity: string;
  sourceFields: string[];
  targetEntity: string;
}

export interface AIForeignKeyEntityField {
  name: string;
  type: string;
}

export interface AIForeignKeyEntity {
  name: string;
  fields: AIForeignKeyEntityField[];
  identity_fields: string[];
}

export interface AIForeignKeyProposalRequest {
  mode: 'CREATE' | 'EDIT';
  entities: AIForeignKeyEntity[];
  request: string;
  existingForeignKey?: Record<string, unknown> | null;
}

export interface AIForeignKeyProposalResponse {
  status: AIForeignKeyProposalStatus;
  message: string;
  proposal: AIForeignKeyProposal | null;
}
