/**
 * ============================================================================
 * FORGE — Framework for Observed Rules & Engineered Data
 * ============================================================================
 *
 * File: forge-foreign-key.interface.ts
 * Purpose: Defines the foreign key contract.
 *
 * Author: Ranjoy Sen
 * Email: ranjoy.sen@collins.com
 *
 * ============================================================================
 */

export interface ForgeForeignKey {
  name: string;
  source: {
    entity: string;
    fields: string[];
  };
  target: {
    entity: string;
    fields: string[];
  };
}
