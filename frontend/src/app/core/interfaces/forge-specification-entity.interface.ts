/**
 * ============================================================================
 * FORGE — Framework for Observed Rules & Engineered Data
 * ============================================================================
 *
 * File: forge-specification-entity.interface.ts
 * Purpose: Defines the specification entity contract.
 *
 * Author: Ranjoy Sen
 * Email: ranjoy.sen@collins.com
 *
 * ============================================================================
 */

import type { ForgeSpecificationField } from './forge-specification-field.interface';

export interface ForgeSpecificationEntity {
  name: string;
  description?: string;
  population?: {
    count?: number;
  };
  fields: ForgeSpecificationField[];
  identity?: {
    fields?: string[];
  };
}
