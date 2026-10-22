/**
 * File: resource-reference.interface.ts
 * Purpose: Identifies a typed FORGE resource.
 */

import { ResourceType } from '../types/resource-type.type';

export interface ResourceReference {
  resourceType: ResourceType;
  dataModelId: string;
  jobId?: string;
  entityName?: string;
}
