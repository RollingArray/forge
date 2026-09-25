/**
 * File: data-model.interface.ts
 * Purpose: Frontend domain model for a FORGE Data Model.
 */

export interface DataModel {
  dataModelId: string;
  ownerUserId: string;
  accessRole: 'OWNER' | 'CONTRIBUTOR' | 'VIEWER';
  name: string;
  description: string;
  color: string;
  tags: string[];
  entities: number;
  relationships: number;
  updated: string;
  status: string;
}
