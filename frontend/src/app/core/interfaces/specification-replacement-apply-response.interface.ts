/**
 * ============================================================================
 * FORGE — Framework for Observed Rules, Generation & Engineered Data
 * ============================================================================
 *
 * File: specification-replacement-apply-response.interface.ts
 * Purpose: API response contract for applying specification replacement.
 *
 * Author: Ranjoy Sen
 * Email: ranjoy.sen@collins.com
 *
 * ============================================================================
 */

export interface SpecificationReplacementApplyResponse {
  applied: boolean;
  summary: Record<string, number>;
  specification_revision: string;
}
