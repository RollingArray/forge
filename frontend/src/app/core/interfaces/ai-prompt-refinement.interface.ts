/**
 * Frontend contract for iterative business-prompt refinement.
 */

export type AIPromptCompletenessStatus =
  | 'INCOMPLETE'
  | 'NEEDS_REVIEW'
  | 'READY_FOR_SPECIFICATION';

export type AIPromptRefinementAnswerType =
  | 'yes_no'
  | 'integer'
  | 'decimal'
  | 'text'
  | 'field'
  | 'operator'
  | 'choice';

export interface AIPromptRefinementQuestion {
  id: string;
  question: string;
  answer_type: AIPromptRefinementAnswerType;
  options: string[];
  suggested_answer: string | null;
  recommendation_rationale: string | null;
  required: boolean;
}

export interface AIPromptRefinementResponse {
  refined_prompt: string;
  completeness_status: AIPromptCompletenessStatus;
  summary: string;
  understood_requirements: string[];
  assumptions: string[];
  open_questions: AIPromptRefinementQuestion[];
  missing_requirements: string[];
}
