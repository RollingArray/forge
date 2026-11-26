/**
 * ============================================================================
 * FORGE — Framework for Observed Rules, Generation & Engineered Data
 * ============================================================================
 *
 * File: specification-replacement-csv.interface.ts
 * Purpose: CSV sections used for full specification replacement.
 *
 * Author: Ranjoy Sen
 * Email: ranjoy.sen@collins.com
 *
 * ============================================================================
 */

export interface SpecificationReplacementCsv {
  entities: string;
  fields_and_keys: string;
  foreign_keys: string;
  relationships: string;
  constraints: string;
}
