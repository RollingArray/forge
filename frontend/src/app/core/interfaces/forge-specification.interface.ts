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

import { ForgeConstraint } from './forge-constraint.interface';
import { ForgeForeignKey } from './forge-foreign-key.interface';
import { ForgeSpecificationDependency } from './forge-specification-dependency.interface';
import { ForgeSpecificationEntity } from './forge-specification-entity.interface';
import { ForgeSpecificationGeneration } from './forge-specification-generation.interface';
import { ForgeSpecificationModel } from './forge-specification-model.interface';
import { ForgeSpecificationRelationship } from './forge-specification-relationship.interface';

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
