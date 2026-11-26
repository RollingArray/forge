/**
 * ============================================================================
 * FORGE — Framework for Observed Rules, Generation & Engineered Data
 * ============================================================================
 *
 * File: specification-replacement-apply-request.interface.ts
 * Purpose: API request contract for applying specification replacement.
 *
 * Author: Ranjoy Sen
 * Email: ranjoy.sen@collins.com
 *
 * ============================================================================
 */

export interface SpecificationReplacementApplyRequest {
  base_revision: string;
  csv_digest: string;
  csv: import('./specification-replacement-csv.interface').SpecificationReplacementCsv;
}
