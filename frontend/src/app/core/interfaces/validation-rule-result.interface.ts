export interface ValidationRuleResult {
  rule_id: string;
  category: string;
  status: string;
  evaluated?: boolean;
  details?: Record<string, unknown>;
}
