/**
 * ============================================================================
 * FORGE — Framework for Observed Rules & Engineered Data
 * ============================================================================
 *
 * File: forge-specification-relationship.interface.ts
 * Purpose: Defines the specification relationship contract.
 *
 * Author: Ranjoy Sen
 * Email: ranjoy.sen@collins.com
 *
 * ============================================================================
 */

export interface ForgeSpecificationRelationship {
  source: string;
  target: string;
  type: string;
  source_participation?: string;
  target_participation?: string;
}
