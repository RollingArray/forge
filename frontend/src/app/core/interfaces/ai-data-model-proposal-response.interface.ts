/**
 * File: ai-data-model-proposal-response.interface.ts
 * Purpose: API response contract for FORGE AI Data Model proposals.
 */

export interface AIDataModelProposalResponse {
  proposal_id: string;
  name: string;
  description: string;
  suggested_tags: string[];
  reasoning: string;
}
