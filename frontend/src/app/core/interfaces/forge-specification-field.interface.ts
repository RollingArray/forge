/**
 * ============================================================================
 * FORGE — Framework for Observed Rules & Engineered Data
 * ============================================================================
 *
 * File: forge-specification-field.interface.ts
 * Purpose: Defines the specification field contract.
 *
 * Author: Ranjoy Sen
 * Email: ranjoy.sen@collins.com
 *
 * ============================================================================
 */

import type { ForgeFieldGeneration } from './forge-field-generation.interface';

export interface ForgeSpecificationField {
  name: string;
  type: string;
  description?: string;
  generation?: ForgeFieldGeneration;
  identity?: {
    strategy?: string;
  };
}
