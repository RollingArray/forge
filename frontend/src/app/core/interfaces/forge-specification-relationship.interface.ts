import { ForgeRelationshipEndpointValue } from '../types/forge-relationship-endpoint-value.type';

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
  source: ForgeRelationshipEndpointValue;
  target: ForgeRelationshipEndpointValue;
  type: string;
  source_participation?: string;
  target_participation?: string;
}
