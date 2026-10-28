/**
 * Frontend contract for a whole-specification authoring proposal.
 */

export type AIWholeSpecificationProposalStatus =
  | 'PROPOSE'
  | 'CLARIFY'
  | 'INVALID'
  | 'UNSUPPORTED';

export interface AIWholeSpecificationValidation {
  can_continue: boolean;
  findings: unknown[];
}

export interface AIWholeSpecificationRecommendation {
  id: string;
  title: string;
  proposed_value: string;
  rationale: string;
  alternatives: string[];
  requires_confirmation: boolean;
}

export type AIWholeSpecificationAnswerType = "text" | "field" | "number" | "choice";

export interface AIWholeSpecificationDecisionItem {
  id: string;
  question: string;
  answer_type: AIWholeSpecificationAnswerType;
  required: boolean;
  recommendation: AIWholeSpecificationRecommendation | null;
}

export interface AIWholeSpecificationProposalResponse {
  status: AIWholeSpecificationProposalStatus;
  message: string;
  specification: Record<string, unknown> | null;
  assumptions: string[];
  clarification_questions: string[];
  reasoning: string;
  validation: AIWholeSpecificationValidation;
  recommendations: AIWholeSpecificationRecommendation[];
  decision_items: AIWholeSpecificationDecisionItem[];
}
