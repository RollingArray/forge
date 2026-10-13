/**
 * ============================================================================
 * FORGE — Framework for Observed Rules & Engineered Data
 * ============================================================================
 *
 * File: forge-constraint.interface.ts
 * Purpose: Defines the specification constraint contract.
 *
 * Author: Ranjoy Sen
 * Email: ranjoy.sen@collins.com
 *
 * ============================================================================
 */

export interface ForgeConstraint {
  entity: string;
  field: string;
  operator: string;
  value: string | number | boolean;
}
