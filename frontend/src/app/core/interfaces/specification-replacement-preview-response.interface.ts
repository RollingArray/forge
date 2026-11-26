/**
 * ============================================================================
 * FORGE — Framework for Observed Rules, Generation & Engineered Data
 * ============================================================================
 *
 * File: specification-replacement-preview-response.interface.ts
 * Purpose: API response contract for specification replacement preview.
 *
 * Author: Ranjoy Sen
 * Email: ranjoy.sen@collins.com
 *
 * ============================================================================
 */

export interface SpecificationReplacementPreviewResponse {
  base_revision: string;
  csv_digest: string;
  can_apply: boolean;
  summary: Record<string, number>;
  validation: null;
  issues: Record<string, unknown>[];
  candidate: Record<string, unknown> | null;
}
