/**
 * Describes an AI-generated entity proposal for user review.
 */
export interface AIEntityProposal {
  name: string;
  description: string;
  population: number;
  reasoning: string;
}
