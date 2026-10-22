/**
 * File: resource-definition.interface.ts
 * Purpose: Describes a supported FORGE resource and its presentation metadata.
 */

import { ResourceReference } from './resource-reference.interface';
import { ResourceType } from '../types/resource-type.type';

export interface ResourceDefinition {
  type: ResourceType;
  label: string;
  icon: string;
  requiresJobId: boolean;
  buildRoute: (reference: ResourceReference) => string[] | null;
}
