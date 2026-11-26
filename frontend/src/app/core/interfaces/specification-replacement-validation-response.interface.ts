/**
 * ============================================================================
 * FORGE — Framework for Observed Rules, Generation & Engineered Data
 * ============================================================================
 *
 * File: specification-replacement-validation-response.interface.ts
 * Purpose: API response contract for canonical specification replacement validation.
 *
 * Author: Ranjoy Sen
 * Email: ranjoy.sen@collins.com
 *
 * ============================================================================
 */

import type { SpecificationValidationResult } from './specification-validation.interface';

export interface SpecificationReplacementValidationResponse {
  base_revision: string;
  csv_digest: string;
  summary: Record<string, number>;
  validation: {
    model_name: string;
    specification_version: string;
    vocabulary_version: string;
    errors: number;
    warnings: number;
    unsupported: number;
    passed: number;
    total_checks: number;
    entities_validated: number;
    can_continue: boolean;
    findings: SpecificationValidationResult['findings'];
    entities: SpecificationValidationResult['entities'];
  };
  specification: Record<string, unknown>;
}
