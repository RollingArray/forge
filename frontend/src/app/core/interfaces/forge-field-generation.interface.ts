/**
 * ============================================================================
 * FORGE — Framework for Observed Rules & Engineered Data
 * ============================================================================
 *
 * File: forge-field-generation.interface.ts
 * Purpose: Defines the field generation settings contract.
 *
 * Author: Ranjoy Sen
 * Email: ranjoy.sen@collins.com
 *
 * ============================================================================
 */

export interface ForgeFieldGeneration {
  strategy?: string;
  distribution?: string;
  generator?: string;
  parameters?: Record<string, unknown>;
}
