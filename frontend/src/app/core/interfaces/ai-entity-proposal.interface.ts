/**
 * Describes an AI-generated entity proposal for user review.
 */
export interface AIEntityProposal {
  proposalId: string;
  name: string;
  description: string;
  population: number;
  reasoning: string;
}
