export type ValidationSeverity =
  | 'error'
  | 'warning'
  | 'passed';

export type ValidationCategory =
  | 'Specification'
  | 'Model'
  | 'Entity'
  | 'Relationship'
  | 'Foreign Key'
  | 'Constraint'
  | 'Generation';

export interface ValidationFinding {
  id: string;
  severity: ValidationSeverity;
  category: ValidationCategory;
  title: string;
  details: string;
  entity?: string;
  field?: string;
}

export interface ValidationEntity {
  name: string;
  status: 'valid' | 'warning' | 'error';
  checks: number;
  errors: number;
  warnings: number;
}

export interface ValidationViewModel {
  modelName: string;
  specificationVersion: string;
  vocabularyVersion: string;

  errors: number;
  warnings: number;
  passed: number;
  totalChecks: number;

  entitiesValidated: number;

  canContinue: boolean;

  findings: readonly ValidationFinding[];
  entities: readonly ValidationEntity[];
}
