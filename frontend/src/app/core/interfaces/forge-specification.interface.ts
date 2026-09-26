/**
 * ============================================================================
 * FORGE — Framework for Observed Rules & Engineered Data
 * ============================================================================
 *
 * File: forge-specification.interface.ts
 * Purpose: Frontend representation of the canonical FORGE specification.
 *
 * Author: Ranjoy Sen
 * Email: ranjoy.sen@collins.com
 *
 * ============================================================================
 */

export interface ForgeSpecification {
  version: string;
  vocabularyVersion: string;
  model: ForgeSpecificationModel;
  generation: ForgeSpecificationGeneration;
  entities: ForgeSpecificationEntity[];
  relationships: ForgeSpecificationRelationship[];
  foreignKeys: ForgeForeignKey[];
  constraints: ForgeConstraint[];
  dependencies: ForgeSpecificationDependency[];
  statisticalBehavior: unknown[];
  scenarios: unknown[];
}

export interface ForgeSpecificationModel {
  name: string;
  description: string;
}

export interface ForgeSpecificationGeneration {
  seed: number;
  scenario: string;
}

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

export interface ForgeSpecificationField {
  name: string;
  type: string;
  description?: string;
  generation?: ForgeFieldGeneration;
  identity?: {
    strategy?: string;
  };
}

export interface ForgeFieldGeneration {
  strategy?: string;
  distribution?: string;
  generator?: string;
  parameters?: Record<string, unknown>;
}

export interface ForgeSpecificationRelationship {
  source: string;
  target: string;
  type: string;
  source_participation?: string;
  target_participation?: string;
}

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

export interface ForgeConstraint {
  entity: string;
  field: string;
  operator: string;
  value: string | number | boolean;
}

export interface ForgeSpecificationDependency {
  [key: string]: unknown;
}
