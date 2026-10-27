/**
 * File: ai-data-model-proposal.interface.ts
 * Purpose: Frontend contract for a FORGE AI Data Model proposal.
 */

export interface AIDataModelProposal {
  proposalId: string;
  name: string;
  description: string;
  suggestedTags: string[];
  reasoning: string;
}
