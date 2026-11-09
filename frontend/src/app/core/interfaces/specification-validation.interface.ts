/**
 * ============================================================================
 * FORGE — Framework for Observed Rules & Engineered Data
 * ============================================================================
 *
 * File: specification-validation.interface.ts
 * Purpose: API contract for deterministic FORGE specification validation.
 *
 * ============================================================================
 */

export type ValidationSeverity = 'error' | 'unsupported' | 'warning' | 'passed';

export type ValidationCategory =
  | 'Specification'
  | 'Model'
  | 'Entity'
  | 'Relationship'
  | 'Foreign Key'
  | 'Constraint'
  | 'Generation';

export interface SpecificationValidationFinding {
  id: string;
  severity: ValidationSeverity;
  category: ValidationCategory;
  title: string;
  details: string;
  remediation?: string | null;
  entity?: string | null;
  field?: string | null;
}

export interface SpecificationValidationEntity {
  name: string;
  status: 'valid' | 'warning' | 'error';
  checks: number;
  errors: number;
  warnings: number;
  unsupported: number;
}

export interface SpecificationValidationResult {
  modelName: string;
  specificationVersion: string;
  vocabularyVersion: string;
  errors: number;
  warnings: number;
  unsupported: number;
  passed: number;
  totalChecks: number;
  entitiesValidated: number;
  canContinue: boolean;
  findings: SpecificationValidationFinding[];
  entities: SpecificationValidationEntity[];
}
