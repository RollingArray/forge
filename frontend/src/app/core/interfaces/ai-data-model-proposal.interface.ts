/**
 * File: ai-data-model-proposal.interface.ts
 * Purpose: Frontend contract for a FORGE AI Data Model proposal.
 */

export interface AIDataModelProposal {
  name: string;
  description: string;
  suggestedTags: string[];
  reasoning: string;
}
